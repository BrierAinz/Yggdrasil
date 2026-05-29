<<<<<<< HEAD
# Arquitectura Yggdrasil - Documento Maestro

> **Version:** 2.0  
> **Fecha:** 2026-04-29  
> **Autor:** Völundr + Hermes  
> **Estado:** Post-Remasterizacion

---

## Vision Global

Yggdrasil es un ecosistema de desarrollo personal basado en la mitologia nordica. Cada uno de los 9 reinos tiene un proposito tecnico definido. Nada vive fuera de lugar.
=======
# Arquitectura Yggdrasil — Documento Maestro

> **Versión:** 3.0  
> **Fecha:** 2026-05-19  
> **Autor:** Völundr  
> **Estado:** Activo — Ecosistema v5.1.0

---

## Visión Global

Yggdrasil es un ecosistema de desarrollo personal basado en la mitología nórdica. Cada uno de los 9 reinos tiene un propósito técnico definido. Nada vive fuera de lugar.
>>>>>>> origin/main

---

## Mapa de Reinos (Estado Actual)

```
<<<<<<< HEAD
Yggdrasil/
|
|-- Asgard/          [CORE] Agentes CLI + monitoreo (4.5 GB, 516 py)
|-- Vanaheim/        [IA] Bots, agentes autonomos (442 KB, 64 py)
|-- Alfheim/         [UI] Prototipos visuales, electronica (47 KB, 1 js)
|-- Svartalfheim/    [DOCS] Conocimiento, guias, arquitectura (2 MB, 21 py)
|-- Muspelheim/      [WIP] Sprint mode, experimentos activos (5 KB, 4 files)
|-- Helheim/         [ARCHIVE] Legacy, cuarentena, cementerio (pesado)
|-- Niflheim/        [RESOURCES] Models, datasets, assets (4.3 GB, 12 files)
|-- Jotunheim/       [GIANT] Proyectos masivos >1 mes (reservado)
|-- Midgard/         [PERSONAL] Apps de uso diario (reservado)
=======
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
>>>>>>> origin/main
```

---

## Flujo de Vida de un Proyecto

```
<<<<<<< HEAD
[Idea] -> Muspelheim (sprint, 2 semanas max)
            |
            |-- Falla / Abandono -> Helheim (archivar)
            |
            |-- Valida -> [Reino Destino]
                 |
                 |-- Agente/IA -> Vanaheim
                 |-- Dashboard/Monitoreo -> Asgard
                 |-- App personal -> Midgard
                 |-- Prototipo UI -> Alfheim
                 |-- Proyecto >1 mes -> Jotunheim
                 |-- Documentacion -> Svartalfheim
                 |-- Assets/Models -> Niflheim
=======
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
>>>>>>> origin/main
```

---

## Dependencias Entre Reinos

```
<<<<<<< HEAD
Asgard (Lilith)
    |
    |-- [usa] Niflheim/Models/ (LLM local)
    |-- [usa] Svartalfheim/docs/ (guia de uso)
    |-- [usa] Vanaheim/tools/ (tools externos)
    |
Vanaheim (Bots)
    |
    |-- [usa] Niflheim/Models/ (modelos de IA)
    |-- [contribuye a] Svartalfheim/docs/ (documentacion)
    |
Alfheim (UI)
    |
    |-- [usa] Asgard/ (orquestar comandos)
    |-- [usa] Vanaheim/ (visualizar bots)
    |
Svartalfheim (Docs)
    |
    |-- [documenta] Todos los reinos
    |
Niflheim (Resources)
    |
    |-- [sirve a] Asgard, Vanaheim, Alfheim
=======
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
>>>>>>> origin/main
```

---

<<<<<<< HEAD
## Reglas de Oro (Post-Remasterizacion)

1. **Sin basura regenerable:** node_modules, pycache, .map, etc. van a cuarentena o se destruyen.
2. **Sin codigo duplicado:** Un modulo vive en un solo lugar. Los demas lo importan.
3. **Sin archivos sueltos:** Todo proyecto tiene README.md y estructura definida.
4. **Sin binarios sin fuente:** Si hay un .exe, debe haber codigo fuente o build script.
5. **Migracion explicita:** Todo cambio de reino se documenta en commit y README.

---

## Metricas de Salud (2026-04-29)

| Metrica | Antes | Despues |
|---------|-------|---------|
| Archivos totales | 62,272 | ~1,500 |
| Tamano total | ~11 GB | 8.8 GB |
| Basura | 60,000+ | 0 (en cuarentena) |
| Proyectos activos | 4 | 7 |
| Reinos vacios | 5 | 2 (Jotunheim, Midgard reservados) |
=======
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
>>>>>>> origin/main

---

## Puntos de Entrada

| Si quieres... | Ve a... |
|---------------|---------|
<<<<<<< HEAD
| Usar el agente CLI | Asgard/Hermes-Lilith/ |
| Entrenar/poner un bot | Vanaheim/Bots/ |
| Crear una UI | Alfheim/ui-seed/ |
| Leer documentacion | Svartalfheim/docs/ |
| Buscar un modelo LLM | Niflheim/Models/ |
| Ver codigo viejo | Helheim/Archives_Lilith_Legacy_2026-04-29/ |
| Iniciar un sprint | Muspelheim/ |

---

## Proximas Expansiones Planificadas

1. **Jotunheim:** Proyecto de ingestion de datos masiva o training de LLM
2. **Midgard:** Dashboard personal de productividad (calendario + tareas + metricas)
3. **Alfheim:** Orquestador visual con Electron + React
4. **Vanaheim:** Consolidar dependencias Python con requirements.txt unificado
5. **Asgard:** Refactor progresivo del monolito (123k LOC -> modulos)
=======
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
>>>>>>> origin/main

---

## Contacto

<<<<<<< HEAD
- **Issues / Bugs:** Crear nota en Svartalfheim/issues/
- **Solicitar remasterizacion:** Ejecutar Asgard/scripts/yggdrasil_health_check.py
- **Setup inicial:** Ejecutar setup_yggdrasil.py en raiz

---

*Yggdrasil crece con orden o no crece.*
=======
- **Issues / Bugs:** GitHub Issues en BrierAinz/Yggdrasil
- **Health check:** `python3 health_check.py` en raíz
- **Setup inicial:** `scripts/setup_yggdrasil.py`
- **CLI launcher:** `python3 yggdrasil_cli.py launch`

---

*Yggdrasil crece con orden o no crece.*
>>>>>>> origin/main
