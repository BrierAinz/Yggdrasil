"""Lilith Agent — Persistent memory store."""

import json
import sqlite3
from pathlib import Path


class Memory:
    """SQLite-backed persistent memory with knowledge base."""

    def __init__(self, db_path: Path = Path("lilith_memory.db")):
        self.db_path = Path(db_path)
        self.conn = sqlite3.connect(str(db_path))
        self._init_db()

    def _init_db(self):
        self.conn.executescript("""
            CREATE TABLE IF NOT EXISTS memories (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT NOT NULL,
                role TEXT NOT NULL,
                content TEXT NOT NULL,
                tags TEXT DEFAULT '',
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            );
            CREATE TABLE IF NOT EXISTS knowledge (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                category TEXT NOT NULL,
                key TEXT NOT NULL,
                value TEXT NOT NULL,
                updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(category, key)
            );
            CREATE TABLE IF NOT EXISTS sessions (
                session_id TEXT PRIMARY KEY,
                title TEXT,
                messages_json TEXT,
                updated_at TEXT DEFAULT CURRENT_TIMESTAMP
            );
            CREATE INDEX IF NOT EXISTS idx_mem_session ON memories(session_id);
            CREATE INDEX IF NOT EXISTS idx_know_cat ON knowledge(category);
        """)
        self.conn.commit()

    # ── Conversation Memory ──

    def store(self, session_id: str, role: str, content: str, tags: str = ""):
        self.conn.execute(
            "INSERT INTO memories (session_id, role, content, tags) VALUES (?, ?, ?, ?)",
            (session_id, role, content, tags),
        )
        self.conn.commit()

    def recall(self, session_id: str, limit: int = 30) -> list[dict]:
        rows = self.conn.execute(
            "SELECT role, content, created_at FROM memories WHERE session_id=? ORDER BY id DESC LIMIT ?",
            (session_id, limit),
        ).fetchall()
        return [{"role": r[0], "content": r[1], "created_at": r[2]} for r in reversed(rows)]

    def search(self, query: str, limit: int = 10) -> list[dict]:
        rows = self.conn.execute(
            "SELECT role, content, created_at FROM memories WHERE content LIKE ? ORDER BY id DESC LIMIT ?",
            (f"%{query}%", limit),
        ).fetchall()
        return [{"role": r[0], "content": r[1], "when": r[2]} for r in rows]

    def sessions(self, limit: int = 10) -> list[str]:
        return [
            r[0]
            for r in self.conn.execute(
                "SELECT DISTINCT session_id FROM memories ORDER BY id DESC LIMIT ?", (limit,)
            ).fetchall()
        ]

    # ── Knowledge Base ──

    def learn(self, category: str, key: str, value: str):
        self.conn.execute(
            """
            INSERT INTO knowledge (category, key, value, updated_at)
            VALUES (?, ?, ?, CURRENT_TIMESTAMP)
            ON CONFLICT(category, key)
            DO UPDATE SET value=excluded.value, updated_at=CURRENT_TIMESTAMP
            """,
            (category, key, value),
        )
        self.conn.commit()

    def know(self, category: str | None = None) -> list[dict]:
        if category:
            rows = self.conn.execute(
                "SELECT category, key, value FROM knowledge WHERE category=?", (category,)
            ).fetchall()
        else:
            rows = self.conn.execute("SELECT category, key, value FROM knowledge").fetchall()
        return [{"category": r[0], "key": r[1], "value": r[2]} for r in rows]

    def forget(self, category: str, key: str | None = None):
        if key:
            self.conn.execute("DELETE FROM knowledge WHERE category=? AND key=?", (category, key))
        else:
            self.conn.execute("DELETE FROM knowledge WHERE category=?", (category,))
        self.conn.commit()

    # ── Session Save/Restore ──

    def save_session(self, session_id: str, title: str, messages: list):
        self.conn.execute(
            """
            INSERT INTO sessions (session_id, title, messages_json, updated_at)
            VALUES (?, ?, ?, CURRENT_TIMESTAMP)
            ON CONFLICT(session_id)
            DO UPDATE SET title=excluded.title, messages_json=excluded.messages_json,
            updated_at=CURRENT_TIMESTAMP
            """,
            (session_id, title, json.dumps(messages, ensure_ascii=False)),
        )
        self.conn.commit()

    def load_session(self, session_id: str) -> list | None:
        row = self.conn.execute(
            "SELECT messages_json FROM sessions WHERE session_id=?", (session_id,)
        ).fetchone()
        if row:
            return json.loads(row[0])
        return None

    def list_saved_sessions(self) -> list[dict]:
        rows = self.conn.execute(
            "SELECT session_id, title, updated_at FROM sessions ORDER BY updated_at DESC LIMIT 20"
        ).fetchall()
        return [{"session_id": r[0], "title": r[1], "updated_at": r[2]} for r in rows]
