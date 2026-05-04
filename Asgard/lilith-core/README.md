# lilith-core

> *The seed of Yggdrasil — where all roots converge.*

Core engine providing the LLM client, configuration, logging, and shared types for the Lilith AI agent.

## Installation

```bash
pip install -e .
```

## Usage

```python
from lilith_core import Config, LilithError

config = Config.load("config.yaml")
# Core types and exceptions are available across all Lilith subsystems
```

## Architecture

This package is part of the **Asgard** realm in the Yggdrasil ecosystem.

- Part of the Lilith AI agent v2 modular architecture
- Depends on: `requests>=2.28.0`, `pydantic>=2.0`
- Foundation layer — all other Lilith packages depend on `lilith-core`

## License

MIT
