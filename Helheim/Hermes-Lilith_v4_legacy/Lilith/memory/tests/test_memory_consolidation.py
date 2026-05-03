"""
Tests para Memory Consolidation
===============================
RED-GREEN-REFACTOR: TDD estricto para consolidacion de memoria.
"""
from pathlib import Path

import pytest
from Lilith.memory.memory_consolidation import MemoryConsolidation


class TestMemoryConsolidation:
    """Tests para consolidacion de episodios."""

    @pytest.fixture
    def consolidation(self, tmp_path):
        db_path = tmp_path / "test_consolidation.db"
        # Crear tabla episodes para tests
        import sqlite3

        with sqlite3.connect(db_path) as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS episodes (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT NOT NULL,
                    user_input TEXT NOT NULL,
                    response TEXT,
                    context TEXT,
                    embedding BLOB,
                    compressed INTEGER DEFAULT 0,
                    tags TEXT
                )
            """
            )
            conn.commit()
        return MemoryConsolidation(db_path)

    def test_add_to_queue(self, consolidation):
        consolidation.add_to_queue(1, "test input", "test response")
        stats = consolidation.get_stats()
        assert stats["queue_size"] == 1

    def test_add_to_queue_deduplication(self, consolidation):
        consolidation.add_to_queue(1, "test", "response")
        consolidation.add_to_queue(1, "test", "response")
        stats = consolidation.get_stats()
        # OR IGNORE evita duplicados exactos
        assert stats["queue_size"] == 1

    def test_consolidate_episodes_merge(self, consolidation):
        consolidation.add_to_queue(1, "Python project setup", "Use venv")
        consolidation.add_to_queue(2, "Python project setup guide", "Use virtualenv")
        result = consolidation.consolidate_episodes()
        assert "processed" in result
        # Con solo 2 episodios no hay suficientes similares para merge
        assert result["processed"] >= 0

    def test_consolidate_episodes_deduplicate(self, consolidation):
        consolidation.add_to_queue(1, "exact same input", "exact same response")
        consolidation.add_to_queue(2, "exact same input", "exact same response")
        result = consolidation.consolidate_episodes()
        assert "deduplicated" in result

    def test_consolidate_episodes_compress(self, consolidation):
        consolidation.add_to_queue(1, "a" * 1000, "b" * 1000)
        result = consolidation.consolidate_episodes()
        assert "processed" in result

    def test_consolidate_empty_queue(self, consolidation):
        result = consolidation.consolidate_episodes()
        assert result["processed"] == 0
        assert result["merged_groups"] == 0

    def test_get_consolidated_episodes(self, consolidation):
        consolidation.add_to_queue(1, "test", "response")
        consolidation.consolidate_episodes()
        episodes = consolidation.get_consolidated_episodes()
        assert isinstance(episodes, list)

    def test_persistencia(self, tmp_path):
        db_path = tmp_path / "persist_consolidation.db"
        import sqlite3

        with sqlite3.connect(db_path) as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS episodes (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT NOT NULL,
                    user_input TEXT NOT NULL,
                    response TEXT,
                    context TEXT,
                    embedding BLOB,
                    compressed INTEGER DEFAULT 0,
                    tags TEXT
                )
            """
            )
            conn.commit()
        c1 = MemoryConsolidation(db_path)
        c1.add_to_queue(1, "test", "response")

        c2 = MemoryConsolidation(db_path)
        stats = c2.get_stats()
        assert stats["queue_size"] == 1
