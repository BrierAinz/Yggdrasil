# Deep Dive: Auditoría de decisiones (metacognición) en producción

**Objetivo:** Resolver tres aristas técnicas antes de extender el módulo de auditoría: (1) extracción estructurada del "por qué", (2) estrategia de rotación del log, (3) concurrencia y bloqueo. El código actual vive en `Backend/core/auditor/decision_auditor.py` y ya registra decisiones del Planner en `Data/decision_audit.jsonl`.

---

## 1. Extracción estructurada del "reason" (por qué)

**Situación:** En Planner y Clasificador, la "razón" puede estar en la cabeza del LLM (Lucifer/Eva) o ser inferible desde el código (heurística, intent matched, learned plan).

### Decisión: **Híbrido — razón heurística por defecto; LLM opcional y acotado**

- **No** forzar a todos los agentes a devolver un JSON con `{"reasoning": "..."}`. Implicaría cambiar system prompts y parsing en muchos sitios y aumentaría tokens y fragilidad.
- **Sí** rellenar el campo `reason` desde el código Python de forma sistemática:
  - **Planner:** La "razón" ya es implícita: `decision_source` (e.g. `intent_patterns`, `classifier`, `learned_plan`, `fallback_lucifer`) + `matched_intent` / `plan_generated` explican el qué. Se puede normalizar un `reason` corto por fuente, ej. `"intent: read_file | path: Backend/core/planner.py"`, `"learned_plan"`, `"classifier → delegate_lucifer"`, `"no_intent_or_learned_plan_matched"`. Todo esto es **heurístico**, sin llamar al LLM.
  - **Clasificador:** Hoy el LLM devuelve texto libre ("important: true/false"). Opciones:
    - **A)** Dejar `reason` como resumen heurístico: `"heuristic_then_llm"`, `"keywords_hit: llm, rag"`, o el snippet del contenido que pasó la criba. Sin tocar el prompt.
    - **B)** Extensión opcional: en la Fase 2 del clasificador, añadir una frase al prompt: "En una línea opcional después, indica por qué (ej. «reason: menciona RAG»)." Parsear esa línea si existe y guardarla en `reason`; si no, usar heurística. Sin exigir JSON estructurado al LLM.
- **Recomendación:** Implementar **A** en la primera iteración (solo razón heurística en clasificador). Si más adelante se quiere traza explícita del LLM, añadir **B** solo en clasificador y parsear la línea opcional.

### Esquema del evento de auditoría

Mantener un único formato de evento con `reason` opcional (string):

- `reason`: siempre string cuando se rellena; generado por código (heurístico) o, en el futuro, por parseo opcional de una línea del LLM. Sin exigir subcampos tipo `{"summary": "...", "llm_reason": "..."}` por ahora; si un día el clasificador devuelve texto explícito, se puede guardar en `reason` tal cual (con tope de caracteres).

---

## 2. Estrategia de rotación del log (Disk I/O)

**Problema:** Un solo `decision_audit.jsonl` crece sin límite. La poda actual (`_prune_audit`) **reescribe todo el archivo** tras cada append (lee, filtra por fecha y por número de entradas, escribe de nuevo). Eso:

- No escala con muchos eventos (I/O pesado en cada escritura).
- Es **peligroso con concurrencia**: otro hilo puede hacer append entre nuestra lectura y nuestra escritura, y la reescritura borraría su línea.

### Decisión: **Rotación por fecha (archivo diario) + retención por días**

- **Nombre de archivo:** `decision_audit_YYYY-MM-DD.jsonl` (ej. `decision_audit_2026-03-15.jsonl`). Un archivo por día; el día en UTC para evitar ambigüedades con zonas horarias.
- **Escritura:** Solo **append** al archivo del día. No reescribir ni leer el archivo completo en el camino crítico.
- **Retención:** Borrar archivos cuya fecha (del nombre) sea anterior a `audit_retention_days` (ej. 30). La limpieza puede hacerse:
  - **Opción recomendada:** En el primer `append_decision()` de cada día (o al arranque del proceso), listar `Data/decision_audit_*.jsonl`, eliminar los que tengan fecha &lt; hoy - retention_days. Así no bloqueamos cada append con una poda pesada.
  - Alternativa: job/cron externo que borre archivos viejos.
- **Ventajas:** Revisión humana trivial ("quiero ver qué pasó el 15 de marzo" → un solo archivo). Sin condición de carrera por reescritura. Append es O(1) por evento.
- **Config:** En `Config/memory.json` (o en un `Config/audit.json` si se prefiere separar): `audit_retention_days` (default 30), y opcionalmente `audit_dir` para la carpeta (default `Data/`). Si se quiere límite por tamaño además de por tiempo, se puede documentar más adelante un "si el archivo del día supera X MB, rotar a `decision_audit_YYYY-MM-DD_2.jsonl`"; por ahora no es necesario.

### Migración desde el estado actual

- El código actual escribe en `Data/decision_audit.jsonl` y usa `_prune_audit()`. Al adoptar rotación por fecha:
  - Dejar de llamar a `_prune_audit()` en cada append.
  - Cambiar `_audit_path()` a algo como `_audit_path_for_today()` que devuelva `Data/decision_audit_YYYY-MM-DD.jsonl`.
  - Añadir función `_prune_old_audit_files()` que borre archivos `decision_audit_*.jsonl` con fecha en el nombre &lt; hoy - retention_days, y llamarla una vez al día (o al arranque).
  - Opcional: un script único que lea `decision_audit.jsonl` (si existe), reparta líneas por fecha y escriba en los nuevos archivos por día, luego renombre o archive el monolitónico.

---

## 3. Bloqueo síncrono vs. asíncrono (concurrencia)

**Problema:** El PlanExecutor usa `ThreadPoolExecutor` para oleadas paralelas; varios hilos pueden completar pasos en el mismo milisegundo y llamar a `append_decision()` (o equivalente) al mismo tiempo. Escribir en el mismo archivo JSONL sin coordinación puede provocar:

- Líneas entrelazadas o truncadas (condición de carrera).
- Si además hubiera poda que reescribe el archivo, corrupción o pérdida de datos.

### Decisión: **`threading.Lock` en el módulo de auditoría**

- Usar un **único `threading.Lock`** dentro de `decision_audit.py` (o el módulo que centralice la escritura). Toda escritura a disco (append a un archivo de auditoría) se hace **solo** tras adquirir el lock.
- Ventajas:
  - Implementación simple; no introduce colas ni hilos adicionales.
  - El coste de un append (una línea JSON) es muy bajo; el lock se retiene unos milisegundos. No se espera a un batch.
  - Comportamiento predecible y fácil de depurar.
- Desventaja menor: si en el futuro hubiera cientos de escrituras por segundo desde muchos hilos, el lock podría ser un cuello. Con decenas de eventos por DAG y jobs cada hora, es irrelevante.

### No usar (por ahora) cola + hilo escritor

- Un diseño "encolar eventos y que un hilo secundario escriba en batch" sería más complejo (cola thread-safe, hilo daemon, flush al cerrar, riesgo de pérdida si el proceso termina brusco). No está justificado con el volumen actual.
- Si más adelante el volumen creciera, se podría:
  - Mantener el lock pero escribir a una cola en memoria y que un solo hilo vuelque la cola al archivo cada N ms o N eventos; o
  - Usar rotación por fecha + lock; cada archivo diario sigue siendo un solo writer por proceso.

### Alcance del lock

- **Cubrir:** `append_decision(...)` (o la función que escriba una línea en el JSONL). Adquirir el lock, abrir archivo (path del día), append una línea, cerrar, liberar lock. Si se implementa `_prune_old_audit_files()`, ejecutarla **fuera** del lock o en un lock breve solo para listar/borrar archivos viejos (no el mismo archivo al que se hace append), para no bloquear los appends.

---

## 4. Resumen de decisiones

| Arista | Decisión |
|--------|----------|
| **Reason** | Heurístico por defecto (código Python). Planner: reason derivado de decision_source + matched_intent/plan_generated. Clasificador: reason heurístico (ej. "heuristic_then_llm", keywords). Opcional más adelante: una línea de "reason" en la respuesta del LLM del clasificador, parseada y guardada. No forzar JSON con reasoning en todos los agentes. |
| **Rotación** | Por **fecha**: `decision_audit_YYYY-MM-DD.jsonl`. Append solo; retención borrando archivos con fecha &lt; hoy - audit_retention_days (en primer append del día o al arranque). Sin reescritura en caliente. |
| **Concurrencia** | **`threading.Lock`** en el módulo; toda escritura (append) al JSONL pasa por el lock. No cola ni hilo escritor por ahora. Poda de archivos viejos fuera del lock de append. |

---

## 5. Referencias de código actual

- **Auditor:** `Backend/core/auditor/decision_auditor.py` — `log_plan_decision()`, `_audit_path()`, `_prune_audit()`.
- **Config de retención:** `Config/memory.json` (`audit_max_entries`, `audit_max_days`) — a migrar/ampliar a `audit_retention_days` y rotación por fecha.
- **Llamadas desde Planner:** `Backend/core/planner.py` (varios `log_plan_decision(..., reason=...)` ya con reason heurístico en algunos casos).
- **Executor (concurrencia):** `Backend/core/plan_executor.py` — `ThreadPoolExecutor`, múltiples `_execute_step_worker` que podrían llamar a un futuro `append_decision(decision_type="step_executed", ...)`.

Con estas tres aristas resueltas, el módulo de auditoría queda definido para implementación sin cuello de botella de rendimiento ni vertedero incomprensible, y con seguridad ante concurrencia y crecimiento del log.

---

## 6. Casos límite del I/O

### 6.1 Colisión de zonas horarias (UTC vs local, ej. CST/CDMX)

- Los nombres de archivo usan **siempre la fecha en UTC** (`decision_audit_YYYY-MM-DD.jsonl`). En Ciudad de México (UTC-6), una decisión a las 22:00 local se registra en el archivo del **día siguiente** en UTC.
- **GET /api/discord/audit?date=...:** Por defecto, `date` se interpreta como **fecha UTC** (el archivo que se lee es exactamente ese día UTC). Quien consulta desde Discord debe pedir la fecha en UTC o asumir el desfase (ej. "hoy" en la API = hoy UTC, no hoy local).
- **Opción futura:** Si se implementa `date=today&tz=America/Mexico_City`, la API puede resolver "hoy" en esa zona y devolver eventos de los archivos UTC que intersectan con ese día local (a lo sumo dos archivos: noche anterior UTC + día actual UTC).

### 6.2 Concurrencia en la poda (_maybe_prune_once_per_day)

- `_maybe_prune_once_per_day()` se invoca **dentro de `_WRITE_LOCK`** (desde `append_decision`), por lo que solo un hilo la ejecuta a la vez; no hay doble ejecución por parte de dos hilos en el mismo proceso.
- Por si en el futuro la poda se llamara desde otro sitio o hubiera race (ej. dos procesos), los **borrados** (`f.unlink()`) van envueltos en `try/except (ValueError, OSError, FileNotFoundError)`: si otro hilo/proceso ya borró el archivo, no se propaga la excepción y el hilo de limpieza no colapsa.

### 6.3 Inflación del payload (bloat)

- El módulo **no confía** en que el llamador saneé el payload. Se aplica **`_sanitize_payload(payload)`** antes de escribir:
  - Recorre recursivamente dict/list.
  - Trunca cualquier string a `MAX_PAYLOAD_STRING_CHARS` (2000).
  - Limita profundidad a `MAX_PAYLOAD_DEPTH` (6).
  - Limita longitud de listas a `MAX_PAYLOAD_LIST_LEN` (50); el resto se sustituye por un indicador `<truncated N more>`.
- Así, aunque el PlanExecutor pase un resultado de extracción web masiva en `payload`, la línea escrita queda acotada y no se generan líneas de megabytes.
