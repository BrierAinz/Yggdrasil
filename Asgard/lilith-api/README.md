# lilith-api

<<<<<<< HEAD
FastAPI Gateway with WebSocket support.

Part of the Yggdrasil ecosystem.
=======
> *Bifröst rendered in endpoints — the shimmering bridge between mortals and gods.*

REST API layer exposing the Lilith agent over HTTP via FastAPI, letting external clients send prompts and receive structured responses.

## Installation

```bash
pip install -e .
```

## Usage

```python
from lilith_api.main import create_app

app = create_app()
# Or launch directly from the CLI entry point:
#   lilith-api
# Or via poethepoet:
#   poe api
```

### Key Patterns

**Lazy Initialization** — Heavy modules load only on first request:

```python
from lilith_api import get_memory, get_tools

@app.get("/status")
async def status(memory=Depends(get_memory)):
    return {"entries": memory.count_entries()}
```

**Dependency Injection** — FastAPI `Depends()` for all stateful routes.

**orjson** — Automatic fast JSON serialization (~10x faster than stdlib json).

**CORS** — Restricted to localhost origins for security.

**ThreadPool** — Scales with hardware: `min(32, (os.cpu_count() or 4) + 4)`.

## Architecture

This package is part of the **Asgard** realm in the Yggdrasil ecosystem.

- Part of the Lilith AI agent v2 modular architecture
- Depends on: `lilith-core>=2.0.0`, `lilith-tools>=2.0.0`, `lilith-memory>=2.0.0`, `lilith-orchestrator>=2.0.0`, `fastapi>=0.100`, `uvicorn[standard]>=0.23`, `pydantic>=2.0`, `orjson>=3.9`
- Optional: `uvloop>=0.17` for high-performance event loop

## Exports

| Symbol | Description |
|--------|-------------|
| `app` | FastAPI application instance |
| `get_config` | Lazy config dependency |
| `get_engine` | Lazy engine dependency |
| `get_memory` | Lazy memory dependency |
| `get_tools` | Lazy tools dependency |

## License

MIT
>>>>>>> origin/main
