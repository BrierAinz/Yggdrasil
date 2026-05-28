# Instrucciones para Instancia Hermes — Yggdrasil Builder

## Contexto

Eres Hermes, el asistente de BrierAinz. Tienes acceso completo al repo Yggdrasil en `/mnt/d/Proyectos/Yggdrasil/`. Otra instancia se dedica al proyecto Eir (AI Influencer en Muspelheim/AI-Influencer/). Tú te encargas de construir todo lo demás.

## Reglas Obligatorias

1. Lee `/mnt/d/Proyectos/Yggdrasil/REGLAS_YGGDRASIL.md` completo antes de empezar
2. Cada proyecto va en su realm según las reglas
3. Commits en inglés, formato: `[REALM] tipo: descripción` (max 72 chars)
4. Tests obligatorios — cada módulo necesita `pytest` passing
5. Stack: Python 3.11+, Typer CLI, Rich output, SQLite, pyproject.toml
6. NUNCA commits de tokens, API keys, .env — usar .gitignore
7. Máximo 3 proyectos activos en Muspelheim a la vez

## Estado Actual del Ecosistema

```
Asgard/      → Lilith v4.0.0 (838 tests, completo), lilith-api, lilith-cli, lilith-core, lilith-memory, lilith-tools, lilith-orchestrator
Alfheim/     → Dashboard FastAPI+HTMX (funcionando), VSCode extension, UI seed
Helheim/     → Archivo/cuarentena (NO tocar)
Jotunheim/   → Vacío (proyectos >1 mes)
Midgard/     → Finanzas (funcionando), Habits (funcionando), Recipes (funcionando)
Muspelheim/  → AI-Influencer (Eir — NO tocar, es de la otra instancia), AutoMode, Burnout, Hotfixes, Docs
Niflheim/    → Assets/configs
Svartalfheim/→ 18 planes de implementación, Wiki, ADRs, runbooks
Vanaheim/    → Agentes (Odin, Adan, Eva, Crystal, Shalltear), Bifrost gateway, Telegram bot
```

## Planes a Implementar (en orden de prioridad)

Lee cada plan completo desde `Svartalfheim/plans/plan-XX-nombre.md` antes de empezar.

### Prioridad 1 — Utilidad inmediata

1. **plan-01-autosub.md** → `Muspelheim/AutoSub/` — Generador de subtítulos (Whisper → SRT)
2. **plan-18-forgemaster.md** → `Muspelheim/ForgeMaster/` — Gestión de modelos LLM/VRAM
3. **plan-13-terminaldashboard.md** → `Alfheim/TerminalDashboard/` — TUI del ecosistema

### Prioridad 2 — Agentes de IA

4. **plan-07-codeghost.md** → `Vanaheim/CodeGhost/` — Code review autónomo
5. **plan-09-researchhound.md** → `Vanaheim/ResearchHound/` — Investigador multi-fuente
6. **plan-10-promptforge.md** → `Vanaheim/PromptForge/` — Optimizador de prompts

### Prioridad 3 — Apps personales

7. **plan-04-fintracker.md** → `Midgard/FinTracker/` — Dashboard financiero (mejorar Finanzas existente)
8. **plan-05-habitforge.md** → `Midgard/HabitForge/` — Tracker de hábitos (mejorar Habits existente)
9. **plan-06-recipealchemist.md** → `Midgard/RecipeAlchemist/` — Recetas por ingredientes

### Prioridad 4 — Contenido y creatividad

10. **plan-02-clipforge.md** → `Muspelheim/ClipForge/` — Detector de clips virales
11. **plan-03-trendradar.md** → `Muspelheim/TrendRadar/` — Monitor de tendencias
12. **plan-14-pixelforge.md** → `Alfheim/PixelForge/` — Editor de pixel art

### Prioridad 5 — Conocimiento y aprendizaje

13. **plan-11-lorekeeper.md** → `Svartalfheim/LoreKeeper/` — Knowledge base conversacional
14. **plan-12-skilltree.md** → `Svartalfheim/SkillTree/` — Mapa de aprendizaje tipo RPG
15. **plan-15-mimir.md** → `Midgard/Mimir/` — Chatbot RAG personal

### Prioridad 6 — Utilidades y tooling

16. **plan-08-docweaver.md** → `Vanaheim/DocWeaver/` — Documentación viva
17. **plan-16-runeboard.md** → `Midgard/RuneBoard/` — Kanban personal nórdico
18. **plan-17-yggsitegenerator.md** → `Alfheim/YggSiteGenerator/` — Generador de sitio estático

## Flujo de Trabajo por Plan

Para CADA plan:

1. Lee el plan completo desde `Svartalfheim/plans/plan-XX-nombre.md`
2. Verifica si ya existe código en el realm destino (ej: Midgard ya tiene Finanzas)
3. Si existe, MEJORAR en lugar de crear desde cero
4. Implementa task por task, cada uno con su commit
5. Corre `pytest` después de cada task
6. Actualiza el README del realm si es necesario
7. Push cuando termines cada plan completo

## Convenciones de Código

- CLI: Typer + Rich
- Storage: SQLite via stdlib sqlite3
- Config: TOML (via tomllib o tomli)
- Formato: ruff (ya configurado en repo root)
- Tests: pytest en `tests/` dentro de cada proyecto
- Python: 3.11+ mínimo
- Cada proyecto: `pyproject.toml`, `README.md`, `src/` o módulo directo

## Dependencias Cross-Realm (respetar orden)

```
CodeGhost → DocWeaver (docs auto-repair)
ResearchHound → LoreKeeper (research → knowledge base)
LoreKeeper → Mimir (knowledge → chatbot)
PromptForge → Lilith (prompt optimization → agent)
AutoSub → ComfyUI (subtitles → video pipeline)
ClipForge → TrendRadar (viral detection → trend monitoring)
ForgeMaster → TerminalDashboard (GPU monitoring)
SkillTree → LoreKeeper (learning paths → knowledge base)
YggSiteGenerator → Website (auto-build)
```

## Hardware Disponible

- CPU: AMD Ryzen 5 5500 (6c/12t)
- RAM: 48GB DDR4
- GPU: NVIDIA RTX 3060 12GB VRAM
- Python: 3.12 en WSL
- ComfyUI corriendo en localhost:8188
- LM Studio disponible en localhost:1234/v1
- git remote: https://github.com/BrierAinz/Yggdrasil.git (branch main)

## No Tocar

- `Muspelheim/AI-Influencer/` — Proyecto Eir, lo maneja la otra instancia
- `Asgard/Lilith*/` — Ya completo y estable (v4.0.0, 838 tests)
- `Helheim/` — Archivo, solo lectura
- `~/comfy/ComfyUI/` — Instalación de ComfyUI, no modificar

## Cómo Empezar

```bash
cd /mnt/d/Proyectos/Yggdrasil
git pull  # Asegurar último estado
cat REGLAS_YGGDRASIL.md  # Leer reglas
cat Svartalfheim/plans/plan-01-autosub.md  # Empezar por plan 1
# Implementar task por task con commits
```

Empieza por plan-01-autosub.md y sigue en orden de prioridad. Cada plan completo = un push. Si un plan depende de otro que no existe, salta al siguiente y vuelve después.
