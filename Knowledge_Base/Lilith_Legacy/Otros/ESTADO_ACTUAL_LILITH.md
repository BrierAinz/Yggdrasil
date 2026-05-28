# Estado actual de Lilith — 2026-03-19

Documento de referencia rápida: dónde estamos, qué funciona, qué se acaba de implementar.

---

## Versión: Lilith 4.0 → 4.1 (post-sesión 2026-03-19)

---

## Stack técnico

| Componente | Tecnología |
|---|---|
| API principal | FastAPI (Python), puerto 8000 |
| Bot Discord | discord.py (Puerto `D:/Proyectos/Yggdrasil/Asgard/Lilith/Discord/`) |
| Bot Telegram | Servicio separado (handlers en `api/telegram_api.py`) |
| Memoria vectorial | ChromaDB local (`Core/Memory/chroma/`) |
| Memoria cognitiva | MuninnDB (REST, localhost:8475) |
| Memoria episódica | JSONL (`Core/Data/episodes.jsonl`) |
| Memoria trabajo | `WorkingMemory` en RAM, por canal |
| Planificador | `core/planner.py` (Kimi/OpenRouter) |
| Ejecutor | `core/plan_executor.py` + `core/agent_caller.py` |
| Orquestador | `core/orchestrator.py` |
| Scheduler | APScheduler en `core/task_scheduler.py` |

---

## Panteón de agentes

| Agente | Tool | Backend | Especialidad |
|---|---|---|---|
| Odín | `delegate_odin` | Kimi (OpenRouter) | Investigación, contexto largo |
| Eva | `delegate_eva` | Grok (xAI) | Análisis, creatividad |
| Adán | `delegate_adan` | Qwen 2.5 Coder 7B (Ollama local) | Código, scripts |
| Crystal | canal Discord público | OpenRouter + Ollama fallback | Asistente público |
| Albedo | interno | Lucifer/local | Centinela de calidad |
| Lucifer | `delegate_lucifer` | LM local (Ollama) | Respuestas rápidas |

---

## Memoria: estado actual (v4.0)

### Capas

```
ChromaDB (vectorial)
  ├── Chunks de 450 chars con timestamp
  ├── Temporal decay (half-life=30 días)
  └── Purge semanal (threshold=0.1)

MuninnDB (cognitiva, REST)
  ├── Vaults por agente: lilith, odin, eva, adan, crystal
  ├── Activación con campo "why" (bm25, hebbian, temporal)
  └── Trigger callbacks → /api/muninn/trigger

Episódica (JSONL)
  ├── Max 5000 episodios, retención 90 días
  ├── SessionSummarizer (inactividad 30 min, resúmenes en jsonl)
  └── Pre-purge: resume antes de borrar

WorkingMemory (RAM, por canal)
  ├── Decay 0.15/mensaje, min 0.05
  └── Pins (no decaen), patrón "recuerda que X"

MuninnEdges (JSONL: Data/muninn_edges.jsonl)
  └── Relaciones entre conceptos: intent→tool, tool_sequence, confirmación
```

---

## Flujo de mensajes (simplificado)

```
Usuario → Discord/Telegram
  → API handler (discord_api.py / telegram_api.py)
    → WorkingMemory.extract + SessionSummarizer.record_activity
    → Orchestrator.process_message
      → Planner (Kimi) → Plan [Step, ...]
      → PlanExecutor.run_plan
        → AgentCaller.execute (con FallbackChain + ComplexityRouter + OutputValidator)
        → MuninnEdges.record_plan_edges
    → Response → bot → usuario
```

---

## Scheduler (jobs activos)

| Job | Frecuencia | Función |
|---|---|---|
| learning_consolidation | Cada 6h | Consolida aprendizaje |
| episodic_cleanup | Diario 03:00 | Purga episodios viejos (pre-purge: summary) |
| chromadb_purge | Lunes 04:00 | Purga vectores decaídos |
| session_summarizer_check | Cada 15 min | Detecta inactividad y resume sesiones |

---

## Configuraciones clave

- `Core/Config/memory.json` — schema v4.0: decay, working memory, session summarizer
- `Core/Config/muninn.json` — per-agent vaults, triggers, proactive_multi_vault
- `Core/Config/agents.json` — fallback_chains, fallback_strategy, max_fallback_attempts
- `Core/Config/planner.json` — scratchpad, max_web_steps, dag config
- `Core/Config/crystal.json` — OpenRouter key, fallback Ollama

---

## Nuevos módulos (sesión 2026-03-19)

| Módulo | Ruta | Función |
|---|---|---|
| `working_memory.py` | `core/memory/` | WorkingMemory por canal |
| `memory_router.py` | `core/memory/` | Write/search unificado |
| `session_summarizer.py` | `core/` | Resúmenes de sesión automáticos |
| `muninn_edges.py` | `core/` | Grafo de relaciones (JSONL) |
| `muninn_triggers.py` | `core/` | Motor de trigger callbacks |
| `muninn_trigger_api.py` | `api/` | POST /api/muninn/trigger |
| `agent_metrics.py` | `core/` | Métricas de latencia/éxito por tool |
| `agents_api.py` | `api/` | GET /api/agents/health y /stats |
| `agents/prompt_template.py` | `core/agents/` | PromptTemplate composable |
| `agents/fallback_chain.py` | `core/agents/` | Cadena de fallback configurable |
| `agents/complexity_router.py` | `core/agents/` | Routing Adán→Eva por complejidad |
| `agents/output_validator.py` | `core/agents/` | Validación heurística de salidas |
| `agents/review_chain.py` | `core/agents/` | Revisión inter-agente (Albedo) |
| `auto_delegate.py` | `core/` | Detección de URLs en Telegram (auto-investigación) |
| `nl_param_extractor.py` | `core/` | Extracción NL de parámetros de filesystem |
| `exec_sandbox.py` | `core/` | Ejecución segura con kill de árbol y output cap |
| `progress_manager.py` | `core/` | Streaming de progreso por request_id (WS) |
| `pc_agent_tools.py` | `core/tools_v3/` | PC Agent como LilithTools (8 tools pc_*) |
| `progress_ws.py` | `api/` | WebSocket `/ws/progress?request_id=X` |
| `dashboard_api.py` | `api/` | Dashboard completo (7 endpoints + SPA HTML) |

---

## Flujo de mensajes — Telegram (v4.1)

```
Owner escribe en Telegram (texto libre, sin comandos)
  → telegram_bot.py: _keep_typing() (loop en thread)
  → POST /api/telegram/chat {text, chat_id, request_id}
    → SessionSummarizer.record_activity
    → AutoDelegateDetector.detect(text)
      → Si URL conocida: override text con investigation_message
      → Si URL desconocida: devuelve pregunta al owner
    → Historial conversacional inyectado en system_prompt
    → Planner.plan(text) → Steps
    → _plan_needs_confirmation(steps)?
      → SÍ: genera token, devuelve plan_preview con botones inline
      → NO: execute_steps(steps, progress_callback=_progress_cb)
        → ProgressManager.publish(ProgressEvent) por step
    → _append_history(chat_id, "assistant", response)
  → telegram_bot.py: inline keyboard si requires_confirmation
  → _stop_typing.set()
```

## Flujo de progreso — WebSocket

```
Bot Discord genera request_id = uuid.hex
Bot abre ws://localhost:8000/ws/progress?request_id=X  ← suscribe cola
Bot POST /api/discord/chat {text, request_id, ...}
  → Backend execute_steps con progress_callback
    → progress_callback(i, tool_name, label)
      → ProgressManager.publish(ProgressEvent(request_id, step, "running", pct))
      → WS recibe → bot edita: "🔮 [████░░░░░░] eva…"
  → Al terminar: publish(status="done", pct=1.0)
Bot cancela WS task, borra placeholder, envía embed final
```

---

## APIs disponibles (resumen)

| Método | Ruta | Función |
|---|---|---|
| POST | `/api/telegram/chat` | Chat de Telegram |
| POST | `/api/telegram/confirm` | Confirmación de plan |
| POST | `/api/discord/chat` | Chat de Discord |
| POST | `/api/discord/confirm` | Confirmación de plan |
| POST | `/api/muninn/trigger` | Trigger de MuninnDB |
| GET | `/api/agents/health` | Salud de agentes |
| GET | `/api/agents/stats` | Métricas de tools |
| WS | `/ws/progress` | Streaming de progreso |
| GET | `/api/dashboard/` | Dashboard HTML |
| GET | `/api/dashboard/overview` | Resumen sistema |
| GET | `/api/dashboard/agents` | Métricas agentes |
| GET | `/api/dashboard/memory` | Stats de memoria |
| GET | `/api/dashboard/learning` | Grafo de edges |
| GET | `/api/dashboard/sessions` | Resúmenes de sesión |
| GET | `/api/dashboard/audit/recent` | Auditoría PC Agent |
| GET | `/dashboard` | Redirect → dashboard |
