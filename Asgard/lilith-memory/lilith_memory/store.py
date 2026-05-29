<<<<<<< HEAD
"""SQLite-backed memory store for Yggdrasil."""

import json
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Optional


class MemoryStore:
    """Persistent memory store using SQLite."""
    
    def __init__(self, db_path: str | Path = "chat_memory.db"):
        self.db_path = Path(db_path)
        self._init_db()
    
    def _init_db(self):
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS memories (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_id TEXT NOT NULL,
                    role TEXT NOT NULL,
                    content TEXT NOT NULL,
                    metadata TEXT DEFAULT '{}',
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP
                )
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_session ON memories(session_id)
            """)
            conn.commit()
    
    def store(self, session_id: str, role: str, content: str, metadata: dict = None) -> int:
        """Store a memory entry."""
        with sqlite3.connect(self.db_path) as conn:
            cur = conn.execute(
                "INSERT INTO memories (session_id, role, content, metadata) VALUES (?, ?, ?, ?)",
                (session_id, role, content, json.dumps(metadata or {}))
            )
            conn.commit()
            return cur.lastrowid
    
    def recall(self, session_id: str, limit: int = 10) -> list[dict]:
        """Recall memories for a session."""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute(
                "SELECT * FROM memories WHERE session_id = ? ORDER BY created_at DESC LIMIT ?",
                (session_id, limit)
            ).fetchall()
            return [dict(r) for r in rows]
    
    def search(self, query: str, limit: int = 5) -> list[dict]:
        """Simple text search across memories."""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute(
                "SELECT * FROM memories WHERE content LIKE ? ORDER BY created_at DESC LIMIT ?",
                (f"%{query}%", limit)
            ).fetchall()
            return [dict(r) for r in rows]
    
    def count(self) -> int:
        with sqlite3.connect(self.db_path) as conn:
            return conn.execute("SELECT COUNT(*) FROM memories").fetchone()[0]
    
    def sessions(self) -> list[str]:
        with sqlite3.connect(self.db_path) as conn:
            rows = conn.execute("SELECT DISTINCT session_id FROM memories").fetchall()
            return [r[0] for r in rows]
=======
"""Persistent key-value memory store backed by SQLite."""

from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import TYPE_CHECKING, Literal, Self


if TYPE_CHECKING:
    from types import TracebackType


class MemoryStore:
    """Persistent key-value memory store backed by SQLite.

    Provides CRUD operations over a ``memories`` table with optional
    embeddings and JSON metadata. WAL mode is enabled automatically
    for better concurrent read/write performance.
    """

    def __init__(self, db_path: Path) -> None:
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

    def _init_db(self) -> None:
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
            """,
            )
            conn.execute("CREATE INDEX IF NOT EXISTS idx_time ON memories(timestamp)")

    # ------------------------------------------------------------------
    # Context manager support
    # ------------------------------------------------------------------

    def __enter__(self) -> Self:
        """Enter the context manager, opening a long-lived connection."""
        self._conn = sqlite3.connect(self.db_path)
        self._conn.execute("PRAGMA journal_mode=WAL")
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> Literal[False]:
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
    # Internal helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _escape_like(value: str) -> str:
        """Escape ``%`` and ``_`` wildcards so user input is treated as literal."""
        return value.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")

    # ------------------------------------------------------------------
    # CRUD operations
    # ------------------------------------------------------------------

    def add(
        self,
        content: str,
        embedding: bytes | None = None,
        metadata: dict | None = None,
    ) -> int:
        """Insert a new memory entry and return its integer id.

        Args:
            content: The text content to store.
            embedding: Optional binary embedding vector.
            metadata: Optional dict stored as JSON.

        Returns:
            The ``id`` of the newly inserted row.

        """
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute(
                "INSERT INTO memories (content, embedding, metadata) VALUES (?, ?, ?)",
                (content, embedding, json.dumps(metadata) if metadata else None),
            )
            return int(cursor.lastrowid or 0)

    def store(
        self,
        content: str,
        embedding: bytes | None = None,
        metadata: dict | None = None,
    ) -> int:
        """Alias for :meth:`add` — insert a new memory entry and return its id.

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
        escaped = self._escape_like(query)
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            conn.execute("PRAGMA case_sensitive_like = OFF")
            rows = conn.execute(
                "SELECT * FROM memories WHERE content LIKE ? ESCAPE '\\' "
                "ORDER BY timestamp DESC LIMIT ?",
                (f"%{escaped}%", limit),
            ).fetchall()
            return [dict(row) for row in rows]

    def recent(self, limit: int = 10) -> list[dict]:
        """Return the most recent memory entries.

        Args:
            limit: Maximum number of entries to return.

        Returns:
            A list of dicts ordered by most recent first.

        """
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute(
                "SELECT * FROM memories ORDER BY timestamp DESC LIMIT ?",
                (limit,),
            ).fetchall()
            return [dict(row) for row in rows]

    def count_entries(self) -> int:
        """Return the total number of entries in the store.

        Returns:
            Integer count of all rows in the ``memories`` table.

        """
        with sqlite3.connect(self.db_path) as conn:
            return conn.execute("SELECT COUNT(*) FROM memories").fetchone()[0]

    def delete(self, entry_id: int) -> bool:
        """Delete a memory entry by its primary key.

        Args:
            entry_id: The ``id`` column value of the row to delete.

        Returns:
            ``True`` if a row was deleted, ``False`` if no row matched.

        """
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("DELETE FROM memories WHERE id = ?", (entry_id,))
            return cursor.rowcount > 0

    def clear(self) -> int:
        """Remove all entries from the memory store.

        Returns:
            The number of rows that were deleted.

        """
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("DELETE FROM memories")
            conn.commit()
            return cursor.rowcount
>>>>>>> origin/main
