# Roadmap hacia Lilith 4.0 — Memoria, aprendizaje, frameworks, tools y config

Propuestas concretas para acercar el proyecto a la 4.0, organizadas por área y prioridad. **Plan de auto-mejora (visión de Lilith):** **[PLAN_AUTOMEJORA_LILITH.md](PLAN_AUTOMEJORA_LILITH.md)**. Incluye mejoras de memoria, aprendizaje, frameworks, tools y JSON que encajan con lo ya construido (3.6/3.7). **La Misión 3.8** toma este roadmap como alcance: ver **[MISION_LILITH_3.8.md](MISION_LILITH_3.8.md)**. **La Misión 3.9** es solo fixes y refinamiento (sin nuevas features): ver **[MISION_LILITH_3.9.md](MISION_LILITH_3.9.md)**.

---

## Estado actual (resumen)

| Área | Qué hay ahora |
|------|----------------|
| **Memoria** | Semántica (hechos, perfil), episódica (logs), procedimental (patrones aprendidos), hilo (Discord por canal/hilo). `memory.json`: pesos, límites, `query_synonyms`, timeouts, `thread_memory_*`. |
| **Aprendizaje** | `LearningEngine`: sugiere patrones desde episodios exitosos; memoria procedimental con refuerzo. `FeedbackStore`: valoración 1–5 y refuerzo de `pattern_id`. Sin aplicación automática de sugerencias a `intent_patterns.json`. |
| **Frameworks** | Orchestrator + Planner + PlanExecutor + AgentCaller. Planner: intents desde JSON, clasificador local, planes aprendidos. Secuencial (no DAG). |
| **Tools** | ToolRegistryV3, delegate_* (Eva, Adán, Lucifer, Odín, local_irreverent), read_file, edit_file, list_directory, chained_tools (execute_chained), self_improve. |
| **JSON** | `intent_patterns.json`, `memory.json`, `discord_roles.json`, `local_public_llm.json`, `discord_context_instructions.json`, `chained_tools.json`, `security.json`. |

---

## 1. Memoria

### 1.1 Corto plazo (sin cambiar backend)

- **`memory.json`:**
  - Añadir **`recent_facts_weight`** (ej. 0.2): en búsqueda semántica, dar más peso a hechos con `timestamp` reciente.
  - Ampliar **`query_synonyms`** por dominio (proyectos, personas, términos del amo) y documentar en el propio JSON con `_comment`.
  - Añadir **`thread_memory_priority_hint`**: `"high"` | `"normal"` para subir/bajar el peso del bloque de hilo en el prompt (hoy fijo “prioridad alta”).
- **Indexación por tema:** En memoria semántica, opcionalmente etiquetar hechos con `topic` (ej. "discord", "codigo", "proyecto_x") y en `memory.json` permitir **`filter_by_topic`** en la query para “busca en memoria sobre X”.

### 1.2 Medio plazo (preparar 4.0)

- **Prioridad a hechos recientes:** En el store semántico (o en la capa que formatea contexto), ordenar/ponderar por fecha antes de inyectar en el prompt; el peso configurable vía `memory.json`.
- **Export de memoria de hilo:** Ya previsto en 3.7 (GET thread-memory). Completar y añadir opción **export a JSON** (backup) y, si aplica, **limpieza por antigüedad** (ej. `thread_memory_max_days` en config).
- **Feedback → memoria:** Que el comentario de `/feedback` (y la valoración) se use para: (1) refuerzo de patrón (ya existe) y (2) opcionalmente guardar un hecho en semántica del tipo “El usuario valoró bien X cuando Lilith hizo Y”, para que el contexto futuro incluya preferencias.

### 1.3 Pre-4.0: MuninnDB (memoria cognitiva)

Integrar **[MuninnDB](https://muninndb.com)** como capa de memoria cognitiva **antes** de la 4.0. MuninnDB aporta prioridad temporal (ACT-R), aprendizaje Hebbiano (asociaciones por co-activación) y activación con campo **Why** (explicable, sin LLM en el pipeline). Despliegue local (una binaria), SDK Python (`pip install muninndb`), opcional MCP para Cursor/Claude. Plan de integración: **[PRE_4.0_MUNINNDB.md](PRE_4.0_MUNINNDB.md)**.

---

## 2. Aprendizaje

### 2.1 Corto plazo

- **JSON de aprendizaje:** Crear **`Config/learning.json`** (o extender `memory.json` con bloque `learning`) para:
  - `suggest_intents_threshold`: mínimo de ocurrencias para sugerir un intent (ahora fijo en código).
  - `auto_apply_suggestions`: `false` por defecto; si se pone `true` en el futuro, que el flujo de “aplicar sugerencia” lea esto.
  - `feedback_reinforce_threshold`: valoración mínima para refuerzo (ej. 4).
- **Sugerencias a intent_patterns:** Endpoint o comando (ej. desde `/patrones`) que permita **añadir un intent sugerido** a `intent_patterns.json` con confirmación (manual o por API), sin tocar código. El LearningEngine ya sugiere; falta el “apply” guiado.

### 2.2 Medio plazo (notas para 4.0)

- **Autogeneración guiada:** Flujo en el que el LearningEngine propone un nuevo intent (trigger + tool/agent) y el owner lo acepta/rechaza; se escribe en `intent_patterns.json` y se recarga (o en próximo reinicio).
- **Refuerzo desde feedback:** Además de refuerzo de patrón, guardar en memoria procedimental o en un log “feedback_impact” qué `pattern_id` se reforzó y con qué valoración, para auditoría y afinado.

---

## 3. Frameworks (Orchestrator, Planner, ejecución)

### 3.1 Corto plazo

- **Config del planner:** Extraer a **`Config/planner.json`** (o bloque en `memory.json`): `plan_learned_priority`, `classifier_priority`, `rules_priority`, `use_learned_plan`, `use_classifier`, y opcionalmente listas de “meta_question” y “invalid_path_tokens” para no tener que tocar `planner.py` para afinados.
- **Timeouts por tool:** En `memory.json` o **`Config/tools.json`**: timeouts por tool (`delegate_kimi_cli`, `delegate_albedo`, `delegate_eva`, etc.) y leerlos en AgentCaller o en cada tool; ya existe para Kimi/Albedo, generalizar.

### 3.2 Medio plazo (preparar DAG)

- **Step con dependencias:** El modelo de `Step` ya puede tener un campo `dependencies: List[str]` (IDs de pasos previos). Documentar y usar en PlanExecutor para orden de ejecución (sin paralelo aún).
- **Plan como grafo:** Mantener `List[Step]` como contrato; internamente el Planner podría generar un grafo (nodos = steps, edges = dependencias) y el ejecutor resolver en orden topológico. Así se allana el camino al DAG de 4.0 sin romper la API actual.

---

## 4. Tools

### 4.1 Corto plazo

- **`chained_tools.json`:** Añadir 1–2 cadenas útiles más (ej. “listar directorio y luego delegar a Eva para resumir”, “read_file + delegate_lucifer para explicar”) y documentar placeholders en el JSON.
- **Nuevas tools ligeras:** Por ejemplo:
  - **`get_time_tool`** o **`context_tool`**: devuelve fecha/hora o contexto mínimo; sirve para pruebas y para que el modelo tenga “contexto de tiempo” sin llamar a una API externa.
  - **`memory_search_tool`** (solo owner/trusted): wrapper que expone “buscar en memoria semántica” como tool para que el orquestador pueda usarla en planes.
- **Registro por config:** Opcional **`Config/tools_registry.json`** que liste tools a cargar (por nombre) y parámetros por defecto (ej. timeouts); el `create_default_registry` podría leerlo para decidir qué registrar y con qué config.

### 4.2 Medio plazo (agentes de dominio 4.0)

- **Agentes de dominio:** Definir 1–2 agentes tipo “tool” (ej. **DocumentationAgent**, **TestGeneratorAgent**) que encapsulen flujo fijo (plantillas + LLM local opcional) y registrarlos en el ToolRegistryV3; sin DAG aún, como steps secuenciales.
- **Self-improve ampliado:** Que la tool `self_improve` pueda, con confirmación, proponer cambios en `intent_patterns.json` o en `memory.json` (por ejemplo nuevos sinónimos) a partir de episodios y feedback; el owner aprueba antes de escribir.

### 4.3 Minería y refinería web (visión)

Estrategia de alto nivel para que Lilith extraiga datos limpios de la web: **extracción → limpieza → validación/filtrado → estructuración → indexación/almacenamiento**. Agentes de dominio: **WebScraperAgent**, **ContentCleanerAgent**, **QualityFilterAgent**, **DataStructurerAgent**; fuentes clasificadas por calidad (alta/media/baja); integración con memoria semántica o grafo. Implementación recomendada por fases: empezar por WebScraperAgent básico (una fuente de alta calidad), luego ContentCleanerAgent, después QualityFilter y DataStructurer, y escalar con cola de tareas y (opcional) base de grafos. Detalle completo: **[VISION_MINERIA_REFINERIA_WEB.md](VISION_MINERIA_REFINERIA_WEB.md)**.

---

## 5. JSON y config

### 5.1 Nuevos o ampliados

| Archivo | Propósito |
|---------|-----------|
| **`Config/learning.json`** | Umbrales de sugerencias, refuerzo desde feedback, auto_apply (futuro). |
| **`Config/planner.json`** | Prioridades de fuentes, meta_questions, invalid_path_tokens, opcionalmente triggers “skip” para improve_file. |
| **`Config/tools.json`** | Timeouts por tool, opcionalmente “enabled/disabled” por tool. |
| **`memory.json`** | `recent_facts_weight`, `filter_by_topic`, `thread_memory_priority_hint`, ampliar `query_synonyms`. |
| **`intent_patterns.json`** | Seguir añadiendo intents (ej. más triggers para `public_roast`, `local_irreverent_model`); documentar en `_comment` la relación con LearningEngine. |

### 5.2 Documentación en repo

- **`Config/README.md`:** Tabla que liste cada JSON, qué lee cada componente (Planner, MemoryManager, Discord API, etc.) y un enlace al doc de estrategia o misión que lo use.
- **Versión de contrato:** En `memory.json` o en un `Config/schema_version.json`, un campo `config_version` o `schema_version` para evolución futura sin romper compatibilidad.

---

## 6. Priorización sugerida (orden de implementación)

1. **Memoria:** `recent_facts_weight` y ampliar `query_synonyms` en `memory.json`; opcional `thread_memory_priority_hint`.
2. **Aprendizaje:** `Config/learning.json` con umbrales; opcional endpoint/flow para “añadir intent sugerido” desde sugerencias del LearningEngine.
3. **Frameworks:** `Config/planner.json` (o bloque en memory) para prioridades y meta_questions; timeouts por tool en config.
4. **Tools:** 1–2 cadenas nuevas en `chained_tools.json`; opcional `memory_search_tool` para owner.
5. **Docs:** Actualizar `Config/README.md` y referencias en `MISION_LILITH_3.7.md` / `HORIZONTE_LILITH_4.0.md` a estos JSON y a este roadmap.

Con esto se gana **configurabilidad**, **trazabilidad** y **preparación para DAG y memoria en grafo** sin cambiar de versión mayor; cuando se quiera dar el salto a 4.0, el Horizonte 4.0 (DAGs, memoria en grafo, dashboard) seguirá siendo la referencia de diseño.

---

## Referencias

- `HORIZONTE_LILITH_4.0.md` — Visión 4.0: DAG, memoria en grafo, dashboard.
- `VISION_MINERIA_REFINERIA_WEB.md` — Estrategia de minería y refinería web (WebScraper, ContentCleaner, QualityFilter, DataStructurer).
- `PRE_4.0_MUNINNDB.md` — Integración de MuninnDB como memoria cognitiva antes de 4.0.
- `MISION_LILITH_3.8.md` — Config (learning, planner, tools, memory ampliado).
- `MISION_LILITH_3.9.md` — Solo fixes y refinamiento (sin nuevas features).
- `MISION_LILITH_3.7.md` — Bloque memoria, feedback, pipeline, notas para 4.0.
- `Config/memory.json` — Pesos, límites, synonyms, timeouts.
- `Backend/core/learning/learning_engine.py` — Sugerencias y planes aprendidos.
- `Backend/core/feedback_store.py` — Valoración y refuerzo de patrones.
