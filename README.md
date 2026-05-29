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

---

## Quick Start

```bash
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
