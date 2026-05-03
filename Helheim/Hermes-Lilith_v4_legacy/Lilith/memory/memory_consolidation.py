"""
Memory Consolidation
====================
Consolidación inteligente de episodios de memoria.

Algoritmos:
- Merge: combina episodios similares en uno solo
- Deduplication: elimina episodios redundantes
- Summarization: resume grupos de episodios relacionados
- Forgetting: descarta episodios de baja relevancia

Inspired by: jcode memory consolidation + human memory models
"""
import json
import sqlite3
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import numpy as np
from Lilith.memory.base import DB_PATH, EmbeddingModel, cosine_similarity


class MemoryConsolidation:
    """Consolidador de memoria episódica."""

    def __init__(self, db_path: Path = DB_PATH):
        self.db = db_path
        self.embedder = EmbeddingModel()
        self._init_tables()

    def _init_tables(self):
        """Crea tablas para consolidación."""
        with sqlite3.connect(self.db) as conn:
            # Cola de consolidación (episodios pendientes)
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS consolidation_queue (
                    id INTEGER PRIMARY KEY,
                    episode_id INTEGER NOT NULL,
                    added_at TEXT NOT NULL,
                    priority REAL DEFAULT 1.0,
                    FOREIGN KEY (episode_id) REFERENCES episodes(id)
                )
                """
            )

            # Episodios consolidados (merged)
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS consolidated_episodes (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT NOT NULL,
                    content TEXT NOT NULL,
                    source_episodes TEXT,
                    embedding BLOB,
                    relevance_score REAL DEFAULT 1.0
                )
                """
            )

            conn.commit()

    def add_to_queue(
        self, episode_id: int, user_input: str, response: str, priority: float = 1.0
    ):
        """Agrega un episodio a la cola de consolidacion (API publica)."""
        now = datetime.now().isoformat()
        with sqlite3.connect(self.db) as conn:
            # Verificar si ya esta en cola
            existing = conn.execute(
                "SELECT 1 FROM consolidation_queue WHERE episode_id = ?",
                (episode_id,),
            ).fetchone()
            if existing:
                return
            # Insertar episodio si no existe
            cursor = conn.execute(
                "INSERT OR IGNORE INTO episodes (id, timestamp, user_input, response) VALUES (?, ?, ?, ?)",
                (episode_id, now, user_input, response),
            )
            conn.execute(
                "INSERT INTO consolidation_queue (episode_id, added_at, priority) VALUES (?, ?, ?)",
                (episode_id, now, priority),
            )
            conn.commit()

    def queue_for_consolidation(self, episode_id: int, priority: float = 1.0):
        """Agrega un episodio a la cola de consolidacion."""
        now = datetime.now().isoformat()
        with sqlite3.connect(self.db) as conn:
            conn.execute(
                "INSERT OR IGNORE INTO consolidation_queue (episode_id, added_at, priority) VALUES (?, ?, ?)",
                (episode_id, now, priority),
            )
            conn.commit()

    def find_similar_episodes(
        self, episode_id: int, threshold: float = 0.85
    ) -> List[int]:
        """Encuentra episodios similares al dado por similitud de embeddings."""
        with sqlite3.connect(self.db) as conn:
            conn.row_factory = sqlite3.Row
            # Obtener embedding del episodio objetivo
            row = conn.execute(
                "SELECT embedding, user_input FROM episodes WHERE id = ?", (episode_id,)
            ).fetchone()

            if not row or not row["embedding"]:
                return []

            target_emb = np.frombuffer(row["embedding"], dtype=np.float32)
            # Si no se puede deserializar con numpy, intentar con pickle
            if target_emb.size == 0:
                import pickle

                target_emb = pickle.loads(row["embedding"])

            # Buscar candidatos recientes (últimos 200)
            candidates = conn.execute(
                "SELECT id, embedding FROM episodes WHERE id != ? AND embedding IS NOT NULL ORDER BY timestamp DESC LIMIT 200",
                (episode_id,),
            ).fetchall()

            similar = []
            for cand in candidates:
                try:
                    cand_emb = np.frombuffer(cand["embedding"], dtype=np.float32)
                    if cand_emb.size == 0:
                        import pickle

                        cand_emb = pickle.loads(cand["embedding"])
                    sim = cosine_similarity(target_emb, cand_emb)
                    if sim >= threshold:
                        similar.append((cand["id"], sim))
                except Exception:
                    continue

            similar.sort(key=lambda x: x[1], reverse=True)
            return [sid for sid, _ in similar[:10]]

    def merge_episodes(self, episode_ids: List[int]) -> Optional[int]:
        """Combina múltiples episodios similares en uno consolidado."""
        if len(episode_ids) < 2:
            return None

        with sqlite3.connect(self.db) as conn:
            conn.row_factory = sqlite3.Row
            episodes = []
            for eid in episode_ids:
                row = conn.execute(
                    "SELECT * FROM episodes WHERE id = ?", (eid,)
                ).fetchone()
                if row:
                    episodes.append(dict(row))

            if len(episodes) < 2:
                return None

            # Crear contenido mergeado
            inputs = [ep["user_input"] for ep in episodes]
            responses = [ep["response"] for ep in episodes if ep["response"]]

            merged_input = self._merge_texts(inputs)
            merged_response = self._merge_texts(responses) if responses else ""

            content = f"Usuario: {merged_input}\n"
            if merged_response:
                content += f"Lilith: {merged_response}\n"

            # Timestamp del episodio más reciente
            timestamps = [ep["timestamp"] for ep in episodes]
            latest_ts = max(timestamps)

            # Calcular relevance score (basado en frecuencia y recencia)
            age_days = (datetime.now() - datetime.fromisoformat(latest_ts)).days
            recency_score = max(0, 1.0 - age_days / 30)
            frequency_score = min(len(episodes) / 5, 1.0)
            relevance = (recency_score + frequency_score) / 2

            # Generar embedding del contenido mergeado
            embedding_blob = None
            if self.embedder.is_available():
                emb = self.embedder.encode([merged_input])
                if emb is not None:
                    import pickle

                    embedding_blob = pickle.dumps(emb[0])

            # Insertar episodio consolidado
            cursor = conn.execute(
                "INSERT INTO consolidated_episodes (timestamp, content, source_episodes, embedding, relevance_score) VALUES (?, ?, ?, ?, ?)",
                (
                    latest_ts,
                    content,
                    json.dumps(episode_ids),
                    embedding_blob,
                    relevance,
                ),
            )
            consolidated_id = cursor.lastrowid

            # Marcar episodios originales como comprimidos
            placeholders = ",".join("?" * len(episode_ids))
            conn.execute(
                f"UPDATE episodes SET compressed = 1 WHERE id IN ({placeholders})",
                episode_ids,
            )

            # Limpiar cola
            conn.execute(
                f"DELETE FROM consolidation_queue WHERE episode_id IN ({placeholders})",
                episode_ids,
            )

            conn.commit()
            return consolidated_id

    def _merge_texts(self, texts: List[str]) -> str:
        """Mergea múltiples textos eliminando redundancia."""
        if not texts:
            return ""
        if len(texts) == 1:
            return texts[0]

        # Estrategia simple: unión de oraciones únicas
        sentences = set()
        for text in texts:
            for sent in text.split("."):
                sent = sent.strip()
                if sent and len(sent) > 10:
                    sentences.add(sent)

        # Ordenar por longitud (más informativas primero) y limitar
        sorted_sents = sorted(sentences, key=len, reverse=True)
        merged = ". ".join(sorted_sents[:5])
        return merged + "." if not merged.endswith(".") else merged

    def deduplicate_episodes(self, threshold: float = 0.95) -> int:
        """Elimina episodios duplicados (muy similares). Retorna cantidad eliminada."""
        with sqlite3.connect(self.db) as conn:
            conn.row_factory = sqlite3.Row
            episodes = conn.execute(
                "SELECT id, embedding, user_input FROM episodes WHERE compressed = 0 AND embedding IS NOT NULL ORDER BY timestamp DESC"
            ).fetchall()

            if len(episodes) < 2:
                return 0

            to_compress = set()

            for i, ep1 in enumerate(episodes):
                if ep1["id"] in to_compress:
                    continue

                try:
                    emb1 = np.frombuffer(ep1["embedding"], dtype=np.float32)
                    if emb1.size == 0:
                        import pickle

                        emb1 = pickle.loads(ep1["embedding"])
                except Exception:
                    continue

                for ep2 in episodes[i + 1 :]:
                    if ep2["id"] in to_compress:
                        continue

                    try:
                        emb2 = np.frombuffer(ep2["embedding"], dtype=np.float32)
                        if emb2.size == 0:
                            import pickle

                            emb2 = pickle.loads(ep2["embedding"])
                        sim = cosine_similarity(emb1, emb2)
                        if sim >= threshold:
                            to_compress.add(ep2["id"])
                    except Exception:
                        continue

            if to_compress:
                placeholders = ",".join("?" * len(to_compress))
                conn.execute(
                    f"UPDATE episodes SET compressed = 1 WHERE id IN ({placeholders})",
                    list(to_compress),
                )
                conn.commit()

            return len(to_compress)

    def forget_old_episodes(self, days: int = 90, min_mentions: int = 1):
        """Marca episodios antiguos de baja relevancia como olvidados."""
        cutoff = (datetime.now() - timedelta(days=days)).isoformat()

        with sqlite3.connect(self.db) as conn:
            # Episodios antiguos no mencionados recientemente
            old = conn.execute(
                "SELECT id FROM episodes WHERE timestamp < ? AND compressed = 0",
                (cutoff,),
            ).fetchall()

            if old:
                ids = [r[0] for r in old]
                placeholders = ",".join("?" * len(ids))
                conn.execute(
                    f"UPDATE episodes SET compressed = 1 WHERE id IN ({placeholders})",
                    ids,
                )
                conn.commit()

            return len(old)

    def consolidate_episodes(self) -> Dict:
        """Alias público de consolidate_batch para compatibilidad con tests."""
        return self.consolidate_batch(batch_size=20)

    def consolidate_batch(self, batch_size: int = 20) -> Dict:
        """Ejecuta consolidación en lote. Retorna estadísticas."""
        with sqlite3.connect(self.db) as conn:
            queue = conn.execute(
                "SELECT episode_id FROM consolidation_queue ORDER BY priority DESC LIMIT ?",
                (batch_size,),
            ).fetchall()

        merged_count = 0
        deduped_count = 0

        for (episode_id,) in queue:
            similar = self.find_similar_episodes(episode_id)
            if len(similar) >= 2:
                # Incluir el episodio original
                all_ids = [episode_id] + similar
                result = self.merge_episodes(all_ids)
                if result:
                    merged_count += 1

        # Deduplicación general
        deduped_count = self.deduplicate_episodes()

        return {
            "merged_groups": merged_count,
            "deduplicated": deduped_count,
            "processed": len(queue),
        }

    def get_consolidated_episodes(self, limit: int = 10) -> List[Dict]:
        """Obtiene episodios consolidados."""
        with sqlite3.connect(self.db) as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute(
                "SELECT * FROM consolidated_episodes ORDER BY relevance_score DESC, timestamp DESC LIMIT ?",
                (limit,),
            ).fetchall()
            return [dict(r) for r in rows]

    def get_stats(self) -> Dict:
        """Estadísticas de consolidación."""
        with sqlite3.connect(self.db) as conn:
            queue_size = conn.execute(
                "SELECT COUNT(*) FROM consolidation_queue"
            ).fetchone()[0]
            consolidated = conn.execute(
                "SELECT COUNT(*) FROM consolidated_episodes"
            ).fetchone()[0]
            return {
                "queue_size": queue_size,
                "consolidated_episodes": consolidated,
            }


# Instancia global
_consolidation_instance: Optional[MemoryConsolidation] = None


def get_consolidation() -> MemoryConsolidation:
    """Obtiene instancia global del consolidador."""
    global _consolidation_instance
    if _consolidation_instance is None:
        _consolidation_instance = MemoryConsolidation()
    return _consolidation_instance
