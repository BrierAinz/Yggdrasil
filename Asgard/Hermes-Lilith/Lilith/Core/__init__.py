# Lilith Core Module
# Exposes LLMProvider and get_provider as primary LLM interface.
# LMStudioClient (llm_client) remains available as legacy compat.

from .llm_provider import LLMProvider, get_provider, list_providers, switch_provider
