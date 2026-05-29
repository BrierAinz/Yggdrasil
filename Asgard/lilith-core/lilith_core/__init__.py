<<<<<<< HEAD
"""Lilith Core - Base types, configuration, and logging for Yggdrasil."""

__version__ = "2.1.0"

from lilith_core.config import YggdrasilConfig, get_config
from lilith_core.types import Realm, Status, Project, Agent, Service
from lilith_core.logger import setup_logger, get_logger
from lilith_core.providers import ProviderConfig, get_provider, chat_completion

__all__ = [
    "YggdrasilConfig", "get_config",
    "Realm", "Status", "Project", "Agent", "Service",
    "setup_logger", "get_logger",
    "ProviderConfig", "get_provider", "chat_completion",
]
=======
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
>>>>>>> origin/main
