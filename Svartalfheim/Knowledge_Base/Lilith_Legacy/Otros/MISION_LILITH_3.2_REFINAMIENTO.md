# MISIÓN LILITH 3.2 — REFINAMIENTO DE MEMORIA Y SISTEMA

**Objetivo:** Mejorar y refinar la memoria de Lilith (tri-capa), la configuración centralizada y la observabilidad, sin romper lo ya validado en 3.0/3.1.

**Base:** Misión 3.0 completada (`MISION_LILITH_3.0_COMPLETO.md`), Panteón V3.1, confirmaciones por DM (✅/❌), persistencia y auditoría en JSON/JSONL.

---

## ESQUEMA COMPLETO DE LA MISIÓN

```
┌─────────────────────────────────────────────────────────────────────────────┐
│  MISIÓN 3.2 — REFINAMIENTO                                                   │
├─────────────────────────────────────────────────────────────────────────────┤
│  BLOQUE A — YA IMPLEMENTADO (premisas de la misión)                          │
│  BLOQUE B — MEMORIA EPISÓDICA (retención, filtrado, resúmenes)              │
│  BLOQUE C — MEMORIA PROCEDIMENTAL (refuerzo, vencimiento, intención)         │
│  BLOQUE D — MEMORIA SEMÁNTICA (hechos, perfil vs hechos, opcional embed)    │
│  BLOQUE E — INTEGRACIÓN Y OBSERVABILIDAD                                     │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## BLOQUE A — PREMISAS (YA HECHO)

Esto queda como base de la misión; no hay tareas pendientes aquí.

| Ítem | Descripción | Ubicación |
|------|-------------|-----------|
| **A.1** | Persistencia de confirmaciones en disco | `Core/Data/discord_pending_confirmations.json`; carga/guardado en `discord_api.py`. Tras reinicio de API, los pendientes siguen hasta TTL o resolución. |
| **A.2** | Config de canales en JSON | `Discord/data/allowed_channels.json`. Prioridad sobre `.env` en `get_allowed_channel_ids()`. |
| **A.3** | Comandos `/lilith allow add | remove | list` | Solo owner; gestionan la whitelist de canales sin tocar `.env`. |
| **A.4** | Auditoría de confirmaciones | `Core/Data/discord_audit.jsonl`. Eventos: `confirm_requested`, `confirm_confirmed`, `confirm_cancelled`, `confirm_error`. |
| **A.5** | Documento de refinamiento de memoria | `Core/Docs/REFINAMIENTO_MEMORIA_LILITH.md` (referencia técnica). |

---

## BLOQUE B — MEMORIA EPISÓDICA

**Objetivo:** Que la episódica no crezca sin control y que el aprendizaje use solo episodios útiles.

| Fase | Tarea | Descripción | Criterio de éxito |
|------|--------|-------------|--------------------|
| **B.1** | Política de retención | En `EpisodicStore`: límite por cantidad (ej. últimos N episodios) o por fecha (ej. borrar/archivar episodios > X días). Configurable vía constante o `Config/memory.json`. | No crecimiento ilimitado; LearningEngine sigue teniendo ventana reciente. |
| **B.2** | Filtrado por outcome | En `LearningEngine.analyze_and_suggest_patterns` (y donde se lean episodios para aprender): usar solo episodios con `outcome == "success"` (y opcionalmente excluir los marcados como fallo). | Los patrones sugeridos se basan en interacciones exitosas. |
| **B.3** | Resúmenes por sesión (opcional) | Pipeline post-episódico: cada N interacciones o al “cierre de sesión”, generar un resumen (vía Lucifer o plantilla) y guardarlo en un store de resúmenes (ej. `Data/memory/session_summaries.jsonl`). | Memoria semántica o un “contexto reciente” puede alimentarse de resúmenes en lugar de todos los logs. |

**Archivos a tocar:** `Backend/core/memory/episodic/store.py`, `Backend/core/learning/learning_engine.py`, opcional nuevo módulo `core/memory/summaries` o uso de `Backend/memory/session_summarizer.py` si existe.

---

## BLOQUE C — MEMORIA PROCEDIMENTAL

**Objetivo:** Que los patrones aprendidos se refuercen o deprecen según uso y éxito.

| Fase | Tarea | Descripción | Criterio de éxito |
|------|--------|-------------|--------------------|
| **C.1** | Refuerzo por éxito | Cuando el Planner usó un plan procedimental y el resultado fue `outcome == "success"`, actualizar ese patrón (ej. incrementar peso, última_fecha_uso). Si el plan se usó y falló, no reforzar (o bajar prioridad). | Patrones que funcionan ganan peso; los que fallan no se refuerzan. |
| **C.2** | Vencimiento o validez | En `ProceduralStore` (o modelo de datos): campo opcional `last_used`, `use_count` o `valid_until`. En `get_plan_for_message` (o equivalente), no devolver patrones “vencidos” (ej. no usados en X días) o darles menor prioridad. | Patrones obsoletos dejan de usarse sin borrarlos de golpe. |
| **C.3** | Agrupación por intención | Etiquetar patrones con intención (ej. `edit_file`, `analyze_code`, `chitchat`). Planner o LearningEngine eligen por intención + similitud de mensaje. Permite combinar con salida del `LocalIntentClassifier`. | Mejor matching mensaje → plan aprendido. |

**Archivos a tocar:** `Backend/core/memory/procedural/store.py`, modelos en `procedural/`, `Backend/core/learning/learning_engine.py`, `Backend/core/planner.py`.

---

## BLOQUE D — MEMORIA SEMÁNTICA

**Objetivo:** Contexto más rico y actualizable sin llenar el prompt con todo el historial.

| Fase | Tarea | Descripción | Criterio de éxito |
|------|--------|-------------|--------------------|
| **D.1** | Separar perfil fijo y hechos recientes | En `SemanticStore` o en el consumidor (`get_context_for_prompt`): dos fuentes — (1) perfil estable (nombre, proyectos, rol) y (2) hechos/recordatorios (JSON o JSONL con timestamp). Límite de hechos recientes (ej. últimos 50) para no saturar. | Perfil estable siempre; hechos recientes rotan. |
| **D.2** | Actualización automática de hechos | Módulo de extracción: tras ciertas respuestas (o cuando el usuario dice “guarda que…”, “recuerda que…”), extraer hecho y escribirlo en el store de hechos (con fecha). Opcional: usar Lucifer o reglas para extracción. | La memoria semántica se enriquece con el uso. |
| **D.3** | Búsqueda vectorial (embeddings) — opcional | Sustituir o complementar el “bloque único” de contexto: fragmentos (perfil + hechos) con embeddings; ante cada mensaje, recuperar los K más similares. Requiere modelo de embeddings (local o API) y store vectorial (ChromaDB, FAISS, o simple en disco). | Escalabilidad y relevancia del contexto inyectado. |

**Archivos a tocar:** `Backend/core/memory/semantic/store.py`, `Backend/memory/semantic_memory.py`, nuevo store de hechos (ej. `Data/memory/facts.jsonl`), opcional `core/memory/embeddings.py` y store vectorial.

---

## BLOQUE E — INTEGRACIÓN Y OBSERVABILIDAD

**Objetivo:** Unificar criterios y poder medir el comportamiento de la memoria y del Planner.

| Fase | Tarea | Descripción | Criterio de éxito |
|------|--------|-------------|--------------------|
| **E.1** | Ponderar fuentes en el Planner | Config (ej. `Config/memory.json` o constantes): pesos o prioridades entre (1) plan aprendido, (2) clasificador local, (3) reglas fijas. Planner combina o elige según esas prioridades y umbrales. | Comportamiento refinable sin cambiar código. |
| **E.2** | Versionado unificado (opcional) | `Backend/version.py` o similar: `LILITH_VERSION = "3.2"`, `MEMORY_VERSION`, `PHASE`. Módulos y docs referencian la misma versión. | Coherencia de versión en logs y documentación. |
| **E.3** | Observabilidad de memoria | Logs o métricas (ej. en `discord_audit.jsonl` o nuevo `memory_metrics.jsonl`): cuando se usa plan aprendido vs regla vs clasificador; cuántos episodios se consultaron; cuántos hechos inyectados. Opcional: dashboard o script que resuma. | Trazabilidad de decisiones de memoria. |

**Archivos a tocar:** `Backend/core/planner.py`, `Backend/core/config_schema.py` o nuevo `Config/memory.json`, opcional `Backend/version.py`, módulo de métricas o extensión de auditoría.

---

## ORDEN DE BATALLA SUGERIDO

Enfoque en **victorias rápidas** y bases sólidas antes de optimización avanzada.

| Fase | Nombre | Tareas | Esfuerzo | Impacto |
|------|--------|--------|----------|---------|
| **Fase 1** | **Higiene y fundamentos** | **B.1** Retención episódica (límite por fecha) · **B.2** Filtrado por outcome | Bajo | Alto — evita crecimiento infinito y mejora de inmediato la calidad de los patrones generados. |
| **Fase 2** | **Inteligencia adaptativa** | **C.1** Refuerzo procedimental · **D.1** Perfil vs hechos | Medio | Transformador — memoria procedimental "viva" que se auto-mejora; semántica separada en estable vs efímero. |
| **Fase 3** | **Automatización y control** | **D.2** Actualización automática de hechos · **E.1** Ponderación de fuentes (`Config/memory.json`) | Medio | Estratégico — Lilith aprende hechos nuevos de la conversación; control del Planner en tiempo real sin tocar código. |
| **Fase 4** | **Optimización avanzada** (opcional) | C.2, C.3, B.3, D.3, E.2, E.3 (vencimiento, intención, resúmenes, embeddings, versionado, observabilidad) | Variable | Bonus — para cuando el núcleo de Fases 1–3 esté asentado. |

**Principio:** No parches; bases para un sistema de memoria robusto y escalable. Primero higiene y fundamentos; luego inteligencia adaptativa; después automatización y control; por último optimización avanzada.

---

## ORDEN DE EJECUCIÓN RECOMENDADO (DETALLE)

1. **B.1** (retención episódica) — bajo esfuerzo, evita crecimiento ilimitado.  
2. **B.2** (filtrar por outcome) — bajo esfuerzo, mejora calidad de patrones.  
3. **C.1** (refuerzo procedimental) — medio esfuerzo, impacto directo en planes aprendidos.  
4. **D.1** (perfil vs hechos) — medio esfuerzo, base para D.2.  
5. **D.2** (actualización automática de hechos) — medio esfuerzo.  
6. **E.1** (ponderar fuentes).  
7. **C.2** y **C.3** (vencimiento e intención en procedimental).  
8. **B.3**, **D.3**, **E.2**, **E.3** según prioridad (resúmenes, embeddings, versionado, observabilidad).

---

## CRITERIOS DE CIERRE DE LA MISIÓN 3.2

- Retención episódica y filtrado por outcome implementados y documentados.  
- Al menos refuerzo por éxito (C.1) en memoria procedimental.  
- Perfil vs hechos (D.1) en memoria semántica y, si se asume el compromiso, actualización automática de hechos (D.2).  
- Integración de prioridades/ponderación (E.1) documentada o implementada.  
- `REFINAMIENTO_MEMORIA_LILITH.md` y este documento actualizados con el estado final.

---

## ESTADO DE IMPLEMENTACIÓN (Fases 1–3 ejecutadas)

| Tarea | Estado | Archivos / notas |
|-------|--------|------------------|
| **B.1** Retención episódica | ✅ | `EpisodicStore._prune_old()`; `Config/memory.json`: `max_episodic_days`, `max_episodic_entries`. Prune tras cada `store()`. |
| **B.2** Filtrado por outcome | ✅ | `LearningEngine.analyze_and_suggest_patterns`: solo logs con `outcome == "success"`. |
| **C.1** Refuerzo procedimental | ✅ | `ProceduralStore.increment_use(pattern_id)`; `LearningEngine.get_plan_for_message` devuelve `(plan, pattern_id)`; `Orchestrator` llama `reinforce_procedural_pattern` tras éxito. |
| **D.1** Perfil vs hechos | ✅ | `SemanticMemory`: `facts.jsonl`, `add_fact()`, `get_recent_facts()`; `get_context_for_prompt()` incluye bloque "[Hechos recientes]". |
| **D.2** Actualización automática de hechos | ✅ | `_maybe_store_fact()` en orquestador: detecta "guarda que", "recuerda que", "anota que" y llama `memory_manager.add_fact()`. |
| **E.1** Ponderación de fuentes | ✅ | `Config/memory.json`: `use_learned_plan`, `use_classifier`; `Planner._memory_config()` y comprobaciones en `plan()`. |

**Fase 4** (C.2, C.3, B.3, D.3, E.2, E.3) queda como optimización avanzada opcional.

---

## REFERENCIAS

- `MISION_LILITH_3.0_COMPLETO.md` — Estado 3.0 validado.  
- `REFINAMIENTO_MEMORIA_LILITH.md` — Detalle técnico de mejoras de memoria.  
- `HORIZONTE_LILITH_4.0.md` — Visión a largo plazo.
