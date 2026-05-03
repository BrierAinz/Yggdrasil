# MISIÓN: Lilith v2.3 — Modo Automático + Notificaciones + Dashboard

**Visión:** Lilith deja de ser reactiva y se vuelve proactiva: ejecuta tareas multi-paso sin intervención, monitorea el entorno en background y presenta métricas de uso en un dashboard integrado.

---

## Feature 1: Modo Automático (Auto-Mode)
- **Activación:** `/auto [objetivo]` o toggle ⚡ AUTO en la UI.
- **Backend:** `Backend/core/auto_mode/` — task_planner, task_executor, task_monitor, auto_mode_manager.
- **Eventos WS:** auto_plan_created, auto_task_started, auto_task_completed, auto_mode_done.
- **UI:** Tarjeta de plan, barra de progreso, ⏸ Pausar / ▶ Continuar.

## Feature 2: Notificaciones Proactivas
- **Backend:** `Backend/core/notifications/` — notification_engine, monitors (pattern, error, task, schedule), notification_store.
- **Tipos:** PATTERN_DETECTED, ERROR_RECURRING, TASK_REMINDER, INSIGHT, SUGGESTION.
- **API:** GET /api/notifications, POST /api/notifications/{id}/read.
- **UI:** Badge en header, drawer notificaciones, toast para urgentes.

## Feature 3: Dashboard de Métricas
- **Backend:** metrics_collector.py, GET /api/dashboard/stats.
- **Payload:** tokens, sesiones, agentes, memoria, auto_mode.
- **UI:** Botón 📊, 3 cards (tokens, sesiones, 4/4 agentes), donut uso agentes, bar sesiones/día, sección memoria.

---

## Plan de implementación
- **Fase A — Dashboard** ✅ (métricas completas + UI con donut/bar/memoria)
- **Fase B — Notificaciones** ✅ (engine, 4 monitores, API, badge, drawer, toast)
- **Fase C — Modo Automático** ✅ (planner, executor, monitor, eventos WS, UI plan/progreso, file_context)

---

## Lilith v2.3 — Completado

**Estado:** Cerrado. Todas las fases verificadas end-to-end.

| Feature | Estado | Notas |
|--------|--------|--------|
| Dashboard | ✅ | Métricas reales, recharts, botón 📊 en header |
| Notificaciones proactivas | ✅ | 4 monitores (ErrorPattern, TokenUsage, Inactivity, MemoryInsight), badge, drawer, toast |
| Modo automático | ✅ | `/auto [objetivo]`, TaskPlanner (Kimi) + file_context, TaskExecutor (Eva/Adán/Kimi), TaskMonitor, panel de progreso, resumen final en chat |
| Badge 💾 Aprendido | ✅ | Integrado en flujo |

**Verificación (logs Core):**
- `[Planner] Resuelto por ruta completa` para archivos en el objetivo (ej. `Backend/main.py`)
- `[AutoMode] file_context keys: ['Backend/main.py']` — contexto llega al executor
- Adán/Eva reciben código real en el prompt (~4k chars)

---

## Tests

**Suite:** Antes 114 passed · 45 failed · 8 skipped → Después **143 passed · 0 failed · 14 skipped**.

| Fix | Descripción |
|-----|-------------|
| Gemini | 8 tests → skip controlado (módulo deprecado) |
| WebBrowser | `cleanup()` → `close()` (o getattr) |
| SQLite PermissionError | Uso de `tmp_path` en phase4 y auto_workflow |
| Paths hardcodeados | `Path(__file__).resolve().parent.parent.parent` para raíz Lilith en Tests/fases/ |
| Tests async | `@pytest.mark.asyncio` en conversational_flow, general, lilith, ws_debug, websocket_chat |
| KeyError document_count | Schema flexible en stats (document_count / count / entero) |
| Auto_workflow umbrales | `MIN_SUCCESS_RATE` / `MIN_QUALITY_SCORE` + monkeypatch en tests |
| Legacy duplicados | Skip en test_auto_workflow.py, test_persona_auto_update.py (y fases) |
| UnicodeDecodeError | `open(..., encoding='utf-8')` en test_planning_engine |

**Comando:** `python -m pytest Tests/ --tb=no -q`

---
*2026-03-12 — v2.3 cerrada*
