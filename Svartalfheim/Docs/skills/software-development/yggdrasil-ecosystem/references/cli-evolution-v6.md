# Yggdrasil CLI v6.0 Architecture

## Overview

In May 2026, lilith-cli (Asgard/lilith-cli/) was completely rewritten from a basic chat client (796 lines, argparse) into a full AI agent REPL similar to Hermes CLI. Version jumped from 2.1.0 to 3.0.0. The `yggdrasil` entry point now unifies the old `yggdrasil_cli.py` sysadmin CLI and the chat agent into one.

## Package Structure

```
Asgard/lilith-cli/lilith_cli/
├── __init__.py          # Exports YggdrasilConfig, load_config, save_config
├── config.py            # YAML config (Pydantic), ~/.yggdrasil/config.yaml
├── providers.py         # Unified LLM provider (LiteLLM + Local), streaming, tool calls
├── render.py            # Rich terminal renderer (Norse dark-fantasy theme)
├── commands.py          # Slash command registry: /help /tools /model /provider /memory /clear /status /config /quit /save
├── agent.py             # AgentSession orchestrator: message loop, tool-call resolution, streaming
├── repl.py              # Interactive REPL (prompt_toolkit), streaming output, history
├── main.py              # Cyclopts v4 entry point: yggdrasil, yggdrasil chat, yggdrasil status, etc.
├── client.py            # Legacy HTTP client (kept for API mode)
└── tui/                 # Textual TUI dashboard (preserved)
    ├── app.py
    ├── agent_view.py
    ├── log_view.py
    └── realm_view.py
```

## Entry Points

pyproject.toml defines three scripts:
- `yggdrasil` → `lilith_cli.main:main` (primary)
- `lilith` → `lilith_cli.main:main` (alias)
- `yggdrasil-tui` → `lilith_cli.tui.app:main` (dashboard)

## CLI Commands

```
yggdrasil              # Launch interactive REPL (default)
yggdrasil "prompt"     # One-shot mode
yggdrasil chat          # Explicit REPL mode
yggdrasil status        # Realm health status (from yggdrasil_cli.py)
yggdrasil launch        # Launch services menu (from yggdrasil_cli.py)
yggdrasil config        # Show/edit config
yggdrasil config --reset # Regenerate default config
```

Flags: `--model`, `--provider`, `--local`, `--no-tools`, `--verbose`, `--config`, `--version`

## Key Components

### config.py — YggdrasilConfig (Pydantic v2)
- Models: YggdrasilConfig, ToolsConfig, MemoryConfig, HistoryConfig, ProviderProfile
- `${ENV_VAR}` interpolation for secrets (API keys)
- Auto-creates `~/.yggdrasil/config.yaml` on first run
- Per-provider profile overrides in `providers:` dict

### providers.py — LLMProviderWrapper
- Delegates to lilith_core.providers.LiteLLMProvider when available, falls back to direct litellm
- Streaming via async generators (yielding dicts with content/model/finish_reason)
- Tool calling: OpenAI function-calling format, delta accumulation for streaming
- Exponential backoff: 3 retries, base delay 1.0s
- ToolCall and ToolResult dataclasses

### agent.py — AgentSession
- Holds: config, provider, tools registry, memory store (SQLite via lilith_memory), conversation history
- `process_message(text)` — full loop: LLM → tool calls → results → repeat up to 10 iterations
- `process_message_stream(text)` — async generator yielding events: text, tool_call, tool_result, done
- Tool integration: loads from lilith_tools.ToolRegistry (decorator-based registration)
- Memory: lazy-init from lilith_memory.MemoryStore
- Token usage tracking per session
- Callback hook `_on_tool_call` for REPL to display tool execution in real-time

### repl.py — Interactive REPL
- Built on prompt_toolkit: FileHistory, WordCompleter, AutoSuggestFromHistory
- Prompt format: `[bold gold1]᛭ {model}[/][dim]:[/] `
- Slash command autocomplete (12 commands + aliases)
- Streaming output with Rich rendering
- Ctrl+C cancels current generation (not exit), Ctrl+D exits
- History persisted at `~/.yggdrasil/history`

### render.py — Rich Renderer
- Custom YGGDRASIL_THEME: gold1 for realms, cyan for tools, red for errors
- render_welcome() — Norse runic ASCII art banner
- render_markdown() — Rich Markdown with syntax highlighting
- render_tool_call() — Panel with tool name, args, result
- render_status() — Table of realm health
- render_error() — Red error display

### commands.py — 10 Slash Commands
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
| /save | | Save conversation to file |

## Dependencies (pyproject.toml v3.0.0)

- lilith-core, lilith-memory, lilith-orchestrator, lilith-tools (workspace)
- textual>=0.50.0 (TUI)
- cyclopts>=2.0.0 (CLI framework)
- rich>=13.0.0 (terminal rendering)
- prompt-toolkit>=3.0 (REPL)
- pydantic>=2.0 (config validation)
- pyyaml>=6.0 (config file)
- litellm>=1.0.0 (LLM provider)

## Integration with yggdrasil_cli.py

The root `yggdrasil_cli.py` (1159 lines) provides sysadmin functions (launch, status, clean, backup, etc.). The new CLI imports these via lazy import:

```python
def _lazy_import_yggdrasil_cli():
    root = str(Path(__file__).resolve().parents[3])
    if root not in sys.path:
        sys.path.insert(0, root)
    import yggdrasil_cli
    return yggdrasil_cli
```

This is used by `/status` and `yggdrasil status` commands to reuse existing realm health logic.

## Cyclopts v4 Syntax Note

Cyclopts v4 (4.11.2+) changed the Parameter syntax. The old style fails:

```python
# ❌ BROKEN — causes TypeError at import time
def chat(
    model: Annotated[Optional[str], Parameter("--model", "-m", help="Override model")] = None,
)

# ✅ CORRECT — v4 requires list for short/long flags
def chat(
    model: Annotated[Optional[str], Parameter(name=["--model", "-m"], help="Override model")] = None,
)
```

Key differences:
- `name` parameter takes a **list** for combined short+long flags: `name=["--model", "-m"]`
- Positional Parameter arguments no longer accepted — all config via keyword args
- `show=False` for hidden params: `Parameter(show=False)`

## Default Config (~/.yggdrasil/config.yaml)

```yaml
provider: openai
model: gpt-4o-mini
api_key: ${OPENAI_API_KEY}
base_url: null
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
# providers:  # Per-provider overrides
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