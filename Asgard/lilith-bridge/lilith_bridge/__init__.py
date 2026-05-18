"""Lilith Bridge — Bidirectional gateway connecting Yggdrasil to Hermes Agent.

Provides two integration modes:
- ``create_bridge_router()`` — embed bridge endpoints into an existing FastAPI app.
- ``create_standalone_app()`` — run the bridge as a standalone server on port 9001.
"""

from .config import BridgeConfig, load_bridge_config
from .models import (
    BridgeChatRequest,
    BridgeChatResponse,
    BridgeHealth,
    BridgeMemoryQuery,
    BridgeMemoryStore,
    BridgeSkillSearch,
    HermesChatRequest,
    HermesChatResponse,
    HermesToolExecute,
    HermesToolResult,
)


__version__ = "1.0.0"

__all__ = [
    "BridgeChatRequest",
    "BridgeChatResponse",
    "BridgeConfig",
    "BridgeHealth",
    "BridgeMemoryQuery",
    "BridgeMemoryStore",
    "BridgeSkillSearch",
    "HermesChatRequest",
    "HermesChatResponse",
    "HermesToolExecute",
    "HermesToolResult",
    "load_bridge_config",
]
