"""Tests for the SQLite-backend adapter."""

from __future__ import annotations

import asyncio
from typing import TYPE_CHECKING

from lilith_memory.backends import SQLiteBackend
from lilith_memory.backends.base import MemoryBackend
from lilith_memory.store import MemoryStore


if TYPE_CHECKING:
    from pathlib import Path


# ------------------------------------------------------------------
# Tests
# ------------------------------------------------------------------


def test_adapter_implements_interface():
    """SQLiteBackend should be a subclass of MemoryBackend."""
    assert issubclass(SQLiteBackend, MemoryBackend)


def test_crud_operations_match_original(tmp_path: Path):
    """The async SQLiteBackend should produce the same results as MemoryStore."""

    # ---- Set up both the raw store and the adapter ----
    db = tmp_path / "compat.db"
    raw = MemoryStore(db)
    adapter = SQLiteBackend(db)

    # We'll use a single event loop for all async calls
    loop = asyncio.new_event_loop()

    # ---- add ----
    entry_id = loop.run_until_complete(
        adapter.add("hello from adapter", metadata={"origin": "test"})
    )
    assert entry_id  # should return a non-empty string id

    # Verify the raw store sees it too
    assert raw.count_entries() >= 1

    # ---- search ----
    results = loop.run_until_complete(adapter.search("adapter"))
    assert len(results) >= 1
    assert any(r["content"] == "hello from adapter" for r in results)

    # ---- recent ----
    loop.run_until_complete(adapter.add("second entry"))
    recent = loop.run_until_complete(adapter.recent(limit=2))
    assert len(recent) == 2

    # ---- count ----
    assert adapter.count() == 2

    # ---- delete ----
    deleted = loop.run_until_complete(adapter.delete(entry_id))
    assert deleted is True
    assert adapter.count() == 1

    # ---- clear ----
    removed = loop.run_until_complete(adapter.clear())
    assert removed == 1
    assert adapter.count() == 0

    loop.close()
