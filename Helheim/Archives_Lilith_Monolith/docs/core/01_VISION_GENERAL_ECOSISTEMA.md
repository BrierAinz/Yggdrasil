# 01 - Visión General del Ecosistema Lilith + Yggdrasil

> **Versión:** 4.0  
> **Fecha:** 2026-03-21  
> **Ubicación:** `D:\Proyectos\Yggdrasil\Asgard\Lilith\Core\Docs\`

---

## 1.1 ¿Qué es Lilith?

**Lilith** es un asistente de IA con memoria persistente, orquestador de herramientas y bots para Discord/Telegram. Está diseñada como un **sistema multi-agente** que coordina especialistas (el Panteón) para resolver tareas complejas.

### Características distintivas:
- **Memoria tri-capa**: Semántica (largo plazo), Episódica (sesiones), Procedimental (patrones)
- **Panteón de agentes**: Eva, Adán, Odín, Albedo, Shalltear, Crystal
- **Orquestación inteligente**: Router automático según complejidad y contexto
- **Tools V3**: 30+ herramientas (archivos, ejecución, búsqueda, delegación)
- **Multi-plataforma**: Discord, Telegram, VS Code, API REST

---

## 1.2 ¿Qué es Yggdrasil?

**Yggdrasil** (el Árbol del Mundo) es el ecosistema de proyectos organizado en **nueve reinos**. Es el sistema nervioso donde Lilith opera como orquestador central.

### Los Nueve Reinos:

| # | Reino | Naturaleza | Contenido Actual |
|---|-------|-----------|------------------|
| 1 | **Asgard** | Poder divino | ✅ Lilith (orquestador central) |
| 2 | **Alfheim** | Luz, UI | Vacío (preparado para frontend) |
| 3 | **Midgard** | Mundo humano | Piano Autoplayer, Arte, GitHub |
| 4 | **Svartalfheim** | Forja | **Bóveda de conocimiento** (5,468 archivos) |
| 5 | **Vanaheim** | Magia, experimentos | Vacío (Albedo debería estar aquí) |
| 6 | **Jotunheim** | Gigantes | Vacío (monolitos futuros) |
| 7 | **Muspelheim** | Fuego, creación | Vacío (desarrollo activo) |
| 8 | **Niflheim** | Niebla, docs | Assets, venv, Stable Diffusion |
| 9 | **Helheim** | Más allá | Vacío (archivados) |

---

## 1.3 Arquitectura Global

```
┌─────────────────────────────────────────────────────────────────────────┐
│                           INTERFACES DE USUARIO                         │
├─────────────┬─────────────┬────────────────┬────────────────────────────┤
│   Discord   │  Telegram   │   VS Code Ext  │      Frontend SPA          │
│    Bot      │    Bot      │   (lilith-)    │   (React + WebSocket)      │
└──────┬──────┴──────┬──────┴────────┬───────┴────────────┬───────────────┘
       │             │               │                    │
       └─────────────┴───────────────┴────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                         LILITH CORE - API LAYER                         │
│                    FastAPI + WebSocket + IPC Client                     │
│              /api/discord/*  /api/telegram/*  /api/vscode/*             │
└─────────────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                       ORQUESTADOR CENTRAL                               │
│  ┌─────────────┐  ┌──────────────┐  ┌────────────────────────────────┐ │
│  │   Planner   │→ │ PlanExecutor │→ │    PANTEÓN DE AGENTES          │ │
│  │   (DAG)     │  │  (waves)     │  │  ┌─────┐┌─────┐┌─────┐┌─────┐ │ │
│  └─────────────┘  └──────────────┘  │  │ Eva ││Adán ││Odín ││Albedo│ │ │
│         ↑                    ↓      │  │(Grok)││(Qwen)││(Kimi)││(Local)│ │
│  ┌─────────────┐      ┌──────────────┐│  └─────┘└─────┘└─────┘└─────┘ │ │
│  │   Memory    │←────→│ ToolRegistry │└────────────────────────────────┘ │
│  │   Manager   │      │     V3       │                                   │
│  └─────────────┘      └──────────────┘                                   │
└─────────────────────────────────────────────────────────────────────────┘
                              │
              ┌───────────────┼───────────────┐
              ▼               ▼               ▼
┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐
│  MEMORIA        │  │  TOOLS V3       │  │  LLM PROVIDERS  │
│  tri-capa       │  │  30+ tools      │  │  multi-backend  │
├─────────────────┤  ├─────────────────┤  ├─────────────────┤
│ • Semantic      │  │ • File ops      │  │ • Kimi (262k)   │
│ • Episodic      │  │ • Exec          │  │ • Grok (Eva)    │
│ • Procedural    │  │ • Web search    │  │ • Venice        │
│ • MuninnDB      │  │ • Delegation    │  │ • OpenRouter    │
└─────────────────┘  └─────────────────┘  └─────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                           YGGDRASIL - 9 REINOS                          │
│                    Ecosistema de proyectos organizado                   │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## 1.4 Flujo de Datos

```
Usuario envía mensaje
        │
        ▼
┌───────────────┐
│  Transporte   │  ← Discord / Telegram / VS Code / SPA
│   (Bot/API)   │
└───────┬───────┘
        │
        ▼
┌───────────────┐
│  Albedo:Somb  │  ← Clasificación previa
│  (shadow)     │
└───────┬───────┘
        │
        ▼
┌───────────────┐
│  RAG + Memory │  ← Recuperar contexto relevante
│  (semantic)   │
└───────┬───────┘
        │
        ▼
┌───────────────┐
│    Planner    │  ← Generar plan de pasos
│  (DAG/waves)  │
└───────┬───────┘
        │
        ▼
┌───────────────┐
│ PlanExecutor  │  ← Ejecutar pasos
│  (parallel)   │
└───────┬───────┘
        │
        ▼
┌───────────────┐
│   Agente      │  ← Delegar a especialista
│  (router)     │
└───────┬───────┘
        │
        ▼
┌───────────────┐
│  Respuesta    │  ← Streaming al usuario
│  (generate)   │
└───────────────┘
        │
        ▼
┌───────────────┐
│ Consolidación │  ← Guardar en memoria
│  (episodic)   │
└───────────────┘
```

---

## 1.5 Convenciones del Proyecto

### Nombres de archivos:
- `README.md` / `RESUMEN.md` - Documentación de entrada
- `*_API.md` - Documentación de APIs
- `MISION_*.md` - Documentos de misión/arquitectura
- ` numbered: 01_, 02_, ...` - Documentación secuencial

### Estructura de carpetas:
```
Lilith/
├── Core/
│   ├── Backend/        # Python FastAPI
│   ├── Frontend/spa/   # React + Vite
│   ├── Config/         # JSONs de config
│   ├── Docs/           # Documentación
│   ├── Memory/         # Datos de memoria
│   ├── Tests/          # Tests pytest
│   ├── Tools/          # Utilidades
│   └── Workspace/      # Destrezas, Taller
├── Discord/            # Bot Discord
├── Telegram/           # Bot Telegram
└── VSCode/             # Extensión VS Code
```

---

## 1.6 Glosario

| Término | Significado |
|---------|-------------|
| **Panteón** | Conjunto de agentes especializados |
| **MuninnDB** | Sistema de memoria cognitiva externa |
| **RAG** | Retrieval-Augmented Generation |
| **DAG** | Directed Acyclic Graph (planificación) |
| **Wave** | Oleada de ejecución paralela |
| **Tool V3** | Herramientas del sistema (protocolo unificado) |
| **Shadow** | Clasificación previa (Albedo rol 1) |
| **Scribe** | Documentación automática (Albedo rol 2) |
| **Sentinel** | Quality control (Albedo rol 3) |

---

*Documento 01 del índice de documentación de Lilith*
