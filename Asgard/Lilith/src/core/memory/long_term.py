"""
Long-Term Memory - Sistema de memoria a largo plazo

v5.0: Archivado, resumen y recuperación de contexto histórico.
Mantiene memoria relevante compactada para sesiones largas.
"""
import json
import logging
import sqlite3
from dataclasses import asdict, dataclass
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger("lilith.memory.long_term")


@dataclass
class ConversationSummary:
    """Resumen de una conversación o período."""

    id: str
    session_id: str
    start_time: str
    end_time: str
    summary: str
    key_topics: List[str]
    key_decisions: List[str]
    message_count: int
    archived: bool = False


@dataclass
class ArchivedConversation:
    """Conversación archivada."""

    id: str
    session_id: str
    archived_at: str
    messages: List[Dict[str, Any]]
    summary: Optional[str] = None


class LongTermMemory:
    """
    Sistema de memoria a largo plazo.

    Features:
    - Archivado automático de conversaciones antiguas
    - Generación de resúmenes periódicos
    - Recuperación de contexto histórico relevante
    - Compresión de memoria
    """

    def __init__(self, db_path: Optional[Path] = None):
        if db_path is None:
            base = Path(__file__).resolve().parents[3]
            db_path = base / "Config" / "long_term_memory.db"

        self.db_path = db_path
        self._ensure_db()

        # Configuración
        self.archive_after_days = 7
        self.summary_interval = 50  # mensajes
        self.max_active_messages = 100

    def _ensure_db(self):
        """Crea tablas necesarias."""
        with sqlite3.connect(self.db_path) as conn:
            # Resúmenes
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS conversation_summaries (
                    id TEXT PRIMARY KEY,
                    session_id TEXT NOT NULL,
                    start_time TEXT NOT NULL,
                    end_time TEXT NOT NULL,
                    summary TEXT NOT NULL,
                    key_topics TEXT,  -- JSON array
                    key_decisions TEXT,  -- JSON array
                    message_count INTEGER,
                    archived BOOLEAN DEFAULT 0,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP
                )
            """
            )

            # Conversaciones archivadas
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS archived_conversations (
                    id TEXT PRIMARY KEY,
                    session_id TEXT NOT NULL,
                    archived_at TEXT NOT NULL,
                    messages TEXT NOT NULL,  -- JSON
                    summary TEXT,
                    metadata TEXT  -- JSON
                )
            """
            )

            # Índices
            conn.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_summaries_session
                ON conversation_summaries(session_id)
            """
            )
            conn.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_archived_session
                ON archived_conversations(session_id)
            """
            )

            conn.commit()

    async def should_archive(
        self, session_id: str, message_count: int, last_activity: datetime
    ) -> bool:
        """
        Determina si una sesión debe ser archivada.

        Args:
            session_id: ID de sesión
            message_count: Número de mensajes
            last_activity: Última actividad

        Returns:
            True si debe archivarse
        """
        # Por cantidad de mensajes
        if message_count > self.max_active_messages:
            return True

        # Por inactividad
        days_inactive = (datetime.utcnow() - last_activity).days
        if days_inactive > self.archive_after_days:
            return True

        return False

    async def archive_conversation(
        self,
        session_id: str,
        messages: List[Dict[str, Any]],
        generate_summary: bool = True,
    ) -> bool:
        """
        Archiva una conversación.

        Args:
            session_id: ID de sesión
            messages: Mensajes a archivar
            generate_summary: Si debe generar resumen

        Returns:
            True si se archivó
        """
        try:
            summary = None
            if generate_summary and messages:
                summary = await self._generate_summary(messages)

            import secrets

            archive_id = secrets.token_hex(8)

            with sqlite3.connect(self.db_path) as conn:
                conn.execute(
                    """
                    INSERT INTO archived_conversations
                    (id, session_id, archived_at, messages, summary)
                    VALUES (?, ?, ?, ?, ?)
                """,
                    (
                        archive_id,
                        session_id,
                        datetime.utcnow().isoformat(),
                        json.dumps(messages),
                        summary,
                    ),
                )
                conn.commit()

            logger.info(
                f"Conversación {session_id} archivada ({len(messages)} mensajes)"
            )
            return True

        except Exception as e:
            logger.error(f"Error archivando conversación: {e}")
            return False

    async def _generate_summary(self, messages: List[Dict[str, Any]]) -> str:
        """Genera resumen de mensajes."""
        # Implementación simple - en producción usar LLM
        user_msgs = [m for m in messages if m.get("role") == "user"]
        assistant_msgs = [m for m in messages if m.get("role") == "assistant"]

        topics = self._extract_topics(messages)

        summary_parts = [
            f"Conversación de {len(messages)} mensajes",
            f"({len(user_msgs)} del usuario, {len(assistant_msgs)} del asistente)",
            f"Temas principales: {', '.join(topics[:5])}",
        ]

        return "; ".join(summary_parts)

    def _extract_topics(self, messages: List[Dict[str, Any]]) -> List[str]:
        """Extrae temas de mensajes."""
        # Implementación simple por keywords
        all_text = " ".join(m.get("content", "") for m in messages)
        words = all_text.lower().split()

        # Contar frecuencia
        from collections import Counter

        word_counts = Counter(words)

        # Filtrar palabras comunes y cortas
        stopwords = {"el", "la", "de", "que", "y", "a", "en", "un", "es", "con", "para"}
        topics = [
            word
            for word, count in word_counts.most_common(20)
            if len(word) > 4 and word not in stopwords
        ]

        return topics

    async def create_periodic_summary(
        self, session_id: str, messages: List[Dict[str, Any]]
    ) -> Optional[ConversationSummary]:
        """
        Crea un resumen periódico de la conversación.

        Args:
            session_id: ID de sesión
            messages: Mensajes del período

        Returns:
            Resumen creado o None
        """
        if len(messages) < self.summary_interval:
            return None

        try:
            import secrets

            summary_text = await self._generate_summary(messages)
            topics = self._extract_topics(messages)

            # Extraer decisiones (mensajes con "decidimos", "acordamos", etc.)
            decisions = []
            for msg in messages:
                content = msg.get("content", "").lower()
                if any(
                    kw in content
                    for kw in ["decidimos", "acordamos", "vamos a", "queda en"]
                ):
                    decisions.append(msg.get("content", "")[:200])

            summary = ConversationSummary(
                id=secrets.token_hex(8),
                session_id=session_id,
                start_time=messages[0].get("timestamp", datetime.utcnow().isoformat()),
                end_time=messages[-1].get("timestamp", datetime.utcnow().isoformat()),
                summary=summary_text,
                key_topics=topics[:10],
                key_decisions=decisions[:5],
                message_count=len(messages),
            )

            # Guardar
            with sqlite3.connect(self.db_path) as conn:
                conn.execute(
                    """
                    INSERT INTO conversation_summaries
                    (id, session_id, start_time, end_time, summary,
                     key_topics, key_decisions, message_count)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                    (
                        summary.id,
                        summary.session_id,
                        summary.start_time,
                        summary.end_time,
                        summary.summary,
                        json.dumps(summary.key_topics),
                        json.dumps(summary.key_decisions),
                        summary.message_count,
                    ),
                )
                conn.commit()

            return summary

        except Exception as e:
            logger.error(f"Error creando resumen: {e}")
            return None

    async def get_relevant_history(
        self, session_id: str, query: str, limit: int = 3
    ) -> List[ConversationSummary]:
        """
        Recupera resúmenes relevantes del historial.

        Args:
            session_id: ID de sesión
            query: Consulta para buscar relevancia
            limit: Máximo de resultados

        Returns:
            Lista de resúmenes relevantes
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.execute(
                    """
                    SELECT id, session_id, start_time, end_time, summary,
                           key_topics, key_decisions, message_count
                    FROM conversation_summaries
                    WHERE session_id = ?
                    ORDER BY end_time DESC
                    LIMIT ?
                """,
                    (session_id, limit * 2),
                )  # Pedir más para filtrar

                rows = cursor.fetchall()

            summaries = []
            for row in rows:
                # Calcular relevancia simple
                topics = json.loads(row[5] or "[]")
                relevance = self._calculate_relevance(query, topics, row[4])

                if relevance > 0.3:  # Umbral mínimo
                    summaries.append((relevance, row))

            # Ordenar por relevancia y tomar top
            summaries.sort(reverse=True)

            result = []
            for _, row in summaries[:limit]:
                result.append(
                    ConversationSummary(
                        id=row[0],
                        session_id=row[1],
                        start_time=row[2],
                        end_time=row[3],
                        summary=row[4],
                        key_topics=json.loads(row[5] or "[]"),
                        key_decisions=json.loads(row[6] or "[]"),
                        message_count=row[7],
                    )
                )

            return result

        except Exception as e:
            logger.error(f"Error recuperando historial: {e}")
            return []

    def _calculate_relevance(
        self, query: str, topics: List[str], summary: str
    ) -> float:
        """Calcula score de relevancia."""
        query_words = set(query.lower().split())
        topics_set = set(t.lower() for t in topics)
        summary_words = set(summary.lower().split())

        # Overlap con topics
        topic_overlap = (
            len(query_words & topics_set) / len(query_words) if query_words else 0
        )

        # Overlap con summary
        summary_overlap = (
            len(query_words & summary_words) / len(query_words) if query_words else 0
        )

        return (topic_overlap * 0.6) + (summary_overlap * 0.4)

    async def compact_session(
        self, session_id: str, current_messages: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        Compacta una sesión archivando mensajes antiguos.

        Args:
            session_id: ID de sesión
            current_messages: Mensajes actuales

        Returns:
            Mensajes recientes (no archivados)
        """
        if len(current_messages) <= self.max_active_messages:
            return current_messages

        # Dividir en archivar / mantener
        to_archive = current_messages[: -self.max_active_messages]
        to_keep = current_messages[-self.max_active_messages :]

        # Crear resumen antes de archivar
        await self.create_periodic_summary(session_id, to_archive)

        # Archivar
        await self.archive_conversation(session_id, to_archive, generate_summary=False)

        return to_keep

    async def get_archived_conversation(
        self, archive_id: str
    ) -> Optional[ArchivedConversation]:
        """Recupera una conversación archivada."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.execute(
                    """
                    SELECT id, session_id, archived_at, messages, summary
                    FROM archived_conversations
                    WHERE id = ?
                """,
                    (archive_id,),
                )

                row = cursor.fetchone()
                if not row:
                    return None

                return ArchivedConversation(
                    id=row[0],
                    session_id=row[1],
                    archived_at=row[2],
                    messages=json.loads(row[3]),
                    summary=row[4],
                )

        except Exception as e:
            logger.error(f"Error recuperando archivo: {e}")
            return None

    async def cleanup_old_archives(self, days: int = 90):
        """Limpia archivos antiguos."""
        cutoff = (datetime.utcnow() - timedelta(days=days)).isoformat()

        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.execute(
                    """
                    DELETE FROM archived_conversations
                    WHERE archived_at < ?
                """,
                    (cutoff,),
                )

                deleted = cursor.rowcount
                conn.commit()

                logger.info(f"Limpiados {deleted} archivos antiguos")
                return deleted

        except Exception as e:
            logger.error(f"Error limpiando archivos: {e}")
            return 0


# Singleton global
_ltm: Optional[LongTermMemory] = None


def get_long_term_memory() -> LongTermMemory:
    """Obtiene instancia singleton de LTM."""
    global _ltm
    if _ltm is None:
        _ltm = LongTermMemory()
    return _ltm
