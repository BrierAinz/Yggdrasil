# 🏛️ Arquitectura de Lilith — Los Seis Reinos

> *El Yggdrasil es el árbol que sostiene los nueve mundos. Lilith, en su diseño, refleja esta estructura: cada módulo es un reino con su propia ley, pero todos se nutren de las mismas raíces.*

## Visión General del Ecosistema

```
                          ╔════════════════════════╗
                          ║    USUARIO (CLI)        ║
                          ║    El Viajero           ║
                          ╚════════╦═══════════════╝
                                   ║
                          ╔════════▼═══════════════╗
                          ║   LilithCLI (main.py)  ║
                          ║   El Portal              ║
                          ║  ─────────────────────  ║
                          ║  • Input loop            ║
                          ║  • /comandos slash       ║
                          ║  • ANSI themed output     ║
                          ║  • Session management     ║
                          ╚════════╦═══════════════╝
                                   ║
                          ╔════════▼═══════════════╗
                          ║  LilithOrchestrator     ║
                          ║   El Nexus               ║
                          ║  ─────────────────────  ║
                          ║  • chat() / chat_stream()║
                          ║  • Tool execution loop    ║
                          ║  • System prompt + mem   ║
                          ║  • Skill auto-trigger     ║
                          ║  • Registry coordination  ║
                          ╚════════╦═══════════════╝
                                   ║
          ┌────────────┬───────────╬───────────┬────────────┐
          │            │           │           │            │
    ╔═════▼════╗ ╔════▼═══╗ ╔════▼═══╗ ╔════▼═══╗ ╔═════▼════╗
    ║  Memory   ║ ║  LLM    ║ ║  Tools  ║ ║ Swarm   ║ ║   MCP    ║
    ║  Ecos    ║ ║ Oráculo ║ ║Invocac. ║ ║Enjambre ║ ║ Portales ║
    ║ del Más  ║ ║         ║ ║         ║ ║         ║ ║  Dimens. ║
    ║  Allá    ║ ║         ║ ║         ║ ║         ║ ║          ║
    ╚══════════╝ ╚═════════╝ ╚═════════╝ ╚═════════╝ ╚══════════╝
          │            │           │           │            │
    ╔════════════════════════════════════════════════════════════╗
    ║                El Grimorio (config.toml)                  ║
    ║              Fuente Única de Verdad                        ║
    ╚════════════════════════════════════════════════════════════╝
```

## Flow de Datos Principal

```
User Input
    │
    ▼
┌─────────────┐     ┌──────────────────────────────────────┐
│  LilithCLI   │────▶│         LilithOrchestrator           │
│  (main.py)   │     │                                      │
└─────────────┘     │  1. _build_system_prompt()            │
                      │     ├─ Base SYSTEM_PROMPT            │
                      │     ├─ + Memoria relevante            │
                      │     └─ + Skills activos               │
                      │                                      │
                      │  2. Enviar al LLM (chat/chat_stream) │
                      │     └─ LLMProvider con fallback      │
                      │                                      │
                      │  3. Si tool_calls en respuesta:      │
                      │     ├─ _execute_tool()               │
                      │     │   ├─ Native: TOOL_EXECUTORS    │
                      │     │   └─ MCP: DynamicToolRegistry  │
                      │     └─ Agregar resultado al contexto  │
                      │     └─ Volver a paso 2 (loop)         │
                      │                                      │
                      │  4. Guardar episodio en memoria       │
                      │     └─ EnhancedMemory.add_episode()   │
                      │                                      │
                      │  5. Retornar respuesta al CLI         │
                      └──────────────────────────────────────┘
```

## Los Seis Reinos — Descripción de Módulos

### 1. El Portal — `Lilith/main.py`

El punto de entrada. La interfaz CLI que el viajero utiliza para comunicarse con Lilith.

| Componente | Descripción |
|------------|-------------|
| `LilithCLI` | Clase principal del CLI. Gestiona el loop de input, comandos slash, themed output |
| `C` (Colors) | Códigos ANSI para tema dark fantasy: `C.HEAL` (verde), `C.CORRUPT` (rojo), `C.SHADOW` (gris), etc. |
| `S` (Styles) | Estilos de texto: `S.TITLE`, `S.ASSISTANT`, `S.PROMPT`, `S.DIM`, `S.INFO`, `S.WARNING`, `S.ERROR`, `S.SUCCESS` |

**CLI args:** `--no-banner`, `--streaming`, `--no-streaming`, `--model`, `--cwd`, `-v/--version`

### 2. El Nexus — `Lilith/Core/`

El corazón de Lilith. Coordina todos los reinos.

| Módulo | Rol |
|--------|-----|
| `orchestrator.py` | `LilithOrchestrator` — loop principal de chat, tool execution, inyección de memoria/skills |
| `llm_provider.py` | `LLMProvider` — Comunicación con LLMs vía OpenAI API, multi-provider con fallback |
| `dynamic_tools.py` | `DynamicToolRegistry` — Registro unificado de tools nativas + MCP |
| `skill_registry.py` | `SkillRegistry` — Carga y hot-reload de skills con auto-trigger |
| `config.py` | Capa retro-compat que deriva constantes del Grimorio (TOML) |
| `toml_config.py` | `LilithConfig` — Parser TOML, fuente única de verdad |

### 3. Ecos del Más Allá — `Lilith/Memory/`

Sistema de memoria híbrido con embeddings vectoriales, grafo de conocimiento y búsqueda full-text.

| Módulo | Rol |
|--------|-----|
| `enhanced.py` | `EnhancedMemory` — API principal: episodios, entidades, facts, consolidación |
| `memory_graph.py` | `MemoryGraph` (NetworkX) — Grafo de conocimiento con entidades y relaciones |
| `memory_consolidation.py` | `MemoryConsolidation` — Compresión y resumen automático de episodios antiguos |
| `memory_retrieval.py` | `HybridRetriever` — Búsqueda híbrida: vector + keyword (FTS5) + graph + recency |
| `base.py` | `EmbeddingModel` (sentence-transformers), `cosine_similarity`, rutas compartidas |

**Almacenamiento:** SQLite (`lilith_memory.db`) con tablas: `episodes`, `summaries`, `entities`, `facts`, `errors`.

**Embeddings:** `all-MiniLM-L6-v2` (sentence-transformers). Lazy loading — no bloquea si no está instalado.

### 4. Las Invocaciones — `Lilith/tools/`

Tools nativas organizadas en categorías. Cada módulo expone `get_tools()` (definiciones OpenAI) y `execute_tool(name, args)`.

| Categoría | Módulo | Tools principales |
|-----------|--------|-------------------|
| Archivos | `files.py` | `read_file`, `write_file`, `list_directory`, `file_exists` |
| Sistema | `system.py` | `run_terminal`, `open_vscode`, `open_application` |
| Red | `network.py` | `ping`, `check_port`, `download_file`, `check_internet`, `get_network_info` |
| Coding | `coding.py` | `run_git`, `run_npm`, `run_python_script`, `search_in_files`, `get_git_status`, `list_git_branches` |
| Browser | `browser.py` | `open_url`, `search_google`, `clipboard_read`, `clipboard_write`, `type_text`, `press_key`, `copy_to_clipboard` |
| Desktop | `desktop.py` | `screenshot`, `get_cursor_position`, `list_windows` |
| Windows | `windows.py` | `list_processes`, `kill_process`, `get_system_info`, `get_disk_space`, `list_services`, `start_service`, `stop_service` |
| Dashboard | `dashboard.py` | Control del dashboard web |
| Swarm | `swarm.py` | Comunicación con el enjambre |
| MCP Connect | `mcp_connect.py` | Bridge a servidores MCP |

### 5. El Enjambre — `Lilith/Swarm/`

Sistema multi-agente para delegación de tareas especializadas.

| Módulo | Rol |
|--------|-----|
| `manager.py` | `SwarmManager` — Orquestación de agentes, distribución de tareas |
| `agent.py` | `SwarmAgent`, `AgentStatus` — Agente individual con estado y comunicación |

### Sub-Agentes — `Lilith/Agents/`

Agentes especializados predefinidos.

| Módulo | Rol |
|--------|-----|
| `agent_manager.py` | `AgentManager`, `SubAgent`, `AgentCapability`, `AgentPersonality` — Gestión de sub-agentes |

**Plantillas:** researcher, coder, writer, explainer, critic — con capacidades y personalidades dedicadas.

### 6. Portales Dimensionales — `Lilith/MCP/`

Integración con Model Context Protocol para tools externas.

| Módulo | Rol |
|--------|-----|
| `manager.py` | `MCPManager` — Gestión del ciclo de vida de servidores MCP |
| `protocol.py` | `MCPClient` — Comunicación stdio/HTTP con servidores MCP |

### Módulos Complementarios

| Módulo | Directorio | Descripción |
|--------|------------|-------------|
| RAG | `Lilith/RAG/` | Indexación y búsqueda semántica de documentos |
| Scheduler | `Lilith/Scheduler/` | Tareas programadas (cron-like) |
| Plugins | `Lilith/Plugins/` | Sistema de plugins extensible |
| Dashboard | `Lilith/Dashboard/` | Web UI en tiempo real (aiohttp + WebSocket) |

## Diagrama de Relaciones entre Reinos

```
                ┌─────────────────┐
                │  El Grimorio     │
                │  (config.toml)   │
                │  FUENTE ÚNICA    │
                └────────┬────────┘
                         │
           ┌─────────────┼─────────────────┐
           │             │                 │
    ┌──────▼──────┐ ┌────▼─────┐  ┌───────▼──────┐
    │  LilithConfig│ │config.py │  │LLMProvider   │
    │  (toml_config│ │(retro-   │  │(providers,   │
    │   .py)       │ │compat)   │  │ fallback)    │
    └──────┬──────┘ └────┬─────┘  └───────┬──────┘
           │              │                │
           └──────────────┼────────────────┘
                          │
                   ┌──────▼──────┐
                   │Orchestrator │
                   │  El Nexus   │
                   └──────┬──────┘
                          │
        ┌─────────┬───────┼───────┬──────────┐
        │         │       │       │          │
  ┌─────▼──┐ ┌───▼───┐ ┌▼────┐ ┌▼─────┐ ┌──▼──────┐
  │Memory  │ │Skills │ │Tool │ │Swarm │ │Dashboard│
  │Enhanced│ │Registry│ │Reg. │ │Agent │ │ Server  │
  └────────┘ └───────┘ └──┬──┘ └──────┘ └─────────┘
                          │
                ┌─────────┼──────────┐
                │         │          │
          ┌─────▼──┐ ┌───▼────┐ ┌───▼────┐
          │ Native │ │  MCP   │ │Custom  │
          │ Tools  │ │Tools   │ │Executors│
          └────────┘ └────────┘ └────────┘
```

## El Grimorio — LilithConfig como Fuente Única de Verdad

La configuración de Lilith se gestiona desde **un único punto**: `~/.lilith/config.toml`, parseado por `LilithConfig`.

### Jerarquía de Configuración

```
┌──────────────────────────────────┐
│  Prioridad 1: config.toml        │  ←Fuente de verdad
│  (~/.lilith/config.toml)        │
├──────────────────────────────────┤
│  Prioridad 2: Variables de ent. │  ←Override (ej: KIMI_API_KEY)
│  (env vars)                     │
├──────────────────────────────────┤
│  Prioridad 3: Defaults          │  ←Valores hardcodeados
│  (en toml_config.py)           │
└──────────────────────────────────┘
```

### API Clave de LilithConfig

```python
from Lilith.Core.toml_config import get_config

config = get_config()

# Acceso con dotted keys
base_url = config.get("llm.providers.lm_studio.base_url")
max_calls = config.get("llm.max_tool_calls", default=25)

# Secciones completas
providers = config.get("llm.providers", default={})

# Guardar cambios
config.set("llm.streaming", True)
config.save()
```

El módulo `config.py` actúa como **capa retro-compat** que deriva constantes legacy del TOML:

```python
from Lilith.Core.config import SYSTEM_PROMPT, MAX_TOOL_CALLS, SKILLS_DIR
```

## DynamicToolRegistry — Registro Unificado

El `DynamicToolRegistry` es el registro centralizado que combina tools nativas y MCP:

```
┌────────────────────────────────────────┐
│        DynamicToolRegistry             │
│                                        │
│  ┌──────────────┐  ┌───────────────┐  │
│  │  Native Tools │  │   MCP Tools    │  │
│  │  (35+ funcs)  │  │  (dinámicas)   │  │
│  │              │  │               │  │
│  │ read_file    │  │ Per-servidor   │  │
│  │ run_terminal │  │ Auto-registro  │  │
│  │ ping         │  │ Lazy connect   │  │
│  │ ...          │  │               │  │
│  └──────┬───────┘  └───────┬───────┘  │
│         │                   │          │
│         └───────┬───────────┘          │
│                 │                      │
│          get_openai_tools()             │
│          execute(name, args)            │
│          get_stats()                    │
│          clear_mcp_tools()              │
└────────────────────────────────────────┘
```

**Características:**
- Registro unificado: nativas y MCP comparten el mismo namespace
- Búsqueda por nombre: `get_tool(name)` → `ToolInfo`
- Generación de schemas OpenAI: `get_openai_tools()` → lista para el LLM
- Ejecución bifurcada: nativa (síncrona) vs MCP ( asíncrona vía `_run_async`)
- Stats: `get_stats()` → conteo de tools nativas vs MCP

## Thread-Safety y Modelo de Concurrencia

Lilith utiliza un modelo híbrido de concurrencia:

### Threading

| Componente | Mecanismo | Detalle |
|------------|-----------|---------|
| `DynamicToolRegistry` | `threading.Lock` | Protege registro de tools durante add/remove/navigate |
| `SkillRegistry` | `threading.RLock` | Hot-reload de skills desde filesystem |
| `LLMProvider` | Thread-safe por diseño | Cada request es atómica vía `httpx` |
| `MCPManager` | `asyncio` en thread separado | Comunicación stdio/HTTP con servidores MCP |

### Async Bridge

```python
def _run_async(coro):
    """Ejecuta corrutina async desde contexto síncrono.

    Si ya hay un event loop corriendo, crea un thread nuevo.
    Si no, usa asyncio.run() directamente.
    """
```

Este patrón se usa en:
- Inicialización de MCP (`_try_init_mcp`)
- Ejecución de tools MCP
- Cierre de MCP (`close()`)

### Regla de Oro

> El `DynamicToolRegistry` usa un `threading.Lock` (`self._registry_lock`) que el Orchestrator adquiere antes de cualquier lectura/escritura del registry. Esto garantiza que las tools MCP pueden registrarse en runtime sin corromper la lista que el LLM está usando.

---

*«Los Seis Reinos no son islas aisladas sino raíces entrelazadas del mismo Yggdrasil. Cada invocación recorre el árbol completo antes de retornar al viajero.»*
