# Feedback progresivo del DAG (streaming del PlanExecutor)

Diseño para que el mensaje de Discord pase de "🔮 Lilith está pensando..." a actualizaciones paso a paso (ej. "Paso 1: Extrayendo Reddit ✅", "Paso 2: Lucifer sintetizando...") mientras se ejecuta el DAG, sin bloquear la API HTTP.

---

## Objetivo

- **Problema:** La API es HTTP síncrona; el cliente espera hasta que toda la oleada del DAG termina. El usuario ve un único placeholder durante 30–60 s.
- **Objetivo:** Que un listener asíncrono en Discord reciba eventos de progreso y edite el embed en tiempo real.

---

## Base implementada (4.0 UX)

1. **`PlanExecutor.run_plan(..., progress_callback=...)`**  
   Acepta un callback opcional `(step_index: int, step_id: str, label: str) -> None` que se invoca tras cada paso (o tras cada oleada paralela). Las etiquetas son legibles (ej. "Extrayendo lore", "Lucifer sintetizando") vía `_label_for_tool(tool_name)`.

2. **`Orchestrator.execute_plan(..., progress_callback=...)`** y **`execute_steps(..., progress_callback=...)`**  
   Reenvían el callback al PlanExecutor para que la API pueda inyectar uno.

---

## Arquitectura objetivo (cola + WebSocket)

1. **Request con `X-Request-ID`**  
   El bot de Discord genera un `request_id` (UUID), envía `POST /api/discord/chat` con header `X-Request-ID: <request_id>` y (en paralelo) se conecta al WebSocket y envía `{ "subscribe": "<request_id>" }`.

2. **API: callback → cola**  
   En `discord_chat`, al llamar a `orchestrator.execute_plan(..., progress_callback=...)`, el callback pone en una cola thread-safe (p. ej. `queue.Queue`) eventos `{ "request_id": "...", "step_index": n, "step_id": "...", "label": "..." }`. El hilo que ejecuta el plan es el que invoca el callback; la cola debe ser segura entre hilos.

3. **Consumidor asyncio**  
   Una tarea en el bucle de FastAPI (o del servidor que monta el router de Discord) lee de la cola (o de un diccionario `request_id → Queue`) y, para cada evento, hace broadcast por WebSocket a los clientes que se suscribieron a ese `request_id`.

4. **Protocolo WebSocket**  
   - Cliente envía: `{ "action": "subscribe", "request_id": "uuid" }`.  
   - Servidor envía eventos de progreso y cierre (ver sección *Estructura del payload* y *Ciclo de vida del request_id*).

5. **Bot Discord**  
   - Crea el placeholder "🔮 Lilith está pensando...".  
   - Lanza en paralelo: (A) tarea que espera la respuesta HTTP, (B) tarea que mantiene conexión WS (o reconecta) y, al recibir `plan_progress`, edita el mensaje con un embed que muestra "Paso N: &lt;label&gt; ✅" y el paso actual "en curso".  
   - Cuando (A) termina, envía la respuesta final, borra el placeholder (o lo reemplaza) y deja de escuchar eventos de ese `request_id`.

---

## Consideraciones

- **Thread-safety:** El callback se ejecuta en el hilo del `PlanExecutor` (o del `asyncio.to_thread`). La cola debe ser `queue.Queue` (o similar) y el consumidor en el main loop debe usar `loop.call_soon_threadsafe` o un `asyncio.Queue` alimentado desde el hilo.
- **WebSocket existente:** En `Core/Backend/api/server.py` ya existe `/ws` y gestión de conexiones; el router de Discord puede vivir en el mismo FastAPI y compartir un registro de colas por `request_id`, o exponer un endpoint WS específico para progreso de chat (ej. `/ws/discord-progress`).
- **Timeout:** Si el HTTP tarda más de 120 s, el bot ya actualiza el placeholder a "⏳ Procesando..."; los eventos de progreso pueden seguir llegando y actualizando hasta que llegue la respuesta final.

---

## Deep Dive: vectores de riesgo del streaming

### 1. Límites de edición en Discord (rate limiting)

**Riesgo:** La API de Discord limita las ediciones de un mismo mensaje a **5 ediciones cada 5 segundos**. Si el DAG completa varios pasos muy rápidos (p. ej. 4 pasos locales en 2 s), editar el placeholder por cada evento dispararía HTTP 429 (Too Many Requests).

**Decisión:** **Throttling en el cliente (bot)** con ventana mínima entre ediciones.

- **Parámetro configurable:** `progress_edit_min_interval_seconds` (ej. `1.0`). No se envía más de una edición al mismo mensaje por ese intervalo.
- **Estrategia:** En el listener del bot que recibe `plan_progress`:
  - Mantener el **último evento** pendiente (step_index, step_id, label) y un **timestamp de la última edición** para ese mensaje.
  - Al llegar un evento: si han pasado ≥ `progress_edit_min_interval_seconds` desde la última edición, editar de inmediato con el estado actual (ej. "Paso 1 ✅ · Paso 2 ✅ · Paso 3: Lucifer sintetizando...").
  - Si no ha pasado el intervalo, **no editar aún**; marcar el evento como "último pendiente" y programar una **tarea diferida** (asyncio.sleep hasta completar el intervalo) que entonces edite con ese último estado (solo si no llegó ya un evento más reciente). Así se agrupan varios eventos rápidos en una sola edición.
- **Al final:** Cuando llega la respuesta HTTP o `plan_done`, se hace **una última edición** con el estado final (todos los pasos ✅) si hubo pendiente, y acto seguido se borra el placeholder o se reemplaza por la respuesta. No depender de "una edición por paso"; el usuario ve actualizaciones suaves sin topar el rate limit.

**Resumen:** Throttle por mensaje (mín. 1 edición por segundo o valor configurable); agrupar eventos rápidos en una sola edición; última actualización al terminar.

---

### 2. Ciclo de vida del WebSocket (multiplexación vs. efímero)

**Riesgo:** El bot debe recibir eventos por `request_id`. ¿Una conexión WS efímera por comando largo o una conexión persistente multiplexada?

**Decisión:** **Conexión WebSocket persistente (una por proceso del bot)** con multiplexación por `request_id`.

- **Motivos:**
  - Evitar abrir/cerrar WS por cada mensaje largo (overhead, posibles fallos de reconexión justo cuando llega el progreso).
  - El bot ya mantiene una sesión larga; reutilizar una sola conexión simplifica la lógica y el firewall/proxy.
  - Multiplexar por `request_id` es trivial: el servidor envía `{ "type": "plan_progress", "request_id": "...", ... }` y el cliente despacha al handler del `request_id` correspondiente (o ignora si ya terminó).
- **Implementación en el bot:**
  - Al arrancar (o al primer uso), abrir **una** conexión WS a la API (ej. `wss://.../ws/discord-progress` o canal dedicado en `/ws`).
  - Por cada mensaje que requiera feedback progresivo: generar `request_id`, registrar un **handler temporal** (asyncio.Queue o callback) para ese `request_id`, enviar `{ "action": "subscribe", "request_id": "..." }` por el WS existente, lanzar POST /chat con `X-Request-ID`, y la tarea que escucha el WS reenvía solo los eventos con ese `request_id` al handler.
  - Al recibir `plan_done` o al completar el HTTP, desregistrar el handler y dejar de encolar eventos para ese `request_id`.
- **Caída del WS:** Si la conexión se cierra (red, reinicio API), el bot puede reintentar con backoff y, para requests en curso, seguir mostrando solo el placeholder genérico hasta que el HTTP responda (degradación elegante).

**Resumen:** Un WS persistente por bot; suscripciones efímeras por `request_id` sobre ese canal; sin conexión WS nueva por comando.

---

### 3. Cruce de fronteras (sync → async)

**Riesgo:** El `progress_callback` se ejecuta en un **hilo de worker** (PlanExecutor / `asyncio.to_thread`). Si en el callback se hace `asyncio_queue.put_nowait(...)` desde ese hilo, se rompe la invariante de asyncio (solo el thread del event loop debe tocar el `asyncio.Queue`). Hace falta cruzar la frontera sync → async de forma segura.

**Decisión:** **`asyncio.run_coroutine_threadsafe(put(...), loop)` hacia un `asyncio.Queue` en el event loop.**

- **Flujo:**
  1. En el **handler que sirve el request** (FastAPI, ya en el event loop): se obtiene `loop = asyncio.get_running_loop()` y se crea un `asyncio.Queue` (o se usa un registro `request_id → asyncio.Queue`) que vive en ese loop.
  2. El **progress_callback** que se pasa a `execute_plan` se ejecuta en el **worker thread** (dentro de `asyncio.to_thread`). En ese callback **no** se debe llamar a `queue.put_nowait(...)` desde el worker (el `asyncio.Queue` no es thread-safe para escritura desde otro hilo). La forma correcta de cruzar la frontera es:
     - `asyncio.run_coroutine_threadsafe(queue.put(event), loop)`. Esto programa la coroutine `queue.put(event)` en el loop y devuelve un `concurrent.futures.Future`; el worker no debe hacer `.result()` para no bloquear. El evento (dict con request_id, step_index, step_id, label) se serializa en el worker y se consume en el loop.
  3. Una **tarea asyncio** en el mismo loop hace `await queue.get()` (o lee de la cola asociada al `request_id`) y, por cada evento, reenvía a los clientes WS suscritos a ese `request_id`.
- **Alternativa (válida pero con más piezas):** Usar `queue.Queue` (estándar, thread-safe) en el callback con `queue.put(event)` y un **hilo de fondo** o una tarea que haga `while True: event = sync_queue.get(); loop.call_soon_threadsafe(asyncio_queue.put_nowait, event)`. Funciona, pero añade un hilo o polling. `run_coroutine_threadsafe(queue.put(event), loop)` desde el worker evita ese hilo: el productor es el worker del PlanExecutor y el consumidor es una coroutine en el loop.
- **Detalle:** El callback debe recibir la referencia al `loop` y al `queue` (o al registro) al construirlo en el handler HTTP; no puede usar `asyncio.get_event_loop()` desde el worker (puede no ser el loop correcto). El handler que llama a `execute_plan` (desde una coroutine) tiene acceso al loop y crea el queue; pasa un closure o un objeto que encapsule `loop` y `queue` al callback.

**Resumen:** Callback en worker thread → `asyncio.run_coroutine_threadsafe(queue.put(event), loop)`; consumidor en el mismo loop con `await queue.get()`; sin tocar `asyncio.Queue` desde el worker directamente.

---

## Implementación: forma de los datos y ciclo de vida

### 1. Estructura del payload de progreso

**Decisión:** El servidor emite en cada tick el **estado completo del DAG** para ese request, no solo el paso actual. Así el bot puede renderizar "Paso 2/5: Lucifer sintetizando..." sin mantener estado propio y sin riesgo de desincronización.

**Forma del evento (JSON por WebSocket):**

```json
{
  "type": "plan_progress",
  "request_id": "550e8400-e29b-41d4-a716-446655440000",
  "total_steps": 5,
  "steps": [
    { "step_index": 0, "step_id": "0", "label": "Extrayendo lore", "status": "done" },
    { "step_index": 1, "step_id": "1", "label": "Extrayendo lore", "status": "done" },
    { "step_index": 2, "step_id": "aggregator", "label": "Lucifer sintetizando", "status": "running" }
  ],
  "current_step_index": 2,
  "current_step_id": "aggregator",
  "current_label": "Lucifer sintetizando",
  "status": "running"
}
```

- **`total_steps`:** Número total de pasos del plan (para "Paso X / total_steps").
- **`steps`:** Lista de todos los pasos conocidos hasta ese momento, cada uno con `step_index`, `step_id`, `label`, `status` (`"running"` | `"done"` | `"error"`). El último con `status: "running"` es el actual; los anteriores son `"done"`.
- **`current_*`:** Redundante pero cómodo para el bot (evita buscar en `steps` el que está en curso).
- **`status` (raíz):** `"running"` | `"done"` | `"error"`. Si es `"error"`, el payload incluirá `error_message` (ver *Manejo de errores*).

El **progress_callback** actual solo recibe `(step_index, step_id, label)` por paso. La API (consumidor de la cola) mantendrá en memoria, por `request_id`, la lista de pasos ya completados y el paso actual; al recibir cada evento del callback, construirá este payload completo y lo enviará por WS. Así el PlanExecutor no necesita conocer `total_steps` ni el historial; la capa HTTP/WS arma el estado completo.

**Evento de cierre:**

```json
{ "type": "plan_done", "request_id": "...", "status": "done" }
```

o en caso de error:

```json
{ "type": "plan_done", "request_id": "...", "status": "error", "error_message": "..." }
```

---

### 2. Ciclo de vida del request_id (cliente Discord)

**Decisión:** Generar **un solo** identificador por “comando largo” con la librería estándar y usarlo tanto en HTTP como en WebSocket.

- **Generación:** `request_id = uuid.uuid4().hex` (32 caracteres, sin guiones) o `str(uuid.uuid4())` si se prefiere UUID canónico. Documentar una sola forma en el protocolo (recomendado: `.hex` para cabeceras y URLs más cortas).
- **HTTP:** El bot envía la petición con `httpx.AsyncClient` añadiendo la cabecera `X-Request-ID: <request_id>` en el POST a `/api/discord/chat`.
- **WebSocket:** En el **mismo** flujo, **antes o justo después** de lanzar el POST, el bot envía por la conexión WS persistente el mensaje `{ "action": "subscribe", "request_id": "<request_id>" }` con el **mismo** valor. No generar un segundo UUID.
- **Orden sugerido:** (1) Generar `request_id`, (2) registrar el handler para ese `request_id` en el listener WS, (3) enviar `subscribe` por WS, (4) lanzar POST con `X-Request-ID`. Así la suscripción está activa antes de que el servidor pueda emitir el primer evento.

**Resumen:** Un único `uuid.uuid4().hex` por request; misma cadena en cabecera HTTP y en `subscribe` del WebSocket; suscripción WS antes o a la par del POST.

---

### 3. Manejo de errores en la frontera (fallo en ThreadPoolExecutor)

**Decisión:** El **progress_callback** (o la capa que lo envuelve en la API) debe emitir un **evento con `status: "error"`** por WebSocket cuando un paso falle de forma estrepitosa, para que el embed se ponga en rojo de inmediato. El error también viajará en la respuesta HTTP síncrona al terminar (código 500 y cuerpo con el mensaje); el WS no sustituye eso, solo mejora la UX.

- **Dónde detectar el fallo:** En el PlanExecutor, cuando un paso lanza excepción (ej. en el worker del ThreadPoolExecutor), además de escribir `_PLACEHOLDER_UNAVAILABLE` o de abortar el plan, se debe invocar el callback con un **evento de error** (o una variante del callback). Opciones:
  - **A)** Extender la firma del callback a algo como `(step_index, step_id, label, status="done"|"error", error_message=None)`. Si `status == "error"`, la API emite el payload completo con ese paso en `status: "error"` y `status` raíz `"error"`, y opcionalmente `plan_done` con `status: "error"`.
  - **B)** Mantener el callback actual y, en la API, al recibir la excepción de `asyncio.to_thread(execute_plan, ...)` (cuando el plan devuelve o lanza), emitir un último evento `plan_done` con `status: "error"` y el mensaje. El problema es que eso llega **al final**, no en el instante del fallo; el usuario no vería el paso concreto que falló hasta que termine el request.
- **Recomendación:** **A.** El PlanExecutor, al capturar la excepción de un paso (en el bucle de waves), antes de re-lanzar o devolver, llama a `progress_callback(step_index, step_id, label, status="error", error_message=str(e))`. La API traduce eso al payload completo con ese paso en rojo y envía `plan_done` con `status: "error"`. El bot puede pintar el embed en rojo y mostrar "Paso 3: &lt;label&gt; ❌" y el mensaje de error.

**Resumen:** Emitir por WS un evento de progreso con `status: "error"` (y opcionalmente `plan_done` con `status: "error"`) en el momento del fallo; la respuesta HTTP sigue siendo el canal de verdad para el cuerpo del error; el WS es para feedback visual inmediato.

---

## Referencias

- `Backend/core/plan_executor.py`: `run_plan(..., progress_callback=...)`, `_label_for_tool`.
- `Backend/core/orchestrator.py`: `execute_plan(..., progress_callback=...)`, `execute_steps(..., progress_callback=...)`.
- `Discord/handlers/chat_handler.py`: placeholder y espera HTTP; punto de integración del listener WS.
- `Backend/api/server.py`: WebSocket `/ws` y `route_ipc_to_websocket`; posible extensión para `plan_progress`.
