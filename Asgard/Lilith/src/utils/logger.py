from __future__ import annotations

import json
import logging
import os
from datetime import datetime, timezone
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import Optional


class JSONFormatter(logging.Formatter):
    """Formatea logs como JSON para fácil parsing."""

    def format(self, record: logging.LogRecord) -> str:  # type: ignore[override]
        log_data = {
            "ts": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "module": record.name,
            "msg": record.getMessage(),
            "session_id": getattr(record, "session_id", None),
            "agent": getattr(record, "agent", None),
            "duration_ms": getattr(record, "duration_ms", None),
        }
        if record.exc_info:
            log_data["exception"] = self.formatException(record.exc_info)
        return json.dumps(log_data, ensure_ascii=False)


class AutoModeFilter(logging.Filter):
    """Filtra registros para auto_mode.jsonl (solo módulo de auto_mode)."""

    AUTO_MODE_LOGGERS = {"TaskPlanner", "TaskExecutor", "TaskMonitor"}

    def filter(self, record: logging.LogRecord) -> bool:  # type: ignore[override]
        return record.name in self.AUTO_MODE_LOGGERS


def _ensure_once() -> bool:
    """
    Asegura que setup_logging solo se ejecute una vez por proceso.
    Devuelve True si es la primera vez.
    """
    root = logging.getLogger()
    if getattr(root, "_lilith_logging_configured", False):
        return False
    setattr(root, "_lilith_logging_configured", True)
    return True


def setup_logging(log_dir: str = "Memory/logs") -> None:
    """Configurar logging estructurado para todo el proyecto."""
    if not _ensure_once():
        return

    base_path = Path(__file__).resolve().parent.parent
    logs_path = base_path / log_dir
    os.makedirs(logs_path, exist_ok=True)

    root = logging.getLogger()
    root.setLevel(logging.DEBUG)

    # Handler principal: lilith.jsonl (INFO+)
    file_handler = RotatingFileHandler(
        logs_path / "lilith.jsonl",
        maxBytes=10_000_000,
        backupCount=5,
        encoding="utf-8",
    )
    file_handler.setFormatter(JSONFormatter())
    file_handler.setLevel(logging.INFO)

    # Handler de errores: errors.jsonl (ERROR+)
    error_handler = RotatingFileHandler(
        logs_path / "errors.jsonl",
        maxBytes=5_000_000,
        backupCount=3,
        encoding="utf-8",
    )
    error_handler.setFormatter(JSONFormatter())
    error_handler.setLevel(logging.ERROR)

    # Handler específico auto_mode: auto_mode.jsonl (INFO+, solo TaskPlanner/TaskExecutor/TaskMonitor)
    auto_mode_handler = RotatingFileHandler(
        logs_path / "auto_mode.jsonl",
        maxBytes=5_000_000,
        backupCount=3,
        encoding="utf-8",
    )
    auto_mode_handler.setFormatter(JSONFormatter())
    auto_mode_handler.setLevel(logging.INFO)
    auto_mode_handler.addFilter(AutoModeFilter())

    # Handler consola legible
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(
        logging.Formatter("%(asctime)s [%(levelname)s] %(name)s: %(message)s")
    )
    console_handler.setLevel(logging.DEBUG)

    root.addHandler(file_handler)
    root.addHandler(error_handler)
    root.addHandler(auto_mode_handler)
    root.addHandler(console_handler)


def get_logger(name: Optional[str] = None) -> logging.Logger:
    """Obtener logger con la configuración global ya aplicada."""
    return logging.getLogger(name)
