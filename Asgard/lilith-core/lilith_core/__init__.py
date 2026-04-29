"""Lilith Core - Motor fundamental del agente CLI."""
__version__ = "2.0.0"

from .config import Config
from .exceptions import LilithError, ToolError, LLMError

__all__ = ["Config", "LilithError", "ToolError", "LLMError"]
