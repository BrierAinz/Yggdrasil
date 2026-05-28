# Deep Dive — Lógica exacta de implementación 4.0

Detalles de bajo nivel para el scratchpad (DAG) con truncamiento, chunking vectorial con solapamiento y generación/rastreo de `source_id`. Referencia para implementación a prueba de balas.

---

## 1. Gestión de memoria del DAG y truncamiento (tail_per_step)

### Pregunta

Con límite `scratchpad_max_context_chars = 10_000` y un paso que requiere contexto de los Pasos 1 y 2, ¿repartimos 5_000/5_000 o usamos un reparto dinámico?

### Decisión: reparto proporcional por longitud

**No** se asigna estrictamente la mitad a cada uno. Se asigna a cada paso una **cuota proporcional** a su longitud original, de modo que:

- Un paso corto no “desperdicia” parte del presupuesto.
- Un paso largo recibe más caracteres (se preserva más información donde hay más contenido).
- El total inyectado no supera `max_context_chars`.

### Algoritmo

1. **Entrada:** `step_results: Dict[str, str]` (claves = índice de paso `"0"`, `"1"`, …), `context_from_steps: List[str]` (ej. `["0", "1"]`), `max_context_chars: int`.

2. **Obtener textos y longitudes:**
   - `texts = [step_results[i] for i in context_from_steps if i in step_results]`
   - `lengths = [len(t) for t in texts]`
   - `total_len = sum(lengths)`

3. **Si `total_len <= max_context_chars`:** concatenar todos los textos con separador `\n\n---\n\n` y usar eso como contexto. Fin.

4. **Si `total_len > max_context_chars` (truncamiento proporcional):**
   - Para cada índice `j` en `context_from_steps` con resultado en `step_results`:
     - `quota_j = floor(max_context_chars * lengths[j] / total_len)`
     - Si `quota_j <= 0`: no incluir ese paso (o asignar 1 carácter mínimo; en la práctica se usa `max(1, quota_j)`).
   - Ajuste por redondeo: si `sum(quota_j) < max_context_chars`, repartir el sobrante en orden (p. ej. al paso más largo) hasta igualar o acercarse a `max_context_chars`.
   - Para cada paso: tomar **solo el final** del texto: `tail_j = texts[j][-quota_j:]`.
   - Concatenar `tail_0`, `tail_1`, … con el mismo separador.

5. **Separador:** `\n\n---\n\n` entre bloques para que el LLM distinga salidas de distintos pasos.

**Ejemplo:** Paso 1 = 2_000 chars, Paso 2 = 12_000 chars, `max_context_chars = 10_000`.  
`total_len = 14_000`. Cuota_1 = floor(10_000 * 2_000 / 14_000) = 1_428, Cuota_2 = floor(10_000 * 12_000 / 14_000) = 8_571. Suma = 9_999; se puede dar 1 carácter más al paso 2 (8_572). Resultado: últimos 1_428 chars del Paso 1 + últimos 8_572 del Paso 2.

### Configuración

- `Config/planner.json`: `scratchpad_max_context_chars` (default 10_000), `scratchpad_truncation: "tail_per_step"` o `"global_tail"`, y **`scratchpad_prefer`**: `"tail"` (por defecto), `"head"` o `"middle"`.
- **Boilerplate (menús, pies de página):** El ContentCleaner se ejecuta como **paso** del plan; su salida va a `step_results["1"]`. No se ejecuta “antes” de guardar en `step_results`. Por tanto, si un paso usa `context_from_steps: ["0"]`, recibe la salida **cruda** del WebScraper (con posible boilerplate al final). **Recomendación:** que los planes referencien el paso del **ContentCleaner** (p. ej. `["1"]`) cuando el flujo sea minería web. Si aun así se referencia salida con boilerplate al final, usar `scratchpad_prefer: "head"` o `"middle"` para tomar el inicio o el centro del texto en lugar del final.

---

## 2. Integridad del contexto en el chunking vectorial (overlap)

### Pregunta

¿Implementamos solapamiento (p. ej. 50 caracteres) entre chunks para no cortar el significado en la frontera?

### Decisión: sí, overlap fijo y preferencia por fronteras de oración

- **Tamaño de chunk:** 400–500 caracteres (p. ej. 450) para alinear con el límite del encoder (~256 tokens).
- **Overlap:** 50 caracteres entre chunks consecutivos.
- **Fronteras:** intentar cortar en límites “suaves” (final de oración o de párrafo) cuando sea posible, sin comprometer el tamaño objetivo.

### Algoritmo de chunking

1. **Entrada:** `text: str`, `chunk_size: int = 450`, `overlap: int = 50`, `prefer_sentence_boundary: bool = True`.

2. **Precondición:** `overlap < chunk_size` (p. ej. 50 < 450).

3. **Paso efectivo por chunk:** `step = chunk_size - overlap` (ej. 400 caracteres nuevos por chunk).

4. **Generación de chunks:**
   - `start = 0`
   - Mientras `start < len(text)`:
     - `candidate_end = min(start + chunk_size, len(text))`
     - Si `prefer_sentence_boundary` y no estamos al final del texto: buscar hacia atrás desde `candidate_end` el último `. `, `\n` o `! `, `? ` en `[start, candidate_end]`; si existe y no aleja el final más de 80 caracteres, usar ese como `end`; si no, `end = candidate_end`.
     - Chunk = `text[start:end].strip()`; si no está vacío, añadir a la lista.
     - `start = end - overlap` (siguiente ventana con 50 chars de solapamiento). Si `start >= len(text)`, salir.

5. **Salida:** lista de strings (chunks) que se indexan por separado en ChromaDB, todos con el mismo `source_id` (véase sección 3).

### Delimitador de respaldo (código/logs, Base64, JSON minificado)

Si en la ventana de 80 caracteres **no** aparece ningún divisor natural (`. `, `.\n`, `! `, `? `, `\n\n`), el algoritmo usa un **respaldo**: el último espacio o tab en esa ventana. Así se evita partir un token por la mitad en cadenas Base64, JSON minificado o matrices continuas. Si tampoco hay espacio/tab, se corta en `candidate_end` (corte rígido).

### Configuración

- `Config/memory.json`: `vector_chunk_threshold: 500` (por encima se aplica chunking), `vector_chunk_size: 450`, `vector_chunk_overlap: 50`. La preferencia por frontera de oración está fija en el código (`prefer_sentence_boundary: true`).

---

## 3. Generación y rastreo del source_id

### Pregunta

¿Cómo inyectamos `source_id`? ¿Cambiamos la firma de `add_fact` para exigir metadatos o generamos un hash del documento completo antes del chunking?

### Decisión: hash del documento + firma ampliada opcional

- **Origen único por “documento”:** Antes de chunking, se calcula un **identificador de documento** que comparten todos los chunks. Ese es el `source_id`.
- **Generación por defecto:** `source_id = SHA-256(texto_completo_normalizado).hexdigest()[:16]` (16 caracteres basta para colisiones despreciables y mantiene IDs cortos). Se usa el texto **antes** de chunking para que todos los fragmentos del mismo documento tengan el mismo `source_id`.
- **Firma de la API:**
  - `add_fact(text, fact_id=None, source_id=None)`:
    - Si `source_id` viene dado (p. ej. desde el pipeline de minería), se usa ese.
    - Si no y el texto es largo (p. ej. `len(text) > chunk_size`), se hace chunking y se genera `source_id = hash(full_text)`; todos los chunks se almacenan con ese `source_id`.
    - Si el texto es corto y no hay `source_id`, se usa `fact_id` o timestamp como hasta ahora; no es obligatorio guardar `source_id` para hechos cortos (retrocompatibilidad).
  - En el **vector store**: `add_fact(base_path, fact_id, fact_text, source_id=None)`. Si `source_id` está presente, se guarda en metadatos de ChromaDB (`metadatas=[{"source_id": source_id}]`) para poder aplicar `one_per_source` en la búsqueda.

### Flujo completo (texto largo, chunking)

1. Llega `add_fact(long_text)` o `add_fact(long_text, source_id=None)`.
2. `source_id = source_id or hashlib.sha256(long_text.strip().encode("utf-8")).hexdigest()[:16]`.
3. Chunking con overlap (algoritmo de la sección 2) → lista de chunks.
4. Para cada chunk `i`: `fact_id_i = f"{source_id}_chunk_{i}"`.
5. Persistencia:
   - JSONL: una línea por chunk con `ts`, `text` (chunk), `source_id`.
   - ChromaDB: `upsert(ids=[fact_id_i], documents=[chunk], embeddings=[...], metadatas=[{"source_id": source_id}])`.
6. En **búsqueda**: se pide a ChromaDB más candidatos (`k_candidates_multiplier * k` desde `memory.json`), se devuelven metadatos e `ids` y se aplica `_diversify_by_source` para rellenar hasta `k` resultados maximizando diversidad por `source_id`.

### Resolución de empates (mismo source_id, similitud casi idéntica)

Dentro de cada `source_id`, los chunks se ordenan por **(distance, chunk_index)**. Si dos chunks del mismo documento tienen distancia muy similar, se prefiere el de **índice menor** (p. ej. `chunk_0`), asumiendo que suele contener la introducción o el contexto principal del documento. El índice se obtiene de `fact_id` (formato `{source_id}_chunk_{i}`).

Configuración en `Config/memory.json`: `vector_facts_k`, `vector_candidates_multiplier`, `vector_diversity_strategy` (`one_per_source`), `vector_chunk_threshold`, `vector_chunk_size`, `vector_chunk_overlap`.

---

*Documento de implementación 4.0. Coherente con `PROYECCION_4_0_CASOS_LIMITE.md` y `DEEP_DIVE_ARQUITECTURA.md`.*
