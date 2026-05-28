# Contexto para Claude Code — Sesiones de desarrollo en Lilith

Este documento resume lo que Claude Code necesita saber para continuar trabajando en el proyecto sin necesidad de re-explorar desde cero.

---

## Dónde estamos

- **Versión**: Lilith 4.1 (tras sesión 2026-03-19, dos rondas)
- **Working dir del proyecto**: `D:/Proyectos/Yggdrasil/Asgard/Lilith/`
- **Directorio de Discord bot**: `D:/Proyectos/Yggdrasil/Asgard/Lilith/Discord/`
- **Directorio de Telegram bot**: `D:/Proyectos/Yggdrasil/Asgard/Lilith/Telegram/`
- **API Core**: `D:/Proyectos/Yggdrasil/Asgard/Lilith/Core/Backend/api/server.py` (FastAPI, puerto 8000)
- **Config**: `D:/Proyectos/Yggdrasil/Asgard/Lilith/Core/Config/`
- **Docs**: `D:/Proyectos/Yggdrasil/Asgard/Lilith/Core/Docs/`

---

## Archivos más importantes para retomar trabajo

| Archivo | Por qué importa |
|---|---|
| `Core/Backend/api/server.py` | Registro de todos los routers; startup con ensure_vaults |
| `Core/Backend/api/discord_api.py` | Handler principal Discord: planner, executor, confirms, progress |
| `Core/Backend/api/telegram_api.py` | Handler principal Telegram: NL completo, auto_delegate, historial, progress |
| `Core/Backend/api/dashboard_api.py` | Dashboard REST + SPA HTML embebida |
| `Core/Backend/api/progress_ws.py` | WebSocket `/ws/progress` para streaming de progreso |
| `Core/Backend/core/orchestrator.py` | process_message → plan → execute |
| `Core/Backend/core/planner.py` | Genera planes con Kimi, Muninn quality check |
| `Core/Backend/core/plan_executor.py` | Ejecuta steps, DAG, Albedo centinela, edges, progress_callback |
| `Core/Backend/core/agent_caller.py` | Delega a tools/agentes: fallback, metrics, review |
| `Core/Backend/core/muninn_memory.py` | Interface a MuninnDB: vaults, activate, write |
| `Core/Backend/core/muninn_edges.py` | Grafo de relaciones concept→concept (JSONL) |
| `Core/Backend/core/muninn_triggers.py` | Motor de trigger callbacks |
| `Core/Backend/core/session_summarizer.py` | Resúmenes de sesión automáticos |
| `Core/Backend/core/progress_manager.py` | Colas de progreso por request_id para WS |
| `Core/Backend/core/exec_sandbox.py` | Ejecución segura con kill tree y output cap |
| `Core/Backend/core/auto_delegate.py` | Detección de URLs en Telegram (v2) |
| `Core/Backend/core/nl_param_extractor.py` | Extracción NL de params de filesystem |
| `Core/Backend/core/tools_v3/pc_agent_tools.py` | 8 LilithTools que envuelven PCAgent |
| `Telegram/telegram_bot.py` | Bot de Telegram: typing loop, confirmaciones inline |
| `Discord/handlers/chat_handler.py` | Handler Discord: WS progress, request_id, placeholder |
| `Core/Config/memory.json` | Parámetros de memoria: decay, episodic, working memory |
| `Core/Config/muninn.json` | Vaults, triggers, proactive_multi_vault |
| `Core/Config/agents.json` | Fallback chains, strategy, error patterns |
| `Core/Config/auto_delegate.json` | Config AutoDelegateDetector v1 (Discord) y v2 (Telegram) |
| `Core/Config/pc_agent.json` | Config PC Agent, incluye sección `sandbox` |
| `Core/Config/intent_patterns.json` | 7 intents pc_* + todos los demás |

---

## Patrones de código importantes

### Fire-and-forget async desde sync
```python
from Backend.core.muninn_memory import _run_coro_fire_and_forget
_run_coro_fire_and_forget(MuninnMemory(base_path).write_agent_output(...))
```

### Leer vault antes de ejecutar agente
```python
memory_block = await MuninnMemory(base_path).get_agent_memory("agent_name", task)
system_prompt = system_prompt + "\n\n" + memory_block
```

### Escribir engrama después de ejecutar
```python
_run_coro_fire_and_forget(MuninnMemory(bp).write_agent_output("adan", task, result_text))
```

### Registrar edge de plan
```python
from Backend.core.muninn_edges import get_edge_manager
get_edge_manager(base_path).record_plan_edges(steps_dicts, user_intent)
```

### Confirmar/denegar como engrama
```python
await _record_confirmation_to_muninn("authorize"|"deny", plan_summary, message, transport)
get_edge_manager(_project_root()).record_confirmation_edge("authorize"|"deny", plan_summary, tool_names)
```

---

## Arquitectura de memoria (resumen)

```
ChromaDB ←→ vector_store.py        (chunks 450 chars, decay temporal)
MuninnDB ←→ muninn_memory.py       (per-agent vaults, hebbian, Why)
JSONL    ←→ episodic_store.py       (episodios, max 5000, 90 días)
JSONL    ←→ muninn_edges.py         (relaciones entre conceptos)
JSONL    ←→ session_summarizer.py   (resúmenes de sesión)
RAM      ←→ working_memory.py       (por canal, decay por mensaje)
```

---

## Endpoints disponibles (post sesión 2026-03-19)

| Endpoint | Módulo | Función |
|---|---|---|
| `POST /api/muninn/trigger` | `muninn_trigger_api.py` | Callback de MuninnDB |
| `GET /api/agents/health` | `agents_api.py` | Salud de agentes |
| `GET /api/agents/stats` | `agents_api.py` | Métricas de todos los tools |
| `GET /api/agents/stats/{tool}` | `agents_api.py` | Stats de un tool específico |
| `WS /ws/progress` | `progress_ws.py` | Streaming de progreso (param: request_id) |
| `GET /api/dashboard/` | `dashboard_api.py` | Dashboard HTML |
| `GET /api/dashboard/overview` | `dashboard_api.py` | Resumen del sistema |
| `GET /api/dashboard/agents` | `dashboard_api.py` | Métricas de agentes |
| `GET /api/dashboard/memory` | `dashboard_api.py` | Stats de memoria |
| `GET /api/dashboard/learning` | `dashboard_api.py` | Grafo de edges y aprendizaje |
| `GET /api/dashboard/sessions` | `dashboard_api.py` | Resúmenes de sesión |
| `GET /api/dashboard/audit/recent` | `dashboard_api.py` | Auditoría PC Agent |
| `GET /dashboard` | `server.py` | Redirect a `/api/dashboard/` |

## Patrones nuevos (v4.1)

### Progress callback en execute_steps
```python
# En api handlers (telegram_api.py / discord_api.py):
from Backend.core.progress_manager import get_progress_manager, ProgressEvent
_pm = get_progress_manager()
_request_id = _pm.create_request()

def _progress_cb(step_idx, sid, label):
    _pm.publish(ProgressEvent(request_id=_request_id, step=sid, status="running", pct=(step_idx+1)/total))

response = await asyncio.to_thread(
    orchestrator.execute_steps, steps, ..., progress_callback=_progress_cb
)
```

### ExecSandbox (reemplaza subprocess.run en pc_agent)
```python
from Backend.core.exec_sandbox import get_exec_sandbox
sb = get_exec_sandbox(base_path)
result = sb.run(args, cwd=cwd_str)
# result.ok, result.stdout, result.stderr, result.timed_out, result.elapsed_s
```

### AutoDelegateDetector (Telegram)
```python
from Backend.core.auto_delegate import get_auto_delegate_detector
delegation = get_auto_delegate_detector(_project_root()).detect(text, role="owner")
if delegation:
    if delegation["action"] == "ask_user":
        return respuesta_pregunta
    elif delegation["action"] == "auto_investigate":
        text = delegation["investigation_message"]  # override para planner
```

---

## Pendientes conocidos (post sesión 2026-03-19)

- [ ] Tests para los nuevos módulos (exec_sandbox, progress_manager, auto_delegate, pc_agent_tools)
- [ ] Integrar `PromptTemplate` en los agentes existentes (Odín, Eva, Adán usan strings monolíticos)
- [ ] Calibrar umbrales de `complexity_router.py` con datos reales de uso
- [ ] Añadir gráficas históricas al dashboard (actualmente solo estado actual, no series temporales)
- [ ] `muninn_edges` en prompts de agentes: buscar aristas relacionadas antes de delegar

---

## Convenciones del proyecto

- **Imports**: siempre relativos dentro de `Backend.*` cuando se importa desde `api/`; relativos (`.`) dentro de `core/`
- **Async**: la API es async; los agentes internos (Eva, Adán) son sync con `asyncio.to_thread` donde necesario
- **Config**: siempre leer de `Config/*.json` con `json_safe.safe_load(path, default={})` para robustez
- **Logging**: `logger = logging.getLogger("lilith.<modulo>")` — prefijo `lilith.` siempre
- **NUNCA hardcodear tokens/keys** — leer de env vars (`os.getenv(...)`)
