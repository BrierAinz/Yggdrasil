# Agentes y orquestación en Lilith

Documento de referencia sobre el ecosistema de agentes, tools y el flujo de orquestación (Planner, PlanExecutor, AgentCaller) en el entorno de Lilith. Incluye el registro de agentes 4.0, los flujos de contexto y la relación con la memoria.

---

## 1. Visión general

Lilith no es un único modelo: es un **orquestador** que decide **qué hacer** con cada mensaje del usuario (plan) y **quién lo ejecuta** (tools o agentes). Los "agentes" son entidades con identidad (Eva, Adán, Lucifer, Odín) y capacidades de dominio (Web Scraper, Content Cleaner, etc.); las **tools** son capacidades atómicas (leer archivo, guardar hecho, etc.). El **Planner** genera una lista de pasos (plan); el **PlanExecutor** los ejecuta en orden, inyectando el resultado de un paso en el siguiente; el **AgentCaller** resuelve cada paso contra el **AgentRegistry** o el **ToolRegistryV3**.

```
Usuario → Discord API → Orchestrator.execute_plan(message)
                              ↓
                        Planner.plan(message)  →  [ Step(tool_1), Step(tool_2), ... ]
                              ↓
                        PlanExecutor.run_plan(plan, registry, context, ...)
                              ↓
                        Por cada Step: AgentCaller.execute(step, registry)
                              ↓
                        AgentRegistry.get_by_tool_name(step.tool_name)  →  Agent.execute(params)
                        O bien: registry.execute(step.tool_name, params)  →  Tool
                              ↓
                        Resultado → last_result / step_results → siguiente paso o respuesta final
```

---

## 2. AgentRegistry y clase Agent (4.0)

### 2.1 Concepto

El **AgentRegistry** es el catálogo de "agentes" como entidades de primera clase. Cada agente tiene:

- **agent_id:** Identificador interno (eva, adan, lucifer, odin, web_scraper, …).
- **tool_name:** Nombre con el que el Planner y los Steps lo invocan (delegate_eva, delegate_web_scraper, …).
- **description:** Texto breve para listados o futura selección automática.
- **execute(params):** Recibe el diccionario de parámetros del Step y devuelve un **ToolResult** (dict con `response`, opcionalmente `error`, etc.).

No hay distinción obligatoria entre "agente LLM" y "agente de dominio": todos implementan la misma interfaz. Los que delegan en un LLM externo (Eva, Adán, Lucifer, Odín) están envueltos en tools existentes (DelegateEvaTool, etc.) y registrados como `_DelegateToolAgent`.

### 2.2 Agentes registrados por defecto

| agent_id | tool_name | Descripción | Backend / implementación |
|----------|-----------|-------------|---------------------------|
| eva | delegate_eva | Análisis, documentación, insights | Grok (DelegateEvaTool) |
| adan | delegate_adan | Código, refactor, tests | Qwen (DelegateAdanTool) |
| lucifer | delegate_lucifer | Creativo, conversacional, voz de Lilith | Venice (DelegateLuciferTool) |
| odin | delegate_odin | Análisis masivo, contexto largo | Kimi (DelegateOdinTool) |
| web_scraper | delegate_web_scraper | Extracción de texto desde URLs | WebScraperAgent (requests + BeautifulSoup) |
| content_cleaner | delegate_content_cleaner | Limpieza de HTML y boilerplate | ContentCleanerAgent |
| quality_filter | delegate_quality_filter | Filtro de calidad heurístico (longitud, densidad) | QualityFilterAgent |
| data_structurer | delegate_data_structurer | Entidades, resumen, tópico (texto formateado) | DataStructurerAgent |

Otros **tools** que no son "agentes" en el registry pero participan en los planes: `read_file`, `list_directory`, `edit_file`, `generate_reply`, `store_semantic_fact`, `lore_extractor`, `delegate_kimi_cli`, `delegate_albedo`, etc. El AgentCaller solo consulta el AgentRegistry para los `tool_name` que estén registrados ahí; el resto se ejecuta vía **ToolRegistryV3**.

---

## 3. Cómo se ejecuta un paso (AgentCaller)

1. El **PlanExecutor** tiene un Step con `tool_name` y `params`.
2. **AgentCaller.execute(step, registry, skip_cache)**:
   - Si hay caché de respuestas (B.1) y el paso es cacheable, devuelve la respuesta cacheada si aplica.
   - Si el **AgentRegistry** tiene un agente para ese `tool_name`, llama a **agent.execute(params)** y devuelve su resultado.
   - Si no, llama a **registry.execute(step.tool_name, step.params)** (ToolRegistryV3), que puede ser una tool pura (read_file, lore_extractor, store_semantic_fact, etc.).
3. El resultado (ToolResult) se convierte a texto con `_result_to_str` y se guarda en **last_result** y en **step_results[str(i)]** para el scratchpad (context_from_steps).

Así, "delegate_eva" lo ejecuta el agente Eva (que internamente usa DelegateEvaTool), y "lore_extractor" lo ejecuta la LoreExtractorTool del registro de tools, no un agente.

---

## 4. Planner: de mensaje a plan

El **Planner** decide qué secuencia de pasos (plan) corresponde al mensaje del usuario. Las fuentes de decisión, en orden de prioridad, son:

1. **Planes aprendidos** (memoria procedimental): si el motor de aprendizaje devuelve un plan para una intención similar, se usa ese plan.
2. **Clasificador local** (opcional): predice una tool (read_file, list_directory, delegate_eva, delegate_lucifer) y se genera un plan de un paso.
3. **Intent patterns** (`Config/intent_patterns.json`): se hace match por triggers (palabras clave) y se devuelve el plan asociado al intent (agent o tool).
   - **agent:** Se traduce a uno o más Steps con `tool_name` delegate_* (ej. agent "web_scraper" → secuencia scrape → clean → quality → structurer → store).
   - **tool:** Un solo Step con esa tool (ej. tool "lore_extractor" → Step(lore_extractor, params)).
4. **Matching learning (4.0):** Si está habilitado y hay sugerencia por similitud de mensajes anteriores, se puede devolver un plan de un paso (delegate_eva, delegate_lucifer o delegate_adan).
5. **Fallback:** Un solo paso `delegate_lucifer` para respuesta conversacional.

No hay (aún) enrutamiento dinámico de **topic** en función del contenido del mensaje o la URL; el topic se puede pasar como parámetro en el Step si en el futuro el Planner o un módulo de topic_router lo rellenan.

---

## 5. PlanExecutor: ejecución lineal y scratchpad

- **Ejecución:** Secuencial, paso a paso. Por cada Step se llama a AgentCaller.execute; el resultado se guarda en **last_result** y en **step_results[str(i)]**.
- **Contexto al siguiente paso:** Por defecto, el siguiente paso recibe `params["context"] = last_result`. Si el Step tiene **context_from_steps** (lista de índices de pasos), el contexto se construye desde **step_results** con truncamiento proporcional (scratchpad) y opción tail/head/middle (scratchpad_prefer).
- **Casos especiales:** Para `generate_reply` y `delegate_lucifer` se inyecta además historial de conversación, contexto semántico (memoria) y, si aplica, delegaciones recientes. Para los pasos intermedios de la minería web (content_cleaner, quality_filter, data_structurer) solo reciben la salida del paso anterior, no el historial de delegaciones.

No hay ejecución paralela aún; los planes son listas ordenadas. Ver **ORQUESTACION_Y_ESTRUCTURACION_4_0.md** para la hoja de ruta de paralelismo (DAG, ThreadPoolExecutor).

---

## 6. Flujos de datos por tipo de tarea

| Tarea | Plan típico | Agentes/tools implicados |
|-------|-------------|---------------------------|
| Conversación / pregunta abierta | [ delegate_lucifer ] | Lucifer (Venice) |
| Análisis profundo / documentación | [ delegate_eva ] | Eva (Grok) |
| Código / refactor | [ delegate_adan ] | Adán (Qwen) |
| Análisis masivo de proyecto | [ gather_directory, delegate_odin ] | Odín (Kimi) |
| Minería web (investigar URL) | [ delegate_web_scraper, delegate_content_cleaner, delegate_quality_filter, delegate_data_structurer, store_semantic_fact ] | WebScraper, ContentCleaner, QualityFilter, DataStructurer, StoreSemanticFactTool |
| Extracción de lore (wiki/Reddit) | [ lore_extractor ] | LoreExtractorTool (MediaWiki API / Reddit .json) |
| Guardar hecho explícito | [ store_semantic_fact ] (context inyectado) | StoreSemanticFactTool |

En el flujo de minería web, la salida de cada agente se pasa como **context** al siguiente; el DataStructurerAgent recibe el texto ya limpio y filtrado y produce el texto formateado que store_semantic_fact guarda en memoria semántica (y ChromaDB con chunking y source_id si aplica).

---

## 7. Memoria y agentes

- **Memoria semántica / ChromaDB:** La usan el Planner (contexto para el plan) y las tools que guardan hechos (store_semantic_fact, LoreExtractor, pipeline de minería). Los hechos pueden llevar **source_id** y **topic** para diversidad y filtrado.
- **Memoria episódica y procedimental:** Se actualizan en **MemoryManager.post_interaction**, que el **Orchestrator** llama tras una ejecución de plan exitosa (solo en el flujo con orquestador completo, típicamente rol owner). Los agentes no escriben directamente en memoria; el orquestador centraliza la persistencia tras ejecutar el plan.
- **Thread memory (Discord):** Se carga y se actualiza por canal/hilo en la API de Discord; no es propiedad de un agente concreto, sino del flujo de conversación.

---

## 8. Resumen de responsabilidades

| Componente | Responsabilidad |
|------------|-----------------|
| **Orchestrator** | Recibe mensaje, obtiene plan del Planner, ejecuta plan con PlanExecutor, llama a MemoryManager.post_interaction al terminar. |
| **Planner** | Genera lista de Steps a partir del mensaje (aprendido, clasificador, intent patterns, matching learning, fallback). |
| **PlanExecutor** | Ejecuta cada Step en orden; mantiene step_results y last_result; inyecta contexto (scratchpad) según context_from_steps y scratchpad_prefer. |
| **AgentCaller** | Por cada Step, resuelve si es un agente (AgentRegistry) o una tool (ToolRegistryV3) y ejecuta; aplica caché y truncamiento de task si aplica. |
| **AgentRegistry** | Mapea tool_name (delegate_*) a Agent; los agentes implementan execute(params) → ToolResult. |
| **ToolRegistryV3** | Registra todas las tools (read_file, lore_extractor, store_semantic_fact, delegate_* si no están en AgentRegistry, etc.) y ejecuta por nombre. |

---

*Documento de referencia sobre agentes y orquestación en Lilith. Para decisiones estratégicas sobre estructuración, paralelismo y topic routing, ver ORQUESTACION_Y_ESTRUCTURACION_4_0.md.*
