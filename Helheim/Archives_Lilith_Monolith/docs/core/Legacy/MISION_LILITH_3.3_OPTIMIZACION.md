# MISIÓN LILITH 3.3 — OPTIMIZACIÓN Y CONFIGURACIÓN JSON

**Objetivo:** Evolución del sistema actual (Fases 4–5 del plan 3.2), configuración declarativa por JSON, y bases para memoria híbrida y meta-aprendizaje.

**Base:** Misión 3.2 completada (retención episódica, refuerzo procedimental, perfil vs hechos, ponderación, JSON seguro).

---

## NIVEL 1 — EVOLUCIÓN (Fases 4 y 5 del plan 3.2)

### 1.1 Memoria procedimental inteligente (C.2 y C.3)

| Tarea | Descripción | Criterio de éxito |
|-------|-------------|-------------------|
| **C.2 Vencimiento de patrones** | Si un patrón no se usa en N días (ej. 30), se mueve a `store_old_patterns.json` y se quita del activo. La base procedimental se mantiene ágil. | Patrones inactivos archivados; `list_patterns()` solo devuelve activos. |
| **C.3 Agrupación por intención** | Etiqueta opcional `intent` en cada patrón. El Planner clasifica la intención del mensaje (ej. `edit_file`, `analyze_code`) y el LearningEngine solo busca planes aprendidos en esa categoría. | Mejor precisión del matching mensaje → plan aprendido. |

### 1.2 Memoria semántica escalable (D.3)

| Tarea | Descripción | Criterio de éxito |
|-------|-------------|-------------------|
| **D.3 Búsqueda vectorial** | Hechos y perfil como vectores (embeddings). Ante una pregunta, búsqueda por similitud (ChromaDB, FAISS o sentence-transformers local). | Preguntas como "¿qué dijiste sobre el rendimiento el mes pasado?" recuperan hechos relevantes sin palabras exactas. |

### 1.3 Memoria episódica compacta (B.3)

| Tarea | Descripción | Criterio de éxito |
|-------|-------------|-------------------|
| **B.3 Resúmenes de sesión** | Cada N interacciones (ej. 10) o al cierre, Lucifer genera un resumen; se guarda como hecho de alto nivel o en `session_summaries.jsonl`. | Memoria semántica con visión panorámica sin revisar cientos de episodios. |

---

## NIVEL 2 — UNIFICACIÓN Y CONVERGENCIA

### 2.1 Memoria híbrida

- **Concepto:** Una sola búsqueda de contexto: hechos, perfil, planes aprendidos y episodios exitosos en un formato unificado (ej. embeddings).
- **Resultado:** Una pregunta combina hecho relevante + plan aprendido + episodio donde se aplicó.

### 2.2 Grafo de conocimiento (Knowledge Graph)

- **Concepto:** Nodos = entidades (Ainz, Lilith, EditFileTool, Yggdrasil); aristas = relaciones (CREADOR_DE, USA).
- **Ventaja:** Razonamiento por inferencia (ej. "¿qué herramientas usamos para Yggdrasil?" recorriendo el grafo).
- **Implementación:** Neo4j o representación JSON de grafo.

---

## NIVEL 3 — AUTOMATIZACIÓN Y META-APRENDIZAJE

### 3.1 Auto-configuración de memoria

- **Concepto:** Ajuste dinámico de `Config/memory.json` (ej. bajar `use_learned_plan` si muchos planes no se usan, subir `max_facts` si los hechos son útiles).
- **Mecanismo:** LearningEngine genera meta-informe de rendimiento y propone cambios de config (o los aplica con validación).

### 3.2 Generación proactiva de patrones

- **Concepto:** A partir de episodios exitosos, Lilith sugiere: "En 5 de las últimas 8 veces que pediste optimizar, el plan fue X. ¿Lo convierto en plan procedimental permanente?"
- **Resultado:** De ejecutora a consejera activa en la optimización de su propia mente.

---

## NIVEL 1 (CONFIG) — HERRAMIENTAS JSON DECLARATIVAS

### 1.1 Router de intenciones por JSON

- **Archivo:** `Config/intent_patterns.json`
- **Contenido:** Lista de intenciones con `name`, `agent` o `action`, `triggers`, `priority`, `explicit_only`, `requires_gather_directory`, etc.
- **Implementación:** El Planner carga este JSON y resuelve la intención por prioridad; ya no depende solo de reglas hardcodeadas. Cambios de comportamiento sin tocar código.

### 1.2 Patrones procedimentales en JSON mejorado

- **Formato:** Cada patrón con `pattern_id`, `intent`, `plan`, `metadata` (use_count, last_used, success_rate, created_on).
- **Ventaja:** Refuerzo y metadatos forman parte del dato; el store es un contenedor de lectura/escritura.

---

## NIVEL 2 (CONFIG) — MINI-SCRIPTS / DSL EN JSON

### 2.1 Chain Tool (herramientas encadenadas)

- **Archivo:** `Config/chained_tools.json`
- **Contenido:** Herramientas definidas como secuencias de pasos con variables `{path}`, `{output_of_step_0}`, condiciones simples (if/then/else).
- **Implementación:** `ExecuteChainedTool` que carga el JSON, resuelve variables con entradas y salidas de pasos anteriores, y ejecuta la cadena. Permite configurar flujos sin nuevo código Python.

### 2.2 Ventajas del enfoque JSON-first

- Configuración en caliente: cambiar intenciones o cadenas sin reiniciar.
- Claridad y observabilidad: la lógica de alto nivel es legible en JSON.
- Extensibilidad para Trusted: `trusted_tools.json` con cadenas seguras.
- Backend como motor que ejecuta recetas definidas en JSON.

---

## ORDEN DE EJECUCIÓN SUGERIDO (Misión 3.3)

1. **Config/intent_patterns.json + Planner JSON-driven** — Router de intenciones declarativo.
2. **C.2** — Archivar patrones no usados en 30 días (`store_old_patterns.json`).
3. **C.3** — Campo `intent` en patrones y matching por intención en LearningEngine/Planner.
4. **B.3** (opcional) — Resúmenes de sesión con Lucifer.
5. **Config/chained_tools.json + ExecuteChainedTool** (opcional) — Cadenas de herramientas por JSON.
6. D.3, memoria híbrida, grafo, auto-config y generación proactiva — según prioridad y recursos.

---

## ESTADO DE IMPLEMENTACIÓN (primera ola)

| Tarea | Estado | Detalle |
|-------|--------|---------|
| **intent_patterns.json** | ✅ | `Config/intent_patterns.json` con intents (store_fact, explicit_*, massive_analysis, deep_analysis, read_file, list_directory, edit_file, improve_file). |
| **Planner JSON-driven** | ✅ | `_load_intent_patterns`, `_resolve_intent_from_config`, `_get_matched_intent_name`. Las reglas hardcodeadas de intención se sustituyen por resolución desde JSON; fallback a Lucifer. |
| **C.2 Vencimiento** | ✅ | `ProceduralStore._archive_old_patterns(max_days_unused)`: mueve patrones con `last_used`/`created_at` &lt; cutoff a `store_old_patterns.json`. `list_patterns()` llama a archivo antes de devolver. `Config/memory.json`: `procedural_archive_days` (default 30). |
| **C.3 Agrupación por intención** | ✅ | `list_patterns(intent_filter=None)`. `get_plan_for_message(message, intent_hint=None)`. Planner obtiene `intent_hint = _get_matched_intent_name(text)` y lo pasa al LearningEngine; solo se consideran patrones con ese `intent`. `add_pattern(..., intent=...)` opcional. |

---

## REFERENCIAS

- `MISION_LILITH_3.2_REFINAMIENTO.md` — Base 3.2.
- `REFINAMIENTO_MEMORIA_LILITH.md` — Detalle técnico de memoria.
- `HORIZONTE_LILITH_4.0.md` — Visión a largo plazo.
