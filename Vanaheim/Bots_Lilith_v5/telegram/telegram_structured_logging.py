"""
Structured Logging para Telegram Bot

Sistema de logging con:
- Rotación diaria de archivos
- Formato estructurado (JSON opcional)
- Niveles configurables
- Context injection
"""

import json
import logging
import sys
from datetime import datetime, timezone
from logging.handlers import TimedRotatingFileHandler
from pathlib import Path
from typing import Any, Dict, Optional


class StructuredFormatter(logging.Formatter):
    """
    Formatter estructurado con contexto adicional

    Formato: [TIMESTAMP] [LEVEL] [MODULE] MESSAGE {context}
    """

    def format(self, record: logging.LogRecord) -> str:
        """Formatear record con estructura"""
        # Timestamp ISO
        timestamp = datetime.fromtimestamp(record.created, tz=timezone.utc).isoformat()

        # Nivel
        level = record.levelname

        # Módulo
        module = record.name

        # Mensaje
        message = record.getMessage()

        # Contexto adicional (si hay)
        context = {}
        if hasattr(record, "context"):
            context = record.context

        # Exception info
        if record.exc_info:
            exception_text = self.formatException(record.exc_info)
            context["exception"] = exception_text

        # Construir línea
        parts = [f"[{timestamp}]", f"[{level:8}]", f"[{module}]", message]

        if context:
            parts.append(json.dumps(context, ensure_ascii=False))

        return " ".join(parts)


class JSONFormatter(logging.Formatter):
    """
    Formatter JSON para procesamiento automático

    Cada línea es un objeto JSON completo
    """

    def format(self, record: logging.LogRecord) -> str:
        """Formatear record como JSON"""
        log_obj = {
            "timestamp": datetime.fromtimestamp(
                record.created, tz=timezone.utc
            ).isoformat(),
            "level": record.levelname,
            "module": record.name,
            "message": record.getMessage(),
            "line": record.lineno,
        }

        # Contexto adicional
        if hasattr(record, "context"):
            log_obj["context"] = record.context

        # Exception
        if record.exc_info:
            log_obj["exception"] = self.formatException(record.exc_info)

        return json.dumps(log_obj, ensure_ascii=False)


def setup_telegram_logging(
    log_dir: Path,
    level: int = logging.INFO,
    json_format: bool = False,
    console_output: bool = True,
) -> logging.Logger:
    """
    Configurar logging para Telegram bot

    Args:
        log_dir: Directorio para logs
        level: Nivel de logging (DEBUG, INFO, WARNING, ERROR)
        json_format: Usar formato JSON
        console_output: Enviar logs a console también

    Returns:
        Logger configurado
    """
    # Crear directorio
    log_dir.mkdir(parents=True, exist_ok=True)

    # Logger raíz para Telegram
    logger = logging.getLogger("telegram_bot")
    logger.setLevel(level)

    # Limpiar handlers existentes
    logger.handlers.clear()

    # Handler: archivo con rotación diaria
    log_file = log_dir / "telegram.log"
    file_handler = TimedRotatingFileHandler(
        filename=log_file,
        when="midnight",
        interval=1,
        backupCount=30,  # Mantener 30 días
        encoding="utf-8",
    )
    file_handler.setLevel(level)

    # Formatter
    if json_format:
        formatter = JSONFormatter()
    else:
        formatter = StructuredFormatter()

    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)

    # Handler: console (opcional)
    if console_output:
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(level)
        console_handler.setFormatter(formatter)
        logger.addHandler(console_handler)

    logger.info(
        "Telegram logging configured",
        extra={
            "context": {
                "log_dir": str(log_dir),
                "level": logging.getLevelName(level),
                "json_format": json_format,
            }
        },
    )

    return logger


def log_with_context(
    logger: logging.Logger,
    level: int,
    message: str,
    context: Optional[Dict[str, Any]] = None,
):
    """
    Log con contexto adicional

    Args:
        logger: Logger a usar
        level: Nivel (logging.INFO, etc.)
        message: Mensaje
        context: Dict con contexto adicional
    """
    extra = {"context": context} if context else {}
    logger.log(level, message, extra=extra)


# Helpers de conveniencia
def log_api_call(
    logger: logging.Logger,
    endpoint: str,
    method: str = "POST",
    status_code: Optional[int] = None,
    duration_ms: Optional[float] = None,
    error: Optional[str] = None,
):
    """Log de llamada a API"""
    context = {"endpoint": endpoint, "method": method}

    if status_code:
        context["status_code"] = status_code

    if duration_ms:
        context["duration_ms"] = round(duration_ms, 1)

    if error:
        context["error"] = error
        logger.error(f"API call failed: {endpoint}", extra={"context": context})
    else:
        logger.info(f"API call: {endpoint}", extra={"context": context})


def log_message_received(
    logger: logging.Logger,
    chat_id: int,
    user_id: int,
    message_text: str,
    message_length: int,
):
    """Log de mensaje recibido"""
    context = {"chat_id": chat_id, "user_id": user_id, "length": message_length}

    # Truncar mensaje largo
    if message_length > 100:
        preview = message_text[:100] + "..."
    else:
        preview = message_text

    logger.info(f"Message received: {preview}", extra={"context": context})


def log_message_sent(
    logger: logging.Logger,
    chat_id: int,
    response_length: int,
    backend_used: Optional[str] = None,
):
    """Log de mensaje enviado"""
    context = {"chat_id": chat_id, "length": response_length}

    if backend_used:
        context["backend"] = backend_used

    logger.info("Message sent", extra={"context": context})
