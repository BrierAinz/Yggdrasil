# The Nine Realms

Guia completa de los 9 realms de Yggdrasil. Cada reino tiene un proposito definido en el ecosistema.

---

## Asgard — Core Infrastructure

**Proposito:** Infraestructura central del ecosistema.

Asgard contiene los 8 paquetes `lilith-*` que forman la base de Yggdrasil. Es el corazon del sistema.

### Paquetes Activos

| Paquete | Version | Descripcion |
|---------|---------|-------------|
| **lilith-core** | 2.1.0 | Tipos base, configuracion, logging, proveedores LLM |
| **lilith-memory** | 1.0.0 | Store de memoria vectorial con backend SQLite |

**lilith-core** modulos:
- `config.py` — Configuracion centralizada
- `types.py` — Tipos base y dataclasses
- `logger.py` — Logging estructurado
- `providers.py` — Gestion multi-provider de LLMs

**lilith-memory** modulos:
- `store.py` — Store de memoria con SQLite y busqueda por embeddings

### Paquetes Esqueleto

| Paquete | Descripcion |
|---------|-------------|
| lilith-api | FastAPI Gateway con WebSocket |
| lilith-bridge | Puente a Telegram/Discord |
| lilith-cli | Interfaz de terminal |
| lilith-orchestrator | Coordinacion de agentes |
| lilith-skills | Gestion de skills |
| lilith-tools | PC control, browser, RAG |

Estos paquetes tienen `pyproject.toml` + `__init__.py` pero sin logica implementada.

---

## Vanaheim — AI Agents

**Proposito:** Frameworks para agentes autonomos.

| Proyecto | Estado | Descripcion |
|----------|--------|-------------|
| bifrost | Esqueleto | Puente de comunicacion entre agentes |
| vanaheim-framework | Esqueleto | Framework base para agentes |

---

## Alfheim — UI / Interfaces

**Proposito:** Dashboards, interfaces visuales, frontend.

| Proyecto | Estado | Descripcion |
|----------|--------|-------------|
| TerminalDashboard | Referenciado | Dashboard de terminal |
| YggdrasilForge | Referenciado | Herramienta de construccion |

---

## Svartalfheim — Documentacion y Scripts

**Proposito:** Conocimiento, planes, scripts, wiki.

El reino de los enanos oscuros. Aqui vive toda la documentacion del ecosistema.

### Estructura

```
Svartalfheim/
├── Docs/                    # Documentacion principal
│   ├── API.md               # Documentacion de la API
│   ├── ARCHITECTURE.md      # Arquitectura detallada
│   ├── TUTORIALS.md         # Tutoriales
│   └── *.md                 # Docs de arquitectura, RAG, instancias
├── Knowledge_Base/          # Base de conocimiento
│   ├── Lilith_Docs/         # Documentacion activa (101 archivos)
│   └── Lilith_Legacy/       # Conocimiento heredado
├── Scripts/                 # Scripts de automatizacion (22 archivos)
│   ├── ask_archivero.py     # Consulta al archivero RAG
│   ├── index_docs_to_muninn.py  # Indexacion de documentos
│   ├── health_check.sh      # Verificacion de salud
│   └── test_*.py            # Suite de tests
├── plans/                   # Planes de implementacion (21 planes)
└── wiki/                    # ADRs, features, runbooks, templates
```

### Reglas

1. Documentacion y scripts, nada mas.
2. Los scripts residen en `Scripts/`.
3. Los planes siguen el formato `plan-NN-*.md`.
4. La wiki es sagrada (ADRs, runbooks, features, templates).
5. `Lilith_Docs` es la fuente viva.
6. `Lilith_Legacy` es de solo consulta.

---

## Muspelheim — Desarrollo Activo

**Proposito:** Proyectos en desarrollo, experimentos, WIP.

Maximo 4 proyectos activos simultaneamente.

### Horror-GameMaster (Activo)

Motor de juego de terror procedural con IA:

- **Dataset:** 2,200+ entradas JSONL (v3 generacion activa, 19 modelos)
- **Tests:** 84 tests
- **Modulos:** 8 modulos
- **Fases completadas:**
  - Fase 1: Dataset base
  - Fase 2: Motor de Terror
  - Fase 3: Integracion LLM
  - Fase 4: Frontend
- **Scripts:** `generate_v2.py`, `generate_v3.py` (rotacion BytePlus + MiMo)

### Estructura

```
Muspelheim/
├── Horror-GameMaster/
│   ├── data/          # Datasets JSONL
│   ├── deploy/        # Configuracion de despliegue
│   ├── docs/          # Documentacion y brainstorm
│   ├── scripts/       # Scripts de generacion
│   ├── src/           # Codigo fuente (8 modulos)
│   ├── tests/         # Suite de tests
│   └── Dockerfile     # Contenedor
└── README.md
```

---

## Niflheim — Assets

**Proposito:** Modelos, datasets, recursos estaticos.

Todo el contenido esta excluido de git via `.gitignore`:

- Modelos: `.safetensors`, `.pth`, `.pt`, `.bin`, `.onnx`, `.ckpt`
- Datasets: `.jsonl`, `.csv`, `.parquet`
- Assets: Imagenes, videos, audio

---

## Helheim — Archivo

**Proposito:** Proyectos muertos, cuarentena. Solo lectura.

| Proyecto | Fecha | Causa |
|----------|-------|-------|
| kohya_ss | 2026-05-21 | Eliminado (LoRA training, ahora externo) |
| Lilith monolito v5.0 | 2026-05-21 | Migrado a modulos lilith-* |
| AI-Influencer | — | Archivado |
| AutoSub | — | Archivado |
| ForgeMaster | — | Archivado |

**Regla:** Los proyectos archivados no se modifican. Documentar fecha y causa.

---

## Jotunheim — Massive

**Proposito:** Proyectos de gran escala (>1 mes). Maximo 2 activos.

Reservado para futuro uso. Sin proyectos activos actualmente.

---

## Midgard — Personal

**Proposito:** Proyectos personales, scripts individuales.

```
Midgard/
├── scripts/     # Scripts personales
└── README.md
```

---

## Resumen Visual

```
         ┌─────────────┐
         │   Asgard     │  Core (8 lilith-* packages)
         │   (Core)     │
         └──────┬───────┘
    ┌───────────┼───────────┐
    │           │           │
┌───┴───┐  ┌───┴───┐  ┌───┴───┐
│Vanaheim│  │Alfheim│  │Svart- │
│(Agents)│  │ (UI)  │  │alfheim│
└────────┘  └───────┘  │ (Docs)│
                        └───────┘
    ┌───────────┼───────────┐
    │           │           │
┌───┴───┐  ┌───┴───┐  ┌───┴───┐
│Muspel- │  │Nifl-  │  │Helheim│
│heim    │  │heim   │  │(Dead) │
│(WIP)   │  │(Assets│  └───────┘
└────────┘  └───────┘
    ┌───────────┼───────────┐
    │                       │
┌───┴───────┐         ┌────┴────┐
│Jotunheim  │         │Midgard  │
│(Massive)  │         │(Personal│
└───────────┘         └─────────┘
```
