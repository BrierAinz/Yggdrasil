# lilith-memory

> *Mimir's Well — the waters that hold all that was and will be.*

Hybrid memory system managing conversation history, long-term recall, and context windows for the Lilith AI agent.

## Installation

```bash
pip install -e .

# With mem0 persistent memory backend:
pip install -e ".[mem0]"
```

## Usage

### MemoryStore (SQLite-based)

```python
from lilith_memory import MemoryStore

store = MemoryStore()
await store.remember("user_id", "The hero wields a rune-etched blade")
```

### Pluggable Backends

```python
from lilith_memory import MemoryBackend, SQLiteBackend, Mem0Backend

# SQLite backend (default, wraps MemoryStore with async interface)
backend = SQLiteBackend(db_path="memory.db")
await backend.add("user_id", "Rune-etched blade gleams in the dark")
results = await backend.search("blade", limit=5)

# Mem0 backend (persistent long-term memory with semantic vector search)
backend = Mem0Backend()  # auto-configures from MEM0_API_KEY env var
await backend.add("user_id", "The frost giant falls")
results = await backend.search("giant", limit=5)

# Custom backend (implement MemoryBackend ABC)
class MyBackend(MemoryBackend):
    async def add(self, user_id, content, metadata=None): ...
    async def search(self, query, limit=10): ...
    async def recent(self, user_id, limit=10): ...
    async def delete(self, user_id, content): ...
    async def clear(self, user_id): ...
    async def count(self, user_id=None): ...
```

## Architecture

This package is part of the **Asgard** realm in the Yggdrasil ecosystem.

- Part of the Lilith AI agent v2 modular architecture
- Depends on: none (standalone memory primitives)
- Consumed by: `lilith-orchestrator`, `lilith-api`, `lilith-cli`
- Backends: `SQLiteBackend` (default), `Mem0Backend` (optional, requires `mem0ai>=0.1`)

## License

MIT
