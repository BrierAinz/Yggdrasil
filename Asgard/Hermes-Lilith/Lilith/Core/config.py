# Lilith Configuration
# ===================
# Este archivo configura la conexion a LM Studio y comportamiento del agente.
# Para cambiar el modelo, modifica DEFAULT_MODEL o dejalo en "auto" para detectar.
#
# Ahora delega a LilithConfig (TOML) como fuente unica de verdad.
# Las constantes existentes se mantienen para retro-compatibilidad.

import os
from pathlib import Path

# Cargar .env si existe (API keys, configuracion local)
try:
    from dotenv import load_dotenv

    _PROJECT_ROOT = Path(__file__).parent.parent.parent
    _env_file = _PROJECT_ROOT / ".env"
    if _env_file.exists():
        load_dotenv(_env_file)
except ImportError:
    pass

# Detectar ruta base del proyecto (para rutas relativas)
if "_PROJECT_ROOT" not in dir():
    _PROJECT_ROOT = Path(__file__).parent.parent.parent

# ─── Configuracion TOML Unificada ───────────────────────────────────────────────
# El grimorio es la fuente de verdad. Las constantes abajo se derivan de el.
# Prioridad: TOML file > env vars > defaults

from Lilith.Core.toml_config import LilithConfig, get_config

_config = get_config()

# ─── Constantes publicas (retro-compatibilidad) ─────────────────────────────────
# Estas constantes siguen siendo la API publica del modulo.
# Ahora se alimentan del grimorio TOML en vez de estar hardcoded.

# LM Studio Connection
LM_STUDIO_URL = _config.get(
    "llm.providers.lm_studio.base_url", "http://localhost:1234/v1"
)

# Modelo por defecto
DEFAULT_MODEL = _config.get("llm.default_model", "auto")


# LLM Providers
def _build_llm_providers() -> list:
    """Construye la lista de providers desde el config TOML."""
    providers_data = _config.get("llm.providers", {})
    result = []
    for name, pdata in providers_data.items():
        result.append(
            {
                "name": name,
                "type": pdata.get("type", "local"),
                "base_url": pdata.get("base_url", ""),
                "model": pdata.get("model", "auto"),
                "api_key": pdata.get("api_key") or None,
            }
        )
    return result


LLM_PROVIDERS = _build_llm_providers()

# Provider activo
LLM_PROVIDER = _config.get("llm.default_provider", "auto")

# Chat Settings
MAX_HISTORY_MESSAGES = _config.get("chat.max_history", 50)

# System Prompt
SYSTEM_PROMPT = f"""Eres LILITH, una asistente AI avanzada con personalidad propia.

## QUIEN SOY
- Soy tu asistente personal en esta PC
- Tengo acceso a herramientas para controlar tu sistema
- Estoy aqui para hacerte la vida mas facil
- Aprendo de cada tarea que hacemos juntos

## MI PERSONALIDAD
- Soy directa y clara en mis respuestas
- Si no puedo hacer algo, te lo digo honestamente
- Me gusta ser util y proactiva
- A veces agrego comentarios utiles
- Estoy aqui para ayudarte, no solo para obedecer

## HERRAMIENTAS DISPONIBLES
Tengo acceso a estas herramientas:

### Control de PC
- screenshot: Tomar captura de pantalla
- get_cursor_position: Ver posicion del mouse
- list_windows: Ver ventanas abiertas

### Sistema de Archivos
- read_file(path): Leer archivo de texto
- write_file(path, content): Crear/modificar archivo
- list_directory(path): Ver contenido de carpeta (SOLO 1 nivel)
- file_exists(path): Verificar si existe archivo

### Comandos de Sistema
- run_terminal(command): Ejecutar comando PowerShell
- open_vscode(path): Abrir VS Code en carpeta
- open_application(app): Abrir aplicacion

### Coding
- run_git(command): Comandos git
- search_in_files(path, query): Buscar en archivos

### Red
- ping(host): Hacer ping
- check_internet(): Verificar conexion

## REGLAS CRITICAS DE USO DE HERRAMIENTAS

### list_directory: SOLO UN NIVEL
❌ NO llames list_directory varias veces en subcarpetas
✅ Para explorar, usa list_directory UNA VEZ en la carpeta raiz
✅ Si el usuario quiere ver subcarpetas, pregunta primero

### Despues de usar tools:
❌ NO repitas la misma herramienta multiples veces
✅ Resume los resultados y da tu respuesta final

### Resumenes:
✅ Cuando explores carpetas, DA UN RESUMEN, no listes todo
✅ Estructura la informacion de forma util

## COMO TRABAJO
1. Analizo tu solicitud
2. Decido si necesito herramientas (generalmente NO para resumenes simples)
3. Si uso herramientas, las uso con inteligencia
4. Te doy respuesta clara y util

## REGLAS IMPORTANTES
- Si no sabes algo, di que no lo sabes
- Para explorar carpetas, explora UN NIVEL y resume
- No hagas loops infinitos de herramientas
- Si la respuesta esta en el contexto, NO uses herramientas

## ESTILO DE RESPUESTA
- Directa y util
- Breve pero completa
- Incluyo contexto cuando es necesario
- Si algo sale mal, te explico que paso

¡Estoy lista para ayudarte! ¿Que necesitas?
"""

# Tool Settings
TOOL_TIMEOUT = _config.get("tools.timeout", 60)
MAX_TOOL_CALLS = _config.get("tools.max_calls", 25)

# Memory Settings
MEMORY_DIR = _config.get("memory.dir", str(_PROJECT_ROOT / "memory"))
SAVE_HISTORY = _config.get("memory.save_history", True)

# Paths
WORKSPACE = _config.get("workspace.dir", "D:\\Proyectos\\Midgard")
PROJECTS_DIR = _config.get("workspace.projects_dir", "D:\\Proyectos")

# Logging
LOG_LEVEL = _config.get("logging.level", "INFO")
LOG_FILE = _config.get("logging.file", str(_PROJECT_ROOT / "logs" / "lilith.log"))

# Skills Settings
SKILLS_DIR = Path(_config.get("skills.dir", str(Path.home() / ".lilith" / "skills")))
SKILLS_HOT_RELOAD = _config.get("skills.hot_reload", True)
SKILLS_AUTO_TRIGGER = _config.get("skills.auto_trigger", True)
SKILLS_MAX_TRIGGERED = _config.get("skills.max_triggered", 3)

# ─── Config Reload Helper ───────────────────────────────────────────────────────
# Permite recargar la config desde TOML (para hot-reload o cambios en runtime)


def reload_config() -> None:
    """Recarga la configuracion desde el grimorio TOML.

    Actualiza las constantes del modulo para reflejar los cambios.
    Nota: algunas constantes son inmutables si ya fueron importadas
    por otros modulos. Usar get_config().get() para valores dinamicos.
    """
    global LM_STUDIO_URL, DEFAULT_MODEL, LLM_PROVIDERS, LLM_PROVIDER
    global MAX_HISTORY_MESSAGES, SYSTEM_PROMPT
    global TOOL_TIMEOUT, MAX_TOOL_CALLS
    global MEMORY_DIR, SAVE_HISTORY, WORKSPACE, PROJECTS_DIR
    global LOG_LEVEL, LOG_FILE
    global SKILLS_DIR, SKILLS_HOT_RELOAD, SKILLS_AUTO_TRIGGER, SKILLS_MAX_TRIGGERED

    _config.reload()

    LM_STUDIO_URL = _config.get(
        "llm.providers.lm_studio.base_url", "http://localhost:1234/v1"
    )
    DEFAULT_MODEL = _config.get("llm.default_model", "auto")
    LLM_PROVIDERS = _build_llm_providers()
    LLM_PROVIDER = _config.get("llm.default_provider", "auto")
    MAX_HISTORY_MESSAGES = _config.get("chat.max_history", 50)
    TOOL_TIMEOUT = _config.get("tools.timeout", 60)
    MAX_TOOL_CALLS = _config.get("tools.max_calls", 25)
    MEMORY_DIR = _config.get("memory.dir", str(_PROJECT_ROOT / "memory"))
    SAVE_HISTORY = _config.get("memory.save_history", True)
    WORKSPACE = _config.get("workspace.dir", "D:\\Proyectos\\Midgard")
    PROJECTS_DIR = _config.get("workspace.projects_dir", "D:\\Proyectos")
    LOG_LEVEL = _config.get("logging.level", "INFO")
    LOG_FILE = _config.get("logging.file", str(_PROJECT_ROOT / "logs" / "lilith.log"))
    SKILLS_DIR = Path(
        _config.get("skills.dir", str(Path.home() / ".lilith" / "skills"))
    )
    SKILLS_HOT_RELOAD = _config.get("skills.hot_reload", True)
    SKILLS_AUTO_TRIGGER = _config.get("skills.auto_trigger", True)
    SKILLS_MAX_TRIGGERED = _config.get("skills.max_triggered", 3)
