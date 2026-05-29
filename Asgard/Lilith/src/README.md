# Backend

Lógica de backend para Lilith 3.x: orquestador, planificador, herramientas (tools_v3), agentes, memoria y API.

## Estructura

```
Backend/
├── main.py              # Proceso Core (IPC server, opcional)
├── api/                 # FastAPI: server.py, discord_api.py
├── core/                # Motor 3.0/3.5: orchestrator, planner, plan_executor, agent_caller,
│                       # tools_v3 (registry, file_*, delegate_*, memory), learning, input_sanitizer
├── tools/               # Herramientas (autonomous, enhanced, ecosystem)
├── memory/              # Logs, semantic_memory, session_manager
├── llm/                 # Clientes LLM (Ollama, Grok, Venice, Kimi)
├── observability/
└── _legacy/             # Código deprecado (no usar)
```

## Uso

Desde **`Lilith/Core/`** (con `PYTHONPATH` que incluya `Core`):

```bash
python -m Backend.main.py           # Proceso Core (IPC)
python -m Backend.api.server       # API REST + WebSocket
```

Desde la raíz del proyecto: usar `arranque_lilith.bat` (API + Discord) o `Core/launch_lilith.bat` (Core + API).

## Componentes principales (3.x)

- **Orchestrator** — Coordina Planner, PlanExecutor y MemoryManager.
- **Planner** — Genera planes (Steps) desde intent_patterns, clasificador y memoria procedimental.
- **PlanExecutor / AgentCaller** — Ejecutan pasos; cache de agentes, validación de parámetros.
- **ToolRegistryV3** — Catálogo de tools (lazy loading); read_file, edit_file, delegate_eva/adan/lucifer/odin, etc.
- **MemoryManager** — Memoria tri-capa (semántica, episódica, procedimental) y búsqueda unificada.

## Documentación

- `Core/Docs/MISION_LILITH_3.5.md` — Estado de la misión 3.5.
- `Core/Docs/DEFENSA_INYECCION_PROMPTS.md` — Validación de entrada, security.json, lista blanca dominios.
- `Core/Docs/ESTRUCTURA_PROYECTO.md` — Mapa del proyecto.
- `Core/Config/README.md` — memory.json y resto de configuración.
