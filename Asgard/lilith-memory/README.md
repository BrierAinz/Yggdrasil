# lilith-memory

> *Mimir's Well — the waters that hold all that was and will be.*

Hybrid memory system managing conversation history, long-term recall, and context windows for the Lilith AI agent.

## Installation

```bash
pip install -e .
```

## Usage

```python
from lilith_memory import MemoryStore

store = MemoryStore()
await store.remember("user_id", "The hero wields a rune-etched blade")
```

## Architecture

This package is part of the **Asgard** realm in the Yggdrasil ecosystem.

- Part of the Lilith AI agent v2 modular architecture
- Depends on: none (standalone memory primitives)
- Consumed by: `lilith-orchestrator`, `lilith-api`, `lilith-cli`

## License

MIT
