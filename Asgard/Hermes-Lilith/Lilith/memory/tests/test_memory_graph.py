"""
Tests para Memory Graph
=======================
RED-GREEN-REFACTOR: TDD estricto para el grafo de conocimiento.
"""
from pathlib import Path

import pytest
from Lilith.memory.memory_graph import MemoryGraph


class TestMemoryGraph:
    """Tests para el grafo de entidades y relaciones."""

    @pytest.fixture
    def graph(self, tmp_path):
        db_path = tmp_path / "test_graph.db"
        return MemoryGraph(db_path)

    def test_add_entity(self, graph):
        graph.add_entity("Python", "language", "2026-05-01")
        entities = graph.get_all_entities()
        assert len(entities) == 1
        assert entities[0]["name"] == "python"  # lowercase
        assert entities[0]["type"] == "language"
        assert entities[0]["mentions"] == 1

    def test_add_duplicate_entity_increments_mentions(self, graph):
        graph.add_entity("Python", "language", "2026-05-01")
        graph.add_entity("Python", "language", "2026-05-01")
        entities = graph.get_all_entities()
        assert len(entities) == 1
        assert entities[0]["mentions"] == 2

    def test_add_relation(self, graph):
        graph.add_entity("Python", "language", "2026-05-01")
        graph.add_entity("FastAPI", "framework", "2026-05-01")
        graph.add_relation("Python", "FastAPI", "uses")
        relations = graph.get_relations("Python")
        assert len(relations) == 1
        assert relations[0]["relation_type"] == "uses"
        assert relations[0]["source"] == "python"
        assert relations[0]["target"] == "fastapi"

    def test_add_relation_creates_entities(self, graph):
        # add_relation debe crear entidades automaticamente
        graph.add_relation("A", "B", "relates_to")
        entities = graph.get_all_entities()
        assert len(entities) == 2
        names = {e["name"] for e in entities}
        assert names == {"a", "b"}

    def test_relation_strength_increments(self, graph):
        graph.add_relation("A", "B", "relates_to", strength=1.0)
        graph.add_relation("A", "B", "relates_to", strength=1.0)
        relations = graph.get_relations("A")
        assert len(relations) == 1
        # Se refuerza: min(1.0 + 0.5, 5.0) = 1.5
        assert relations[0]["strength"] == 1.5

    def test_get_neighbors_min_strength(self, graph):
        graph.add_relation("A", "B", "relates_to", strength=2.0)
        graph.add_relation("A", "C", "relates_to", strength=0.3)
        neighbors = graph.get_neighbors("A", min_strength=0.5)
        names = [n[0] for n in neighbors]
        assert "b" in names
        assert "c" not in names  # strength 0.3 < 0.5

    def test_get_related_entities(self, graph):
        graph.add_relation("A", "B", "relates_to")
        graph.add_relation("B", "C", "relates_to")
        related = graph.get_related_entities("A", max_depth=2)
        names = {r["name"] for r in related}
        assert "b" in names
        assert "c" in names  # indirecto depth=2

    def test_get_graph_stats(self, graph):
        graph.add_entity("A", "test")
        graph.add_entity("B", "test")
        graph.add_entity("C", "test")
        graph.add_relation("A", "B", "relates_to")
        graph.add_relation("B", "C", "relates_to")
        stats = graph.get_graph_stats()
        assert stats["entities"] == 3
        assert stats["relations"] == 2
        assert stats["avg_strength"] > 0

    def test_extract_relations(self, graph):
        text = "Python usa FastAPI para construir APIs web"
        entities = ["Python", "FastAPI"]
        graph.extract_relations(text, entities, "2026-05-01")
        relations = graph.get_relations("Python")
        assert len(relations) >= 1
        assert relations[0]["relation_type"] == "uses"

    def test_persistencia(self, tmp_path):
        db_path = tmp_path / "persist_graph.db"
        g1 = MemoryGraph(db_path)
        g1.add_entity("Persist", "test", "2026-05-01")
        g1.add_relation("Persist", "Test", "relates_to")

        # Nueva instancia, mismo archivo
        g2 = MemoryGraph(db_path)
        entities = g2.get_all_entities()
        assert len(entities) == 2
        names = {e["name"] for e in entities}
        assert "persist" in names
        assert "test" in names
