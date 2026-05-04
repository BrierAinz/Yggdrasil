# lilith-api

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
```

## Architecture

This package is part of the **Asgard** realm in the Yggdrasil ecosystem.

- Part of the Lilith AI agent v2 modular architecture
- Depends on: `lilith-core>=2.0.0`, `lilith-tools>=2.0.0`, `lilith-memory>=2.0.0`, `lilith-orchestrator>=2.0.0`, `fastapi>=0.100`, `uvicorn[standard]>=0.23`, `pydantic>=2.0`, `orjson>=3.9`

## License

MIT
