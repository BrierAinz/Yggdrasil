# Orquestación y estructuración 4.0 — Vectores estratégicos

Respuestas a las tres preguntas de investigación sobre el agente estructurador, la ejecución paralela en el DAG y el enrutamiento dinámico de tópicos. Sirve como hoja de ruta para la siguiente fase.

---

## 1. El agente estructurador (DataStructurerAgent) y el flujo de Lore

**Pregunta:** ¿Implementamos un paso donde Adán, Eva o Lucifer transformen el texto limpio en un formato rígido (JSON con personajes, lugares, eventos_clave) antes de ChromaDB, o el chunking semántico sobre texto plano es suficiente?

**Estado actual:**

- **Pipeline minería web (investigate_web):** Ya existe el flujo completo scrape → ContentCleaner → QualityFilter → **DataStructurerAgent** → store_semantic_fact. El DataStructurerAgent es **heurístico**: extrae entidades (ALL_CAPS, CamelCase, términos técnicos), resumen extractivo y tópico por palabras clave. No usa LLM; la salida es texto formateado (`[Minería web] Tópico: … Resumen: … Conceptos: …`), no JSON rígido.
- **Pipeline Lore (LoreExtractor):** Se guarda el **texto plano** extraído (MediaWiki o Reddit) directamente en memoria, con chunking y source_id. No pasa por DataStructurerAgent ni por ningún LLM.

**Opciones de diseño:**

| Enfoque | Pros | Contras |
|--------|------|--------|
| **Chunking sobre texto plano (actual para Lore)** | Simple, sin latencia ni coste de LLM; la búsqueda semántica ya recupera por significado. | No hay estructura explícita (personajes, lugares); las consultas tipo "¿qué personajes aparecen?" requieren que el modelo infiera del texto recuperado. |
| **DataStructurerAgent sobre lore** | Reutiliza el mismo agente; añade tópico y conceptos de forma consistente con la minería web. | Sigue siendo heurístico; no extrae "personajes" o "lugares" como campos si no están en las listas de términos. |
| **Paso LLM (Lucifer/Eva) → JSON estructurado** | Salida rígida (personajes, lugares, eventos_clave) ideal para consultas estructuradas o para rellenar una base de grafos. | Latencia, coste y dependencia del modelo; hay que definir schema y manejar fallos de parsing. |

**Recomendación:**

- **Corto plazo:** Mantener el chunking semántico sobre texto plano para Lore como está. Es suficiente para RAG conversacional ("¿qué sabes de Valhalla?"). Opcionalmente, hacer que el **LoreExtractor** pueda encadenar un paso con **DataStructurerAgent** (mismo flujo que investigate_web) cuando el usuario pida "extrae y estructura el lore de…", de modo que se añada tópico y conceptos sin cambiar la forma de guardado.
- **Fase siguiente (4.1):** Si se necesitan consultas del tipo "listar personajes" o "eventos clave del reino X", añadir un **paso opcional** donde el texto limpio (o la salida del DataStructurerAgent) se envía a **Lucifer o Eva** con un prompt tipo "Extrae y devuelve un JSON con: personajes, lugares, eventos_clave". Ese JSON puede guardarse como un hecho más (texto del JSON o campos indexados) o alimentar un futuro grafo. El paso sería opcional y configurable (ej. `lore_structurer_llm: true` en config) para no añadir latencia por defecto.

---

## 2. Ejecución paralela en el DAG (PlanExecutor)

**Pregunta:** Si el Planner decide extraer de 3 URLs a la vez, ¿usaremos asyncio.gather o ThreadPoolExecutor para paralelizar los pasos independientes?

**Estado actual:**

- El **PlanExecutor** ejecuta los planes **de forma estrictamente lineal**: un bucle `for step in plan` que ejecuta cada paso, actualiza `last_result` y `step_results`, e inyecta el contexto en el siguiente. No hay DAG ni paralelismo.
- El **scratchpad** (step_results, context_from_steps) está preparado para que un paso consuma salidas de pasos anteriores no adyacentes, pero la **ejecución** sigue siendo secuencial.
- Los **locks** (p. ej. _REDDIT_LOCK) están listos para cuando haya concurrencia: varios hilos pueden llamar a la misma tool; el lock serializa solo la sección crítica del rate limit.

**Opciones de diseño:**

| Enfoque | Pros | Contras |
|--------|------|--------|
| **asyncio.gather** | Natural si las tools pasan a ser async (httpx.AsyncClient, etc.); un solo hilo, sin GIL. | Requiere que todo el flujo sea async (PlanExecutor, AgentCaller, tools); las APIs actuales (requests, etc.) son síncronas. |
| **ThreadPoolExecutor** | Permite paralelizar **sin** reescribir las tools a async; cada paso independiente se ejecuta en un worker. | GIL en CPU; para I/O (red, disco) sigue siendo útil. Hay que definir qué pasos son "independientes" (grafo de dependencias). |
| **Mantener secuencial de momento** | Cero riesgo de regresiones; el orden garantizado simplifica el debug. | No se aprovecha paralelismo cuando el plan tiene varias extracciones independientes. |

**Recomendación:**

- **Fase actual:** Asumir ejecución **estrictamente secuencial**. El Planner no genera aún planes con "3 URLs en paralelo"; genera una lista ordenada de pasos. Cuando se quiera paralelizar, el siguiente paso es:
  1. **Representación del plan:** Que el plan pueda ser un DAG (lista de pasos con dependencias explícitas: "el paso 3 depende de 1 y 2"). Mientras tanto, se puede definir un convenio: "pasos con el mismo índice de nivel o sin context_from_steps entre ellos" se consideran paralelizables.
  2. **Motor de ejecución:** Usar **ThreadPoolExecutor** para los pasos que no dependan de resultados de otros (pasos con dependencias satisfechas). El PlanExecutor tendría una fase de "agrupar pasos ejecutables" y lanzar `executor.submit(execute_step, step)` para cada uno, luego `concurrent.futures.wait` y actualizar `step_results` con los resultados antes de la siguiente oleada. asyncio.gather se reservaría para cuando las tools tengan versión async (p. ej. LoreExtractor con httpx.AsyncClient).
- **Resumen:** No está implementado aún; el terreno (locks, step_results) está listo. La opción recomendada para la primera versión paralela es **ThreadPoolExecutor** sobre pasos con dependencias satisfechas, sin convertir todo el stack a async de entrada.

---

## 3. Enrutamiento dinámico de tópicos (Topic Routing)

**Pregunta:** ¿Quién asigna el topic de forma dinámica cuando el usuario dice "Extrae de esta URL de Reddit": el Planner (reglas/intent), Lucifer, o el usuario debe pasarlo a mano?

**Estado actual:**

- El **topic** es un parámetro opcional en LoreExtractorTool y en store_semantic_fact. Si no se envía, el hecho se guarda **sin** topic (o con topic vacío); en búsqueda, si no hay `vector_topic_filter`, no se aplica filtro.
- El **Planner** no inspecciona la URL ni el contenido para asignar topic. Cuando el intent es `extract_lore`, genera un paso `lore_extractor` con `params={"message": text, "store": True}`; no rellena `topic`.
- Por tanto, hoy el topic se asigna **manualmente** (el usuario debe decir "extrae con topic rol_lore" o similar, y habría que extender el parser para capturar eso) o **no se asigna**.

**Opciones de diseño:**

| Enfoque | Pros | Contras |
|--------|------|--------|
| **Reglas en intent_patterns / Planner** | Determinista y rápido; p. ej. si la URL contiene "reddit.com/r/worldbuilding" → topic=rol_lore, "reddit.com/r/gamedev" → topic=gamedev. | Requiere mantener un mapa URL/subreddit → topic; no cubre URLs genéricas. |
| **Clasificador (Lucifer o modelo local)** | Puede inferir topic a partir del título del post, del subreddit o del texto extraído. | Latencia y coste; hay que definir las etiquetas y el prompt o modelo. |
| **Usuario lo indica en el mensaje** | Máximo control. | Poca comodidad; hay que parsear "extrae con topic X" en el Planner. |

**Recomendación:**

- **Corto plazo:** Añadir **reglas ligeras en el Planner** (o en un módulo de "topic_router") que, cuando el paso sea `lore_extractor` y el mensaje contenga una URL, inspeccionen la URL y asignen topic por convención:
  - Subreddit conocido: `r/worldbuilding`, `r/DnDBehindTheScreen` → `rol_lore`; `r/gamedev`, `r/gamedesign` → `gamedev`.
  - Dominio Fandom: opcionalmente `topic=mitologia` o `topic=rol_lore` por defecto para wikis, o dejar sin topic hasta tener más señales.

---

## 4. Materialización: El Siguiente Salto (implementado)

Respuestas aplicadas a las tres preguntas de implementación.

### 4.1 Motor de tópicos (topic_router heurístico)

**Decisión:** El mapeo URL/subreddit/host → topic reside en un **archivo JSON externo** (`Config/topic_routes.json`) para facilitar actualización sin tocar código. La tool LoreExtractorTool carga ese archivo y aplica la resolución **dentro de la misma tool** antes de llamar a `add_fact`.

- **Estructura:** `topic_routes.json` tiene `subreddits` (ej. `"worldbuilding": "rol_lore"`) y `hosts` (ej. `"godofwar.fandom.com": "mitologia"`). Claves en minúsculas al comparar.
- **Resolución:** Si el usuario no pasa `topic`, la tool extrae subreddit de la URL (Reddit) o host de `wiki_base` (MediaWiki) y busca en el diccionario cargado.
- **Fallback:** Si el archivo no existe o falla la carga, se usa un diccionario por defecto embebido en código (`_DEFAULT_TOPIC_ROUTES`).

### 4.2 Síntesis con DataStructurerAgent (lore)

**Decisión:** **Texto original intacto** + bloque de metadatos al principio. No se reemplaza el artículo por un resumen denso.

- **Comportamiento:** Si `structurer_before_store=true`, LoreExtractorTool ejecuta DataStructurerAgent sobre el texto extraído; la salida estructurada (tópico, resumen, conceptos) se concatena como **prefijo** seguido de `\n\n---\n\n` y el texto original completo. Ese string es lo que se guarda en memoria semántica.
- **Ventaja:** La búsqueda vectorial sigue teniendo el narrative completo; los metadatos mejoran el contexto y la clasificación por topic sin perder detalle de worldbuilding.

### 4.3 DAG en el PlanExecutor (preparativos)

**Decisión:** Los planes complejos (p. ej. minería) se definen como **DAG en un archivo externo** (`Config/plan_dags.json`), con nodos que tienen `tool_name`, `params` y `depends_on`. El Planner convierte el DAG en una **lista ordenada por dependencias** (orden topológico) y la devuelve al PlanExecutor; la ejecución sigue siendo secuencial, pero la fuente de verdad es el grafo.

- **Formato:** Por cada plan (ej. `investigate_web`), un objeto `nodes` con ids (`"0"`, `"1"`, …); cada nodo tiene `depends_on: []` o `["0"]`, etc. En `params` se puede usar `{{message}}` para inyectar el mensaje del usuario.
- **Uso:** El Planner, al resolver el intent `web_scraper`, intenta cargar el DAG `investigate_web` desde `plan_dags.json`; si existe, llama a `_dag_to_steps(dag, text)` para obtener la lista de Steps en orden topológico y la devuelve. Si no hay DAG, se usa la lista plana hardcodeada.
- **Futuro:** Cuando el PlanExecutor soporte ejecución paralela, los pasos con `depends_on` vacío podrán lanzarse en paralelo (ThreadPoolExecutor); el mismo `plan_dags.json` servirá sin cambiar de formato.
- **Fase siguiente:** Si se quiere afinar (p. ej. un post en r/gamedev que habla de narrativa), un **paso opcional de clasificación** con Lucifer sobre el título o el primer párrafo extraído podría devolver `topic` y pasarse al store. Ese paso sería opcional y configurable.
- **Resumen:** Implementar un **topic_router** basado en URL/subreddit (reglas) que el Planner o la tool invoquen antes de guardar; el usuario puede seguir pasando `topic` explícito si lo desea.

---

## 5. Refinamiento del DAG y orquestación (escenarios de estrés)

Análisis de los tres vectores de fallo antes de introducir ejecución paralela real en el PlanExecutor.

### 5.1 Gestión de errores en nodos dependientes (DAG)

**Pregunta:** Si el paso "0" (delegate_web_scraper) falla con HTTP 403, ¿fail-fast (abortar todo) o marcar "0" como fallido y cancelar solo los nodos que dependen de él, permitiendo que otras ramas independientes sigan?

**Opciones:**

| Política | Comportamiento | Cuándo usar |
|----------|----------------|-------------|
| **fail-fast** | En cuanto un nodo devuelve error (o `error: true` en ToolResult), el PlanExecutor aborta el plan y devuelve el mensaje de error. No se ejecutan más pasos. | Cadenas lineales (investigate_web: 0→1→2→3→4). Si falla el scraper, no tiene sentido ejecutar cleaner/filter/structurer. |
| **cancel-dependents-only** | Se marca el nodo como fallido; no se programan ni ejecutan los nodos cuyo `depends_on` incluye a ese nodo. El resto del DAG (ramas independientes) sigue. | DAG con ramas paralelas: p. ej. tres extracciones en paralelo (0a, 0b, 0c) y un nodo "3" que depende de las tres; si 0b falla, 0a y 0c pueden completar y "3" podría recibir resultados parciales o marcarse como fallido. |

**Recomendación para 4.0:**

- **Por defecto (y para el DAG actual):** **fail-fast**. El plan `investigate_web` es una cadena lineal; si falla cualquier paso, abortar evita gastar llamadas y da una respuesta clara al usuario.
- **Cuando existan DAG con ramas paralelas:** Añadir en `Config/planner.json` (o en el propio `plan_dags.json` por plan) una clave opcional `dag_failure_policy`: `"fail_fast"` | `"cancel_dependents_only"`. El PlanExecutor, al implementar ThreadPoolExecutor, comprobará esa política: si es `cancel_dependents_only`, no programará los sucesores del nodo fallido y seguirá con el resto; si es `fail_fast` o no está definida, abortará en el primer error.

**Implementación futura (PlanExecutor):** Antes de ejecutar un paso, no hay cambio; cuando se pase a ejecución por oleadas (por dependencias), en cada oleada se esperará a todos los pasos de esa oleada; si alguno falla, aplicar la política configurada y, en fail-fast, devolver inmediatamente el error.

---

### 5.2 Ciclos en la definición del DAG (plan_dags.json)

**Pregunta:** Si se introduce por error un ciclo (A depends_on B, B depends_on A), ¿el código entra en bucle infinito o se lanza un error claro?

**Estado actual:** La función `_dag_to_steps` en el Planner usa un ordenamiento tipo Kahn: en cada iteración se añade a `order` un nodo cuyas dependencias ya están en `order`. Si en algún momento ningún nodo de `remaining` puede añadirse (porque todos tienen al menos una dependencia fuera de `order`), queda un conjunto `remaining` no vacío: eso indica ciclo o dependencias inválidas (p. ej. depends_on un id que no existe).

**Implementación:** Se ha añadido detección explícita de ciclo: cuando `not added` y `remaining` no está vacío, se lanza **`DAGCycleError`** (subclase de `ValueError`) con el nombre del DAG y la lista de nodos que no pudieron ordenarse (los involucrados en el ciclo o con deps rotas). El Planner captura `DAGCycleError` al resolver `web_scraper`, registra un warning y **fallback a la lista plana** hardcodeada, de modo que el sistema sigue funcionando aunque el JSON esté mal.

**Recomendación:** No validar el DAG "al arrancar" (no hay un único arranque de Lilith que cargue todos los DAG). La validación ocurre **en el momento del plan**: cuando el usuario dispara un intent que usa un DAG, se llama a `_dag_to_steps` y, si hay ciclo, se lanza y se captura, y se usa el plan plano. Opcionalmente, se podría añadir un script de comprobación (o un test) que cargue `plan_dags.json` y llame a `_dag_to_steps` para cada DAG con un mensaje dummy, para detectar ciclos en CI o tras editar el JSON.

---

### 5.3 Inyección dinámica de variables e instancias de sub-grafo

**Pregunta:** Para "extraer 3 URLs del mensaje y procesarlas en paralelo", ¿existe un mecanismo que genere N instancias de un sub-grafo (una por URL)?

**Estado actual:** El DAG en `plan_dags.json` es **estático**: un único flujo con `{{message}}` sustituido por el mensaje completo. No hay convención para "lista de valores" (p. ej. `{{urls}}`) ni expansión de un sub-grafo en N nodos (uno por URL).

**Opciones de diseño para el futuro:**

1. **Expandir en el Planner (recomendado):**  
   Para intents que lo requieran (p. ej. "investiga estas 3 URLs"), el Planner podría:
   - Detectar en el mensaje una lista de URLs (regex o parser).
   - Cargar un DAG "plantilla" que tenga un nodo especial o un marcador (ej. `"expand": "urls"`).
   - Generar N copias del sub-grafo (scraper → cleaner → …) con `params` donde `{{url}}` sea distinto en cada copia; los ids de nodos pasarían a ser compuestos (ej. `0_url_1`, `0_url_2`, `0_url_3`) y un nodo "agregador" dependería de todos ellos (`depends_on: ["0_url_1", "0_url_2", "0_url_3"]`).
   - Devolver la lista de Steps ya expandida (orden topológico de ese grafo ampliado). El PlanExecutor no necesitaría saber que hubo "expansión"; solo ejecutaría pasos en orden o, con paralelismo, ejecutaría en paralelo los nodos de la primera oleada (las 3 extracciones).

2. **Herramienta "multi-url" en una sola tool:**  
   Una tool que reciba la lista de URLs y, internamente, haga las N peticiones en paralelo (p. ej. ThreadPoolExecutor dentro de la tool). El DAG seguiría siendo estático (un solo nodo "scraper_multi"); la complejidad se encapsula en la tool. Menos flexible para combinar con otros pasos del DAG por URL.

3. **Placeholder en JSON:**  
   En `plan_dags.json`, algo como `"params": { "task": "{{message}}", "urls_key": "extract_urls" }` y que el Planner interprete "extraer del mensaje la lista asociada a extract_urls (ej. URLs) y expandir". Requeriría convención y documentación.

**Recomendación:** Mantener el DAG estático actual; para el caso "N URLs en paralelo", implementar en una **fase posterior** la expansión en el Planner (opción 1): un intent específico o una regla que detecte "varias URLs" y genere el grafo expandido antes de llamar a `_dag_to_steps`. El JSON del DAG no obliga a topología estática "para siempre": el Planner puede ser el que, a partir de un DAG plantilla y una lista extraída del mensaje, produzca un DAG ampliado en memoria y luego lo convierta a steps. Así no hace falta cambiar el formato de `plan_dags.json` para el caso simple (un solo mensaje/URL).

---

## 6. Concurrencia y agregación (extremos del grafo)

Definición de cómo se obtienen las entidades para expansión, cómo se agregan las salidas paralelas y qué límites de concurrencia se aplican.

### 6.1 Identificación de entidades (extractor de URLs)

**Pregunta:** ¿Cómo extraer la lista de URLs del mensaje del usuario: regex puro o paso de NLP/clasificador?

**Decisión:** **Expresiones regulares puras en el Planner**, por baja latencia y cero dependencia de modelos. Un paso de NLP o clasificador local añadiría latencia y complejidad sin necesidad para el caso “enlaces en texto”.

**Implementación:** En el Planner se ha añadido `_extract_urls_from_message(text, max_urls=10)`:

- **Patrón:** `https?://[^\s\)\]\">\']+` (URLs que terminan en espacio, paréntesis, corchetes o comillas). Se elimina puntuación final (`. , ; :`) del token.
- **Salida:** Lista ordenada por primera aparición, sin duplicados, con tope `max_urls` (por defecto 10) para no generar DAG gigantes.
- **Uso:** Cuando se implemente la expansión dinámica (sección 5.3), el intent “investiga estas URLs” (o similar) llamará a `_extract_urls_from_message(message)`; si hay 2+ URLs se usará el DAG plantilla expandido (N copias del sub-grafo); si hay 0 o 1 URL se mantiene el flujo actual (un solo mensaje o una sola URL).

**Alternativa futura:** Si hiciera falta distinguir “enlaces que el usuario pide procesar” de “enlaces mencionados en un párrafo”, se podría añadir un paso opcional de clasificador/NLP solo para ese intent; por defecto, regex es suficiente.

---

### 6.2 El nodo agregador (fan-in)

**Pregunta:** ¿Qué tool ejecuta el nodo agregador que depende de las N salidas (0_url_1, 0_url_2, …)? ¿Concatenación en el PlanExecutor o Lucifer para resumen unificado?

**Opciones:**

| Enfoque | Comportamiento | Pros / contras |
|--------|----------------|-----------------|
| **Concatenación en PlanExecutor** | El “agregador” no es una tool real. El PlanExecutor, para un paso con `context_from_steps: ["0_url_1", "0_url_2", …]`, construye ya hoy el contexto con `_build_context_from_steps` (scratchpad) y lo inyecta en el **siguiente** paso. Ese siguiente paso puede ser `store_semantic_fact` (guarda el texto concatenado) o `delegate_lucifer` (recibe el bloque unificado como contexto). | Sin tool nueva; reutiliza scratchpad; bajo coste. |
| **Tool “aggregate_context”** | Una tool explícita que recibe en `params` las claves de steps y devuelve la concatenación (o un resumen muy corto). El PlanExecutor la invocaría como un paso más; su salida sería el `last_result` para el siguiente paso. | Contrato claro; la agregación es un paso visible en el plan. |
| **Lucifer como agregador** | El nodo agregador es `delegate_lucifer` con `context` = concatenación de las N salidas y `task` tipo “Resume en un único texto coherente las siguientes extracciones para el usuario.” | Resumen unificado y legible para Discord; coste de API y latencia. |

**Recomendación:**

- **Por defecto:** No definir un “nodo agregador” como tool distinta. El nodo de fan-in se modela como un paso cuyo **único propósito** es que el PlanExecutor inyecte en el siguiente paso el `context` construido desde las N salidas (`context_from_steps`). Es decir: el agregador es **implícito** (el mecanismo de scratchpad). El paso que **sigue** al fan-in será quien “consuma” ese contexto:
  - **store_semantic_fact:** recibe el texto concatenado y lo guarda (comportamiento actual de scratchpad).
  - **delegate_lucifer:** recibe el mismo bloque y puede redactar un resumen unificado antes de enviar a Discord.
- **Opcional (config o por DAG):** Si en el futuro se quiere “siempre resumen Lucifer” cuando hay N URLs, el último paso del DAG expandido puede ser `delegate_lucifer` con task de resumen y `context_from_steps` apuntando a las N ramas; así el nodo agregador “lógico” es Lucifer, y la concatenación la sigue haciendo el PlanExecutor para rellenar su `context`.

**Resumen:** La agregación es **concatenación en el PlanExecutor** (scratchpad); la “tool” que recibe ese contexto puede ser `store_semantic_fact` (solo guardar) o `delegate_lucifer` (resumen unificado para el usuario).

---

### 6.3 Límites de concurrencia (max_workers)

**Pregunta:** ¿`max_workers` global en configuración (ej. 4 o 5) como embudo o límite dinámico según nodos paralelos del DAG?

**Decisión:** **Límite global en configuración**, con cota superior efectiva = `min(dag_max_workers, N)` donde N = número de nodos paralelos en la oleada actual. Así se evita golpear red y cuotas de API con demasiados hilos aunque el DAG tenga muchas ramas.

**Implementación:**

- En **`Config/planner.json`** (o en un futuro `executor.json` si se separa): clave **`dag_max_workers`** (por defecto **5**). Actúa como embudo de seguridad para el `ThreadPoolExecutor` del PlanExecutor cuando se implemente ejecución paralela.
- Al ejecutar una oleada de nodos paralelos, el PlanExecutor usará `min(dag_max_workers, len(nodos_paralelos))` como tamaño del pool (o ejecutará en lotes de ese tamaño si se prefiere no tener más workers que nodos). Con Ryzen 5 5500 y 48 GB RAM, 4–5 workers son suficientes para I/O; el cuello de botella suele ser red y límites de APIs (Reddit, MediaWiki, etc.), no CPU.

**Documentación:** El valor y su intención quedan documentados en `planner.json` mediante `_comment_dag_max_workers`. No se crean más hilos de los necesarios para la oleada actual.

---

## 7. Cuellos de botella y UX (antes del encendido)

Tres escenarios críticos antes de activar ejecución paralela o DAGs con fan-in grande.

### 7.1 Saturación del contexto en el fan-in

**Pregunta:** Si se extraen 5 URLs y el agregador (p. ej. delegate_lucifer) recibe la concatenación de las 5 extracciones, ¿`scratchpad_max_context_chars` con truncamiento proporcional basta o se pierde coherencia narrativa?

**Riesgo:** Con 5 artículos largos y reparto estrictamente proporcional, cada uno recibe ~2000 caracteres si el tope es 10 000; si uno es mucho más largo que los demás, los cortos pueden quedar con una cuota muy pequeña y el resumen de Lucifer perdería contexto de esas fuentes.

**Decisión e implementación:** Se añade una **cuota mínima por fuente** (`scratchpad_min_chars_per_source`, por defecto **800** en `Config/planner.json`). En `_build_context_from_steps`:

- Primero se calculan las cuotas proporcionales como hasta ahora.
- Si `min_chars_per_source > 0`, cada cuota se lleva al menos ese mínimo.
- Si la suma de cuotas supera `max_context_chars`, se reescala proporcionalmente para no exceder el tope (y se reparte el resto en un paso para evitar redondeos).

Así, con 5 fuentes y tope 10 000, cada una recibe al menos 800 caracteres (4000 en total para el mínimo); el resto se reparte de forma proporcional. La coherencia narrativa por fuente mejora sin dejar de respetar el límite global. Opcionalmente, en DAGs con muchas ramas (p. ej. 8+), se puede subir `scratchpad_max_context_chars` o bajar el número de URLs a expandir (p. ej. `max_urls` en el extractor).

---

### 7.2 Embotellamiento en los locks (contención Reddit)

**Pregunta:** Si el DAG expande 5 URLs de Reddit en la misma oleada, los 5 hilos chocan con `_REDDIT_LOCK`; con `_REDDIT_MIN_GAP = 2.0` s, el último hilo puede tardar 8–10+ segundos solo en despachar su petición. ¿Cómo afecta al timeout global de la interacción con Discord?

**Análisis:** La serialización en el lock es deliberada para cumplir con el rate limit de Reddit. El tiempo total de la oleada de 5 Reddits será del orden de 5×2 s + 5×latencia_HTTP ≈ 10–15+ s solo para esa oleada, a lo que hay que sumar el resto del plan (scrape, cleaner, filter, structurer, store, posible Lucifer). Discord suele dar **3 segundos** para la primera respuesta antes de marcar "failed" o "thinking"; muchas integraciones permiten **defer** (responder en 3 s con "thinking" y luego editar/enviar el mensaje final antes de 15 min).

**Recomendaciones:**

1. **Límite de URLs cuando hay Reddit:** En la expansión dinámica del DAG, si se detectan varias URLs de Reddit, limitar a 2–3 en paralelo (o serializarlas en el propio plan) para no disparar 5× gap. Configurable p. ej. `max_reddit_urls_per_plan` en `planner.json` o en la tool.
2. **Timeout del cliente:** El cliente que llama a `POST /api/discord/chat` debe usar un timeout de red alto (p. ej. 60–120 s) para planes largos; el timeout de Discord para "editar mensaje" es mucho más amplio (minutos).
3. **Acuse de recibo (ver 7.3):** Enviar un mensaje inmediato ("Lilith está explorando X enlaces...") dentro de los 3 s y luego editar con el resultado evita que el usuario crea que el bot se colgó y permite que el backend trabaje 30–60 s si hace falta.

---

### 7.3 Feedback asíncrono al usuario (UX en Discord)

**Pregunta:** ¿Hay algún mecanismo de acuse de recibo en Discord (mensaje temporal "Lilith está explorando 3 enlaces..." que luego se edita con el resultado)?

**Estado actual:** El endpoint `POST /api/discord/chat` es síncrono: espera a que `orchestrator.execute_plan` termine y devuelve la respuesta en un único JSON. El **cliente** (bot de Discord que invoca esta API) es quien envía mensajes a Discord. Por tanto, el acuse de recibo debe implementarse en el **cliente** (p. ej. en el proceso que recibe eventos de Discord y llama a la API).

**Recomendación:**

1. **Patrón "placeholder + editar":** Antes de llamar a `POST /api/discord/chat` (o justo después de enviar la petición), el cliente envía a Discord un mensaje de la bot como "Lilith está pensando..." o "Explorando X enlaces...". Cuando la API devuelve, el cliente **edita** ese mensaje con la respuesta final (o envía un segundo mensaje y opcionalmente borra el placeholder).
2. **Cuándo mostrar placeholder:** Siempre que el plan pueda ser largo (p. ej. más de 3 pasos o intents como `investigate_web` / `extract_lore`). Opcionalmente, la API puede devolver en el JSON un campo **`long_running`** o **`estimated_steps`** (ya disponible en el plan) para que el cliente decida si mostró placeholder y si debe mostrar "Explorando N enlaces...".
3. **Discord "defer":** Si el cliente usa interacciones (slash commands, botones), puede usar `defer()` / "thinking" para tener hasta 15 minutos para editar la respuesta; el flujo sigue siendo: respuesta rápida (< 3 s) y luego edición con el resultado.

**Resumen:** No hace falta cambiar la API para el acuse de recibo; el cliente debe enviar un mensaje inmediato y editar (o reemplazar) cuando llegue la respuesta. Opcionalmente, la API puede exponer una señal (`long_running`, `steps_count`) para que el cliente adapte el texto del placeholder ("Pensando...", "Explorando 3 enlaces...", etc.).

---

## 8. El salto a producción (vectores de riesgo)

Tres vectores evaluados antes de encender scraping masivo o ThreadPoolExecutor.

### 8.1 Concurrencia en la base de datos (bloqueos de escritura)

**Pregunta:** Con ThreadPoolExecutor, varias ramas podrían escribir a la vez (varios `store_semantic_fact`). ¿ChromaDB y los gestores JSON/JSONL son thread-safe o hay que sincronizar en el hilo principal?

**Análisis:** ChromaDB (persistencia con DuckDB/SQLite) y los append a `facts.jsonl` en `SemanticMemory.add_fact` no están protegidos por defecto. Escrituras concurrentes pueden provocar "database is locked" (Chroma) o líneas JSONL intercaladas/corruptas.

**Decisión e implementación:** Se ha añadido un **Lock global de escritura** en el **MemoryManager** (`threading.Lock()`). Todas las llamadas a `add_fact` pasan por `MemoryManager.add_fact`, que adquiere `_write_lock` antes de delegar en `semantic_store.add_fact`. Así, aunque varios hilos del DAG ejecuten `store_semantic_fact` en paralelo, las escrituras (JSONL + ChromaDB) se serializan y se evitan bloqueos y corrupción. Lecturas (search_facts, get_recent_facts) no necesitan el lock para consistencia básica; si en el futuro se exige consistencia estricta lectura/escritura, se puede ampliar el lock o usar un RLock por capa.

**Alternativa documentada:** Otra opción sería que el PlanExecutor, en modo paralelo, **no** permita que los workers llamen a tools que escriben; en su lugar, los resultados se devolverían al hilo principal y este ejecutaría un único paso de "persistir" al final. Por ahora, el lock en MemoryManager es la solución más simple y compatible con el diseño actual (cada step puede invocar store_semantic_fact).

---

### 8.2 Granularidad del feedback asíncrono (WebSockets vs HTTP)

**Pregunta:** ¿Es viable un canal WebSockets entre FastAPI y el bot de Discord para transmitir el progreso del DAG en tiempo real ("Paso 1/5: Extrayendo Reddit...", "Paso 2/5: Estructurando entidades...")?

**Estado actual:** El flujo es HTTP síncrono: el cliente espera la respuesta final. El placeholder "Lilith está explorando..." puede estar 40–60 s sin cambios.

**Opciones:**

| Enfoque | Descripción | Viabilidad |
|--------|-------------|------------|
| **Solo HTTP + placeholder** | Un único mensaje inicial y edición al terminar. | Ya documentado (sección 7.3). Suficiente para la mayoría de casos. |
| **WebSockets para progreso** | El cliente abre un WebSocket a FastAPI; el PlanExecutor (o el Orchestrator) emite eventos por paso ("step_start", "step_done", "wave", etc.); el bot recibe y edita el mensaje en Discord ("Paso 1/5: ..."). | **Viable en el futuro.** Requiere: (1) endpoint WebSocket en FastAPI (p. ej. `/api/discord/chat/stream` o un canal por sesión); (2) que el cliente envíe un `channel_id` / `message_id` para editar; (3) que el PlanExecutor (o un wrapper) invoque un callback o publique en una cola por cada paso/wave; (4) que el worker que atiende el WebSocket envíe al bot (o que el bot sea el que mantiene el WS y edita el mensaje). La complejidad es media-alta (estado de sesión, timeout del WS, reconexión). |
| **Polling** | El cliente hace GET cada N segundos a un endpoint de estado (job_id) y actualiza el mensaje. | Alternativa sin WebSockets; requiere almacenar estado de "plan en curso" por job_id y limpiarlo al terminar. |

**Recomendación:** Mantener **HTTP + placeholder** como está. Para una segunda iteración (mejor UX en planes muy largos), implementar **WebSockets**: el cliente que inicia el chat envía la petición y abre un WS con un `request_id`; la API, al ejecutar el plan, envía eventos al WS asociado a ese request (si existe); el cliente actualiza el mensaje de Discord en cada evento. No es necesario para el primer encendido.

---

### 8.3 Validación del espacio latente (prueba de fuego)

**Pregunta:** Tras la primera extracción real (p. ej. wiki de un juego de rol), ¿cómo validamos que topic_router y chunking semántico funcionaron? ¿Script que consulte ChromaDB y mida similitud o solo preguntas a Lilith en Discord?

**Enfoque recomendado (combinado):**

1. **Prueba subjetiva en Discord:** Después de alimentar a Lilith (p. ej. "Extrae el lore de [URL wiki]"), hacer preguntas concretas en Discord ("¿Qué sabes de X?", "¿Quién es el personaje Y?") y valorar si las respuestas son coherentes y usan el contenido extraído. Rápido y válido como primera comprobación.
2. **Script de validación (ChromaDB):** Un script que consulte directamente el vector store con frases esperadas (p. ej. nombres de personajes o conceptos del lore) y muestre los resultados con `topic`, `source_id`, distancia y un fragmento del texto. Así se comprueba que (a) los chunks están indexados, (b) el `topic` asignado por topic_router es el esperado, y (c) la similitud devuelve fragmentos relevantes. En el repo se añade **`Scripts/validate_chroma_facts.py`**: recibe una query y opcionalmente un topic; usa la misma lógica que la memoria (vector_store.search_facts) e imprime los top-k resultados con metadatos. Uso: `python Scripts/validate_chroma_facts.py "Valhalla" --topic rol_lore` desde la raíz del proyecto (Core).
3. **Métricas opcionales:** Si se quiere ir más allá, se puede definir un pequeño set de preguntas y respuestas esperadas (por dominio) y medir recall@k o que la respuesta de Lilith contenga ciertas entidades; eso quedaría para una fase de QA más formal.

**Resumen:** Para el primer encendido, combinar (1) preguntas en Discord y (2) ejecución de `validate_chroma_facts.py` con 2–3 queries representativas del dominio ingerido. El script no sustituye la prueba con usuario real, pero da una comprobación objetiva de que el pipeline de indexación y filtro por topic funciona.

---

## 9. Atomicidad y umbrales (micro-fisuras resueltas)

Tres aspectos que afectan la consistencia y la calidad de la memoria a largo plazo.

### 9.1 Atomicidad de la escritura dual (split-brain)

**Pregunta:** Si la escritura en JSONL tiene éxito pero ChromaDB falla (OOM, I/O), ¿hay rollback o queda memoria dividida (hecho en texto pero invisible para búsqueda vectorial)?

**Decisión:** Evitar split-brain invirtiendo el **orden de escritura**: primero **ChromaDB**, luego **JSONL**. Así, si ChromaDB falla, no se escribe ninguna línea en JSONL y no hay hecho “solo en texto”. Si ChromaDB tiene éxito y falla la escritura en JSONL (p. ej. disco lleno), el hecho sigue siendo recuperable por búsqueda vectorial; solo quedaría fuera de `get_recent_facts` (recencia por JSONL). Ese caso es más raro y aceptable.

**Implementación:** En `SemanticMemory.add_fact` (Backend.memory.semantic_memory) se reordenó la lógica: para un hecho único se llama a `vs_add_fact` (ChromaDB) y solo después se hace el append a `facts.jsonl`. Para el caso con chunking, se ejecutan todos los `vs_add_fact` en bucle y, si no hay excepción, se escriben todas las líneas JSONL en un solo `open(..., "a")`. Si en el bucle ChromaDB lanza (p. ej. en el tercer chunk), no se escribe JSONL; puede quedar un ChromaDB “parcial” (2 de 5 chunks), que se puede corregir con una nueva ejecución (upsert sobrescribirá). No se implementa rollback explícito en ChromaDB (borrar los chunks ya insertados) para no complicar el flujo.

---

### 9.2 Umbral del ruido (distance cut-off)

**Pregunta:** ChromaDB devuelve siempre K resultados si hay datos, aunque sean poco relevantes. ¿Existe un umbral de distancia máxima para descartar resultados antes de inyectarlos en el prompt?

**Decisión:** Sí. Se añade en **`Config/memory.json`** la clave **`vector_max_distance`** (por defecto **1.5** para embeddings L2 normalizados). Los resultados de `search_facts` con `distance` mayor que ese valor se filtran en `_get_facts_for_query` antes de devolverlos al LLM. Si `vector_max_distance` es 0, vacío o no numérico, no se aplica filtro (comportamiento anterior).

**Implementación:** En `SemanticMemory._get_facts_for_query`, tras obtener `results` de `search_facts`, se lee `vector_max_distance` de la config; si es un float > 0, se hace `results = [r for r in results if r.get("distance") is None or r.get("distance") <= threshold]`. Así Lilith solo recibe hechos por debajo del umbral de “ruido” configurado.

---

### 9.3 Manejo de actualizaciones (upserts vs inserts)

**Pregunta:** Si se re-extrae la misma fuente (misma URL/wiki) más tarde, ¿ChromaDB duplica chunks (add) o sobrescribe (upsert)?

**Estado actual:** El **vector_store** ya utiliza **`collection.upsert(...)`** en `add_fact` (no `add`). Los `fact_id` son estables: hecho único → timestamp; chunks → `{source_id}_chunk_{i}`. Si se vuelve a extraer el mismo contenido, el `source_id` (hash del texto o el que proporcione la tool) será el mismo y los `fact_id` de los chunks coincidirán; **upsert** reemplaza los vectores y documentos existentes con el mismo id. No hay duplicados ni saturación por versiones viejas.

**Recomendación:** Mantener upsert. Si en el futuro el `source_id` se derivara solo de la URL (sin hash del contenido), una actualización de la wiki produciría el mismo `source_id` y los mismos `fact_id` por posición de chunk; la re-extracción actualizaría los chunks en ChromaDB correctamente.

---

## 10. Hacia la concurrencia y la UX (tres frentes)

Después del Paciente Cero: estado del defer en Discord, madurez para ThreadPoolExecutor y formateo del fan-in en la personalidad.

### 10.1 Límite de 3 segundos en Discord (defer y placeholder)

**Pregunta:** ¿Está configurado el chat_handler para enviar un defer o placeholder que nos dé la gracia de 15 minutos?

**Estado:**

- **Slash commands** (/eva, /adan, /lucifer, /auto, /charla, etc.): En **bot.py** cada comando hace **`await interaction.response.defer()`** (o `defer(ephemeral=True)`) **antes** de llamar al handler que invoca la API. Eso cumple con el límite de 3 segundos de Discord para interacciones y otorga hasta **15 minutos** para enviar el follow-up. No hace falta cambiar nada en slash.
- **Mensajes normales** (on_message / mención o DM): No hay “interaction” que deferir. Para que el usuario no crea que el bot se colgó cuando el plan tarda (DAG, lore, varias URLs), en **chat_handler.py** se implementó un **placeholder inmediato**: en cuanto se recibe el mensaje se envía **"🔮 Lilith está pensando..."** al canal; luego se llama a la API (timeout 120 s) y, al terminar, se borra el placeholder y se envía la respuesta real. Así la primera respuesta visible llega en ~1 s y se evita la sensación de colgado aunque el backend tarde 30–60 s.

**Resumen:** Slash ya usa defer (15 min de gracia). Mensajes normales usan placeholder inmediato "Lilith está pensando..." y edición/borrado al recibir la respuesta.

---

### 10.2 Activación del ThreadPoolExecutor (oleadas topológicas)

**Pregunta:** ¿El código está lo bastante maduro para sustituir el bucle lineal por agrupación en oleadas y ejecución en paralelo?

**Estado:** El **PlanExecutor** sigue siendo un **bucle for** secuencial sobre la lista de pasos. La infraestructura defensiva está lista: **`_write_lock`** en MemoryManager (escrituras thread-safe), política **fail-fast** documentada, **plan_dags.json** con `depends_on` y **`_dag_to_steps`** que devuelve una lista en orden topológico. Lo que falta es que el **formato del plan** que recibe el PlanExecutor preserve la estructura de dependencias: hoy el Planner convierte el DAG en una **lista plana** de Steps (orden topológico) y no pasa `depends_on` por paso. Para ejecutar oleadas en paralelo hace falta que cada Step (o el plan completo) exponga **qué pasos pueden ejecutarse en paralelo** (los que tienen todas sus dependencias satisfechas).

**Próximo paso recomendado:** (1) Extender el **Step** (o el tipo de plan) para incluir opcionalmente `step_id` y `depends_on` (lista de ids). (2) Cuando el Planner use un DAG (p. ej. desde `plan_dags.json` o un DAG expandido con N URLs), que emita **Steps con esa metadata**. (3) En el PlanExecutor: agrupar pasos por “oleada” (todos los que tienen `depends_on` vacío o ya resueltos), ejecutar cada oleada con **ThreadPoolExecutor** (o `asyncio.gather` si las tools pasan a async), actualizar `step_results`, y pasar a la siguiente oleada. El código actual está **listo** para ese cambio (lock, fail-fast, scratchpad con `context_from_steps`); solo falta el formato del plan y la lógica de oleadas en el ejecutor.

---

### 10.3 Formateo del fan-in en el prompt (citar fuentes vs asimilar)

**Pregunta:** Cuando Lucifer recibe un bloque grande de texto (varias fuentes, scratchpad_min_chars_per_source = 800), ¿Lilith debe citar explícitamente las fuentes ("He revisado los archivos de Fandom y Reddit...") o responder como si ese conocimiento hubiera estado siempre en su mente?

**Opciones:**

| Enfoque | Descripción | Cuándo usar |
|--------|-------------|-------------|
| **Citar fuentes** | Instrucción en el prompt o en la personalidad: que Lilith mencione brevemente de dónde viene la información (Fandom, Reddit, “los archivos que consulté”) cuando el contexto inyectado provenga de minería/lore. Refuerza transparencia y confianza. | Si quieres que el Master sepa que la respuesta se basa en extracciones recientes y no en “memoria antigua”. |
| **Asimilar** | Sin instrucción especial: el modelo responde con el conocimiento inyectado como si fuera propio. Más natural y “aristocrática” (el conocimiento está en su mente, no “acabo de leer”). | Si prefieres que Lilith hable como si siempre hubiera conocido ese lore, sin meta-comentarios sobre fuentes. |

**Recomendación:** Dejar la decisión en **configuración o en la personalidad**. Añadir en **Config** (p. ej. `planner.json` o `memory.json`) una clave opcional **`lilith_cite_sources_when_mining`** (booleano, por defecto `false`). Si es `true`, el Orchestrator o el armado del system prompt para Lucifer puede inyectar una línea del tipo: *"El contexto siguiente proviene de extracciones recientes (wikis, Reddit). Puedes mencionar brevemente las fuentes si es natural (ej. «según lo extraído de Fandom…»); si no, responde con normalidad."* Si es `false`, no se añade nada y Lucifer asimila el bloque como conocimiento propio. Así se puede calibrar el tono (transparencia vs fluidez) sin tocar código cada vez.

---

## 11. Paralelismo y oleadas (decisiones implementadas)

Tres escenarios críticos antes de refactorizar el ejecutor a oleadas con ThreadPoolExecutor.

### 11.1 Gestión de tiempos muertos en la oleada (barrera vs timeout)

**Pregunta:** ¿Barrera estricta (esperar a que todos terminen) o timeout por oleada que cancele los colgados y continúe solo con los exitosos?

**Decisión:** **Barrera estricta por defecto** (`concurrent.futures.wait(..., return_when=ALL_COMPLETED)`). Si una URL tarda 45 s, la oleada espera 45 s; el nodo agregador recibe todas las salidas y el plan es predecible.

**Opcional:** En **`Config/planner.json`** la clave **`dag_wave_timeout_seconds`** (por defecto **0**) actúa como timeout por oleada: si es > 0, el PlanExecutor hace `wait(futures, timeout=...)`; los futuros no terminados se cancelan y se escribe en `step_results` el marcador `"(Paso cancelado por timeout de oleada)"`. La siguiente oleada (p. ej. agregador) puede recibir menos entradas; el comportamiento es configurable para entornos donde se prefiera no bloquear por un solo recurso lento.

**Implementación:** PlanExecutor lee `dag_wave_timeout_seconds`; si > 0, usa `wait(..., timeout=...)`, cancela los pendientes y rellena sus claves en `step_results` con el mensaje de cancelación. Si no hay timeout, se usa solo `wait(..., return_when=ALL_COMPLETED)`.

---

### 11.2 Seguridad de hilos en step_results (solo escritura en el hilo principal)

**Pregunta:** ¿Lock para proteger escrituras en `step_results` o confiar en recolección en el hilo principal?

**Decisión:** **Recolección en el hilo principal**. Los workers solo ejecutan la tool y devuelven el resultado vía `Future.result()`. El hilo principal, tras `wait()`, hace `step_results[sid] = fut.result()` para cada futuro. Así **solo un hilo escribe** en `step_results` y no hace falta `threading.Lock`. Los hilos del pool no acceden al diccionario compartido para escribir.

**Implementación:** La función **`_execute_step_worker`** solo recibe `caller`, `tool_name`, `params`, `registry`, `skip_cache` y devuelve la cadena de resultado. El PlanExecutor construye `params` en el hilo principal (con `_build_step_params` y el estado actual de `step_results`), envía el trabajo al executor y, después de `wait()`, asigna los resultados a `step_results` en el mismo hilo.

---

### 11.3 Evolución de la clase Step (retrocompatibilidad)

**Pregunta:** ¿Step con `step_id` y `depends_on` mantiene retrocompatibilidad o reescribimos todos los planes al formato nuevo?

**Decisión:** **Retrocompatibilidad estricta**. La clase **Step** tiene **`step_id: Optional[str] = None`** y **`depends_on: Optional[List[str]] = None`**. Los planes que no los usen (lista plana actual) siguen siendo válidos: en el PlanExecutor, para cada paso se usa `step_id = getattr(step, "step_id", None) or str(i)` y `depends_on = getattr(step, "depends_on", None)`; si `depends_on` es `None`, se asigna `[str(i-1)]` si `i > 0` y `[]` si `i == 0`. Así los planes lineales antiguos se interpretan como cadena 0 → 1 → 2 → … sin tocar el Planner ni los planes estáticos. Los planes generados desde un DAG (p. ej. `_dag_to_steps`) ya rellenan `step_id` y `depends_on` explícitamente.

**Implementación:** En **planner.py**, `Step` es un dataclass con los cuatro campos; los constructores existentes que solo pasan `tool_name` y `params` siguen funcionando. En **plan_executor.py**, la normalización a `(step_id, depends_on, step)` aplica los valores por defecto antes de calcular oleadas.

---

## 12. Cuellos de botella: pureza de datos, filtrado hacia APIs y fan-out

Tres frentes para que la entrada a Lilith sea quirúrgicamente limpia y la delegación a APIs sea eficiente.

### 12.1 Grado de pureza de los datos (DataStructurerAgent)

**Pregunta:** ¿“Datos limpios” = solo texto libre de basura web, o = transformar con DataStructurerAgent a un esquema JSON rígido (entidades_clave, resumen_tecnico, conceptos) antes de memoria?

**Estado actual:**

- **LoreExtractorTool:** Extrae texto plano sin HTML (BeautifulSoup + `_strip_html`). Por defecto guarda ese texto tal cual en ChromaDB (con chunking y `source_id`). Opcionalmente `structurer_before_store=true` encadena **DataStructurerAgent**: la salida es **texto formateado** (`[Minería web] Tópico: … Resumen: … Conceptos: …`) como **prefijo** + `\n\n---\n\n` + texto original. No se guarda JSON rígido en memoria.
- **DataStructurerAgent:** Heurístico (regex, listas de términos). No produce JSON con campos fijos; produce un bloque de texto enriquecido. No usa LLM.

**Opciones:**

| Enfoque | Significado de “limpio” | Pros | Contras |
|--------|-------------------------|------|--------|
| **Solo sin basura web (actual por defecto)** | Menús, footers, tablas CSS eliminados; texto plano. | Rápido, sin pérdida de detalle; RAG semántico funciona bien sobre párrafos. | No hay campos consultables (ej. “dame entidades”). |
| **Prefijo heurístico (structurer_before_store)** | Lo anterior + bloque Tópico/Resumen/Conceptos al inicio. | Mejor clasificación por tópico y resumen en el mismo chunk. | Sigue sin ser JSON; entidades son heurísticas. |
| **JSON rígido antes de memoria** | Esquema con `entidades_clave`, `resumen_tecnico`, `conceptos` guardado como hecho o en otro store. | Consultas estructuradas, posible grafo. | Requiere paso LLM o schema fijo; más latencia y coste; hay que definir dónde se guarda (ChromaDB como texto del JSON o store aparte). |

**Recomendación:**

- **Definir “limpio” en dos niveles:**
  - **Nivel 1 (obligatorio):** Texto libre de basura web. Lo cumple LoreExtractor + BeautifulSoup hoy.
  - **Nivel 2 (opcional):** Enriquecimiento para memoria. Hoy = prefijo heurístico (`structurer_before_store`). Si en el futuro se necesitan consultas del tipo “listar personajes” o campos fijos, añadir un **paso opcional** (config o Fase 4.1) que envíe el texto a Lucifer/Eva y guarde un **JSON** como hecho adicional o en un store secundario; no sustituir el texto plano en ChromaDB para no romper RAG conversacional.
- **Conclusión:** No es prioritario construir DataStructurerAgent para que transforme todo a JSON rígido antes de tocar memoria local. El texto plano (o texto + prefijo heurístico) es suficiente para ingesta limpia y RAG; el JSON rígido queda como evolución opcional cuando haya requisitos concretos de consultas estructuradas.

---

### 12.2 Filtrado de contexto hacia las APIs (Grok, Venice)

**Pregunta:** ¿Enviar el contexto extraído tal cual (confiando en `scratchpad_max_context_chars`) o implementar un paso de compresión local estricto antes de que la carga salga hacia las APIs externas?

**Estado actual:**

- El **PlanExecutor** construye el contexto para `delegate_lucifer` / `delegate_eva` desde `step_results` vía `_build_context_from_steps`, con:
  - **scratchpad_max_context_chars** (ej. 10 000): tope duro del texto concatenado.
  - **scratchpad_min_chars_per_source**: cuota mínima por paso en fan-in.
  - **scratchpad_truncation** (tail_per_step / global_tail) y **scratchpad_prefer** (tail/head/middle).
- No existe un paso de **compresión** (resumidor local, extractor de frases clave) antes de llamar a Grok o Venice. Lo que entra en `params["context"]` es el texto truncado por esas reglas.

**Opciones:**

| Enfoque | Comportamiento | Pros | Contras |
|--------|----------------|------|--------|
| **Solo truncamiento (actual)** | Confiar en `scratchpad_max_context_chars` y cuotas. | Simple, predecible, sin latencia extra. | Si el límite es alto, se consumen muchos tokens en la API; si es bajo, se puede perder detalle. |
| **Compresión local estricta** | Paso previo (resumidor LLM local o extractor heurístico) que reduce el texto antes de enviarlo a Grok/Venice. | Menos tokens y coste en APIs externas. | Latencia y complejidad; riesgo de perder matices; requiere modelo local o reglas de extracción. |
| **Límite más bajo solo para delegate_\*** | Leer en config algo como `delegate_max_context_chars` (ej. 4 000) y aplicar un recorte adicional al bloque que se inyecta en `params["context"]` cuando el paso es delegate_eva o delegate_lucifer. | Control fino del coste por llamada sin añadir un paso nuevo. | Sigue siendo truncamiento, no compresión semántica. |

**Recomendación:**

- **Corto plazo:** Mantener el modelo actual (truncamiento por scratchpad) y ser **estricto por configuración**: bajar `scratchpad_max_context_chars` si las llamadas a Grok/Venice son caras o lentas (ej. 6 000–8 000 para respuestas con mucho contexto). Opcionalmente introducir **delegate_max_context_chars** en `planner.json`: si está definido, en `_build_step_params` para `delegate_lucifer` / `delegate_eva` aplicar un recorte adicional al `user_part` (o al bloque construido) antes de montar `params["context"]`, de modo que el payload que sale de tu máquina tenga un tope explícito por delegación.
- **Medio plazo:** Si el coste en tokens sigue siendo alto, valorar un **paso de compresión opcional** (resumidor local o heurístico) solo para ramas que envían mucho contexto a APIs externas; no como default, sino como opción configurable (ej. `compress_context_before_delegate: true` y un módulo que reduzca el texto a N caracteres o a un resumen).

---

### 12.3 Manejo de la concurrencia en la extracción (fan-out de URLs)

**Pregunta:** ¿Es prioritario activar ya la extracción paralela masiva (N URLs → N hilos de limpieza/extracción) o seguir testeando estabilidad con una URL por mensaje?

**Estado actual:**

- **PlanExecutor** ya ejecuta oleadas en paralelo con **ThreadPoolExecutor** cuando el plan tiene varios pasos con dependencias satisfechas en la misma oleada.
- **Planner** tiene **`_extract_urls_from_message(text, max_urls=10)`** implementado, pero **no** lo usa al resolver intents. Para `extract_lore` devuelve un único paso `lore_extractor` con `params={"message": text, "store": True}` (una sola “tarea” por mensaje). Para `investigate_web` se usa el DAG lineal (scraper → cleaner → filter → structurer → store) con `{{message}}` inyectado; no se expande a N instancias por URL.
- Por tanto: **fan-out de URLs no está activado**. La teoría (DAG, oleadas, locks) está; falta que el Planner, ante un mensaje con varias URLs, genere N pasos (o N ramas del DAG) y el PlanExecutor los ejecute en una sola oleada.

**Opciones:**

| Enfoque | Comportamiento | Pros | Contras |
|--------|----------------|------|--------|
| **Seguir 1 URL por mensaje** | No usar `_extract_urls_from_message` para expandir el plan. | Estabilidad, menos superficie de fallo, rate limits (Reddit) más controlados. | Ingesta más lenta si el usuario pega 5 enlaces. |
| **Activar fan-out ahora** | Si el mensaje tiene 2+ URLs, generar N pasos (lore_extractor o investigate_web por URL), misma oleada; ThreadPoolExecutor ya los ejecutaría en paralelo. | Ingesta más rápida; aprovecha la infra ya implementada. | Más carga en red y APIs (Reddit 2 s entre peticiones); más puntos de fallo; hay que definir bien N máximo (ej. 3–5) y manejo cuando alguna URL falla. |

**Recomendación:**

- **Prioridad según objetivo:**
  - Si el objetivo inmediato es **estabilidad y validación** (que la cadena 1 URL → limpieza → memoria funcione bien en producción): **no** activar fan-out masivo aún; seguir con extracciones de una en una y usar el tiempo en observación (logs, calidad de lo guardado, tiempos de respuesta).
  - Si el objetivo es **acelerar ingesta** (p. ej. poblar la memoria con muchas fuentes en poco tiempo): **sí** activar el fan-out de forma controlada: en el Planner, cuando el intent sea `extract_lore` o `investigate_web`, llamar a `_extract_urls_from_message(message)`; si hay 2+ URLs, generar N pasos con `step_id` distintos (ej. `0_url_0`, `0_url_1`, …) y `depends_on=[]`, más un paso agregador que dependa de todos; límite `min(N, max_urls_per_plan)` con `max_urls_per_plan` en config (ej. 3–5) para no saturar Reddit ni timeouts de Discord.
- **Implementación sugerida cuando se active:** (1) Añadir en `planner.json` algo como `max_urls_per_plan: 3`. (2) En `_resolve_intent_from_config`, para `lore_extractor`: si `urls = _extract_urls_from_message(text)` y `len(urls) >= 2`: construir N Steps `lore_extractor` con `params={"message": url, "store": True}` o con una URL cada uno; `step_id` único por URL; `depends_on=[]`; opcionalmente un paso siguiente que dependa de todos (p. ej. delegate_lucifer con `context_from_steps` = lista de esos step_ids) para resumir. (3) Para `investigate_web` con varias URLs, análogo: N copias del subgrafo de extracción, luego agregador. Así la decisión queda en configuración y en un único punto del Planner.

---

## 13. El desafío del Fan-Out: tres vectores de riesgo resueltos

Al activar el fan-out dinámico (varias URLs → DAG en tiempo de ejecución), el Planner y el PlanExecutor deben evitar colisiones de truncamiento, fallos en cascada y contaminación cruzada en el prompt. Respuestas implementadas:

### 13.1 Colisión de truncamiento en el agregador

**Riesgo:** Si se concatenan 3 URLs y el total supera `delegate_max_context_chars` (ej. 6000), un recorte final crudo podría eliminar por completo una de las fuentes del contexto enviado a Lucifer.

**Decisión:** El truncamiento proporcional del scratchpad (**tail_per_step**, **min_chars_per_source**) se aplica **antes** del límite hacia la API. Para los pasos **delegate_lucifer** y **delegate_eva**, cuando el contexto se construye desde varias fuentes (`context_from_steps` / `depends_on`), el PlanExecutor usa:

- **max_context_chars efectivo** = `min(scratchpad_max_context_chars, delegate_max_context_chars)` si `delegate_max_context_chars` > 0.

Así, `_build_context_from_steps` ya produce un bloque de tamaño ≤ `delegate_max_context_chars`, con cuotas proporcionales (y mínimas por fuente si `scratchpad_min_chars_per_source` > 0). No se aplica un recorte final crudo que pueda borrar una URL entera; el límite de la API se respeta en la fase de construcción del contexto.

**Implementación:** En `_build_step_params`, al llamar a `_build_context_from_steps` para un paso delegate_* con varias claves, se pasa `max_ctx = min(scratchpad["max_context_chars"], cap_delegate)` cuando `delegate_max_context_chars` está definido.

---

### 13.2 Tolerancia a fallos parciales (resiliencia del DAG)

**Riesgo:** En una oleada de 3 hilos (3 URLs), si uno falla (403, timeout, Reddit bloqueado), un comportamiento fail-fast aborta todo y las URLs 1 y 3 tampoco se aprovechan.

**Decisión:** Se introduce una **política configurable**:

- **dag_partial_failure_tolerant = false** (por defecto): Comportamiento **fail-fast**: al fallar un paso de la oleada, se escribe el mensaje de error en `step_results[sid]` y se devuelve de inmediato; el plan se aborta.
- **dag_partial_failure_tolerant = true**: **Fallo parcial tolerado**: al fallar un paso, se escribe en `step_results[sid]` el marcador `"(Fuente no disponible)"` y **no** se hace `return`; se siguen recogiendo el resto de futuros. El nodo agregador (siguiente oleada) recibe solo las salidas exitosas (y las cadenas de fallo como texto), pudiendo generar respuesta a partir de las fuentes disponibles.

**Implementación:** En `plan_executor.py`, en el bucle que procesa los `futures` de una oleada, si `fut.result()` lanza: si `scratchpad["dag_partial_failure_tolerant"]` es true, se asigna `step_results[sid] = "(Fuente no disponible)"` y se continúa; si no, se asigna el mensaje de error y se hace `return step_results[sid]`. Configuración en **Config/planner.json**: `dag_partial_failure_tolerant`.

---

### 13.3 Contaminación cruzada en el prompt (separadores)

**Riesgo:** Con varias fuentes concatenadas solo con `\n\n---\n\n`, el LLM puede mezclar entidades de un texto con las de otro (“fugas de atención”).

**Decisión:** Se añade una opción para **delimitadores explícitos por fuente**:

- **scratchpad_use_source_tags = false** (por defecto): Se mantiene el separador estándar `\n\n---\n\n` entre fragmentos (comportamiento actual).
- **scratchpad_use_source_tags = true**: Al construir el contexto desde **varias** fuentes para un paso **delegate_lucifer** o **delegate_eva**, cada fragmento se envuelve en etiquetas XML: `<source id="step_id">...</source>`, donde `step_id` es la clave del paso (ej. `"0"`, `"0_url_1"`). Así el modelo recibe barreras claras entre fuentes y puede referenciarlas por `id` si se le pide.

**Implementación:** En `_build_context_from_steps` se añade el parámetro **use_source_tags**. Cuando es true y hay más de una fuente, cada fragmento (tras el truncamiento proporcional) se emite como `\n\n<source id="key">fragmento</source>`. En `_build_step_params` se activa cuando `scratchpad["scratchpad_use_source_tags"]` es true, el paso es delegate_* y hay más de una clave en el contexto. Configuración en **Config/planner.json**: `scratchpad_use_source_tags`.

---

## 14. Flujo local y multi-fuente: metadatos, persistencia y disparador del fan-out

Tres pruebas de estrés sobre memoria local limpia, delegación a agentes y fan-out.

### 14.1 Riqueza de metadatos en las etiquetas XML

**Pregunta:** ¿Se inyecta la URL original o el dominio en la etiqueta `<source>` para que Lucifer pueda referenciar fuentes de forma natural?

**Decisión e implementación:**

- **LoreExtractorTool** devuelve en su resultado **`url`** y **`domain`** (cuando aplica: Reddit = url + domain del netloc; MediaWiki = URL canónica de la página + netloc del wiki_base). El PlanExecutor no conocía antes la URL; ahora la obtiene del resultado de la tool.
- El **PlanExecutor** mantiene **step_metadata: Dict[sid, {url?, domain?}]**, rellenado al recoger el resultado de cada paso (single-step u oleada). **LoreExtractorTool** incluye en su `return` los campos `url` y `domain`; otras tools que los devuelvan se beneficiarán igual.
- **`_build_context_from_steps`** recibe **step_metadata** opcional. Cuando **use_source_tags** es true, cada fragmento se envuelve en `<source id="..." url="..." domain="...">` si step_metadata aporta `url` o `domain` para esa clave; los valores se escapan para atributos XML (`_xml_escape_attr`).

Así Lucifer recibe, por ejemplo, `<source id="0" url="https://reddit.com/r/..." domain="reddit.com">...</source>` y puede referenciar la fuente de forma natural.

---

### 14.2 Protección de la memoria local ante fallos parciales

**Pregunta:** ¿Existe riesgo de que el string "(Fuente no disponible)" (o el de timeout) se persista en ChromaDB/JSONL?

**Riesgo:** Si el paso siguiente a la oleada es **store_semantic_fact** y su contexto se construye con `context_from_steps` incluyendo los step_ids de la oleada, el contexto concatenado podría contener "(Fuente no disponible)" o "(Paso cancelado por timeout de oleada)" y ese texto se guardaría en la memoria local.

**Decisión e implementación:**

- Se introduce el parámetro **skip_unavailable_sources** en **`_build_context_from_steps`**. Cuando es **True**, se **excluyen** del contexto las claves cuyo valor es exactamente **"(Fuente no disponible)"** o empieza por **"(Paso cancelado"** (timeout).
- **Solo se activa** cuando el paso que consume el contexto es **store_semantic_fact**: al construir sus `params`, se llama a `_build_context_from_steps(..., skip_unavailable_sources=True)`. Así el texto que se persiste en ChromaDB/JSONL **nunca** incluye esos placeholders; solo entran las salidas exitosas.
- Para **delegate_lucifer** (y otros delegate_*) **no** se activa skip: el agregador sigue recibiendo los placeholders en el scratchpad efímero, de modo que el modelo puede decir que una fuente no estuvo disponible.

Constante **`_PLACEHOLDER_UNAVAILABLE`** y **`_PLACEHOLDER_TIMEOUT`** en `plan_executor.py` para unificar los textos y el filtrado.

---

### 14.3 Disparador del fan-out (regex) en el Planner

**Pregunta:** ¿Está ya activada **`_extract_urls_from_message`** para generar dinámicamente el subgrafo de extracción ante múltiples enlaces?

**Estado anterior:** La función existía pero **no** se usaba al resolver el intent; el sistema seguía con una URL por comando (un solo paso `lore_extractor` con el mensaje completo).

**Decisión e implementación:**

- **Activado** en **`_resolve_intent_from_config`** para el intent **lore_extractor**:
  - Se llama a **`_extract_urls_from_message(text)`**.
  - Se lee **max_urls_per_plan** de **Config/planner.json** (por defecto 5; 0 = desactivar fan-out).
  - Si **max_urls_per_plan > 0** y hay **2 o más URLs**, se generan **N pasos** `lore_extractor` (uno por URL, con `params={"message": url, "store": True}`), con **step_id** `"0"`, `"1"`, … y **depends_on=[]**, y un paso final **delegate_lucifer** con **context_from_steps** = lista de esos step_ids y **depends_on** = misma lista (agregador). Las URLs se limitan a **min(len(urls), max_urls_per_plan)**.
  - Si hay 0 o 1 URL, o max_urls_per_plan es 0, se mantiene el comportamiento anterior: un solo paso `lore_extractor` con `params={"message": text, "store": True}`.

Así, un solo mensaje con varias URLs dispara la oleada de extracciones en paralelo (PlanExecutor) y el agregador sintetiza con Lucifer; ya no es obligatorio enviar una URL por comando.

---

*Documento de orquestación y estructuración 4.0. Coherente con HORIZONTE_LILITH_4.0.md y CONSOLIDACION_CONOCIMIENTO.md.*
