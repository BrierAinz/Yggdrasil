"""
Lilith Logger System
====================
Structured logging con estetica dark fantasy para Lilith v3.

Los Norns graban cada evento en las raices del Yggdrasil — aqui
los susurros de Niflheim y las runas de Midgard encuentran su
forma en logs con colores ancestrales y formato JSON estructurado.

Consola: DarkFantasyFormatter con runas Unicode y colores ANSI
Archivo: JsonFormatter para persistencia y analisis
"""

import json
import logging
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

# ─── Colores ANSI para terminal dark fantasy ──────────────────────────────────────

COLORS = {
    "DEBUG": "\033[36m",       # Cyan — susurros de Niflheim
    "INFO": "\033[32m",        # Verde — runas de Midgard
    "WARNING": "\033[33m",     # Amber — advertencias de Heimdall
    "ERROR": "\033[31m",       # Rojo — fuego de Muspelheim
    "CRITICAL": "\033[35m",    # Magenta — ira de los Norns
}
RESET = "\033[0m"


class DarkFantasyFormatter(logging.Formatter):
    """Formatter con estetica dark fantasy para consola.

    Las runas de los nueve mundos se manifiestan en cada nivel de log:
    - DEBUG:    ᚨ (Ansuz) — conocimiento oculto, susurros de Niflheim
    - INFO:     ᚱ (Raido) — camino correcto, runas de Midgard
    - WARNING:  ᛏ (Tiwaz) — advertencia, vigilancia de Heimdall
    - ERROR:    ᛁ (Isa)    — peligro, estasis, fuego de Muspelheim
    - CRITICAL: ᛉ (Algiz)  — proteccion urgente, ira de los Norns

    Formato: [RUNA] timestamp module | message
    """

    LEVEL_RUNES = {
        "DEBUG": "ᚨ",      # Ansuz — conocimiento oculto
        "INFO": "ᚱ",       # Raido — camino correcto
        "WARNING": "ᛏ",    # Tiwaz — advertencia
        "ERROR": "ᛁ",      # Isa — peligro
        "CRITICAL": "ᛉ",   # Algiz — proteccion urgente
    }

    def __init__(self, fmt=None, datefmt=None, style='%'):
        # Default format with dark fantasy styling
        if fmt is None:
            fmt = "[%(rune)s] %(asctime)s %(module)s | %(message)s"
        if datefmt is None:
            datefmt = "%H:%M:%S"
        super().__init__(fmt=fmt, datefmt=datefmt, style=style)

    def format(self, record: logging.LogRecord) -> str:
        """Formatea un log record con runas y colores ANSI."""
        # Añadir runa al record
        record.rune = self.LEVEL_RUNES.get(record.levelname, "?")

        # Aplicar formato base
        message = super().format(record)

        # Aplicar color ANSI segun nivel
        color = COLORS.get(record.levelname, RESET)
        return f"{color}{message}{RESET}"


class JsonFormatter(logging.Formatter):
    """Formatter JSON para archivos de log estructurados.

    Cada entrada se convierte en un objeto JSON con campos fijos
    que permiten analisis y busqueda eficiente — como las runas
    ordenadas del pozo de Mimir.
    """

    def format(self, record: logging.LogRecord) -> str:
        """Convierte un LogRecord a JSON string."""
        log_entry = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
            "message": record.getMessage(),
        }

        # Añadir campos extra si existen
        if hasattr(record, "extra_data"):
            log_entry["extra"] = record.extra_data

        # Añadir info de excepcion si existe
        if record.exc_info and record.exc_info[0] is not None:
            log_entry["exception"] = {
                "type": record.exc_info[0].__name__,
                "message": str(record.exc_info[1]),
                "traceback": self.formatException(record.exc_info),
            }

        return json.dumps(log_entry, ensure_ascii=False, default=str)


# ─── Logger Factory ────────────────────────────────────────────────────────────────

_loggers: dict = {}
_log_dir: Optional[Path] = None


def _ensure_log_dir() -> Path:
    """Asegura que el directorio de logsExista."""
    global _log_dir
    if _log_dir is None:
        _log_dir = Path.home() / ".lilith" / "logs"
    _log_dir.mkdir(parents=True, exist_ok=True)
    return _log_dir


def get_logger(name: str, level: int = logging.INFO) -> logging.Logger:
    """Obtiene logger con nombre de modulo y formateo dark fantasy.

    Los Norns escriben en dos libros: uno con runas de colores
    para la consola, otro en JSON eterno para los archivos.
    Cada modulo solicita su logger por nombre y recibe ambas
    salidas configuradas.

    Args:
        name: Nombre del modulo (ej: 'lilith.orchestrator').
        level: Nivel de logging (default: INFO).

    Returns:
        Logger configurado con consola y archivo handlers.
    """
    if name in _loggers:
        return _loggers[name]

    logger = logging.getLogger(name)
    logger.setLevel(level)

    # Evitar handlers duplicados si el logger ya fue configurado
    if logger.handlers:
        _loggers[name] = logger
        return logger

    # ── Console Handler: DarkFantasyFormatter ──
    console_handler = logging.StreamHandler(sys.stderr)
    console_handler.setLevel(level)
    console_handler.setFormatter(DarkFantasyFormatter())
    logger.addHandler(console_handler)

    # ── File Handler: JsonFormatter ──
    try:
        log_dir = _ensure_log_dir()
        log_file = log_dir / "lilith.log"
        file_handler = logging.FileHandler(
            str(log_file), encoding="utf-8", mode="a"
        )
        file_handler.setLevel(logging.DEBUG)  # Archivo siempre captura todo
        file_handler.setFormatter(JsonFormatter())
        logger.addHandler(file_handler)
    except Exception:
        # Si no se puede crear el archivo de log, no crashear
        pass

    # No propagar al logger raiz
    logger.propagate = False

    _loggers[name] = logger
    return logger


# ── Logger Global ──
logger = get_logger("lilith")