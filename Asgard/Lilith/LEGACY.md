# ⚠️ LEGACY — Lilith Monolith v5.0

**Status:** DEPRECATED — Archived 2026-05-21 during Yggdrasil Refactoring Phase 2

**This directory contains the original Lilith monolith (v5.0, 477 files).**

The functionality has been refactored into the following workspace packages:

| Old Module | New Package |
|---|---|
| `src/core/` | `lilith-core` |
| `src/memory/` | `lilith-memory` |
| `src/tools/` | `lilith-tools` |
| `src/api/` | `lilith-api` |
| CLI / REPL | `lilith-cli` |
| `src/` orchestrator | `lilith-orchestrator` |
| `src/` bridge | `lilith-bridge` |
| Skills | `lilith-skills` |

## What's Here

- **Core/** — Original monolith: Destrezas (skills), Workspace, Tools, launchers
- **src/** — Refactored v5 API with IPC server, REST endpoints, LLM routing
- **scripts/** — Legacy .bat launchers
- **Data/** — Runtime state (chroma DBs, session logs, memory — NOT production code)

## Migration Notes

- No new package imports from this directory
- `Data/` contains only local runtime artifacts
- The new packages use `lilith-*` namespace via uv workspace
- `yggdrasil_cli.py` (root) is the replacement for the old `scripts/lilith_cli.py`

## Planned Action

Move `Asgard/Lilith/` → `Helheim/Archives_Lilith_Legacy/` after git history is preserved.

