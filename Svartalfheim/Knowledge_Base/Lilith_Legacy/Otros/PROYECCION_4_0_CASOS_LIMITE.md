# Proyección 4.0 — Casos límite y decisiones de diseño

Documento de investigación para la refactorización hacia 4.0: definición de casos límite en scratchpad (DAG), recuperación vectorial, QualityFilter y memoria de hilo. Basado en el diagnóstico del Deep Dive (truncamiento vectorial, ejecutor lineal, falsos positivos, saturación).

---

## 1. Límites de contexto en el scratchpad (DAG)

**Problema:** Con `step_results: Dict[str, str]` y `context_from_steps: ["step_1", "step_2"]`, concatenar salidas masivas (minería web + análisis de Lucifer) puede desbordar la ventana de contexto del LLM en el Paso 3.

**Opciones consideradas:**

| Enfoque | Pros | Contras |
|--------|------|--------|
| **Resumidor intermedio en PlanExecutor** | Control centralizado del tamaño; un solo punto de política (max_chars, truncar vs. resumir). | Añade latencia (llamada a LLM o extractor) y acopla el ejecutor a un servicio de resumen. |
| **Agentes estrictamente concisos** | Sin cambios en PlanExecutor; responsabilidad en cada agente. | Difícil de imponer; agentes externos (Lucifer, Eva) no controlamos el tamaño; planes existentes pueden seguir devolviendo bloques largos. |
| **Híbrido: tope + resumen opcional** | Acotar siempre (truncar o concatenar hasta N chars); si el plan declara `summarize_context: true` para un paso, el ejecutor invoca un paso de resumen antes. | Requiere convención en la definición del Step (metadatos) y un “agente resumidor” o tool. |

**Decisión recomendada:**

1. **Tope duro en el PlanExecutor (4.0 mínimo viable):** Al construir `params["context"]` desde `context_from_steps`, concatenar las salidas con un separador pero **truncar el resultado total** a un `max_context_chars` (p. ej. 8000–12000 caracteres) configurable en `Config/planner.json`. Si se excede, truncar por paso de forma proporcional o “últimos N caracteres por step” para no perder solo el último. Así se evita el desborde sin añadir latencia.
2. **Resumidor opcional (4.1):** Añadir en la definición del Step un flag `summarize_if_over_chars: 6000`. Si la concatenación supera ese umbral, el PlanExecutor inserta un “paso fantasma” que llama a una tool/agente de resumen (ej. `summarize_for_context`) y usa su salida como contexto del paso que lo requiere. El resumidor puede ser un delegate a un LLM con prompt “Resume en menos de 2000 caracteres preservando hechos clave”.
3. **Convención de agentes:** Documentar que los agentes internos (WebScraper, ContentCleaner, DataStructurer) deben devolver resúmenes o trozos acotados cuando su salida va a ser reutilizada como contexto de otro paso; para agentes externos (Eva, Adán, Lucifer) el tope en el ejecutor es la defensa principal.

**Config sugerida (ejemplo):**

```json
{
  "scratchpad_max_context_chars": 10000,
  "scratchpad_summarize_if_over_chars": 0,
  "scratchpad_truncation": "tail_per_step"
}
```

- `scratchpad_truncation`: `"tail_per_step"` (recortar por el final por paso) o `"global_tail"` (un solo bloque al final).

---

## 2. Inanición en la recuperación vectorial (Retrieval Starvation)

**Problema:** Con chunking (400–500 caracteres, `ts_chunk_i`), si `vector_facts_k = 5` y un solo artículo largo genera 10 chunks muy similares a la query, ChromaDB puede devolver 5 chunks del mismo documento. Se pierde diversidad semántica (otros documentos no aparecen).

**Opciones consideradas:**

| Enfoque | Pros | Contras |
|--------|------|--------|
| **Maximum Marginal Relevance (MMR)** | Bien estudiado; balance explícito relevancia vs. diversidad; no requiere metadatos. | Hay que implementarlo (score = λ * sim(q,d) - (1-λ) * max sim(d,d_selected)); puede ser costoso si k o el candidature set crece. |
| **Agrupar por source_id y tomar 1 por fuente** | Garantiza diversidad por documento; simple de explicar. | Puede dejar fuera el mejor chunk de un documento muy relevante; requiere que ChromaDB (o nuestra capa) devuelva/soporte metadata `source_id`. |
| **Híbrido: recuperar más, luego re-rank/diversificar** | Recuperar 2k o 3k candidatos; aplicar MMR o “1 chunk por source_id hasta llenar k slots”. | Más control; algo más de coste en embedding/cálculo. |

**Decisión recomendada:**

1. **Fase chunking inicial (4.0):** Al guardar chunks, almacenar en metadata de ChromaDB (o en el id) el `source_id` (ej. `ts` del hecho padre o hash del documento). En `search_facts`, pedir a ChromaDB **más resultados** de los necesarios (p. ej. `k_candidates = min(3 * k, 50)` con k = vector_facts_k).
2. **Post-procesado de diversidad:** Implementar una función `diversify_results(results, k, strategy="one_per_source")`:
   - **one_per_source:** Agrupar por `source_id`; ordenar grupos por score (mejor chunk del grupo); tomar el mejor chunk de cada grupo hasta completar k; si sobran slots, rellenar con los siguientes mejores chunks sin restricción. Así se garantiza al menos variedad por documento.
3. **Opcional (4.1) MMR:** Si se observa que “uno por fuente” deja respuestas pobres (p. ej. muchos documentos cortos), añadir MMR como alternativa configurable en `memory.json`: `vector_diversity_strategy: "one_per_source" | "mmr"`, con `mmr_lambda` (0.7 = más relevancia, 0.3 = más diversidad).

**Config sugerida (ejemplo):**

```json
{
  "vector_facts_k": 5,
  "vector_candidates_multiplier": 3,
  "vector_diversity_strategy": "one_per_source",
  "vector_mmr_lambda": 0.6
}
```

---

## 3. Bypass determinista en el QualityFilter (código y logs)

**Problema:** La fórmula heurística (0.4 * length_score + 0.6 * density) produce falsos positivos en código fuente y logs (bloquean contenido técnico valioso). Se desea evitar llamadas a LLM (latencia).

**Decisión:** Implementar un **pre-filtro por expresiones regulares** que detecte contenido “técnico por formato” y le asigne `quality_score = 1.0` sin pasar por el cálculo de densidad por stopwords.

**Reglas de bypass (regex):**

| Patrón | Descripción | Ejemplo |
|--------|-------------|--------|
| Bloques Markdown de código | Tres backticks en una línea, contenido hasta cierre | `\`\`\`python\n...\n\`\`\`` |
| Líneas que parecen logs con timestamp ISO | Fecha/hora ISO al inicio de línea o entre corchetes | `2024-01-15T12:00:00`, `[2024-01-15 12:00:00]` |
| Líneas de nivel de log estándar | `[INFO]`, `[DEBUG]`, `[ERROR]`, etc. | `[INFO] ...` |
| Bloques de código típicos (indentación + keywords) | Múltiples líneas que empiezan con espacios/tabs y contienen `def`, `class`, `return`, `{`, `}` | Heurístico: ≥2 líneas con indent y keyword |

**Comportamiento:**

- Si el texto **cumple** alguna regla de bypass (p. ej. contiene un bloque ``` o varias líneas con timestamp ISO / nivel de log), se considera “contenido técnico” y se devuelve **sin** evaluar densidad: `quality_score = 1.0`, texto pasado al siguiente paso con prefijo `[Calidad validada: 1.0 | bypass: código/log detectado]`.
- Configuración en `Config/quality_filter.json`: `bypass_deterministic: true` (activar), opcionalmente `bypass_markdown_code: true`, `bypass_log_patterns: true` para activar/desactivar cada familia de reglas.

Implementación: ver `QualityFilterAgent` y función `_bypass_deterministic(text, config)` en `Backend/core/quality_filter_agent.py`.

---

## 4. Saturación de la memoria de hilo

**Pregunta:** ¿El archivo de memoria de hilo crece indefinidamente? ¿Existe poda o límite al leer?

**Respuesta (código actual):** **Sí existe control.** No hay saturación indefinida.

- **En escritura (`append`):** `Backend/core/discord_thread_memory.py` mantiene solo los últimos **max_exchanges** intercambios (par user + assistant). Por defecto `MAX_EXCHANGES = 30` en el módulo; la llamada desde `discord_api.py` usa el mismo valor. Tras cada append, se hace `data["messages"] = messages[-max_exchanges:]`, por lo que el archivo **nunca** guarda más de 30 intercambios (60 mensajes).
- **Config:** `Config/memory.json` define `thread_memory_max_exchanges: 30` y `thread_memory_max_chars: 2500`. El valor de `max_exchanges` usado en `append` viene del módulo (30); en **lectura**, `_thread_memory_block` usa `cfg["max_exchanges"]` desde config (por defecto 15 en la config actual), es decir se cargan solo los **últimos 15 intercambios** para inyectar en el prompt.
- **Límite de caracteres al inyectar:** `format_thread_memory_for_prompt(messages, max_chars=cfg["max_chars"])` trunca el texto formateado a **2500 caracteres** (configurable). Si el bloque supera ese tamaño, se devuelve `"… (resumen)\n" + text[-max_chars:]` (solo el final).

**Resumen:**

| Capa | Límite | Dónde |
|------|--------|--------|
| Persistencia en disco | Máx. 30 intercambios (60 mensajes) | `discord_thread_memory.append()` → `messages[-max_exchanges:]` |
| Carga para el prompt | Últimos 15 intercambios (desde config) | `load(..., max_exchanges=cfg["max_exchanges"])` |
| Tamaño inyectado en system prompt | 2500 caracteres | `format_thread_memory_for_prompt(..., max_chars=cfg["max_chars"])` |

**Recomendación 4.0:** Unificar que el `max_exchanges` de **append** se lea también de `memory.json` (hoy el módulo usa 30 fijo), para que todo sea configurable desde un solo sitio. Opcional: añadir `thread_memory_max_exchanges_append` si se quisiera guardar más en disco (ej. 50) pero seguir cargando solo 15 para el prompt (más historia disponible para futuras extensiones).

---

## Referencias

- **Lógica exacta de implementación:** `Docs/DEEP_DIVE_IMPLEMENTACION_4_0.md` (algoritmos de truncamiento proporcional DAG, chunking con overlap, generación de source_id y diversidad en búsqueda).

*Documento de proyección 4.0. Actualizar cuando se implementen scratchpad, chunking + diversidad y ajustes de thread memory.*
