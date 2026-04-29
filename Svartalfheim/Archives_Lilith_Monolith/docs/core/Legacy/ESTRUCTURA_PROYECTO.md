# Estructura del proyecto Lilith

Resumen de carpetas y responsabilidades. Para una guía de arranque y visión general, ver **`Lilith/README.md`** (raíz del repo).

---

## Raíz del repo (`Lilith/`)

- **`arranque_lilith.bat`** — Inicia API (Core) y bot Discord en dos ventanas.
- **`cerrar_lilith.bat`** — Cierra los procesos de Lilith.
- **`README.md`** — Descripción del monorepo, estructura y cómo arrancar.

---

## Core (`Lilith/Core/`)

| Carpeta / archivo | Uso |
|-------------------|-----|
| **Backend/** | Lógica principal: `main.py` (IPC), `api/server.py` (FastAPI), `core/` (orchestrator, planner, tools_v3, memory, learning), `llm/`, `tools/`, `memory/`. |
| **Config/** | Configuración: `memory.json`, `security.json`, `discord_roles.json`, `intent_patterns.json`, `chained_tools.json`, `persona.md`. Ver `Config/README.md`. |
| **Data/** | Datos generados en ejecución: cache, `decision_audit.jsonl`, feedback, meta_report (no versionado en detalle). |
| **Memory/** | Persistencia de memoria (semántica, episódica, procedimental). |
| **Docs/** | Documentación: misiones 3.x, defensa inyección, estructura, fases. |
| **Tests/** | Tests (raíz y `fases/`). Ver `Tests/README.md`. |
| **Scripts/** | Scripts de utilidad: verify_*, audit_lilith, download_model, etc. |
| **Tools/** | Cliente IPC, carga de env; usado por la API. |
| **Frontend/** | SPA opcional (React/Vite). |
| **Workspace/** | Destrezas y talleres (skills, flujos). |
| **start_server.py** / **launch_lilith.bat** | Lanzadores desde Core (API y/o proceso main.py). |

---

## Discord (`Lilith/Discord/`)

- **bot.py** — Punto de entrada del bot (slash commands, eventos).
- **handlers/** — chat_handler, command_handler, notification_handler.
- **auth.py** — Roles (owner/trusted/public), lista de confianza.
- **config.py** / **.env** — Token, URL de la API, IDs de canal/servidor.

El bot **solo habla con la API por HTTP**; no importa módulos de Backend.

---

## Dependencias entre componentes

- **Discord → API** (HTTP a `LILITH_API_URL`).
- **API (server.py) → Backend** (imports de `Backend.*`; opcionalmente IPC al proceso `main.py`).
- **Config** leído por Backend y por la API (Config/ en Core).

---

## Nuevos módulos (sesión 2026-03-19, parte 1)

| Módulo | Ruta | Función |
|---|---|---|
| `working_memory.py` | `core/memory/` | WorkingMemory por canal (decay, pins) |
| `memory_router.py` | `core/memory/` | Write/search unificado con isolación Crystal |
| `session_summarizer.py` | `core/` | Resúmenes de sesión automáticos |
| `muninn_edges.py` | `core/` | Grafo JSONL de relaciones concept→concept |
| `muninn_triggers.py` | `core/` | Motor de trigger callbacks de MuninnDB |
| `muninn_trigger_api.py` | `api/` | POST /api/muninn/trigger |
| `agent_metrics.py` | `core/` | Métricas latencia/éxito por tool (RAM) |
| `agents_api.py` | `api/` | GET /api/agents/health y /stats |
| `prompt_template.py` | `core/agents/` | AgentPromptConfig composable |
| `fallback_chain.py` | `core/agents/` | Cadena de fallback configurable |
| `complexity_router.py` | `core/agents/` | Routing Adán→Eva por complejidad |
| `output_validator.py` | `core/agents/` | Validación heurística de salidas |
| `review_chain.py` | `core/agents/` | Revisión inter-agente (Albedo centinela) |

## Nuevos módulos (sesión 2026-03-19, parte 2 — Misiones 6–8)

| Módulo | Ruta | Función |
|---|---|---|
| `auto_delegate.py` | `core/` | AutoDelegateDetector: URLs en Telegram, scoring por dominio, rate limit 10/h |
| `nl_param_extractor.py` | `core/` | NLParamExtractor: LLM + heurísticas regex para filesystem ops |
| `exec_sandbox.py` | `core/` | ExecSandbox: kill tree, output cap 256KB/2000L, timeout configurable |
| `progress_manager.py` | `core/` | ProgressManager: colas por request_id, replay, step_callback |
| `pc_agent_tools.py` | `core/tools_v3/` | 8 LilithTools: pc_list/mkdir/move/copy/delete/write_file/exec/batch |
| `progress_ws.py` | `api/` | WebSocket `/ws/progress?request_id=X` con keepalive |
| `dashboard_api.py` | `api/` | Reescrito: 7 endpoints REST + SPA HTML dark theme embebida |

### Archivos de bot actualizados

| Archivo | Cambio |
|---|---|
| `Telegram/telegram_bot.py` | `_keep_typing()` loop en thread; typing activo durante llamadas largas |
| `Discord/handlers/chat_handler.py` | `request_id` por petición; `_listen_progress_ws()` actualiza placeholder en tiempo real |

### Configs actualizadas

| Archivo | Cambio |
|---|---|
| `Config/auto_delegate.json` | Campos para AutoDelegateDetector v2 (Telegram) |
| `Config/pc_agent.json` | Sección `"sandbox"` con timeout_s, max_output_bytes, max_lines |
| `Config/intent_patterns.json` | 7 intents pc_* (pc_list_dir, pc_mkdir, pc_move, pc_copy, pc_delete, pc_write_file, pc_exec) |

## Documentación relacionada

- `Lilith/README.md` — Visión general y arranque.
- `Core/Config/README.md` — Claves de `memory.json` y otros config.
- `Core/Config/discord_roles_checklist.md` — Checklist de permisos por rol.
- `Core/Docs/DEFENSA_INYECCION_PROMPTS.md` — Capas de seguridad (input, dominios, salida).
- `Core/Docs/MISION_LILITH_3.5.md` — Estado de la misión 3.5 y checklist de validación.
- `Core/Docs/ESTADO_ACTUAL_LILITH.md` — Estado técnico post-sesión 2026-03-19.
- `Core/Docs/CONTEXTO_CLAUDE_CODE.md` — Guía de contexto para Claude Code.
