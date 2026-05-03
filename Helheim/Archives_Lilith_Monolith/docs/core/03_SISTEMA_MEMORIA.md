# 03 - Sistema de Memoria Tri-Capa + MuninnDB

> **Versión:** 4.1  
> **Fecha:** 2026-03-21  
> **Ubicación:** `Lilith/Core/Backend/core/memory/`  
> **Estado:** final

---

## 3.1 Visión General

El sistema de memoria de Lilith es una arquitectura **multi-capa, multi-modal** que simula diferentes tipos de memoria humana:

```
┌─────────────────────────────────────────────────────────────┐
│                     MEMORY LAYERS                           │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│   ┌─────────────┐   ┌─────────────┐   ┌─────────────┐      │
│   │   WORKING   │   │   SESSION   │   │   EPISODIC  │      │
│   │   MEMORY    │◄──►│   MEMORY    │◄──►│   MEMORY    │      │
│   │  (corto)    │   │  (medio)    │   │ (medio-largo│      │
│   └──────┬──────┘   └──────┬──────┘   └──────┬──────┘      │
│          │                 │                  │              │
│          └─────────────────┼──────────────────┘              │
│                            ▼                                │
│   ┌─────────────────────────────────────────────────────┐  │
│   │              MEMORY MANAGER / ROUTER                 │  │
│   │        (interfaz unificada, búsqueda ponderada)      │  │
│   └─────────────────────────────────────────────────────┘  │
│                            │                                │
│          ┌─────────────────┼─────────────────┐              │
│          ▼                 ▼                 ▼              │
│   ┌─────────────┐   ┌─────────────┐   ┌─────────────┐      │
│   │   SEMANTIC  │   │ PROCEDURAL  │   │   MUNINN    │      │
│   │   MEMORY    │   │   MEMORY    │   │     DB      │      │
│   │  (largo)    │   │  (largo)    │   │ (cognitiva) │      │
│   │ ChromaDB    │   │    JSON     │   │  HTTP API   │      │
│   └─────────────┘   └─────────────┘   └─────────────┘      │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

---

## 3.2 Memoria Semántica

### 3.2.1 Ubicación
- `Lilith/Core/Backend/core/memory/semantic/`
- `Lilith/Core/Backend/memory/semantic_memory.py`

### 3.2.2 Componentes

| Archivo | Propósito |
|---------|-----------|
| `vector_store.py` | Almacenamiento vectorial ChromaDB + embeddings |
| `store.py` | Interfaz de alto nivel (SemanticStore) |

### 3.2.3 VectorStore (ChromaDB)

**Tecnologías:**
- **ChromaDB**: Base de datos vectorial persistente
- **Embeddings**: `all-MiniLM-L6-v2` (SentenceTransformers)
- **Persistencia**: `Data/chroma_facts/`

**Features:**

| Feature | Descripción |
|---------|-------------|
| Chunking inteligente | Divide textos >450 chars con overlap de 50 |
| Diversidad por source | Estrategia `one_per_source` |
| Decay temporal | Half-life de 30 días |
| Filtro por topic | Acotación por dominio |

**Almacenamiento dual:**
```
JSONL (facts.jsonl) ──┬──→ ChromaDB (búsqueda vectorial)
                      └──→ Últimos N hechos (recientes)
```

**Campos de metadatos:**
```python
{
  "timestamp": "2026-03-21T04:17:22+00:00",
  "source_id": "fact_001",
  "topic": "gamedev"
}
```

### 3.2.4 SemanticMemory (Backend/memory/)

**Archivos gestionados:**

| Archivo | Contenido |
|---------|-----------|
| `user_profile.json` | Perfil del usuario |
| `projects.json` | Proyectos activos |
| `code_style.json` | Reglas de estilo de código |
| `architecture_decisions.json` | Decisiones técnicas (ADRs) |
| `facts.jsonl` | Hechos recientes (append-only) |

**Funciones:**
- `get_context_for_prompt(query)`: Genera contexto para LLM
- `add_fact()`: Almacena hechos con chunking automático
- `update_code_style()`: Aprende patrones vía Eva Agent
- `record_architecture_decision()`: Documenta ADRs

### 3.2.2 Indexación por Temas (v4.2)

Clasificación automática de hechos semánticos por temas.

**Ubicación:** `Core/Backend/core/topic_classifier.py`

**Taxonomía:**

| Tema | Subtopics | Keywords |
|------|-----------|----------|
| `codigo` | backend, frontend, testing | refactor, bug, function |
| `discord` | commands, handlers, roles | discord, bot, slash |
| `documentacion` | arquitectura, API, usuario | docs, README, guía |
| `infraestructura` | muninn, scheduler, backups | deploy, server, db |
| `memoria` | episodica, semantica, cognitiva | memoria, facts, episodios |

**Uso:**
```python
from Backend.core.topic_classifier import classify_content
from Backend.core.memory_store import MemoryStore

# Clasificar contenido
topics = classify_content("Implementé slash commands")
# Resultado: ["discord", "codigo"]

# Guardar con topics
mem = SemanticMemory(
    domain="codigo",
    entity="discord_commands",
    fact="Implementé slash commands",
    topics=topics
)
store.upsert_memory(mem)

# Buscar por tema
results = store.search_by_topic(
    query="async await",
    topics=["codigo"],
    k=5
)
```

**Ver documentación completa:** `MEMORIA_EPISODICA_INDEXADA.md`

---

## 3.3 Memoria Episódica

### 3.3.1 Ubicación
- `Lilith/Core/Backend/core/memory/episodic/`

### 3.3.2 Estructura

| Archivo | Propósito |
|---------|-----------|
| `store.py` | EpisodicStore - Logs de interacciones |
| `models.py` | InteractionLog dataclass |

### 3.3.3 Formato de Almacenamiento

**JSONL append-only:** `memory/episodic/interactions.jsonl`

```python
{
  "timestamp": "2026-03-21T04:17:22+00:00",
  "user_id": "usuario_discord",
  "message": "Hazme un script de Python",
  "plan": [{"tool_name": "write_file", "params": {...}}],
  "final_response": "Aquí tienes el script...",
  "outcome": "success"  # success | failure | user_corrected
}
```

### 3.3.4 Memoria Episódica Enriquecida (v4.2)

Extensión del sistema episódico con metadatos adicionales.

**Ubicación:** `Core/Backend/core/episodic_store.py`

**Campos Adicionales:**

| Campo | Tipo | Descripción |
|-------|------|-------------|
| `project_id` | str | Proyecto asociado (lilith, nazarick, personal) |
| `outcome` | str | success \| failure \| partial |
| `tags` | List[str] | Tags automáticos (refactor, bug_fix, etc.) |
| `emotional_tag` | str | frustrating \| successful \| routine \| exciting |
| `context_snapshot` | dict | Estado relevante del momento |
| `tool_used` | str | Tool utilizada |

**Auto-Tagging:**

| Tag | Detección |
|-----|-----------|
| `refactor` | Keywords: "refactor", "reestructura" |
| `bug_fix` | Keywords: "bug", "error", "fix" |
| `deployment` | Keywords: "deploy", "release", "prod" |
| `optimization` | Keywords: "optimiza", "performance" |

**Consultas Avanzadas:**
```python
# Por outcome
failures = store.query_by_outcome("failure", project_id="lilith")

# Timeline de proyecto
episodes = store.query_by_project("lilith", start_date="2024-01-01")

# Estadísticas
stats = store.get_stats_by_project("lilith")
# Retorna: success_rate, emotional_breakdown, top_tags
```

**Ver documentación completa:** `MEMORIA_EPISODICA_INDEXADA.md`

### 3.3.5 Política de Retención

**Configuración en `Config/memory.json`:**
```json
{
  "max_episodic_days": 90,
  "max_episodic_entries": 5000
}
```

**Métodos:**
- `store()`: Añade interacción + aplica retención
- `list_recent(limit)`: Recupera últimas N interacciones

---

## 3.4 Memoria Procedimental

### 3.4.1 Ubicación
- `Lilith/Core/Backend/core/memory/procedural/`

### 3.4.2 Estructura

| Archivo | Propósito |
|---------|-----------|
| `store.py` | ProceduralStore - Patrones aprendidos |
| `models.py` | LearnedPattern dataclass |

### 3.4.3 Formato de Patrón

**Almacenamiento:** `memory/procedural_v3/learned_patterns.json`

```python
{
  "pattern_id": "p_0",
  "description": "Cuando pide código Python",
  "trigger": "python script",
  "action": {"tool_name": "write_file", "template": "python"},
  "intent": "code_generation",
  "created_at": "2026-03-21T04:17:22+00:00",
  "use_count": 5,
  "last_used": "2026-03-21T04:17:22+00:00"
}
```

### 3.4.4 Features

| Feature | Descripción |
|---------|-------------|
| Archivado automático | No usados en 30 días → `store_old_patterns.json` |
| Refuerzo | `increment_use()` actualiza contador y timestamp |
| Filtrado por intent | Busca patrones por intención |

---

## 3.5 MuninnDB (Memoria Cognitiva)

### 3.5.1 Ubicación
- `Lilith/Core/Backend/core/muninn_memory.py`
- `Lilith/Core/Backend/core/muninn_edges.py`
- `Lilith/Core/Backend/core/muninn_triggers.py`

### 3.5.2 Arquitectura

**Servicio externo** de memoria cognitiva con:
- Vaults por agente
- Grafo de relaciones
- Sistema de triggers proactivos

### 3.5.3 MuninnMemory (`muninn_memory.py`)

**Vaults por agente:**
```python
AGENT_VAULTS = {
    "lilith":    "lilith",
    "odin":      "odin",
    "eva":       "eva",
    "adan":      "adan",
    "crystal":   "crystal",
    "shalltear": "shalltear",
    "telegram":  "telegram",
}
```

**Vaults por transporte:**
```python
TRANSPORT_VAULTS = {
    "discord": "default",
    "telegram": "telegram",
}
```

**Operaciones:**
- `write()`: Almacena engramas con metadata
- `activate()`: Recuperación cognitiva por contexto
- `search()`: Búsqueda por concepto
- `get_agent_memory()`: Recupera memoria específica

**Campo "Why" (explicabilidad):**
```python
{
  "concept": "python_async",
  "content": "Asyncio es importante...",
  "score": 0.85,
  "why": {
    "bm25": 0.6,
    "hebbian": 0.7,
    "temporal": 0.5,
    "total": 0.85
  }
}
```

### 3.5.4 EdgeManager (`muninn_edges.py`)

**Grafo de relaciones local:** `Data/muninn_edges.jsonl`

**Tipos de aristas:**
- `intent_uses_tool`: Intención → Herramienta
- `tool_sequence`: Secuencia de herramientas
- `confirmation`: Plan → Resultado
- `tool_outcome`: Herramienta → Éxito/Fracaso

**Operaciones:**
- `add_edge()`: Crea/refuerza arista
- `search_related()`: BFS de N saltos
- `record_plan_edges()`: Extrae relaciones de planes

### 3.5.5 MuninnTriggerEngine (`muninn_triggers.py`)

**Sistema de proactividad:**
- Callbacks de MuninnDB vía API
- Rate limiting: max 4-5 triggers/hora
- Tags urgentes: `urgent`, `critical`, `owner_alert`

**Configuración (`Config/muninn.json`):**
```json
{
  "trigger_rules": {
    "max_per_hour": 4,
    "min_score": 0.55,
    "allowed_vaults": ["lilith", "telegram"],
    "excluded_tags": ["debug", "test"],
    "min_hebbian_for_notify": 0.2
  }
}
```

---

## 3.6 Memory Manager y Router

### 3.6.1 MemoryManager (`manager.py`)

**Interfaz unificada:**
```python
class MemoryManager:
    - semantic_store: SemanticStore
    - episodic_store: EpisodicStore
    - procedural_store: ProceduralStore
```

**Métodos clave:**
- `search_context(query)`: Búsqueda ponderada
  - facts: 60%
  - profile: 30%
  - summaries: 10%
- `store_episodic()`: Guarda interacción completa
- `add_fact()`: Thread-safe con write lock
- `reinforce_procedural_pattern()`: Refuerza patrones
- `post_interaction()`: Pipeline post-interacción

### 3.6.2 MemoryRouter (`memory_router.py`)

**Punto de escritura único y lectura dual:**

```
Escritura:
  ↓ JSONL + ChromaDB (siempre)
  ↓ MuninnDB (solo si important=True)

Lectura:
  ↑ ChromaDB (todos)
  ↑ MuninnDB (todos excepto Crystal)
```

**Aislación por transporte:**
- `discord_public` (Crystal): Solo contenido `discord_public`
- Otros transportes: Acceso completo con deduplicación

---

## 3.7 Session Memory

### 3.7.1 Implementaciones

| Implementación | Ubicación | Características |
|----------------|-----------|-----------------|
| **Completa** | `core/session_manager.py` | Auto-guardado, gzip, export markdown |
| **Simple** | `memory/session_manager.py` | Guardado manual |

### 3.7.2 SessionSummarizer (`core/session_summarizer.py`)

**Triggers de resumen:**
1. **Inactividad**: N minutos sin mensajes
2. **Pre-purga**: Antes de eliminar episodios antiguos
3. **Bajo demanda**: "¿qué hicimos ayer?"

**Almacenamiento:** `Data/session_summaries.jsonl`

```python
{
  "timestamp": "2026-03-21T04:17:22+00:00",
  "channel_id": "discord_123",
  "episode_count": 15,
  "summary": "Trabajamos en refactorizar...",
  "tags": ["refactor", "api", "python"],
  "reason": "inactivity"
}
```

---

## 3.8 Working Memory

### 3.8.1 Concepto

Memoria de **corto plazo** por canal que se inyecta en cada system prompt.

### 3.8.2 Características

| Feature | Valor |
|---------|-------|
| Decay | -0.15 por mensaje procesado |
| Mínimo | Expira si importancia < 0.05 |
| Máximo | 20 ítems (eviction del menos importante) |
| Pins | Ítems fijados nunca expiran |

### 3.8.3 API

```python
wm = get_working_memory("discord")
wm.add("nombre_sesion", "Trabajando en módulo X", importance=1.0)
wm.pin("nombre_sesion")
wm.tick()  # Aplica decay
context = wm.format_for_prompt(max_items=10)
```

### 3.8.4 Detección Automática

**Patrones que activan extracción:**
- "recuerda que..."
- "ten en cuenta que..."
- "no olvides que..."
- "importante: ..."
- "anota que..."

---

## 3.9 Memory API

### 3.9.1 Endpoints REST

| Endpoint | Retorna |
|----------|---------|
| `GET /api/memory/semantic` | user_profile + últimas 5 decisions |
| `GET /api/memory/episodic` | Últimos 10 resúmenes de sesión |
| `GET /api/memory/procedural` | error_history + patterns |

### 3.9.2 Uso

Panel de memoria en la UI de Lilith para visualización/debug.

---

## 3.10 Estructura de Archivos

```
Lilith/Core/
├── Backend/core/memory/
│   ├── __init__.py              # Exports
│   ├── manager.py               # MemoryManager
│   ├── memory_router.py         # MemoryRouter
│   ├── working_memory.py        # WorkingMemory
│   ├── muninn_adapter.py        # Adapter MuninnDB
│   ├── memory_store.py          # ChromaDB Pydantic
│   │
│   ├── semantic/
│   │   ├── store.py             # SemanticStore
│   │   ├── vector_store.py      # ChromaDB + embeddings
│   │   └── db.py
│   │
│   ├── episodic/
│   │   ├── store.py             # EpisodicStore (JSONL)
│   │   └── models.py            # InteractionLog
│   │
│   └── procedural/
│       ├── store.py             # ProceduralStore (JSON)
│       └── models.py            # LearnedPattern
│
├── Backend/core/
│   ├── muninn_memory.py         # MuninnMemory client
│   ├── muninn_edges.py          # EdgeManager (grafo)
│   ├── muninn_triggers.py       # TriggerEngine
│   ├── session_manager.py       # SessionManager
│   └── session_summarizer.py    # SessionSummarizer
│
└── Backend/api/
    └── memory_api.py            # Endpoints REST
```

---

## 3.11 Configuración

### 3.11.1 `Config/memory.json`

```json
{
  "weight_facts": 0.6,
  "weight_profile": 0.3,
  "weight_summaries": 0.1,
  "max_episodic_days": 90,
  "max_episodic_entries": 5000,
  "chunk_size": 450,
  "chunk_overlap": 50,
  "query_synonyms": {
    "proyecto": ["project", "código", "app"],
    "error": ["bug", "fallo", "problema"]
  }
}
```

### 3.11.2 `Config/muninn.json`

```json
{
  "url": "https://api.muninn.io",
  "token": "mk_...",
  "agent_vaults": {...},
  "trigger_rules": {...}
}
```

## 3.12 Referencias y Documentación Relacionada

| Documento | Descripción |
|-----------|-------------|
| `MEMORIA_EPISODICA_INDEXADA.md` | Memoria episódica enriquecida + indexación por temas |
| `MULTI_MODELO_HIBRIDO.md` | Selector automático de modelos LLM |
| `Core/Config/memory_topics.json` | Taxonomía de temas |
| `Core/Config/episodic.json` | Configuración de episodios |

---

*Documento 03 del índice de documentación de Lilith*
