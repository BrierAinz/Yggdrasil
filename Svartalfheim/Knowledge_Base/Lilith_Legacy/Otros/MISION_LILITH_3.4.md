# MISIÓN LILITH 3.4 — MEMORIA INTELIGENTE Y OBSERVABILIDAD

**Objetivo:** Búsqueda semántica (D.3), base de memoria híbrida, versionado unificado y observabilidad del sistema. Sentar las bases para un salto a 4.0.

**Base:** Misión 3.3 completada (intents JSON, C.2/C.3, Chain Tool, B.3 resúmenes, .bat arranque/cierre).

---

## BLOQUE 1 — BÚSQUEDA VECTORIAL (D.3)

| Tarea | Descripción | Esfuerzo | Criterio de éxito |
|-------|-------------|----------|-------------------|
| **D.3a Embeddings de hechos** | Convertir hechos recientes (`facts.jsonl`) en vectores y guardarlos (ChromaDB en disco o FAISS/sentence-transformers). Al pedir contexto, recuperar los K hechos más similares a la pregunta en lugar de los últimos N. | Alto | Preguntas como "¿qué dijiste sobre rendimiento?" devuelven hechos relevantes por similitud. |
| **D.3b Perfil fragmentado** | Opcional: fragmentos de perfil (nombre, proyectos, preferencias) también con embeddings para búsqueda unificada. | Medio | `search_semantic(query)` devuelve perfil + hechos por relevancia. |

**Tecnología sugerida:** `sentence-transformers` (modelo local, ej. `all-MiniLM-L6-v2`) + ChromaDB persistente en `Data/chroma_facts` o un índice FAISS. Sin dependencias externas de API para embeddings.

---

## BLOQUE 2 — MEMORIA HÍBRIDA (BASE)

| Tarea | Descripción | Esfuerzo | Criterio de éxito |
|-------|-------------|----------|-------------------|
| **H.1 Un solo punto de búsqueda** | `MemoryManager.search_context(query, limit)` que internamente consulta: (1) hechos por embeddings si D.3 está activo, (2) perfil estable, (3) últimos resúmenes de sesión. Devuelve un único bloque ordenado por relevancia para inyectar en el prompt. | Medio | El Planner/Orchestrator solo llama a `search_context`; la mezcla de fuentes es interna. |
| **H.2 Pesos configurables** | En `Config/memory.json`: `search_weights` (hechos, perfil, resúmenes) para ponderar cuánto de cada fuente se incluye. | Bajo | Comportamiento refinable sin tocar código. |

---

## BLOQUE 3 — VERSIONADO Y OBSERVABILIDAD (E.2, E.3)

| Tarea | Descripción | Esfuerzo | Criterio de éxito |
|-------|-------------|----------|-------------------|
| **E.2 Versionado unificado** | `Backend/version.py` (o `Core/version.py`) con `LILITH_VERSION = "3.4"`, `MEMORY_VERSION`, `PHASE`. Endpoint `GET /api/status` o `/api/version` que lo exponga; logs y docs referencian la misma versión. | Bajo | Una sola fuente de verdad para la versión. |
| **E.3 Observabilidad de memoria** | Cada decisión del Planner: registrar en `Data/memory_metrics.jsonl` (o extender `discord_audit`) qué fuente ganó (plan_learned, classifier, intent_patterns, fallback), opcionalmente cuántos hechos/patrones se consultaron. Sin impacto en rendimiento (escritura asíncrona o por lotes). | Medio | Trazabilidad para afinar config y debugging. |

---

## BLOQUE 4 — META-APRENDIZAJE (OPCIONAL PARA 3.4)

| Tarea | Descripción | Esfuerzo | Criterio de éxito |
|-------|-------------|----------|-------------------|
| **M.1 Sugerencias proactivas de patrones** | LearningEngine (o herramienta `suggest_patterns`): analizar últimos episodios exitosos, detectar secuencias repetidas (mensaje similar → mismo plan) y generar un informe o lista "Patrones candidatos: ... ¿Añadir a procedimental?". No aplicar automáticamente; el usuario decide. | Medio | Lilith pasa de ejecutora a consejera en la mejora de su propia memoria. |
| **M.2 Meta-informe de config** | Periódicamente (o bajo petición): informe "use_learned_plan se usó en X% de casos; max_facts actual K; sugerencia: ...". Guardar en `Data/meta_report.json` o mostrarlo en `/status`. Sin auto-aplicar cambios en `memory.json`. | Bajo | Base para una futura auto-configuración con validación humana. |

---

## ORDEN DE EJECUCIÓN RECOMENDADO (3.4)

1. **E.2** — Versionado unificado (rápido, orden en la casa).
2. **E.3** — Observabilidad de memoria (métricas de decisión del Planner).
3. **D.3a** — Embeddings + ChromaDB/FAISS para hechos; integrar en `get_context_for_prompt` o en `search_semantic`.
4. **H.1** — Punto de búsqueda unificado `search_context` (con o sin D.3 ya completo).
5. **H.2** — Pesos en config.
6. **D.3b** — Perfil fragmentado (opcional).
7. **M.1, M.2** — Según prioridad (sugerencias de patrones y meta-informe).

---

## DEPENDENCIAS OPCIONALES (D.3)

- `sentence-transformers` (modelo local).
- `chromadb` (persistencia vectorial) o `faiss-cpu` (índice en memoria/disco).
- Configuración en `Config/memory.json`: `use_vector_search: true`, `embedding_model`, `chroma_path`, etc. Si no están o fallan, degradación elegante a comportamiento actual (últimos N hechos).

---

## ESTADO DE IMPLEMENTACIÓN (Olas 1 y 2)

| Tarea | Estado | Notas |
|-------|--------|-------|
| **E.2** Versionado unificado | Hecho | `Backend/core/version.py` con `LILITH_VERSION = "3.4"`. Expuesto en `GET /api/status` y `GET /api/version`. |
| **E.3** Observabilidad del Planner | Hecho | `Backend/core/auditor/decision_auditor.py` escribe en `Core/Data/decision_audit.jsonl`. Planner registra `learned_plan`, `classifier`, `intent_patterns`, `fallback_lucifer`. |
| **D.3a** Embeddings de hechos | Hecho | `Backend/core/memory/semantic/vector_store.py`: ChromaDB + sentence-transformers. `add_fact` y `search_facts`. Integrado en `SemanticMemory.add_fact` y `get_context_for_prompt(query)`. Degradación si no hay `sentence-transformers`/`chromadb`. |
| **H.1 + H.2** Búsqueda unificada y pesos | Hecho | `MemoryManager.search_context(query)` combina perfil + hechos (vector si disponible) + resúmenes de sesión. Pesos en `Config/memory.json`: `weight_facts`, `weight_profile`, `weight_summaries`. Planner usa `search_context` en lugar de `search_semantic`. |

**Dependencias opcionales para D.3a:** `pip install sentence-transformers chromadb`

---

## REFERENCIAS

- `MISION_LILITH_3.3_OPTIMIZACION.md` — Estado 3.3.
- `REFINAMIENTO_MEMORIA_LILITH.md` — Detalle técnico de memoria.
- `HORIZONTE_LILITH_4.0.md` — Visión a largo plazo.
