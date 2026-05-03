# Changelog — Lilith

All notable changes to the Lilith project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [4.0.0] — 2025-05-02

### The Convergence — All Realims United

Lilith v4.0.0 marks the complete convergence of the Nine Realms. Every subsystem is battle-tested, production-hardened, and interconnected.

### FASE 8 — Memory RAG

#### Added
- `SessionStore` — save/load/search session summaries with semantic vector search
- `BackgroundConsolidator` — daemon thread for periodic episode merging (>0.85 similarity) and fact promotion (>=3 mentions)
- Auto-summary on session close
- Context injection from relevant past sessions on new conversation start
- CLI commands: `/session list`, `/session search`, `/session load`, `/session save`, `/session delete`
- `/consolidate` command for manual consolidation cycle with stats
- 17 new tests for orchestrator session integration

### FASE 9 — Production Hardening

#### Added
- `CircuitBreaker` — CLOSED/OPEN/HALF_OPEN states, configurable failure threshold (5), 30s recovery timeout
- `retry_with_backoff()` — exponential backoff with jitter (0.5s base, max 3 retries), configurable retryable exceptions
- `RetryConfig` dataclass for complete retry configuration
- `LilithError` hierarchy: `ProviderError`, `ToolError`, `MemoryError`, `ConfigError`
- `sanitize_output()` — strips Bearer tokens, API keys (sk-*, ghp_*, glpat-*), URLs with credentials, emails
- `format_error()` — dark fantasy themed error messages per error type
- `get_logger()` — structured logging with runic prefixes (ᚱ INFO, ᛏ DEBUG, ᚨ WARN, ᛃ ERROR)
- `GracefulShutdownManager` — signal handlers for SIGINT/SIGTERM, LIFO hook execution, atexit cleanup
- `save_crash_marker()` / `check_crash_recovery()` — crash detection and session recovery
- Circuit breaker integration per LLM provider in `llm_provider.py`
- `None` handling in `sanitize_output()`
- 46 resilience tests, 21 error handler tests, 26 graceful shutdown tests

### FASE 10 — Dashboard v2

#### Added
- Memory Visualization: interactive canvas graph with force-directed layout, zoom, drag, tooltips
- Memory tabs: Graph / Entities / Facts / Episodes with runic icons
- Memory stats bar with quick counts
- 5 new WebSocket handlers: `memory_stats`, `memory_entities`, `memory_facts`, `memory_graph`, `memory_episodes`
- 6 new REST API endpoints: `/api/memory/stats`, `/api/memory/entities`, `/api/memory/facts`, `/api/memory/graph`, `/api/memory/episodes`, `/api/memory/search`
- 13 new frontend JS functions for memory visualization
- 143 new dashboard tests (182 total)

### FASE 14 — Multi-Agent Orchestration

#### Added
- `LilithMCPServer` — MCP protocol server exposing skills and tools via JSON-RPC (stdio transport)
- `CronScheduler` — periodic task scheduler with configurable intervals, SQLite persistence, CLI commands (`/cron list/enable/disable/run`)
- `AgentTemplate` / `TemplateLibrary` — predefined agent templates (researcher, coder, analyst, reviewer, creative) with YAML support and custom templates from `~/.lilith/templates/`
- `TemplateRenderer` — variable injection into prompt templates
- CLI: `/cron`, `/templates` commands
- 166 new MCP/Cron/Templates tests

### Changed
- Version bump from 3.0.0 to 4.0.0
- Orchestrator: `_inject_session_context()` searches past sessions for relevant context
- Orchestrator: `_build_system_prompt()` includes session context
- Orchestrator: `reset()` saves session before clearing
- Orchestrator: `close()` saves session and stops consolidator
- `llm_provider.py`: circuit breaker per provider, retry with backoff, structured error handling

### Tests
- **819 total tests passing** (2 skipped, 0 failures) — from 402 at v3.0.0

---

## [3.0.0] — 2025-04-30

### The Awakening — Lilith v3

Complete rewrite of the Lilith agent with modular architecture, Norse mythology aesthetic, and 9-realm ecosystem.

#### Added
- Modular architecture: Core (Orchestrator, LLM Provider, Skills, Swarm), Memory (Graph, Retrieval), Dashboard, MCP, Bifrost
- Multi-provider LLM: LM Studio (local) → Kimi/Moonshot (remote) with auto-fallback
- TOML configuration system with deep merge and validation
- Skill System v1 with YAML/Markdown support
- Swarm Intelligence with AgentSpawner and persistent agents
- MCP Protocol for tool discovery
- Streaming responses with Rich live display
- SQLite-based vector + graph + FTS5 hybrid memory
- WebSocket Dashboard with real-time visualization
- Telegram Bot integration
- 402 tests passing

---

## [2.0.0] — 2025-03-15

### The Spark — Initial Release

Early versions of Lilith with basic LLM integration and memory.

#### Added
- Basic LLM provider integration
- Simple conversation memory
- CLI interface with Rich formatting
- Telegram bot basic commands

---

## [1.0.0] — 2025-01-01

### Genesis

Initial project setup and proof of concept.