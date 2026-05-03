# Planes de Desarrollo Yggdrasil

> Índice maestro de planes detallados para cada idea del ecosistema.
> Para ejecutar un plan, usar el skill `subagent-driven-development`.

## Muspelheim — Proyectos WIP / Active Dev

| # | Plan | Proyecto | Realm | Descripción |
|---|------|----------|-------|-------------|
| 01 | [AutoSub](plan-01-autosub.md) | AutoSub | Muspelheim | Generador automático de subtítulos (Whisper → SRT) |
| 02 | [ClipForge](plan-02-clipforge.md) | ClipForge | Muspelheim | Detector de clips virales (energy, faces, transcript) |
| 03 | [TrendRadar](plan-03-trendradar.md) | TrendRadar | Muspelheim | Monitor de tendencias multi-plataforma |

## Midgard — Aplicaciones Personales

| # | Plan | Proyecto | Realm | Descripción |
|---|------|----------|-------|-------------|
| 04 | [FinTracker](plan-04-fintracker.md) | FinTracker | Midgard | Dashboard financiero personal |
| 05 | [HabitForge](plan-05-habitforge.md) | HabitForge | Midgard | Tracker de hábitos con análisis de correlaciones |
| 06 | [RecipeAlchemist](plan-06-recipealchemist.md) | RecipeAlchemist | Midgard | Recetas por ingredientes disponibles |
| 15 | [Mimir](plan-15-mimir.md) | Mimir | Midgard | Chatbot RAG con knowledge base personal |
| 16 | [RuneBoard](plan-16-runeboard.md) | RuneBoard | Midgard | Kanban personal con runas nórdicas |

## Vanaheim — Agentes de IA

| # | Plan | Proyecto | Realm | Descripción |
|---|------|----------|-------|-------------|
| 07 | [CodeGhost](plan-07-codeghost.md) | CodeGhost | Vanaheim | Agente de code review autónomo |
| 08 | [DocWeaver](plan-08-docweaver.md) | DocWeaver | Vanaheim | Mantenedor de documentación viva |
| 09 | [ResearchHound](plan-09-researchhound.md) | ResearchHound | Vanaheim | Investigador autónomo multi-fuente |
| 10 | [PromptForge](plan-10-promptforge.md) | PromptForge | Vanaheim | Optimizador iterativo de prompts |

## Svartalfheim — Documentación y Conocimiento

| # | Plan | Proyecto | Realm | Descripción |
|---|------|----------|-------|-------------|
| 11 | [LoreKeeper](plan-11-lorekeeper.md) | LoreKeeper | Svartalfheim | Base de conocimiento conversacional (RAG) |
| 12 | [SkillTree](plan-12-skilltree.md) | SkillTree | Svartalfheim | Mapa interactivo de aprendizaje tipo RPG |

## Alfheim — Prototipos UI

| # | Plan | Proyecto | Realm | Descripción |
|---|------|----------|-------|-------------|
| 13 | [TerminalDashboard](plan-13-terminaldashboard.md) | TerminalDashboard | Alfheim | TUI dashboard del ecosistema Yggdrasil |
| 14 | [PixelForge](plan-14-pixelforge.md) | PixelForge | Alfheim | Editor de pixel art con paletas retro |
| 17 | [YggSiteGenerator](plan-17-yggsitegenerator.md) | YggSiteGenerator | Alfheim | Generador de sitio estático para GitHub Pages |

## Niflheim — Recursos y Assets

| # | Plan | Proyecto | Realm | Descripción |
|---|------|----------|-------|-------------|
| 18 | [ForgeMaster](plan-18-forgemaster.md) | ForgeMaster | Muspelheim | Gestión de modelos LLM, VRAM, y disk usage |

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
```

## Convenciones

- Cada plan está en `Svartalfheim/plans/plan-XX-nombre.md`
- Los proyectos se crean en el realm correspondiente: `Muspelheim/AutoSub/`, `Vanaheim/CodeGhost/`, etc.
- Todo proyecto usa: `pyproject.toml`, Typer CLI, Rich output, SQLite, pytest
- Los tests se configuran según `REGLAS_YGGDRASIL.md`
