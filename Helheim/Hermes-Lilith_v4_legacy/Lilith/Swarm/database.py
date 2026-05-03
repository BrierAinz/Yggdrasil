"""
Swarm Database - Persistencia de estado del swarm
==================================================
SQLite para guardar/recuperar sesiones, agentes, mensajes y conflictos.
"""
import json
import sqlite3
import threading
import time
from pathlib import Path
from typing import Dict, List, Optional

DEFAULT_DB_PATH = Path(__file__).parent.parent.parent / "data" / "swarm.db"


class SwarmDatabase:
    """Base de datos SQLite para persistencia del swarm."""

    def __init__(self, db_path: Optional[Path] = None):
        self.db_path = db_path or DEFAULT_DB_PATH
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._local = threading.local()
        self._init_db()

    def _get_conn(self) -> sqlite3.Connection:
        """Obtiene conexion thread-local."""
        if not hasattr(self._local, "conn") or self._local.conn is None:
            self._local.conn = sqlite3.connect(
                str(self.db_path), check_same_thread=False
            )
            self._local.conn.row_factory = sqlite3.Row
        return self._local.conn

    def _init_db(self):
        """Inicializa schema."""
        conn = self._get_conn()
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS swarm_sessions (
                id TEXT PRIMARY KEY,
                task TEXT NOT NULL,
                status TEXT DEFAULT 'active',
                repo_path TEXT,
                use_llm INTEGER DEFAULT 0,
                created_at REAL NOT NULL,
                completed_at REAL
            );

            CREATE TABLE IF NOT EXISTS swarm_agents (
                id TEXT PRIMARY KEY,
                session_id TEXT NOT NULL,
                task TEXT NOT NULL,
                status TEXT DEFAULT 'idle',
                capabilities TEXT,
                context TEXT,
                result TEXT,
                files_read TEXT,
                files_written TEXT,
                started_at REAL,
                completed_at REAL,
                duration_seconds REAL DEFAULT 0,
                FOREIGN KEY (session_id) REFERENCES swarm_sessions(id)
            );

            CREATE TABLE IF NOT EXISTS swarm_messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT NOT NULL,
                from_id TEXT,
                to_id TEXT,
                msg_type TEXT NOT NULL,
                content TEXT,
                data TEXT,
                timestamp REAL NOT NULL,
                FOREIGN KEY (session_id) REFERENCES swarm_sessions(id)
            );

            CREATE TABLE IF NOT EXISTS swarm_conflicts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT NOT NULL,
                file_path TEXT NOT NULL,
                agent_ids TEXT NOT NULL,
                severity TEXT,
                resolution TEXT,
                resolved INTEGER DEFAULT 0,
                created_at REAL NOT NULL,
                resolved_at REAL,
                FOREIGN KEY (session_id) REFERENCES swarm_sessions(id)
            );

            CREATE INDEX IF NOT EXISTS idx_agents_session ON swarm_agents(session_id);
            CREATE INDEX IF NOT EXISTS idx_messages_session ON swarm_messages(session_id);
            CREATE INDEX IF NOT EXISTS idx_conflicts_session ON swarm_conflicts(session_id);
            """
        )
        conn.commit()

    # ═══════════════════════════════════════════════════════════════════════════
    # Sessions
    # ═══════════════════════════════════════════════════════════════════════════

    def save_session(
        self,
        session_id: str,
        task: str,
        status: str = "active",
        repo_path: str = "",
        use_llm: bool = False,
        completed_at: Optional[float] = None,
    ):
        """Guarda o actualiza una sesion."""
        conn = self._get_conn()
        conn.execute(
            """
            INSERT INTO swarm_sessions (id, task, status, repo_path, use_llm, created_at, completed_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(id) DO UPDATE SET
                task=excluded.task,
                status=excluded.status,
                repo_path=excluded.repo_path,
                use_llm=excluded.use_llm,
                completed_at=excluded.completed_at
            """,
            (
                session_id,
                task,
                status,
                repo_path,
                int(use_llm),
                time.time(),
                completed_at,
            ),
        )
        conn.commit()

    def get_session(self, session_id: str) -> Optional[Dict]:
        """Recupera una sesion."""
        conn = self._get_conn()
        row = conn.execute(
            "SELECT * FROM swarm_sessions WHERE id = ?", (session_id,)
        ).fetchone()
        if row:
            return dict(row)
        return None

    def list_sessions(self, limit: int = 50) -> List[Dict]:
        """Lista sesiones recientes."""
        conn = self._get_conn()
        rows = conn.execute(
            "SELECT * FROM swarm_sessions ORDER BY created_at DESC LIMIT ?",
            (limit,),
        ).fetchall()
        return [dict(r) for r in rows]

    def delete_session(self, session_id: str):
        """Elimina una sesion y todo su contenido."""
        conn = self._get_conn()
        conn.execute("DELETE FROM swarm_agents WHERE session_id = ?", (session_id,))
        conn.execute("DELETE FROM swarm_messages WHERE session_id = ?", (session_id,))
        conn.execute("DELETE FROM swarm_conflicts WHERE session_id = ?", (session_id,))
        conn.execute("DELETE FROM swarm_sessions WHERE id = ?", (session_id,))
        conn.commit()

    # ═══════════════════════════════════════════════════════════════════════════
    # Agents
    # ═══════════════════════════════════════════════════════════════════════════

    def save_agent(self, session_id: str, agent_data: Dict):
        """Guarda o actualiza un agente."""
        conn = self._get_conn()
        result = agent_data.get("result")
        if isinstance(result, dict):
            result = json.dumps(result)
        conn.execute(
            """
            INSERT INTO swarm_agents (
                id, session_id, task, status, capabilities, context,
                result, files_read, files_written, started_at, completed_at, duration_seconds
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(id) DO UPDATE SET
                status=excluded.status,
                result=excluded.result,
                files_read=excluded.files_read,
                files_written=excluded.files_written,
                completed_at=excluded.completed_at,
                duration_seconds=excluded.duration_seconds
            """,
            (
                agent_data["id"],
                session_id,
                agent_data.get("task", ""),
                agent_data.get("status", "idle"),
                json.dumps(agent_data.get("capabilities", [])),
                json.dumps(agent_data.get("context", {})),
                result,
                json.dumps(agent_data.get("files_read", [])),
                json.dumps(agent_data.get("files_written", [])),
                agent_data.get("started_at"),
                agent_data.get("completed_at"),
                agent_data.get("duration_seconds", 0.0),
            ),
        )
        conn.commit()

    def get_agents(self, session_id: str) -> List[Dict]:
        """Recupera agentes de una sesion."""
        conn = self._get_conn()
        rows = conn.execute(
            "SELECT * FROM swarm_agents WHERE session_id = ?", (session_id,)
        ).fetchall()
        result = []
        for r in rows:
            d = dict(r)
            for field in (
                "capabilities",
                "context",
                "result",
                "files_read",
                "files_written",
            ):
                if d.get(field):
                    try:
                        d[field] = json.loads(d[field])
                    except Exception:
                        pass
            d["use_llm"] = bool(d.get("use_llm", 0))
            result.append(d)
        return result

    # ═══════════════════════════════════════════════════════════════════════════
    # Messages
    # ═══════════════════════════════════════════════════════════════════════════

    def save_message(self, session_id: str, msg_data: Dict):
        """Guarda un mensaje."""
        conn = self._get_conn()
        data = msg_data.get("data", {})
        if isinstance(data, dict):
            data = json.dumps(data)
        conn.execute(
            """
            INSERT INTO swarm_messages (session_id, from_id, to_id, msg_type, content, data, timestamp)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                session_id,
                msg_data.get("from_id"),
                msg_data.get("to_id"),
                msg_data.get("msg_type", "broadcast"),
                msg_data.get("content", ""),
                data,
                msg_data.get("timestamp", time.time()),
            ),
        )
        conn.commit()

    def get_messages(self, session_id: str, limit: int = 1000) -> List[Dict]:
        """Recupera mensajes de una sesion."""
        conn = self._get_conn()
        rows = conn.execute(
            "SELECT * FROM swarm_messages WHERE session_id = ? ORDER BY timestamp LIMIT ?",
            (session_id, limit),
        ).fetchall()
        result = []
        for r in rows:
            d = dict(r)
            if d.get("data"):
                try:
                    d["data"] = json.loads(d["data"])
                except Exception:
                    pass
            result.append(d)
        return result

    # ═══════════════════════════════════════════════════════════════════════════
    # Conflicts
    # ═══════════════════════════════════════════════════════════════════════════

    def save_conflict(self, session_id: str, conflict_data: Dict):
        """Guarda un conflicto."""
        conn = self._get_conn()
        conn.execute(
            """
            INSERT INTO swarm_conflicts
            (session_id, file_path, agent_ids, severity, resolution, resolved, created_at, resolved_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                session_id,
                conflict_data["file_path"],
                json.dumps(conflict_data.get("agent_ids", [])),
                conflict_data.get("severity", "unknown"),
                conflict_data.get("resolution", ""),
                int(conflict_data.get("resolved", False)),
                conflict_data.get("created_at", time.time()),
                conflict_data.get("resolved_at"),
            ),
        )
        conn.commit()

    def get_conflicts(self, session_id: str) -> List[Dict]:
        """Recupera conflictos de una sesion."""
        conn = self._get_conn()
        rows = conn.execute(
            "SELECT * FROM swarm_conflicts WHERE session_id = ? ORDER BY created_at",
            (session_id,),
        ).fetchall()
        result = []
        for r in rows:
            d = dict(r)
            if d.get("agent_ids"):
                try:
                    d["agent_ids"] = json.loads(d["agent_ids"])
                except Exception:
                    pass
            d["resolved"] = bool(d["resolved"])
            result.append(d)
        return result

    def update_conflict_resolution(self, conflict_id: int, resolution: str):
        """Actualiza resolucion de un conflicto."""
        conn = self._get_conn()
        conn.execute(
            "UPDATE swarm_conflicts SET resolution = ?, resolved = 1, resolved_at = ? WHERE id = ?",
            (resolution, time.time(), conflict_id),
        )
        conn.commit()

    def close(self):
        """Cierra conexiones."""
        if hasattr(self._local, "conn") and self._local.conn:
            self._local.conn.close()
            self._local.conn = None


# Instancia global
_db_instance: Optional[SwarmDatabase] = None


def get_swarm_db(db_path: Optional[Path] = None) -> SwarmDatabase:
    """Obtiene instancia global de la base de datos."""
    global _db_instance
    if _db_instance is None:
        _db_instance = SwarmDatabase(db_path)
    return _db_instance
