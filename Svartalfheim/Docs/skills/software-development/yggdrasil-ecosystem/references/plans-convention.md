# Yggdrasil Implementation Plans Convention

## Location

All plans: `Svartalfheim/plans/plan-NN-projectname.md`
Master index: `Svartalfheim/plans/INDEX.md`

## Naming Convention

- Zero-padded numeric prefix: `plan-01-autosub.md`, `plan-02-clipforge.md`
- Project name in kebab-case matching the directory name
- INDEX.md contains realm-grouped tables, dependency graph, and conventions

## Plan Structure

Each plan file contains:

```markdown
# ProjectName — Short Description

> **For Hermes:** Use subagent-driven-development skill to implement this plan task-by-task.

**Goal:** One sentence.
**Architecture:** 2-3 sentences.
**Tech Stack:** Key technologies.
**Realm:** RealmName/ProjectName/

---

## Task 1: [Descriptive Name]
## Task 2: ...
## Task N: Tests + CI
```

## Plan-to-Realm Mapping

| Realm | Plans |
|-------|-------|
| Muspelheim | 01-AutoSub, 02-ClipForge, 03-TrendRadar |
| Midgard | 04-FinTracker, 05-HabitForge, 06-RecipeAlchemist, 15-Mimir, 16-RuneBoard |
| Vanaheim | 07-CodeGhost, 08-DocWeaver, 09-ResearchHound, 10-PromptForge |
| Svartalfheim | 11-LoreKeeper, 12-SkillTree |
| Alfheim | 13-TerminalDashboard, 14-PixelForge, 17-YggSiteGenerator |
| Niflheim | 18-ForgeMaster |

## Cross-Realm Dependencies

```
CodeGhost → DocWeaver (docs auto-repair)
ResearchHound → LoreKeeper (research → knowledge base)
LoreKeeper → Mimir (knowledge → chatbot)
PromptForge → Lilith (prompt optimization)
AutoSub → ComfyUI (subtitles → video pipeline)
ClipForge → TrendRadar (viral detection → trend monitoring)
ForgeMaster → TerminalDashboard (GPU monitoring data)
SkillTree → LoreKeeper (learning paths)
YggSiteGenerator → website/ (auto-build static site)
```

## Tech Stack Defaults

All Yggdrasil projects share these defaults unless there's a reason not to:
- CLI: Typer + Rich
- TUI (optional): Textual
- Storage: SQLite
- Testing: pytest
- Config: pyproject.toml with [project.scripts] entry points
- Pre-commit: ruff, black, trailing-whitespace, end-of-file-fixer, check-large-files (1MB max)