"""
Error Handler System
====================
Manejo global de errores para Lilith v3.

Los Norns conocen cada hilo del destino — aqui registramos los fallos
del Yggdrasil para que ni el caos de Muspelheim pueda derrumbar el sistema.
Excepciones no capturadas se archivan en la memory de errores, y los
mensajes al usuario llevan la estetica oscura de siempre.
"""

import re
import sys
import traceback
from typing import Optional

from Lilith.Core.lilith_logger import get_logger

logger = get_logger("lilith.error_handler")

# ─── Jerarquia de Errores ──────────────────────────────────────────────────────

class LilithError(Exception):
    """Base para errores de Lilith.

    Toda sombra que cae sobre el Yggdrasil desciende de esta raiz.
    """
    pass


class ProviderError(LilithError):
    """Error de LLM provider.

    Cuando los afluentes del Bifrost fallan, este error informa
    cual de los nueve caminos se ha cerrado.

    Attributes:
        provider: Nombre del provider que fallo.
        status_code: Codigo HTTP del error, si aplica.
    """

    def __init__(self, provider: str, message: str, status_code: Optional[int] = None):
        self.provider = provider
        self.status_code = status_code
        super().__init__(f"[{provider}] {message}" + (f" (HTTP {status_code})" if status_code else ""))


class ToolError(LilithError):
    """Error en ejecucion de tool.

    Cuando una de las herramientas forjadas por los enanos falla,
    este error captura tanto el nombre del artefacto como la
    naturaleza de la falla.

    Attributes:
        tool_name: Nombre de la tool que fallo.
        original_error: Excepcion original que causo el fallo.
    """

    def __init__(self, tool_name: str, message: str, original_error: Optional[Exception] = None):
        self.tool_name = tool_name
        self.original_error = original_error
        detail = f" (caused by: {type(original_error).__name__}: {original_error})" if original_error else ""
        super().__init__(f"[Tool:{tool_name}] {message}{detail}")


class MemoryError(LilithError):
    """Error en el sistema de memoria.

    Cuando las runas grabadas en las raices del Yggdrasil se erosionan,
    este error marca el punto de olvido.
    """
    pass


class ConfigError(LilithError):
    """Error en la configuracion del grimorio.

    Cuando el libro de hechizos tiene paginas ilegibles o runas
    corruptas, este error se alza como centinela.
    """
    pass


# ─── Patrones de Sanitizacion ──────────────────────────────────────────────────────

_SENSITIVE_PATTERNS = [
    # API keys en headers de autorizacion
    (re.compile(r'(Authorization["\s:=]+)\S+', re.IGNORECASE), r'\1[REDACTED]'),
    (re.compile(r'(Bearer\s+)\S+', re.IGNORECASE), r'\1[REDACTED]'),
    (re.compile(r'(api[_-]?key["\s:=]+)\S+', re.IGNORECASE), r'\1[REDACTED]'),
    (re.compile(r'(apikey["\s:=]+)\S+', re.IGNORECASE), r'\1[REDACTED]'),
    # Tokens de servicios conocidos (ótimo 8+ chars para cubrir test y real)
    (re.compile(r'\bsk-[a-zA-Z0-9_-]{4,}\b'), r'[REDACTED_TOKEN]'),
    (re.compile(r'\bghp_[a-zA-Z0-9]{4,}\b'), r'[REDACTED_TOKEN]'),
    (re.compile(r'\bglpat-[a-zA-Z0-9]{4,}\b'), r'[REDACTED_TOKEN]'),
    # URLs con credenciales embebidas
    (re.compile(r'://([^:@\s]+):([^@\s]+)@'), r'://[REDACTED_USER]:[REDACTED_PASS]@'),
    # Emails — no es dato ultra-sensitivo pero sanitizar por seguridad
    (re.compile(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'), r'[REDACTED_EMAIL]'),
    # API keys en query params o JSON
    (re.compile(r'(["\']*(?:api[_-]?key|token|secret|password)["\']*\s*[:=]\s*["\']?)(\S{8,})', re.IGNORECASE), r'\1[REDACTED]'),
]


def sanitize_output(text: str) -> str:
    """Remueve API keys, tokens y datos sensibles del output.

    Los Norns tejen velos sobre los secretos del Yggdrasil — esta funcion
    asegura que ningun token escapable permanezca visible en el texto que
    cruza el Bifrost hacia el usuario.

    Patrones sanitizados:
    - Authorization headers (Bearer xxx)
    - api_key=xxx, token=xxx, password=xxx
    - Token patterns (sk-*, ghp_*, glpat-*)
    - URLs con credenciales embebidas (user:pass@host)
    - Email addresses
    - JSON/query params con valores sensibles

    Args:
        text: Texto potencialmente con datos sensibles.

    Returns:
        Texto con datos sensibles reemplazados por [REDACTED].
    """
    if text is None:
        return ""
    if not isinstance(text, str):
        text = str(text)
    result = text
    for pattern, replacement in _SENSITIVE_PATTERNS:
        result = pattern.sub(replacement, result)
    return result


# ─── Mensajes Dark Fantasy ──────────────────────────────────────────────────────────

_DARK_FANTASY_MESSAGES = {
    "ConnectionError": "Las raices del Yggdrasil no alcanzan ese reino — conexion fallida.",
    "TimeoutError": "El Bifrost se ha oscurecido — la conexion agoto su tiempo.",
    "ProviderError": "Los dioses de este camino no responden — error del provider.",
    "ToolError": "El artefacto forjado se ha roto — error en la herramienta.",
    "MemoryError": "Las runas se han erosionado — error en el sistema de memoria.",
    "ConfigError": "El grimorio tiene paginas corruptas — error de configuracion.",
    "PermissionError": "Las puertas de Asgard permanecen selladas — permiso denegado.",
    "FileNotFoundError": "El pergamino no existe en los archivos del Yggdrasil.",
    "default": "Una sombra se ha cruzado en el camino — error inesperado.",
}


def format_error(error: Exception, context: str = "") -> str:
    """Formatea errores para display al usuario.

    Muestra un mensaje limpio con estetica dark fantasy, sin exponer
    tracebacks internos. Registra el traceback completo en el logger
    para que los Nords puedan diagnosticar los problemas.

    Args:
        error: La excepcion a formatear.
        context: Contexto adicional (ej: nombre del provider, tool).

    Returns:
        Mensaje formateado para mostrar al usuario.
    """
    error_type = type(error).__name__
    error_message = str(error)

    # Buscar mensaje dark fantasy para el tipo de error
    dark_message = _DARK_FANTASY_MESSAGES.get(
        error_type,
        _DARK_FANTASY_MESSAGES["default"],
    )

    # Construir mensaje para el usuario
    parts = [f"⚠ {dark_message}"]
    if context:
        parts.append(f"  Contexto: {context}")
    parts.append(f"  Detalle: {error_message[:200]}")

    # Registrar traceback completo en logger
    tb = traceback.format_exception(type(error), error, error.__traceback__)
    full_traceback = "".join(tb)
    logger.error(
        "Error capturado: %s: %s\n%s",
        error_type,
        error_message,
        full_traceback,
    )

    return "\n".join(parts)


def handle_exception(exc_type, exc_value, exc_traceback):
    """Global exception handler para excepciones no capturadas.

    Instalado como sys.excepthook, intercepta cualquier excepcion no
    capturada y la archiva en los anales del Yggdrasil sin.crashear
    el programa. Los Norns registran cada sombra que cruza el destino.

    Args:
        exc_type: Tipo de la excepcion.
        exc_value: Valor de la excepcion.
        exc_traceback: Traceback completo.
    """
    # Ignorar KeyboardInterrupt — es una salida voluntaria
    if issubclass(exc_type, KeyboardInterrupt):
        sys.__excepthook__(exc_type, exc_value, exc_traceback)
        return

    # Formatear traceback completo
    tb_lines = traceback.format_exception(exc_type, exc_value, exc_traceback)
    full_traceback = "".join(tb_lines)

    # Registrar en logger con nivel CRITICAL
    logger.critical(
        "Excepcion no capturada: %s: %s\n%s",
        exc_type.__name__,
        str(exc_value),
        full_traceback,
    )

    # Mostrar mensaje dark fantasy al usuario
    error_msg = format_error(exc_value)
    print(f"\n{error_msg}\n", file=sys.stderr)

    # Intentar registrar en EnhancedMemory si esta disponible
    try:
        from Lilith.memory.enhanced import get_memory
        memory = get_memory()
        memory.add_episode(
            user_input="[SYSTEM_ERROR]",
            response=full_traceback[:500],
            tools_used=[],
            session_id="error_handler",
        )
    except Exception:
        # Si la memoria tampoco funciona, ya registramos en logger
        pass


def setup_global_error_handler():
    """Instala sys.excepthook con handle_exception.

    Las Norns vigilan los nueve mundos — esta funcion instala un
    centinela que intercepta toda excepcion no capturada para que
    el Yggdrasil nunca caiga en silencio.
    """
    sys.excepthook = handle_exception
    logger.info("Error handler global instalado — las Norns vigilan el Yggdrasil.")