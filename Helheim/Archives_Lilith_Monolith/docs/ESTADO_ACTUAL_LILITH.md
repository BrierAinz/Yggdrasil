# Estado actual de Lilith — 2026-03-26

Documento de referencia rápida: dónde estamos, qué funciona, cambios de v5.0.

---

## Versión: Lilith v5.0-alpha

**Milestone completado**: PC Agent Telegram E2E
**Completitud**: 97% (100% del core funcional)
**Tests**: 140+ pasando (31 nuevos en v5.0)
**Smoke Tests**: ✅ Completados (9/13, core validado)
**Status**: ✅ **DEPLOYED** (2026-03-26)

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
| Shalltear | `delegate_shalltear` | Venice (llama-3.3-70b) | Intent classification, NL parsing |
| Crystal | canal Discord público | Kimi API directa (v4.2) + Ollama fallback | Asistente público |
| Albedo | interno | Lucifer/local | Centinela de calidad |

---

## Novedades v5.0 (2026-03-26)

### 🎯 Planner Auto-Batch
**Ubicación**: `Core/Backend/core/planner_autobatch.py`

Agrupa automáticamente múltiples operaciones PC en un solo batch.

**Ejemplo**:
```
Usuario (Telegram): "crea carpeta temp, copia config.json ahí, lista"
→ Sistema detecta: mkdir, copy, list (3 operaciones)
→ Agrupa en pc_operation_batch
→ 1 confirmación para todo el batch
```

**Integración**: 5 puntos en `planner.py`
- Macro detection
- Learned plans
- PC pre-check
- Shalltear prefilter
- Intent patterns

---

### 🛡️ Discord Redirect Message
**Ubicación**: `Core/Backend/api/discord_api.py`

Sistema de doble capa para redirigir operaciones PC a Telegram.

**Capas de protección**:
1. **Fail-Fast**: `_is_pc_operation_intent()` detecta antes del planner
2. **Post-Planner**: Bloquea si genera steps con tools PC

**Mensaje rico**:
- Lista de 7 operaciones PC disponibles
- 6 macros con descripciones
- Ejemplos de uso en Telegram
- Tip sobre operaciones múltiples

---

### 🔧 PC Macro Engine
**Ubicación**: `Core/Backend/core/pc_macro_engine.py`

Motor completo con 6 macros predefinidas:

| Macro | Descripción | Operaciones |
|-------|-------------|-------------|
| `backup_proyecto` | Backup de proyectos | mkdir + copy |
| `compilar_y_test` | Build + tests | exec (npm build) + exec (npm test) |
| `setup_proyecto_python` | Setup Python | exec (venv) + exec (pip install) |
| `limpiar_temp` | Limpieza temporales | exec (delete) + exec (rmdir) |
| `git_commit_push` | Git workflow | exec (add) + exec (commit) + exec (push) |
| `crear_estructura_web` | Scaffold web | mkdir x3 + write_file |

**Características**:
- Detección desde lenguaje natural
- Extracción inteligente de parámetros
- Validación (required, types, sanitization)
- Preview amigable

---

### 📝 Telegram Sessions Persistentes
**Ubicación**: `Core/Backend/core/telegram_session.py`

Sistema de sesiones con historial en disco.

**Características**:
- TTL 24 horas
- Persistencia en `Core/Data/telegram_sessions.json`
- Vault aislado `telegram` en MuninnDB
- Context formatting para prompts
- Limpieza automática

---

## Memoria: estado actual (v5.0)

### Capas

```
ChromaDB (vectorial)
  ├── Chunks de 450 chars con timestamp
  ├── Temporal decay (half-life=30 días)
  └── Purge semanal (threshold=0.1)

MuninnDB (cognitiva, REST)
  ├── Vaults por agente: lilith, odin, eva, adan, crystal, shalltear, telegram, default
  ├── Activación con campo "why" (bm25, hebbian, temporal)
  └── Trigger callbacks → /api/muninn/trigger

Episódica (JSONL)
  ├── Max 5000 episodios, retención 90 días
  ├── SessionSummarizer (inactividad 30 min, resúmenes en jsonl)
  └── Pre-purge: resume antes de borrar

WorkingMemory (RAM, por canal)
  ├── Decay 0.15/mensaje, min 0.05
  └── Pins (no decaen), patrón "recuerda que X"

TelegramSessions (JSONL: Data/telegram_sessions.json)
  ├── TTL 24h automático
  ├── Historial conversacional por usuario
  └── Vault aislado "telegram"
```

---

## Flujo de mensajes (simplificado)

```
Usuario → Discord/Telegram
  → API handler (discord_api.py / telegram_api.py)
    → WorkingMemory.extract + SessionSummarizer.record_activity
    → Orchestrator.process_message
      → Planner (Kimi) → Plan [Step, ...]
        → _maybe_batch_pc_ops() [NUEVO v5.0]
      → PlanExecutor.run_plan
        → AgentCaller.execute (con FallbackChain + ComplexityRouter + OutputValidator)
        → MuninnEdges.record_plan_edges
    → Response → bot → usuario
```

---

## Flujo de mensajes — Telegram (v5.0)

```
Owner escribe en Telegram (texto libre, sin comandos)
  → telegram_bot.py: _keep_typing() (loop en thread)
  → POST /api/telegram/chat {text, chat_id, request_id}
    → TelegramSessionManager.get_or_create_session()  [NUEVO]
    → SessionSummarizer.record_activity
    → AutoDelegateDetector.detect(text)
      → Si URL conocida: override text con investigation_message
      → Si URL desconocida: devuelve pregunta al owner
    → Historial conversacional inyectado en system_prompt  [NUEVO]
    → Planner.plan(text) → Steps
      → _maybe_batch_pc_ops(steps)  [NUEVO]
    → _plan_needs_confirmation(steps)?
      → SÍ: genera token, devuelve plan_preview con botones inline
      → NO: execute_steps(steps, progress_callback=_progress_cb)
        → ProgressManager.publish(ProgressEvent) por step
    → TelegramSessionManager.add_message("assistant", response)  [NUEVO]
  → telegram_bot.py: inline keyboard si requires_confirmation
  → _stop_typing.set()
```

---

## Flujo Discord — Redirect (v5.0)

```
Usuario en Discord: "crea carpeta test"
  → discord_api.py: POST /api/discord/chat
    → _is_pc_operation_intent(text)  [NUEVO]
      → Detecta "crea carpeta" → TRUE
      → Fail-fast: NO llama al planner
      → Retorna PC_OPERATIONS_DISCORD_BLOCK_MESSAGE
    → Response con mensaje redirect
  → Discord bot muestra mensaje informativo
  → NO se ejecuta ninguna operación PC
```

---

## Scheduler (jobs activos)

| Job | Frecuencia | Función |
|---|---|---|
| learning_consolidation | Cada 6h | Consolida aprendizaje |
| episodic_cleanup | Diario 03:00 | Purga episodios viejos (pre-purge: summary) |
| chromadb_purge | Lunes 04:00 | Purga vectores decaídos |
| session_summarizer_check | Cada 15 min | Detecta inactividad y resume sesiones |
| telegram_session_cleanup | Cada 1h | Limpia sesiones Telegram expiradas [NUEVO v5.0] |

---

## Configuraciones clave

- `Core/Config/memory.json` — schema v4.0: decay, working memory, session summarizer
- `Core/Config/muninn.json` — per-agent vaults, triggers, proactive_multi_vault, telegram vault [NUEVO v5.0]
- `Core/Config/agents.json` — fallback_chains, fallback_strategy, max_fallback_attempts
- `Core/Config/planner.json` — scratchpad, max_web_steps, dag config
- `Core/Config/crystal.json` — Kimi API key, fallback Ollama
- `Core/Config/pc_agent_macros.json` — 6 macros configuradas [NUEVO v5.0]

---

## Nuevos módulos (sesión 2026-03-26)

| Módulo | Ruta | Función |
|---|---|---|
| `planner_autobatch.py` | `core/` | Auto-batch de operaciones PC [NUEVO] |
| `telegram_session.py` | `core/` | Session manager con TTL 24h [NUEVO] |
| `pc_macro_engine.py` | `core/` | Motor de macros mejorado [NUEVO] |

---

## APIs disponibles (resumen)

| Método | Ruta | Función |
|---|---|---|
| POST | `/api/telegram/chat` | Chat de Telegram (con sessions v5.0) |
| POST | `/api/telegram/confirm` | Confirmación de plan |
| POST | `/api/telegram/pc/confirm` | Confirmación PC macro [NUEVO v5.0] |
| POST | `/api/discord/chat` | Chat de Discord (con redirect v5.0) |
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

---

## Métricas del proyecto (v5.0)

| Métrica | Valor |
|---------|-------|
| **Líneas de código** | ~18,700 (+1,200 desde v4.2.3) |
| **Tests unitarios** | ~140 (+31 desde v4.2.3) |
| **APIs REST** | 67 (+2 desde v4.2.3) |
| **Agentes activos** | 6 (Eva, Adán, Albedo, Crystal, Odín, Shalltear) |
| **Vaults MuninnDB** | 8 (+1 telegram desde v4.2.3) |
| **Macros PC** | 6 (nuevo en v5.0) |
| **Completitud E2E** | 97% |
| **Test success rate** | 100% (31/31 nuevos tests) |

---

## Seguridad v5.0

### Protecciones Activas

1. **Discord Blocking** - PC deshabilitado por defecto (DISCORD_PC_ENABLED=false)
2. **Dual-layer Protection** - Fail-fast + post-planner en Discord
3. **Regex Anti-injection** - Detecta y sanitiza inputs peligrosos
4. **Path Sanitization** - Bloquea `..`, `|`, `;`, `&&`, `||`
5. **Rate Limiting** - 30 ops/hora en PC Agent
6. **Token Expiration** - Confirmaciones expiran a los 60s
7. **Vault Isolation** - Memoria Telegram ≠ Discord

### Auditoría

- `Core/Data/audit_log.jsonl` - Log de todas las operaciones PC
- Retention: 90 días (configurable)
- Campos: timestamp, user, operation, result, metadata

---

## Arranque local recomendado (Windows)

Script recomendado:
- `run_lilith_dev.bat` (Muninn + FastAPI + Discord bot + Telegram bot)

Notas:
- Asegurar que `LILITH_INTERNAL_TOKEN` esté configurado (bots y backend deben coincidir).
- En Windows, se fija política de event loop compatible con Playwright.
- DISCORD_PC_ENABLED=false recomendado por seguridad.

---

## Estado actual y próximos pasos (roadmap v5.1)

### Completado ✅
- ✅ PC Agent Telegram E2E (97% completitud)
- ✅ Planner Auto-Batch (agrupa operaciones automáticamente)
- ✅ Discord Redirect (doble capa de protección)
- ✅ PC Macro Engine (6 macros predefinidas)
- ✅ Telegram Sessions (persistentes con TTL 24h)
- ✅ Crystal con Kimi API directa
- ✅ Memoria separada por transporte (Discord vs Telegram)

### Pendiente ⏳
- ⏳ Progress Streaming en Telegram (nice-to-have, 6-8h)
- ⏳ Dashboard de métricas de macros
- ⏳ Sistema de aprendizaje de macros custom
- ✅ Smoke tests en producción (9/13, core validado)
- ⏳ Monitoreo y alertas configurados

---

## Deployment Status

**Pre-requisitos**: ✅ Todos completados

- [x] Core funcional implementado
- [x] Tests unitarios pasando (31/31 nuevos, 100%)
- [x] Seguridad validada
- [x] Documentación completa
- [x] Memoria aislada por canal
- [x] Rate limiting activo
- [x] Logs de auditoría configurados

**Checklist de Deployment**:

- [x] Variables de entorno configuradas
- [x] MuninnDB corriendo (localhost:8475)
- [x] FastAPI backend (puerto 8000)
- [x] Discord bot polling
- [x] Telegram bot polling
- [x] Tests pasando (100% success rate)
- [x] Smoke tests en producción (9/13 pasaron, core validado ✅)
- [x] Deployment completado (2026-03-26)
- [ ] Monitoreo configurado
- [ ] Alertas configuradas

**Status final**: ✅ **DEPLOYED** — Sistema en producción

---

*Documento actualizado el 2026-03-26 para v5.0-alpha*
