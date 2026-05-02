# 📖 API Interna de Lilith — Los Grimorios del Nexus

> *Cada módulo expone su API como un grimorio de invocaciones. Aquí se documentan los encantamientos disponibles para quienes osan extender los Reinos.*

## Índice

- [LilithOrchestrator](#lilithorchestrator)
- [DynamicToolRegistry](#dynamictoolregistry)
- [SkillRegistry](#skillregistry)
- [EnhancedMemory](#enhancedmemory)
- [AgentManager](#agentmanager)
- [SwarmManager](#swarmmanager)
- [MCPManager](#mcpmanager)
- [LilithConfig](#lilithconfig)
- [LLMProvider](#llmprovider)
- [HybridRetriever](#hybridretriever)

---

## LilithOrchestrator

**Módulo:** `Lilith.Core.orchestrator`
**Rol:** El Nexus — coordina LLM, memoria, tools, skills y MCP.

### Constructor

```python
from Lilith.Core.orchestrator import LilithOrchestrator

orch = LilithOrchestrator(provider=None)
# provider: LLMProvider opcional. Si None, usa get_provider() con fallback automático.
```

### Métodos Públicos

#### `chat(user_input: str) -> str`

Procesa input del usuario y retorna la respuesta completa. Soporta tool-calling iterativo (máximo `MAX_TOOL_CALLS` iteraciones).

```python
response = orch.chat("Lista los archivos del proyecto")
# → Respuesta del LLM, posiblemente usando tools en el camino
```

**Flujo interno:**
1. `_build_system_prompt()` — Inyecta memoria relevante + skills activos
2. Envía al LLM vía `LLMProvider.chat()` con tools disponibles
3. Si hay `tool_calls` en la respuesta, ejecuta cada tool y agrega resultado al contexto
4. Repite hasta que el LLM no llame más tools (o alcanza límite)
5. `EnhancedMemory.add_episode()` — Guarda la interacción

#### `chat_stream(user_input: str) -> Iterator[str]`

Streaming de respuesta. **No soporta tool-calling interactivo** — las tools no se ejecutan en modo stream.

```python
for chunk in orch.chat_stream("Explícame la recursividad"):
    print(chunk, end="", flush=True)
```

#### `reset()`

Reinicia la conversación (limpia mensajes, preserva memoria persistente).

```python
orch.reset()
```

#### `get_history() -> List[Dict]`

Retorna historial de mensajes (sin el system prompt).

```python
history = orch.get_history()
# [{"role": "user", "content": "..."}, {"role": "assistant", "content": "..."}, ...]
```

#### `switch_provider(name: str) -> None`

Cambia al proveedor LLM especificado.

```python
orch.switch_provider("kimi")  # Forzar uso de Kimi remoto
orch.switch_provider("lm_studio")  # Volver a local
```

#### `refresh_mcp_tools() -> Dict[str, int]`

Reconecta servidores MCP y re-registra sus tools. Retorna estadísticas:

```python
stats = orch.refresh_mcp_tools()
# {"native": 35, "mcp": 12}
```

#### `get_provider_info() -> dict`

Retorna información del proveedor activo y tools registradas.

```python
info = orch.get_provider_info()
# {"name": "LM Studio", "model": "mistral-7b", "type": "local",
#  "available": True, "tools": {"native_tools": 35, "mcp_tools": 0, "total": 35}}
```

#### `get_registry_stats() -> Dict`

Estadísticas del registry de tools.

```python
stats = orch.get_registry_stats()
# {"native_tools": 35, "mcp_tools": 0, "total": 35, "tools": [...]}
```

#### `close()`

Cierra recursos, incluyendo MCP si está activo.

```python
orch.close()
```

---

## DynamicToolRegistry

**Módulo:** `Lilith.Core.dynamic_tools`
**Rol:** Registro unificado de tools nativas + MCP.

### ToolInfo (Dataclass)

```python
@dataclass
class ToolInfo:
    name: str                          # Nombre único de la tool
    description: str                   # Descripción para el LLM
    parameters: Dict[str, Any]        # JSON Schema de parámetros
    source: ToolSource                 # NATIVE o MCP
    executor: Optional[Callable]       # Función ejecutora (nativas)
    mcp_client: Optional[Any]          # Cliente MCP (tools remotas)
    mcp_server_name: Optional[str]     # Nombre del servidor MCP
```

### Enum ToolSource

```python
class ToolSource(Enum):
    NATIVE = "native"    # Tools nativas de Lilith
    MCP = "mcp"          # Tools de servidores MCP
```

### Obtener Instancia

```python
from Lilith.Core.dynamic_tools import get_dynamic_tool_registry

registry = get_dynamic_tool_registry()  # Singleton
```

### Métodos Públicos

#### `register_native_tools(tools_definitions: List[Dict], executors: Dict[str, Callable]) -> int`

Registra tools nativas. Retorna cantidad registradas.

```python
from Lilith.tools import ALL_TOOLS
from Lilith.Core.orchestrator import TOOL_EXECUTORS

count = registry.register_native_tools(ALL_TOOLS, TOOL_EXECUTORS)
# → 35
```

#### `register_mcp_tools(mcp_manager: MCPManager) -> int`

Registra todas las tools de servidores MCP conectados.

```python
count = registry.register_mcp_tools(mcp_manager)
```

#### `get_tool(name: str) -> Optional[ToolInfo]`

Busca una tool por nombre.

```python
tool = registry.get_tool("read_file")
# ToolInfo(name="read_file", source=ToolSource.NATIVE, ...)
```

#### `execute(name: str, args: Dict) -> Any` (async)

Ejecuta una tool. Para tools nativas usa el executor síncrono; para MCP usa el cliente async.

```python
result = await registry.execute("read_file", {"path": "/tmp/test.txt"})
result = await registry.execute("mcp_tool_name", {"param": "value"})
```

#### `get_openai_tools() -> List[Dict]`

Retorna todas las tools en formato OpenAI function calling (para enviar al LLM).

```python
tools = registry.get_openai_tools()
# [{"type": "function", "function": {"name": "read_file", ...}}, ...]
```

#### `get_stats() -> Dict`

Estadísticas del registry.

```python
stats = registry.get_stats()
# {"native_tools": 35, "mcp_tools": 5, "total": 40, "tools": ["read_file", ...]}
```

#### `clear_mcp_tools() -> None`

Remueve todas las tools MCP del registry (las nativas se conservan).

```python
registry.clear_mcp_tools()
```

---

## SkillRegistry

**Módulo:** `Lilith.Core.skill_registry`
**Rol:** Registro central de skills con hot-reload vía watchdog.

### Obtener Instancia

```python
from Lilith.Core.skill_registry import get_skill_registry

registry = get_skill_registry()
```

### Métodos Públicos

#### `reload() -> List[str]`

Recarga todos los skills desde el directorio. Retorna lista de nombres cargados.

```python
loaded = registry.reload()
# ["api-design", "error-handling", "security"]
```

#### `get_triggered_skills(user_input: str, max_skills: int = 3) -> List[Skill]`

Busca skills relevantes al input del usuario, basándose en keywords/trigger.

```python
skills = registry.get_triggered_skills("diseña una API REST")
# [Skill(name="api-design", ...), Skill(name="security", ...)]
```

#### `get_skill(name: str) -> Optional[Skill]`

Busca un skill por nombre.

```python
skill = registry.get_skill("api-design")
# Skill(name="api-design", trigger=["api", "rest", "endpoint"], ...)
```

#### `list_skills() -> List[str]`

Lista nombres de todos los skills registrados.

```python
names = registry.list_skills()
# ["api-design", "error-handling", "security", ...]
```

#### `add_on_reload_callback(callback: Callable[[List[str]], None]) -> None`

Registra callback que se ejecuta cuando los skills se recargan.

```python
def on_skills_reloaded(names):
    print(f"Skills recargados: {names}")

registry.add_on_reload_callback(on_skills_reloaded)
```

### Skill (Dataclass)

```python
@dataclass
class Skill:
    name: str                  # Identificador único
    description: str           # Descripción
    trigger: List[str]         # Keywords que activan el skill
    priority: int              # Prioridad (mayor = más relevante)
    content: str               # Contenido del skill (markdown)
    file_path: Optional[Path]  # Archivo de origen
```

Los skills se almacenan como archivos `.md` en `~/.lilith/skills/`.

---

## EnhancedMemory

**Módulo:** `Lilith.Memory.enhanced`
**Rol:** Sistema de memoria híbrido con embeddings, grafo, consolidación y retrieval.

### Obtener Instancia

```python
from Lilith.Memory.enhanced import get_memory

memory = get_memory()  # Singleton
```

### Episodios

#### `add_episode(user_input, response="", tools_used=None, session_id="default") -> int`

Agrega un episodio de conversación. Genera embedding, extrae entidades, actualiza grafo y encola para consolidación.

```python
episode_id = memory.add_episode(
    user_input="¿Cómo ordeno una lista en Python?",
    response="Puedes usar sorted() o list.sort()...",
    tools_used=["run_python_script"],
    session_id="20260501_143000"
)
# → 42
```

#### `get_recent_episodes(count=10, session_id=None) -> List[Dict]`

Obtiene episodios recientes, opcionalmente filtrados por sesión.

```python
recent = memory.get_recent_episodes(count=5)
# [{"id": 42, "user_input": "...", "response": "...", "timestamp": "..."}, ...]
```

#### `search_episodes(query: str, limit: int = 5) -> List[Dict]`

Búsqueda semántica por embeddings. Fallback a búsqueda de texto si no hay modelo.

```python
results = memory.search_episodes("ordenar lista Python")
# [{"id": 42, "user_input": "...", "response": "..."}, ...]
```

#### `get_relevant_context(query: str, max_tokens: int = 1200) -> str`

Retorna contexto relevante formateado para inyectar en el system prompt.

```python
context = memory.get_relevant_context("configurar git")
# "CONTEXTO RELEVANTE DE MEMORIA:\n- [2026-05-01] Tu: ¿cómo configuro git? | Lilith: ..."
```

### Compresión

#### `compress_old_episodes(keep_recent=50)`

Comprime episodios antiguos en resúmenes. Se ejecuta automáticamente cuando hay >100 episodios activos.

```python
memory.compress_old_episodes(keep_recent=50)
```

#### `get_summaries(limit=10) -> List[Dict]`

Obtiene resúmenes comprimidos.

```python
summaries = memory.get_summaries(limit=5)
```

### Entidades y Facts

#### `add_entity(name, entity_type, context="") -> int`

```python
memory.add_entity("Docker", "technology", "Mencionado en contexto de deployment")
```

#### `add_fact(category, key, value, confidence=1.0) -> int`

```python
memory.add_fact("preferences", "language", "español", confidence=0.9)
```

#### `get_facts(category=None) -> List[Dict]`

```python
facts = memory.get_facts("preferences")
# [{"key": "language", "value": "español", "confidence": 0.9}]
```

### Estadísticas

#### `get_stats() -> Dict`

```python
stats = memory.get_stats()
# {"episodes": 142, "compressed_episodes": 35, "summaries": 5,
#  "entities": 28, "facts": 12, "errors": 2}
```

---

## AgentManager

**Módulo:** `Lilith.Agents.agent_manager`
**Rol:** Gestión de sub-agentes especializados (Vanaheim).

### Obtener Instancia

```python
from Lilith.Agents.agent_manager import get_agent_manager

manager = get_agent_manager()
```

### Plantillas Predefinidas

| Template | Personalidad | Capacidades |
|----------|-------------|-------------|
| `researcher` | ANALYTICAL | RESEARCH, ANALYSIS, SUMMARIZATION |
| `coder` | PRACTICAL | CODING, CODE_REVIEW, DEBUGGING |
| `writer` | CREATIVE | WRITING, EDITING, TRANSLATION |
| `explainer` | EDUCATOR | EXPLANATION, SUMMARIZATION, COMPARISON |
| `critic` | CRITIC | ANALYSIS, CODE_REVIEW, CLASSIFICATION |

### Métodos Públicos

#### `create_agent(template=None, **kwargs) -> SubAgent`

Crea un sub-agente a partir de template o custom.

```python
# Desde template
agent = manager.create_agent("coder")

# Custom
agent = manager.create_agent(
    name="Mi Agente",
    description="Agente especializado",
    personality=AgentPersonality.ANALYTICAL,
    capabilities=[AgentCapability.CODING],
    system_prompt="Eres un experto en..."
)
```

#### `dehydrate_task(agent_id, task) -> Dict`

Delega una tarea a un agente. El agente usa el proveedor LLM configurado con su system prompt y temperatura.

```python
result = manager.dehydrate_task(
    agent_id="coder_001",
    task="Revisa este código y encuentra bugs"
)
# {"status": "completed", "result": "...", "execution_time": 3.2}
```

#### `list_agents() -> List[SubAgent]`

Lista todos los agentes registrados.

```python
agents = manager.list_agents()
for agent in agents:
    print(f"{agent.name}: {agent.success_rate:.1f}% success")
```

#### `get_agent(agent_id) -> Optional[SubAgent]`

```python
agent = manager.get_agent("coder_001")
```

#### `remove_agent(agent_id) -> bool`

```python
manager.remove_agent("coder_001")
```

### SubAgent (Dataclass)

```python
@dataclass
class SubAgent:
    id: str
    name: str
    description: str
    personality: AgentPersonality
    capabilities: List[AgentCapability]
    system_prompt: str
    tools: List[str]                  # Tools disponibles
    model_preference: Optional[str]   # Modelo LLM preferido
    temperature: float = 0.7
    max_tokens: int = 4096
    enabled: bool = True
    stats: Dict[str, Any]             # Estadísticas de uso
```

---

## SwarmManager

**Módulo:** `Lilith.Swarm.manager`
**Rol:** Orquestación de tareas multi-agente (enjambre).

### Obtener Instancia

```python
from Lilith.Swarm.manager import get_swarm_manager

swarm = get_swarm_manager()
```

### Métodos Públicos

#### `spawn_agent(task_desc, capabilities=None) -> SwarmAgent`

Crea un agente del enjambre para una tarea específica.

```python
agent = swarm.spawn_agent(
    task_desc="Analizar logs del servidor",
    capabilities=["analysis", "research"]
)
```

#### `distribute_task(task, strategy="round_robin", agent_ids=None) -> Dict`

Distribuye una tarea entre agentes del enjambre.

```python
result = swarm.distribute_task(
    task="Revisar PR #42",
    strategy="best_fit",
    agent_ids=["agent_1", "agent_2"]
)
```

#### `get_status() -> Dict`

Estado del enjambre completo.

```python
status = swarm.get_status()
# {"agents": 3, "active": 2, "idle": 1, "completed_tasks": 15}
```

#### `kill_agent(agent_id) -> bool`

Termina un agente del enjambre.

```python
swarm.kill_agent("agent_3")
```

#### `save_swarm(name) -> Dict` / `load_swarm(name) -> Dict`

Persiste/restaura el estado del enjambre.

```python
swarm.save_swarm("equipo_review")
swarm.load_swarm("equipo_review")
```

#### `get_history(limit=20) -> List[Dict]`

Historial de tareas completadas.

```python
history = swarm.get_history(limit=10)
```

---

## MCPManager

**Módulo:** `Lilith.MCP.manager`
**Rol:** Gestión del ciclo de vida de servidores Model Context Protocol.

### Obtener Instancia

```python
from Lilith.MCP.manager import get_mcp_manager

mcp = get_mcp_manager()
```

### Métodos Públicos

#### `start() -> None` (async)

Inicia todos los servidores MCP configurados en `config.toml`.

```python
await mcp.start()
```

#### `stop() -> None` (async)

Detiene todos los servidores MCP.

```python
await mcp.stop()
```

#### `get_tools() -> List[Dict]`

Lista las tools disponibles de todos los servidores MCP.

```python
tools = mcp.get_tools()
# [{"name": "mcp_tool_1", "description": "...", ...}, ...]
```

#### `call_tool(name, args) -> Any` (async)

Ejecuta una tool MCP.

```python
result = await mcp.call_tool("mcp_tool_name", {"param": "value"})
```

#### `get_status() -> Dict`

Estado de los servidores MCP.

```python
status = mcp.get_status()
# {"servers": [{"name": "filesystem", "status": "connected", "tools": 5}, ...]}
```

### MCPClient (Protocol)

Soporta dos transportes:

| Transporte | Config | Descripción |
|-----------|--------|-------------|
| `stdio` | `command`, `args`, `env` | Proceso hijo, comunicación por stdin/stdout |
| `http` | `url`, `headers` | Servidor HTTP con JSON-RPC |

Configuración en `config.toml`:

```toml
[[mcp.servers]]
name = "filesystem"
transport = "stdio"
command = "python3"
args = ["-m", "mcp_server_filesystem"]

[[mcp.servers]]
name = "remote_api"
transport = "http"
url = "http://localhost:8080/mcp"
```

---

## LilithConfig

**Módulo:** `Lilith.Core.toml_config`
**Rol:** Parser TOML — fuente única de verdad para toda la configuración.

### Obtener Instancia

```python
from Lilith.Core.toml_config import get_config

config = get_config()  # Singleton
```

### Acceso a Configuración

#### `get(key: str, default=None) -> Any`

Acceso con dotted keys a cualquier valor del TOML.

```python
# Valores simples
base_url = config.get("llm.providers.lm_studio.base_url")
# → "http://localhost:1234/v1"

max_calls = config.get("llm.max_tool_calls", default=25)
# → 25

# Secciones completas
providers = config.get("llm.providers", default={})
# → {"lm_studio": {...}, "kimi": {...}}
```

#### `set(key: str, value) -> None`

Establece un valor (en memoria, requiere `save()` para persistir).

```python
config.set("llm.streaming", True)
config.save()
```

#### `save() -> None`

Persiste la configuración actual al archivo TOML.

```python
config.set("dashboard.port", 9000)
config.save()
```

#### `reload() -> None`

Recarga la configuración desde el archivo TOML (descarta cambios no guardados).

```python
config.reload()
```

### Jerarquía

```
TOML file (~/.lilith/config.toml)
    ↓ get() → busca en TOML primero
Env vars (LILITH_*, KIMI_API_KEY, etc.)
    ↓ si no encuentra en TOML, busca en env
Defaults (hardcodeados en toml_config.py)
    ↓ si no hay en env, usa defaults
→ Valor final
```

### Auto-Creación

Si `~/.lilith/config.toml` no existe, `LilithConfig` lo crea con valores por defecto y estructura completa.

---

## LLMProvider

**Módulo:** `Lilith.Core.llm_provider`
**Rol:** Comunicación con proveedores LLM vía OpenAI-compatible API.

### Obtener Instancia

```python
from Lilith.Core.llm_provider import get_provider

provider = get_provider()  # Default (lm_studio con fallback a kimi)
provider = get_provider("kimi")  # Específico
```

### Métodos Públicos

#### `chat(messages: List[Dict], tools: List[Dict] = None) -> Dict`

Envía mensajes al LLM y retorna la respuesta completa. Incluye tool-calling si `tools` se proporciona.

```python
response = provider.chat(
    messages=[{"role": "user", "content": "Hola"}],
    tools=available_tools
)
# {"choices": [{"message": {"content": "...", "tool_calls": [...]}}]}
```

#### `chat_stream(messages: List[Dict], tools=None) -> Iterator[str]`

Streaming de la respuesta. No soporta tool-calling interactivo.

```python
for chunk in provider.chat_stream(messages):
    print(chunk, end="", flush=True)
```

#### `chat_with_tools(messages, tools) -> Dict`

Variante de `chat()` con énfasis en tool-calling.

#### `is_available() -> bool`

Verifica si el proveedor responde.

```python
if provider.is_available():
    # Proveedor listo
```

#### `test_all_providers() -> Dict[str, bool]`

Testea todos los proveedores configurados.

```python
results = provider.test_all_providers()
# {"lm_studio": True, "kimi": True}
```

### Fallback Automático

Si el proveedor primario no responde, el sistema intenta automáticamente con los proveedores alternativos en el orden configurado. El usuario puede forzar un proveedor con `orch.switch_provider("kimi")`.

---

## HybridRetriever

**Módulo:** `Lilith.Memory.memory_retrieval`
**Rol:** Retrieval híbrido para búsqueda en memoria.

### Pesos Configurables

```python
retriever = HybridRetriever(
    vector_weight=0.4,    # Similitud coseno en embeddings
    keyword_weight=0.3,   # Búsqueda FTS5 (BM25-like)
    graph_weight=0.2,     # Vecinos en grafo de conocimiento
    recency_weight=0.1,   # Decaimiento exponencial por recencia
)
```

### Métodos Públicos

#### `retrieve(query, limit=10, include_sources=False) -> List[Dict]`

Retrieval híbrido principal. Combina vector + keyword + graph + recency.

```python
episodes = retriever.retrieve("configurar git", limit=5, include_sources=True)
# [{"id": 42, "user_input": "...", "retrieval_score": 0.85, "retrieval_sources": {...}}, ...]
```

#### `retrieve_with_context(query, max_tokens=2000) -> str`

Retorna texto formateado listo para inyectar en prompt.

```python
context = retriever.retrieve_with_context("Python threads")
# "CONTEXTO RELEVANTE DE MEMORIA:\n- [2026-05-01] Tu: ... | Lilith: ..."
```

#### `vector_search(query, limit=20) -> List[Tuple[int, float]]`

Búsqueda pura por similitud de embeddings.

#### `keyword_search(query, limit=20) -> List[Tuple[int, float]]`

Búsqueda pura por keywords (FTS5).

#### `graph_search(query, limit=20) -> List[Tuple[int, float]]`

Búsqueda por relaciones en el grafo de conocimiento.

---

*«El Grimorio está abierto. Las invocaciones están documentadas. Que el viajero use este conocimiento con sabiduría — o con la debida imprudencia.»*
