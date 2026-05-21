# ⚠️ LEGACY — Vanaheim Monolith

**Status:** DEPRECATED — Archived 2026-05-21 during Yggdrasil Refactoring Phase 3

The following directories contain legacy Vanaheim code that has been superseded
by the refactored workspace packages:

| Old Directory | Replacement |
|---|---|
| `Agents/` (Adán, Eva, Mimir, Odin) | `vanaheim-framework/` (modular agent system) |
| `Core/` (API, models, memory) | `lilith-core/`, `lilith-api/`, `lilith-memory/` |
| `Config/` (agent configs) | per-package config (pyproject.toml, .env) |
| `Bots_Lilith_v5/` (Telegram bot) | `lilith-bridge/` (multi-platform gateway) |
| `Council/` (templates) | `lilith-orchestrator/` (council system) |

## Active Packages (DO NOT MODIFY THESE)

- `vanaheim-framework/` — Agent framework (pyproject.toml, tests/)
- `bifrost/` — Gateway server (pyproject.toml, tests/)
- `gamemaster-mcp-server/` — MCP server for game characters

## Planned Action

Move legacy dirs to `Helheim/Archives_Vanaheim_Legacy/` after git history is preserved.
