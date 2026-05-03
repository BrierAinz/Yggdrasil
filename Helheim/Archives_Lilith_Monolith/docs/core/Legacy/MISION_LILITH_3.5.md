# MISIÓN LILITH 3.5 — EL ESMERILADO

**Estado:** **CERRADA** (implementación completa; validación en entorno real pendiente).

**Visión:** Refinar, pulir y optimizar el núcleo de Lilith 3.4. Esta misión no busca añadir nuevas capacidades, sino alcanzar la perfección en las existentes: eficiencia, claridad, inteligencia y una experiencia de usuario impecable. Es la diferencia entre una herramienta funcional y una obra de arte.

**Base:** Misión 3.4 completada (versionado, auditor de decisiones, VectorStore, search_context con pesos).

---

## BLOQUE A — PULIDO Y EXPERIENCIA DE USUARIO (Refinamiento Rápido)

**Objetivo:** Eliminar la aspereza de las interacciones y hacer que cada respuesta se sienta intencionada e inteligente, incluso los fallos.

| Fase | Tarea | Descripción | Criterio de éxito |
|------|-------|-------------|-------------------|
| **A.1** | Refinar el Fallback Inteligente | Crear una FallbackTool (o lógica equivalente) que, antes de delegar a Lucifer, consulte la memoria semántica. Si encuentra hechos relevantes, genera una respuesta contextual ("Basado en lo que recuerdo..."). | Lilith parece "saber" en lugar de "preguntar a otro" en más casos. |
| **A.2** | Respuestas Proactivas a Errores | Crear un ErrorHandlerTool (o capa en el Orchestrator) que analice excepciones comunes (FileNotFound, KeyError). Si un archivo no existe, busca archivos con nombres similares en el proyecto y sugiere una corrección. | Los errores comunes se convierten en sugerencias útiles en lugar de mensajes crudos. |
| **A.3** | Dar "Voz" a las Tools | Modificar tools como ListDirectoryTool y GatherDirectoryTool para que su salida no sea solo datos, sino un resumen con el tono de Lilith ("He explorado el directorio. Aquí están los fragmentos que he encontrado..."). | La salida de cualquier tool se siente coherente con la personalidad de Lilith. |

---

## BLOQUE B — EFICIENCIA Y ARQUITECTURA INTERNA (Refinamiento Medio)

**Objetivo:** Optimizar la maquinaria interna para mayor rendimiento, escalabilidad y un código más limpio y mantenible.

| Fase | Tarea | Descripción | Criterio de éxito |
|------|-------|-------------|-------------------|
| **B.1** | Cacheo de Respuestas de Agentes | Implementar una capa de cacheo simple (`Data/cache/`) que guarde la respuesta de un agente (Eva, Adán, etc.) a una tarea específica durante un tiempo configurable (ej. 1 hora). | Las tareas repetitivas se resuelven desde la caché, reduciendo latencia y coste de API. |
| **B.2** | Lazy Loading del ToolRegistryV3 | Modificar el ToolRegistryV3 para que las herramientas no se carguen todas al inicio; se instancian solo la primera vez que se invocan. | El tiempo de arranque de la API se reduce significativamente. |
| **B.3** | Refactor del Orchestrator (Separación de Responsabilidades) | Dividir el Orchestrator en tres componentes: **PlanExecutor** (solo ejecuta pasos), **MemoryManager** (toda la lógica de memoria) y **AgentCaller** (delegación a agentes). | El núcleo es más modular, más fácil de probar y preparado para plugins y DAGs (Horizonte 4.0). |

---

## BLOQUE C — INTELIGENCIA Y AUTONOMÍA (Refinamiento Profundo)

**Objetivo:** Hacer que Lilith sea más inteligente en sus decisiones y más autónoma en su aprendizaje.

| Fase | Tarea | Descripción | Criterio de éxito |
|------|-------|-------------|-------------------|
| **C.1** | Delegación Inteligente (Meta-Clasificador) | Crear un **DelegationClassifier** que, antes de enviar una tarea a un agente costoso (Eva), evalúe si Lucifer podría hacerlo "suficientemente bien". Optimiza el uso de recursos. | Las tareas simples se resuelven con el motor rápido; los agentes pesados se reservan para lo que realmente los necesita. |
| **C.2** | Autogeneración de Intent Patterns | El LearningEngine analiza episodios exitosos sin intención clara y sugiere nuevas entradas para `intent_patterns.json`. Ej: "He notado que 5 veces me pediste 'optimizar esto' y delegué a Adán. ¿Debería crear una intención 'optimize_code'?". | Lilith ayuda a optimizar su propia configuración basándose en el uso real. |
| **C.3** | Bucle de Feedback Explícito | Añadir un comando `/feedback [calidad 1-5] [comentario opcional]` que califique la última respuesta. Este feedback se guarda en la memoria episódica y se usa para el refuerzo (o castigo) de patrones procedimentales. | El aprendizaje se guía por la satisfacción del usuario, no solo por el éxito técnico. |

---

## BLOQUE D — CONVERGENCIA CON EL HORIZONTE (Observabilidad y Cierre)

Elementos del horizonte 3.5/4.0 que encajan con el esmerilado: observabilidad, datos para afinar y pulido Discord.

| Fase | Tarea | Descripción | Criterio de éxito |
|------|-------|-------------|-------------------|
| **D.1** | Retención del audit (E.5) | Límite de tamaño o antigüedad para `decision_audit.jsonl` (ej. últimas 5000 líneas o 30 días). | Audit acotado; no crecimiento indefinido. |
| **D.2** | Meta-informe de config (M.2) | Bajo petición o periódicamente: informe "use_learned_plan en X% de casos; max_facts K; sugerencia: …". Guardar en `Data/meta_report.json` o exponer en `/api/status` o `/api/version`. Sin auto-aplicar cambios. | Datos para afinar memoria y Planner sin tocar código. |
| **D.3** | Resumen de auditoría (E.4, opcional) | Endpoint `/api/audit/summary` o página simple que lea `decision_audit.jsonl` y muestre resumen por fuente, intención y últimas N decisiones. | Visibilidad rápida del comportamiento del Planner. |
| **D.4** | Pulido Discord | Revisar comandos slash y permisos (roles owner/trusted/public). Opcional: comando `/patrones` (solo owner) que muestre patrones aprendidos o candidatos (C.2). | Matriz de roles coherente; integración del meta-aprendizaje en Discord. |

---

## ORDEN DE EJECUCIÓN RECOMENDADO

1. **B.3** — Refactor del Orchestrator. Es la tarea más importante: un núcleo modular es la base para todo lo demás.
2. **A.1, A.2, A.3** — Pulido de experiencia. Con el núcleo limpio, es más fácil añadir fallback inteligente, manejo de errores y voz en las tools.
3. **B.1, B.2** — Eficiencia: cacheo de agentes y lazy loading del registro.
4. **D.1** — Retención del audit (rápido; evita crecimiento del log).
5. **C.1, C.2, C.3** — Inteligencia: DelegationClassifier, autogeneración de intent patterns, bucle de feedback.
6. **D.2, D.3, D.4** — Meta-informe, resumen de auditoría y pulido Discord.

---

## ESTADO DE IMPLEMENTACIÓN (primera ola)

| Fase | Estado | Notas |
|------|--------|-------|
| **B.3** Refactor Orchestrator | Hecho | `PlanExecutor`, `AgentCaller`, `MemoryManager.post_interaction`; Orchestrator coordina los tres. |
| **A.1** Fallback inteligente | Hecho | En `PlanExecutor`: si hay memoria semántica relevante, se instruye a Lucifer a iniciar con «Basado en lo que recuerdo». |
| **A.2** Respuestas proactivas a errores | Hecho | En `AgentCaller`: FileNotFoundError → sugerencia de paths similares; KeyError → mensaje claro. |
| **A.3** Voz en tools | Hecho | `ListDirectoryTool` y `GatherDirectoryTool` devuelven texto con tono de Lilith. |
| **D.1** Retención del audit | Hecho | `decision_auditor`: `_prune_audit()` por `audit_max_entries` y `audit_max_days` (Config/memory.json). |
| **B.1** Cacheo de agentes | Hecho | `agent_response_cache.py` + `Data/cache/`; TTL en `Config/memory.json` (`agent_cache_ttl_seconds`). |
| **B.2** Lazy loading registry | Hecho | `register_lazy()` en `ToolRegistryV3`; `create_default_registry` usa solo factories. |
| **C.1** DelegationClassifier | Hecho | En `AgentCaller`: tareas "sencillas" para delegate_eva → delegate_lucifer. |
| **C.2** Autogeneración intents | Hecho | `LearningEngine.suggest_intent_patterns_from_audit()`; usado por `/api/discord/patrones`. |
| **C.3** Feedback explícito | Hecho | `FeedbackStore`, `record_last_plan` en Orchestrator, POST `/api/discord/feedback`, slash `/feedback`. |
| **D.2** Meta-informe | Hecho | `meta_report.py`, GET `/api/meta-report` (opcional `?write_file=true`). |
| **D.3** Resumen auditoría | Hecho | GET `/api/audit/summary?limit=100`. |
| **D.4** Pulido Discord | Hecho | GET `/api/discord/patrones`, slash `/patrones` (owner), `/feedback` (valoración 1-5). |

---

## CRITERIOS DE CIERRE DE LA MISIÓN 3.5

- [x] El Orchestrator ha sido refactorizado en sus tres componentes principales (PlanExecutor, MemoryManager, AgentCaller).
- [x] Las respuestas de fallback y error son contextualizadas y útiles.
- [x] Las herramientas de sistema tienen una salida coherente con la voz de Lilith.
- [x] El sistema de cacheo de agentes está operativo (Data/cache/, agent_cache_ttl_seconds).
- [x] El DelegationClassifier está activo (delegate_eva → delegate_lucifer cuando la tarea es sencilla).
- [x] El bucle de feedback explícito está implementado (/feedback, record_last_plan, reinforce si rating ≥ 4).
- [x] El audit tiene retención; meta-informe y resumen de auditoría disponibles (/api/meta-report, /api/audit/summary).

---

## CHECKLIST PENDIENTE DE VALIDACIÓN

*Ejecutar en entorno real (API + Discord) para cerrar la validación de la misión. Debajo tienes los ejemplos para copiar y pegar; después de cada prueba, marca [x] en el ítem.*

- [x] **Arranque:** `arrancar_lilith.bat` o Core API + Discord bot; comprobar que no hay errores de import (lazy loading, feedback_store, meta_report).
- [x] **Registry:** Primera petición a una tool debe instanciarla; `GET /api/status` debe mostrar `tools_registered` = 14 (o el número de tools registradas).
- [x] **Cache:** Repetir la misma petición a un agente (ej. "explica X"); la segunda debe ser más rápida si está en caché. Fix aplicado: clave de caché usa sufijo del contexto para no repetir la misma respuesta.
- [x] **DelegationClassifier:** Mensaje corto sin "análisis profundo" que antes iba a Eva → debe ir a Lucifer (revisar logs o decision_audit).
- [x] **Feedback:** En Discord, usar el **comando slash** `/feedback` (no escribir el texto en el chat); comprobar `Data/feedback.jsonl` y que no falle el endpoint.
- [x] **Patrones:** Usar el **comando slash** `/patrones` en Discord (owner) o abrir en navegador `GET /api/discord/patrones`; deben devolver learned + suggested_intents.
- [x] **Meta y audit:** Abrir en **navegador** `http://localhost:8000/api/meta-report` y `http://localhost:8000/api/audit/summary` (no escribir en el chat); deben devolver JSON con sources y sugerencias.

---

### Ejemplos para copiar y pegar (validación)

Usa estos textos/comandos en orden; después de cada uno, comprueba el resultado y marca [x] en el ítem correspondiente arriba.

| Paso | Dónde | Qué copiar y pegar |
|------|--------|---------------------|
| **1. Arranque** | Terminal (desde `D:\Proyectos\Yggdrasil\Asgard\Lilith`) | `arrancar_lilith.bat` |
| **2. Registry** | Navegador (API en marcha) | `http://localhost:8000/api/status` |
| **3. Cache (primera vez)** | Discord (mensaje a Lilith) | `Explica en una frase qué es un algoritmo de ordenamiento.` |
| **3. Cache (segunda vez)** | Discord (mismo mensaje) | `Explica en una frase qué es un algoritmo de ordenamiento.` |
| **4. DelegationClassifier** | Discord (mensaje corto, sin "análisis profundo") | `Resume en dos líneas qué hace un Planner.` |
| **5. Feedback** | Discord: **comando slash** (escribir `/` → elegir **feedback** → valoración 5) | No escribas "/feedback 5" como mensaje; usa el menú de comandos. |
| **6. Patrones** | Discord: **comando slash** (escribir `/` → elegir **patrones**) o navegador | `/patrones` desde el menú, o abrir URL en navegador. |
| **6. Patrones (API)** | Navegador | `http://localhost:8000/api/discord/patrones` |
| **7. Meta-informe** | Navegador | `http://localhost:8000/api/meta-report` |
| **7. Audit** | Navegador | `http://localhost:8000/api/audit/summary` |

**Notas:**  
- **/feedback** y **/patrones** son **comandos slash** de Discord: escribe **/** en el chat y elige el comando en la lista; si escribes el texto a mano, Lilith lo trata como mensaje normal y no ejecuta el comando.  
- **meta-report** y **audit/summary** se validan **abriendo la URL en el navegador**, no escribiéndola en el chat.  
- La checklist superior está marcada [x] cuando la validación se ha comprobado.

---

## CÓMO ESTO PREPARA EL HORIZONTE 4.0

| Esmerilado 3.5 | Facilita en 4.0 |
|----------------|------------------|
| **B.3** Orchestrator refactorizado | DAGs y ejecución paralela: PlanExecutor puede evolucionar a ejecutor de grafo sin reescribir todo. |
| **B.2** Lazy loading del registry | Plugins y agentes de dominio: nuevas tools se cargan bajo demanda. |
| **C.2** Autogeneración de intent patterns | Dashboard de memoria y aprobación de sugerencias: mismo flujo "Lilith propone, usuario decide". |
| **D.2 / D.3** Meta-informe y audit | Dashboard de observabilidad y control de memoria (Horizonte 4.0, punto 4). |

*Referencia: `HORIZONTE_LILITH_4.0.md` — agentes de dominio, DAGs, memoria en grafo, dashboard.*

---

## REFERENCIAS

- **MISION_LILITH_3.4.md** — Base de memoria inteligente y observabilidad sobre la que se construye el esmerilado.
- **HORIZONTE_LILITH_4.0.md** — Visiones de plugins, DAGs, memoria en grafo y dashboard; la refactorización 3.5 los hace más viables.

---

*El objetivo de la 3.5 no es añadir, sino perfeccionar: convertir a Lilith en un instrumento afilado, preciso y una alegría de usar antes de la siguiente gran campaña.*
