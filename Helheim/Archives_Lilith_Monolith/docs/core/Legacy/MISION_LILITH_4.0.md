# MISIÓN LILITH 4.0 — ECOSISTEMA Y APRENDIZAJE

**Estado:** EN PROGRESO — Flujo de minería web completo (Fases 0–4) implementado; siguiente: Fase 3/4 del ecosistema (delegador universal, comunicación inter-agente) o afinado de tópicos/entidades.

**Visión:** Evolucionar de cerebro único a ecosistema de agentes autónomos (ver [HORIZONTE_LILITH_4.0.md](HORIZONTE_LILITH_4.0.md)). La 4.0 se aborda por fases; el **inicio** es el **Matching Learning**: aprender qué agente/herramienta conviene para cada tipo de mensaje a partir del uso.

---

## Fase 0: Matching Learning (inicio)

**Objetivo:** Que Lilith aprenda de cada decisión del Planner (mensaje → tool elegida) y use ese aprendizaje para sugerir la tool en mensajes similares. Sin cambiar aún la arquitectura de agentes; solo añadir una capa de aprendizaje por uso.

| Elemento | Descripción |
|----------|-------------|
| **Record** | En cada `plan()`: registrar (mensaje, tool principal usada) en `Data/matching_learning.jsonl` (o MuninnDB opcional). |
| **Suggest** | Antes de decidir: consultar historial de mensajes similares y devolver la tool más frecuente como sugerencia. |
| **Integración** | Planner: si se va a usar fallback (Lucifer), antes consultar el matching learner; si sugiere una tool con suficiente confianza, usarla. Tras cada decisión, llamar `record()`. |
| **Config** | `Config/learning.json`: `matching_learning_enabled`, `matching_learning_min_matches`, `matching_learning_confidence_threshold`. |

**Criterios de cierre Fase 0:**
- [x] Módulo `matching_learner` con `record()` y `suggest()`.
- [x] Config en `learning.json` y uso desde el Planner.
- [x] Planner usa la sugerencia cuando cae en fallback y la confianza supera el umbral.
- [x] Tras cada `plan()` se registra la decisión para aprendizaje futuro.

---

## Siguiente paso lógico: refinar la intuición

La base está sentada. El siguiente paso **no** es añadir una capacidad drástica nueva, sino **afinar** esta habilidad.

| Paso | Acción |
|------|--------|
| **1. Observar y ajustar** | Dejar que el sistema acumule unos días de datos en `Data/matching_learning.jsonl`. Luego analizar: ¿muchos falsos positivos? ¿Falsos negativos? Ajustar `matching_learning_min_matches` y `matching_learning_confidence_threshold` en `Config/learning.json` para optimizar precisión. |
| **2. Mejorar la similitud (opcional)** | Si la similitud Jaccard (por palabras) resulta demasiado simple en ciertos casos, se puede evolucionar a TF-IDF + similitud coseno **sin cambiar el resto del módulo** (solo la función de similitud en `matching_learner.py`). Por ahora, la simplicidad es una virtud. |
| **3. Proceder a la Fase 1** | Con la intuición básica funcionando y calibrada, el siguiente hito era el **AgentRegistry** — ya implementado. |

---

## Fase 1: AgentRegistry (implementada)

**Objetivo:** Registrar agentes como entidades de primera clase; el AgentCaller ejecuta los pasos `delegate_*` vía el registro cuando está disponible.

| Elemento | Descripción |
|----------|-------------|
| **Clase base `Agent`** | `agent_id`, `tool_name`, `description`, `execute(params)` → ToolResult. En `Backend/core/agent_registry.py`. |
| **AgentRegistry** | `register(agent)`, `get(agent_id)`, `get_by_tool_name(tool_name)`, `list_agents()`. |
| **Agentes migrados** | Eva, Adán, Lucifer y Odín como wrappers sobre las tools existentes (`DelegateEvaTool`, etc.) para no duplicar lógica. |
| **AgentCaller** | Si tiene `agent_registry` y el paso es un agente registrado, ejecuta `agent.execute(params)`; si no, usa el ToolRegistryV3. |
| **Orchestrator** | Crea `create_default_agent_registry(base_path)` por defecto e inyecta el registry en el AgentCaller. |

**Criterios de cierre Fase 1:**
- [x] Clase `Agent` y `AgentRegistry` en `agent_registry.py`.
- [x] Eva, Adán, Lucifer, Odín registrados (wrappers sobre las tools actuales).
- [x] AgentCaller usa el registry para `delegate_eva`, `delegate_adan`, `delegate_lucifer`, `delegate_odin`.
- [x] Orchestrator inyecta el registry al construir el PlanExecutor/AgentCaller.

---

## Fase 2: WebScraperAgent (implementada)

**Objetivo:** Primer agente de dominio nuevo registrado en el AgentRegistry: extraer texto de URLs para minería web.

| Elemento | Descripción |
|----------|-------------|
| **WebScraperAgent** | `Backend/core/web_scraper_agent.py`: clase `Agent` con `agent_id=web_scraper`, `tool_name=delegate_web_scraper`. Extrae texto con requests + BeautifulSoup; elimina script/style/nav/footer; respeta `Config/web_sources.json`. |
| **Config** | `Config/web_sources.json`: `allowed_domains` (vacío = todos), `timeout_seconds`, `max_chars`. |
| **Intent** | `investigate_web` en `intent_patterns.json`: triggers "investiga en la web", "extrae contenido de", "scrapea", etc.; agent `web_scraper`. |
| **Planner** | Resolución `agent == "web_scraper"` → `Step(tool_name="delegate_web_scraper", params={"task": text, "context": ""})`. La URL se extrae del mensaje o del parámetro `url`. |

**Criterios de cierre Fase 2:**
- [x] Clase `WebScraperAgent(Agent)` con extracción de texto desde URL.
- [x] Registro en `create_default_agent_registry()`.
- [x] Intent `investigate_web` y manejo en Planner.
- [x] Dependencia `beautifulsoup4` en `requirements.txt`.

**Siguiente:** QualityFilterAgent o DataStructurerAgent; ver [VISION_MINERIA_REFINERIA_WEB.md](VISION_MINERIA_REFINERIA_WEB.md).

---

## Fase 2b: ContentCleanerAgent (implementada)

**Objetivo:** Segunda capa de la refinería web: limpiar el texto crudo que devuelve WebScraperAgent.

| Elemento | Descripción |
|----------|-------------|
| **ContentCleanerAgent** | `Backend/core/content_cleaner_agent.py`: `agent_id=content_cleaner`, `tool_name=delegate_content_cleaner`. Recibe texto en `params["context"]` o `params["text"]`; elimina HTML residual, normaliza espacios y filtra líneas boilerplate (cookies, menús, etc.). |
| **Encadenamiento** | El intent `investigate_web` devuelve dos pasos: `delegate_web_scraper` → `delegate_content_cleaner`. El PlanExecutor inyecta la salida del scraper como `context` del cleaner; la respuesta final es el texto limpio. |

**Criterios de cierre:**
- [x] Clase `ContentCleanerAgent(Agent)` con pipeline de limpieza.
- [x] Registro en `create_default_agent_registry()`.
- [x] Intent `investigate_web` genera plan de 2 pasos (scrape + clean) → actualizado a 3 pasos con QualityFilter.

---

## Fase 3b: QualityFilterAgent (implementada)

**Objetivo:** Filtrar contenido de baja calidad antes de estructurar o guardar; evitar contaminar la memoria semántica con datos mediocres o erróneos.

| Elemento | Descripción |
|----------|-------------|
| **QualityFilterAgent** | `Backend/core/quality_filter_agent.py`: `agent_id=quality_filter`, `tool_name=delegate_quality_filter`. Recibe texto en `params["context"]`; evalúa **longitud** (min_length, ideal_min_length) y **densidad de información** (ratio palabras sustantivas vs. stopwords ES/EN). Combina en `quality_score` 0.0–1.0. |
| **Config** | `Config/quality_filter.json`: `min_score` (umbral; por debajo se descarta), `min_length`, `ideal_min_length`. |
| **Comportamiento** | Si `score < min_score`: devuelve mensaje "Contenido filtrado por baja calidad (score X)". Si pasa: devuelve el texto con prefijo `[Calidad validada: X \| palabras: N]` para downstream (DataStructurer, usuario). |
| **Encadenamiento** | El intent `investigate_web` genera **3 pasos**: delegate_web_scraper → delegate_content_cleaner → delegate_quality_filter. La salida de cada paso es el `context` del siguiente. |

**Criterios de cierre:**
- [x] Clase `QualityFilterAgent(Agent)` con score heurístico (longitud + densidad).
- [x] Config `quality_filter.json` y umbral `min_score`.
- [x] Registro y 3.er paso en el plan de `investigate_web`.

**Siguiente:** Ajustar tópicos/entidades en config o ampliar fuentes; flujo completo cerrado.

---

## Fase 4: DataStructurerAgent + store_semantic_fact (implementada)

**Objetivo:** Estructurar el texto validado y guardarlo en memoria semántica para cerrar el flujo de minería web.

| Elemento | Descripción |
|----------|-------------|
| **DataStructurerAgent** | `Backend/core/data_structurer_agent.py`: `agent_id=data_structurer`, `tool_name=delegate_data_structurer`. Recibe texto (con prefijo de calidad); extrae **entidades** (ALL_CAPS, CamelCase, términos técnicos), **resumen** extractivo (primeras frases / 400 chars), **tópico** por palabras clave (PostgreSQL, ML, etc.). Salida: texto formateado `[Minería web] Tópico: … Resumen: … Conceptos: …`. |
| **Config** | `Config/data_structurer.json`: `max_summary_chars`, `max_entities`. |
| **StoreSemanticFactTool** | `Backend/core/tools_v3/memory_tools.py`: tool `store_semantic_fact` que recibe `fact` o `context` (inyectado por el plan) y llama a `MemoryManager(base_path).add_fact(text)`. |
| **Encadenamiento** | El intent `investigate_web` genera **5 pasos**: delegate_web_scraper → delegate_content_cleaner → delegate_quality_filter → delegate_data_structurer → store_semantic_fact. La salida del structurer se inyecta como `context` del último paso y se guarda en memoria semántica. |

**Criterios de cierre:**
- [x] DataStructurerAgent con extracción de entidades, resumen y tópico.
- [x] Tool store_semantic_fact registrada y 5.º paso en el plan.
- [x] Flujo completo: desde URL hasta hecho en memoria.

---

## Visión del flujo completo (minería web) ✅

Orden: *"Lilith, investiga sobre 'técnicas de indexación en PostgreSQL', valida solo fuentes de calidad, estructura los hallazgos y guárdalos en tu memoria."*

| Paso | Agente / Tool | Estado |
|------|----------------|--------|
| 1 | **WebScraperAgent** | Extrae contenido de URLs. ✅ |
| 2 | **ContentCleanerAgent** | Limpia HTML y ruido. ✅ |
| 3 | **QualityFilterAgent** | Evalúa calidad; descarta bajo umbral. ✅ |
| 4 | **DataStructurerAgent** | Extrae entidades (B-tree, GiST, VACUUM), resumen, tópico. ✅ |
| 5 | **store_semantic_fact** | Guarda el hecho estructurado en memoria semántica. ✅ |

El flujo está cerrado: una sola orden de investigación web puede terminar con el hecho guardado en memoria.

---

## Fases siguientes (plan 4.0)

| Fase | Descripción |
|------|-------------|
| **Fase 1 — Registro de agentes** | AgentRegistry; agentes como clase con `execute()`. ✅ Implementado. |
| **Fase 2 — Minería web (agentes + tool)** | WebScraper, ContentCleaner, QualityFilter, DataStructurer + store_semantic_fact; intent investigate_web en 5 pasos. ✅ Implementado. |
| **Fase 3 — Delegador universal** | Planner puede elegir agente desde el registro por capacidad (opcional). |
| **Fase 4 — Comunicación inter-agente** | Lilith como bus: resultado de un agente → contexto para otro. |

---

## Documentos relacionados

- [HORIZONTE_LILITH_4.0.md](HORIZONTE_LILITH_4.0.md) — Visión ecosistema de agentes.
- [VISION_MINERIA_REFINERIA_WEB.md](VISION_MINERIA_REFINERIA_WEB.md) — Estrategia de extracción y refinería de datos desde la web (agentes WebScraper, ContentCleaner, QualityFilter, DataStructurer).
- [ROADMAP_HACIA_4.0.md](ROADMAP_HACIA_4.0.md) — Propuestas por área.
- [MISION_LILITH_3.9.md](MISION_LILITH_3.9.md) — Fixes y refinamiento previos.
