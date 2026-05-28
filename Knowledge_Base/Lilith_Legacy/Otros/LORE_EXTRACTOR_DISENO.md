# LoreExtractorTool (Lore-Seeker) — Decisiones de diseño

Herramienta para extraer contenido de APIs de wikis (MediaWiki/Fandom) y Reddit (.json), sin pasar por ContentCleaner. Respuestas a las preguntas de implementación del Deep Dive.

---

## 1. Destino de los datos extraídos

**Pregunta:** ¿Enviar directamente a `SemanticMemory.add_fact(text, source_id)` o pasar primero por Lucifer para resumir/extraer puntos clave?

**Decisión:** **Directo a memoria** por defecto.

- El contenido que devuelven MediaWiki (`explaintext=1`) y Reddit (JSON) ya viene en **texto plano**, sin HTML ni menús. No hace falta ContentCleaner.
- El flujo actual de memoria (chunking + `source_id` + diversidad `one_per_source`) ya maneja textos largos y evita saturar el prompt.
- Pasar por Lucifer añadiría latencia y coste; es útil cuando el usuario pide explícitamente un **resumen** o "extrae solo los puntos clave". Eso se puede modelar como un **plan en dos pasos**: `[lore_extractor con store=False] → [delegate_lucifer] → [store_semantic_fact]` cuando en el futuro se añada un intent "extrae y resume el lore de...".

**Implementación:** La tool tiene `store=True` por defecto y llama a `MemoryManager.add_fact(text, source_id=source_id)` tras extraer. Parámetro opcional `store=False` devuelve solo el texto para que un plan futuro pueda pasarlo a Lucifer y luego a `store_semantic_fact`.

---

## 2. Manejo de metadatos (Reddit: upvotes)

**Pregunta:** ¿Guardar la puntuación (upvotes) del comentario como parte del texto indexado para dar más peso, o solo texto puro?

**Decisión:** **Solo texto puro** en el hecho guardado.

- La densidad de información se mantiene alta; el modelo y la búsqueda semántica trabajan sobre contenido, no sobre números.
- Los upvotes (y autor, subreddit, etc.) se devuelven en la **respuesta** de la tool (`metadata`) para que el usuario o un futuro ranking los vea; no se incrustan en el cuerpo del hecho.
- Si más adelante se quiere priorizar por score en la **recuperación** (p. ej. ordenar por upvotes al elegir qué comentarios incluir), se puede guardar score en metadatos en JSONL/ChromaDB y usar ese campo en la capa de búsqueda, sin contaminar el texto indexado.

**Implementación:** En modo Reddit, el cuerpo guardado es: título del post + `selftext` + cuerpos de comentarios de nivel superior, sin líneas tipo `[score=42]`. `metadata` en el resultado incluye `post_score`, `post_author`, `subreddit` para referencia o display.

---

## 3. Modos de operación

| Modo        | Fuente              | Mecanismo                                                                 | Uso principal                          |
|------------|---------------------|---------------------------------------------------------------------------|----------------------------------------|
| **mediawiki** | Fandom / MediaWiki  | GET `api.php?action=query&prop=extracts&explaintext=1&titles=...&format=json` | Mitología, worldbuilding, wikis de juegos |
| **reddit**   | Reddit              | GET URL del hilo + `.json`; parsear post y comentarios de nivel superior  | Diseño de juegos, experiencias, debates |

La tool detecta automáticamente modo y parámetros si el usuario incluye una **URL** en el mensaje (Reddit o Fandom); si no, debe indicar `mode`, y para MediaWiki `wiki_base` y `title`, o para Reddit `url`.

---

## 4. Integración

- **Registro:** `lore_extractor` en `ToolRegistryV3` (lazy).
- **Intent:** `extract_lore` en `Config/intent_patterns.json` con triggers ("extrae el lore de", "extrae de la wiki", "extrae de reddit", etc.); el Planner devuelve un paso `lore_extractor` con `message` = texto del usuario.
- **Almacenamiento:** `MemoryManager.add_fact(text, source_id=...)` y `StoreSemanticFactTool` aceptan `source_id` opcional; la cadena SemanticStore → SemanticMemory ya soporta `source_id` para chunking y diversidad.

---

*Documento de diseño Lore-Seeker. Coherente con CALIBRACION_MINERIA_Y_FUENTES.md y VISION_MINERIA_REFINERIA_WEB.md.*
