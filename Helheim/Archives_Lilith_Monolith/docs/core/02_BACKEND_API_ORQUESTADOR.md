# 02 - Backend: API, Orquestador y Sistema de Planificación

> **Versión:** 5.0
> **Fecha:** 2026-03-23
> **Ubicación:** `Lilith/Core/Backend/`

---

## 2.1 Estructura del Backend

```
Backend/
├── api/                    # FastAPI - Endpoints REST
│   ├── server.py          # Servidor principal
│   ├── discord_api.py     # API para Discord bot
│   ├── telegram_api.py    # API para Telegram bot
│   ├── vscode_api.py      # API para extensión VS Code
│   ├── memory_api.py      # API de memoria
│   ├── agents_api.py      # Métricas de agentes
│   └── ...
├── core/                   # Núcleo del sistema
│   ├── agents/            # Panteón de agentes
│   ├── memory/            # Sistema de memoria tri-capa
│   ├── tools_v3/          # Herramientas V3
│   ├── planning/          # Planificación alternativa
│   ├── orchestrator.py    # Orquestador principal
│   ├── planner.py         # Planificador
│   ├── plan_executor.py   # Ejecutor de planes
│   └── agent_router.py    # Router de agentes
├── llm/                    # Clientes LLM
│   ├── kimi_client.py     # Kimi (262k context, Crystal)
│   ├── grok_client.py     # xAI Grok (Eva)
│   ├── venice_client.py   # Venice AI (Shalltear)
│   └── ollama_client.py   # Ollama local (Adán, Albedo)
├── capabilities/           # Capacidades del sistema
│   ├── git_tools.py
│   └── system_executor.py
└── utils/                  # Utilidades
```

---

## 2.2 API REST (server.py)

### Endpoints Principales

| Método | Endpoint | Descripción |
|--------|----------|-------------|
| GET | `/api/status` | Estado del sistema |
| GET | `/api/version` | Versión detallada |
| GET | `/api/meta-report` | Meta-informe de uso |
| GET | `/api/tools` | Lista todas las tools |
| POST | `/api/chat` | Chat HTTP (fallback) |
| POST | `/api/execute` | Ejecutar tool con trust check |
| POST | `/api/confirm` | Confirmar ejecución pendiente |

### WebSocket Endpoints

| Endpoint | Uso |
|----------|-----|
| `/ws` | WebSocket legacy |
| `/ws/conversational` | WebSocket conversacional con Core |

### Routers Incluidos

```python
app.include_router(ide_router)        # /api/ide/*
app.include_router(memory_router)     # /api/memory/*
app.include_router(dashboard_router)  # /api/dashboard/*
app.include_router(discord_router)    # /api/discord/*
app.include_router(telegram_router)   # /api/telegram/*
app.include_router(scheduler_router)  # Tareas programadas
app.include_router(proactive_router)  # Sugerencias proactivas
app.include_router(agents_api_router) # /api/agents/*
```

---

## 2.3 Sistema de Orquestación

### 2.3.1 Orchestrator (`orchestrator.py`)

El **Orchestrator** es el director de orquesta que coordina Planner, PlanExecutor y MemoryManager.

```python
class Orchestrator:
    def __init__(self, planner, registry, memory_manager, 
                 plan_executor=None, agent_caller=None, agent_registry=None)
    
    def execute_plan(message, context, conversation_history, 
                     user_id, skip_cache, progress_callback, 
                     event_callback, channel)
```

**Flujo de ejecución:**

1. **Albedo: Sombra** - Clasificación previa y resolución trivial
2. **RAG Preemptivo** - Recuperar 3 recuerdos relevantes
3. **Planner.plan()** - Generar plan de pasos
4. **PlanExecutor.run_plan()** - Ejecutar el plan
5. **Consolidación** - Extraer y guardar recuerdos
6. **Albedo: Escriba** - Documentación en background

### 2.3.2 Agent Loop (`agent_loop.py`)

```python
class AgentLoop:
    def __init__(self, tool_registry=None, max_iterations=10)
    
    async def run(objetivo, context)          # Ejecuta objetivo
    async def run_multi_step(pasos)           # Ejecuta múltiples pasos
    def explain_routing(task, context_tokens) # Explica selección
```

- **Máximo 10 iteraciones** para evitar loops infinitos
- Selección automática de agente según contexto

---

## 2.4 Sistema de Planificación

### 2.4.1 Planner (`planner.py`)

Genera planes ejecutables a partir de mensajes de usuario.

**PlanResult:**
```python
@dataclass
class PlanResult:
    steps: List[Step]
    confidence: float        # 0.0 - 1.0
    confidence_reason: str   # "intent_clear" | "fallback_used" | ...
```

**Fases de planificación:**

| # | Fase | Descripción |
|---|------|-------------|
| 1 | Macro Detection | Detectar macros de PC |
| 2 | Memory Config | Cargar Config/memory.json y planner.json |
| 3 | Preemptive Retrieval | Consultar Muninn/semántica |
| 4 | Plan Aprendido | Usar LearningEngine |
| 5 | Clasificador Local | LocalIntentClassifier |
| 6 | Pre-check PC | Detectar operaciones de listado |
| 7 | Shalltear Pre-filtro | Clasificación rápida |
| 8 | Intent Patterns | Config/intent_patterns.json |
| 9 | Matching Learning | Sugerencias basadas en historial |
| 10 | Fallback | Respuesta conversacional |

### 2.4.2 Plan Executor (`plan_executor.py`)

Ejecuta planes por **oleadas (waves)** en paralelo.

```python
def run_plan(plan: List[Step], registry: ToolRegistryV3, *,
             context: str = "",
             user_id: str = "",
             conversation_history: List[Dict] = None,
             semantic_context: List[Dict] = None,
             skip_cache: bool = False,
             base_path: Path = None,
             progress_callback: Callable = None,
             event_callback: Callable = None)
```

**Características:**
- Ejecución paralela por oleadas (DAG)
- Scratchpad con step_results
- Context building desde pasos previos
- Web budget (cortafuegos cognitivo)
- Handoff horizontal supervisado
- Freno de mano: máximo 3 fallos consecutivos
- Albedo Centinela: quality review

**Ejemplo de ejecución por waves:**
```
Wave 1: [read_file, list_directory]  ← Paralelo
Wave 2: [delegate_eva]               ← Dependiente de Wave 1
Wave 3: [edit_file]                  ← Dependiente de Wave 2
```

---

## 2.5 Agent Router y Panteón

### 2.5.1 Agent Router (`agent_router.py`)

**Reglas de routing:**

| Agente | Trigger | Modelo |
|--------|---------|--------|
| **Eva** | Contexto > 50k tokens, análisis, docs | grok-4-fast-reasoning |
| **Adán** | Código puro, tests, refactor | qwen2.5-coder:7b (local) |
| **Odín** | Creativo, privado, investigación | kimi-for-coding (262k) |
| **Kimi/Lilith** | Default, orquestación | kimi-for-coding |

```python
class AgentRouter:
    def select_agent(task, context_tokens) -> str
    async def execute(task, agent_name, context, context_tokens) -> Dict
```

### 2.5.2 Panteón de Agentes

| Agente | Archivo | Rol | Backend |
|--------|---------|-----|---------|
| **BaseAgent** | `base_agent.py` | Clase abstracta | - |
| **Eva** | `eva_agent.py` | Analista meticulosa | Grok (xAI) |
| **Adán** | `adan_agent.py` | Ejecutor de código | Ollama/Qwen local |
| **Odín** | `odin_agent.py` | Pensador profundo | Kimi 262k |
| **Albedo** | `albedo_agent.py` | Guardiana Suprema | Ollama local |
| **Shalltear** | `shalltear_agent.py` | Agente táctico | Venice AI |
| **Crystal** | `crystal_agent.py` | Cara pública Discord | Kimi (v4.2) |

#### Albedo - 4 Roles:

1. **Sombra** (`shadow_classify`) - Clasificación de complejidad
2. **Escriba** (`scribe_process`) - Documentación de interacciones
3. **Centinela** (`sentinel_review`) - Quality control de outputs
4. **Intérprete** (`interpret_for_channel`) - Reformateo para canales

#### Shalltear - Funciones:

- `classify_intent()` - Clasificación rápida de intenciones
- `parse_nl_to_params()` - Parseo NL a parámetros estructurados
- `score_importance()` - Puntuación de importancia 0-10
- `quick_answer()` - Respuestas rápidas

---

## 2.6 Clientes LLM

### 2.6.1 Kimi Client (`kimi_client.py`)

```python
class KimiClient:
    API_URL = "https://api.kimi.com/coding/v1"
    MODEL = "kimi-for-coding"  # 262k context
    
    async def generate_text(prompt, system_prompt=None, 
                           temperature=0.7, max_tokens=4096)
    async def check_health()
```

- Protocolo: Anthropic Messages API
- Features: Streaming simulado, generate_text, health check

### 2.6.2 Grok Client (`grok_client.py`)

```python
class GrokClient:
    API_URL = "https://api.x.ai/v1"
    MODEL = "grok-4-fast-reasoning"
    
    async def generate_text(prompt, system_prompt=None)
    async def chat(messages, temperature=0.7, max_tokens=4096)
```

- Protocolo: OpenAI-compatible
- Features: True streaming, chat completions

### 2.6.3 Venice Client (`venice_client.py`)

```python
class VeniceClient:
    API_URL = "https://api.venice.ai/api/v1"
    MODELS = ["venice-uncensored", "llama-3.3-70b"]
    
    async def generate(prompt, system_prompt=None)
    async def chat(messages)
```

- Uso: Shalltear, modelos sin censura
- Features: Async/sync generation, JSON mode

### 2.6.4 Ollama Client (`ollama_client.py`)

```python
class OllamaClient:
    BASE_URL = "http://localhost:11434"

    async def chat(model, messages)
    async def generate(model, prompt)
```

- Uso: Adán, Albedo, fallback local
- Models: `qwen2.5-coder:7b`, `llama3.2:latest`

> **Nota v4.2:** Crystal migró de OpenRouter a Kimi API directa.
> El cliente OpenRouter ya no se usa en el sistema.

---

## 2.7 Capabilities

### 2.7.1 Git Tools (`git_tools.py`)

```python
class GitTools:
    def execute(commands: List[str]) -> str
    def get_status() -> str
    def get_diff() -> str
```

### 2.7.2 System Executor (`system_executor.py`)

```python
class SystemExecutor:
    def assess_risk(command: str) -> Literal["low", "medium", "high"]
    def execute(command: str) -> str
```

- Block-list: `rm -rf`, `format`, etc.
- Heurísticas de riesgo por palabras clave

---

## 2.8 Auto-Mode

### 2.8.1 Task Planner (`auto_mode/task_planner.py`)

```python
class TaskPlanner:
    async def plan(objetivo: str) -> Dict
```

**Output:**
```python
{
    "objetivo": "resumen",
    "subtareas": [
        {"id": 1, "descripcion": "...", "agente": "eva|adan|kimi"}
    ],
    "estimacion": "2-4 minutos",
    "file_context": {...}
}
```

### 2.8.2 Task Executor (`auto_mode/task_executor.py`)

- Ejecución secuencial de subtareas
- Pausa/reanudación vía TaskMonitor
- Fallback a Kimi si falla

### 2.8.3 Task Monitor (`auto_mode/task_monitor.py`)

**Persistencia:** `Memory/auto_mode/tasks.json`

**Estados:**
- `pending` → `planning` → `running` → `done`/`failed`
- `paused` (pausado)

---

## 2.9 Configuración

### 2.9.1 Config Manager (`config_manager.py`)

```python
class ConfigManager:
    def load() -> AppConfig
    def update(patch: dict) -> AppConfig
    def _migrate_legacy_to_v1(legacy: Dict) -> Tuple[Dict, bool]
```

### 2.9.2 Config Schema (`config_schema.py`)

```python
class AppConfig(BaseModel):
    config_version: int = 1
    llm: LLMConfig
    system: SystemConfig
    safety: SafetyConfig
```

**Providers soportados:**
```python
Provider = Literal["ollama", "openai", "anthropic", "deepseek", 
                   "qwen", "grok", "venice", "kimi"]
```

---

## 2.10 AgentRegistry y Agentes de Dominio

El **AgentRegistry** es el catálogo de agentes como entidades de primera clase.

```python
class AgentRegistry:
    def register(agent: Agent)  # Registra agente
    def get_by_tool_name(tool_name: str) -> Optional[Agent]
    def list_agents() -> List[Dict]
```

**Agentes Registrados por Defecto:**

| agent_id | tool_name | Descripción | Backend |
|----------|-----------|-------------|---------|
| eva | delegate_eva | Análisis, documentación | Grok |
| adan | delegate_adan | Código, refactor | Qwen |
| lucifer | delegate_lucifer | Creativo, conversacional | Venice |
| odin | delegate_odin | Análisis masivo | Kimi |
| web_scraper | delegate_web_scraper | Extracción web | BeautifulSoup |
| content_cleaner | delegate_content_cleaner | Limpieza HTML | Local |
| quality_filter | delegate_quality_filter | Filtro de calidad | Local |
| data_structurer | delegate_data_structurer | Estructuración | Local |

**Agent vs Tool:**
- **Agentes:** Implementan `execute(params) → ToolResult`, registrados en AgentRegistry
- **Tools:** Capacidades atómicas en ToolRegistryV3 (read_file, edit_file, etc.)
- El PlanExecutor consulta primero AgentRegistry, luego ToolRegistry

### Flujos de Datos por Tarea

| Tarea | Plan Típico | Agentes/Tools |
|-------|-------------|---------------|
| Conversación | [ delegate_lucifer ] | Lucifer (Venice) |
| Análisis profundo | [ delegate_eva ] | Eva (Grok) |
| Código/refactor | [ delegate_adan ] | Adán (Qwen) |
| Análisis masivo | [ gather_directory, delegate_odin ] | Odín (Kimi) |
| Minería web | [ web_scraper, content_cleaner, quality_filter, data_structurer, store_semantic_fact ] | Pipeline completo |
| Extracción lore | [ lore_extractor ] | LoreExtractorTool |
| Guardar hecho | [ store_semantic_fact ] | StoreSemanticFactTool |

**Flujo de Minería Web:**
```
URL → WebScraper → ContentCleaner → QualityFilter → DataStructurer → StoreSemanticFact
```

Cada paso recibe la salida del anterior vía `params["context"]`.

---

## 2.11 Nuevos Módulos (Era 4.0)

### Módulos de Agente Avanzados

| Módulo | Ruta | Función |
|--------|------|---------|
| `complexity_router.py` | `core/agents/` | Routing Adán→Eva por complejidad |
| `fallback_chain.py` | `core/agents/` | Cadena de fallback configurable |
| `output_validator.py` | `core/agents/` | Validación heurística de salidas |
| `prompt_template.py` | `core/agents/` | AgentPromptConfig composable |
| `review_chain.py` | `core/agents/` | Revisión inter-agente (Albedo centinela) |

### Módulos de Memoria y Ejecución

| Módulo | Ruta | Función |
|--------|------|---------|
| `working_memory.py` | `core/memory/` | WorkingMemory por canal (decay, pins) |
| `memory_router.py` | `core/memory/` | Write/search unificado con aislación Crystal |
| `session_summarizer.py` | `core/` | Resúmenes de sesión automáticos |
| `muninn_edges.py` | `core/` | Grafo JSONL de relaciones concept→concept |
| `muninn_triggers.py` | `core/` | Motor de trigger callbacks de MuninnDB |
| `auto_delegate.py` | `core/` | AutoDelegateDetector (URLs, scoring) |
| `nl_param_extractor.py` | `core/` | NLParamExtractor: LLM + regex para filesystem |
| `exec_sandbox.py` | `core/` | ExecSandbox: kill tree, output caps |
| `progress_manager.py` | `core/` | ProgressManager: colas por request_id |
| `agent_metrics.py` | `core/` | Métricas latencia/éxito por tool |

---

## 2.12 Plugin System

El **Plugin System** permite añadir nuevas tools, personas del Panteón y transportes sin modificar el código core ni reiniciar el servidor.

### Estructura de un Plugin

```python
# Core/Backend/plugins/mi_plugin.py

from Backend.core.plugin_manager import BasePlugin, PluginManager

class Plugin(BasePlugin):
    name = "mi_plugin"
    version = "1.0.0"
    description = "Descripción breve"

    def on_load(self, manager: PluginManager) -> None:
        schema = {
            "type": "object",
            "properties": {
                "parametro": {"type": "string"}
            },
            "required": ["parametro"]
        }
        manager.register_tool(
            plugin_name=self.name,
            tool_name="nombre_de_la_tool",
            tool_func=_mi_tool_func,
            schema=schema,
        )

    def on_unload(self) -> None:
        pass
```

### API REST de Plugins

| Método | Endpoint | Descripción |
|--------|----------|-------------|
| GET | `/api/plugins/list` | Listar plugins activos |
| POST | `/api/plugins/load` | Cargar plugin |
| POST | `/api/plugins/reload` | Hot-reload plugin |
| POST | `/api/plugins/unload` | Descargar plugin |
| GET | `/api/plugins/status/{name}` | Estado de plugin |

### Seguridad de Plugins

**Imports prohibidos (bloqueados por AST):**
- `os.system`, `subprocess`, `pty`, `commands`, `popen`
- `ctypes`, `winreg`, `msvcrt`

**Checksum SHA256:** Verificación opcional en `plugins.json`

---

## 2.13 Scheduler (Tareas Programadas)

Jobs activos gestionados por APScheduler:

| Job | Frecuencia | Función |
|-----|------------|---------|
| `learning_consolidation` | Cada 6h | Consolida aprendizaje |
| `episodic_cleanup` | Diario 03:00 | Purga episodios viejos |
| `chromadb_purge` | Lunes 04:00 | Purga vectores decaídos |
| `session_summarizer_check` | Cada 15 min | Detecta inactividad y resume |

**Archivo:** `core/task_scheduler.py`

---

## 2.14 Diagrama de Flujo de Ejecución

```
Usuario
  │
  ▼
┌──────────────┐
│   Discord/   │
│   Telegram   │
└──────┬───────┘
       │
       ▼
┌──────────────┐
│  discord_api │
│  telegram_api│
└──────┬───────┘
       │
       ▼
┌──────────────┐
│   server.py  │  ← FastAPI
└──────┬───────┘
       │
       ▼
┌──────────────┐
│  orchestrator│  ← Coordina todo
└──────┬───────┘
       │
       ├────────────┬────────────┐
       ▼            ▼            ▼
┌──────────┐  ┌──────────┐  ┌──────────┐
│  planner │  │  memory  │  │ registry │
│  (DAG)   │  │  manager │  │  tools   │
└────┬─────┘  └──────────┘  └────┬─────┘
     │                           │
     ▼                           ▼
┌──────────┐              ┌──────────┐
│plan_exec │─────────────→│  tools   │
│ (waves)  │              │   v3     │
└────┬─────┘              └────┬─────┘
     │                         │
     ▼                         ▼
┌──────────┐              ┌──────────┐
│  agent   │              │  memory  │
│  caller  │              │  stores  │
└────┬─────┘              └──────────┘
     │
     ▼
┌──────────┐
│   LLM    │  ← Kimi/Grok/Venice/Ollama
│  client  │
└──────────┘
```

## 2.9 Sistema Multi-Modelo Híbrido (v4.2)

Selector automático de modelos LLM según complejidad de tarea.

**Componentes:**
- `ComplexityAnalyzer`: Estima complejidad por heurísticas
- `ModelSelector`: Elige modelo óptimo por rol/complejidad
- `CostTracker`: Tracking de ahorros vs baseline

**Estrategia:**
| Complejidad | Modelo | Latencia |
|-------------|--------|----------|
| TRIVIAL | Haiku | ~800ms |
| SIMPLE/MODERATE | Sonnet | ~1500ms |
| COMPLEX/EXPERT | Opus | ~2500ms |

**Ver documentación completa:** `MULTI_MODELO_HIBRIDO.md`

---

## 2.15 Sistemas v5.0 - Intelligence Suite

Nuevos sistemas avanzados de IA implementados en v5.0.

### 2.15.1 Memory Augmented Generation (MAG)

Sistema de generación aumentada con memoria para respuestas contextuales.

| Módulo | Archivo | Función |
|--------|---------|---------|
| `embeddings` | `core/mag/embeddings.py` | Multi-proveedor (Kimi/OpenAI/local) |
| `vector_store` | `core/mag/vector_store.py` | Almacenamiento vectorial con MuninnDB |
| `mag_engine` | `core/mag/mag_engine.py` | Indexación y recuperación |
| `context_augmenter` | `core/mag/context_augmenter.py` | Inyección de contexto en prompts |
| `chat_integration` | `core/mag/chat_integration.py` | Integración automática con chat |

**Uso:**
```python
from Backend.core.mag import get_mag_engine

engine = get_mag_engine()

# Indexar documento
result = await engine.index_document(
    content="Documento largo...",
    metadata={"source": "kb"},
    doc_id="doc_123"
)

# Recuperar contexto
retrieval = await engine.retrieve("pregunta", top_k=5)
```

### 2.15.2 Function Calling v2

Sistema nativo de llamada a funciones con registro automático.

| Módulo | Archivo | Función |
|--------|---------|---------|
| `schemas` | `core/functions/schemas.py` | FunctionSchema, ParameterSchema |
| `parser` | `core/functions/parser.py` | Parser multi-formato (OpenAI/Anthropic/tags) |
| `registry` | `core/functions/registry.py` | Registro con decorador @register |
| `executor` | `core/functions/executor.py` | Ejecución con timeouts |

**Uso:**
```python
from Backend.core.functions import get_function_registry

registry = get_function_registry()

@registry.register(name="calculate")
def calculate(expression: str) -> str:
    return f"Result: {eval(expression)}"

# En LLM
tools = registry.to_openai_format()
```

### 2.15.3 Agent Swarm

Sistema multi-agente con planificación y coordinación.

| Módulo | Archivo | Función |
|--------|---------|---------|
| `agent_base` | `core/agents/agent_base.py` | Clase base de agente |
| `swarm` | `core/agents/swarm.py` | Registro y ejecución paralela |
| `task_planner` | `core/agents/task_planner.py` | Descomposición de tareas |
| `coordinator` | `core/agents/coordinator.py` | Asignación dinámica |

**Roles:**
- `PLANNER` - Planificación
- `EXECUTOR` - Ejecución
- `RESEARCHER` - Investigación
- `REVIEWER` - Revisión

**Uso:**
```python
from Backend.core.agents import get_swarm, get_coordinator

swarm = get_swarm()
coordinator = get_coordinator(swarm)

result = await coordinator.execute("Tarea compleja")
```

### 2.15.4 Long-Term Memory

Memoria a largo plazo con archivado automático.

Archivo: `core/memory/long_term.py`

**Features:**
- Archivado por antigüedad
- Resúmenes periódicos
- Compactación de sesiones

### 2.15.5 Performance Monitor

Monitoreo de performance con auto-tuning.

Archivo: `core/performance/monitor.py`

**Métricas:**
- Latencia de APIs
- Tasa de éxito
- Tokens por minuto
- Auto-tuning de límites

---

## 2.16 Fase 4 Enterprise Suite (v5.0-Fase4)

Sistemas enterprise avanzados para entornos multi-usuario, aprendizaje automático y observabilidad.

### 2.16.1 Multi-User & Colaboración

Gestión de sesiones compartidas, permisos granulares y sistema de comentarios.

| Módulo | Archivo | Función |
|--------|---------|---------|
| `session_manager` | `core/collaboration/session_manager.py` | Sesiones multi-usuario, presencia, WebSockets |
| `permissions_granular` | `core/collaboration/permissions_granular.py` | ACLs por recurso, roles, grants |
| `comments` | `core/collaboration/comments.py` | Threads, replies, reacciones, menciones |

**Roles:**
- `OWNER` - Control total
- `ADMIN` - Gestión de participantes
- `EDITOR` - Lectura/escritura
- `VIEWER` - Solo lectura

**Uso:**
```python
from Backend.core.collaboration import get_session_manager, UserRole

manager = get_session_manager()
session = await manager.create_session(
    name="Proyecto",
    owner_id="user_1"
)

await manager.add_participant(
    session_id=session.id,
    user_id="user_2",
    role=UserRole.EDITOR
)
```

### 2.16.2 Auto-Discovery & Learning

Detección automática de patrones y sugerencias inteligentes.

| Módulo | Archivo | Función |
|--------|---------|---------|
| `pattern_discovery` | `core/learning/pattern_discovery.py` | Detección de secuencias y patrones |
| `suggestion_engine` | `core/learning/suggestion_engine.py` | Motor de sugerencias |
| `usage_analytics` | `core/learning/usage_analytics.py` | Analytics de uso |

**Tipos de patrones:**
- `SEQUENCE` - Secuencias de acciones
- `TEMPORAL` - Patrones horarios
- `CONDITIONAL` - Correlaciones si→entonces

**Uso:**
```python
from Backend.core.learning import get_pattern_discovery

discovery = get_pattern_discovery()
await discovery.record_action(user_id, "tool", "read_file")
patterns = await discovery.analyze_user_patterns(user_id)
```

### 2.16.3 Advanced Observability

Tracing distribuido y métricas custom.

| Módulo | Archivo | Función |
|--------|---------|---------|
| `tracing` | `core/observability/tracing.py` | OpenTelemetry-style tracing |
| `metrics_custom` | `core/observability/metrics_custom.py` | Métricas de negocio |

**Uso - Tracing:**
```python
from Backend.core.observability.tracing import get_tracer, trace_span

tracer = get_tracer()
with trace_span(tracer, "operation") as span:
    tracer.add_event("checkpoint")
```

**Uso - Metrics:**
```python
from Backend.core.observability.metrics_custom import get_metrics_registry, MetricType

metrics = get_metrics_registry()
metrics.register_metric("counter", MetricType.COUNTER, "desc")
await metrics.record("counter", 1)
```

### 2.16.4 APIs REST

**Collaboration:**
```
POST   /api/collaboration/sessions
GET    /api/collaboration/sessions/{id}
POST   /api/collaboration/sessions/{id}/participants
WS     /api/collaboration/sessions/{id}/ws
POST   /api/collaboration/comments/threads
GET    /api/collaboration/comments/threads
```

**Learning:**
```
GET    /api/learning/patterns
GET    /api/learning/suggestions
POST   /api/learning/actions/record
GET    /api/learning/analytics/report
```

---

*Documento 02 del índice de documentación de Lilith*
