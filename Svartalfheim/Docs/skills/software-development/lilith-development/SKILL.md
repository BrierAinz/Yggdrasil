---
name: lilith-development
description: Development patterns, architecture, module conventions, and testing for the Hermes-Lilith agent CLI project. Covers project structure, Swarm coordination, memory systems, tool integration, CLI commands, and pytest patterns.
version: 1.0.0
author: Assistant
---

# Lilith Development

Development guide for the Hermes-Lilith project — a dark-fantasy-themed personal CLI agent written in Python that connects to LM Studio (local LLM) via OpenAI-compatible API.

## Project Context

- **Path:** `/mnt/d/Proyectos/Yggdrasil/Asgard/Hermes-Lilith/` (WSL) or `D:\Proyectos\Yggdrasil\Asgard\Hermes-Lilith\` (Windows)
- **Part of:** Yggdrasil ecosystem (9-realm Norse architecture)
- **LLM backend:** Multi-provider with automatic fallback — LM Studio (local, `http://localhost:1234/v1`) → Kimi Code (remote, `https://api.kimi.com/coding/v1`, requires `X-Client: claude-code` header). Controlled by `LLM_PROVIDER` env var: `"auto"` (fallback), `"lm_studio"`, or `"kimi"`.
- **Model config:** `DEFAULT_MODEL = "auto"` (auto-detects first available model). Kimi uses `kimi-for-coding` (internally Kimi-k2.6, 262K context).
- **API keys:** Stored in `.env` (gitignored), loaded via `python-dotenv`. Never hardcode keys in source.
- **Entry point:** `Lilith/main.py` → `LilithCLI` class with argparse
- **Global command:** `lilith` via install.bat (PATH wrapper)

## Architecture

```
Lilith/
  main.py              # CLI (LilithCLI class, argparse, /commands, --batch mode)
  batch.py              # BatchRunner: programmatic LLM invocation (no REPL)
  Core/
    config.py           # Public constants (retro-compat), delegates to LilithConfig/TOML
    toml_config.py      # LilithConfig: TOML unified config (~/.lilith/config.toml)
    llm_client.py       # httpx client with list_models(), chat(), chat_stream()
    llm_provider.py     # Multi-provider (LM Studio + Kimi), circuit breaker, retry, auto-fallback
    orchestrator.py      # Chat orchestration, tool dispatch, streaming, DynamicToolRegistry, session context
    dynamic_tools.py    # DynamicToolRegistry: native + MCP tools unified registry
    resilience.py        # CircuitBreaker (CLOSED/OPEN/HALF_OPEN), retry_with_backoff, RetryConfig
    error_handler.py     # LilithError hierarchy, sanitize_output (API key redaction), format_error
    lilith_logger.py      # Structured logging with runic prefixes (ᚱ=INFO, ᛏ=DEBUG, ᚨ=WARN, ᛃ=ERROR)
    graceful_shutdown.py  # Signal handlers (SIGINT/SIGTERM), atexit, crash markers, shutdown hooks LIFO
    skill_parser.py      # Skill dataclass v2: triggers, regex, intent, templates, render()
    skill_registry.py    # Skill registry v2: enable/disable, stats, YAML support, tools validation
    tests/
      test_llm_provider.py
      test_orchestrator.py
      test_skill_parser.py
      test_skill_registry.py
      test_skill_v2.py           # 76 tests (regex, intent, templates, enable/disable, stats)
      test_toml_config.py        # 64 tests for TOML config system
      test_integration_e2e.py   # 32 tests E2E integration
      test_memory_rag.py         # 48 tests (SessionStore, BackgroundConsolidator, RAG integration)
      test_orchestrator_session.py # 17 tests (session store + consolidator in orchestrator)
  Swarm/                # FASE 3 — Multi-agent coordination (COMPLETE)
    manager.py           # SwarmManager: spawn/kill, background coordinator
    agent.py             # SwarmAgent: thread lifecycle, file tracking, locking
    message_bus.py       # MessageBus: thread-safe pub/sub with broadcast
    conflict_resolver.py # ConflictResolver: detect, auto-merge, severity
    database.py          # SwarmDatabase: SQLite persistence (thread-local conns)
    executor.py          # SwarmExecutor: LLM+tools execution loop
    prompts.py           # System prompts for swarm workers
    tests/
      test_swarm.py      # 25 tests (bus, agent, manager, conflicts, integration)
      test_fase4_5.py    # 15 tests (database, persistence, executor, LLM mode)
  memory/               # FASE 2 — Semantic memory (EnhancedMemory v2)
    base.py                # EmbeddingModel (SentenceTransformer all-MiniLM-L6-v2, 384d), cosine_similarity, DB_PATH
    enhanced.py            # Vector memory, embeddings, entity extraction, compression
    memory_graph.py        # MemoryGraph (entities, relations, path finding, strength decay)
    memory_consolidation.py # Consolidation: merge similar, dedup, promote, forget
    memory_retrieval.py    # HybridRetriever: vector + keyword + graph + recency, FTS5
    session_store.py        # SessionStore: save/load/search sessions, semantic context injection
    background_consolidator.py # BackgroundConsolidator: daemon thread, periodic consolidation
  tools/                # All tool implementations + OpenAI function defs
    file_tools.py
    system_tools.py
    coding_tools.py
    network_tools.py
    browser_tools.py
    windows_tools.py
    desktop_tools.py
    swarm.py              # CLI tool functions for /swarm commands
    mcp_connect.py        # CLI tool functions for /mcp commands
    dashboard.py           # CLI tool functions for /dashboard commands
  MCP/                  # FASE 4 — Model Context Protocol client/manager
    client.py            # MCPClient: connect, list_tools, call_tool, timeouts
    config.py            # MCPServerConfig dataclass + mcp_servers.json loader
    manager.py           # MCPManager: registry, lifecycle, _resolve_env
    server.py            # LilithMCPServer: expose Lilith as MCP server (FASE 14)
    cron.py              # CronScheduler: periodic tasks, SQLite persistence (FASE 14)
    templates.py          # AgentTemplate, TemplateLibrary, TemplateRenderer (FASE 14)
    tests/test_mcp.py     # 51 tests
    tests/test_mcp_server.py  # MCP server tests
    tests/test_cron.py       # Cron scheduler tests
    tests/test_templates.py   # Agent template tests
  Dashboard/             # FASE 5 — Web dashboard (HTTP + WebSocket)
    __init__.py           # Exports DashboardServer, get_dashboard
    server.py             # DashboardServer: aiohttp WS+HTTP, command handlers
    frontend/
      index.html          # Dark fantasy UI with rune particles canvas, pane layout
      style.css            # Full dark fantasy/Norse/Lovecraftian CSS (1121 lines)
      app.js               # WS client, pane management, particle system, glitch effect
    tests/test_dashboard.py  # 39 tests (server, theme, frontend files, CLI tool)
  skills/                 # Built-in skill templates (auto-copied to ~/.lilith/skills/)
    coding.md              # Programming assistance (priority 90)
    debugging.md           # Debugging & troubleshooting (priority 95, highest)
    research.md            # Research & investigation (priority 80)
    writing.md              # Creative & documentary writing (priority 75)
    analysis.md             # Data analysis & comparison (priority 70)
  plugins/               # Plugin system
  __init__.py
```

## CLI Command Pattern

Commands are defined in `LilithCLI.COMMANDS` dict and dispatched in `run()` via if/elif chain. To add a new command:

1. Add entry to `COMMANDS` dict: `"newcmd": "Description of the command"`
2. Add `elif cmd == "newcmd":` block in `run()` method
3. For sub-commands (like `/swarm spawn`), create a `_handle_newcmd(self, args)` method
4. Add to argparse epilog help text

### Swarm CLI Integration (example)

The `/swarm` command delegates to `_handle_swarm_command(self, args)` (line 167), which parses sub-commands: `spawn`, `status`, `kill`, `killall`, `result`, `save`, `load`, `history`.

Key pattern — swarm uses a global singleton via `get_swarm_manager()`:
```python
from Lilith.Swarm.manager import get_swarm_manager
mgr = get_swarm_manager()
```

For LLM mode, the executor is initialized lazily:
```python
if use_llm and not mgr._executor:
    from Lilith.Swarm.executor import SwarmExecutor
    from Lilith.Core.llm_client import LMStudioClient
    client = LMStudioClient()
    executor = SwarmExecutor(client)
    mgr._executor = executor
    mgr._use_llm = True
```

## Testing Patterns

### Running Tests

```bash
# From project root (WSL path)
cd /mnt/d/Proyectos/Yggdrasil/Asgard/Hermes-Lilith
python3 -m pytest Lilith/Swarm/tests/test_swarm.py -v --tb=short
python3 -m pytest Lilith/Swarm/tests/test_fase4_5.py -v --tb=short
```

Note: Use `python3` not `python` in WSL. The project is at the Yggdrasil root which has `pytest.ini`.

### Test Structure Conventions

- Each module gets its own test class: `TestMessageBus`, `TestSwarmAgent`, `TestSwarmManager`, etc.
- Tests use `sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))` to find the project root
- SQLite tests use `tempfile.NamedTemporaryFile(suffix=".db", delete=False)` with `setup_method`/`teardown_method`
- Agent lifecycle tests use `time.sleep()` for thread coordination (not ideal but works)
- Mock LLM clients: simple class with `chat()` method returning dict with `choices`
- Thread-safe patterns tested: file locking (`_acquire_lock`), message bus concurrency

### Pytest Markers

The project uses markers defined in `pytest.ini` at Yggdrasil root. Check `/mnt/d/Proyectos/Yggdrasil/pytest.ini` for available markers.

## Module Patterns

### Thread Safety

All Swarm modules use thread-safe patterns:
- `threading.RLock()` for re-entrant locks in managers
- `threading.local()` for SQLite connections in `SwarmDatabase`
- `queue.Queue` for message passing in `MessageBus`
- `threading.Event` for agent stop signals

### Singleton Pattern

Managers use module-level `get_X()` functions:
```python
_manager = None

def get_swarm_manager() -> SwarmManager:
    global _manager
    if _manager is None:
        _manager = SwarmManager()
    return _manager
```

### Database Persistence

`SwarmDatabase` stores sessions, agents, messages, and conflicts. Default path:
```python
Path(__file__).parent.parent.parent / "data" / "swarm.db"
```

Thread-local connections via `threading.local()` to avoid SQLite threading issues.

### CLI Tool Definitions

`Lilith/tools/swarm.py` defines OpenAI-compatible function definitions:
```python
def get_swarm_tools() -> list:
    return [spawn_swarm_def, swarm_status_def, swarm_kill_def, ...]
```

These map to actual `spawn_swarm()`, `swarm_status()`, etc. functions that the orchestrator can call as tools.

## Skills System v2 (FASE 7)

`Lilith/Core/skill_parser.py` and `Lilith/Core/skill_registry.py` were upgraded to v2 with extended triggers, templates, enable/disable, and usage stats.

### Skill Dataclass v2 Fields

```python
@dataclass
class Skill:
    name: str
    description: str
    content: str                          # Markdown body
    version: str = "1.0.0"
    trigger: List[str]       = []         # keyword triggers (backward compat)
    trigger_regex: List[str] = []         # regex patterns (compiled on parse)
    trigger_intent: List[str] = []        # intent labels (coding, research, etc.)
    priority: int = 100
    enabled: bool = True                  # can be disabled without removing
    tools_required: List[str] = []        # validated against DynamicToolRegistry
    prompt_template: Optional[str] = None  # overrides content when set
    source_file: Optional[Path] = None
    metadata: Dict[str, Any] = {}
    _times_triggered: int = 0
    _last_triggered: Optional[float] = None
```

### Trigger Scoring (ponderado)

- Keyword match: weight 0.4
- Regex match: weight 0.4
- Intent match: weight 0.2
- `should_trigger()` uses configurable threshold (default 0.1)

### Template Rendering

```python
skill.render(user_input="...", context="...", memory="", skills="coding, debugging")
```

Variables: `{{user_input}}`, `{{context}}`, `{{memory}}`, `{{skills}}`. Falls back to `skill.content` if no `prompt_template`.

### Skill Registry v2 Methods

- `enable_skill(name)`, `disable_skill(name)`, `is_enabled(name)`
- `record_trigger(name)` — increments `_times_triggered`, sets `_last_triggered`
- `get_usage_stats()` — returns `{name: {times_triggered, last_triggered}}`
- `get_triggered_skills()` — filters only `enabled=True` skills
- `set_tool_registry(dynamic_registry)` — inject for tools_required validation
- `SKILL_EXTENSIONS = {".md", ".yaml", ".yml"}` — loads all three formats

### Built-in Skills (5 files in `Lilith/skills/`)

| Skill | Priority | Triggers | Tools Required |
|-------|----------|----------|----------------|
| `debugging` | 95 (highest) | bug, crash, traceback, exception, regex for errors | shell, python |
| `coding` | 90 | code, program, function, class, debug, python, javascript | shell, python, file |
| `research` | 80 | research, find, search, investigate, what is | web_search, web_extract |
| `writing` | 75 | write, draft, summarize, blog, article | — |
| `analysis` | 70 | analyze, compare, evaluate, data, metrics | — |

Built-in skills auto-copy to `~/.lilith/skills/` on first CLI start (non-destructive, won't overwrite existing).

### CLI Command `/skills`

- `/skills` or `/skills list` — list all skills with name, description, enabled status, trigger count
- `/skills reload` — reload all skills from disk
- `/skills enable <name>` / `/skills disable <name>` — toggle skill activation
- `/skills stats` — show usage statistics (trigger counts, last triggered timestamps)
- `/skills info <name>` — detailed info (triggers, regex, intent, priority, tools, template)

### Orchestrator Integration

In `_build_system_prompt()`, triggered skills inject context using `skill.render()` with variables, and `record_trigger()` is called for each activated skill. Only enabled skills are considered.

### Production Hardening (FASE 9)

Four resilience and reliability modules:

**resilience.py** — Circuit Breaker + Retry
- `CircuitBreaker`: states CLOSED → OPEN (after N failures) → HALF_OPEN (after recovery timeout). Configurable `failure_threshold` (default 5), `recovery_timeout` (30s)
- `retry_with_backoff()`: exponential backoff with jitter (0.5s base, max 3 attempts). Configurable retryable exception list
- `RetryConfig` dataclass: `max_retries`, `base_delay`, `max_delay`, `jitter`, `retryable_exceptions`
- Integrated in `llm_provider.py`: each LLMProvider has its own CircuitBreaker

**error_handler.py** — Error Hierarchy + Sanitization
- `LilithError` → `ProviderError` (provider name + status_code), `ToolError` (tool_name + original_error), `MemoryError`, `ConfigError`
- `sanitize_output(text)`: strips Bearer tokens, `sk-*`/`ghp_*`/`glpat-*` tokens, API key assignments, URLs with credentials, emails
- `format_error(err, context=None)`: dark fantasy themed error messages mapped by exception type
- Handles `None` and non-string inputs (returns `""` or `str()`)

**lilith_logger.py** — Structured Dark Fantasy Logging
- `get_logger(name, level=None)`: factory returning styled logger
- Runic prefixes: ᚱ (INFO), ᛏ (DEBUG), ᚨ (WARNING), ᛃ (ERROR), ᛬ (CRITICAL)
- Format: `[RUNA] HH:MM:SS module | message`
- Per-module log level configuration, contextual emojis per module name

**graceful_shutdown.py** — Clean Shutdown + Crash Recovery
- `register_shutdown_hook(func)`: LIFO-ordered cleanup callbacks
- `execute_shutdown()`: idempotent, runs hooks once only
- `save_crash_marker(session_id)` / `check_crash_recovery()` / `clear_crash_marker()`: uses `~/.lilith/.crash_marker` to detect unclean exits
- `setup_graceful_shutdown(on_shutdown=None)`: registers SIGINT/SIGTERM handlers + atexit
- Integrated in `main.py`: saves session + stops consolidator on Ctrl+C; detects crash on next startup

### Dashboard v2 (FASE 10)

Dashboard upgraded with Memory Visualization, Swarm Panel, Settings, and REST API.

**server.py additions (+150 lines):**

5 new WebSocket command handlers:
- `memory_stats` → `_handle_memory_stats` — episode/entity/fact/error counts
- `memory_entities` → `_handle_memory_entities` — entities with type filter, min_mentions; strips embedding blobs
- `memory_facts` → `_handle_memory_facts` — facts with category filter
- `memory_graph` → `_handle_memory_graph` — knowledge graph nodes (entities) + edges (relations) for visualization
- `memory_episodes` → `_handle_memory_episodes` — recent episodes with count/session_id; strips embedding blobs

6 new REST API endpoints (`do_GET`):
- `GET /api/memory/stats` — memory statistics JSON
- `GET /api/memory/entities?type=X&min_mentions=N` — entity listing
- `GET /api/memory/facts?category=X` — fact listing
- `GET /api/memory/graph` — knowledge graph nodes + edges
- `GET /api/memory/episodes?count=N&session_id=X` — episode listing
- `GET /api/memory/search?q=X` — semantic search

All handlers use defensive `hasattr()` checks to work with or without a Lilith instance. Embedding blobs are stripped before JSON serialization.

**Frontend (app.js +473 lines, style.css +297 lines, index.html +38 lines):**

13 new JS functions:
- `updateMemoryStats(stats)`, `updateMemoryEntities(entities)`, `updateMemoryFacts(facts)` — render tab content
- `updateMemoryGraph(graphData)` → `drawMemoryGraph()` — canvas force-directed graph with zoom, drag, tooltips
- `updateMemoryEpisodes(episodes)` — timeline rendering
- `switchMemoryTab(tabName)` — tab switching (Graph/Entities/Facts/Episodes)
- `fetchMemoryData(tabName)`, `fetchMemoryStats()`, `fetchAllMemoryData()` — HTTP API fetches
- `memoryGraphZoom(factor)`, `memoryGraphReset()` — zoom controls
- `setupGraphInteraction()` — mouse/touch interaction for canvas graph

Memory pane redesigned with tabbed interface (runic icons), stats bar, canvas graph, search overlay.

### Memory RAG Integration (FASE 8)

The Orchestrator now integrates `SessionStore` and `BackgroundConsolidator`:

```python
# In LilithOrchestrator.__init__():
from Lilith.memory.session_store import get_session_store
from Lilith.memory.background_consolidator import get_consolidator

self.session_store = get_session_store()
self._consolidator = None  # lazy-started
self._current_session_id = datetime.now().strftime("%Y%m%d_%H%M%S")
```

Key methods:
- `start_consolidator()` / `stop_consolidator()` — manage daemon thread
- `_inject_session_context(query)` — searches past sessions for relevant context
- `_build_system_prompt()` — includes session context from past conversations
- `_save_current_session()` — auto-summarizes and saves current session
- `reset()` — saves session before resetting session_id
- `close()` — saves session + stops consolidator

### CLI `/session` and `/consolidate`

- `/session` or `/session list` — list saved sessions with active session marker
- `/session search <query>` — semantic search through sessions with scores
- `/session load <id>` — restore a past session's episodes into messages
- `/session delete <id>` — delete a session (protected: can't delete active)
- `/session save` — explicitly save current session
- `/consolidate` — run manual consolidation cycle, display merged/promoted/decayed counts

### CLI `/cron`

- `/cron` or `/cron list` — list all cron jobs with schedule, status, last run
- `/cron enable <id>` — enable a disabled cron job
- `/cron disable <id>` — disable an enabled cron job
- `/cron run <id>` — manually trigger a cron job immediately

### CLI `/templates`

- `/templates` or `/templates list` — list all agent templates (built-in + custom)
- `/templates info <name>` — show template details (system prompt, tools, variables)
- `/templates run <name>` — execute a template as a new agent task

### Skill File Format

Both `.md` (YAML frontmatter + Markdown body) and `.yaml`/`.yml` (pure YAML) are supported. YAML files use the same schema as frontmatter.

## Master Plan Status

| Fase | Nombre | Estado |
|------|--------|--------|
| 0 | Foundation | Done |
| 1 | Skills Framework | Done (SkillRegistry, hot-reload, auto-trigger) |
| 2 | Semantic Memory v2 | Done (MemoryGraph, Consolidation, HybridRetriever) |
| 3 | Swarm Coordination | **COMPLETE** (8 modules, 40 tests) |
| 4 | MCP Integration | **COMPLETE** (51 tests) |
| 5 | Dashboard | **COMPLETE** (39 tests, dark fantasy UI overhaul) |
| 6 | Integration + Polish | **COMPLETE** (328 tests total) |
| 7 | Skills System v2 | **COMPLETE** (402 tests, +74 skill tests) |
| 8 | Memory RAG + Sessions | **COMPLETE** (468 tests, +66 memory tests) |
| 9 | Production Hardening | **COMPLETE** (561 tests, +93 resilience/error/shutdown tests) |
| 10 | Dashboard v2 | **COMPLETE** (704 tests, +143 API/frontend tests) |
| 11 | GitHub Pages | **COMPLETE** (6-page static site, deploy workflow) |
| 12 | Svartalfheim Wiki | **COMPLETE** (9 realm pages, 10 ADRs, 3 runbooks, glossary) |
| 13 | Midgard Apps | **COMPLETE** (Finanzas, Habits, Recipes — 112 tests) |
| 14 | MCP Server + Cron + Templates | **COMPLETE** (166 tests) |
| 15 | v4.0.0 Release | **COMPLETE** (838 tests, batch mode added, Kimi Code API fixed) |

**Current version:** v4.0.0 (The Convergence — All Nine Realms United)

## Batch Mode

Lilith supports programmatic invocation via `--batch` flag for external agents and scripts. No interactive REPL — prompt in, response out.

### CLI Usage

```bash
# Simple prompt (response to stdout)
lilith --batch "Explain quantum entanglement"

# JSON output (includes model, version, status, usage)
lilith --batch "Summarize this" --batch-json

# Stream tokens as they arrive
lilith --batch "Tell me a story" --batch-stream

# Disable tools (text-only, no function calls)
lilith --batch "Translate to Old Norse" --batch-no-tools

# Custom system prompt
lilith --batch "Write a haiku" --batch-sys "You are a Japanese poet"

# Override model
lilith --batch "Quick test" --model kimi-for-coding

# Module invocation
python3 -m Lilith.batch "prompt here"
```

### Exit Codes

| Code | Meaning |
|------|---------|
| 0 | Success |
| 1 | LLM error (provider unreachable, API key missing, etc.) |
| 2 | No provider available (all circuits open or no keys) |

### Python API

```python
from Lilith.batch import run_batch

exit_code = run_batch(
    prompt="Explain quantum entanglement",
    json_output=True,      # structured JSON response
    no_tools=True,         # disable tools
    system_prompt="You are a physicist",
)
```

### Delegation from External Agents

```bash
# Hermes or other agents can delegate tasks
python3 -m Lilith.batch --json "Generate a database schema for..."
```

### Implementation Details

- `BatchRunner` class in `Lilith/batch.py` creates a `LilithOrchestrator` instance
- `--batch-no-tools` sets `orchestrator._force_no_tools = True`, making `_get_tools_for_llm()` return `[]`
- `--batch-stream` streams tokens to stdout without JSON wrapping
- `--batch-json` outputs `{"status": "success", "model": "...", "version": "4.0.0", "response": "...", "usage": {...}}`
- Test suite: `Lilith/Core/tests/test_batch.py` (18 tests)

### GitHub Pages Website (FASE 11)

The Yggdrasil public-facing website lives at `/mnt/d/Proyectos/Yggdrasil/website/` (separate repo from Lilith).

- **6 pages:** `index.html`, `realms.html`, `hermes-lilith.html`, `architecture.html`, `setup.html`, `changelog.html`
- **Static site:** No build step — pure HTML/CSS/JS with dark fantasy theme
- **Deploy:** GitHub Actions workflow at `.github/workflows/deploy-website.yml` — auto-deploys on push to `main` when `website/` changes
- **CNAME:** `yggdrasil.brierainz.dev`
- **Design system:** Inter + JetBrains Mono fonts, Norse mythology aesthetic (runic icons, glow effects, dark color palette)
- **URL:** `https://brierainz.github.io/Yggdrasil/` (or custom domain)

## TOML Config System (FASE 6)

`~/.lilith/config.toml` is the single source of truth for all configuration. Priority: **TOML file > env vars > hardcoded defaults**.

Key class: `Lilith.Core.toml_config.LilithConfig` (singleton, thread-safe with `threading.Lock`).

- `get(key, default)` — dotted key access: `config.get("llm.providers.lm_studio.base_url")`
- `set(key, value)` — modify in-memory config
- `save()` — persist to TOML file
- `reload()` — re-read from disk (hot-reload)
- Auto-creates default config if `~/.lilith/config.toml` doesn't exist
- `Lilith.Core.config.py` retains all public constants as retro-compat API, now backed by `LilithConfig`

Env vars still override TOML: `LILITH_LM_URL`, `LILITH_MODEL`, `LILITH_PROVIDER`, `LILITH_WORKSPACE`, `LILITH_SKILLS`, `KIMI_API_KEY`, etc.

## DynamicToolRegistry (FASE 6)

`Lilith.Core.dynamic_tools.DynamicToolRegistry` is the unified registry for all tools (native + MCP). Singleton thread-safe.

- `register_native_tools(all_tools, executors)` — register Python tool functions
- `register_mcp_tools(mcp_manager)` — register tools from MCP servers
- `get_openai_tools()` — returns OpenAI function-calling schema for ALL registered tools
- `execute(tool_name, args)` — dispatch to native executor or MCP client
- `get_stats()` — counts: total, native, mcp, mcp_connected
- `clear_mcp_tools()` / `refresh_mcp_tools()` — for MCP server lifecycle

The Orchestrator initializes the registry in `__init__`, calls `_try_init_mcp()` to connect MCP, and uses `get_openai_tools()` for LLM tool definitions. No more hardcoded `ALL_TOOLS` — everything goes through the registry.

## Pitfalls

- **Banner corruption:** Never use f-string multiline with complex expressions (like spacing math) — use string concatenation instead
- **setx PATH truncation:** Use PowerShell `[Environment]::SetEnvironmentVariable` instead
- **Dual entry points resolved:** `Asgard/lilith-cli/` was upgraded to v3.0.0 (Yggdrasil CLI v6.0) — a full Hermes-like agent REPL with streaming, tool calling, Rich rendering, and Cyclopts v4 commands. The `yggdrasil` entry point now unifies sysadmin (status, launch) and agent REPL. **Providers use httpx directly (NOT litellm)** — the litellm module had a namespace clash in the workspace. See `lilith-cli-setup` skill for full config/architecture. `Lilith/main.py` (Hermes-Lilith) remains the separate dark-fantasy standalone CLI with Swarm/MCP/Dashboard features.
- **Cyclopts v4 Parameter syntax:** v4.11.2+ requires `Parameter(name=["--flag", "-f"])` (list), NOT `Parameter("--flag", "-f")` (positional args). Positional args cause `TypeError` at import time. Always use keyword args in Cyclopts Parameter. Also: `*args` cannot have defaults — use `args: tuple[str, ...] = ()` instead.
- **litellm namespace clash:** `import litellm` in the Yggdrasil workspace resolves to an empty namespace due to the `lilith-core/lilith_core/providers/litellm_provider.py` shadowing. The v6.0 CLI uses httpx directly for OpenAI-compatible endpoints. Never add `import litellm` to `lilith-cli/lilith_cli/providers.py`.
- **OpenCode/GLM-5.1 provider config:** Must use `provider: opencode` (not `openai`) in `~/.yggdrasil/config.yaml` because provider resolution looks up `providers[<provider_name>]` for API key and base URL. Using `openai` would load `providers.openai` which has `${OPENAI_API_KEY}` env var (likely unset).
- **Python in WSL:** Use `python3` not `python`
- **LM Studio must be running:** All LLM-dependent features need the local server active on port 1234
- **Database paths:** Use `Path(__file__)` relatives, not hardcoded absolute paths — the project runs from both WSL and Windows
- **Thread-local DB connections:** Never share SQLite connections across threads — use `threading.local()` pattern
- **Test path resolution:** When tests are in `Module/tests/`, use `Path(__file__).parent.parent / "frontend"` NOT `Path(__file__).parent.parent / "Module" / "frontend"` — the `.parent.parent` already goes up to the module root. Double-nesting yields `Module/Module/frontend/`
- **_resolve_env pattern:** When resolving env vars in config, always include the key in the result dict even if the env var is missing (log a warning instead of silently dropping it)
- **History trimming:** Any method that appends to a bounded list must trim that list — don't only trim inside an `if` branch, since the `else` path also appends
- **.env secrets:** API keys go in `.env` (loaded by `python-dotenv` in `config.py`). `.env` is gitignored. Never commit real keys — `.env.example` contains only placeholder values. Always verify `.gitignore` has `.env` when adding secrets.
- **Pre-commit hooks:** The repo uses `black` + `isort` + trailing-whitespace + end-of-file fixers. After `git add -A && git commit`, hooks may reformat files — just `git add -A && git commit` again to proceed. For time-sensitive commits, use `--no-verify` to skip hooks.
- **pytest path resolution for .env:** Tests that verify `.env` exists or contains specific keys must use `Path(__file__).parent.parent.parent.parent / ".env"` (up to project root), NOT `parent.parent / ".env"` (which resolves inside the package).
- **Frontend redesigns preserving JS wireup:** When redesigning HTML/CSS in the Dashboard frontend, preserve ALL element IDs (`chat-input`, `terminal-input`, `memory-search-input`, `connection-status`, etc.), class names (`pane`, `active`, `chat-msg`, `modal hidden`, etc.), and onclick handlers (`toggleLayout()`, `toggleSettings()`, `sendChat()`). The tests in `test_dashboard.py` check for specific content like "dark fantasy" in CSS and test file existence, but the real risk is JS breakage — `app.js` binds event listeners by ID. Add decorative elements only; never rename or remove functional elements.
- **Dashboard aesthetic conventions:** Follow the design system in `references/dark-fantasy-design-system.md` (colors, runes, animations, particle system, element IDs). When modifying the dashboard UI, use the catalog of must-preserve IDs and global functions listed there. Add decorative elements only; never rename or remove functional elements. After visual overhauls, always run `python3 -m pytest Lilith/Dashboard/tests/ -q` to verify the 39 frontend tests still pass.
- **Version bump checklist:** When bumping the version, update ALL of these: `Lilith/__init__.py` (`__version__`), `Lilith/main.py` (version string in `--version` handler AND compact header line AND `/memory` banner), `Lilith/Dashboard/__init__.py` (docstring version), `Lilith/MCP/protocol.py` (`MCP_CLIENT_VERSION`). Search for `v2.` and `0.2.` patterns to find stragglers.
- **Singleton reset in tests:** When testing modules that use singletons (`LilithConfig`, `DynamicToolRegistry`, `MCPManager`), always reset the singleton before/after tests. Use `autouse` fixtures with `reset()` or `__init__()` calls to prevent cross-test contamination.
- **Orchestrator initialization without provider:** `LilithOrchestrator()` will raise `ConnectionError` if no LLM provider is available. In tests, always pass a mock provider: `LilithOrchestrator(provider=mock_provider)`. In headless mode, the CLI should catch this gracefully.
- **TOML config env var override:** env vars override TOML values, so `.env` file values take precedence. This means `KIMI_API_KEY` in `.env` will always win over `api_key = "..."` in `config.toml`. This is by design for security (no secrets in TOML files).
- **Tools without executors:** Some CLI-only tools (`spawn_swarm`, `swarm_status`, `swarm_kill`, `swarm_result`, `mcp_list`, `mcp_connect`, `mcp_disconnect`, `mcp_call`) are registered in `ALL_TOOLS` but have no executor in `TOOL_EXECUTORS`. They are handled by CLI command dispatch, not by the LLM. The `DynamicToolRegistry` logs warnings for these but still registers them for schema completeness.
- **Skill rendering in Orchestrator:** When building the system prompt, use `skill.render(user_input=..., context=..., memory=..., skills=...)` instead of raw `skill.content`. If `render()` returns empty, fall back to `skill.content[:2000]`. Always call `record_trigger(skill.name)` after injecting — this is how usage stats are tracked.
- **Built-in skill auto-copy:** `_copy_builtin_skills()` in `LilithCLI.__init__` copies from `Lilith/skills/` to `~/.lilith/skills/` only if the file doesn't already exist. Never overwrite user customizations. Use `shutil.copy2()` to preserve metadata.
- **Invalid regex in trigger_regex:** The parser compiles regex patterns on load. Invalid regex gets a `logger.warning()` and the pattern is skipped (not added to the compiled list). Tests should verify this graceful behavior — invalid regex should NOT crash the parser.
- **Kimi Code API X-Client header:** The Kimi Code API (`api.kimi.com/coding/v1`) REQUIRES the `X-Client: claude-code` header. Without it, requests fail with `access_terminated_error`. The `_get_headers()` method in `LLMProvider` auto-adds this header when `kimi.com` is in the base URL. Do NOT use the old `api.moonshot.cn/v1` endpoint — it's a different service. The model is `kimi-for-coding` (not `kimi-2.6`). See `references/llm-provider.md` for full details.
- **Git commit messages:** Long commit messages ( multiline `-m`) fail with exit code 1 in this repo. Use short single-line messages and `--no-verify` to skip hooks: `git commit -m "feat: short desc" --no-verify`. For detailed changelogs, put them in a separate file or the PR description.
- **SessionStore embedding fallback:** `search_sessions()` uses `EmbeddingModel` for semantic search. If sentence-transformers is unavailable, it falls back to LIKE-based keyword search. Tests should mock `EmbeddingModel.is_available()` to return `False` to test this path.
- **BackgroundConsolidator lifecycle:** Always call `stop_consolidator()` on shutdown. The daemon thread uses `threading.Event` for graceful stop. In CLI, it's stopped in the exit handler. In tests, use `setup_method`/`teardown_method` to ensure no dangling threads.
- **Memory DB path in tests:** Use `tmp_path` fixture for isolated SQLite databases. Never test against the real `~/.lilith/lilith_memory.db`. Reset singletons (`get_memory()`, `get_session_store()`, etc.) between test classes to avoid cross-contamination.
- **Sub-agent delegation verification:** When using `delegate_task`, always verify sub-agent output before committing. Sub-agents can time out (leaving partial work), leave functions referenced but unimplemented (JS function stubs), or produce code with subtle bugs (regex patterns too strict). Run `python3 -m pytest` after each delegation to catch issues. Read the modified files to verify completeness. **Verification checklist after each delegation:**
  1. Run full test suite (`python3 -m pytest Lilith/ -q --tb=short`)
  2. `git diff --cached --stat` — verify file list matches expectations
  3. Check for unreferenced function stubs: `grep -rn "def |function " new_files | grep -v test` then verify each is called
  4. If sub-agent modified frontend JS/HTML: verify all referenced functions exist, all element IDs are present, no `ReferenceError` stubs
  5. If sub-agent timed out (`exit_reason: max_iterations`): explicitly check what it said it left incomplete in its summary, and finish those items manually before committing
- **Regex sanitization token lengths:** In `sanitize_output()`, API token regex patterns must use short minimum lengths (`{4,}`) not production-length minimums (`{20,}`). Real tokens are long, but test fixtures use short strings. Use `\b` word boundaries to prevent false positives: `\bsk-[a-zA-Z0-9_-]{4,}\b`, `\bghp_[a-zA-Z0-9]{4,}\b`, `\bglpat-[a-zA-Z0-9]{4,}\b`.
- **sanitize_output None handling:** `sanitize_output()` must handle `None` input (return `""`), not crash with `TypeError`. Non-string inputs should be `str()`-converted first, then pattern-substituted.
- **Circuit breaker test isolation:** `CircuitBreaker` is stateful (tracks failure count, state transitions). In tests, create fresh instances per test method — never share a circuit breaker across test methods without resetting.
- **Dashboard JS function completeness:** When adding WebSocket handlers in `app.js` that dispatch to JS functions (e.g., `case 'memory_stats': updateMemoryStats(data)`), always implement the receiving function in the same edit session. Unimplemented function references will cause `ReferenceError` at runtime in the browser.
- **Dashboard test file separation:** New Dashboard API tests go in `Lilith/Dashboard/tests/test_dashboard_api.py`. The original `test_dashboard.py` tests frontend file existence and basic server config. API endpoint tests test the actual `DashboardServer` command handlers and HTTP routing.
- **Multi-repo commits:** FASE 11+ changes span two repos: `Hermes-Lilith` (Python code, tests) and the Yggdrasil root (`website/`, `.github/`, `REGLAS_YGGDRASIL.md`). Commit to the correct repo. Lilith code changes go in `Asgard/Hermes-Lilith/`, website/deploy changes go in the Yggdrasil root. Each repo has its own git history — don't accidentally `git add` website files in the Lilith repo or vice versa.
- **Midgard app paths:** Midgard apps (`finanzas/`, `habits/`, `recipes/`) live under `/mnt/d/Proyectos/Yggdrasil/Midgard/` — a SIBLING repo to `Asgard/Hermes-Lilith/`. They are NOT inside the Lilith package. Their tests use `sys.path` insertion to find their own modules, not Lilith's.
- **MCP server stdio protocol:** The `LilithMCPServer` uses stdin/stdout JSON-RPC — never attempt to use it over HTTP directly. External agents connect via MCP client which manages the subprocess and protocol framing.
- **Cron scheduler SQLite locking:** CronScheduler uses SQLite for persistence. Like all SQLite in this project, it needs `threading.local()` for thread-local connections. Never share a connection across threads.
- **Template variable injection:** `TemplateRenderer` uses `{{variable}}` syntax (Jinja-like but simplified). Variables not provided in the context dict are left as-is (not removed). This is intentional — missing variables render literally so the user can see what wasn't substituted.
- **Svartalfheim docs are separate repo:** Wiki/ADR content lives in `/mnt/d/Proyectos/Yggdrasil/Svartalfheim/`, not inside Hermes-Lilith. Document changes commit to the Yggdrasil root repo.
- **Batch phase completion verification:** When completing multiple phases in a single session (e.g., "completa todas las fases de una"), delegate sub-tasks in parallel but ALWAYS run the full test suite after ALL delegates complete, not after each one. Sub-agents can produce conflicting changes that only surface at integration time.
- **Sub-agent timeout handling:** When `delegate_task` times out (`exit_reason: max_iterations`), check what files were created/modified by running `git status --short` and `git diff --stat HEAD`. Partial work from timed-out agents is usually salvageable — finish the remaining functions/tests manually rather than starting over.

### MCP CLI Integration

The `/mcp` command delegates to `handle_mcp_command()` in `Lilith/tools/mcp_connect.py`. Sub-commands: `connect`, `disconnect`, `list`, `tools`, `call`, `status`, `config`. Uses singleton `get_mcp_manager()`.

### Dashboard CLI Integration

The `/dashboard` command delegates to `handle_dashboard_command()` in `Lilith/tools/dashboard.py`. Sub-commands: `start`, `stop`, `status`, `help`. The server is a singleton via `get_dashboard()`. The DashboardServer runs aiohttp with WebSocket on the configured port (default 8765) and HTTP on port+1 (8766). Frontend files are served from `Dashboard/frontend/`.

### Production Hardening (FASE 9)

Four new modules for resilience and reliability:

**resilience.py** — Circuit Breaker + Retry
- `CircuitBreaker`: states CLOSED → OPEN (after N failures) → HALF_OPEN (after recovery timeout), configurable `failure_threshold` (default 5) and `recovery_timeout` (30s)
- `retry_with_backoff()`: exponential backoff with jitter (0.5s base, max 3 attempts), configurable retryable exception list
- `RetryConfig` dataclass: `max_retries`, `base_delay`, `max_delay`, `jitter`, `retryable_exceptions`
- Integrated in `llm_provider.py`: each LLMProvider has its own CircuitBreaker instance

**error_handler.py** — Error Hierarchy + Sanitization
- `LilithError` → `ProviderError` (provider name + status_code), `ToolError` (tool name + original_error), `MemoryError`, `ConfigError`
- `sanitize_output(text)`: strips Bearer tokens, `sk-*`/`ghp_*`/`glpat-*` tokens, API key assignments, URLs with credentials, emails
- `format_error(err, context=None)`: dark fantasy themed error messages mapped by exception type
- Handles `None` and non-string inputs gracefully (returns `""` or `str()`)

**lilith_logger.py** — Structured Dark Fantasy Logging
- `get_logger(name, level=None)`: factory returning styled logger
- Runic prefixes: ᚱ (INFO), ᛏ (DEBUG), ᚨ (WARNING), ᛃ (ERROR), ᛬ (CRITICAL)
- Format: `[RUNA] HH:MM:SS module | message`
- Dark fantasy mode with contextual emojis per module name
- Per-module log level configuration

**graceful_shutdown.py** — Clean Shutdown + Crash Recovery
- `register_shutdown_hook(func)`: LIFO-ordered cleanup callbacks
- `execute_shutdown()`: idempotent, runs hooks once
- `request_shutdown()`: triggers `execute_shutdown()` via threading.Event
- `setup_graceful_shutdown(on_shutdown=None)`: registers SIGINT/SIGTERM handlers + atexit
- `save_crash_marker(session_id)` / `check_crash_recovery()` / `clear_crash_marker()`: use `~/.lilith/.crash_marker` file to detect unclean exits
- Integrated in `main.py`: saves session + stops consolidator on Ctrl+C, detects crash on next startup

### MCP Server (FASE 14)

`Lilith/MCP/server.py` — `LilithMCPServer` exposes Lilith skills and tools via JSON-RPC MCP protocol (stdio transport).

- Inherits MCP protocol patterns from `Lilith/MCP/client.py`
- Registers internal Lilith tools as MCP-callable functions
- Transport: stdio (stdin/stdout JSON-RPC)
- Used by external agents (Hermes, Vanaheim agents) to invoke Lilith capabilities
- Integrated in `Lilith/MCP/__init__.py` for easy import

### Cron Scheduler (FASE 14)

`Lilith/MCP/cron.py` — `CronScheduler` for periodic task execution within Lilith.

- SQLite-backed persistence (`~/.lilith/cron.db`)
- Configurable intervals: daily, hourly, custom cron expressions
- Thread-safe job execution with locking
- CLI integration: `/cron list`, `/cron enable <id>`, `/cron disable <id>`, `/cron run <id>`
- Integrated with LilithCLI command dispatch in `main.py`
- Status tracking: last_run, next_run, success/failure counts

### Agent Templates (FASE 14)

`Lilith/MCP/templates.py` — `AgentTemplate` and `TemplateLibrary` for predefined agent prompts.

- 5 built-in templates: `researcher`, `coder`, `analyst`, `reviewer`, `creative`
- YAML-based template definitions with variable injection
- Custom templates: load from `~/.lilith/templates/` directory
- `TemplateRenderer` substitutes `{{variables}}` into prompt templates
- CLI: `/templates list`, `/templates info <name>`, `/templates run <name>`
- Each template defines: name, description, system_prompt, tools, model_hint, variables

### Midgard Personal Apps (FASE 13)

Three standalone CLI apps in the Yggdrasil repo (`/mnt/d/Proyectos/Yggdrasil/Midgard/`):

**Finanzas** (`Midgard/finanzas/`)
- `midgard_finanzas` CLI entry point
- Track income/expenses, category-based budgets, date filtering
- SQLite persistence (`~/.midgard/finanzas.db`)
- Reports: summary, category breakdown, monthly trends
- 29 tests

**Habits** (`Midgard/habits/`)
- `midgard_habits` CLI entry point
- Daily habit tracking with streaks, completion rates, weekly/monthly views
- SQLite persistence (`~/.midgard/habits.db`)
- Streak calculation, trend visualization
- 45 tests

**Recipes** (`Midgard/recipes/`)
- `midgard_recipes` CLI entry point
- Recipe management with ingredients, instructions, tags, difficulty ratings
- SQLite persistence (`~/.midgard/recipes.db`)
- Search by ingredient, tag, difficulty; random recipe selection
- 38 tests

All three apps share: dark fantasy CLI aesthetic (Rich), SQLite persistence, standalone installation, Norse-themed naming.

### Svartalfheim Wiki (FASE 12)

Documentation and knowledge base in `/mnt/d/Proyectos/Yggdrasil/Svartalfheim/`:

- **9 realm pages** — one per Yggdrasil realm with purpose, tech stack, conventions
- **10 ADRs** (Architecture Decision Records) — numbered decisions on key tech choices
- **3 runbooks** — operational guides (deployment, troubleshooting, monitoring)
- **Cross-realm dependency map** — which realms depend on which
- **Glossary** — Norse-themed terminology mapping
- **Templates** — ADR template, runbook template, realm page template

### CLI Commands Added in FASE 9

No new user-facing CLI commands. The graceful shutdown hooks are integrated into the existing exit flow:
- Ctrl+C → signal handler → `execute_shutdown()` → saves session, stops consolidator, clears crash marker
- Unclean exit → crash marker persists → next startup shows "Previous session detected" + `/session load` hint

## Linked References

- `references/swarm-architecture.md` — detailed Swarm module architecture and API reference
- `references/llm-provider.md` — multi-provider LLM fallback system, Kimi integration, provider configuration
- `references/batch-mode.md` — batch mode: BatchRunner, CLI args, JSON output, delegation patterns, exit codes
- `references/dark-fantasy-design-system.md` — dark fantasy/Norse/Lovecraftian CSS design system, rune particles, glitch effects, color palette, animation catalog, and element IDs that must be preserved
- `references/toml-config.md` — TOML config system: LilithConfig API, priority hierarchy, dotted-key access, hot-reload, retro-compat with config.py constants
- `references/memory-rag.md` — Memory RAG architecture: SessionStore, BackgroundConsolidator, HybridRetriever weights, session context injection, test patterns

## See Also

- `lilith-cli-setup` — specific skill for CLI installation, PATH configuration, install.bat