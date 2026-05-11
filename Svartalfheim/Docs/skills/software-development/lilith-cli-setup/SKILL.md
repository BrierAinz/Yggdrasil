---
name: lilith-cli-setup
description: >
  Setup and configuration of the Yggdrasil CLI agent (lilith-cli v6.1+).
  Covers installation via uv, config.yaml with Pydantic validation, LLM provider setup
  (httpx-based for OpenAI-compatible endpoints), REPL usage with Hermes-inspired QoL
  features (reasoning panels, /redo, /copy, /system, /history, auto-save, Norse Rich
  theme), slash commands, and troubleshooting. Evolved from Hermes-Lilith standalone
  CLI into a unified agent with streaming, tool calling, and Cyclopts v4 CLI framework.
trigger: >
  When setting up, configuring, or troubleshooting the Yggdrasil CLI (lilith-cli),
  the `yggdrasil` command, config.yaml, LLM providers, REPL, or slash commands.
  Also when connecting to OpenCode/GLM-5.1 or any OpenAI-compatible API endpoint.
tags: [yggdrasil, lilith-cli, cyclopts, repl, agent, config, opencode, httpx]
version: 6.5.0
---

# Yggdrasil CLI Setup (lilith-cli v3.0.0+)

## Overview

The Yggdrasil CLI (`yggdrasil` command) is the unified agent REPL for the Yggdrasil ecosystem. It evolved from the basic lilith-cli v2.1.0 (argparse + basic chat) into a full AI agent with streaming, tool calling, Rich rendering, and Cyclopts v4 subcommands.

**Package:** `Asgard/lilith-cli/` in the Yggdrasil monorepo
**Entry points:** `yggdrasil` (primary), `lilith` (alias), `yggdrasil-tui` (dashboard)
**Config:** `~/.yggdrasil/config.yaml`

## Installation

```bash
# From Yggdrasil root
cd /mnt/d/Proyectos/Yggdrasil
uv sync --package lilith-cli

# Verify
uv run yggdrasil --version  # → 3.0.0
uv run yggdrasil --help
```

Persistent install (global command):
```bash
uv pip install -e ./Asgard/lilith-cli
```

## Configuration

### Config File: ~/.yggdrasil/config.yaml

Auto-generated on first run with sensible defaults. Edit directly or use `/config` in REPL.

```yaml
provider: openai          # openai, anthropic, ollama, local
model: gpt-4o-mini        # default model
api_key: ${OPENAI_API_KEY}  # env var interpolation
base_url: null             # custom endpoint
system_prompt: >
  You are Lilith, an AI agent of the Yggdrasil ecosystem...
temperature: 0.7
max_tokens: 4096
tools:
  filesystem: true
  coding: true
  web_search: true
  browser: true
  system: true
memory:
  enabled: true
  db_path: ~/.yggdrasil/memory.db
history:
  max_turns: 50
  save: true
# Provider overrides (uncomment to activate)
# providers:
#   anthropic:
#     api_key: ${ANTHROPIC_API_KEY}
#     model: claude-sonnet-4-20250514
#   ollama:
#     base_url: http://localhost:11434
#     model: llama3
#   local:
#     base_url: http://localhost:1234/v1
#     model: local-model
```

### Config Features
- **`${ENV_VAR}` interpolation** — secrets read from environment, never hardcoded
- **Pydantic v2 validation** — type checking, defaults, error messages
- **`yggdrasil config`** — display current config
- **`yggdrasil config --reset`** — regenerate with defaults

### Required Environment Variables

```bash
# At least one API key is required
export OPENAI_API_KEY="sk-..."
# Optional providers
export ANTHROPIC_API_KEY="sk-ant-..."
```

### Local LLM (LM Studio / Ollama)

No API key needed. Set in config:
```yaml
provider: local
base_url: http://localhost:1234/v1
model: local-model
```

Or via CLI: `yggdrasil chat --local --model my-model`

## CLI Commands

```
yggdrasil              # Launch interactive REPL (default)
yggdrasil "prompt"    # One-shot mode (print response and exit)
yggdrasil chat         # Explicit REPL mode
yggdrasil status       # Realm ecosystem health status
yggdrasil launch       # Service launcher menu
yggdrasil config       # Show current config
yggdrasil config --reset  # Regenerate default config
yggdrasil --version    # Show version
yggdrasil --help       # Show help
```

### Chat Flags
```
--model, -m MODEL      Override model for this session
--provider, -p PROVIDER  Override provider
--local                 Use local LM Studio (shortcut)
--no-tools              Disable tool calling
--verbose               Verbose logging
--config, -c PATH       Use alternate config file
```

## REPL Usage

The REPL uses prompt_toolkit with:
- **History** — persisted at `~/.yggdrasil/history`
- **Autocomplete** — slash commands + model/provider names
- **Ctrl+C** — cancel current generation (not exit)
- **Ctrl+D** — exit

### Slash Commands

| Command | Aliases | Description |
|---------|---------|-------------|
| /help | /h, /? | Show available commands |
| /tools | | List available tools |
| /model | | Show or switch model |
| /provider | | Show or switch provider |
| /memory | /m | Search memory |
| /clear | /cls | Clear conversation |
| /status | | Realm ecosystem status |
| /config | | Show current config |
| /quit | /exit, /q | Exit |
| /save | | Save conversation to file (auto-saves on exit) |
| /redo | /retry | Re-send last user message to model |
| /copy | /cp | Copy last response to clipboard (supports /copy N) |
| /system | | Show or modify system prompt |
| /history | /hist | Show conversation history (supports /history N) |
| /compact | /summarize | Compress history by summarizing older messages (supports /compact N) |
| /resume | /load | Resume a saved conversation (lists recent, /resume <N> or /resume <search>) |
| /file | /f | Attach local file to conversation context (preview + inject) |
| /export | /exp | Export conversation to Markdown or JSON (~/.yggdrasil/exports/) |
| /theme | /themes | Switch or list visual themes (norse, cyberpunk, minimal) |

## Architecture (7 Modules)

See `yggdrasil-ecosystem` reference `cli-evolution-v6.md` for full details.

| Module | Purpose |
|--------|---------|
| `main.py` | Cyclopts v4 entry point, subcommands |
| `config.py` | Pydantic v2 YAML config with env var interpolation |
| `providers.py` | httpx-based provider, streaming, tool calls, retry, **reasoning_content** events |
| `agent.py` | AgentSession: message loop, tool resolution, **`_last_user_message`** for /redo |
| `repl.py` | prompt_toolkit REPL, Norse PtStyle, **Markdown lexer**, multiline Alt+Enter + Ctrl+O, streaming with reasoning panels, turn counter, auto-save |
| `render.py` | Rich Norse theme: **ThemeManager (Norse/Cyberpunk/Minimal themes)**, welcome banner, turn separators, thinking panel, tool cards, Markdown |
| `commands.py` | 19 slash commands: original 10 + /redo, /copy, /system, /history, /compact, /resume, /theme, /file, /export |

## QoL Features (Hermes-Inspired)

### Visual Rendering (render.py)
- **Norse theme** — `YGGDRASIL_THEME` dict with realm/frost/rune/grove/bark colors
- **Welcome banner** — ASCII tree art with model/provider/tools/memory info
- **Turn separators** — Rich `Rule` with turn number per message
- **Role separators** — `render_user_separator(text)` shows `▸ Tú {text}` with dotted line, `render_assistant_separator()` shows `◂ Lilith` with themed solid line. These appear at each turn boundary so the user can visually distinguish their input from the model's output. **Pitfall:** The assistant separator must show the agent's NAME (e.g. "Lilith"), NOT the theme label (e.g. "Norse") — the theme is visual context, not identity.
- **Thinking panel** — Dim magenta panel for GLM-5.1 `reasoning_content`
- **Tool call cards** — Bordered card with name/args
- **Markdown rendering** — Final response re-rendered as Rich Markdown
- **Token usage** — `prompt↑ completion↓ totalΣ` format with timer
- **Token bar in toolbar** — `_live_tokens` dict in repl.py updates bottom toolbar per-turn: shows `Tokens: N↑ N↓ NΣ Turn: N`
- **Dynamic style** — `DynamicStyle` wraps `PtStyle.from_dict(get_theme().pt_style)` so `/theme <name>` takes effect immediately without REPL restart

### Streaming REPL (repl.py)
- **Reasoning content streaming** — `reasoning` events rendered as live text, then collapsed into thinking panel
- **Silent accumulation** — Tokens accumulate in memory during streaming, rendered as Markdown once at stream end. Do NOT print raw chunks during streaming or text appears twice (raw + Markdown). A Rich `Status` spinner shows activity during accumulation. The `_assistant_sep_shown` flag ensures `render_assistant_separator()` fires exactly once at the first output token (reasoning, text, or tool_call), regardless of event type order.
- **Live Thinking Spinner** — Rich `Status` (dots spinner) shows "᛭ Pensando…" while waiting for first stream token, stops on first `reasoning`/`text`/`tool_call` event
- **Auto-save on exit** — Conversations saved to `~/.yggdrasil/conversations/conv_YYYYMMDD_HHMMSS.json`
- **/resume** (alias /load) — Lists saved conversations as a Rich table, restores selected conversation into session history by index or search
- **Enhanced prompt** — Norse-themed PtStyle colors, Markdown PygmentsLexer syntax highlighting, Alt+Enter/Escape+Enter for multi-line input, Ctrl+O toggle multiline mode, bottom toolbar showing mode + key hints
- **Turn counter** — Each message shows "Turno N" separator
- **Clipboard** — WSL `clip.exe`, xclip/xsel, pbcopy, OSC 52 fallback chain
- **Multi-line input** — Detects unclosed brackets/colons for continuation

### Slash Commands (commands.py)
- **/redo** (alias /retry) — Re-sends last user message, pops stale history entries
- **/copy** (alias /cp) — Copies last or Nth assistant response to clipboard; strips reasoning tags
- **/system** — Show current system prompt in a Rich Panel, or set new one via `/system <text>`
- **/history** (alias /hist) — Show last N messages; supports `/history 5` for last 5
- **/file** (alias /f) — Attach local file to conversation: `/file path/to/file.py [prompt]`. Shows Rich Panel preview (first 10 lines, line count, bytes), injects as markdown code block with language detection. Max 5 MB.
- **/export** (alias /exp) — Export conversation to `~/.yggdrasil/exports/`: `/export` (md default), `/export json`, `/export md myname`. Markdown has role headers + emoji icons; JSON has full metadata + messages.
- **/theme** (alias /themes) — List themes (`/theme`), switch (`/theme cyberpunk`), show current (`/theme current`). Persists to `config.yaml` `theme:` field. Three themes: norse (gold1/runes), cyberpunk (cyan/magenta/neon), minimal (white/grey, no decorations).

### Windows Launcher

To launch Yggdrasil from Windows (double-click or Windows Terminal):

1. Create `/home/brierainz/yggdrasil_launch.sh`:
```bash
#!/bin/bash
export PATH="$HOME/.local/bin:$PATH"
cd /mnt/d/Proyectos/Yggdrasil
uv run yggdrasil chat
```

2. Create `C:\Users\Game_\yggdrasil_terminal.bat`:
```bat
@echo off
title Yggdrasil CLI
wsl -d Ubuntu -e bash /home/brierainz/yggdrasil_launch.sh
```

3. Desktop shortcut (PowerShell):
```powershell
$ws = New-Object -ComObject WScript.Shell
$desktop = [Environment]::GetFolderPath('Desktop')
$sc = $ws.CreateShortcut("$desktop\Yggdrasil CLI.lnk")
$sc.TargetPath = 'C:\Users\Game_\yggdrasil_terminal.bat'
$sc.Save()
```

**Pitfall:** Windows Desktop may be at `C:\Users\Game_\OneDrive\Desktop` (not `%USERPROFILE%\Desktop`). Always use `[Environment]::GetFolderPath('Desktop')` in PowerShell to find it. Raw `cmd.exe /c "echo ... > Desktop.lnk"` does NOT work for shortcuts — use the WScript.Shell COM object.

**Pitfall:** Do NOT use `wt.exe -w yggdrasil new-tab wsl ...` with inline commands — shell escaping breaks (error 0x80070002). Use the `.bat` + `.sh` file pair approach above.

### Theme System (render.py)

Three built-in themes, switchable at runtime:

| Theme | Prefix | Colors | Style |
|-------|--------|--------|-------|
| norse | ᛭ | gold1/gold3 on grey11 | Dark-fantasy, rune borders |
| cyberpunk | ⟐ | cyan/magenta on grey11 | Neon, digital rain |
| minimal | › | white/grey70 | Clean, no decorations |

Implementation: `CLITheme` dataclass → `PtStyle.from_dict()` → `DynamicStyle(callable)` in prompt_toolkit. `_load_saved_theme()` reads `theme:` from config.yaml at REPL start. `set_theme()` writes `theme:` to config.yaml for persistence.

**Pitfall:** Rich custom theme colors (e.g. `rune`, `realm`, `frost`) do NOT work in `Table(header_style=)` or similar Rich formatting — use standard color names like `gold1`, `grey11`, `cyan`. Custom colors only work in `console.print()` with the `style=` parameter when the Rich `Theme` is registered on the console.

### providers.py Reasoning
- **Stream events** — `{"type": "reasoning", "content": chunk}` yielded for `reasoning_content` deltas
- **Normalised response** — `_normalise_response()` includes `reasoning_content` key in return dict
- This lets GLM-5.1's chain-of-thought display as a separate thinking panel

### agent.py /redo Support
- **`_last_user_message`** attribute — stored in both `process_message()` and `process_message_stream()`
- **`last_user_message`** property — exposes for /redo command
- **`compact_history()`** — replaces older messages with LLM-generated summary + keeps N recent turns
- **`generate_compact_summary()`** — asks the LLM to summarize the conversation for /compact

## Provider & API Configuration

### OpenCode / GLM-5.1 (Primary Provider)

The current primary provider is OpenCode with GLM-5.1. The config MUST use `provider: opencode` (not `openai`) when using the OpenCode endpoint, because the `providers:` block lookup is by provider name:

```yaml
provider: opencode
model: glm-5.1
base_url: https://opencode.ai/zen/go/v1
api_key: sk-...   # Direct key (preferred over ${ENV_VAR} if env var not set)
providers:
  opencode:
    api_key: sk-...
    base_url: https://opencode.ai/zen/go/v1
    model: glm-5.1
```

### How Provider Resolution Works

1. `_resolve_api_key()` checks `providers[<provider_name>].api_key` first, then falls back to top-level `api_key`
2. `_resolve_base_url()` checks `providers[<provider_name>].base_url` first, then falls back to top-level `base_url`
3. `_resolve_model()` returns the raw model ID (no prefix) — httpx sends it directly to the OpenAI-compatible endpoint

### Key Pitfall: `${ENV_VAR}` Without the Environment Variable

If you write `api_key: ${OPENAI_API_KEY}` in config.yaml but the env var is NOT set, the interpolation leaves the literal string `${OPENAI_API_KEY}` — which will cause 401 Auth errors. **Always set the env var OR hardcode the key directly.**

### How providers.py Works (v6.0)

`providers.py` uses **httpx directly** (not litellm) for all OpenAI-compatible endpoints. This avoids the litellm namespace clash issue and is faster/lighter. The provider:
- Creates an async httpx client with `Authorization: Bearer <key>` header
- Sends requests to `<base_url>/chat/completions`
- Supports streaming (SSE parsing) and non-streaming completions
- Supports OpenAI-format tool calling with stream accumulation
- Retries 3x with exponential backoff on transient errors
- Does NOT use litellm at all (removed due to import conflicts in workspace)

## Troubleshooting

See `references/v6-0-bugfixes.md` for detailed debugging transcripts of bugs found during development.

| Problem | Cause | Fix |
|---------|-------|-----|
| `yggdrasil: command not found` | Not installed globally | `cd /mnt/d/Proyectos/Yggdrasil && uv sync --package lilith-cli` then use `uv run yggdrasil` |
| Config errors on startup | Missing API key for provider | Set env var or add to config.yaml |
| `TypeError: Parameter()` | Cyclopts v4 syntax | Use `Parameter(name=["--flag", "-f"])` NOT `Parameter("--flag", "-f")` |
| `SyntaxError: var-positional argument cannot have default` | Cyclopts v4 `*args` with default | Use `args: tuple[str, ...] = ()` instead of `*args` |
| 401 Unauthorized from API | `${ENV_VAR}` literal in header | Set the env var OR hardcode the API key in config |
| Wrong provider used | `provider: openai` looks up `providers.openai` | Use `provider: opencode` for OpenCode endpoint |
| `module 'litellm' has no attribute 'acompletion'` | litellm namespace clash in workspace | v6.0 uses httpx directly — this should not happen. If it does, check providers.py imports. |
| No tool calls | `tools: false` in config or `--no-tools` flag | Set `tools: { filesystem: true, ... }` in config |
| Streaming duplicates output | GLM-5.1 sends `reasoning_content` in SSE delta chunks | providers.py `stream()` must skip deltas with `reasoning_content` and no `content`/`tool_calls`. Also filter `reasoning_content` in `_normalise_response()` for non-streaming path |
| `TypeError: PromptSession.__init__() got unexpected keyword argument 'enable_open_brackets'` | prompt_toolkit doesn't have this parameter | Remove `enable_open_brackets=True` from `PromptSession()` constructor |
| `AttributeError: 'coroutine' object has no attribute 'strip'` | `prompt_async()` is already an async coroutine | Do NOT wrap with `asyncio.to_thread()` — just `await prompt_session.prompt_async(...)` directly |
| `/help` crashes with `NameError: name 'c' is not defined` | Lambda variable `c` used outside scope in f-string | Ensure loop variable matches: `for cmd in ...: ... cmd.aliases` (not `c.aliases`) |
| `_resolve_model()` ignores profile override | Method only returned `config.model` | Fixed: checks `providers[<name>].model` first, then falls back to `config.model` |
| `httpx.ConnectError` from REPL | REPL ran `prompt_async` with `to_thread` | Same fix as `AttributeError: 'coroutine'` — await `prompt_async` directly |
| Streaming not working | Provider doesn't support streaming | Use a streaming-capable provider (OpenAI, Anthropic, local) |
| Memory search fails | SQLite DB not created | Run once to auto-create `~/.yggdrasil/memory.db` |
| Import errors | Workspace not synced | `uv sync --package lilith-cli` from monorepo root |
| Rich custom colors fail in Table header | `Table(header_style="bold rune")` silently falls back | Use standard Rich color names (`gold1`, `grey11`, `cyan`) in `Table`, `Panel`, etc. Custom `Theme` colors only work via `console.print(style=...)` |
| Windows Terminal launch fails | `wt.exe` inline command escaping breaks (error 0x80070002) | Use `.bat` + `.sh` file pair, not inline `wsl -e bash -ic "..."` |
| Desktop shortcut not created | Desktop folder at `OneDrive\Desktop`, not `%USERPROFILE%\Desktop` | Use `[Environment]::GetFolderPath('Desktop')` in PowerShell |
| `/file` says "No hay mensajes" | Called on empty history | Normal — `/file` injects a user message but `/export` needs at least 1 message |
| Streaming duplicates response text | `console.print(Text(chunk))` during streaming + `render_markdown(accumulated)` at the end prints everything twice | Remove raw streaming `console.print()` — only accumulate chunks silently, render as Markdown once at stream end. Use `_assistant_sep_shown` flag so separator fires exactly once at first token |
| Assistant separator shows theme name instead of agent name | `render_assistant_separator()` used `theme.label` (e.g. "Norse") | Use the agent's name string (e.g. "Lilith"), not `theme.label`. The theme is visual style, not identity |
| Ruff pre-commit fails | TC001/TC003 (move imports to TYPE_CHECKING), RUF005 (use `[*a, *b]` not `[a] + b`), PLW2901 (loop var overwritten), F841 (unused var), F401 (unused import) | Move type-only imports under `if TYPE_CHECKING:`, unpack iterables, rename loop vars (`raw_line`), remove unused vars/imports. For RUF006 (store `create_task` ref), add `# noqa: RUF006` — the ref is intentionally discarded in cleanup. |

## Distinction from Hermes-Lilith

There are TWO Lilith CLIs:

1. **Yggdrasil CLI (`lilith-cli` v3.0.0)** — the new agent REPL at `Asgard/lilith-cli/`. Entry point: `yggdrasil`. Uses Cyclopts v4, Rich, prompt_toolkit, **httpx** (not litellm — namespace clash in workspace). This is the evolving agent CLI with streaming, tool calling, and a dark-fantasy Rich theme.

2. **Hermes-Lilith (`Lilith/main.py`)** — the standalone dark-fantasy CLI at `Asgard/Hermes-Lilith/`. Entry point: `lilith` (via install.bat). Has Swarm, MCP server, Dashboard, Enhanced Memory v2. This is the full-featured monolith.

The Yggdrasil CLI is modular (separate packages for core/tools/memory/orchestrator), while Hermes-Lilith is monolithic. They share the same LLM providers and memory format but have different feature sets.

### v6.0 CLI Architecture (Current)

The `lilith-cli` package was rewritten in v6.0 from a basic argparse chatbot to a full agent REPL modeled after Hermes. Key changes:
- **providers.py** uses httpx directly for OpenAI-compatible endpoints (not litellm) — avoids the litellm import clash in the workspace
- **Streaming SSE parsing** built into providers.py with tool-call accumulation
- **Config resolution** uses per-provider profile overrides: `_resolve_api_key()`, `_resolve_base_url()`, AND `_resolve_model()` all check `providers[<name>]` first, then fall back to top-level config
- **OpenCode/GLM-5.1** is currently the primary provider — must use `provider: opencode` to match the `providers.opencode` profile