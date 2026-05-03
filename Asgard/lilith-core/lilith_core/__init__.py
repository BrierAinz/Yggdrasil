"""Lilith Core - Motor fundamental del agente CLI."""

__version__ = "2.0.0"

from .config import Config
from .exceptions import LilithError, LLMError, ToolError


__all__ = ["Config", "LLMError", "LilithError", "ToolError"]
