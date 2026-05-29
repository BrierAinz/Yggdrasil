# Memory RAG System (FASE 8)

## Architecture

Lilith's memory system is a layered hybrid architecture with 6 modules:

```
                    ┌─────────────────┐
                    │   Orchestrator   │
                    │  (entry point)   │
                    └────────┬─────────┘
                             │
              ┌──────────────┼──────────────┐
              │              │              │
    ┌─────────▼──┐  ┌───────▼──────┐  ┌───▼──────────┐
    │SessionStore│  │  EnhancedMem  │  │ Background   │
    │ (sessions) │  │  (episodes)  │  │Consolidator  │
    └────────────┘  └───────┬──────┘  └──────────────┘
                             │
              ┌──────────────┼──────────────┐
              │              │              │
    ┌─────────▼──┐  ┌───────▼──────┐  ┌───▼──────────┐
    │HybridRetriev│  │ MemoryGraph  │  │ Consolidation│
    │(vec+key+gr) │  │(entities+rl)│  │  (merge+prom)│
    └────────────┘  └──────────────┘  └──────────────┘
```

## SessionStore (`Lilith/Memory/session_store.py`)

Saves/restores conversation sessions with semantic search.

### SQLite Schema

```sql
CREATE TABLE sessions (
    id TEXT PRIMARY KEY,          -- session_id format: YYYYMMDD_HHMMSS
    created TEXT NOT NULL,
    last_active TEXT NOT NULL,
    summary TEXT,                  -- TF keyword extraction summary
    embedding BLOB,               -- pickled numpy 384d vector
    episode_count INTEGER DEFAULT 0,
    metadata TEXT                  -- JSON dict
);
```

### Key Methods

- `save_session(session_id, summary, episode_count, metadata)` — upsert with auto-generated embedding
- `load_session(session_id)` → dict or None
- `list_sessions(limit=20)` → list of dicts sorted by last_active
- `delete_session(session_id)` — remove session
- `search_sessions(query, limit=5)` — semantic search via EmbeddingModel (falls back to LIKE keyword match)
- `get_relevant_context(query, max_sessions=3, max_tokens=1000)` → formatted text for prompt injection
- `auto_summary(episodes)` — TF top-8 keyword extraction, no LLM required

### Singleton

```python
from Lilith.memory.session_store import get_session_store
store = get_session_store()
```

## BackgroundConsolidator (`Lilith/Memory/background_consolidator.py`)

Daemon thread that periodically runs consolidation cycles.

### Configuration

- Default interval: 300 seconds (5 minutes)
- Configurable via `interval_seconds` parameter
- Uses `threading.Event` for graceful stop

### Cycle Operations

1. **Merge similar episodes** (>0.85 cosine similarity via `MemoryConsolidation`)
2. **Promote frequent entities** (≥3 mentions → permanent facts)
3. **Decay weak relations** (strength decay via `MemoryGraph.decay_strength`)

### Stats Tracking

```python
consolidator.stats  # → {"cycles_run": N, "episodes_merged": N, "facts_promoted": N}
consolidator.last_run  # → ISO timestamp string
consolidator.is_running  # → bool
```

### Singleton

```python
from Lilith.memory.background_consolidator import get_consolidator
c = get_consolidator()
c.start()  # starts daemon thread
c.stop()   # graceful stop
```

## Orchestrator Integration

The Orchestrator coordinates all memory subsystems:

- `self.session_store` — injected in `__init__`
- `self._consolidator` — lazy-started via `start_consolidator()`
- `_inject_session_context(query)` — searches past sessions for relevant context
- `_build_system_prompt()` — includes session context block
- `_save_current_session()` — auto-summarizes current session using `auto_summary()`
- `reset()` — saves session before resetting session_id
- `close()` — saves session + stops consolidator

### Session Context Injection

When building the system prompt, the Orchestrator calls:
```python
session_ctx = self._inject_session_context(user_input)
```
This returns formatted text from relevant past sessions, which gets appended to the system prompt. Falls back to empty string if no relevant sessions found.

## HybridRetriever Weights

| Source     | Default Weight |
|------------|----------------|
| Vector     | 0.4            |
| Keyword    | 0.3            |
| Graph      | 0.2            |
| Recency    | 0.1            |

Diversity bonus: +0.05 per source that matched an episode.

## Test Count Progression

- FASE 6 start: 232 tests
- FASE 6.3 (E2E): 328 tests
- FASE 7 (Skills v2): 402 tests
- FASE 8 (Memory RAG): 468 tests

## Key Pitfalls

1. **EmbeddingModel is lazy-load** — `is_available()` triggers model download on first call. In tests, mock it to avoid downloading `all-MiniLM-L6-v2`.
2. **SQLite thread safety** — SessionStore and BackgroundConsolidator use separate connections. Never share a connection across threads.
3. **Singleton reset in tests** — Always reset `get_session_store()` and `get_consolidator()` singletons between test classes, or use `tmp_path` for isolated DBs.
4. **Auto-summary is keyword-based** — `auto_summary()` uses TF keyword extraction, not an LLM. It extracts top-8 terms by frequency. Don't expect coherent paragraph summaries.
5. **Consolidator daemon lifecycle** — Always `stop()` the consolidator in teardown. Dangling daemon threads cause test failures.