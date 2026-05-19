# lilith-core

> *The seed of Yggdrasil — where all roots converge.*

Core engine providing the LLM client, configuration, logging, and shared types for the Lilith AI agent.

## Installation

```bash
pip install -e .

# With LiteLLM multi-model support:
pip install -e ".[litellm]"
```

## Usage

### Configuration

```python
from lilith_core import Config, LilithError

config = Config.load("config.yaml")
# Core types and exceptions are available across all Lilith subsystems
```

### LLM Providers

```python
from lilith_core import LLMProvider, LocalProvider, LiteLLMProvider

# Local provider — direct httpx to local OpenAI-compatible servers
provider = LocalProvider(base_url="http://localhost:1234/v1")
result = await provider.complete([{"role": "user", "content": "Hello"}])

# LiteLLM provider — 100+ models via unified API
provider = LiteLLMProvider()  # auto-configures from environment
result = await provider.complete(messages, model="gpt-4")

# Provider interface (abstract base class for custom providers)
class MyProvider(LLMProvider):
    async def complete(self, messages, **kwargs): ...
    async def stream(self, messages, **kwargs): ...
    async def list_models(self): ...
```

## Architecture

This package is part of the **Asgard** realm in the Yggdrasil ecosystem.

- Part of the Lilith AI agent v2 modular architecture
- Depends on: `requests>=2.28.0`, `pydantic>=2.0`
- Optional: `litellm>=1.40` for multi-model provider support
- Foundation layer — all other Lilith packages depend on `lilith-core`

## Exports

| Symbol | Description |
|--------|-------------|
| `Config` | YAML-based configuration with env var support |
| `LilithError` | Base exception for all Lilith errors |
| `LLMError` | LLM-specific error (timeouts, rate limits) |
| `ToolError` | Tool execution error |
| `LLMProvider` | Abstract base class for LLM providers |
| `LocalProvider` | Direct httpx client for local OpenAI-compatible servers |
| `LiteLLMProvider` | Multi-model provider via LiteLLM (optional) |

## License

MIT
