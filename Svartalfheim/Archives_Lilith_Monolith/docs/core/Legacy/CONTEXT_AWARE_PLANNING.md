# Context-Aware Planning — Referencia técnica (D.10 + D.11)

**Versión:** 4.1
**Archivos principales:**
- `Core/Backend/core/planner.py`
- `Core/Backend/core/learning/pattern_detector.py`

---

## D.10 — Preemptive Retrieval

### ¿Por qué?

Antes de 4.1, el Planner generaba planes sin consultar la memoria histórica. Cada request comenzaba "en blanco", ignorando facts o episodios relevantes que Lilith ya conocía. Esto producía respuestas repetitivas y planes sin contexto.

Con D.10, el Planner consulta MuninnDB **antes de planear** y enriquece el contexto de los agentes con información histórica relevante.

### Flujo detallado

```
Planner.plan(message)
    │
    ├─ _fetch_preemptive_context(message)
    │       │
    │       ├─ 1) Intentar MuninnDB (sincrónico si no hay event loop)
    │       │       └─ activate([message], vault="facts", max_results=5)
    │       │           → [{"concept": "...", "content": "...", "score": 0.8}, ...]
    │       │
    │       ├─ 2) Fallback: memoria semántica local (si Muninn no disponible)
    │       │       └─ memory_manager.search_context(message, limit=3)
    │       │
    │       └─ 3) Formatear como bloque XML
    │               → "<relevant_context>\n- concepto: contenido\n</relevant_context>"
    │
    ├─ Ejecutar fases normales (macros, classifier, shalltear, intent_patterns, fallback)
    │
    └─ _inject_preemptive_context(steps, ctx)
            └─ Para cada step con tool_name en AGENT_TOOLS y context vacío:
                   step.params["context"] = ctx
```

### Cuándo se usa cada fuente

| Situación | Fuente usada |
|-----------|-------------|
| No hay event loop activo (sync context) | MuninnDB primero |
| Hay event loop activo (async, e.g. request FastAPI) | Skip Muninn (no bloqueamos) → semántica |
| Muninn desactivado (`enabled=false`) | Semántica |
| Muninn error de conexión | Semántica |
| Sin memory_manager | Ninguna (context vacío) |
| Sin resultados en ninguna fuente | Context vacío (sin inyección) |

### Tools que reciben el contexto

El contexto se inyecta solo en tools de agentes con `context` vacío:

```python
_agent_tools = {
    "delegate_odin", "delegate_eva", "delegate_adan",
    "delegate_cursor", "delegate_kimi_cli",
    "delegate_shalltear", "delegate_odin_creative",
    "generate_reply",
}
```

No se modifica: `read_file`, `list_directory`, `web_search`, `lore_extractor`, `store_semantic_fact`, `pc_*`, ni ninguna tool que ya tenga context con contenido.

### Configuración

```json
// Core/Config/planner.json
{
  "preemptive_retrieval": {
    "enabled": true,          // Activar/desactivar globalmente
    "muninn_top_k": 5,        // Máx facts desde Muninn
    "semantic_top_k": 3,      // Máx facts desde semántica (fallback)
    "context_template": "<relevant_context>\nRelevant facts from memory:\n{facts}\n</relevant_context>"
  }
}
```

Para desactivar sin modificar código:
```json
{"preemptive_retrieval": {"enabled": false}}
```

### Ejemplo de bloque inyectado

```xml
<relevant_context>
Relevant facts from memory:
- arquitectura: El proyecto Lilith usa FastAPI como servidor web principal
- muninn: MuninnDB almacena memories cognitivas con scoring hebbian/temporal
- discord: El bot Discord usa threads separados por usuario para contexto
</relevant_context>
```

Este bloque aparece en el param `context` del Step antes de enviarlo al agente (Odín, Eva, etc.).

### Rendimiento

- Sin event loop: add ~10-100ms (request HTTP a MuninnDB local)
- Con event loop: 0ms overhead (skip automático → usa semántica en thread)
- La semántica local: <5ms (ChromaDB local)
- Si ambas fallan: 0ms (silencioso)

El preemptive retrieval **nunca bloquea ni retrasa** el planning en contexto async.

---

## D.11 — Aprendizaje Activo (Pattern Detector)

### ¿Por qué?

Lilith registra episodios en `episodic_log.jsonl` por cada interacción. Con D.11, analiza ese log periódicamente para detectar tareas que el usuario repite y sugerir automatizarlas.

### Algoritmo de detección

```python
# 1. Cargar episodios de los últimos N días
episodes = load_recent_episodes(lookback_days=30)

# 2. Para cada episodio, calcular:
#    - tool: extraída de tags (tag "tool:xxx") o source
#    - similarity_key: primeras 6 palabras significativas del resumen

# 3. Agrupar en dict: (tool, similarity_key) → {count, examples}

# 4. Filtrar grupos con count >= min_occurrences (default: 3)

# 5. Generar sugerencias de texto legible
```

**similarity_key:** elimina stop words (el/la/de/en/a/y/o/que/se/es) y toma las 6 primeras palabras restantes, en minúsculas. Esto agrupa variaciones del mismo resumen.

Ejemplo:
- "Revisar los logs del servidor de producción" → `"revisar logs servidor produccion"`
- "Revisar logs del servidor" → `"revisar logs servidor"`
→ Agrupados como el mismo patrón.

### Job diario

Registrado en `TaskScheduler` como job cron:
```
ID: pattern_analysis
Trigger: cron hora=8, minuto=30
→ PatternDetector(base_path).detect_and_notify()
```

### Configuración

```json
// Core/Config/learning.json
{
  "pattern_detection": {
    "enabled": true,
    "min_occurrences": 3,     // Mínimo de repeticiones para sugerir
    "lookback_days": 30,      // Ventana de análisis en días
    "notify_owner": true      // Enviar notificación vía Discord
  }
}
```

### Notificación al owner

```
💡 Sugerencias de automatización detectadas:

• He notado que la tarea 'revisar logs servidor' (tool: delegate_eva)
  se repite 5 veces en los últimos 30 días. ¿Quieres que lo automatice
  con un monitor o tarea programada?

• He notado que la tarea 'buscar actualizaciones dependencias'
  (tool: delegate_adan) se repite 3 veces en los últimos 30 días.
  ¿Quieres que lo automatice con un monitor o tarea programada?
```

### Logs

```
[PatternDetector] Found 2 repetitive tasks: ['revisar logs servidor', 'buscar actualizaciones']
[PatternDetector] Notificación enviada al owner con 2 sugerencias.
[Scheduler] pattern_analysis: 2 sugerencias generadas.
```

### Extensión futura

El `PatternDetector` devuelve objetos estructurados:
```python
[
  {
    "tool": "delegate_eva",
    "pattern": "revisar logs servidor",
    "count": 5,
    "examples": ["Revisar logs del servidor", "Revisa los logs del server"],
    "suggestion": "He notado que la tarea..."
  }
]
```

Se puede extender para:
- Crear automáticamente un `scheduled_tasks.json` entry
- Proponer un `source_monitors.json` entry
- Integrar con el sistema de DAGs (crear plan automático)

---

## Tests

```bash
# Ejecutar todos los tests de D.10 + D.11
pytest Core/Tests/test_context_aware_planning.py -v

# Tests individuales
pytest Core/Tests/test_context_aware_planning.py::TestPreemptiveRetrieval -v
pytest Core/Tests/test_context_aware_planning.py::TestPatternDetector -v
```

### Tests cubiertos

| Test | Qué verifica |
|------|--------------|
| `test_preemptive_context_disabled_by_config` | Config `enabled=false` → string vacío |
| `test_preemptive_context_with_semantic_fallback` | Muninn inactivo → usa semántica |
| `test_inject_into_delegate_step` | Inyecta en `delegate_odin` con context vacío |
| `test_inject_skips_non_agent_tools` | `read_file`, `list_directory` no modificados |
| `test_inject_skips_non_empty_context` | No sobreescribe context con contenido |
| `test_plan_sets_preemptive_context_attr` | `_preemptive_context` siempre existe en Planner |
| `test_plan_injects_context_in_fallback` | Context inyectado en plan fallback |
| `test_analyze_empty_store` | Sin episodios → lista vacía |
| `test_analyze_detects_repetitive_task` | 3+ episodios similares → sugerencia |
| `test_analyze_disabled_by_config` | Config `enabled=false` → lista vacía |
