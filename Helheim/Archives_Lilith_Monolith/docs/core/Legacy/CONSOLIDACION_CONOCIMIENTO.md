# Consolidación del conocimiento — Retención y recuperación

Puntos ciegos resueltos en la tubería de ingestión (add_fact + ChromaDB) para que la retención y la recuperación no tengan fugas.

---

## 1. Paginación y truncamiento (límites de MediaWiki)

**Problema:** El endpoint `prop=extracts&explaintext=1` trunca artículos muy largos; sin tokens de continuación solo se guardaba la introducción en artículos masivos.

**Solución implementada:**

- **Primario:** Uso de **action=parse&prop=text** para obtener el **artículo completo** en HTML; se hace strip de etiquetas y se devuelve texto plano. Así se evita el límite de `extracts` (p. ej. 1 200 caracteres en algunas instalaciones).
- **Fallback:** Si la API `parse` no está disponible o falla (p. ej. wiki sin extensión), se usa **prop=extracts** y se itera con los parámetros **continue** / **excontinue** de la respuesta para concatenar todos los fragmentos cuando la API devuelve paginación.

**Código:** `LoreExtractorTool._mediawiki_extract(..., full_page=True)` intenta primero `parse`; si hay texto, lo devuelve; si no, entra al bucle `query` + `continue` con `extracts`.

---

## 2. Taxonomía en el espacio vectorial (filtrado por metadatos)

**Problema:** Con D&D, game feel y mitología de Valhalla en la misma base, la búsqueda semántica puede mezclar contextos.

**Solución implementada:**

- **Campo opcional `topic`** en la cadena de almacenamiento: `add_fact(text, source_id=..., topic=...)` en MemoryManager, SemanticStore, SemanticMemory y vector_store. En ChromaDB se guarda en **metadatos** junto a `source_id`: `metadatas=[{"source_id": "...", "topic": "rol_lore"}]`.
- **Filtro en búsqueda:** `search_facts(..., topic=...)` pasa a ChromaDB un **where** cuando `topic` está definido: `where={"topic": "rol_lore"}`, de modo que solo se devuelven hechos de ese dominio.
- **Configuración global (opcional):** En `Config/memory.json`, **vector_topic_filter** permite acotar por defecto todas las búsquedas a un dominio (p. ej. `"vector_topic_filter": "rol_lore"`). Si está vacío o no existe, no se aplica filtro.
- **En la tool:** `LoreExtractorTool` y `StoreSemanticFactTool` aceptan parámetro opcional **topic** (ej. `rol_lore`, `gamedev`, `mitologia`) y lo propagan a `add_fact`.

**Valores de ejemplo para topic:** `rol_lore`, `rol_mecanicas`, `gamedev`, `mitologia`, `programacion`, etc. El Planner o el usuario pueden indicar el topic al guardar; en recuperación se usa el filtro cuando se desea acotar a un dominio.

---

## 3. Rate limiting y 429 en Reddit

**Problema:** Reddit limita las peticiones sin autenticar (pocas decenas por minuto); varias extracciones seguidas pueden devolver HTTP 429 y bloquear la herramienta.

**Solución implementada:**

- **Intervalo mínimo entre peticiones:** Variable global `_LAST_REDDIT_REQUEST` y constante `_REDDIT_MIN_GAP` (2 s). Antes de cada GET a Reddit se espera el tiempo restante hasta cumplir ese gap.
- **Reintentos con backoff en 429:** Función `_reddit_get()` que, ante **429 Too Many Requests**, espera `2^attempt` segundos (1, 2, 4 s) y reintenta hasta `max_retries` (3). El resto de errores también reintenta con la misma espera.
- **Uso:** `_reddit_extract()` deja de hacer `requests.get` directo y usa `_reddit_get()`, que centraliza el gap y el manejo de 429.

**Código:** `lore_extractor_tool._reddit_get`, `_REDDIT_MIN_GAP`, `_LAST_REDDIT_REQUEST`; en 429 se registra warning y se hace `time.sleep(wait)` antes de reintentar.

---

## 4. Casos extremos 4.0 (refuerzos)

### 4.1 Contaminación por tablas en MediaWiki (_strip_html)

**Riesgo:** Con `action=parse` el HTML incluye infoboxes, navboxes, TOC y tablas que, al colapsar a texto, generan ruido ("Fuerza 18 Destreza 14 HP 200...").

**Solución:** `_strip_html()` usa **BeautifulSoup** (si está disponible) para eliminar explícitamente antes de `get_text()`:
- Clases/selectores: `.infobox`, `.navbox`, `.toc`, `#toc`, `.wikitable`, `table.ambox`, `.reference`, `ol.references`, `sup.reference`, `.citation`, `.metadata`.
- Referencias numéricas `[1]`, `[2]` se eliminan por regex tras la extracción.
- Si BeautifulSoup no está, se usa el fallback por regex (sin aislamiento de bloques).

### 4.2 Ceguera vectorial por filtro estricto (zero-hit fallback)

**Riesgo:** Con `vector_topic_filter` activo, una pregunta híbrida (ej. "¿Cómo programo el combate por turnos basado en estas reglas de rol?") puede devolver 0 resultados si solo se buscan hechos con topic `rol_lore` y la parte técnica está en `gamedev`.

**Solución:** En `SemanticMemory._get_facts_for_query()`, cuando hay **topic_filter** y la búsqueda devuelve **0 resultados**, se hace un **segundo intento sin filtro** (`topic=None`). Así las consultas híbridas pueden recuperar hechos de otros dominios cuando el filtrado por topic no devuelve nada.

### 4.3 Condiciones de carrera en el rate limiting (Reddit)

**Riesgo:** Con un DAG o ejecución paralela (varios pasos extrayendo de Reddit a la vez), la variable global de último request y el gap podrían sufrir race conditions y provocar ráfagas de peticiones y 429.

**Solución:** Se usa un **threading.Lock** (`_REDDIT_LOCK`). Toda la sección "calcular gap → sleep si aplica → actualizar _LAST_REDDIT_REQUEST" se ejecuta dentro de `with _REDDIT_LOCK`, de modo que solo un hilo puede pasar por ese tramo a la vez. La petición HTTP se hace fuera del lock para no bloquear a otros hilos más de lo necesario; el gap queda garantizado entre dos peticiones consecutivas aunque haya paralelismo.

---

## Referencias

- MediaWiki: Parse API (artículo completo), Query API + continue (extracts).
- ChromaDB: metadatos por documento, parámetro `where` en `query()`.
- Reddit: User-Agent obligatorio, rate limit sin auth, 429 con retry-after implícito.

---

*Documento de consolidación del conocimiento. Coherente con LORE_EXTRACTOR_DISENO.md y DEEP_DIVE_IMPLEMENTACION_4_0.md.*
