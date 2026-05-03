# 04 - Sistema de Herramientas V3

> **Versión:** 4.0  
> **Fecha:** 2026-03-21  
> **Ubicación:** `Lilith/Core/Backend/core/tools_v3/`

---

## 4.1 Infraestructura Base

### 4.1.1 Protocolo (`protocol.py`)

Define la interfaz abstracta para todas las tools:

```python
class LilithTool(ABC):
    @property
    @abstractmethod
    def name(self) -> str
    
    def get_description(self) -> str
    def get_parameters_schema(self) -> Dict
    def execute(self, params: Dict) -> ToolResult  # str | Dict
```

**ToolResult:** `Union[str, Dict[str, Any]]`

### 4.1.2 Base (`base.py`)

Implementación base usando atributos de clase:

```python
class ToolV3Base:
    name: str
    description: str
    
    def execute(params) -> ToolResult
```

### 4.1.3 Registry (`registry.py`)

Catálogo dinámico con **lazy loading**:

```python
class ToolRegistryV3:
    def register(tool: LilithTool)
    def register_lazy(name: str, factory: Callable)
    def get(name: str) -> Optional[LilithTool]
    def execute(name: str, params: Dict) -> ToolResult
    def list_tools() -> List[Dict]
    def has(name: str) -> bool
```

---

## 4.2 Tools de Sistema de Archivos

### 4.2.1 FileReadTool (`file_read_tool.py`)

**Nombre:** `read_file`

**Propósito:** Lee contenido de archivos con seguridad.

| Parámetro | Tipo | Descripción |
|-----------|------|-------------|
| `path` | string (req) | Ruta relativa al proyecto |
| `max_chars` | int | Límite de caracteres |
| `limit_lines` | int | Límite de líneas |

**Seguridad:** `SecurityGuard.check_path()`, `validate_path()`

---

### 4.2.2 FileEditTool (`file_edit_tool.py`)

**Nombre:** `edit_file`

**Propósito:** Edita archivos (reemplazar, escribir, insertar).

| Parámetro | Tipo | Descripción |
|-----------|------|-------------|
| `path` | string (req) | Ruta del archivo |
| `action` | enum | `edit` \| `write` \| `insert` |
| `target` | string | Texto a reemplazar |
| `replacement` | string | Nuevo texto |
| `content` | string | Contenido (write/insert) |
| `line_number` | int | Línea para insertar |

---

### 4.2.3 ListDirectoryTool (`list_directory_tool.py`)

**Nombre:** `list_directory`

| Parámetro | Tipo | Default | Descripción |
|-----------|------|---------|-------------|
| `path` | string | "." | Ruta a listar |
| `pattern` | string | - | Patrón glob (*.py) |

**Salida:** Formato con emojis (📁 carpetas, 📄 archivos)

---

### 4.2.4 GatherDirectoryTool (`gather_directory_tool.py`)

**Nombre:** `gather_directory`

**Propósito:** Recolecta contenido de múltiples archivos recursivamente.

| Parámetro | Tipo | Default | Descripción |
|-----------|------|---------|-------------|
| `path` | string | "Backend" | Ruta a recorrer |
| `max_chars` | int | 80,000 | Límite total |
| `max_files` | int | 100 | Máximo archivos |

**Extensiones soportadas:** `.py`, `.md`, `.txt`, `.json`, `.yml`, `.yaml`, `.toml`, `.ini`, `.cfg`, `.sh`, `.bat`, `.ps1`, `.html`, `.css`, `.js`, `.ts`, `.vue`, `.rs`, `.go`

---

## 4.3 Tools de Ejecución

### 4.3.1 ExecTool (`exec_tool.py`)

**Nombre:** `exec`

**Propósito:** Ejecuta comandos permitidos de forma segura.

**Características de seguridad:**
- Sin shell (`shell=False`)
- Recibe `argv` como lista
- Validación con `SecurityGuard.check_exec()`
- Timeout: 15s (default)
- Logs en `scratch/exec_logs/`

| Parámetro | Tipo | Descripción |
|-----------|------|-------------|
| `command_args` | list[str] | Argumentos (argv) |
| `cwd` | string | Directorio de trabajo |
| `tail_chars` | int | Caracteres de salida (max 12000) |

---

## 4.4 Tools de Búsqueda

### 4.4.1 WebSearchTool (`web_search_tool.py`)

**Nombre:** `web_search`

| Parámetro | Tipo | Default | Descripción |
|-----------|------|---------|-------------|
| `query` | string (req) | - | Texto a buscar |
| `max_results` | int | 5 | Máximo 5 |
| `blacklist` | list[str] | default | Dominios excluidos |

**Blacklist default:** youtube.com, youtu.be, pinterest.com, instagram.com, tiktok.com, facebook.com, x.com, twitter.com

---

### 4.4.2 LoreExtractorTool (`lore_extractor_tool.py`)

**Nombre:** `lore_extractor`

**Modos:**
- `mediawiki`: Artículos de Fandom/Wikis
- `reddit`: Hilos de Reddit vía API JSON

| Parámetro | Tipo | Descripción |
|-----------|------|-------------|
| `mode` | enum | `mediawiki` \| `reddit` |
| `url` | string | URL del hilo (Reddit) |
| `wiki_base` | string | Base URL del wiki |
| `title` | string | Título de la página |
| `store` | bool | Guardar en memoria (default true) |
| `max_reddit_comments` | int | Máximo comentarios (default 15) |
| `topic` | string | Taxonomía para memoria |

---

## 4.5 Tools de Memoria

### 4.5.1 MemoryTools (`memory_tools.py`)

Tres tools en uno:

#### SearchSemanticMemoryTool
**Nombre:** `search_semantic_memory`

| Parámetro | Tipo | Descripción |
|-----------|------|-------------|
| `query` | string (req) | Consulta de búsqueda |

#### StoreInteractionTool
**Nombre:** `store_interaction`

| Parámetro | Tipo | Descripción |
|-----------|------|-------------|
| `user_message` | string | Mensaje del usuario |
| `plan` | array | Plan ejecutado |
| `final_response` | string | Respuesta final |
| `outcome` | string | Resultado |
| `user_id` | string | ID del usuario |

#### StoreSemanticFactTool
**Nombre:** `store_semantic_fact`

| Parámetro | Tipo | Descripción |
|-----------|------|-------------|
| `fact` / `context` | string | Hecho a guardar |
| `source_id` | string | ID para chunking |
| `topic` | string | Dominio/taxonomía |

---

## 4.6 Tools de Delegación (Agentes)

### 4.6.1 AgentTools (`agent_tools.py`)

| Tool | Nombre | Agente | Modelo | Propósito |
|------|--------|--------|--------|-----------|
| DelegateEvaTool | `delegate_eva` | Eva | Grok | Análisis, documentación |
| DelegateAdanTool | `delegate_adan` | Adán | Qwen | Código, refactor |
| DelegateLuciferTool | `delegate_lucifer` | Lucifer/Odín | Kimi | Creativo |
| DelegateOdinTool | `delegate_odin` | Odín | Kimi 262k | Análisis masivo |
| DelegateLocalIrreverentTool | `delegate_local_irreverent` | Local | Ollama | Roasts |

**Parámetros comunes:**
| Parámetro | Tipo | Descripción |
|-----------|------|-------------|
| `task` | string (req) | Tarea específica |
| `context` | string | Contexto adicional |

**Personalidades:**
- **Eva:** Estratega militar, formato HALLAZGO/EVIDENCIA/RIESGOS/RECOMENDACIÓN
- **Adán:** Artesano del código, código en inglés
- **Lucifer:** Conocedor oscuro, erudito prohibido
- **Odín:** Padre del conocimiento, exhaustivo

---

### 4.6.2 ShalltearTool (`shalltear_tool.py`)

| Tool | Nombre | Propósito |
|------|--------|-----------|
| DelegateShalltearTool | `delegate_shalltear` | Clasificación, parsing NL |
| ShalltearParseTool | `shalltear_parse_pc` | Parsea NL a operaciones PC |

**Tareas de Shalltear:**
- `classify_intent`: Clasificar intenciones
- `parse_nl`: Parsing NL a JSON
- `score_importance`: Puntuar importancia
- `quick_answer`: Respuesta rápida

---

## 4.7 Tools de PC Agent

### 4.7.1 PCAgentTools (`pc_agent_tools.py`)

8 Tools de sistema para operaciones del owner:

| Tool | Nombre | Descripción | Confirma |
|------|--------|-------------|----------|
| PCListTool | `pc_list` | Lista carpeta | No |
| PCMkdirTool | `pc_mkdir` | Crea carpetas | No |
| PCMoveTool | `pc_move` | Mueve archivos | No |
| PCCopyTool | `pc_copy` | Copia archivos | No |
| PCDeleteTool | `pc_delete` | Elimina archivos | **Sí** |
| PCWriteFileTool | `pc_write_file` | Escribe archivos | No |
| PCExecTool | `pc_exec` | Ejecuta comandos | **Sí** |
| PCBatchTool | `pc_batch` | Múltiples operaciones | **Sí** |

**Aliases de rutas:** `proyectos`, `lilith`, `yggdrasil`, `desktop`, `downloads`, `documents`

---

## 4.8 Tools de CLI Externos

### 4.8.1 CursorCLITool (`cursor_cli_tool.py`)

**Nombre:** `delegate_cursor`

| Parámetro | Tipo | Descripción |
|-----------|------|-------------|
| `task` | string (req) | Tarea para Cursor |
| `context` | string | Contexto adicional |
| `allow_edits` | bool | Permitir modificaciones |

**Timeout:** 120s

---

### 4.8.2 KimiCLITool (`kimi_cli_tool.py`)

**Nombre:** `delegate_kimi_cli`

| Parámetro | Tipo | Descripción |
|-----------|------|-------------|
| `task` | string (req) | Tarea para Kimi |
| `context` | string | Contexto adicional |
| `model` | string | Modelo (moonshot-v1-128k) |

---

### 4.8.3 AlbedoCLITool (`albedo_cli_tool.py`)

**Nombre:** `delegate_albedo`

**Workspace:** `Workspace/Yggdrasil/Vanaheim/Albedo`

| Parámetro | Tipo | Descripción |
|-----------|------|-------------|
| `task` | string (req) | Misión para Albedo |
| `context` | string | Contexto adicional |

---

## 4.9 Tools de Respuesta y Diversión

### 4.9.1 GenerateReplyTool (`generate_reply_tool.py`)

**Nombre:** `generate_reply`

**Cadena de fallbacks:**
1. Grok (voz propia de Lilith) con persona desde `personas.json`
2. Odín (Kimi)
3. Albedo (local)

| Parámetro | Tipo | Descripción |
|-----------|------|-------------|
| `message` / `user_message` | string (req) | Mensaje del usuario |
| `context` | string | Contexto adicional |

---

### 4.9.2 FunTools (`fun_tools.py`)

| Tool | Nombre | Descripción |
|------|--------|-------------|
| ChisteTool | `chiste` | Cuenta un chiste |
| MemeTool | `meme` | Frase de meme |

**Seguridad:** Solo para usuarios Trusted.

---

## 4.10 Tools Avanzadas

### 4.10.1 SelfImproveTool (`self_improvement_tool.py`)

**Nombre:** `self_improve`

**Propósito:** Analiza memoria episódica para encontrar patrones.

| Parámetro | Tipo | Default | Descripción |
|-----------|------|---------|-------------|
| `limit` | int | 500 | Máximo interacciones (max 2000) |

---

### 4.10.2 ExecuteChainedTool (`chained_tool.py`)

**Nombre:** `execute_chained`

**Propósito:** Ejecuta secuencias definidas en `Config/chained_tools.json`.

| Parámetro | Tipo | Descripción |
|-----------|------|-------------|
| `chain_name` | string (req) | Nombre de la cadena |
| `path` | string | Ruta (placeholder) |
| `fact` | string | Hecho (placeholder) |

**Placeholders:** `{path}`, `{output_of_step_0}`, `{output_of_step_1}`...

---

### 4.10.3 YieldToAgentTool (`yield_tool.py`)

**Nombre:** `yield_to_agent`

**Propósito:** Pausa ejecución y delega subtarea (supervisor pattern).

| Parámetro | Tipo | Descripción |
|-----------|------|-------------|
| `target` | enum | Solo `"eva"` |
| `task_description` | string (req) | Instrucción imperativa |
| `context_payload` | string (req) | Formato/contexto exacto |

**Mecanismo:** Lanza `AgentYieldException` para reanudación.

---

### 4.10.4 OwnerSystemTool (`owner_system_tool.py`)

**Nombre:** `owner_system_action`

| Parámetro | Tipo | Default | Descripción |
|-----------|------|---------|-------------|
| `action` | enum | req | `shutdown` \| `restart` \| `lock` |
| `delay_seconds` | int | 60 | Retraso |

**Whitelist:** `Config/security.json` → `owner_system_actions`

---

### 4.10.5 ProjectTool (`project_tool.py`)

**Nombre:** `project`

**Acciones:**
| Acción | Descripción |
|--------|-------------|
| `create` | Crear proyecto |
| `list` | Listar proyectos |
| `status` | Ver estado |
| `add_task` | Añadir tarea |
| `advance` | Siguiente tarea pendiente |

---

## 4.11 Tools de Browser (V4)

### 4.11.1 BrowserTools (`tools_v4_os_control/`)

| Tool | Nombre | Descripción |
|------|--------|-------------|
| BrowserGotoTool | `browser_goto` | Navegar a URL |
| BrowserClickTool | `browser_click` | Click en elemento |
| BrowserFillTool | `browser_fill` | Rellenar campo |
| BrowserScrollTool | `browser_scroll` | Scroll página |
| BrowserExtractTool | `browser_extract` | Extraer contenido |

---

## 4.12 Registro de Tools

### 4.12.1 Registro Completo

30+ tools registradas con lazy loading:

**Categorías:**
- **Filesystem:** `read_file`, `edit_file`, `list_directory`, `gather_directory`
- **Ejecución:** `exec`
- **Búsqueda:** `web_search`, `lore_extractor`
- **Memoria:** `search_semantic_memory`, `store_interaction`, `store_semantic_fact`
- **Delegación:** `delegate_eva`, `delegate_adan`, `delegate_lucifer`, `delegate_odin`, `delegate_shalltear`, `delegate_local_irreverent`, `delegate_cursor`, `delegate_kimi_cli`, `delegate_albedo`
- **PC Agent:** `pc_list`, `pc_mkdir`, `pc_move`, `pc_copy`, `pc_delete`, `pc_write_file`, `pc_exec`, `pc_batch`
- **Sistema:** `owner_system_action`, `project`, `self_improve`, `execute_chained`, `yield_to_agent`
- **Browser:** `browser_goto`, `browser_click`, `browser_fill`, `browser_scroll`, `browser_extract`
- **Respuesta:** `generate_reply`, `chiste`, `meme`, `shalltear_parse_pc`

### 4.12.2 Registro Limitado (Trusted)

Solo para usuarios Trusted:
- `generate_reply`
- `chiste`
- `meme`

---

## 4.13 Seguridad Integrada

| Mecanismo | Descripción |
|-----------|-------------|
| `SecurityGuard` | Validación de permisos |
| `validate_path` | Sanitización de rutas |
| `validate_instruction` | Prevención de inyección |
| `sanitize_input` | Limpieza de inputs |
| Confirmación | Requerida para operaciones destructivas |
| Allowlist | Comandos permitidos |
| Blacklist | Dominios bloqueados |

---

*Documento 04 del índice de documentación de Lilith*
