# Misión: Auditoría de decisiones (metacognición) — Pasos A–Z

**Objetivo:** Implementar y extender el módulo de auditoría de decisiones según el diseño en **DEEP_DIVE_AUDITORIA_DECISIONES_METACOGNICION.md**: rotación por fecha, concurrencia segura con Lock, reason heurístico sistemático, y puntos de registro en Planner, Executor, Clasificador y confirmaciones.

**Estado:** Implementación completada (A–Z). Archivos diarios `Data/decision_audit_YYYY-MM-DD.jsonl` (UTC), `append_decision` unificada, reason en Planner, step_executed en Executor, classify_important en Clasificador, confirm_requested/confirm_resolved en Discord. Lectura: `GET /api/discord/audit`, `GET /api/discord/audit/download`, comando `/lilith audit` (Embed + descargar). Legacy: primer append renombra `decision_audit.jsonl` → `decision_audit_legacy.jsonl`.

**Estado base (histórico):** `Backend/core/auditor/decision_auditor.py` ya existía y registraba decisiones del Planner en `Data/decision_audit.jsonl`; el Planner llamaba a `log_plan_decision()` en varias fuentes.

**Pasos:** A (Config) → B–E (rotación, lock, poda) → F–G (API unificada, reason Planner) → H–J (Executor, Clasificador, Confirmaciones) → K–M (esquema, migración, memory.json) → N (lectura) → O–Q (pruebas, logging, version) → U–Z (validación, truncado, docs, changelog, permisos, cierre).

---

## Preparando el terreno: decisiones para L (Legacy) y N (Lectura)

Antes de programar la secuencia S, se fijan estas dos decisiones logísticas.

### L — La pila de legacy (`Data/decision_audit.jsonl`)

**Pregunta:** ¿Hay información crítica que deba conservarse a toda costa?

- **Si SÍ (necesitas historial auditable anterior):** Escribir un script **una sola vez**, por ejemplo `Scripts/migrate_audit.py`, que:
  1. Lea `Data/decision_audit.jsonl` línea a línea.
  2. Parsee cada línea como JSON, extraiga `timestamp` (o el campo que lleve la fecha).
  3. Obtenga la fecha en UTC y escriba esa línea en `Data/decision_audit_YYYY-MM-DD.jsonl` correspondiente (usando la misma lógica de path que el auditor, con lock si se invoca desde el mismo proceso, o sin lock si el script corre offline).
  4. Al final, renombre el archivo viejo a `Data/decision_audit_legacy.jsonl.bak` (o lo mueva a un subdirectorio `Data/archive/`).
  El código nuevo **solo** escribe en archivos diarios; no vuelve a tocar el legacy.

- **Si NO (puedes empezar en limpio desde hoy):** No migrar. Al activar la rotación por fecha:
  1. Renombrar el archivo existente a `Data/decision_audit_legacy.jsonl` (o `.bak`) para no perderlo por si acaso.
  2. A partir de ese momento, toda escritura va a `decision_audit_YYYY-MM-DD.jsonl`.
  No hace falta `Scripts/migrate_audit.py`; el legacy queda como archivo histórico opcional para inspección manual.

**Decisión recomendada:** **Empezar en limpio** (renombrar a `decision_audit_legacy.jsonl` y no migrar), salvo que tengas un requisito explícito de conservar y consultar el historial antiguo. Si más adelante necesitas ese historial, puedes añadir el script de migración y ejecutarlo una vez.

---

### N — Exposición en Discord (comando /lilith audit y endpoint)

**Pregunta:** ¿Enviar el archivo completo como adjunto o mostrar los últimos eventos en un Embed?

- **Opción A — Adjunto:** El bot envía el archivo del día (o el rango pedido) como `.jsonl` o `.txt` adjunto. Ventaja: puedes abrirlo en tu máquina, buscar, analizar con herramientas. Desventaja: en canales con muchos usuarios el adjunto puede resultar pesado; no ves un resumen rápido en el chat.

- **Opción B — Embed en el chat:** El bot parsea las últimas N líneas (ej. 5–10), formatea cada evento (fecha, tipo, reason, preview de message/payload) y las muestra en un Embed (o varios si hay límite de caracteres). Ventaja: lectura rápida sin salir de Discord. Desventaja: no sustituye un análisis profundo sobre el archivo completo.

**Decisión recomendada:** **Híbrido.**

1. **Por defecto (Embed):** El comando `/lilith audit` (y el endpoint `GET /api/discord/audit?date=...&limit=10`) devuelve/muestra las **últimas 10 eventos** (o 5 si prefieres menos ruido) formateados en un Embed: una línea por evento con `timestamp`, `decision_type`, `actor`, `reason` y un preview corto de `message` o `payload` (ej. 80 caracteres). Así ves de un vistazo qué decidió Lilith sin descargar nada.

2. **Adjunto bajo petición:** Añadir un parámetro o subcomando, por ejemplo `/lilith audit descargar` o `?attach=1` en el endpoint, que envíe el archivo del día (o el rango solicitado) como adjunto `.jsonl` para cuando quieras analizarlo en local. Opcionalmente un botón en el Embed tipo "Descargar hoy (.jsonl)" que responda con el adjunto.

Con esto se cubre tanto la consulta rápida en chat como la necesidad de tener el archivo completo en tu computadora cuando haga falta.

---

## A. Configuración de auditoría

- **A.1** Crear o extender config para auditoría:
  - En `Config/memory.json`: añadir `audit_retention_days` (default 30); mantener `audit_max_entries` y `audit_max_days` como legacy hasta migración completa, o deprecarlos en comentario.
  - Opcional: crear `Config/audit.json` con `audit_retention_days`, `audit_dir` (default `"Data"`), `audit_filename_prefix` (default `"decision_audit"`) para no acoplar al memory.json.
- **A.2** Definir convención de nombres: archivo del día = `{audit_dir}/decision_audit_YYYY-MM-DD.jsonl` (fecha en UTC).

---

## B. Rotación por fecha (archivo diario)

- **B.1** Añadir en `decision_auditor.py`:
  - `_audit_base_dir() -> Path`: lee config (audit_dir o Data), devuelve Path a la carpeta de auditoría.
  - `_audit_path_for_date(date: date) -> Path`: devuelve `{base_dir}/decision_audit_{YYYY-MM-DD}.jsonl` para la fecha dada (UTC).
  - `_audit_path_for_today() -> Path`: devuelve `_audit_path_for_date(datetime.now(timezone.utc).date())`.
- **B.2** Sustituir el uso de `_audit_path()` (archivo único) por `_audit_path_for_today()` en la ruta de escritura. Mantener `_audit_path()` como alias a `_audit_path_for_today()` o eliminarlo y actualizar todas las referencias.

---

## C. Concurrencia: threading.Lock

- **C.1** En `decision_auditor.py`, definir un `_write_lock = threading.Lock()` a nivel de módulo.
- **C.2** En toda función que escriba una línea en el JSONL (append): adquirir `_write_lock` antes de abrir el archivo en modo append y liberarlo al salir (usar `with _write_lock:` o try/finally). Garantizar que solo un hilo escribe a la vez en el archivo del día.

---

## D. Eliminar reescritura en caliente (_prune_audit)

- **D.1** Dejar de llamar a `_prune_audit()` después de cada append (esa función reescribe todo el archivo y es incompatible con rotación por fecha y con concurrencia).
- **D.2** Mantener `_prune_audit()` solo para compatibilidad con el archivo legacy `decision_audit.jsonl` si se desea podarlo una última vez antes de migrar; o eliminarla cuando la rotación por fecha esté activa.

---

## E. Retención: borrado de archivos viejos

- **E.1** Implementar `_prune_old_audit_files()`: listar en `_audit_base_dir()` los archivos que coincidan con `decision_audit_*.jsonl`, extraer la fecha del nombre (regex o parse de `YYYY-MM-DD`), borrar los que sean anteriores a `today - audit_retention_days`. No usar el lock de escritura para esta operación (o usar un lock breve solo para listar/borrar).
- **E.2** Llamar a `_prune_old_audit_files()` en el primer append del día: guardar en variable de módulo la última fecha en que se hizo prune (ej. `_last_prune_date`); si `today != _last_prune_date`, ejecutar prune y actualizar `_last_prune_date`. Alternativa: ejecutar prune al arranque del proceso (en el primer uso del auditor) en lugar de “primer append del día”.

---

## F. API unificada de escritura

- **F.1** Definir `append_decision(decision_type: str, actor: str, payload: dict, reason: Optional[str] = None, message: Optional[str] = None, extra: Optional[dict] = None) -> None`. Campos mínimos del payload: según tipo (plan, step_executed, classify_important, confirm_requested, confirm_resolved). Incluir siempre `timestamp` (UTC ISO), `version`, `decision_type`, `actor`; el resto en `payload` o en campos de primer nivel según conveniencia.
- **F.2** Implementar `append_decision` con: adquirir lock, obtener path del día, asegurar que el directorio existe, append una línea JSON, opcionalmente invocar prune de archivos viejos (según E.2), liberar lock. No reescribir archivo.
- **F.3** Hacer que `log_plan_decision(...)` construya un payload estándar y llame a `append_decision(decision_type="plan", actor="planner", payload={...}, reason=..., message=...)` para no duplicar lógica de escritura.

---

## G. Reason heurístico en Planner (todas las fuentes)

- **G.1** **Learned plan:** En la llamada a `log_plan_decision` por learned_plan, añadir `reason="learned_plan"` (y opcionalmente el intent o nombre del plan si está disponible).
- **G.2** **Classifier:** En la llamada por classifier, añadir `reason="classifier"` o `reason=f"classifier → {plan_generated[0]}"`.
- **G.3** **Intent patterns:** En la llamada por intent_patterns, añadir `reason=f"intent:{matched_intent}"` o `reason=f"intent:{matched_intent} | plan:{','.join(plan_generated)}"`.
- **G.4** **Matching learning:** Ya tiene `reason=f"confidence={confidence}"`; mantener o normalizar a `reason=f"matching_learning | confidence={confidence}"`.
- **G.5** **Fallback Lucifer:** Ya tiene `reason="no_intent_or_learned_plan_matched"`; mantener.

Asegurar que en todos los puntos anteriores se pase siempre un `reason` corto y legible (string heurístico).

---

## H. Auditoría en PlanExecutor (step_executed)

- **H.1** En `PlanExecutor`, tras ejecutar cada paso (en el hilo principal, al recoger el resultado de cada future), llamar a `append_decision(decision_type="step_executed", actor="executor", payload={"step_id": sid, "tool_name": step.tool_name, "result_preview": resultado[:200] o similar}, reason=f"tool={step.tool_name}")`. Hacerlo después de `step_results[sid] = ...` para no bloquear la oleada; la llamada es rápida (append con lock).
- **H.2** Opcional: registrar solo pasos que sean delegate_* o read_file/list_directory para no inflar el log; o registrar todos con un flag en config `audit_log_all_steps`.

---

## I. Auditoría en Clasificador (classify_important)

- **I.1** En `Backend/core/auto_learn/classifier.py`, en la fase LLM (cuando se actualiza `x["important"]`), después del bucle sobre `to_refine`, llamar al auditor con `append_decision(decision_type="classify_important", actor="classifier", payload={"items_refined": len(to_refine), "sample_ids": [id del item si existe]}, reason="heuristic_then_llm")`. Si se quiere por ítem, hacer un append por ítem con `payload={"item_id": ..., "important": True/False}` y `reason="heuristic_then_llm"` o snippet de keywords.
- **I.2** Mantener reason heurístico únicamente (sin pedir al LLM una línea de reason en esta misión).

---

## J. Auditoría en confirmaciones (Discord)

- **J.1** En `discord_api.py`, cuando se crea una confirmación pendiente (acción peligrosa): llamar a `append_decision(decision_type="confirm_requested", actor="discord", payload={"token": token, "summary": summary, "owner_id": ...}, reason="dangerous_action")`.
- **J.2** Cuando el usuario autoriza o deniega (endpoint de confirm): llamar a `append_decision(decision_type="confirm_resolved", actor="discord", payload={"token": ..., "result": "confirmed"|"cancelled"}, reason=...)`.

---

## K. Esquema de evento y documentación

- **K.1** Documentar en código o en `DEEP_DIVE_AUDITORIA_DECISIONES_METACOGNICION.md` el esquema mínimo de cada línea JSONL: `timestamp`, `version`, `decision_type`, `actor`, `payload` (objeto), `reason` (opcional), `message` (opcional). Para eventos `plan`, mantener compatibilidad con campos actuales `message`, `decision_source`, `plan_generated`, `matched_intent` dentro de `payload` o en raíz según se defina en F.1–F.3.
- **K.2** Añadir en el deep dive o en este documento una tabla: decision_type → descripción, actor, campos típicos de payload.

---

## L. Migración desde archivo único (legacy)

- **L.1** **Decisión (ver “Preparando el terreno”):** Por defecto, **no migrar**. Si existe `Data/decision_audit.jsonl`, al activar la rotación por fecha: renombrarlo a `Data/decision_audit_legacy.jsonl` (o `.bak`) y a partir de ahí escribir solo en archivos diarios. No ejecutar poda ni reescritura sobre el legacy.
- **L.2** **Opcional (si se exige conservar historial):** Implementar `Scripts/migrate_audit.py` que lea el legacy línea a línea, extraiga fecha de `timestamp`, escriba cada línea en `decision_audit_YYYY-MM-DD.jsonl` correspondiente, y al final renombre el legacy a `.bak`. Ejecución manual una sola vez.

---

## M. Config memory.json / audit

- **M.1** Añadir en `Config/memory.json` la clave `audit_retention_days` (valor 30) y, si se usa, `audit_dir` (valor `"Data"`). Documentar que `audit_max_entries` y `audit_max_days` ya no se usan con rotación por fecha.
- **M.2** En `_audit_config()` (o en una función que lea config de auditoría), leer `audit_retention_days` y `audit_dir` con defaults 30 y "Data".

---

## N. Exposición de la auditoría (lectura)

- **N.1** **Decisión (ver “Preparando el terreno”):** Comportamiento **híbrido**.
- **N.2** **Endpoint GET** `GET /api/discord/audit?date=YYYY-MM-DD&limit=10&attach=0`: lee el archivo del día (o `date` opcional), devuelve las últimas `limit` líneas como JSON (lista de objetos). Si `attach=1`, en la respuesta para Discord se permitirá indicar “enviar como adjunto” (el bot usará este endpoint para generar el adjunto). Solo owner.
- **N.3** **Comando Discord** `/lilith audit` (solo owner): por defecto muestra un **Embed** con las últimas 10 (o 5) eventos formateados: por cada uno, `timestamp`, `decision_type`, `actor`, `reason`, preview de `message`/`payload` (ej. 80 caracteres). Evitar superar el límite de caracteres del Embed (dividir en varios Embeds si hace falta).
- **N.4** **Adjunto bajo petición:** Subcomando o parámetro, ej. `/lilith audit descargar`, o botón “Descargar hoy (.jsonl)” en el Embed, que envíe el archivo del día como adjunto `.jsonl` para análisis en local.

---

## O. Pruebas y verificación

- **O.1** Prueba manual o con script: generar varias decisiones (plan, step, classify), comprobar que se crean archivos `decision_audit_YYYY-MM-DD.jsonl` y que cada línea es JSON válido.
- **O.2** Ejecutar un plan con varios pasos en paralelo (DAG) y comprobar que no hay líneas corruptas ni entrelazadas en el JSONL (lock funcionando).
- **O.3** Comprobar que al cambiar de día (o simular fecha) se escribe en un archivo nuevo y que `_prune_old_audit_files()` borra archivos con fecha anterior a retention_days.

---

## P. Logging y errores

- **P.1** En `append_decision` y en `log_plan_decision`, en caso de excepción (archivo no escribible, JSON no serializable), registrar con `logger.debug` o `logger.warning` y no propagar la excepción al flujo principal (el auditor no debe tumbar el Planner ni el Executor).

---

## Q. Versión y compatibilidad

- **Q.1** Mantener el campo `version` en cada entrada con el valor de `LILITH_VERSION` (o "audit_v2") para distinguir formato legacy del nuevo formato con `decision_type`/`actor`/`payload`.

---

## R. Índice de la misión (checklist)

| Paso | Descripción |
|------|-------------|
| A | Config (audit_retention_days, audit_dir) |
| B | Rotación por fecha (_audit_path_for_today, archivo diario) |
| C | threading.Lock en escritura |
| D | Eliminar _prune_audit en cada append |
| E | _prune_old_audit_files y llamada (primer append del día o arranque) |
| F | append_decision unificada; log_plan_decision delega en ella |
| G | Reason heurístico en todas las fuentes del Planner |
| H | Auditoría en Executor (step_executed) |
| I | Auditoría en Clasificador (classify_important) |
| J | Auditoría en confirmaciones Discord (confirm_requested / confirm_resolved) |
| K | Esquema y documentación de eventos |
| L | Migración opcional del archivo legacy |
| M | Claves en memory.json (audit_retention_days, audit_dir) |
| N | Endpoint y/o comando de lectura de auditoría |
| O | Pruebas (archivos diarios, concurrencia, retención) |
| P | Logging y no propagar excepciones |
| Q | Campo version en entradas |
| T | Referencias (deep dive, código, plan) |
| U | Validación de payload (tipos, tamaños máximos) |
| V | Límite de tamaño por línea (truncar message/payload) |
| W | Documentar decision_type en __init__ o módulo auditor |
| X | Changelog / nota de versión (auditoría v2) |
| Y | Revisión de permisos (quién puede leer audit vía API) |
| Z | Cierre: actualizar PLAN_AUTOMEJORA y ROADMAP con “Auditoría completada” |

---

## S. Orden sugerido de implementación

1. **A, M** — Config.
2. **B, C, E** — Rotación, lock, poda de archivos viejos.
3. **D, F** — Quitar reescritura, API unificada y que log_plan_decision use append_decision.
4. **G** — Reason en Planner.
5. **H, I, J** — Executor, Clasificador, Confirmaciones.
6. **K, L** — Docs y migración legacy.
7. **N** — Lectura (API/comando).
8. **O, P, Q** — Pruebas, logging, version.
9. **U, V, W, X, Y, Z** — Validación, truncado, documentación de tipos, changelog, permisos, cierre en roadmap.

---

## U. Validación de payload

- **U.1** En `append_decision`, validar que `decision_type` y `actor` sean strings no vacíos; que `payload` sea dict (o serializable a dict). Si no, registrar warning y no escribir línea corrupta.

---

## V. Límite de tamaño por línea

- **V.1** Truncar `message` a N caracteres (ej. 2000); truncar cadenas largas dentro de `payload` (ej. `result_preview` a 200–500 caracteres) para que una sola línea JSON no supere un tamaño razonable (ej. 10 KB) y no degrade I/O.

---

## W. Documentación de decision_type

- **W.1** En `auditor/__init__.py` o en el docstring del módulo, listar los `decision_type` soportados: `plan`, `step_executed`, `classify_important`, `confirm_requested`, `confirm_resolved`, y el significado de cada uno.

---

## X. Changelog / nota de versión

- **X.1** Añadir en FIXES_Y_MEJORAS.md o en el changelog del proyecto una entrada: “Auditoría de decisiones v2: rotación por fecha, lock, reason heurístico, eventos executor/clasificador/confirmaciones”.

---

## Y. Permisos de lectura

- **Y.1** Definir quién puede llamar al endpoint de lectura de auditoría: solo owner (Discord) o también trusted con scope restringido. Documentar en la API y en ROLES_Y_PERMISOS si aplica.

---

## Z. Cierre en roadmap

- **Z.1** Tras completar la misión, actualizar **PLAN_AUTOMEJORA_LILITH.md** (y si aplica **ROADMAP_HACIA_4.0.md**) marcando el ítem “Auditoría de decisiones” como implementado y enlazando a esta misión y al deep dive.

---

## T. Referencias

- Diseño: **Core/Docs/DEEP_DIVE_AUDITORIA_DECISIONES_METACOGNICION.md**
- Código actual: **Backend/core/auditor/decision_auditor.py**, **Backend/core/planner.py**, **Backend/core/plan_executor.py**, **Backend/core/auto_learn/classifier.py**, **Backend/api/discord_api.py**
- Plan de auto-mejora: **PLAN_AUTOMEJORA_LILITH.md** (§5 Auditoría de decisiones)

---

## Changelog (auditoría v2)

- **A–F:** Config (audit_retention_days, audit_dir), rotación por fecha, `threading.Lock`, `append_decision()`, `_prune_old_audit_files()`, `log_plan_decision` delega en `append_decision`.
- **G:** Reason heurístico en todas las fuentes del Planner (learned_plan, classifier, intent_patterns, matching_learning, fallback_lucifer).
- **H:** `step_executed` en PlanExecutor (ola única, secuencial y paralela; timeout y fallos incluidos).
- **I:** `classify_important` en auto_learn/classifier (tras refinado LLM).
- **J:** `confirm_requested` y `confirm_resolved` en discord_api (creación desde job, owner, trusted; resolución confirm/cancel/error).
- **L:** Renombre único de `decision_audit.jsonl` → `decision_audit_legacy.jsonl` en el primer append.
- **N:** `GET /api/discord/audit`, `GET /api/discord/audit/download`, comando `/lilith audit` (Embed + descargar).
- **W:** decision_type documentado en docstring del módulo.
- **Z:** PLAN_AUTOMEJORA_LILITH.md §5 actualizado (Auditoría implementada).
