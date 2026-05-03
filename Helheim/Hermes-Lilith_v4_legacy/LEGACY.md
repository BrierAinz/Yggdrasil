# ⚠️ Legacy Archive — Hermes-Lilith (v4)

This directory contains the **Lilith v4 monolith** — the original single-package implementation before the v5 modular refactor.

## Status: ARCHIVED

- **Do not modify** — all active development happens in `Asgard/Lilith/` (v5)
- **Do not rename** — preserved for git history continuity
- **Do not delete** — contains reference implementations and historical context

## Known Stale Paths

Several files in this directory contain hardcoded references to `D:\Proyectos\Midgard`. These are **obsolete** — the project was originally named "Midgard" and later renamed to "Yggdrasil". Affected files:

| File | Stale Path |
|------|-----------|
| `Lilith/Hermes/hermes_config.yaml` | `D:\Proyectos\Midgard\Lilith\Hermes\mcp_bridge.py` |
| `Lilith/Hermes/README.md` | `D:\Proyectos\Midgard\Lilith\Hermes\mcp_bridge.py` |
| `Lilith/README.md` | `cd D:\Proyectos\Midgard\Lilith` |
| `Lilith/launch_lilith.ps1` | `$ProjectRoot = "D:\Proyectos\Midgard"` |
| `SETUP.md` | `set LILITH_WORKSPACE=D:\Proyectos\Midgard` (corrected to Yggdrasil) |
| `skills/automation/SKILL.md` | `D:\Proyectos\Midgard\automation\` |

These paths are left as-is because this is a frozen archive. The active v5 codebase in `Asgard/Lilith/` uses proper path resolution.

## Migration Map

| v4 (this directory) | v5 (Asgard/Lilith/) |
|---------------------|---------------------|
| `Lilith/Core/` | `lilith-core/src/lilith_core/` |
| `Lilith/Memory/` | `lilith-memory/src/lilith_memory/` |
| `Lilith/Tools/` | `lilith-tools/src/lilith_tools/` |
| `Lilith/Orchestrator/` | `lilith-orchestrator/src/lilith_orchestrator/` |
| `Lilith/API/` | `lilith-api/src/lilith_api/` |
| `Lilith/CLI/` | `lilith-cli/src/lilith_cli/` |
| `Lilith/Swarm/` | `src/core/agents/swarm/` |
| `Lilith/Hermes/` | `src/core/integrations/mcp/` |

---

*Last updated: 2026-05-03*
