import json
import sqlite3
from pathlib import Path
from typing import Dict, List, Optional


class MemoryStore:
    def __init__(self, db_path: Path):
        self.db_path = db_path
        self._init_db()

    def _init_db(self):
        with sqlite3.connect(self.db_path) as conn:
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

    def add(
        self,
        content: str,
        embedding: Optional[bytes] = None,
        metadata: Optional[Dict] = None,
    ):
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                "INSERT INTO memories (content, embedding, metadata) VALUES (?, ?, ?)",
                (content, embedding, json.dumps(metadata) if metadata else None),
            )

    def search(self, query: str, limit: int = 5) -> List[Dict]:
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute(
                "SELECT * FROM memories WHERE content LIKE ? ORDER BY timestamp DESC LIMIT ?",
                (f"%{query}%", limit),
            ).fetchall()
            return [dict(row) for row in rows]

    def recent(self, limit: int = 10) -> List[Dict]:
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute(
                "SELECT * FROM memories ORDER BY timestamp DESC LIMIT ?", (limit,)
            ).fetchall()
            return [dict(row) for row in rows]

    def count_entries(self) -> int:
        cursor = self.conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM memories")
        return cursor.fetchone()[0]
