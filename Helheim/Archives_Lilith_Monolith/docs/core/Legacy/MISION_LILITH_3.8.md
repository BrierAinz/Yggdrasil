# MISIÓN LILITH 3.8 — MEMORIA, APRENDIZAJE, FRAMEWORKS, TOOLS Y CONFIG

**Estado:** EN PROGRESO — Fase inicial implementada (config JSON, Planner, LearningEngine, timeouts, chained tools, README).

**Visión:** Puente hacia la 4.0: mejorar memoria, aprendizaje, frameworks, tools y config (JSON) sin abrir aún DAG ni memoria en grafo. La 3.8 concentra lo que acerca el sistema a un estado “4.0-ready” en configurabilidad, trazabilidad y preparación de datos.

**Base:** Misiones 3.6 y 3.7 (refinamiento, interacción, pipeline, trust, modelo híbrido, relay owner, intent public_roast). El detalle de cada propuesta está en **[ROADMAP_HACIA_4.0.md](ROADMAP_HACIA_4.0.md)**.

**Alcance 3.8:** Implementar las mejoras de **corto plazo** del roadmap (memoria, aprendizaje, config del planner/tools, JSON nuevos o ampliados, documentación de config). Las de **medio plazo** quedan como opcionales dentro de 3.8 o como backlog para 4.0.

---

## OBJETIVO GENERAL

- **Memoria:** Peso a hechos recientes, ampliar `query_synonyms`, opcional `thread_memory_priority_hint`; sentar base para indexación por tema y feedback → memoria.
- **Aprendizaje:** Config en `learning.json`, umbrales desde JSON; flujo para aplicar sugerencias de intents (con confirmación).
- **Frameworks:** Config del planner (prioridades, meta_questions, invalid_path_tokens) en JSON; timeouts por tool generalizados.
- **Tools:** Nuevas cadenas en `chained_tools.json`; opcional tool ligera (context/memory_search); opcional `tools.json` o registro por config.
- **Config y docs:** Nuevos o ampliados `learning.json`, `planner.json`, `tools.json`; ampliar `memory.json`; actualizar `Config/README.md` con tabla de JSON y versión de contrato donde aplique.

---

## BLOQUES DE TRABAJO (3.8)

### BLOQUE 1 — MEMORIA

| Id   | Área | Descripción |
|------|------|-------------|
| 1.1  | memory.json | Añadir `recent_facts_weight`, ampliar `query_synonyms`, opcional `thread_memory_priority_hint`. |
| 1.2  | Búsqueda semántica | Usar peso a hechos recientes (timestamp) si está configurado. |
| 1.3  | Export/backup hilo | Completar export de memoria de hilo a JSON si falta; opcional limpieza por antigüedad. |

### BLOQUE 2 — APRENDIZAJE

| Id   | Área | Descripción |
|------|------|-------------|
| 2.1  | learning.json | Crear `Config/learning.json` con `suggest_intents_threshold`, `feedback_reinforce_threshold`, `auto_apply_suggestions` (false). |
| 2.2  | LearningEngine | Leer umbrales desde learning.json en lugar de valores fijos en código. |
| 2.3  | Aplicar sugerencias | Endpoint o flujo (ej. desde /patrones) para añadir un intent sugerido a `intent_patterns.json` con confirmación. |

### BLOQUE 3 — FRAMEWORKS (PLANNER Y TOOLS)

| Id   | Área | Descripción |
|------|------|-------------|
| 3.1  | planner.json | Crear `Config/planner.json` (o bloque en memory) con prioridades, `use_learned_plan`, `use_classifier`, opcionalmente meta_questions e invalid_path_tokens; Planner los lee de config. |
| 3.2  | tools.json / timeouts | Timeouts por tool en config (memory.json o `Config/tools.json`); AgentCaller o tools leen de config. |
| 3.3  | Step con dependencias | Documentar y usar `dependencies` en Step para orden topológico en PlanExecutor (preparación DAG). |

### BLOQUE 4 — TOOLS Y CHAINED TOOLS

| Id   | Área | Descripción |
|------|------|-------------|
| 4.1  | chained_tools.json | Añadir 1–2 cadenas útiles; documentar placeholders en el JSON. |
| 4.2  | Tool ligera | Opcional: `get_time_tool` / `context_tool` o `memory_search_tool` (owner) y registrar en registry. |
| 4.3  | tools_registry.json | Opcional: config que liste tools a cargar y params por defecto. |

### BLOQUE 5 — CONFIG Y DOCUMENTACIÓN

| Id   | Área | Descripción |
|------|------|-------------|
| 5.1  | Config/README.md | Tabla: cada JSON, qué componente lo usa, enlace a misión/roadmap. |
| 5.2  | schema_version | Campo `config_version` o `schema_version` en memory.json o schema_version.json para evolución. |
| 5.3  | Referencias | Actualizar MISION_LILITH_3.7 y HORIZONTE_LILITH_4.0 con mención a 3.8 y ROADMAP_HACIA_4.0. |

---

## CRITERIOS DE CIERRE 3.8

- [x] Memoria: `recent_facts_weight` y `thread_memory_priority_hint` en memory.json; API Discord usa etiqueta de prioridad desde config.
- [x] Aprendizaje: `learning.json` creado; LearningEngine y FeedbackStore leen umbrales desde JSON.
- [x] Planner: `planner.json` creado; Planner lee use_learned_plan, use_classifier y prioridades (fallback a memory.json).
- [x] Timeouts por tool: `tools.json` con `timeouts`; _timeout_from_config lee tools.json luego memory.json.
- [x] Nueva cadena en chained_tools.json: `list_and_summarize` (list_directory + delegate_eva).
- [x] Config/README.md actualizado con schema_version, learning.json, planner.json, tools.json y claves 3.8.
- [x] ROADMAP_HACIA_4.0.md referenciado; schema_version "3.8" en memory.json.

---

## DOCUMENTOS RELACIONADOS

- **[ROADMAP_HACIA_4.0.md](ROADMAP_HACIA_4.0.md)** — Detalle de todas las propuestas (corto y medio plazo) por área.
- **[MISION_LILITH_3.9.md](MISION_LILITH_3.9.md)** — Fase siguiente: solo fixes y refinamiento (sin nuevas features).
- **[HORIZONTE_LILITH_4.0.md](HORIZONTE_LILITH_4.0.md)** — Visión 4.0: DAG, memoria en grafo, dashboard.
- **[MISION_LILITH_3.7.md](MISION_LILITH_3.7.md)** — Interacción, memoria y pulido (base previa).
- **Config/** — memory.json, learning.json, planner.json, tools.json, intent_patterns.json.
