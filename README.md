<<<<<<< HEAD
# Yggdrasil

**BrierStudios — The World Tree AI Ecosystem**

Yggdrasil es un ecosistema modular de IA y software organizado en 9 realms (reinos), cada uno con un proposito definido. Inspirado en la mitologia nordica, el proyecto sigue la arquitectura del Arbol del Mundo que conecta los nueve reinos.

**Version:** 5.1.0 | **Licencia:** MIT | **Python:** >=3.11

---

## Arquitectura: Los 9 Realms

```
Yggdrasil/
├── Asgard/          # Core — Paquetes lilith-* (infraestructura central)
├── Vanaheim/        # AI Agents — Frameworks y agentes autónomos
├── Alfheim/         # UI — Dashboards y interfaces visuales
├── Svartalfheim/    # Docs — Documentación, scripts, planes, wiki
├── Muspelheim/      # Dev/WIP — Proyectos en desarrollo activo
├── Niflheim/        # Assets — Modelos, datasets, recursos estaticos
├── Helheim/         # Archive — Proyectos muertos y cuarentena
├── Jotunheim/       # Massive — Proyectos de gran escala (futuro)
└── Midgard/         # Personal — Proyectos personales y scripts
```

### Asgard — Core Infrastructure

El corazon de Yggdrasil. Contiene los 8 paquetes `lilith-*` que forman la infraestructura base.

| Paquete | Version | Estado | Descripcion |
|---------|---------|--------|-------------|
| **lilith-core** | 2.1.0 | Activo | Tipos base, configuración, logging, proveedores LLM |
| **lilith-memory** | 1.0.0 | Activo | Store de memoria vectorial con backend SQLite |
| **lilith-api** | 1.0.0 | Esqueleto | FastAPI Gateway con soporte WebSocket |
| **lilith-bridge** | 1.0.0 | Esqueleto | Puente entre Lilith y servicios externos (Telegram, Discord) |
| **lilith-cli** | 3.0.0 | Esqueleto | Interfaz de terminal para el ecosistema |
| **lilith-orchestrator** | 1.0.0 | Esqueleto | Coordinacion de agentes y orquestacion de tareas |
| **lilith-skills** | 1.0.0 | Esqueleto | Gestion y descubrimiento de skills |
| **lilith-tools** | 1.0.0 | Esqueleto | Control de PC, automatizacion de navegador, herramientas RAG |

**Modulos activos (lilith-core):**
- `config.py` — Configuracion centralizada del ecosistema
- `types.py` — Tipos base y dataclasses
- `logger.py` — Logging estructurado
- `providers.py` — Gestion de proveedores LLM (multi-provider)

**Modulos activos (lilith-memory):**
- `store.py` — Store de memoria con SQLite y busqueda por embeddings

### Vanaheim — AI Agents

| Proyecto | Estado | Descripcion |
|----------|--------|-------------|
| **bifrost** | Esqueleto | Puente entre agentes y servicios externos |
| **vanaheim-framework** | Esqueleto | Framework base para agentes autonomos |

### Alfheim — UI / Interfaces

| Proyecto | Estado | Descripcion |
|----------|--------|-------------|
| TerminalDashboard | Referenciado | Dashboard de terminal (en pyproject workspace) |
| YggdrasilForge | Referenciado | Herramienta de construccion (en pyproject workspace) |

### Svartalfheim — Documentacion y Scripts

El reino del conocimiento. Aqui vive toda la documentacion, planes, scripts de automatizacion y la memoria ancestral del ecosistema.

```
Svartalfheim/
├── Docs/                    # Documentacion principal
│   ├── API.md               # Documentacion de la API
│   ├── ARCHITECTURE.md      # Arquitectura detallada
│   ├── TUTORIALS.md         # Tutoriales de uso
│   ├── architecture.html    # Diagrama interactivo
│   ├── github-presence-guide.md  # Guia de presencia en GitHub
│   ├── profile-readme.md    # README de perfil GitHub
│   ├── social-preview.svg   # Preview social
│   └── *.md                 # Docs de arquitectura, RAG, instancias
├── Knowledge_Base/          # Base de conocimiento
│   ├── Lilith_Docs/         # Documentacion activa de Lilith (101 archivos)
│   └── Lilith_Legacy/       # Conocimiento heredado del monolito
├── Scripts/                 # Scripts de automatizacion (22 archivos)
│   ├── ask_archivero.py     # Consulta al archivero RAG
│   ├── index_docs_to_muninn.py  # Indexacion de documentos
│   ├── health_check.sh      # Verificacion de salud
│   └── test_*.py            # Suite de tests
├── plans/                   # Planes de implementacion (21 planes)
│   ├── plan-01-autosub.md   # Plan: Generador automatico de subtitulos
│   ├── plan-02-clipforge.md # Plan: Herramienta de clips
│   ├── plan-13-terminal-dashboard.md
│   └── plan-NN-*.md         # Mas planes...
├── wiki/                    # ADRs, features, runbooks, templates
├── notes/                   # Notas rapidas
│   └── quick-notes.md       # Notas de trabajo (69KB)
└── REGLAS.md                # Leyes del reino
```

### Muspelheim — Desarrollo Activo

| Proyecto | Estado | Descripcion |
|----------|--------|-------------|
| **Horror-GameMaster** | Fases 1-4 DONE | Motor de terror procedural con IA |

**Horror-GameMaster** es el proyecto principal de Muspelheim:
- Motor de juego de terror procedural con generacion procedural de eventos
- Dataset de 2,200+ entradas JSONL (v3 generacion activa, 19 modelos)
- 8 modulos, 84 tests
- Scripts: `generate_v2.py`, `generate_v3.py` (rotacion BytePlus + MiMo)
- Fases completadas: 1 (Dataset), 2 (Motor de Terror), 3 (Integracion LLM), 4 (Frontend)

### Niflheim — Assets

Recursos estaticos: modelos, datasets, archivos grandes. Solo README actualmente.

### Helheim — Archivo

Proyectos muertos o en cuarentena. Solo lectura.

| Proyecto | Fecha | Causa |
|----------|-------|-------|
| kohya_ss | 2026-05-21 | Eliminado del monorepo (LoRA training, ahora externo) |
| Lilith monolito v5.0 | 2026-05-21 | Migrado a modulos (reemplazado por 8 paquetes lilith-*) |
| AI-Influencer | — | Archivado |
| AutoSub | — | Archivado |
| ForgeMaster | — | Archivado |

### Jotunheim — Massive (Futuro)

Reservado para proyectos de gran escala. Solo README actualmente.

### Midgard — Personal

| Proyecto | Descripcion |
|----------|-------------|
| scripts/ | Scripts personales |

---

## CLI — Interfaces de Linea de Comandos

Yggdrasil tiene 3 CLI distintas:

### 1. `ygg.py` — CLI Principal (Nordic Theme)

CLI principal con tema Nordic Frost. Interfaz rica con Rich library.

```bash
python ygg.py                    # Menu interactivo
python ygg.py status             # Estado de los reinos
python ygg.py tree               # Arbol de proyectos
python ygg.py size               # Tamano por reino
```

**Tema visual:** Nordic Frost palette, Elder Futhark runes, animaciones.

### 2. `yggdrasil_cli.py` — CLI de Gestion

Herramienta de administracion del ecosistema.

```bash
python yggdrasil_cli.py launch   # Menu interactivo
python yggdrasil_cli.py status   # Estado de salud
python yggdrasil_cli.py clean    # Limpiar archivos regenerables
python yggdrasil_cli.py backup   # Backup de Svartalfheim + configs
python yggdrasil_cli.py tree     # Arbol de proyectos
python yggdrasil_cli.py test     # Ejecutar pytest
python yggdrasil_cli.py health   # Verificar README.md en cada reino
python yggdrasil_cli.py migrate  # Migrar proyecto entre reinos
python yggdrasil_cli.py update   # Git pull + deps
```

### 3. `lilith_agent.py` — Agente IA

Agente de codigo completo con memoria, skills, pensamiento autonomo y ejecucion de codigo. Inspirado en Hermes Agent / Claude Code.

```bash
python lilith_agent.py           # Iniciar agente
```

**Capacidades:**
- Memoria persistente (SQLite)
- Gestion de skills
- Ejecucion de comandos
- Acceso web
- Tema Nordic Frost

### 4. `lilith_cli.py` — CLI del Ecosistema Lilith

Interfaz de terminal para el ecosistema Lilith con chat, memoria y comandos.

```bash
python lilith_cli.py chat        # Chat con Lilith
```

**Comandos del chat:**
- `ayuda` — Mostrar ayuda
- `resumen` — Resumen de la conversacion
- `memoria` — Ultimas entradas de memoria
- `borrar` — Borrar memoria
- `salir` — Terminar

---

## Servicios

| Servicio | Puerto | Paquete | Descripcion |
|----------|--------|---------|-------------|
| API Gateway | 8000 | lilith-orchestrator/gateway | REST API principal |
| Model Orchestrator | 8001 | lilith-orchestrator | Gestion de modelos LLM |
| Memory Service | 8002 | lilith-memory | Servicio de memoria vectorial |

---

## Scripts de Automatizacion

Scripts principales en `Scripts/` y `Svartalfheim/Scripts/`:

| Script | Descripcion |
|--------|-------------|
| `ask_archivero.py` | Consulta al sistema RAG Archivero |
| `index_docs_to_muninn.py` | Indexa documentos a Muninn vault |
| `setup_docs_vault.py` | Configura el vault de documentacion |
| `generate_docs_metadata.py` | Genera metadatos de documentacion |
| `health_check.sh` | Verificacion de salud del ecosistema |
| `test_*.py` | Suite de tests (API, busqueda, LLM, etc.) |

---

## Herramientas del Proyecto

| Archivo | Descripcion |
|---------|-------------|
| `advanced_memory.py` | Memoria con embeddings y busqueda semantica |
| `auto_improvement.py` | Sistema de automejora inteligente |
| `skill_creator.py` | Autocreacion de skills desde conversaciones |
| `agent_permissions.py` | Gestion de permisos de agentes |
| `health_check.py` | Verificacion de salud del sistema |
| `update_architecture.py` | Actualizacion del manifiesto de arquitectura |
| `validate_architecture.py` | Validacion de la arquitectura |
| `verificar_yggdrasil.py` | Verificacion completa del ecosistema |
=======
<div align="center">

# 🌳 Yggdrasil

> *"Del caos del vacio, Yggdrasil crece con raices profundas y ramas que tocan todos los cielos."*

**A personal project ecosystem organized under the Norse Nine Realms metaphor.**

[![License: MIT](https://img.shields.io/badge/License-MIT-f59e0b.svg)](LICENSE)
[![Python 3.10+](https://img.shields.io/badge/Python-3.10+-22d3ee.svg)](https://python.org)
[![Status](https://img.shields.io/badge/Status-Active-34d399.svg)]()
[![GitHub Stars](https://img.shields.io/github/stars/BrierAinz/Yggdrasil?style=flat&color=fbbf24)](https://github.com/BrierAinz/Yggdrasil/stargazers)
[![GitHub Last Commit](https://img.shields.io/github/last-commit/BrierAinz/Yggdrasil?color=a78bfa)](https://github.com/BrierAinz/Yggdrasil/commits/main)
[![Repo Size](https://img.shields.io/github/repo-size/BrierAinz/Yggdrasil?color=fb7185)](https://github.com/BrierAinz/Yggdrasil)
[![CI](https://github.com/BrierAinz/Yggdrasil/actions/workflows/ci.yml/badge.svg)](https://github.com/BrierAinz/Yggdrasil/actions/workflows/ci.yml)
[![Deploy](https://github.com/BrierAinz/Yggdrasil/actions/workflows/deploy-website.yml/badge.svg)](https://github.com/BrierAinz/Yggdrasil/actions/workflows/deploy-website.yml)
[![Security](https://img.shields.io/badge/Security-Policy-blue.svg)](SECURITY.md)
[![PRs Welcome](https://img.shields.io/badge/PRs-Welcome-brightgreen.svg)](CONTRIBUTING.md)

[Website](https://brierainz.github.io/Yggdrasil) · [Setup](#quick-start) · [Architecture](#architecture) · [Realms](#the-nine-realms) · [Docs](#documentation)

</div>

---

## What is Yggdrasil?

Yggdrasil is not a monorepo — it is a **living ecosystem** where every project has a purpose, a lifecycle, and a destination realm. Inspired by Norse cosmology, each of the **Nine Realms** serves a distinct function in the development lifecycle.

The crown jewel is **Lilith**: a local-first AI agent that runs entirely on your hardware via LM Studio, with no cloud lock-in. Control it from anywhere through Telegram. It remembers conversations with vector embeddings, delegates tasks to sub-agents, schedules jobs, and can literally control your PC.

### Key Principles

- **Every project lives in exactly one realm** at any time. No duplicates, no chaos.
- **Strict lifecycle**: Idea → Muspelheim → [Target Realm] → Helheim (if it dies).
- **Local-first AI**: The LLM runs on your machine. Your data never leaves.
- **Single owner**: Designed for personal use. Telegram bot only responds to you.
>>>>>>> origin/main

---

## Quick Start

```bash
<<<<<<< HEAD
# Clonar
git clone <repo-url>
cd Yggdrasil

# Setup
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"

# Ejecutar CLI
python ygg.py

# Ejecutar tests
pytest
```

---

## Estructura de Workspace (uv)

El proyecto usa `uv` como gestor de workspace con los siguientes miembros:

```toml
[tool.uv.workspace]
members = [
    "Asgard/lilith-core",
    "Asgard/lilith-memory",
    "Asgard/lilith-tools",
    "Asgard/lilith-orchestrator",
    "Asgard/lilith-api",
    "Asgard/lilith-cli",
    "Asgard/lilith-skills",
    "Asgard/lilith-bridge",
    ...
]
```

---

## Documentacion

- [Arquitectura](Docs/ARQUITECTURA_YGGDRASIL.md) — Diseno de los 9 realms
- [API](Svartalfheim/Docs/API.md) — Documentacion de la API
- [Tutoriales](Svartalfheim/Docs/TUTORIALS.md) — Guia de uso
- [Ecosystem Research](Docs/ecosystem-research-findings.md) — Investigacion del ecosistema
- [Planes](Docs/plans/) — Planes de implementacion (21 planes)
- [Knowledge Base](Knowledge_Base/) — Base de conocimiento Lilith
- [Changelog](CHANGELOG.md) — Historial de cambios
- [Contributing](CONTRIBUTING.md) — Guia de contribucion
- [Security](SECURITY.md) — Politica de seguridad

---

## BrierStudios

Proyecto mantenido por **BrierStudios** — Dark Fantasy x AI.

---
*Ultima actualizacion: 2026-05-29*
=======
# Clone the tree
git clone https://github.com/BrierAinz/Yggdrasil.git
cd Yggdrasil

# Configure environment
cp Asgard/Lilith/.env.example Asgard/Lilith/.env
# Edit .env with your Telegram bot token, chat ID, and model settings

# Start LM Studio with a loaded model on localhost:1234

# Launch everything
start_lilith.bat        # Windows
# Or manually:
#   cd Asgard/lilith-orchestrator/gateway && uvicorn gateway:app --port 8000
#   cd Vanaheim/Bots_Lilith_v5/telegram && python bot.py
```

<details>
<summary><b>📦 Alternative: GitHub Codespaces</b></summary>

Click the **Code** button on the repo page and select **Codespaces** → **Create codespace on main**. The devcontainer will auto-install Python 3.11, all dependencies, and pre-commit hooks.

You'll still need to set up:
1. LM Studio running locally (or configure a remote LLM endpoint)
2. A `.env` file with your `TELEGRAM_BOT_TOKEN` and `CHAT_ID`

</details>

<details>
<summary><b>🐍 Manual Python Setup</b></summary>

```bash
# Create virtual environment
python -m venv .venv
source .venv/bin/activate  # Linux/macOS
# .venv\Scripts\activate   # Windows

# Install all Lilith modules
pip install -e Asgard/lilith-core \
    -e Asgard/lilith-memory \
    -e Asgard/lilith-tools \
    -e Asgard/lilith-orchestrator \
    -e Asgard/lilith-api \
    -e Asgard/lilith-cli \
    -e Vanaheim/vanaheim-framework

# Or use the setup script
bash setup.sh

# Run tests
pytest

# Format & lint
pre-commit install
pre-commit run --all-files
```

</details>

---

## The Nine Realms

| Realm | Purpose | Key Projects |
|-------|---------|-------------|
| 🏰 **Asgard** | Core Technology | Lilith v5 (agent), Swarm, API, Memory, Tools, CLI, Gateway |
| 🤖 **Vanaheim** | AI Agents | Telegram Bot (Bifrost), VanirAgent Framework, Agent Pantheon |
| ✨ **Alfheim** | UI Prototypes | HTMX Dashboard (stable), TerminalDashboard (TUI), VSCode Extension |
| 📚 **Svartalfheim** | Knowledge Base | Docs, Playbooks, ADRs, Architecture Decisions |
| 🔥 **Muspelheim** | Active Development | AI Influencer (Eir), AutoSub (complete), ForgeMaster |
| ❄️ **Niflheim** | Resources & Tools | Datasets, Models, Configs |
| 🌍 **Midgard** | Personal Apps | Finanzas, HabitForge, RecipeAlchemist |
| 🐉 **Jotunheim** | Massive Projects | Long-term builds (>1 month) — currently empty |
| ☠️ **Helheim** | Graveyard | Archived: Lilith Legacy Monolith (814MB tar.gz) |

[Explore all realms →](https://brierainz.github.io/Yggdrasil/realms.html)

---

## Architecture

```
You (Telegram)
      ↓
Telegram Bot  ---------→  VSCode Ext  ---------→  CLI
      ↓                        ↓                  ↓
      ┌────────────────────────────────────────────┐
      │            Gateway (FastAPI :8000)           │
      └────────────────────────────────────────────┘
                          ↓
      ┌────────────────────────────────────────────┐
      │         Lilith Orchestrator (v5)             │
      │  ┌──────┐ ┌──────┐ ┌──────┐ ┌──────┐       │
      │  │Memory│ │Agents│ │Sched.│ │Plugin│       │
      │  └──────┘ └──────┘ └──────┘ └──────┘       │
      └────────────────────────────────────────────┘
                          ↓
                    LM Studio (localhost:1234)
```

[Full architecture details →](docs/architecture.html)

---

## Lilith Features

| Feature | Description |
|---------|-------------|
| 🔍 **Vector Memory** | Sentence-transformer embeddings + SQLite. Auto-compression, entity extraction, semantic retrieval. |
| 🤖 **Sub-Agent Delegation** | Spawn autonomous coding agents with isolated contexts for parallel workstreams. |
| 🐝 **Swarm Coordination** | Multi-agent orchestration with MessageBus, conflict resolution, and parallel task execution. |
| 📅 **Task Scheduler** | Cron-like scheduling with persistent SQLite backend and REST API. |
| 🔑 **PC Control** | File system, process management, Windows automation, browser, screenshots. |
| 📚 **RAG Pipeline** | Document ingestion, chunking, embedding, semantic search for knowledge bases. |
| 🚀 **Plugin System** | Hot-pluggable tools with dynamic discovery and runtime enable/disable. |
| 📱 **Telegram Control** | Remote interface from anywhere. Owner-only access. |
| 🔄 **Batch Mode** | Run prompts from CLI with `--batch` flag for automation pipelines. |

<details>
<summary><b>🔍 Technical Architecture Details</b></summary>

### Modular Package Structure (v5)

Lilith is built as a modular package ecosystem:

| Package | Purpose | Key Exports |
|---------|---------|-------------|
| `lilith-core` | Base types, config, logging | `LilithConfig`, `LilithBase` |
| `lilith-memory` | Vector memory + SQLite | `EnhancedMemory`, `EntityTracker` |
| `lilith-tools` | PC control, browser, RAG | `ToolRegistry`, `FileSystemTool` |
| `lilith-orchestrator` | Agent coordination | `Orchestrator`, `AgentConfig` |
| `lilith-api` | FastAPI Gateway + WebSocket | `Gateway`, health endpoints |
| `lilith-cli` | Terminal interface | `LilithCLI`, batch mode |

### Dual Layout

Lilith exists in two versions within Asgard:
- **`Asgard/Lilith/`** — Refactored v5 (active, modular packages)
- **`Asgard/Hermes-Lilith/`** — Legacy v4 monolith (archived, not renamed for git history)

### Swarm Coordination

Two implementations exist:

| Location | Version | Architecture |
|----------|---------|-------------|
| `Hermes-Lilith/Lilith/Swarm/` | v4 Legacy | agent, manager, message_bus, conflict_resolver, executor, database |
| `Lilith/src/core/agents/swarm/` | v5 Refactored | swarm, coordinator, task_planner, base, complexity_router, fallback_chain, output_validator, review_chain |

</details>

See the [Lilith agent specs](https://brierainz.github.io/Yggdrasil/lilith.html) for full details.

---

## Hardware Requirements

| Tier | RAM | GPU | Models | Performance |
|------|-----|-----|--------|-------------|
| Minimum | 16GB | — | 7B (Q4) | Functional |
| Recommended | 32GB+ | 4GB+ VRAM | 13-27B | Fast, good context |
| Reference | 48GB DDR4 | RTX 3060 12GB | Up to 27B | Comfortable |

---

## Development

```bash
# Run tests
pytest

# Format code
pre-commit install
pre-commit run --all-files
```

<details>
<summary><b>🧪 Testing Details</b></summary>

The test suite runs across all Lilith modules:

```bash
# Run all tests
pytest

# Run specific module tests
pytest Asgard/lilith-core/tests     # Core functionality
pytest Asgard/lilith-memory/tests    # Memory & embeddings
pytest Asgard/lilith-tools           # Tools & PC control
pytest Asgard/lilith-orchestrator    # Agent orchestration
pytest Asgard/lilith-api/tests       # API endpoints
pytest Asgard/lilith-cli/tests       # CLI interface
pytest Vanaheim/vanaheim-framework   # Agent framework
```

CI runs on every push to `main` with ruff linting, pytest, and pyright type checking.

</details>

---

## Documentation

| Doc | Description |
|-----|-------------|
| [API Reference](docs/API.md) | Complete HTTP and WebSocket endpoint documentation |
| [Architecture](docs/ARCHITECTURE.md) | System diagrams, data flow, and deployment topology |
| [Tutorials by Realm](docs/TUTORIALS.md) | Step-by-step guides for each of the Nine Realms |
| [Changelog](CHANGELOG.md) | Version history and release notes |
| [Contributing](CONTRIBUTING.md) | How to contribute, realm rules, and PR guidelines |
| [Security](SECURITY.md) | Vulnerability reporting and security policy |

---

## Contributing

We welcome contributions! Whether you're fixing a bug, adding a feature, or improving documentation, please read our [Contributing Guide](CONTRIBUTING.md) first.

Key points:
- Every project belongs to exactly one **Realm** — check `REGLAS_YGGDRASIL.md` for the rules
- Use the [bug report](https://github.com/BrierAinz/Yggdrasil/issues/new?template=bug_report.yml) or [feature request](https://github.com/BrierAinz/Yggdrasil/issues/new?template=feature_request.yml) templates
- All PRs must pass CI (ruff lint, pytest, pyright)
- New projects start in **Muspelheim** — the realm of active development

---

## License

MIT — See [LICENSE](LICENSE) for details.

---

<div align="center">

🌳 **Built with patience in the Nine Realms.**

[Website](https://brierainz.github.io/Yggdrasil) · [GitHub](https://github.com/BrierAinz/Yggdrasil) · [Issues](https://github.com/BrierAinz/Yggdrasil/issues) · [Discussions](https://github.com/BrierAinz/Yggdrasil/discussions)

</div>
>>>>>>> origin/main
