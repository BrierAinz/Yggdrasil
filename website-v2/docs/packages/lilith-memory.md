---
sidebar_position: 3
title: lilith-memory
---

# lilith-memory

Persistent memory storage with pluggable backends (SQLite, ChromaDB, Mem0).

## Quick Start

```python
from lilith_memory.store import MemoryStore

# Create a store (SQLite-backed)
store = MemoryStore("my_memory.db")

# Store memories
store.add("User asked about Python", role="user")
store.store("default", "assistant", "Here's how to use Python...")

# Search memories
results = store.search("Python")
for r in results:
    print(r["content"], r["role"])

# Recent entries
recent = store.recent(limit=5)

# Count and clear
print(store.count())  # 2
store.clear()         # returns count removed
```

## MemoryStore API

| Method | Signature | Description |
|--------|-----------|-------------|
| `store()` | `(session_id, role, content, metadata=None) -> int` | Store an entry |
| `add()` | `(content, role="user", session_id="default", metadata=None) -> int` | Convenience wrapper |
| `recall()` | `(session_id, limit=10) -> list[dict]` | Recall by session |
| `recent()` | `(limit=10) -> list[dict]` | Recent entries (default session) |
| `search()` | `(query, limit=5) -> list[dict]` | Text search |
| `count()` | `() -> int` | Total entry count |
| `delete()` | `(entry_id) -> bool` | Delete by ID |
| `clear()` | `() -> int` | Clear all entries |
| `sessions()` | `() -> list[str]` | List all session IDs |

## Backends

### SQLite (default)

```python
from lilith_memory.store import MemoryStore
store = MemoryStore("memory.db")  # WAL mode, thread-safe
```

### SQLiteBackend (async adapter)

```python
from lilith_memory.backends import SQLiteBackend
backend = SQLiteBackend(Path("memory.db"))
await backend.add("async entry")
results = await backend.search("async")
```

### ChromaDB

```python
from lilith_memory.backends import ChromaBackend
# Requires: pip install chromadb
backend = ChromaBackend(collection="my_collection")
```

### Mem0

```python
from lilith_memory.backends import Mem0Backend
# Requires: pip install mem0ai
backend = Mem0Backend(api_key="...")
```

## Memory Layers

Advanced memory architecture with three layers:

- **Working Memory** — Current session context
- **Episodic Memory** — Past interactions
- **Semantic Memory** — Extracted knowledge

```python
from lilith_memory.layers.working_memory import WorkingMemory
from lilith_memory.layers.episodic_memory import EpisodicMemory
from lilith_memory.layers.semantic_memory import SemanticMemory
```
