"""Rich-based terminal renderer for Yggdrasil CLI v6.5.

Provides themed output helpers: markdown, streaming text, tool-call cards,
thinking panels, turn separators, welcome banners, and a theme system
with Norse / Cyberpunk / Minimal presets.
"""

from __future__ import annotations

import time
from contextlib import contextmanager
from typing import TYPE_CHECKING, Any


if TYPE_CHECKING:
    from collections.abc import Generator

from rich.console import Console, Group
from rich.live import Live
from rich.markdown import Markdown
from rich.panel import Panel
from rich.rule import Rule
from rich.syntax import Syntax
from rich.table import Table
from rich.text import Text
from rich.theme import Theme


# ── Theme system ───────────────────────────────────────────────────


class CLITheme:
    """A complete CLI theme definition.

    Attributes:
        name: Theme identifier (used in config and /theme command).
        label: Human-readable display name.
        description: One-line description shown in /theme list.
        theme: Rich ``Theme`` dict for console styling.
        banner: ASCII art string for the welcome banner.
        banner_title: Title inside the banner panel.
        banner_subtitle: Subtitle inside the banner panel.
        border_style: Rich style string for panel borders.
        rule_chars: Characters used in ``Rule`` separators.
        prompt_prefix: Unicode rune used as prompt prefix (᛭ by default).
        thinking_label: Label for thinking/reasoning panels.
        spinner_label: Label for the pre-stream spinner.
        pt_style: prompt_toolkit style dict (for the input prompt).
    """

    def __init__(
        self,
        name: str,
        label: str,
        description: str,
        theme: dict[str, str],
        banner: str,
        banner_title: str = "",
        banner_subtitle: str = "",
        border_style: str = "gold1",
        rule_chars: str = "─",
        prompt_prefix: str = "᛭",
        thinking_label: str = "💭 Pensando...",
        spinner_label: str = "Pensando",
        pt_style: dict[str, str] | None = None,
    ) -> None:
        self.name = name
        self.label = label
        self.description = description
        self.theme = theme
        self.banner = banner
        self.banner_title = banner_title
        self.banner_subtitle = banner_subtitle
        self.border_style = border_style
        self.rule_chars = rule_chars
        self.prompt_prefix = prompt_prefix
        self.thinking_label = thinking_label
        self.spinner_label = spinner_label
        self.pt_style = pt_style or {
            "": "#e0e0e0",
            "prompt": "#ffd700 bold",
            "prompt.dots": "#888888",
            "completion-menu": "bg:#1a1a2e #e0e0e0",
            "completion-menu.completion.current": "bg:#0f3460 #ffd700",
            "auto-suggestion": "#555555 italic",
        }


# ── Banner art ────────────────────────────────────────────────────

_NORSE_BANNER = r"""
           ᛭              ᛟ              ᛭
    ╔═══════════════════════════════════╗
    ║          YGGDRASIL  CLI          ║
    ║             v6.5                  ║
    ║     Where Ancient Meets Digital  ║
    ╚═══════════════════════════════════╝
               ┃      ┃      ┃
        ───────┸──────┸──────┸──────
          Asgard  Midgard  Muspelheim
"""

_CYBERPUNK_BANNER = r"""
          ▄▄▄▄▄ ▄▄   ▄▄▄▄▄ ▄▄   ▄▄▄
          █▄▄▄▄ █▄▄  █▄▄▄▄ █▄▄  █▄▄▄
          █▄▄▄▄ █▄▄▄ █▄▄▄▄ █▄▄▄ █▄▄▄
    ╔═══════════════════════════════════╗
    ║       ⟐ YGGDRASIL  CLI ⟐       ║
    ║             v6.5                  ║
    ║    Signals From The Edge Nodes   ║
    ╚═══════════════════════════════════╝
        ╠══╬══╬══╬══╬══╬══╣
        ║NE█║▓▓▓║▒▒▒║░░░║DA║
        ╚══╩══╩══╩══╩══╩══╝
"""

_MINIMAL_BANNER = r"""
    yggdrasil v6.5
    ─────────────────
"""


# ── Theme presets ──────────────────────────────────────────────────

THEMES: dict[str, CLITheme] = {
    "norse": CLITheme(
        name="norse",
        label="Norse",
        description="Dark-fantasy gold & runes — default theme",
        theme={
            "realm": "gold1",
            "frost": "deep_sky_blue3",
            "grove": "chartreuse3",
            "bark": "tan",
            "rune": "gold1",
            "error": "bold red",
            "success": "green",
            "warning": "yellow",
            "info": "cyan",
            "tool.name": "bold cyan",
            "tool.arg": "dim cyan",
            "tool.result": "green",
            "thinking": "dim italic magenta",
            "usage": "dim",
            "model": "bold gold1",
            "status.ok": "green",
            "status.fail": "red",
            "status.warn": "yellow",
            "turn": "dim gold1",
            "duration": "dim italic",
        },
        banner=_NORSE_BANNER,
        banner_title="[bold red]᛭ Yggdrasil Agent ᛭[/]",
        banner_subtitle="[dim]Where Ancient Meets Digital[/]",
        border_style="gold1",
        rule_chars="─",
        prompt_prefix="᛭",
        thinking_label="[dim]💭 Pensando...[/]",
        spinner_label="Pensando",
        pt_style={
            "": "#e0e0e0",
            "prompt": "#ffd700 bold",
            "prompt.dots": "#888888",
            "completion-menu": "bg:#1a1a2e #e0e0e0",
            "completion-menu.completion.current": "bg:#0f3460 #ffd700",
            "auto-suggestion": "#555555 italic",
        },
    ),
    "cyberpunk": CLITheme(
        name="cyberpunk",
        label="Cyberpunk",
        description="Neon cyan & magenta — digital rain vibes",
        theme={
            "realm": "bright_magenta",
            "frost": "cyan",
            "grove": "bright_green",
            "bark": "grey50",
            "rune": "bright_cyan",
            "error": "bold bright_red",
            "success": "bright_green",
            "warning": "bright_yellow",
            "info": "bright_cyan",
            "tool.name": "bold bright_magenta",
            "tool.arg": "dim cyan",
            "tool.result": "bright_green",
            "thinking": "dim italic bright_magenta",
            "usage": "dim",
            "model": "bold bright_cyan",
            "status.ok": "bright_green",
            "status.fail": "bright_red",
            "status.warn": "bright_yellow",
            "turn": "dim cyan",
            "duration": "dim italic",
        },
        banner=_CYBERPUNK_BANNER,
        banner_title="[bold bright_magenta]⟐ Yggdrasil  CLI ⟐[/]",
        banner_subtitle="[dim bright_cyan]Signals From The Edge Nodes[/]",
        border_style="bright_magenta",
        rule_chars="═",
        prompt_prefix="⟐",
        thinking_label="[dim bright_magenta]⚡ Procesando...[/]",
        spinner_label="Procesando",
        pt_style={
            "": "#00ff9f",
            "prompt": "#ff00ff bold",
            "prompt.dots": "#555555",
            "completion-menu": "bg:#1a002e #00ff9f",
            "completion-menu.completion.current": "bg:#ff00ff #000000",
            "auto-suggestion": "#444444 italic",
        },
    ),
    "minimal": CLITheme(
        name="minimal",
        label="Minimal",
        description="Clean & quiet — no decorations, maximum readability",
        theme={
            "realm": "white",
            "frost": "blue",
            "grove": "green",
            "bark": "grey70",
            "rune": "white",
            "error": "red",
            "success": "green",
            "warning": "yellow",
            "info": "blue",
            "tool.name": "bold white",
            "tool.arg": "dim white",
            "tool.result": "green",
            "thinking": "dim italic",
            "usage": "dim",
            "model": "bold",
            "status.ok": "green",
            "status.fail": "red",
            "status.warn": "yellow",
            "turn": "dim",
            "duration": "dim italic",
        },
        banner=_MINIMAL_BANNER,
        banner_title="[bold]yggdrasil[/]",
        banner_subtitle="[dim]cli[/]",
        border_style="white",
        rule_chars="─",
        prompt_prefix="›",
        thinking_label="[dim]Thinking...[/]",
        spinner_label="Thinking",
        pt_style={
            "": "#cccccc",
            "prompt": "#ffffff",
            "prompt.dots": "#666666",
            "completion-menu": "bg:#222222 #cccccc",
            "completion-menu.completion.current": "bg:#444444 #ffffff",
            "auto-suggestion": "#555555 italic",
        },
    ),
}

# ── Active theme management ────────────────────────────────────────

_active_theme_name: str = "norse"


def get_theme() -> CLITheme:
    """Return the currently active CLI theme."""
    return THEMES.get(_active_theme_name, THEMES["norse"])


def set_theme(name: str) -> CLITheme:
    """Switch the active theme by name. Returns the new theme.

    Raises ``KeyError`` if the theme name is not found.
    """
    global _active_theme_name, console
    if name not in THEMES:
        raise KeyError(name)
    _active_theme_name = name
    theme_obj = THEMES[name]
    # Recreate the global Console with the new Rich Theme.
    console = Console(theme=Theme(theme_obj.theme))
    return theme_obj


def list_themes() -> list[CLITheme]:
    """Return all available themes in definition order."""
    return list(THEMES.values())


# ── Initialise console with default theme ──────────────────────────

YGGDRASIL_THEME = Theme(THEMES["norse"].theme)
console = Console(theme=YGGDRASIL_THEME)

# ── Timer ───────────────────────────────────────────────────────────


class Timer:
    """Simple context-manager timer for tracking response duration."""

    def __init__(self) -> None:
        self._start: float = 0.0
        self.elapsed: float = 0.0

    def __enter__(self) -> Timer:
        self._start = time.perf_counter()
        return self

    def __exit__(self, *args: object) -> None:
        self.elapsed = time.perf_counter() - self._start

    @property
    def human(self) -> str:
        """Return human-readable duration."""
        if self.elapsed < 1:
            return f"{self.elapsed * 1000:.0f}ms"
        if self.elapsed < 60:
            return f"{self.elapsed:.1f}s"
        mins, secs = divmod(int(self.elapsed), 60)
        return f"{mins}m {secs}s"


# ── Welcome banner ──────────────────────────────────────────────────

_WELCOME_TREE = r"""
           ᛭              ᛟ              ᛭
    ╔═══════════════════════════════════╗
    ║          YGGDRASIL  CLI          ║
    ║             v6.5                  ║
    ║     Where Ancient Meets Digital  ║
    ╚═══════════════════════════════════╝
               ┃      ┃      ┃
        ───────┸──────┸──────┸──────
          Asgard  Midgard  Muspelheim
"""


def render_welcome(
    model: str = "",
    provider: str = "",
    tools_count: int = 0,
    has_memory: bool = False,
) -> None:
    """Show the welcome banner using the active theme."""
    theme = get_theme()
    banner_text = Text()
    for line in theme.banner.strip().splitlines():
        banner_text.append(line + "\n", style=f"bold {theme.border_style}")

    console.print()
    console.print(
        Panel(
            banner_text,
            title=theme.banner_title,
            subtitle=theme.banner_subtitle,
            border_style=theme.border_style,
            expand=False,
            padding=(0, 2),
        )
    )

    # Session info line.
    info_parts: list[str] = []
    if model:
        info_parts.append(f"Modelo: [model]{model}[/]")
    if provider:
        info_parts.append(f"Proveedor: [model]{provider}[/]")
    if tools_count:
        info_parts.append(f"Herramientas: {tools_count}")
    mem_icon = "[status.ok]✓[/]" if has_memory else "[status.fail]✗[/]"
    info_parts.append(f"Memoria: {mem_icon}")

    console.print(f"[dim]{'  ·  '.join(info_parts)}[/]")
    console.print("[dim]Escribe [bold cyan]/help[/] para ver los comandos disponibles.[/]")
    console.print()


# ── Turn separators ─────────────────────────────────────────────────


def render_turn_start(turn: int) -> None:
    """Show a visual separator at the start of a new turn."""
    theme = get_theme()
    console.print()
    console.print(
        Rule(f"[turn]Turno {turn}[/]", style=theme.border_style, characters=theme.rule_chars)
    )
    console.print()


def render_user_separator(text: str) -> None:
    """Show a labeled separator for user input."""
    # Truncate long user messages for the label.
    label = text[:60] + "…" if len(text) > 60 else text
    label = label.replace("\n", " ")
    console.print()
    console.print(Rule(f"[dim]▸ Tú[/]  [turn]{label}[/]", style="dim", characters="·"))
    console.print()


def render_assistant_separator() -> None:
    """Show a labeled separator before the assistant's response."""
    theme = get_theme()
    console.print(Rule("[dim]◂ Lilith[/]", style=theme.border_style, characters=theme.rule_chars))
    console.print()


def render_turn_end(duration: float, usage: dict[str, int] | None = None) -> None:
    """Show turn summary: duration + token usage."""
    parts: list[str] = []
    if duration > 0:
        if duration < 1:
            parts.append(f"[duration]{duration * 1000:.0f}ms[/]")
        elif duration < 60:
            parts.append(f"[duration]{duration:.1f}s[/]")
        else:
            mins, secs = divmod(int(duration), 60)
            parts.append(f"[duration]{mins}m {secs}s[/]")

    if usage and any(v > 0 for v in usage.values()):
        prompt = usage.get("prompt_tokens", 0)
        completion = usage.get("completion_tokens", 0)
        total = usage.get("total_tokens", 0)
        parts.append(f"[usage]{prompt}↑ {completion}↓ {total}Σ[/]")

    if parts:
        console.print(f"[dim]{'  ·  '.join(parts)}[/]")


# ── Markdown ────────────────────────────────────────────────────────


def render_markdown(text: str) -> None:
    """Render *text* as Markdown to the terminal."""
    console.print(Markdown(text))


# ── Error ───────────────────────────────────────────────────────────


def render_error(text: str) -> None:
    """Show an error message in bold red."""
    console.print(f"[error]✗ {text}[/]")


# ── Thinking / reasoning ────────────────────────────────────────────


def render_thinking(text: str) -> None:
    """Show a thinking / reasoning panel using the active theme."""
    theme = get_theme()
    # Truncate very long thinking blocks.
    display = text if len(text) <= 1000 else text[:1000] + "…"
    console.print(
        Panel(
            Text(display, style="thinking"),
            title=theme.thinking_label,
            border_style=theme.border_style,
            expand=False,
            padding=(0, 1),
        )
    )


# ── Tool call cards ─────────────────────────────────────────────────


def render_tool_call(name: str, args: dict[str, Any], result: str | None = None) -> None:
    """Show a tool execution card with name, args, and optional result."""
    # Build the header.
    header = Text()
    header.append("⟡ ", style="bold cyan")
    header.append(name, style="tool.name")

    # Args block.
    args_lines: list[str] = []
    for k, v in args.items():
        v_display = v[:120] + "…" if isinstance(v, str) and len(v) > 120 else v
        args_lines.append(f"  {k}: {v_display!r}")
    args_text = "\n".join(args_lines) if args_lines else "  (sin argumentos)"

    body_parts: list[Any] = []
    if args_lines:
        body_parts.append(Syntax(args_text, "python", theme="monokai", line_numbers=False))

    if result is not None:
        # Truncate overly long results.
        display_result = result if len(result) <= 500 else result[:500] + "…"
        body_parts.append(Text())
        body_parts.append(Text("↳ Resultado:", style="tool.result"))
        body_parts.append(Text(display_result))

    renderable = Group(*body_parts) if body_parts else Text(args_text, style="tool.arg")
    console.print(
        Panel(renderable, title=header, border_style="cyan", expand=False, padding=(0, 1))
    )


# ── Status panel ─────────────────────────────────────────────────────


def render_status(status_dict: dict[str, Any]) -> None:
    """Show a status panel with realm health, model info, etc."""
    theme = get_theme()
    table = Table(
        show_header=True,
        header_style=f"bold {theme.border_style}",
        border_style=theme.border_style,
        expand=False,
    )
    table.add_column("Reino / Propiedad", style="realm", min_width=20)
    table.add_column("Estado", min_width=16)

    for key, value in status_dict.items():
        if isinstance(value, bool):
            status_str = "[status.ok]✓ ACTIVO[/]" if value else "[status.fail]✗ INACTIVO[/]"
            table.add_row(key, status_str)
        elif isinstance(value, dict):
            sub = ", ".join(f"{k}={v}" for k, v in value.items())
            table.add_row(key, sub)
        else:
            table.add_row(key, str(value))

    console.print(
        Panel(
            table,
            title="[bold realm]⚔ Status Report ⚔[/]",
            border_style=theme.border_style,
            expand=False,
        )
    )


# ── Token usage ─────────────────────────────────────────────────────


def render_token_usage(usage: dict[str, int]) -> None:
    """Show token usage in dim text after a response."""
    prompt = usage.get("prompt_tokens", 0)
    completion = usage.get("completion_tokens", 0)
    total = usage.get("total_tokens", 0)
    console.print(
        f"[usage]Tokens — prompt: {prompt} · completion: {completion} · total: {total}[/]"
    )


# ── Streaming context manager ────────────────────────────────────────


@contextmanager
def render_streaming() -> Generator[dict[str, Any], None, None]:
    """Context manager that provides a live-updating Rich panel for
    streaming LLM output.

    Usage::

        with render_streaming() as state:
            for chunk in provider.stream(messages):
                state["text"] += chunk["content"]
                state["live"].update(...)

    The returned dict has keys:
      ``text`` — accumulated text so far,
      ``live``  — the Rich ``Live`` instance (already started).
    """
    state: dict[str, Any] = {"text": "", "usage": {}}

    console.print()  # blank line before streaming output
    with Live(console=console, refresh_per_second=12, vertical_overflow="visible") as live:
        state["live"] = live
        try:
            yield state
        finally:
            # Final render.
            if state["text"]:
                console.print()


# ── Thinking spinner (pre-stream) ──────────────────────────────────


def make_thinking_spinner() -> dict[str, Any]:
    """Create a Rich ``Status`` context manager for the pre-stream spinning
    indicator.  Themed according to the active CLITheme.
    """
    import threading

    from rich.status import Status

    theme = get_theme()
    prefix = theme.prompt_prefix

    label = Text()
    label.append(f"{prefix} ", style=f"bold {theme.border_style}")
    label.append(theme.spinner_label, style="italic cyan")
    label.append("…", style="dim")

    status = Status(
        label,
        spinner="dots",
        console=console,
        speed=0.8,
    )

    stop_event = threading.Event()

    def stop() -> None:
        """Signal the spinner to stop."""
        stop_event.set()

    def set_label(new_text: str) -> None:
        """Update the spinner label text."""
        label = Text()
        label.append(f"{prefix} ", style=f"bold {theme.border_style}")
        label.append(new_text, style="italic cyan")
        label.append("…", style="dim")
        status.update(label)

    return {
        "status": status,
        "stop": stop,
        "set_label": set_label,
    }
