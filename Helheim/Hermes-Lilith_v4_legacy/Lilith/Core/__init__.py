# Lilith Core Module
# Exposes LLMProvider and get_provider as primary LLM interface.
# LMStudioClient (llm_client) remains available as legacy compat.

from .llm_provider import LLMProvider, get_provider, list_providers, switch_provider
from .resilience import CircuitBreaker, CircuitBreakerError, RetryConfig, retry_with_backoff
from .error_handler import (
    LilithError,
    ProviderError,
    ToolError,
    MemoryError,
    ConfigError,
    sanitize_output,
    format_error,
    handle_exception,
    setup_global_error_handler,
)
from .lilith_logger import get_logger, logger
