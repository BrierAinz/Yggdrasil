# lilith-memory

<<<<<<< HEAD
Vector memory store with SQLite backend.

Part of the Yggdrasil ecosystem.
=======
> *Mimir's Well — the waters that hold all that was and will be.*

Hybrid memory system managing conversation history, long-term recall, and context windows for the Lilith AI agent.

## Installation

```bash
pip install -e .

# With mem0 persistent memory backend:
pip install -e ".[mem0]"

# With ChromaDB semantic search backend:
pip install -e ".[chroma]"
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
from lilith_memory import MemoryBackend, SQLiteBackend, Mem0Backend, ChromaBackend

# SQLite backend (default, wraps MemoryStore with async interface)
backend = SQLiteBackend(db_path="memory.db")
await backend.add("content", metadata={"user": "hero"})
results = await backend.search("blade", limit=5)

# ChromaDB backend (local semantic search with sentence-transformers)
backend = ChromaBackend(db_path=Path("./chroma_data"))
await backend.add("Rune-etched blade gleams in the dark")
results = await backend.search("blade", limit=5)  # semantic similarity

# Mem0 backend (persistent long-term memory with vector search)
backend = Mem0Backend()  # auto-configures from MEM0_API_KEY env var
await backend.add("The frost giant falls")
results = await backend.search("giant", limit=5)

# Custom backend (implement MemoryBackend ABC)
class MyBackend(MemoryBackend):
    async def add(self, content, metadata=None): ...
    async def search(self, query, limit=5): ...
    async def recent(self, limit=10): ...
    async def delete(self, entry_id): ...
    async def clear(self) -> int: ...
    def count(self) -> int: ...
```

## Architecture

This package is part of the **Asgard** realm in the Yggdrasil ecosystem.

- Part of the Lilith AI agent v2 modular architecture
- Depends on: none (standalone memory primitives)
- Consumed by: `lilith-orchestrator`, `lilith-api`, `lilith-cli`
- Backends: `SQLiteBackend` (default), `ChromaBackend` (optional, requires `chromadb>=0.4.0`), `Mem0Backend` (optional, requires `mem0ai>=0.1`)

## License

MIT
>>>>>>> origin/main
