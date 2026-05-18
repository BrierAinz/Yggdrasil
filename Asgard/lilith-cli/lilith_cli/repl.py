"""Interactive REPL for Yggdrasil CLI v6.0.

Built on ``prompt_toolkit`` with Rich rendering, Norse-themed prompts,
streaming output with thinking panels, slash-command auto-completion,
conversation history, and auto-save on exit.

Inspired by Hermes Agent's REPL architecture (queue-based input,
line-buffered streaming, Rich panels for tool calls, OSC 52 clipboard).
"""

from __future__ import annotations

import asyncio
import json
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import TYPE_CHECKING, Any

from prompt_toolkit import PromptSession
from prompt_toolkit.auto_suggest import AutoSuggestFromHistory
from prompt_toolkit.completion import WordCompleter
from prompt_toolkit.history import FileHistory
from prompt_toolkit.key_binding import KeyBindings
from prompt_toolkit.lexers import PygmentsLexer
from prompt_toolkit.styles import Style as PtStyle
from pygments.lexers import MarkdownLexer as PygmentsMarkdownLexer
from rich.rule import Rule


if TYPE_CHECKING:
    from .agent import AgentSession
from .commands import CommandRegistry
from .config import CONFIG_DIR
from .render import (
    Timer,
    console,
    get_theme,
    list_themes,
    make_thinking_spinner,
    render_assistant_separator,
    render_error,
    render_markdown,
    render_thinking,
    render_tool_call,
    render_turn_end,
    render_user_separator,
    render_welcome,
    set_theme,
)


# ── Prompt constants ────────────────────────────────────────────────

_HISTORY_FILE = CONFIG_DIR / "history"
_CONVERSATIONS_DIR = CONFIG_DIR / "conversations"

_SLASH_COMMANDS = [
    "/help",
    "/tools",
    "/model",
    "/provider",
    "/memory",
    "/clear",
    "/status",
    "/config",
    "/quit",
    "/exit",
    "/save",
    "/redo",
    "/retry",
    "/copy",
    "/cp",
    "/system",
    "/history",
    "/hist",
    "/compact",
    "/summarize",
    "/resume",
    "/load",
    "/theme",
    "/themes",
    "/file",
    "/f",
    "/export",
    "/exp",
    "/h",
    "/?",
    "/m",
    "/cls",
    "/q",
]


def _prompt_continuation(width: int, row: int, column: int) -> list[tuple[str, str]]:
    """Return the continuation prompt for multi-line input.

    Shows theme-aligned dots aligned with the main prompt.
    Returns prompt_toolkit formatted text tuples (style, text).
    """
    theme = get_theme()
    return [("class:prompt.dots", f"{theme.prompt_prefix} ... ")]


# ── Clipboard helpers ───────────────────────────────────────────────


def _copy_to_clipboard(text: str) -> bool:
    """Try copying *text* to the system clipboard. Returns True on success."""
    # 1) Try OSC 52 (works over SSH / tmux)
    try:
        import base64

        encoded = base64.b64encode(text.encode("utf-8")).decode("ascii")
        sys.stdout.write(f"\033]52;c;{encoded}\007")
        sys.stdout.flush()
        return True
    except Exception:
        pass

    # 2) Try WSL → Windows clipboard
    if _is_wsl():
        try:
            import subprocess

            subprocess.run(
                ["clip.exe"],
                input=text.encode("utf-8"),
                check=True,
                capture_output=True,
            )
            return True
        except Exception:
            pass

    # 3) Try xclip / xsel
    for cmd in ["xclip", "xsel", "pbcopy"]:
        try:
            import subprocess

            subprocess.run(
                [cmd],
                input=text.encode("utf-8"),
                check=True,
                capture_output=True,
            )
            return True
        except Exception:
            continue

    return False


def _is_wsl() -> bool:
    """Check if running under Windows Subsystem for Linux."""
    try:
        return "microsoft" in Path("/proc/version").read_text().lower()
    except Exception:
        return False


# ── Multi-line detection ────────────────────────────────────────────


def _is_multi_line_start(text: str) -> bool:
    """Return True if *text* starts an incomplete multi-line block
    (e.g., triple-quote, unclosed bracket).
    """
    stripped = text.rstrip()
    if stripped.endswith(":") and not stripped.startswith("/"):
        return True
    # Unmatched braces / brackets / parens.
    opens = "({["
    closes = ")}]"
    stack: list[str] = []
    for ch in text:
        if ch in opens:
            stack.append(ch)
        elif ch in closes:
            idx = closes.index(ch)
            if stack and stack[-1] == opens[idx]:
                stack.pop()
    return len(stack) > 0


# ── Conversation persistence ────────────────────────────────────────


def _auto_save_conversation(session: AgentSession) -> Path | None:
    """Save the conversation history as JSON. Returns the filepath or None."""
    if not session.history:
        return None

    _CONVERSATIONS_DIR.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now(UTC).strftime("%Y%m%d_%H%M%S")
    filepath = _CONVERSATIONS_DIR / f"conv_{timestamp}.json"

    data = {
        "timestamp": timestamp,
        "model": session.config.model,
        "provider": session.config.provider,
        "messages": session.history,
        "usage": session.total_usage,
    }
    try:
        filepath.write_text(
            json.dumps(data, indent=2, ensure_ascii=False, default=str),
            encoding="utf-8",
        )
        return filepath
    except Exception as exc:
        render_error(f"Error guardando conversación: {exc}")
        return None


def _list_saved_conversations() -> list[dict[str, Any]]:
    """Return a sorted list of saved conversation metadata (newest first)."""
    if not _CONVERSATIONS_DIR.exists():
        return []

    conversations: list[dict[str, Any]] = []
    for fpath in sorted(_CONVERSATIONS_DIR.glob("conv_*.json"), reverse=True):
        try:
            data = json.loads(fpath.read_text(encoding="utf-8"))
            messages = data.get("messages", [])
            # Build a short preview from the first user message.
            preview = ""
            for msg in messages:
                if msg.get("role") == "user":
                    content = msg.get("content", "")
                    preview = content[:80] + ("…" if len(content) > 80 else "")
                    break
            conversations.append(
                {
                    "file": fpath,
                    "name": fpath.stem,
                    "timestamp": data.get("timestamp", ""),
                    "model": data.get("model", "unknown"),
                    "provider": data.get("provider", "unknown"),
                    "message_count": len(messages),
                    "usage": data.get("usage", {}),
                    "preview": preview,
                }
            )
        except Exception:
            continue

    return conversations


def _load_conversation(filepath: Path) -> dict[str, Any] | None:
    """Load a conversation JSON file. Returns the full data dict or None."""
    try:
        return json.loads(filepath.read_text(encoding="utf-8"))
    except Exception as exc:
        render_error(f"Error cargando conversación: {exc}")
        return None


# ── Main REPL ───────────────────────────────────────────────────────


async def run_repl(session: AgentSession) -> None:
    """Launch the interactive REPL loop."""

    # Ensure directories exist.
    _HISTORY_FILE.parent.mkdir(parents=True, exist_ok=True)

    # ── Load saved theme from config ───────────────────────────────
    try:
        import yaml as _yaml

        from .config import CONFIG_FILE

        _raw = _yaml.safe_load(CONFIG_FILE.read_text(encoding="utf-8")) or {}
        _saved_theme = _raw.get("theme", "norse")
        if _saved_theme in [t.name for t in list_themes()]:
            set_theme(_saved_theme)
    except Exception:
        pass  # Fall back to default theme.

    # ── Render welcome ────────────────────────────────────────────
    render_welcome(
        model=session.config.model,
        provider=session.config.provider,
        tools_count=len(session.get_tool_descriptions()),
        has_memory=session.memory is not None,
    )
    console.print()

    # ── Command registry ──────────────────────────────────────────
    registry = CommandRegistry(session)
    registry.discover()

    # ── prompt_toolkit setup ─────────────────────────────────────
    history = FileHistory(str(_HISTORY_FILE))
    completer = WordCompleter(_SLASH_COMMANDS, ignore_case=True, sentence=True)

    # Build prompt_toolkit style from the active theme — dynamically
    # resolved so that /theme switches update the prompt immediately.
    from prompt_toolkit.styles import DynamicStyle

    def _build_pt_style():
        """Build a PtStyle dict from the current theme (called dynamically)."""
        t = get_theme()
        return PtStyle.from_dict(t.pt_style)

    pt_style = DynamicStyle(_build_pt_style)

    # Markdown lexer for syntax highlighting in the input area.
    md_lexer = PygmentsLexer(PygmentsMarkdownLexer)

    # ── Prompt mode state ────────────────────────────────────────
    _multiline_mode = {"active": False}
    _live_tokens = {"prompt": 0, "completion": 0, "total": 0, "turns": 0}

    def _bottom_toolbar():
        """Dynamic bottom toolbar showing input mode, turns, and token usage."""
        t = get_theme()
        mode = (
            f"{t.prompt_prefix} MULTILINE"
            if _multiline_mode["active"]
            else f"{t.prompt_prefix} SINGLE"
        )
        parts = [
            ("class:prompt", mode),
            ("", "  "),
            ("class:auto-suggestion", "Alt+Enter: nueva línea  Ctrl+O: toggle multiline"),
        ]
        # Show token bar if we have usage data.
        s = _live_tokens
        if s["total"] > 0:
            parts.append(("", "  "))
            parts.append(
                ("class:usage", f"Tokens: {s['prompt']}↑ {s['completion']}↓ {s['total']}Σ")
            )
            parts.append(("", " "))
            parts.append(("class:usage", f"Turn: {s['turns']}"))
        return parts

    prompt_session: PromptSession = PromptSession(
        history=history,
        auto_suggest=AutoSuggestFromHistory(),
        completer=completer,
        lexer=md_lexer,
        style=pt_style,
        multiline=False,
        prompt_continuation=_prompt_continuation,
        bottom_toolbar=_bottom_toolbar,
    )

    # Key bindings.
    kb = KeyBindings()

    @kb.add("c-c")
    def _cancel_current(event):
        """Ctrl+C cancels the current generation (not the REPL)."""
        event.app.exit(exception=KeyboardInterrupt, style="class:aborting")

    @kb.add("escape", "enter")
    def _insert_newline(event):
        """Alt+Enter inserts a newline for multi-line input.

        On Windows Terminal, Shift+Enter also sends Escape+Enter,
        so this doubles as Shift+Enter support.
        """
        event.current_buffer.insert_text("\n")

    @kb.add("c-o")
    def _toggle_multiline(event):
        """Ctrl+O toggles multiline mode for the current input."""
        _multiline_mode["active"] = not _multiline_mode["active"]
        buf = event.current_buffer
        buf.is_multiline = _multiline_mode["active"]
        # Toolbar updates automatically via _bottom_toolbar().
        event.app.invalidate()

    # ── Tool call callback ────────────────────────────────────────
    def on_tool_call(name: str, args: dict, result: str) -> None:
        render_tool_call(name, args, result)

    session._on_tool_call = on_tool_call

    # ── Turn counter ──────────────────────────────────────────────
    turn_number = 0

    # ── REPL loop ─────────────────────────────────────────────────
    try:
        while True:
            # Build prompt with turn counter and theme prefix.
            turn_number += 1
            model_name = session.config.model
            current_theme = get_theme()
            prompt_formatted = [
                ("class:prompt", f"{current_theme.prompt_prefix} {model_name}"),
                ("", ": "),
            ]

            try:
                user_input = await prompt_session.prompt_async(
                    prompt_formatted,
                    key_bindings=kb,
                    multiline=_multiline_mode["active"],
                )
            except KeyboardInterrupt:
                # Ctrl+C during prompt: cancel current generation, stay in REPL.
                console.print("[dim]^C Cancelado.[/]")
                continue
            except EOFError:
                # Ctrl+D: exit.
                console.print("\n[dim]Odin te guíe. Hasta la próxima.[/]")
                break

            text = user_input.strip()
            if not text:
                continue

            # ── Slash command dispatch ────────────────────────────
            if text.startswith("/"):
                try:
                    handled = await registry.dispatch(text)
                    if handled:
                        continue
                except SystemExit:
                    break

            # ── Process message via streaming ─────────────────────
            render_user_separator(text)

            try:
                await _process_with_streaming(session, text, stats=_live_tokens)
            except KeyboardInterrupt:
                console.print("\n[dim]^C Generación cancelada.[/]")
                continue
            except ConnectionError as exc:
                render_error(f"Error de conexión: {exc}")
                continue
            except Exception as exc:
                render_error(f"Error: {exc}")
                import traceback

                traceback.print_exc()
                continue

    finally:
        # ── Auto-save on exit ─────────────────────────────────────
        saved_path = _auto_save_conversation(session)
        if saved_path:
            console.print(f"[dim]Conversación guardada: {saved_path.name}[/]")


async def _process_with_streaming(
    session: AgentSession, text: str, stats: dict | None = None
) -> None:
    """Process a user message with streaming output rendering.

    Handles all event types from process_message_stream:
    - "reasoning": GLM-5.1 thinking content → dim panel
    - "text": normal LLM output → line-buffered with final Markdown
    - "tool_call": tool execution start → card
    - "tool_result": tool result → result card
    - "done": turn complete → usage + duration

    Shows an animated thinking spinner while waiting for the first token.
    """
    accumulated = ""
    reasoning_text = ""
    usage: dict[str, int] = {}
    timer = Timer()
    in_reasoning = False
    first_token_received = False
    _assistant_sep_shown = False

    timer.__enter__()

    # ── Start the thinking spinner (shows while LLM processes) ────
    spinner_info = make_thinking_spinner()
    spinner_status = spinner_info["status"]
    spinner_status.__enter__()

    try:
        async for event in session.process_message_stream(text):
            event_type = event.get("type", "")

            # ── Reasoning (GLM-5.1 thinking) ────────────────────
            if event_type == "reasoning":
                chunk = event.get("content", "")
                if chunk:
                    # Show assistant separator before first output.
                    if not _assistant_sep_shown:
                        _assistant_sep_shown = True
                        render_assistant_separator()
                    # Stop spinner on first token (reasoning counts).
                    if not first_token_received:
                        first_token_received = True
                        spinner_status.__exit__(None, None, None)
                        # Don't start spinner again for this turn.

                    reasoning_text += chunk
                    if not in_reasoning:
                        in_reasoning = True
                        # Open the thinking panel header.
                        console.print()
                        console.print(Rule("💭 Pensando...", style="dim magenta", characters="─"))

            # ── Normal text ──────────────────────────────────────
            elif event_type == "text":
                chunk = event.get("content", "")
                if chunk:
                    # Show assistant separator before first output.
                    if not _assistant_sep_shown:
                        _assistant_sep_shown = True
                        render_assistant_separator()
                    # Stop spinner on first real token.
                    if not first_token_received:
                        first_token_received = True
                        spinner_status.__exit__(None, None, None)

                    # Close reasoning panel if transitioning to content.
                    if in_reasoning:
                        in_reasoning = False
                        render_thinking(reasoning_text)
                        reasoning_text = ""
                        console.print()  # blank line before response

                    accumulated += chunk

            # ── Tool call start ───────────────────────────────────
            elif event_type == "tool_call":
                if not _assistant_sep_shown:
                    _assistant_sep_shown = True
                    render_assistant_separator()
                if not first_token_received:
                    first_token_received = True
                    spinner_status.__exit__(None, None, None)

                if accumulated.strip() or reasoning_text:
                    console.print()
                render_tool_call(event["name"], event["arguments"])

            # ── Tool result ──────────────────────────────────────
            elif event_type == "tool_result":
                if not first_token_received:
                    first_token_received = True
                    spinner_status.__exit__(None, None, None)

                render_tool_call(event["name"], {}, event["content"])

            # ── Turn complete ─────────────────────────────────────
            elif event_type == "done":
                usage = event.get("usage", {})
                break

    except StopAsyncIteration:
        pass
    except (KeyboardInterrupt, asyncio.CancelledError):
        # If spinner is still active, stop it.
        if not first_token_received:
            spinner_status.__exit__(None, None, None)
        raise

    # ── Stop spinner if it's somehow still running ──────────────
    if not first_token_received:
        spinner_status.__exit__(None, None, None)

    # ── Final rendering ─────────────────────────────────────────────
    # Close any remaining reasoning block.
    if in_reasoning and reasoning_text:
        render_thinking(reasoning_text)
        console.print()

    # Final newline.
    console.print()

    # If we have accumulated text, render as nicely formatted Markdown.
    if accumulated.strip():
        render_markdown(accumulated)

    # Show turn summary (duration + tokens).
    timer.__exit__(None, None, None)
    render_turn_end(timer.elapsed, usage or session.total_usage)

    # ── Update live token stats for the bottom toolbar ─────────────
    if stats is not None:
        tu = session.total_usage
        stats["prompt"] = tu.get("prompt_tokens", 0)
        stats["completion"] = tu.get("completion_tokens", 0)
        stats["total"] = tu.get("total_tokens", 0)
        stats["turns"] += 1

    # ── Update last user message for /redo ────────────────────────
    session._last_user_message = text


# ── One-shot mode ───────────────────────────────────────────────────


async def run_one_shot(session: AgentSession, prompt: str) -> None:
    """Process a single prompt and print the response (non-interactive)."""
    try:
        response = await session.process_message(prompt)
        console.print(response)
    except Exception as exc:
        render_error(f"Error: {exc}")
        sys.exit(1)
