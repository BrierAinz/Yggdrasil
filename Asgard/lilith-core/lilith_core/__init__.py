"""Lilith Core - Base types, configuration, and logging for Yggdrasil."""

__version__ = "2.1.0"

from lilith_core.config import YggdrasilConfig, get_config
from lilith_core.logger import get_logger, setup_logger
from lilith_core.providers import LLMProvider, LocalProvider
from lilith_core.types import Agent, Project, Realm, Service, Status


__all__ = [
    "Agent",
    "LLMProvider",
    "LocalProvider",
    "Project",
    "Realm",
    "Service",
    "Status",
    "YggdrasilConfig",
    "get_config",
    "get_logger",
    "setup_logger",
]
