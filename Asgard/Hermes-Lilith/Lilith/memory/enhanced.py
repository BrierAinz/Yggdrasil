"""
Enhanced Memory System
======================
Sistema de memoria mejorado con:
- Embeddings semanticos (sentence-transformers)
- Almacenamiento vectorial en SQLite
- Compresion automatica de historial
- Extraccion de entidades
- Busqueda por similitud coseno
"""
import json
import pickle
import re
import sqlite3
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
from Lilith.memory.base import DB_PATH, EmbeddingModel, cosine_similarity
from Lilith.memory.memory_consolidation import get_consolidation
from Lilith.memory.memory_graph import get_memory_graph
from Lilith.memory.memory_retrieval import get_retriever


class EnhancedMemory:
    """
    Sistema de memoria hibrido con embeddings semanticos.
    Usa SQLite para almacenamiento y sentence-transformers para embeddings.

    v2.0: Integra grafo de conocimiento, consolidacion y retrieval hibrido.
    """

    def __init__(self):
        self.db = DB_PATH
        self.embedder = EmbeddingModel()
        self.graph = get_memory_graph()
        self.consolidation = get_consolidation()
        self.retriever = get_retriever()
        self._init_db()

    def _init_db(self):
        """Inicializa tablas de SQLite."""
        with sqlite3.connect(self.db) as conn:
            # Episodios de conversacion
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS episodes (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT NOT NULL,
                    user_input TEXT NOT NULL,
                    response TEXT,
                    tools_used TEXT,
                    embedding BLOB,
                    session_id TEXT DEFAULT 'default',
                    compressed INTEGER DEFAULT 0
                )
            """
            )

            # Resumenes comprimidos
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS summaries (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT NOT NULL,
                    period_start TEXT,
                    period_end TEXT,
                    content TEXT NOT NULL,
                    embedding BLOB,
                    episode_count INTEGER
                )
            """
            )

            # Entidades extraidas
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS entities (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL UNIQUE,
                    type TEXT NOT NULL,
                    first_seen TEXT,
                    last_seen TEXT,
                    mentions INTEGER DEFAULT 1,
                    context TEXT,
                    embedding BLOB
                )
            """
            )

            # Hechos/facts
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS facts (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    category TEXT NOT NULL,
                    key TEXT NOT NULL,
                    value TEXT NOT NULL,
                    confidence REAL DEFAULT 1.0,
                    created TEXT,
                    updated TEXT,
                    UNIQUE(category, key)
                )
            """
            )

            # Errores y soluciones
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS errors (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT,
                    error_type TEXT,
                    message TEXT,
                    solution TEXT,
                    context TEXT,
                    times_seen INTEGER DEFAULT 1
                )
            """
            )

            # Indices para busqueda rapida
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_episodes_time ON episodes(timestamp)"
            )
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_episodes_session ON episodes(session_id)"
            )
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_entities_name ON entities(name)"
            )
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_entities_type ON entities(type)"
            )
            conn.execute("CREATE INDEX IF NOT EXISTS idx_facts_cat ON facts(category)")

            conn.commit()

    # ============================================================
    # EPISODIOS
    # ============================================================

    def add_episode(
        self,
        user_input: str,
        response: str = "",
        tools_used: List[str] = None,
        session_id: str = "default",
    ) -> int:
        """Agrega un episodio de conversacion con embedding."""
        timestamp = datetime.now().isoformat()
        tools_json = json.dumps(tools_used or [])

        # Generar embedding del input del usuario
        embedding_blob = None
        if self.embedder.is_available():
            emb = self.embedder.encode([user_input])
            if emb is not None:
                embedding_blob = pickle.dumps(emb[0])

        with sqlite3.connect(self.db) as conn:
            cursor = conn.execute(
                "INSERT INTO episodes (timestamp, user_input, response, tools_used, embedding, session_id) VALUES (?, ?, ?, ?, ?, ?)",
                (
                    timestamp,
                    user_input,
                    response[:2000],
                    tools_json,
                    embedding_blob,
                    session_id,
                ),
            )
            episode_id = cursor.lastrowid
            conn.commit()

        # Extraer entidades del input
        entities = self._extract_entities(user_input, timestamp)

        # Extraer relaciones entre entidades
        if entities:
            self.graph.extract_relations_from_text(user_input, entities)

        # Agregar a cola de consolidación
        self.consolidation.queue_for_consolidation(episode_id)

        # Verificar si necesita compresion
        self._check_compression()

        return episode_id

    def get_recent_episodes(
        self, count: int = 10, session_id: str = None
    ) -> List[Dict]:
        """Obtiene episodios recientes."""
        with sqlite3.connect(self.db) as conn:
            conn.row_factory = sqlite3.Row
            if session_id:
                rows = conn.execute(
                    "SELECT * FROM episodes WHERE session_id = ? ORDER BY timestamp DESC LIMIT ?",
                    (session_id, count),
                ).fetchall()
            else:
                rows = conn.execute(
                    "SELECT * FROM episodes ORDER BY timestamp DESC LIMIT ?", (count,)
                ).fetchall()
            return [dict(r) for r in rows]

    def search_episodes(self, query: str, limit: int = 5) -> List[Dict]:
        """Busca episodios por similitud semantica."""
        if not self.embedder.is_available():
            # Fallback a busqueda por texto
            return self._search_episodes_text(query, limit)

        query_emb = self.embedder.encode([query])
        if query_emb is None:
            return self._search_episodes_text(query, limit)

        query_vec = query_emb[0]

        with sqlite3.connect(self.db) as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute(
                "SELECT * FROM episodes WHERE embedding IS NOT NULL ORDER BY timestamp DESC LIMIT 200"
            ).fetchall()

        scored = []
        for row in rows:
            emb = pickle.loads(row["embedding"])
            sim = cosine_similarity(query_vec, emb)
            scored.append((sim, dict(row)))

        scored.sort(key=lambda x: x[0], reverse=True)
        return [item for _, item in scored[:limit]]

    def _search_episodes_text(self, query: str, limit: int) -> List[Dict]:
        """Busqueda por texto como fallback."""
        query_lower = f"%{query.lower()}%"
        with sqlite3.connect(self.db) as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute(
                "SELECT * FROM episodes WHERE LOWER(user_input) LIKE ? OR LOWER(response) LIKE ? ORDER BY timestamp DESC LIMIT ?",
                (query_lower, query_lower, limit),
            ).fetchall()
            return [dict(r) for r in rows]

    # ============================================================
    # COMPRESION
    # ============================================================

    def _check_compression(self):
        """Comprime episodios viejos si hay mas de 100."""
        with sqlite3.connect(self.db) as conn:
            count = conn.execute(
                "SELECT COUNT(*) FROM episodes WHERE compressed = 0"
            ).fetchone()[0]

        if count > 100:
            self.compress_old_episodes()

    def compress_old_episodes(self, keep_recent: int = 50):
        """Resume episodios viejos y los archiva."""
        with sqlite3.connect(self.db) as conn:
            conn.row_factory = sqlite3.Row
            old = conn.execute(
                "SELECT * FROM episodes WHERE compressed = 0 ORDER BY timestamp ASC LIMIT ?",
                (keep_recent,),
            ).fetchall()

            if len(old) < 30:
                return

            # Obtener los mas viejos para comprimir
            to_compress = conn.execute(
                "SELECT * FROM episodes WHERE compressed = 0 ORDER BY timestamp ASC LIMIT ?",
                (len(old) - keep_recent,),
            ).fetchall()

        if len(to_compress) < 10:
            return

        # Crear resumen
        lines = []
        for ep in to_compress:
            lines.append(f"Usuario: {ep['user_input'][:100]}")
            if ep["response"]:
                lines.append(f"Lilith: {ep['response'][:100]}")

        summary_text = f"Periodo: {to_compress[0]['timestamp'][:10]} a {to_compress[-1]['timestamp'][:10]}. "
        summary_text += f"{len(to_compress)} interacciones. "
        summary_text += "Temas: " + ", ".join(
            set(ep["user_input"].split()[0:3] for ep in to_compress)[:5]
        )

        # Guardar resumen
        embedding_blob = None
        if self.embedder.is_available():
            emb = self.embedder.encode([summary_text])
            if emb is not None:
                embedding_blob = pickle.dumps(emb[0])

        with sqlite3.connect(self.db) as conn:
            conn.execute(
                "INSERT INTO summaries (timestamp, period_start, period_end, content, embedding, episode_count) VALUES (?, ?, ?, ?, ?, ?)",
                (
                    datetime.now().isoformat(),
                    to_compress[0]["timestamp"],
                    to_compress[-1]["timestamp"],
                    summary_text,
                    embedding_blob,
                    len(to_compress),
                ),
            )

            # Marcar como comprimidos (no borrar, solo marcar)
            ids = [ep["id"] for ep in to_compress]
            placeholders = ",".join("?" * len(ids))
            conn.execute(
                f"UPDATE episodes SET compressed = 1 WHERE id IN ({placeholders})", ids
            )
            conn.commit()

    def get_summaries(self, limit: int = 10) -> List[Dict]:
        """Obtiene resumenes comprimidos."""
        with sqlite3.connect(self.db) as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute(
                "SELECT * FROM summaries ORDER BY timestamp DESC LIMIT ?", (limit,)
            ).fetchall()
            return [dict(r) for r in rows]

    # ============================================================
    # ENTIDADES
    # ============================================================

    def _extract_entities(self, text: str, timestamp: str) -> List[str]:
        """Extrae entidades del texto. Retorna lista de nombres encontrados."""
        found = []

        # Proyectos/carpetas
        project_patterns = [
            r'(?:proyecto|project|carpeta|folder|directorio|path|ruta)\s+["\']?([A-Za-z_][A-Za-z0-9_-]*)["\']?',
            r"[A-Z][a-z]+[A-Z][a-zA-Z]*",  # CamelCase
        ]

        # Tecnologias
        tech_keywords = [
            "python",
            "javascript",
            "typescript",
            "react",
            "vue",
            "angular",
            "docker",
            "kubernetes",
            "aws",
            "azure",
            "gcp",
            "linux",
            "windows",
            "git",
            "github",
            "gitlab",
            "npm",
            "pip",
            "conda",
            "venv",
            "postgres",
            "mysql",
            "mongodb",
            "redis",
            "sqlite",
            "fastapi",
            "flask",
            "django",
            "express",
            "spring",
            "tensorflow",
            "pytorch",
            "sklearn",
            "pandas",
            "numpy",
        ]

        text_lower = text.lower()

        # Extraer tecnologias
        for tech in tech_keywords:
            if tech in text_lower:
                self._upsert_entity(tech, "technology", timestamp, text)
                found.append(tech)

        # Extraer proyectos CamelCase
        for pattern in project_patterns:
            matches = re.findall(pattern, text)
            for match in matches:
                if len(match) > 2 and match.lower() not in tech_keywords:
                    self._upsert_entity(match, "project", timestamp, text)
                    found.append(match)

        return found

    def _upsert_entity(self, name: str, entity_type: str, timestamp: str, context: str):
        """Inserta o actualiza una entidad."""
        name = name.strip()
        if len(name) < 2:
            return

        with sqlite3.connect(self.db) as conn:
            existing = conn.execute(
                "SELECT id, mentions FROM entities WHERE name = ? COLLATE NOCASE",
                (name,),
            ).fetchone()

            if existing:
                conn.execute(
                    "UPDATE entities SET last_seen = ?, mentions = ?, context = ? WHERE id = ?",
                    (timestamp, existing[1] + 1, context[:500], existing[0]),
                )
            else:
                conn.execute(
                    "INSERT INTO entities (name, type, first_seen, last_seen, mentions, context) VALUES (?, ?, ?, ?, ?, ?)",
                    (name, entity_type, timestamp, timestamp, 1, context[:500]),
                )
            conn.commit()

    def get_entities(
        self, entity_type: str = None, min_mentions: int = 1
    ) -> List[Dict]:
        """Obtiene entidades."""
        with sqlite3.connect(self.db) as conn:
            conn.row_factory = sqlite3.Row
            if entity_type:
                rows = conn.execute(
                    "SELECT * FROM entities WHERE type = ? AND mentions >= ? ORDER BY mentions DESC",
                    (entity_type, min_mentions),
                ).fetchall()
            else:
                rows = conn.execute(
                    "SELECT * FROM entities WHERE mentions >= ? ORDER BY mentions DESC",
                    (min_mentions,),
                ).fetchall()
            return [dict(r) for r in rows]

    def search_entities(self, query: str) -> List[Dict]:
        """Busca entidades por nombre."""
        with sqlite3.connect(self.db) as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute(
                "SELECT * FROM entities WHERE name LIKE ? ORDER BY mentions DESC",
                (f"%{query}%",),
            ).fetchall()
            return [dict(r) for r in rows]

    # ============================================================
    # FACTS / PREFERENCIAS
    # ============================================================

    def add_fact(self, category: str, key: str, value: Any, confidence: float = 1.0):
        """Agrega un hecho."""
        now = datetime.now().isoformat()
        with sqlite3.connect(self.db) as conn:
            conn.execute(
                """INSERT INTO facts (category, key, value, confidence, created, updated)
                   VALUES (?, ?, ?, ?, ?, ?)
                   ON CONFLICT(category, key) DO UPDATE SET
                   value = excluded.value,
                   confidence = excluded.confidence,
                   updated = excluded.updated""",
                (category, key, json.dumps(value), confidence, now, now),
            )
            conn.commit()

    def get_facts(self, category: str = None, key: str = None) -> List[Dict]:
        """Obtiene hechos."""
        with sqlite3.connect(self.db) as conn:
            conn.row_factory = sqlite3.Row
            if category and key:
                rows = conn.execute(
                    "SELECT * FROM facts WHERE category = ? AND key = ?",
                    (category, key),
                ).fetchall()
            elif category:
                rows = conn.execute(
                    "SELECT * FROM facts WHERE category = ?", (category,)
                ).fetchall()
            else:
                rows = conn.execute("SELECT * FROM facts").fetchall()

            result = []
            for r in rows:
                d = dict(r)
                try:
                    d["value"] = json.loads(d["value"])
                except:
                    pass
                result.append(d)
            return result

    def get_user_preferences(self) -> Dict[str, Any]:
        """Obtiene preferencias del usuario."""
        facts = self.get_facts(category="user")
        return {f["key"]: f["value"] for f in facts}

    # ============================================================
    # ERRORES
    # ============================================================

    def add_error(
        self, error_type: str, message: str, solution: str = "", context: str = ""
    ):
        """Registra un error."""
        # Verificar si ya existe
        with sqlite3.connect(self.db) as conn:
            existing = conn.execute(
                "SELECT id, times_seen FROM errors WHERE message = ?", (message,)
            ).fetchone()

            if existing:
                conn.execute(
                    "UPDATE errors SET times_seen = ?, solution = COALESCE(NULLIF(?, ''), solution) WHERE id = ?",
                    (existing[1] + 1, solution, existing[0]),
                )
            else:
                conn.execute(
                    "INSERT INTO errors (timestamp, error_type, message, solution, context) VALUES (?, ?, ?, ?, ?)",
                    (
                        datetime.now().isoformat(),
                        error_type,
                        message,
                        solution,
                        context,
                    ),
                )
            conn.commit()

    def search_errors(self, query: str) -> List[Dict]:
        """Busca errores."""
        with sqlite3.connect(self.db) as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute(
                "SELECT * FROM errors WHERE message LIKE ? OR solution LIKE ? ORDER BY times_seen DESC",
                (f"%{query}%", f"%{query}%"),
            ).fetchall()
            return [dict(r) for r in rows]

    # ============================================================
    # CONTEXTO PARA PROMPT
    # ============================================================

    def get_relevant_context(self, current_input: str, max_tokens: int = 1500) -> str:
        """
        Genera contexto relevante para inyectar en el prompt del modelo.
        v2.0: Usa retrieval hibrido (vector + keyword + graph + recency).
        """
        parts = []
        used_tokens = 0

        def add_part(text: str) -> bool:
            nonlocal used_tokens
            tokens = len(text) // 4
            if used_tokens + tokens > max_tokens:
                return False
            parts.append(text)
            used_tokens += tokens
            return True

        # 1. Preferencias del usuario
        prefs = self.get_user_preferences()
        if prefs:
            pref_text = "PREFERENCIAS DEL USUARIO:\n"
            for k, v in prefs.items():
                pref_text += f"  - {k}: {v}\n"
            add_part(pref_text)

        # 2. Retrieval hibrido de episodios
        hybrid_results = self.retriever.retrieve(
            current_input, limit=5, include_sources=True
        )
        if hybrid_results:
            ep_text = "CONVERSACIONES RELACIONADAS PREVIAS:\n"
            for ep in hybrid_results:
                sources = ep.get("retrieval_sources", {})
                source_str = ",".join([f"{k}={v:.2f}" for k, v in sources.items()])
                ep_text += f"  - [{ep['timestamp'][:10]}] Tu: {ep['user_input'][:80]}... [score:{ep.get('retrieval_score',0):.2f}, src:{source_str}]\n"
                if ep["response"]:
                    ep_text += f"    Lilith: {ep['response'][:80]}...\n"
            add_part(ep_text)

        # 3. Entidades relevantes del grafo
        entities = self.get_entities(min_mentions=2)
        if entities:
            ent_text = "ENTIDADES CONOCIDAS:\n"
            for e in entities[:10]:
                # Incluir vecinos del grafo
                neighbors = self.graph.get_neighbors(e["name"], min_strength=0.5)
                neighbor_str = ""
                if neighbors:
                    neighbor_names = [n[0] for n in neighbors[:3]]
                    neighbor_str = f" -> {', '.join(neighbor_names)}"
                ent_text += (
                    f"  - {e['name']} ({e['type']}, {e['mentions']}x{neighbor_str})\n"
                )
            add_part(ent_text)

        # 4. Resumenes de sesiones previas
        summaries = self.get_summaries(2)
        if summaries:
            sum_text = "RESUMENES DE SESIONES PREVIAS:\n"
            for s in summaries:
                sum_text += f"  [{s['period_start'][:10]}] {s['content'][:120]}...\n"
            add_part(sum_text)

        # 5. Errores comunes
        errors = self.search_errors(current_input)
        if errors:
            err_text = "ERRORES CONOCIDOS RELACIONADOS:\n"
            for e in errors[:2]:
                err_text += f"  - {e['message'][:60]}... -> {e['solution'][:60]}...\n"
            add_part(err_text)

        return "\n".join(parts) if parts else ""

    # ============================================================
    # ESTADISTICAS
    # ============================================================

    def get_stats(self) -> Dict[str, int]:
        """Obtiene estadisticas."""
        with sqlite3.connect(self.db) as conn:
            episodes = conn.execute(
                "SELECT COUNT(*) FROM episodes WHERE compressed = 0"
            ).fetchone()[0]
            compressed = conn.execute(
                "SELECT COUNT(*) FROM episodes WHERE compressed = 1"
            ).fetchone()[0]
            summaries = conn.execute("SELECT COUNT(*) FROM summaries").fetchone()[0]
            entities = conn.execute("SELECT COUNT(*) FROM entities").fetchone()[0]
            facts = conn.execute("SELECT COUNT(*) FROM facts").fetchone()[0]
            errors = conn.execute("SELECT COUNT(*) FROM errors").fetchone()[0]

            return {
                "episodes": episodes,
                "compressed_episodes": compressed,
                "summaries": summaries,
                "entities": entities,
                "facts": facts,
                "errors": errors,
            }

    def get_full_history(self, limit: int = 50) -> List[Dict]:
        """Obtiene historial completo."""
        return self.get_recent_episodes(limit)

    def clear(self):
        """Limpia toda la memoria."""
        with sqlite3.connect(self.db) as conn:
            for table in ["episodes", "summaries", "entities", "facts", "errors"]:
                conn.execute(f"DELETE FROM {table}")
            conn.commit()


# Instancia global
_memory_instance: Optional[EnhancedMemory] = None


def get_memory() -> EnhancedMemory:
    """Obtiene instancia global de memoria."""
    global _memory_instance
    if _memory_instance is None:
        _memory_instance = EnhancedMemory()
    return _memory_instance
