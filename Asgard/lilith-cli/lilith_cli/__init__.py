<<<<<<< HEAD
"""Terminal interface for Lilith ecosystem."""

__version__ = "3.0.0"
=======
"""Lilith CLI v3.0 — Yggdrasil Agent REPL (Where Ancient Meets Digital)."""

__version__ = "3.0.0"

from .client import LilithClient
from .config import YggdrasilConfig, load_config, save_config


__all__ = [
    "LilithClient",
    "YggdrasilConfig",
    "load_config",
    "save_config",
]
>>>>>>> origin/main
