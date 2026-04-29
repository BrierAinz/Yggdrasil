import pytest
from lilith_memory.store import MemoryStore


def test_add_and_search(tmp_path):
    store = MemoryStore(tmp_path / "test.db")
    store.add("Hola mundo", metadata={"source": "test"})
    results = store.search("mundo")
    assert len(results) == 1
    assert results[0]["content"] == "Hola mundo"


def test_recent(tmp_path):
    store = MemoryStore(tmp_path / "test.db")
    store.add("Primero")
    store.add("Segundo")
    recent = store.recent(limit=2)
    assert len(recent) == 2
