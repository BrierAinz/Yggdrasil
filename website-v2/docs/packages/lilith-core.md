---
sidebar_position: 2
title: lilith-core
---

# lilith-core

Foundation package: configuration, types, logging, and LLM provider abstractions.

## Quick Start

```python
from lilith_core import YggdrasilConfig, get_config, setup_logger, get_logger

# Load config from defaults (~/.lilith/)
config = get_config()

# Or specify a custom root
config = YggdrasilConfig(root_path="/path/to/project")

# Access config values
print(config.model)          # "auto"
print(config.lm_studio_url)  # "http://localhost:1234/v1"
print(config.max_context)    # 8192

# Get/set values (persisted to config.json)
config.set("temperature", 0.5)
temp = config.get("temperature")  # 0.5

# Logging
setup_logger(level="INFO")
logger = get_logger(__name__)
logger.info("System ready")
```

## YggdrasilConfig

Dataclass-based configuration with YAML, JSON, and env var support.

### Fields

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `root` | Path | `~/.lilith` | Project root directory |
| `model` | str | `"auto"` | Default LLM model |
| `lm_studio_url` | str | `http://localhost:1234/v1` | LM Studio endpoint |
| `temperature` | float | `0.7` | LLM temperature |
| `max_context` | int | `8192` | Max context window |
| `log_level` | str | `"INFO"` | Logging level |

### Methods

- `get(key, default=None)` — Get a config value
- `set(key, value)` — Set and persist to config.json
- `load(path)` — Class method: load from YAML file
- `config_file` — Property: path to config.json

## Types

```python
from lilith_core.types import Realm, Status, Project, Agent, Service

# Nine Realms enum
realm = Realm.ASGARD  # "Asgard"

# Project status
status = Status.ACTIVE  # "active"
```

## Providers

```python
from lilith_core.providers import LLMProvider, LocalProvider

# LLMProvider is the abstract base class
# LocalProvider wraps LM Studio / OpenAI-compatible APIs
provider = LocalProvider(config)
response = await provider.complete("Hello, world!")
```
