"""Persistent key-value memory store backed by SQLite."""

import json
import sqlite3
from pathlib import Path


class MemoryStore:
    """Persistent key-value memory store backed by SQLite.

    Provides CRUD operations over a ``memories`` table with optional
    embeddings and JSON metadata. WAL mode is enabled automatically
    for better concurrent read/write performance.
    """

    def __init__(self, db_path: Path):
        """Initialise the store and create the database schema if needed.

        Args:
            db_path: Path to the SQLite database file. The file is created
                     automatically on first access.

        """
        self.db_path = db_path
        self._conn: sqlite3.Connection | None = None
        self._init_db()

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _get_conn(self) -> sqlite3.Connection:
        """Return the long-lived connection for context-manager usage.

        When used outside a ``with`` block this returns a fresh short-lived
        connection each time so that the class remains safe to use without
        a context manager.
        """
        if self._conn is not None:
            return self._conn
        return sqlite3.connect(self.db_path)

    def _init_db(self):
        """Create the ``memories`` table and indexes, and enable WAL mode."""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("PRAGMA journal_mode=WAL")
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS memories (
                    id INTEGER PRIMARY KEY,
                    content TEXT NOT NULL,
                    embedding BLOB,
                    metadata TEXT,
                    timestamp REAL DEFAULT (unixepoch())
                )
            """
            )
            conn.execute("CREATE INDEX IF NOT EXISTS idx_time ON memories(timestamp)")

    # ------------------------------------------------------------------
    # Context manager support
    # ------------------------------------------------------------------

    def __enter__(self):
        """Enter the context manager, opening a long-lived connection."""
        self._conn = sqlite3.connect(self.db_path)
        self._conn.execute("PRAGMA journal_mode=WAL")
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Exit the context manager, closing the long-lived connection."""
        if self._conn is not None:
            self._conn.close()
            self._conn = None
        return False  # do not suppress exceptions

    # ------------------------------------------------------------------
    # Dunder helpers
    # ------------------------------------------------------------------

    def __len__(self) -> int:
        """Return the number of entries in the store."""
        return self.count_entries()

    # ------------------------------------------------------------------
    # CRUD operations
    # ------------------------------------------------------------------

    def add(
        self,
        content: str,
        embedding: bytes | None = None,
        metadata: dict | None = None,
    ):
        """Insert a new memory entry.

        Args:
            content: The text content to store.
            embedding: Optional binary embedding vector.
            metadata: Optional dict stored as JSON.

        """
        conn = self._get_conn()
        try:
            conn.execute(
                "INSERT INTO memories (content, embedding, metadata) VALUES (?, ?, ?)",
                (content, embedding, json.dumps(metadata) if metadata else None),
            )
            conn.commit()
        finally:
            if self._conn is None:
                conn.close()

    def store(
        self,
        content: str,
        embedding: bytes | None = None,
        metadata: dict | None = None,
    ):
        """Alias for :meth:`add` — insert a new memory entry.

        This method exists because the external API (``lilith_api.main``)
        calls ``memory.store()`` instead of ``memory.add()``.
        """
        return self.add(content=content, embedding=embedding, metadata=metadata)

    def search(self, query: str, limit: int = 5) -> list[dict]:
        """Search memories whose content matches ``query`` (substring).

        Args:
            query: Substring to search for (case-insensitive via LIKE).
            limit: Maximum number of results to return.

        Returns:
            A list of dicts, each representing a matching row, ordered
            by most recent first.

        """
        conn = self._get_conn()
        try:
            conn.row_factory = sqlite3.Row
            rows = conn.execute(
                "SELECT * FROM memories WHERE content LIKE ? ORDER BY timestamp DESC LIMIT ?",
                (f"%{query}%", limit),
            ).fetchall()
            return [dict(row) for row in rows]
        finally:
            if self._conn is None:
                conn.close()

    def recent(self, limit: int = 10) -> list[dict]:
        """Return the most recent memory entries.

        Args:
            limit: Maximum number of entries to return.

        Returns:
            A list of dicts ordered by most recent first.

        """
        conn = self._get_conn()
        try:
            conn.row_factory = sqlite3.Row
            rows = conn.execute(
                "SELECT * FROM memories ORDER BY timestamp DESC LIMIT ?", (limit,)
            ).fetchall()
            return [dict(row) for row in rows]
        finally:
            if self._conn is None:
                conn.close()

    def count_entries(self) -> int:
        """Return the total number of entries in the store.

        Returns:
            Integer count of all rows in the ``memories`` table.

        """
        conn = self._get_conn()
        try:
            count = conn.execute("SELECT COUNT(*) FROM memories").fetchone()[0]
            return count
        finally:
            if self._conn is None:
                conn.close()

    def delete(self, entry_id: int) -> bool:
        """Delete a memory entry by its primary key.

        Args:
            entry_id: The ``id`` column value of the row to delete.

        Returns:
            ``True`` if a row was deleted, ``False`` if no row matched.

        """
        conn = self._get_conn()
        try:
            cursor = conn.execute("DELETE FROM memories WHERE id = ?", (entry_id,))
            conn.commit()
            return cursor.rowcount > 0
        finally:
            if self._conn is None:
                conn.close()

    def clear(self) -> int:
        """Remove all entries from the memory store.

        Returns:
            The number of rows that were deleted.

        """
        conn = self._get_conn()
        try:
            count = self.count_entries()
            conn.execute("DELETE FROM memories")
            conn.commit()
            return count
        finally:
            if self._conn is None:
                conn.close()
