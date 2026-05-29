"""
LLM Module - Lilith AI Core.

Provides unified access to multiple LLM providers with:
- Automatic model selection
- Complexity-based routing
- Response caching
- Cost tracking
"""

from .cost_tracker_extended import (
    CostTrackerExtended,
    get_cost_tracker_v2,
    track_model_usage,
)
from .model_cache import (
    ModelCache,
    cache_response,
    get_cached_response,
    get_model_cache,
)
from .model_selector import (
    ModelSelector,
    SelectionResult,
    get_model_selector,
    select_model,
)
from .smart_llm_client import SmartLLMClient, get_smart_llm_client, smart_chat

__all__ = [
    # Smart LLM Client
    "SmartLLMClient",
    "get_smart_llm_client",
    "smart_chat",
    # Model Selector
    "ModelSelector",
    "SelectionResult",
    "get_model_selector",
    "select_model",
    # Model Cache
    "ModelCache",
    "get_model_cache",
    "get_cached_response",
    "cache_response",
    # Cost Tracking
    "CostTrackerExtended",
    "get_cost_tracker_v2",
    "track_model_usage",
]
