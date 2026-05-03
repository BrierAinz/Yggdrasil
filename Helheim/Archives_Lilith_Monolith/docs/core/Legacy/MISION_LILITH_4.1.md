# Misión Lilith 4.1 — Inteligencia Expandida + Plugin System

**Fecha de implementación:** 2026-03-21
**Responsable:** Claude Code
**Estado:** ✅ Completada

---

## Resumen ejecutivo

Lilith 4.1 introduce dos ejes principales:

1. **Inteligencia expandida (D.10 + D.11):** El Planner ahora consulta MuninnDB antes de generar cualquier plan e inyecta facts relevantes como contexto enriquecido. Además, un job diario detecta patrones repetitivos en los episodios y sugiere automatizaciones al owner.

2. **Plugin System (E.13):** Arquitectura de plugins hot-reload que permite añadir tools, personas y transportes sin reiniciar Lilith.

---

## Bloques implementados

### D.10 — Context-aware Planning

**Archivos modificados:**
- `Core/Backend/core/planner.py` — métodos `_fetch_preemptive_context()` e `_inject_preemptive_context()`
- `Core/Config/planner.json` — sección `preemptive_retrieval`

**Cómo funciona:**

```
Usuario envía mensaje
       ↓
Planner.plan() inicia
       ↓
_fetch_preemptive_context(message)
  ├── MuninnDB.activate([message], vault="facts", top_k=5)
  └── Fallback: MemoryManager.search_context(message, limit=3)
       ↓
Genera bloque <relevant_context>…</relevant_context>
       ↓
_inject_preemptive_context(steps, ctx)
  └── Inyecta en param "context" de delegate_odin/eva/adan/cursor/kimi_cli/generate_reply
       ↓
Plan ejecutado con contexto histórico
```

**Configuración (`Config/planner.json`):**
```json
{
  "preemptive_retrieval": {
    "enabled": true,
    "muninn_top_k": 5,
    "semantic_top_k": 3,
    "context_template": "<relevant_context>\nRelevant facts from memory:\n{facts}\n</relevant_context>"
  }
}
```

**Reglas de inyección:**
- Solo afecta a tools de agentes: `delegate_odin`, `delegate_eva`, `delegate_adan`, `delegate_cursor`, `delegate_kimi_cli`, `delegate_shalltear`, `generate_reply`
- No sobreescribe contexto que ya tenga contenido
- No modifica tools de filesystem/web (`read_file`, `list_directory`, `web_search`, etc.)
- Si Muninn no está disponible o hay event loop activo (async), usa fallback semántico
- Si ninguna fuente retorna resultados, no inyecta nada (silencioso)

**Logs esperados:**
```
[Planner] Preemptive retrieval: 3 facts inyectados desde Muninn
[Planner] Preemptive retrieval: 2 facts desde semántica (fallback)
```

---

### D.11 — Aprendizaje Activo (Pattern Detection)

**Archivos nuevos:**
- `Core/Backend/core/learning/pattern_detector.py` — clase `PatternDetector`

**Archivos modificados:**
- `Core/Backend/core/task_scheduler.py` — job diario `pattern_analysis`
- `Core/Config/learning.json` — sección `pattern_detection`

**Cómo funciona:**

```
Job diario (08:30)
       ↓
PatternDetector.detect_and_notify()
       ↓
_load_recent_episodes(lookback_days=30)
  └── Lee episodic_log.jsonl filtrando por ventana temporal
       ↓
Agrupar por (tool, similarity_key)
  └── similarity_key = primeras 6 palabras significativas del resumen
       ↓
Detectar grupos con count >= min_occurrences (default: 3)
       ↓
Si notify_owner=True → Discord notify_owner() con sugerencias
```

**Configuración (`Config/learning.json`):**
```json
{
  "pattern_detection": {
    "enabled": true,
    "min_occurrences": 3,
    "lookback_days": 30,
    "notify_owner": true
  }
}
```

**Formato de sugerencia enviada al owner:**
```
💡 Sugerencias de automatización detectadas:

• He notado que la tarea 'revisar logs servidor' (tool: delegate_eva) se repite
  4 veces en los últimos 30 días. ¿Quieres que lo automatice con un monitor o
  tarea programada?
```

**Logs esperados:**
```
[PatternDetector] Found 2 repetitive tasks: ['revisar logs servidor', 'buscar actualizaciones']
[PatternDetector] Notificación enviada al owner con 2 sugerencias.
[Scheduler] pattern_analysis: 2 sugerencias generadas.
```

---

### E.13 — Plugin System

**Archivos nuevos:**
- `Core/Backend/core/plugin_manager.py` — `PluginManager` + `BasePlugin`
- `Core/Backend/plugins/` — carpeta de plugins
- `Core/Backend/plugins/example_weather_plugin.py` — plugin de ejemplo
- `Core/Backend/api/plugins_api.py` — endpoints REST de gestión
- `Core/Config/plugins.json` — registro y config de plugins

**Archivos modificados:**
- `Core/Backend/api/server.py` — registro del router de plugins

---

### Tests (22/22 ✓)

**Archivos nuevos:**
- `Core/Tests/test_context_aware_planning.py` — 10 tests (D.10 + D.11)
- `Core/Tests/test_plugin_system.py` — 12 tests (E.13)

```
pytest Tests/test_context_aware_planning.py Tests/test_plugin_system.py
→ 22 passed in ~4s
```

---

## Referencias

- `DEEP_DIVE_IMPLEMENTACION_4_0.md` — arquitectura base v4.0
- `PLUGIN_SYSTEM_GUIDE.md` — guía para crear plugins
- `CONTEXT_AWARE_PLANNING.md` — detalle técnico del preemptive retrieval
- `ROADMAP_HACIA_4.0.md` — mejoras D.10, D.11, E.13
