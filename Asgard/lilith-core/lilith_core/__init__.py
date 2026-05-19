"""Lilith Core - Motor fundamental del agente CLI."""

__version__ = "2.0.0"

from .config import Config
from .exceptions import LilithError, LLMError, ToolError
from .providers import LLMProvider, LocalProvider


try:
    from .providers import LiteLLMProvider
except ImportError:  # litellm not installed
    LiteLLMProvider = None  # type: ignore[assignment,misc]

__all__ = [
    "Config",
    "LLMError",
    "LLMProvider",
    "LilithError",
    "LocalProvider",
    "ToolError",
]
if LiteLLMProvider is not None:
    __all__.append("LiteLLMProvider")
