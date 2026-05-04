# lilith-orchestrator

> *Heimdall's horn — one watcher to rally every realm.*

FastAPI gateway that coordinates all Lilith subsystems: routes requests between the LLM core, memory, and tools to produce unified agent responses.

## Installation

```bash
pip install -e .
```

## Usage

```python
from gateway import create_app

app = create_app()
# Then run with: uvicorn gateway.run:app --host 0.0.0.0 --port 8000
```

## Architecture

This package is part of the **Asgard** realm in the Yggdrasil ecosystem.

- Part of the Lilith AI agent v2 modular architecture
- Depends on: `lilith-core>=2.0.0`, `lilith-tools>=2.0.0`, `lilith-memory>=2.0.0`, `orjson>=3.9`, `uvicorn>=0.24.0`, `fastapi>=0.104.0`
- Optional (Unix): `uvloop` for maximum async performance

## License

MIT
