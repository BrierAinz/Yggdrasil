# Agencia Web V1 — Browser Tool con Playwright

Documentación del subsistema de navegación web de Lilith: motor headless (Playwright + Chromium), herramientas en ToolRegistryV3 y manual para el operador (Adán/Eva).

---

## 1. Objetivo

Permitir que el planificador ejecute tareas de navegación web de forma **síncrona** (desde el hilo del API) usando un navegador persistente: ir a una URL, hacer clic o rellenar campos identificados por `action_id`, desplazar el viewport y extraer contenido en markdown para el LLM.

---

## 2. Arquitectura

```
┌─────────────────────────────────────────────────────────────────┐
│  FastAPI lifespan                                                │
│  → BrowserEngine().start()  (Playwright + Chromium persistente)   │
└─────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────┐
│  BrowserEngine (singleton)                                        │
│  - _page (Playwright), _loop (asyncio)                           │
│  - goto(url), click(action_id), fill(action_id, text), scroll()   │
│  - _get_current_state(include_markdown) → BrowserState           │
└─────────────────────────────────────────────────────────────────┘
                                    │
        ┌───────────────────────────┼───────────────────────────┐
        ▼                           ▼                           ▼
  dom_tagger.js              distiller.py                 browser_tool.py
  (inyectado en página)       (Readability +               (5 tools ToolV3)
  → actions_tree, meta        markdownify)                 → _run_on_engine()
                              → content_markdown
```

- **Motor**: un solo `BrowserEngine` por proceso; se inicia en el `_lifespan` de `Backend/api/server.py` y se detiene al cerrar la app.
- **Tools**: ejecutan corutinas del engine vía `asyncio.run_coroutine_threadsafe(..., engine.loop)` con timeouts; si el engine no está inicializado, devuelven `browser_engine_not_initialized`.
- **Registro**: las 5 tools están en `ToolRegistryV3` (lazy) en `Backend/core/tools_v3/__init__.py` → `create_default_registry()`.

---

## 3. BrowserState

Objeto devuelto por `goto`, `click`, `scroll` (y por `_get_current_state`). Estructura:

| Campo | Tipo | Descripción |
|-------|------|-------------|
| `page_id` | string | Siempre `"v1-single-tab"` en esta versión. |
| `current_url` | string | URL actual de la pestaña. |
| `title` | string | Título de la página (`<title>`). |
| `meta` | object | Ver sección 3.1. |
| `actions_tree` | array | Lista de elementos interactivos; ver sección 3.2. |
| `content_markdown` | string | Solo presente si se pidió (p. ej. en `goto`); contenido destilado en markdown. |

### 3.1. meta (viewport)

Generado por `dom_tagger.js`:

- `viewport_position`: `"top"` | `"middle"` | `"bottom"`
- `can_scroll_down`: boolean
- `can_scroll_up`: boolean

### 3.2. actions_tree

Cada elemento es un objeto con:

- `id`: entero → **action_id** para `browser_click` y `browser_fill`.
- `role`: tag en minúsculas (`a`, `button`, `input`, etc.).
- `type`: para inputs, tipo HTML (`text`, `submit`, etc.) o `undefined`.
- `text`: texto visible, `value`, `placeholder`, `aria-label` o `alt` (recortado a 80 caracteres), o `"[Icono/Vacío]"`.

Solo se incluyen elementos **visibles** en viewport (con margen); cada uno tiene en el DOM el atributo `lilith-id="{id}"` para que Playwright haga `click`/`fill` con el selector `[lilith-id="{id}"]`.

---

## 4. Herramientas (tools)

Todas son herramientas ToolV3 (LilithTool), registradas por nombre en el ToolRegistryV3.

### 4.1. browser_goto

- **Descripción**: Navega a una URL y devuelve el estado de la página (acciones y contenido).
- **Parámetros**: `url` (string, obligatorio).
- **Respuesta**: BrowserState con `content_markdown`.
- **Errores**: `missing_param`, `browser_engine_not_initialized`, `navigation_failed`, `timeout` (20 s).

### 4.2. browser_click

- **Descripción**: Hace clic en un elemento usando su `action_id`.
- **Parámetros**: `action_id` (entero, obligatorio).
- **Respuesta**: BrowserState (sin markdown por defecto) o error.
- **Errores**: `missing_param`, `invalid_param` (action_id no entero), `browser_engine_not_initialized`, `element_blocked` (overlay/modal), `click_failed`, `timeout` (15 s).

### 4.3. browser_fill

- **Descripción**: Escribe texto en un campo identificado por `action_id`.
- **Parámetros**: `action_id` (entero), `text` (string).
- **Respuesta**: `{"status": "filled_success", ...}` o `fill_failed`, `timeout` (10 s).

### 4.4. browser_scroll

- **Descripción**: Desplaza el viewport hacia arriba o abajo y devuelve el nuevo estado.
- **Parámetros**: `direction` (opcional): `"down"` | `"up"` (default `"down"`).
- **Respuesta**: BrowserState sin markdown.
- **Errores**: `browser_engine_not_initialized`, `timeout` (10 s).

### 4.5. browser_extract

- **Descripción**: Extrae fragmentos de texto del `content_markdown` según una query (heurística por líneas).
- **Parámetros**: `content_markdown` (string), `query` (string o lista de palabras).
- **Respuesta**: `{"found": true|false, "extracted_data": "...", "hint": "..."}`.  
  Hints: `no_query_or_content`, `no_match_in_viewport`.
- **Nota**: No usa el motor de navegador; opera sobre el texto ya obtenido (p. ej. tras `browser_goto`).

---

## 5. Flujo típico

1. **browser_goto(url)** → se obtiene `current_url`, `title`, `content_markdown`, `actions_tree`, `meta`.
2. El agente lee `content_markdown` y `actions_tree` para decidir el siguiente paso.
3. Para abrir un enlace o pulsar un botón: **browser_click(action_id)** con un `id` tomado de `actions_tree`.
4. Si el contenido buscado no está visible: **browser_scroll(direction)** y, si hace falta, volver a obtener estado/contenido (p. ej. otro goto no necesario; el estado lo devuelve ya `click`/`scroll`).
5. Para extraer datos concretos del markdown: **browser_extract(content_markdown, query)**.
6. Si aparece **element_blocked**: intentar scroll, cerrar modal o elegir otro elemento. Si **no_match_in_viewport**: scroll o refinar la query en `browser_extract`.

---

## 6. Errores comunes

| Código / Situación | Significado | Acción sugerida |
|--------------------|-------------|------------------|
| `browser_engine_not_initialized` | API no ha arrancado el motor o se cerró. | Asegurar que el servidor está en marcha (lifespan). |
| `missing_param` | Falta `url` o `action_id` según la tool. | Incluir el parámetro en la llamada. |
| `invalid_param` | `action_id` no es entero. | Pasar el entero que viene en `actions_tree[].id`. |
| `element_blocked` | Elemento tapado (overlay, modal, banner). | Scroll, cerrar modal o usar otro action_id. |
| `no_match_in_viewport` | `browser_extract` no encontró la query en el texto. | Scroll para cargar más contenido o ampliar/refinar la query. |
| `timeout` | La operación excedió el tiempo límite. | Reintentar o simplificar la página/acción. |
| `navigation_failed` | Fallo en `goto` (red, DNS, etc.). | Comprobar URL y conectividad. |

---

## 7. Ejemplo validado: Hacker News → primer titular → GitHub

Secuencia ejecutada con éxito en producción:

1. **browser_goto** → `https://news.ycombinator.com/`  
   - Se carga la portada; en `actions_tree` aparecen enlaces (titulares, comentarios, etc.) con sus `id`.
2. **browser_click** → `action_id` del primer titular (enlace principal del primer post).  
   - Navegación a la página destino (en el ejemplo, repositorio en GitHub).
3. **browser_extract** (o lectura directa del `content_markdown` devuelto tras el clic) → título y resumen del proyecto.  
   - Ejemplo: "Turntable Calibration Tool" — herramienta open-source para calibrar tocadiscos vía audio y análisis de señal.

No fue necesario `browser_scroll` ni `browser_fill`; el primer enlace estaba en viewport.

---

## 8. Dependencias y arranque

- **Python**: `playwright`, `readability-lxml`, `markdownify` (en `Core/requirements.txt`).
- **Chromium**: `python -m playwright install chromium` (una vez por entorno).
- **Arranque**: el motor se inicia en el lifespan de `Backend/api/server.py`; no hace falta añadir nada a `arranque_lilith.bat` (la API ya levanta el engine).

Rutas relevantes:

- Motor y tools: `Backend/core/tools_v4_os_control/`  
  - `browser_engine.py`, `browser_tool.py`, `dom_tagger.js`, `distiller.py`
- Registro: `Backend/core/tools_v3/__init__.py` (`create_default_registry`).
- Manual en prompts: `Backend/core/agents/adan_agent.py`, `Backend/core/agents/eva_agent.py` (sección "Herramientas de navegación web (BrowserTool)").
- Tests: `Tests/test_browser_tools_v4.py`.

---

## 9. Manual del operador (inyectado en Adán/Eva)

El siguiente bloque se inyecta en el system prompt de Adán y Eva para que usen correctamente las tools:

- **BrowserState** incluye: `current_url`, `title`, `content_markdown`, `actions_tree`, `meta`.
- **Flujo**: `browser_goto(url)` → leer `content_markdown` y `actions_tree` → usar `action_id` en `browser_click` y `browser_fill`.
- **action_id**: entero de `actions_tree`; identificar el elemento (enlace, botón, input) por su `id` y texto.
- Si no está visible: `browser_scroll("down"|"up")` y volver a extraer/leer.
- **Errores**: `element_blocked` → scroll o otra acción; `no_match_in_viewport` → scroll o refinar query en `browser_extract`.

Versión completa en los propios archivos de agente (`adan_agent.py`, `eva_agent.py`).
