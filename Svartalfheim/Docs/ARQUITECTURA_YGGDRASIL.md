# Arquitectura Yggdrasil — Documento Maestro

> **Versión:** 3.0  
> **Fecha:** 2026-05-19  
> **Autor:** Völundr  
> **Estado:** Activo — Ecosistema v5.1.0

---

## Visión Global

Yggdrasil es un ecosistema de desarrollo personal basado en la mitología nórdica. Cada uno de los 9 reinos tiene un propósito técnico definido. Nada vive fuera de lugar.

---

## Mapa de Reinos (Estado Actual)

```
Yggdrasil/                          # Root — uv workspace (v5.1.0)
│
├── Asgard/                         # Core technology
│   ├── lilith-core/                #   Config, types, base classes (v2.0.0)
│   ├── lilith-memory/              #   SQLite vector store (v2.0.0)
│   ├── lilith-tools/               #   Tool registry + implementations (v2.0.0)
│   ├── lilith-orchestrator/        #   Gateway server (v1.0.0)
│   ├── lilith-api/                 #   Public API — FastAPI, DI, orjson (v2.2.0)
│   ├── lilith-cli/                 #   CLI agent (Cyclopts) + TUI (Textual) (v3.0.0)
│   ├── lilith-skills/              #   Skill definitions + personality (v1.0.0)
│   ├── lilith-bridge/              #   Hermes↔Yggdrasil gateway (v1.0.0)
│   └── Lilith/                     #   Legacy monolith (archived → Helheim)
│
├── Alfheim/                         # UI prototypes
│   ├── dashboard/                  #   HTMX + Alpine.js + Jinja2 dashboard (v1.0.0)
│   ├── TerminalDashboard/           #   Textual TUI (v1.0.0, 188 tests, 81% coverage)
│   ├── YggdrasilForge/            #   Viking 3D Asset Studio (v0.1.0, 62 tests)
│   └── YggdrasilStudio/            #   AI image generation studio (v0.3.0)
│
├── Svartalfheim/                    # Documentation & knowledge base
│   └── Docs/                        #   Plans, research, architecture docs
│
├── Vanaheim/                        # AI agents framework
│   ├── Agents/                      #   5 active: Shalltear, Adán, Eva, Odín, Mimir
│   ├── bifrost/                     #   Bifrost Gateway (FastAPI + JWT)
│   └── Core/                        #   Framework core (models, registry, memory)
│
├── Muspelheim/                      # Active development / WIP
│   ├── AutoSub/                    #   Automatic subtitle generator (v0.1.0, COMPLETE)
│   ├── AI-Influencer/              #   Eir LoRA training pipeline (FASE 0)
│   ├── ForgeMaster/                #   LLM model/VRAM/disk manager (v1.0.0, 250 tests)
│   └── AutoMode/                   #   Templates and automation modes
│
├── Niflheim/                        # Resources & assets (NO code)
├── Helheim/                         # Graveyard / archive
├── Jotunheim/                       # Massive projects (empty, reserved)
└── Midgard/                         # Personal apps (Finanzas, Habits, Recipes)
```

---

## Flujo de Vida de un Proyecto

```
[Idea] → Muspelheim (sprint, 2 semanas max)
            │
            ├─ Falla / Abandono → Helheim (archivar)
            │
            └─ Valida → [Reino Destino]
                 │
                 ├─ Agente/IA → Vanaheim
                 ├─ Dashboard/Monitoreo → Alfheim
                 ├─ App personal → Midgard
                 ├─ Proyecto >1 mes → Jotunheim
                 ├─ Documentación → Svartalfheim
                 └─ Assets/Models → Niflheim
```

---

## Dependencias Entre Reinos

```
Asgard (Lilith Core + API)
    │
    ├─ [usa] Niflheim/Models/ (LLM local)
    ├─ [usa] Svartalfheim/docs/ (guía de uso)
    └─ [usa] Vanaheim/tools/ (tools externos)

Vanaheim (Agentes)
    │
    ├─ [usa] Niflheim/Models/ (modelos de IA)
    └─ [contribuye a] Svartalfheim/docs/ (documentación)

Alfheim (UI)
    │
    ├─ [usa] Asgard/ (API, orquestación)
    └─ [visualiza] Vanaheim/ (estado de agentes)

Svartalfheim (Docs)
    │
    └─ [documenta] Todos los reinos

Niflheim (Resources)
    │
    └─ [sirve a] Asgard, Vanaheim, Alfheim
```

---

## Tooling Stack

| Tool | Purpose | Command |
|------|---------|---------|
| uv | Package manager (workspace) | `uv sync`, `uv pip install` |
| poethepoet | Task runner | `poe test`, `poe lint`, `poe dashboard` |
| ruff | Linter + formatter | `ruff check .`, `ruff format .` |
| pytest | Testing | `pytest` |
| Cyclopts | CLI framework | Type-hint subcommands |
| Rich | Terminal formatting | Tables, trees, progress bars |
| Textual | TUI framework | `lilith_cli.tui.app` |
| HTMX + Alpine.js | Web dashboard | No build pipeline |
| orjson | Fast JSON serialization | Auto-detected in lilith-api |

---

## Reglas de Oro (Post-Remasterización)

1. **Sin basura regenerable:** `node_modules`, `__pycache__`, `.map`, etc. van a cuarentena o se destruyen.
2. **Sin código duplicado:** Un módulo vive en un solo lugar. Los demás lo importan.
3. **Sin archivos sueltos:** Todo proyecto tiene `README.md` y `pyproject.toml`.
4. **Sin binarios sin fuente:** Si hay un `.exe`, debe haber código fuente o build script.
5. **Migración explícita:** Todo cambio de reino se documenta en commit y README.
6. **Commit prefix:** `[REALM] type(scope): description` — ej: `[ASGARD] feat(lilith-core): add memory store`

---

## Métricas de Salud (2026-05-19)

| Métrica | Valor Actual |
|---------|-------------|
| Paquetes workspace | 15 |
| Tests pasando | 65+ (Asgard) + 250 (ForgeMaster) + 188 (TerminalDashboard) + 89 (AutoSub) |
| Ruff check | ✅ All clean |
| Ruff format | ✅ All clean |
| Paquetes con pyproject.toml | 15 (todos los sub-paquetes) |
| Agentes activos | 5 (Shalltear, Adán, Eva, Odín, Mimir) |
| Proyectos completados | AutoSub, ForgeMaster, TerminalDashboard, Dashboard HTMX |

---

## Puntos de Entrada

| Si quieres... | Ve a... |
|---------------|---------|
| Usar el agente CLI | `Asgard/lilith-cli/` (Cyclopts v4 + TUI) |
| Iniciar la API | `uvicorn lilith_api.main:app --port 8000` |
| Entrenar/poner un bot | `Vanaheim/Agents/` |
| Crear una UI | `Alfheim/dashboard/` (HTMX) o `Alfheim/TerminalDashboard/` (Textual) |
| Leer documentación | `Svartalfheim/Docs/` |
| Buscar un modelo LLM | `Muspelheim/ForgeMaster/` (CLI de gestión) |
| Ver código legacy | `Helheim/Hermes-Lilith_v4_legacy/` |
| Iniciar un sprint | `Muspelheim/` |

---

## Próximas Expansiones Planificadas

1. **Jotunheim:** Proyecto de ingesta de datos masiva o training de LLM
2. **Midgard:** Apps personales con pyproject.toml (FinTracker, HabitForge)
3. **Alfheim:** YggdrasilStudio v0.4 (video gen, WS bridge), YggdrasilForge v0.1
4. **Vanaheim:** Agentes Mimir (research), CodeGhost (code review)
5. **Asgard:** Swarm v5 progressive refactor

---

## Contacto

- **Issues / Bugs:** GitHub Issues en BrierAinz/Yggdrasil
- **Health check:** `python3 health_check.py` en raíz
- **Setup inicial:** `scripts/setup_yggdrasil.py`
- **CLI launcher:** `python3 yggdrasil_cli.py launch`

---

*Yggdrasil crece con orden o no crece.*