# Yggdrasil Implementation Plans — Master Index

> 23 planes + 1 cleanup plan · Ubicación: `Svartalfheim/Docs/plans/` (01–18) y `Svartalfheim/plans/` (19–23)

## Active Plans

| # | Plan | Realm | Status | Description |
|---|------|-------|--------|-------------|
| 19 | YggdrasilStudio v0.4 | Alfheim | In Progress | Studio improvements: refactor PromptBuilder/Settings, tests, new endpoints |
| 20 | YggdrasilForge v0.1 | Alfheim | Active | Viking 3D Asset Studio — AI generation + Blender Bridge |
| 21 | Yggdrasil Growth v5 | Cross-realm | Active | Growth plan — WS bridge, Mimir agent, build system |
| 22 | Photon WASM | Alfheim | Planned | Python→WASM via Pyodide for client-side modules |
| 23 | Turborepo Monorepo | Alfheim | Planned | Turborepo migration for Alfheim frontend builds |

## Completed Plans

| # | Plan | Realm | Version | Description |
|---|------|-------|---------|-------------|
| 01 | AutoSub | Muspelheim | v0.1.0 | Generador automático de subtítulos (Whisper → SRT) |
| 13 | TerminalDashboard | Alfheim | v1.0.0 | TUI dashboard del ecosistema Yggdrasil |
| 15 | Mimir | Vanaheim | Active | Investigador profundo (SearXNG + arXiv), agente VanirAgent |
| 18 | ForgeMaster | Muspelheim | v1.0.0 | Gestión de modelos LLM, VRAM y disk usage |

## Planned / Paused Plans

| # | Plan | Realm | Status | Description |
|---|------|-------|--------|-------------|
| 02 | ClipForge | Muspelheim | Planned | Detector de clips virales |
| 03 | TrendRadar | Muspelheim | Planned | Monitor de tendencias multi-plataforma |
| 04 | FinTracker | Midgard | Planned | Dashboard financiero personal |
| 05 | HabitForge | Midgard | Planned | Tracker de hábitos con comprensión de patrones |
| 06 | RecipeAlchemist | Midgard | Planned | Generador de recetas por ingredientes disponibles |
| 07 | CodeGhost | Vanaheim | Planned | Agente de code review autónomo |
| 08 | DocWeaver | Vanaheim | Planned | Agente que mantiene documentación viva |
| 09 | ResearchHound | Vanaheim | Planned | Agente de investigación autónomo |
| 10 | PromptForge | Vanaheim | Planned | Agente que optimiza prompts |
| 11 | LoreKeeper | Svartalfheim | Planned | Base de conocimiento conversacional |
| 12 | SkillTree | Svartalfheim | Planned | Mapa interactivo de aprendizaje |
| 14 | PixelForge | Alfheim | Planned | Editor de pixel art en la web |
| 16 | RuneBoard | Midgard | Planned | Kanban personal con runas nórdicas |
| 17 | YggSiteGenerator | Alfheim | Planned | Generador de sitios estáticos para el ecosistema |

## Cleanup Plan

| File | Description |
|------|-------------|
| `plan-yggdrasil-cleanup.md` | Mega Cleanup & Profesionalización del ecosistema (completado May 2026) |

## Plan-to-Realm Mapping

| Realm | Plans |
|-------|-------|
| **Asgard** | (core packages, no standalone plans) |
| **Alfheim** | 13-TerminalDashboard ✅, 14-PixelForge, 17-YggSiteGenerator, 19-YggdrasilStudio v0.4, 20-YggdrasilForge, 22-Photon WASM, 23-Turborepo |
| **Muspelheim** | 01-AutoSub ✅, 02-ClipForge, 03-TrendRadar, 18-ForgeMaster ✅ |
| **Midgard** | 04-FinTracker, 05-HabitForge, 06-RecipeAlchemist, 16-RuneBoard |
| **Vanaheim** | 07-CodeGhost, 08-DocWeaver, 09-ResearchHound, 10-PromptForge, 15-Mimir ✅ |
| **Svartalfheim** | 11-LoreKeeper, 12-SkillTree |
| **Cross-realm** | 21-Yggdrasil Growth v5, plan-yggdrasil-cleanup |

## Cross-Realm Dependencies

```
YggdrasilStudio (2D) ←──── YggdrasilForge (3D)
   :8080                       :8081
   ComfyUI :8188               Blender MCP :9897
        │                          │
        └── Image → 3D bridge ─────┘

ForgeMaster ──→ Model management for all GPU-dependent projects
Mimir ──→ Research feeds into Svartalfheim/Knowledge/
Photon WASM ──→ Shared with YggdrasilStudio frontend
Turborepo ──→ Unified build for Alfheim frontends (Studio, Forge, Dashboard)
```

## Conventions

- Plan files: `plan-NN-projectname.md` (zero-padded, kebab-case)
- Each plan: Goal, Architecture, Tech Stack, Realm, 8–12 bite-sized Tasks
- Task format: Objective, Files, Steps, Verification, Commit
- Plans 01–18: `Svartalfheim/Docs/plans/`
- Plans 19+: `Svartalfheim/plans/`
- All projects start in their designated realm directory
- All projects use: `pyproject.toml`, CLI framework (Typer/Cyclopts), Rich output, SQLite, pytest
