# Planes de Desarrollo Yggdrasil

> Índice maestro de planes detallados para cada idea del ecosistema.
> Para ejecutar un plan, usar el skill `subagent-driven-development`.

## Muspelheim — Proyectos WIP / Active Dev

| # | Plan | Proyecto | Realm | Estado | Descripción |
|---|------|----------|-------|--------|-------------|
| 01 | [AutoSub](plan-01-autosub.md) | AutoSub | Muspelheim | ✅ COMPLETE | Generador automático de subtítulos (Whisper → SRT) |
| 02 | [ClipForge](plan-02-clipforge.md) | ClipForge | Muspelheim | 📋 Plan | Detector de clips virales (energy, faces, transcript) |
| 03 | [TrendRadar](plan-03-trendradar.md) | TrendRadar | Muspelheim | 📋 Plan | Monitor de tendencias multi-plataforma |
| 18 | [ForgeMaster](plan-18-forgemaster.md) | ForgeMaster | Muspelheim | ✅ v1.0.0 | Gestión de modelos LLM, VRAM, y disk usage |

## Midgard — Aplicaciones Personales

| # | Plan | Proyecto | Realm | Estado | Descripción |
|---|------|----------|-------|--------|-------------|
| 04 | [FinTracker](plan-04-fintracker.md) | FinTracker | Midgard | 📋 Plan | Dashboard financiero personal |
| 05 | [HabitForge](plan-05-habitforge.md) | HabitForge | Midgard | 📋 Plan | Tracker de hábitos con análisis de correlaciones |
| 06 | [RecipeAlchemist](plan-06-recipealchemist.md) | RecipeAlchemist | Midgard | 📋 Plan | Recetas por ingredientes disponibles |
| 16 | [RuneBoard](plan-16-runeboard.md) | RuneBoard | Midgard | 📋 Plan | Kanban personal con runas nórdicas |

## Vanaheim — Agentes de IA

| # | Plan | Proyecto | Realm | Estado | Descripción |
|---|------|----------|-------|--------|-------------|
| 07 | [CodeGhost](plan-07-codeghost.md) | CodeGhost | Vanaheim | 📋 Plan | Agente de code review autónomo |
| 08 | [DocWeaver](plan-08-docweaver.md) | DocWeaver | Vanaheim | 📋 Plan | Mantenedor de documentación viva |
| 09 | [ResearchHound](plan-09-researchhound.md) | ResearchHound | Vanaheim | 📋 Plan | Investigador autónomo multi-fuente |
| 10 | [PromptForge](plan-10-promptforge.md) | PromptForge | Vanaheim | 📋 Plan | Optimizador iterativo de prompts |
| 15 | [Mimir](plan-15-mimir.md) | Mimir | Vanaheim | 🔄 Active | Investigador profundo (SearXNG + arXiv), agente VanirAgent |

> **Nota:** Mimir fue originalmente planeado como "Chatbot RAG" en Midgard, pero se implementó como agente VanirAgent en Vanaheim/Agents/Mimir/ con research_tools.py y agent.py.

## Svartalfheim — Documentación y Conocimiento

| # | Plan | Proyecto | Realm | Estado | Descripción |
|---|------|----------|-------|--------|-------------|
| 11 | [LoreKeeper](plan-11-lorekeeper.md) | LoreKeeper | Svartalfheim | 📋 Plan | Base de conocimiento conversacional (RAG) |
| 12 | [SkillTree](plan-12-skilltree.md) | SkillTree | Svartalfheim | 📋 Plan | Mapa interactivo de aprendizaje tipo RPG |

## Alfheim — Prototipos UI

| # | Plan | Proyecto | Realm | Estado | Descripción |
|---|------|----------|-------|--------|-------------|
| 13 | [TerminalDashboard](plan-13-terminaldashboard.md) | TerminalDashboard | Alfheim | ✅ v1.0.0 | TUI dashboard del ecosistema Yggdrasil |
| 14 | [PixelForge](plan-14-pixelforge.md) | PixelForge | Alfheim | 📋 Plan | Editor de pixel art con paletas retro |
| 17 | [YggSiteGenerator](plan-17-yggsitegenerator.md) | YggSiteGenerator | Alfheim | 📋 Plan | Generador de sitio estático para GitHub Pages |

## Cross-Realm — Infraestructura

| # | Plan | Proyecto | Realm | Estado | Descripción |
|---|------|----------|-------|--------|-------------|
| — | YggdrasilStudio | Studio | Alfheim | 🔄 v0.3.0 | Estudio de generación AI (ver skill) |
| — | YggdrasilForge | Forge | Alfheim | 🔄 v0.1.0 | Estudio 3D Viking (ver skill) |
| — | Alfheim Dashboard | Dashboard | Alfheim | ✅ v1.0.0 | HTMX + Alpine.js dashboard |
| — | WS Bridge | Bridge | Alfheim | 🔄 Active | ComfyUI WebSocket fan-out bridge |

---

## Dependencias Cross-Realm

```
CodeGhost ──→ DocWeaver (docs auto-repair)
ResearchHound ──→ LoreKeeper (research → knowledge base)
LoreKeeper ──→ Mimir (knowledge → chatbot)
PromptForge ──→ Lilith (prompt optimization → agent)
AutoSub ──→ ComfyUI (subtitles → video pipeline)
ClipForge ──→ TrendRadar (viral detection → trend monitoring)
ForgeMaster ──→ Todos (VRAM/disk info → dashboard)
TerminalDashboard ──→ ForgeMaster (GPU monitoring)
SkillTree ──→ LoreKeeper (learning paths → knowledge base)
YggSiteGenerator ──→ Website actual (auto-build)
YggdrasilStudio ──→ ComfyUI (image/video generation)
YggdrasilStudio ──→ WS Bridge (real-time progress)
```

## Convenciones

- Cada plan está en `Svartalfheim/Docs/plans/plan-XX-nombre.md`
- Los proyectos se crean en el realm correspondiente: `Muspelheim/AutoSub/`, `Vanaheim/CodeGhost/`, etc.
- Todo proyecto usa: `pyproject.toml`, Typer CLI, Rich output, SQLite, pytest
- Los tests se configuran según `REGLAS_YGGDRASIL.md`
- Proyectos completados tienen ✅ y su versión
- Planes no iniciados tienen 📋
- Proyectos activos pero no completados tienen 🔄