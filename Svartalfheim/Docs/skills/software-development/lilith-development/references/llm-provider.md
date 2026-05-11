# LLM Provider System

## Architecture

`Lilith/Core/llm_provider.py` implements a multi-provider LLM backend with automatic fallback.

### Providers

| Provider | Type | Base URL | Model | Auth |
|----------|------|----------|-------|------|
| LM Studio | local | `http://localhost:1234/v1` | auto-detected | None |
| Kimi Code | remote | `https://api.kimi.com/coding/v1` | `kimi-for-coding` (internally Kimi-k2.6) | Bearer token via `KIMI_API_KEY` + `X-Client: claude-code` header **required** |

### Kimi Code API Requirements

**CRITICAL:** The Kimi Code API (`api.kimi.com`) is **exclusive to coding agents**. It will reject requests without the proper headers.

1. **Endpoint:** `https://api.kimi.com/coding/v1` (NOT `api.moonshot.cn/v1` — that's the old Moonshot API which is now deprecated for Kimi)
2. **Model ID:** `kimi-for-coding` (the model internally runs Kimi-k2.6 with 262K context, supports reasoning, image input, video input)
3. **Required Header:** `X-Client: claude-code` — Without this, the API returns: `{"error": {"message": "Kimi For Coding is currently only available for Coding Agents such as Kimi CLI, Claude Code, Roo Code, Kilo Code, etc.", "type": "access_terminated_error"}}`
4. **API Keys:** Generated at https://kimi.com in the Kimi Code Console (up to 5 keys, each shown only once)

The `_get_headers()` method in `LLMProvider` automatically adds `X-Client: claude-code` when `kimi.com` is detected in the `base_url`.

### Fallback Logic

`LLM_PROVIDER` env var controls behavior:
- `"auto"` (default): tries LM Studio first, falls back to Kimi Code if LM Studio is unreachable
- `"lm_studio"`: force local only, raises ConnectionError if unavailable
- `"kimi"`: force remote Kimi Code, raises ConnectionError if API key missing or unreachable

Each provider has its own `CircuitBreaker` instance (from `resilience.py`). When a provider's circuit breaker is OPEN, it's skipped in fallback.

### Key Classes

- `LLMProvider`: Represents one backend. Has `chat()` and `chat_stream()`. Auto-detects model on first call when `model="auto"`.
- `get_provider(name=None)`: Returns active provider (uses fallback logic if `name=None`).
- `switch_provider(name)`: Changes active provider, raises `ConnectionError` if unreachable.
- `list_providers()`: Returns status dict for all configured providers.
- `test_all_providers()`: Health check, returns availability per provider.

### Configuration

Defined in `~/.lilith/config.toml` (TOML config system, FASE 6+):

```toml
[llm]
provider = "auto"  # "auto", "lm_studio", or "kimi"
default_model = "auto"

[llm.providers.lm_studio]
type = "local"
base_url = "http://localhost:1234/v1"
model = "auto"

[llm.providers.kimi]
type = "remote"
base_url = "https://api.kimi.com/coding/v1"
model = "kimi-for-coding"
api_key = ""  # se lee de KIMI_API_KEY env var si vacio
```

Env vars override TOML: `LILITH_LM_URL`, `LILITH_MODEL`, `LILITH_PROVIDER`, `KIMI_API_KEY`.

### Adding a New Provider

1. Add provider section to `~/.lilth/config.toml` under `[llm.providers]`
2. Add API key env var to `config.py` and `.env.example`
3. `_init_providers()` in `llm_provider.py` auto-picks it up from TOML config
4. If the provider requires custom headers (like Kimi's `X-Client`), add detection logic in `_get_headers()`
5. Add provider-specific tests to `test_llm_provider.py`

### Pitfalls

- **Kimi Code vs Moonshot:** The old `api.moonshot.cn/v1` endpoint is the Moonshot platform. The new Kimi Code API is at `api.kimi.com/coding/v1`. They use different API keys and different model IDs. Do NOT mix them.
- **X-Client header:** Kimi Code requires `X-Client: claude-code` header. Without it, you get `access_terminated_error`. The `_get_headers()` method adds this automatically when `kimi.com` is in the base URL.
- **API key source:** Kimi Code API keys are generated at kimi.com (Kimi Code Console), NOT at platform.moonshot.cn. Moonshot keys won't work with the Kimi Code endpoint and vice versa.