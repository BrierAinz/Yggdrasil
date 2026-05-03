"""
Memory Graph
============
Grafo de conocimiento para entidades y relaciones.

Almacena entidades (nodos) y relaciones (aristas) en SQLite.
Soporta:
- Extracción automática de relaciones entre entidades
- Búsqueda de vecinos (entidades relacionadas)
- Path finding (caminos entre entidades)
- Strength decay (relaciones se debilitan con el tiempo)

Inspired by: jcode semantic memory (graph + embeddings)
"""
import json
import sqlite3
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple

import numpy as np
from Lilith.memory.base import DB_PATH


class MemoryGraph:
    """Grafo de entidades y relaciones sobre SQLite."""

    def __init__(self, db_path: Path = DB_PATH):
        self.db = db_path
        self._init_tables()

    def _init_tables(self):
        """Crea tablas para el grafo."""
        with sqlite3.connect(self.db) as conn:
            # Entidades (nodos)
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS entities (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL UNIQUE,
                    type TEXT DEFAULT 'unknown',
                    mentions INTEGER DEFAULT 1,
                    first_seen TEXT,
                    last_seen TEXT
                )
                """
            )

            # Relaciones entre entidades (aristas)
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS relations (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    source TEXT NOT NULL,
                    target TEXT NOT NULL,
                    relation_type TEXT NOT NULL DEFAULT 'related',
                    strength REAL DEFAULT 1.0,
                    first_seen TEXT,
                    last_seen TEXT,
                    context TEXT,
                    UNIQUE(source, target, relation_type)
                )
                """
            )

            # Índices para búsqueda rápida
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_entities_name ON entities(name)"
            )
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_relations_source ON relations(source)"
            )
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_relations_target ON relations(target)"
            )
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_relations_type ON relations(relation_type)"
            )

            conn.commit()

    def add_entity(
        self, name: str, entity_type: str = "unknown", timestamp: str = None
    ):
        """Agrega o actualiza una entidad."""
        if timestamp is None:
            timestamp = datetime.now().isoformat()
        name = name.strip().lower()

        with sqlite3.connect(self.db) as conn:
            existing = conn.execute(
                "SELECT id, mentions FROM entities WHERE name = ?",
                (name,),
            ).fetchone()

            if existing:
                conn.execute(
                    "UPDATE entities SET mentions = mentions + 1, last_seen = ? WHERE id = ?",
                    (timestamp, existing[0]),
                )
            else:
                conn.execute(
                    "INSERT INTO entities (name, type, mentions, first_seen, last_seen) VALUES (?, ?, ?, ?, ?)",
                    (name, entity_type, 1, timestamp, timestamp),
                )
            conn.commit()

    def get_all_entities(self) -> List[Dict]:
        """Obtiene todas las entidades."""
        with sqlite3.connect(self.db) as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute(
                "SELECT name, type, mentions FROM entities ORDER BY mentions DESC"
            ).fetchall()
            return [dict(r) for r in rows]

    def add_relation(
        self,
        source: str,
        target: str,
        relation_type: str = "related",
        strength: float = 1.0,
        context: str = "",
    ):
        """Agrega o actualiza una relación entre dos entidades."""
        now = datetime.now().isoformat()
        source = source.strip().lower()
        target = target.strip().lower()

        # Asegurar que ambas entidades existan
        self.add_entity(source, "unknown", now)
        self.add_entity(target, "unknown", now)

        with sqlite3.connect(self.db) as conn:
            existing = conn.execute(
                "SELECT id, strength FROM relations WHERE source = ? AND target = ? AND relation_type = ?",
                (source, target, relation_type),
            ).fetchone()

            if existing:
                # Reforzar relación existente (max strength 5.0)
                new_strength = min(float(existing[1]) + 0.5, 5.0)
                conn.execute(
                    "UPDATE relations SET strength = ?, last_seen = ?, context = ? WHERE id = ?",
                    (new_strength, now, context[:500], existing[0]),
                )
            else:
                conn.execute(
                    "INSERT INTO relations (source, target, relation_type, strength, first_seen, last_seen, context) VALUES (?, ?, ?, ?, ?, ?, ?)",
                    (
                        source,
                        target,
                        relation_type,
                        float(strength),
                        now,
                        now,
                        context[:500],
                    ),
                )
            conn.commit()

    def get_relations(
        self,
        entity: str,
        relation_type: str = None,
        min_strength: float = 0.5,
    ) -> List[Dict]:
        """Obtiene relaciones de una entidad (como source o target)."""
        entity = entity.strip().lower()

        with sqlite3.connect(self.db) as conn:
            conn.row_factory = sqlite3.Row
            if relation_type:
                rows = conn.execute(
                    """SELECT * FROM relations
                       WHERE (source = ? OR target = ?) AND relation_type = ? AND strength >= ?
                       ORDER BY strength DESC""",
                    (entity, entity, relation_type, min_strength),
                ).fetchall()
            else:
                rows = conn.execute(
                    """SELECT * FROM relations
                       WHERE (source = ? OR target = ?) AND strength >= ?
                       ORDER BY strength DESC""",
                    (entity, entity, min_strength),
                ).fetchall()
            return [dict(r) for r in rows]

    def get_neighbors(
        self, entity: str, min_strength: float = 0.5
    ) -> List[Tuple[str, str, float]]:
        """Obtiene vecinos de una entidad con tipo de relación y strength.

        Returns: [(neighbor_name, relation_type, strength), ...]
        """
        entity = entity.strip().lower()
        relations = self.get_relations(entity, min_strength=min_strength)

        neighbors = []
        for rel in relations:
            if rel["source"] == entity:
                neighbors.append((rel["target"], rel["relation_type"], rel["strength"]))
            else:
                neighbors.append((rel["source"], rel["relation_type"], rel["strength"]))

        # Ordenar por strength descendente
        neighbors.sort(key=lambda x: x[2], reverse=True)
        return neighbors

    def find_path(
        self, source: str, target: str, max_depth: int = 3
    ) -> Optional[List[Dict]]:
        """Encuentra camino entre dos entidades (BFS)."""
        source = source.strip().lower()
        target = target.strip().lower()

        if source == target:
            return []

        visited = {source}
        queue = [(source, [])]

        while queue and max_depth > 0:
            next_queue = []
            for current, path in queue:
                relations = self.get_relations(current, min_strength=0.3)
                for rel in relations:
                    neighbor = (
                        rel["target"] if rel["source"] == current else rel["source"]
                    )
                    if neighbor == target:
                        return path + [rel]
                    if neighbor not in visited:
                        visited.add(neighbor)
                        next_queue.append((neighbor, path + [rel]))
            queue = next_queue
            max_depth -= 1

        return None

    def extract_relations(self, text: str, entities: List[str], timestamp: str = None):
        """Alias de extract_relations_from_text para compatibilidad con tests."""
        self.extract_relations_from_text(text, entities)

    def extract_relations_from_text(self, text: str, entities: List[str]):
        """Extrae relaciones entre entidades mencionadas en el texto."""
        import re

        text_lower = text.lower()

        # Patrones de relación
        relation_patterns = [
            ("uses", [r"{}.*usa\w*.*{}", r"{}.*usando.*{}", r"{}.*utiliza\w*.*{}"]),
            ("depends_on", [r"{}.*depend\w*.*{}", r"{}.*requiere.*{}"]),
            ("contains", [r"{}.*contiene.*{}", r"{}.*dentro de.*{}"]),
            ("related", [r"{}.*y.*{}", r"{}.*con.*{}"]),
        ]

        for i, e1 in enumerate(entities):
            for e2 in entities[i + 1 :]:
                e1_lower = e1.lower()
                e2_lower = e2.lower()

                # Verificar si ambas entidades están en el texto
                if e1_lower not in text_lower or e2_lower not in text_lower:
                    continue

                # Buscar patrones de relación
                for rel_type, patterns in relation_patterns:
                    for pattern in patterns:
                        # Probar ambas direcciones
                        regex = pattern.format(re.escape(e1_lower), re.escape(e2_lower))
                        import re

                        if re.search(regex, text_lower):
                            self.add_relation(e1, e2, rel_type, 1.0, text[:200])
                            break
                        regex = pattern.format(re.escape(e2_lower), re.escape(e1_lower))
                        if re.search(regex, text_lower):
                            self.add_relation(e2, e1, rel_type, 1.0, text[:200])
                            break

    def decay_strength(self, decay_factor: float = 0.95, min_strength: float = 0.1):
        """Reduce la fuerza de relaciones antiguas (llamar periódicamente)."""
        with sqlite3.connect(self.db) as conn:
            conn.execute(
                "UPDATE relations SET strength = strength * ? WHERE strength > ?",
                (decay_factor, min_strength),
            )
            conn.execute("DELETE FROM relations WHERE strength <= ?", (min_strength,))
            conn.commit()

    def get_related_entities(
        self,
        entity: str,
        min_strength: float = 0.5,
        limit: int = 10,
        max_depth: int = 2,
    ) -> List[Dict]:
        """Obtiene entidades relacionadas ordenadas por relevancia (con profundidad).

        Args:
            entity: Entidad central.
            min_strength: Fuerza mínima de relación.
            limit: Máximo de entidades a retornar.
            max_depth: Profundidad de búsqueda en el grafo (1=directos, 2=indirectos).

        Returns:
            Lista de dicts con name, relation_type, strength, depth.
        """
        entity = entity.strip().lower()
        visited = {entity}
        results = []
        current_level = [(entity, 0)]  # (entity_name, depth)

        while current_level and max_depth > 0:
            next_level = []
            for current_ent, depth in current_level:
                neighbors = self.get_neighbors(current_ent, min_strength=min_strength)
                for name, rel_type, strength in neighbors:
                    if name not in visited:
                        visited.add(name)
                        results.append(
                            {
                                "name": name,
                                "relation_type": rel_type,
                                "strength": strength,
                                "depth": depth + 1,
                            }
                        )
                        next_level.append((name, depth + 1))
            current_level = next_level
            max_depth -= 1

        # Ordenar por strength descendente
        results.sort(key=lambda x: x["strength"], reverse=True)
        return results[:limit]

    def get_graph_stats(self) -> Dict:
        """Estadísticas del grafo."""
        with sqlite3.connect(self.db) as conn:
            relations = conn.execute("SELECT COUNT(*) FROM relations").fetchone()[0]
            entities = conn.execute("SELECT COUNT(*) FROM entities").fetchone()[0]
            connected = conn.execute(
                "SELECT COUNT(DISTINCT source) + COUNT(DISTINCT target) FROM relations"
            ).fetchone()[0]
            avg_strength = conn.execute(
                "SELECT AVG(strength) FROM relations"
            ).fetchone()[0]

            return {
                "entities": entities,
                "relations": relations,
                "connected_entities": connected,
                "avg_strength": round(avg_strength or 0, 2),
            }

    def to_dict(self) -> Dict:
        """Exporta el grafo completo como diccionario."""
        with sqlite3.connect(self.db) as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute(
                "SELECT * FROM relations ORDER BY strength DESC"
            ).fetchall()
            return {
                "relations": [dict(r) for r in rows],
                "stats": self.get_graph_stats(),
            }


# Instancia global
_graph_instance: Optional[MemoryGraph] = None


def get_memory_graph() -> MemoryGraph:
    """Obtiene instancia global del grafo."""
    global _graph_instance
    if _graph_instance is None:
        _graph_instance = MemoryGraph()
    return _graph_instance
