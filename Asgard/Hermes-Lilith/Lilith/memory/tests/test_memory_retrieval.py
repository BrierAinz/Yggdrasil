"""
Tests para Memory Retrieval (Hybrid)
====================================
RED-GREEN-REFACTOR: TDD estricto para retrieval hibrido.
"""
from pathlib import Path

import pytest
from Lilith.memory.memory_retrieval import HybridRetriever


class TestHybridRetriever:
    """Tests para retrieval hibrido."""

    @pytest.fixture
    def retriever(self, tmp_path):
        db_path = tmp_path / "test_retrieval.db"
        return HybridRetriever(db_path)

    def test_add_episode(self, retriever):
        retriever.add_episode(1, "Python testing with pytest", "Use fixtures")
        with retriever._connect() as conn:
            row = conn.execute("SELECT * FROM episodes WHERE id = 1").fetchone()
        assert row is not None
        assert "pytest" in row[2]  # user_input

    def test_retrieve_vector_search(self, retriever):
        retriever.add_episode(1, "Python testing framework", "pytest is great")
        retriever.add_episode(2, "JavaScript testing", "jest is popular")
        results = retriever.retrieve("Python testing pytest")
        assert len(results) > 0
        # El primero debe ser el de Python
        assert "python" in results[0]["user_input"].lower()

    def test_retrieve_keyword_search(self, retriever):
        retriever.add_episode(1, "Python FastAPI web framework", "async routes")
        retriever.add_episode(2, "Python Django ORM", "models and queries")
        results = retriever.retrieve("FastAPI async")
        assert len(results) > 0
        contents = " ".join(r["user_input"] for r in results)
        assert "fastapi" in contents.lower()

    def test_retrieve_graph_search(self, retriever):
        retriever.add_episode(1, "Python uses FastAPI", "web framework")
        retriever.add_episode(2, "FastAPI depends on Starlette", "ASGI")
        # Extraer entidades y relaciones
        retriever.graph.add_relation("python", "fastapi", "uses")
        retriever.graph.add_relation("fastapi", "starlette", "depends_on")
        results = retriever.retrieve("Python web framework")
        assert len(results) >= 1

    def test_retrieve_combines_sources(self, retriever):
        retriever.add_episode(1, "Python testing", "pytest")
        retriever.add_episode(2, "Python web", "FastAPI")
        retriever.add_episode(3, "JavaScript", "React")
        results = retriever.retrieve("Python")
        assert len(results) >= 2
        ids = {r["id"] for r in results}
        assert 1 in ids or 2 in ids

    def test_retrieve_deduplication(self, retriever):
        """Retrieve no debe retornar el mismo ID multiple veces."""
        retriever.add_episode(1, "Python testing", "pytest")
        retriever.add_episode(
            2, "Python testing", "pytest"
        )  # contenido similar, ID diferente
        results = retriever.retrieve("Python testing")
        # No debe haber IDs duplicados
        ids = [r["id"] for r in results]
        assert len(ids) == len(set(ids))

    def test_retrieve_empty(self, retriever):
        results = retriever.retrieve("nonexistent query")
        assert len(results) == 0

    def test_update_episode(self, retriever):
        retriever.add_episode(1, "old content", "old response")
        retriever.update_episode(1, user_input="new content", response="new response")
        with retriever._connect() as conn:
            row = conn.execute(
                "SELECT user_input, response FROM episodes WHERE id = 1"
            ).fetchone()
        assert row[0] == "new content"
        assert row[1] == "new response"

    def test_delete_episode(self, retriever):
        retriever.add_episode(1, "delete me", "response")
        retriever.delete_episode(1)
        with retriever._connect() as conn:
            row = conn.execute("SELECT * FROM episodes WHERE id = 1").fetchone()
        assert row is None

    def test_persistencia(self, tmp_path):
        db_path = tmp_path / "persist_retrieval.db"
        r1 = HybridRetriever(db_path)
        r1.add_episode(1, "persist test", "response")

        r2 = HybridRetriever(db_path)
        with r2._connect() as conn:
            row = conn.execute("SELECT * FROM episodes WHERE id = 1").fetchone()
        assert row is not None
        assert "persist" in row[2]
