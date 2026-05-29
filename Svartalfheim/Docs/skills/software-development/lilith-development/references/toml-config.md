# Lilith TOML Config System

## Overview

Lilith v3 uses `~/.lilith/config.toml` as the single source of truth for all configuration. The system was introduced in FASE 6 as a replacement for hardcoded Python constants.

**File:** `Lilith/Core/toml_config.py`
**Class:** `LilithConfig` (singleton, thread-safe via `threading.Lock`)
**Config path:** `~/.lilith/config.toml` (auto-created with defaults if missing)

## Priority Hierarchy

```
Env vars (.env) > TOML file values > Hardcoded defaults
```

This means `KIMI_API_KEY` in `.env` always overrides `api_key` in `config.toml`. This is by design — secrets never go in TOML files.

## API

```python
from Lilith.Core.toml_config import LilithConfig, get_config

config = get_config()  # Singleton

# Dotted key access
url = config.get("llm.providers.lm_studio.base_url")
port = config.get("dashboard.port", 8765)  # with default

# Modify and persist
config.set("llm.default_model", "gemma-4-12b")
config.save()  # writes to ~/.lilith/config.toml

# Hot-reload from disk
config.reload()

# Stats
stats = config.get_stats()  # dict with useful info
```

## Retro-Compatibility

`Lilith/Core/config.py` retains ALL public constants (`LM_STUDIO_URL`, `DEFAULT_MODEL`, `LLM_PROVIDERS`, etc.) but now reads them from `LilithConfig` instead of hardcoding. Existing code that imports from `config.py` works unchanged.

`reload_config()` in `config.py` refreshes all module-level constants from TOML.

## TOML Schema

```toml
[llm]
default_provider = "auto"    # "auto", "lm_studio", "kimi"
default_model = "auto"

[llm.providers.lm_studio]
type = "local"
base_url = "http://localhost:1234/v1"
model = "auto"
api_key = ""                 # LM Studio doesn't need a key

[llm.providers.kimi]
type = "remote"
base_url = "https://api.moonshot.cn/v1"
model = "kimi-2.6"
api_key = ""                 # reads from KIMI_API_KEY env var if empty

[chat]
max_history = 50

[tools]
timeout = 60
max_calls = 25

[memory]
dir = ""                     # empty = auto (<project_root>/memory)
save_history = true

[skills]
dir = ""                     # empty = auto (~/.lilith/skills)
hot_reload = true
auto_trigger = true
max_triggered = 3

[workspace]
dir = "D:\\Proyectos\\Midgard"
projects_dir = "D:\\Proyectos"

[dashboard]
host = "localhost"
port = 8765
auto_open = false

[mcp]
config_path = ""             # empty = auto (~/.lilith/mcp.json)

[logging]
level = "INFO"
file = ""                    # empty = auto (<project_root>/logs/lilith.log)
```

## Testing Pattern

When testing with `LilithConfig`, always reset the singleton to avoid cross-test contamination:

```python
@pytest.fixture(autouse=True)
def reset_config():
    LilithConfig._instance = None
    yield
    LilithConfig._instance = None
```

Same pattern for `DynamicToolRegistry._instance` and `MCPManager._instance`.