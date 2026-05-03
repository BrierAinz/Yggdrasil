"""
Memory Retrieval (Hybrid)
=========================
Sistema de retrieval híbrido que combina:
- Vector search (embeddings + cosine similarity)
- Keyword search (BM25-like sobre SQLite FTS)
- Graph search (vecinos en grafo de conocimiento)
- Recency boost (episodios recientes tienen prioridad)

Inspired by: jcode session search + RAG
"""
import contextlib
import json
import math
import pickle
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import numpy as np
from Lilith.memory.base import DB_PATH, EmbeddingModel, cosine_similarity
from Lilith.memory.memory_graph import MemoryGraph


class HybridRetriever:
    """Retriever híbrido: vector + keyword + graph + recency."""

    def __init__(
        self,
        db_path: Path = DB_PATH,
        vector_weight: float = 0.4,
        keyword_weight: float = 0.3,
        graph_weight: float = 0.2,
        recency_weight: float = 0.1,
    ):
        self.db = db_path
        self.embedder = EmbeddingModel()
        self.graph = MemoryGraph(db_path)

        self.weights = {
            "vector": vector_weight,
            "keyword": keyword_weight,
            "graph": graph_weight,
            "recency": recency_weight,
        }

        self._init_fts()

    def _init_fts(self):
        """Inicializa Full-Text Search en SQLite."""
        with sqlite3.connect(self.db) as conn:
            # Asegurar que la tabla episodes existe (para tests)
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

            # FTS5 para búsqueda por texto
            conn.execute(
                """
                CREATE VIRTUAL TABLE IF NOT EXISTS episodes_fts USING fts5(
                    user_input,
                    response,
                    content=episodes,
                    content_rowid=id
                )
                """
            )

            # Trigger para mantener FTS sincronizado
            conn.execute(
                """
                CREATE TRIGGER IF NOT EXISTS episodes_fts_insert AFTER INSERT ON episodes BEGIN
                    INSERT INTO episodes_fts(rowid, user_input, response)
                    VALUES (new.id, new.user_input, new.response);
                END
                """
            )

            conn.execute(
                """
                CREATE TRIGGER IF NOT EXISTS episodes_fts_delete AFTER DELETE ON episodes BEGIN
                    INSERT INTO episodes_fts(episodes_fts, rowid, user_input, response)
                    VALUES ('delete', old.id, old.user_input, old.response);
                END
                """
            )

            conn.commit()

    def vector_search(self, query: str, limit: int = 20) -> List[Tuple[int, float]]:
        """Búsqueda por similitud vectorial. Retorna (episode_id, score)."""
        if not self.embedder.is_available():
            return []

        query_emb = self.embedder.encode([query])
        if query_emb is None:
            return []

        query_vec = query_emb[0]

        with sqlite3.connect(self.db) as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute(
                """SELECT id, embedding, timestamp FROM episodes
                   WHERE compressed = 0 AND embedding IS NOT NULL
                   ORDER BY timestamp DESC LIMIT 300"""
            ).fetchall()

        scored = []
        for row in rows:
            try:
                emb = pickle.loads(row["embedding"])
                sim = cosine_similarity(query_vec, emb)
                scored.append((row["id"], sim))
            except Exception:
                continue

        scored.sort(key=lambda x: x[1], reverse=True)
        return scored[:limit]

    def keyword_search(self, query: str, limit: int = 20) -> List[Tuple[int, float]]:
        """Búsqueda por keywords (FTS5 + BM25-like). Retorna (episode_id, score)."""
        with sqlite3.connect(self.db) as conn:
            conn.row_factory = sqlite3.Row
            # FTS5 search
            rows = conn.execute(
                """SELECT rowid as id, rank FROM episodes_fts
                   WHERE episodes_fts MATCH ?
                   ORDER BY rank LIMIT ?""",
                (query, limit * 2),
            ).fetchall()

            if not rows:
                # Fallback: LIKE search
                query_lower = f"%{query.lower()}%"
                rows = conn.execute(
                    """SELECT id, 0 as rank FROM episodes
                       WHERE LOWER(user_input) LIKE ? OR LOWER(response) LIKE ?
                       ORDER BY timestamp DESC LIMIT ?""",
                    (query_lower, query_lower, limit),
                ).fetchall()

        # Normalizar scores (FTS rank es negativo, menor = mejor)
        scored = []
        for row in rows:
            # Convertir rank a score positivo (0-1)
            rank = row["rank"] if row["rank"] is not None else -1
            score = 1.0 / (1.0 + abs(rank))
            scored.append((row["id"], score))

        scored.sort(key=lambda x: x[1], reverse=True)
        return scored[:limit]

    def graph_search(self, query: str, limit: int = 20) -> List[Tuple[int, float]]:
        """Búsqueda por grafo: encuentra episodios relacionados con entidades del query."""
        # Extraer entidades del query (simple: palabras de >3 chars)
        words = [w.lower() for w in query.split() if len(w) > 3]

        related_entities = set()
        for word in words:
            neighbors = self.graph.get_neighbors(word, min_strength=0.3)
            for neighbor, _, strength in neighbors:
                related_entities.add((neighbor, strength))

        if not related_entities:
            return []

        # Buscar episodios que mencionen entidades relacionadas
        with sqlite3.connect(self.db) as conn:
            conn.row_factory = sqlite3.Row
            all_scores = {}

            for entity, strength in related_entities:
                rows = conn.execute(
                    """SELECT id FROM episodes
                       WHERE compressed = 0 AND (LOWER(user_input) LIKE ? OR LOWER(response) LIKE ?)
                       ORDER BY timestamp DESC LIMIT 50""",
                    (f"%{entity}%", f"%{entity}%"),
                ).fetchall()

                for row in rows:
                    eid = row["id"]
                    # Score = strength de la relación
                    if eid not in all_scores or all_scores[eid] < strength:
                        all_scores[eid] = strength

        scored = [(eid, score) for eid, score in all_scores.items()]
        scored.sort(key=lambda x: x[1], reverse=True)
        return scored[:limit]

    def recency_search(self, limit: int = 20) -> List[Tuple[int, float]]:
        """Score por recencia (exponencial decay)."""
        with sqlite3.connect(self.db) as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute(
                """SELECT id, timestamp FROM episodes
                   WHERE compressed = 0
                   ORDER BY timestamp DESC LIMIT ?""",
                (limit * 2,),
            ).fetchall()

        scored = []
        now = datetime.now()
        for row in rows:
            try:
                ts = datetime.fromisoformat(row["timestamp"])
                age_days = (now - ts).days
                # Exponential decay: score = exp(-age/7)
                score = math.exp(-age_days / 7.0)
                scored.append((row["id"], score))
            except Exception:
                continue

        scored.sort(key=lambda x: x[1], reverse=True)
        return scored[:limit]

    def retrieve(
        self,
        query: str,
        limit: int = 10,
        include_sources: bool = False,
    ) -> List[Dict]:
        """
        Retrieval híbrido principal.

        Combina vector + keyword + graph + recency con weights configurables.
        Retorna episodios enriquecidos con score combinado.
        """
        # Obtener resultados de cada fuente
        vector_results = self.vector_search(query, limit=limit * 2)
        keyword_results = self.keyword_search(query, limit=limit * 2)
        graph_results = self.graph_search(query, limit=limit * 2)
        recency_results = self.recency_search(limit=limit * 2)

        # Combinar scores
        all_episodes: Dict[int, Dict[str, float]] = {}

        for source, results in [
            ("vector", vector_results),
            ("keyword", keyword_results),
            ("graph", graph_results),
            ("recency", recency_results),
        ]:
            weight = self.weights[source]
            for eid, score in results:
                if eid not in all_episodes:
                    all_episodes[eid] = {}
                all_episodes[eid][source] = score * weight

        # Calcular score combinado
        combined = []
        for eid, scores in all_episodes.items():
            total = sum(scores.values())
            # Bonus por diversidad de fuentes
            diversity_bonus = 0.05 * len(scores)
            combined.append((eid, total + diversity_bonus, scores))

        combined.sort(key=lambda x: x[1], reverse=True)
        top_ids = [eid for eid, _, _ in combined[:limit]]

        if not top_ids:
            return []

        # Obtener contenido completo
        placeholders = ",".join("?" * len(top_ids))
        with sqlite3.connect(self.db) as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute(
                f"SELECT * FROM episodes WHERE id IN ({placeholders}) ORDER BY timestamp DESC",
                top_ids,
            ).fetchall()

        # Construir resultado enriquecido
        episodes = []
        for row in rows:
            ep = dict(row)
            eid = ep["id"]
            # Encontrar score combinado
            for cid, score, sources in combined:
                if cid == eid:
                    ep["retrieval_score"] = round(score, 3)
                    if include_sources:
                        ep["retrieval_sources"] = {
                            k: round(v, 3) for k, v in sources.items()
                        }
                    break
            episodes.append(ep)

        # Ordenar por retrieval_score
        episodes.sort(key=lambda x: x.get("retrieval_score", 0), reverse=True)
        return episodes

    def retrieve_with_context(self, query: str, max_tokens: int = 2000) -> str:
        """Retorna texto formateado para inyectar en prompt."""
        episodes = self.retrieve(query, limit=8, include_sources=False)

        if not episodes:
            return ""

        parts = ["CONTEXTO RELEVANTE DE MEMORIA:\n"]
        total_chars = 0

        for ep in episodes:
            text = f"- [{ep['timestamp'][:10]}] Tu: {ep['user_input'][:100]}"
            if ep.get("response"):
                text += f" | Lilith: {ep['response'][:100]}"
            text += f" [score: {ep.get('retrieval_score', 0)}]\n"

            if total_chars + len(text) > max_tokens * 4:
                break

            parts.append(text)
            total_chars += len(text)

        return "".join(parts)

    def _connect(self):
        """Context manager para conexiones SQLite."""
        import contextlib

        return contextlib.closing(sqlite3.connect(self.db))

    def add_episode(
        self,
        episode_id: int,
        user_input: str,
        response: str = "",
        context: str = "",
        timestamp: str = None,
    ):
        """Agrega un episodio a la base de datos."""
        if timestamp is None:
            timestamp = datetime.now().isoformat()
        with sqlite3.connect(self.db) as conn:
            conn.execute(
                """INSERT OR REPLACE INTO episodes (id, timestamp, user_input, response, context)
                   VALUES (?, ?, ?, ?, ?)""",
                (episode_id, timestamp, user_input, response, context),
            )
            conn.commit()

    def update_episode(
        self,
        episode_id: int,
        user_input: str = None,
        response: str = None,
        context: str = None,
    ):
        """Actualiza campos de un episodio."""
        with sqlite3.connect(self.db) as conn:
            if user_input is not None:
                conn.execute(
                    "UPDATE episodes SET user_input = ? WHERE id = ?",
                    (user_input, episode_id),
                )
            if response is not None:
                conn.execute(
                    "UPDATE episodes SET response = ? WHERE id = ?",
                    (response, episode_id),
                )
            if context is not None:
                conn.execute(
                    "UPDATE episodes SET context = ? WHERE id = ?",
                    (context, episode_id),
                )
            conn.commit()

    def delete_episode(self, episode_id: int):
        """Elimina un episodio."""
        with sqlite3.connect(self.db) as conn:
            conn.execute("DELETE FROM episodes WHERE id = ?", (episode_id,))
            conn.commit()

    def get_stats(self) -> Dict:
        """Estadísticas del retriever."""
        return {
            "weights": self.weights,
            "graph_stats": self.graph.get_graph_stats(),
        }


# Instancia global
_retriever_instance: Optional[HybridRetriever] = None


def get_retriever() -> HybridRetriever:
    """Obtiene instancia global del retriever."""
    global _retriever_instance
    if _retriever_instance is None:
        _retriever_instance = HybridRetriever()
    return _retriever_instance
