"""Lilith Core - Motor fundamental del agente CLI."""

__version__ = "2.0.0"

from .config import Config
from .exceptions import LilithError, LLMError, ToolError
from .providers import LiteLLMProvider, LLMProvider, LocalProvider


__all__ = [
    "Config",
    "LLMError",
    "LLMProvider",
    "LilithError",
    "LiteLLMProvider",
    "LocalProvider",
    "ToolError",
]
