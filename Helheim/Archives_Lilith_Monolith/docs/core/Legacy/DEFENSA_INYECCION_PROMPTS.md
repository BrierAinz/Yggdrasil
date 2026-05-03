# Plan de Defensa contra Inyección de Prompts

Estrategia en tres capas: **Validación de Entrada**, **Aislamiento de la Ejecución** y **Sanitización de la Salida**.

---

## Capa 1: Validación de Entrada (El Guardián del Portal) — IMPLEMENTADA

### 1.1 Sanitización básica de input
- **Archivo:** `Backend/core/input_sanitizer.py`
- **Función:** `sanitize_input(text, max_len=None)`  
  - Elimina caracteres de control (`\x00-\x08`, `\x0B`, `\x0C`, `\x0E-\x1F`, `\x7F`).  
  - Limita longitud (por defecto 4000; configurable en `Config/security.json` → `max_input_length`).
- **Integración:** Se llama en el primer punto de entrada del chat (`POST /api/discord/chat` en `discord_api.py`) y en el objetivo de `/auto`.

### 1.2 Validación de parámetros de tools
- **FileReadTool** y **FileEditTool** validan antes de ejecutar:
  - **Path:** sin `..`, sin rutas absolutas con `/`, sin segmentos en `forbidden_paths` y con extensión en `allowed_file_extensions` (si tiene extensión).
  - **Instrucción / target / replacement / content:** sin cadenas de `forbidden_commands_in_instruction` (ej. `rm -rf`, `sudo`, `pip install`, `| bash`, etc.).
- Si la validación falla, la tool devuelve error y no ejecuta.

### 1.3 Listas blancas y negras
- **Archivo:** `Config/security.json`
- **Claves:**
  - `max_input_length`: longitud máxima del input de chat (número).
  - `allowed_file_extensions`: extensiones permitidas para read/edit (lista).
  - `forbidden_paths`: segmentos de ruta prohibidos.
  - `forbidden_commands_in_instruction`: subcadenas prohibidas en instrucciones de edición.
  - `allowed_domains`: **lista blanca para HTTP**. Si está vacía o no existe, se permiten todos los dominios; si tiene entradas (ej. `["api.example.com", "docs.example.com"]`), los plugins web (p. ej. WebBrowser) solo pueden conectarse a esos dominios o subdominios.
- Las tools de archivos y el WebBrowser cargan este JSON y usan estas listas.

---

## Capa 2: Aislamiento de la Ejecución (La Caja de Arena) — RECOMENDACIONES

### 2.1 Sandboxing de plugins
- **Plugins web:** Implementado en `WebBrowser`: si `Config/security.json` tiene `allowed_domains` con entradas, solo se permiten esas URLs (o subdominios). Si está vacío, se permiten todos. `Backend.core.input_sanitizer.validate_http_url(url)` hace la comprobación.
- **Plugins del sistema:** **CursorCLITool** ya usa `subprocess.run(..., shell=False)` con lista de argumentos. Además, `task` y `context` se sanitizan con `sanitize_input` y se validan con `validate_instruction` (misma lista que en edit_file); el prompt total se limita a 8000 caracteres. No usar nunca `shell=True`.
- **Plugins de archivos:** El `FileManager` y las tools de archivos deben operar **siempre dentro del directorio raíz del proyecto** (p. ej. `Workspace/` o la raíz de Lilith). Las validaciones de path (Capa 1) impiden escapar de ese árbol.

### 2.2 Limitación de permisos del proceso
- Ejecutar la API de Lilith con un **usuario del sistema con mínimos privilegios** (no root ni administrador). Así, si un atacante llegara a ejecutar un comando, el alcance quedaría limitado por el sistema operativo.

---

## Capa 3: Sanitización de la Salida (El Último Filtro) — REGLA DE ORO

### 3.1 Nunca confiar en el código generado
- **Regla:** No ejecutar código que venga directamente de un LLM sin revisión humana.
- **Flujo recomendado:**  
  1. El agente (p. ej. Adán) genera el código.  
  2. Lilith muestra el código en Discord (o en otra interfaz).  
  3. El operador lo revisa.  
  4. El operador ejecuta una acción explícita (p. ej. comando tipo “aplicar código” o edición manual) que **lee** el código y lo aplica.  
- El paso 3 es la validación humana; no debe omitirse para acciones destructivas o en producción.

### 3.2 Escape de salida en web
- Si en el futuro se añade una interfaz web, todo texto que provenga de Lilith debe mostrarse con **escape de HTML** para evitar XSS. Frameworks como Flask o FastAPI suelen escapar por defecto en plantillas; comprobar que no se use `| safe` o equivalentes con contenido de agentes sin sanitizar.

---

## Resumen de archivos tocados

| Archivo | Uso |
|--------|-----|
| `Backend/core/input_sanitizer.py` | `sanitize_input`, `validate_path`, `validate_instruction`, carga de `security.json` |
| `Config/security.json` | Listas blancas/negras y `max_input_length` |
| `Backend/core/tools_v3/file_read_tool.py` | Validación de `path` antes de leer |
| `Backend/core/tools_v3/file_edit_tool.py` | Validación de `path` e instrucción/target/replacement/content |
| `Backend/core/tools_v3/cursor_cli_tool.py` | `sanitize_input` y `validate_instruction` en task/context; límite 8000 chars; subprocess sin shell |
| `Backend/core/input_sanitizer.py` | `validate_http_url(url)` para lista blanca de dominios |
| `Backend/tools/autonomous/web_browser.py` | Uso de `validate_http_url` en `_validate_url` (lista blanca `allowed_domains`) |
| `Backend/api/discord_api.py` | Llamada a `sanitize_input` en el body del chat y en el objetivo de `/auto` |
