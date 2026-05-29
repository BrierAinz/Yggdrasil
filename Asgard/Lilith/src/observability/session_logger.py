"""
Lilith - Session Logger
Structured logging for agent sessions with SQLite persistence
"""

import json
import sqlite3
import time
import uuid
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional


@dataclass
class SessionLog:
    """Represents a complete agent session"""

    session_id: str
    start_time: float
    end_time: Optional[float] = None
    user_intent: Optional[str] = None
    final_status: str = "ongoing"  # ongoing, success, failed, cancelled
    metadata: Dict[str, Any] = None

    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}


@dataclass
class InteractionEntry:
    """Single interaction within a session"""

    session_id: str
    timestamp: float
    message_type: str  # 'user', 'assistant', 'tool', 'system'
    content: str
    metadata: Dict[str, Any] = None

    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}


@dataclass
class ToolUsageEntry:
    """Tool execution record"""

    session_id: str
    tool_name: str
    action: str
    duration_ms: float
    success: bool
    error_message: Optional[str] = None
    parameters: Dict[str, Any] = None
    result: Optional[str] = None

    def __post_init__(self):
        if self.parameters is None:
            self.parameters = {}


class SessionLogger:
    """
    Structured session logging with SQLite backend
    Persists agent interactions, tool usage, and session outcomes
    """

    def __init__(self, db_path: str = None):
        """Initialize with database path"""
        if db_path is None:
            # Default to Lilith's data directory
            db_path = Path("D:\\Proyectos\\Lilith\\Core\\memory\\sessions.db")

        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)

        # Initialize database if it doesn't exist
        self._init_database()

        # Current session tracking
        self.current_session_id: Optional[str] = None
        self.session_start_time: Optional[float] = None

    def _init_database(self):
        """Create database tables if they don't exist"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS sessions (
                    session_id TEXT PRIMARY KEY,
                    start_time REAL NOT NULL,
                    end_time REAL,
                    user_intent TEXT,
                    final_status TEXT DEFAULT 'ongoing',
                    metadata TEXT
                )
            """
            )

            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS interactions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_id TEXT NOT NULL,
                    timestamp REAL NOT NULL,
                    message_type TEXT NOT NULL,
                    content TEXT,
                    metadata TEXT,
                    FOREIGN KEY (session_id) REFERENCES sessions(session_id)
                )
            """
            )

            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS tool_usage (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_id TEXT NOT NULL,
                    tool_name TEXT NOT NULL,
                    action TEXT,
                    duration_ms REAL,
                    success BOOLEAN,
                    error_message TEXT,
                    parameters TEXT,
                    result TEXT,
                    FOREIGN KEY (session_id) REFERENCES sessions(session_id)
                )
            """
            )

            conn.commit()

    def start_session(self, user_intent: str = None) -> str:
        """Start a new session and return session_id"""
        self.current_session_id = str(uuid.uuid4())
        self.session_start_time = time.time()

        session = SessionLog(
            session_id=self.current_session_id,
            start_time=self.session_start_time,
            user_intent=user_intent,
            final_status="ongoing",
        )

        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                """
                INSERT INTO sessions
                (session_id, start_time, user_intent, final_status, metadata)
                VALUES (?, ?, ?, ?, ?)
            """,
                (
                    session.session_id,
                    session.start_time,
                    session.user_intent,
                    session.final_status,
                    json.dumps(session.metadata),
                ),
            )
            conn.commit()

        return self.current_session_id

    def log_interaction(self, message_type: str, content: str, metadata: Dict = None):
        """Log a single interaction within current session"""
        if self.current_session_id is None:
            # Auto-start session if none active
            self.start_session()

        entry = InteractionEntry(
            session_id=self.current_session_id,
            timestamp=time.time(),
            message_type=message_type,
            content=content,
            metadata=metadata,
        )

        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                """
                INSERT INTO interactions
                (session_id, timestamp, message_type, content, metadata)
                VALUES (?, ?, ?, ?, ?)
            """,
                (
                    entry.session_id,
                    entry.timestamp,
                    entry.message_type,
                    entry.content,
                    json.dumps(entry.metadata) if entry.metadata else None,
                ),
            )
            conn.commit()

    def log_tool_usage(
        self,
        tool_name: str,
        action: str,
        duration_ms: float,
        success: bool,
        error_message: str = None,
        parameters: Dict = None,
        result: str = None,
    ):
        """Log tool execution details"""
        if self.current_session_id is None:
            self.start_session()

        entry = ToolUsageEntry(
            session_id=self.current_session_id,
            tool_name=tool_name,
            action=action,
            duration_ms=duration_ms,
            success=success,
            error_message=error_message,
            parameters=parameters,
            result=result,
        )

        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                """
                INSERT INTO tool_usage
                (session_id, tool_name, action, duration_ms, success, error_message, parameters, result)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
                (
                    entry.session_id,
                    entry.tool_name,
                    entry.action,
                    entry.duration_ms,
                    entry.success,
                    entry.error_message,
                    json.dumps(entry.parameters) if entry.parameters else None,
                    entry.result,
                ),
            )
            conn.commit()

    def end_session(self, status: str = "success", metadata: Dict = None):
        """End current session with final status"""
        if self.current_session_id is None:
            return

        end_time = time.time()

        if metadata is None:
            metadata = {}

        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                """
                UPDATE sessions
                SET end_time = ?,
                    final_status = ?,
                    metadata = json_patch(metadata, ?)
                WHERE session_id = ?
            """,
                (end_time, status, json.dumps(metadata), self.current_session_id),
            )
            conn.commit()

        # Clear current session
        self.current_session_id = None
        self.session_start_time = None

    def get_session(self, session_id: str) -> Optional[SessionLog]:
        """Retrieve a session by ID"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute(
                """
                SELECT session_id, start_time, end_time, user_intent, final_status, metadata
                FROM sessions WHERE session_id = ?
            """,
                (session_id,),
            )

            row = cursor.fetchone()
            if row:
                return SessionLog(
                    session_id=row[0],
                    start_time=row[1],
                    end_time=row[2],
                    user_intent=row[3],
                    final_status=row[4],
                    metadata=json.loads(row[5]) if row[5] else {},
                )
        return None

    def get_recent_sessions(self, limit: int = 10) -> List[SessionLog]:
        """Get most recent sessions"""
        sessions = []
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute(
                """
                SELECT session_id, start_time, end_time, user_intent, final_status, metadata
                FROM sessions
                ORDER BY start_time DESC
                LIMIT ?
            """,
                (limit,),
            )

            for row in cursor.fetchall():
                sessions.append(
                    SessionLog(
                        session_id=row[0],
                        start_time=row[1],
                        end_time=row[2],
                        user_intent=row[3],
                        final_status=row[4],
                        metadata=json.loads(row[5]) if row[5] else {},
                    )
                )
        return sessions

    def get_session_interactions(self, session_id: str) -> List[InteractionEntry]:
        """Get all interactions for a session"""
        interactions = []
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute(
                """
                SELECT session_id, timestamp, message_type, content, metadata
                FROM interactions
                WHERE session_id = ?
                ORDER BY timestamp
            """,
                (session_id,),
            )

            for row in cursor.fetchall():
                interactions.append(
                    InteractionEntry(
                        session_id=row[0],
                        timestamp=row[1],
                        message_type=row[2],
                        content=row[3],
                        metadata=json.loads(row[4]) if row[4] else {},
                    )
                )
        return interactions

    def get_tool_usage_stats(self, session_id: str = None) -> Dict[str, Any]:
        """Get aggregated tool usage statistics"""
        filters = "WHERE session_id = ?" if session_id else ""
        params = [session_id] if session_id else []

        with sqlite3.connect(self.db_path) as conn:
            # Total usage count
            cursor = conn.execute(
                f"""
                SELECT tool_name, COUNT(*) as count,
                       AVG(duration_ms) as avg_duration,
                       SUM(CASE WHEN success THEN 1 ELSE 0 END) as successes,
                       COUNT(*) as total
                FROM tool_usage {filters}
                GROUP BY tool_name
            """,
                params,
            )

            stats = {}
            for row in cursor.fetchall():
                tool_name = row[0]
                count = row[1]
                avg_duration = row[2] or 0
                successes = row[3]
                total = row[4]

                stats[tool_name] = {
                    "calls": count,
                    "avg_duration_ms": round(avg_duration, 2),
                    "success_rate": round((successes / total * 100), 1)
                    if total > 0
                    else 0,
                }

            return stats

    def get_overall_stats(self) -> Dict[str, Any]:
        """Get overall session statistics"""
        with sqlite3.connect(self.db_path) as conn:
            # Total sessions
            cursor = conn.execute("SELECT COUNT(*) FROM sessions")
            total_sessions = cursor.fetchone()[0]

            # Sessions by status
            cursor = conn.execute(
                """
                SELECT final_status, COUNT(*)
                FROM sessions
                WHERE final_status IS NOT NULL
                GROUP BY final_status
            """
            )
            status_breakdown = dict(cursor.fetchall())

            # Average session duration
            cursor = conn.execute(
                """
                SELECT AVG(end_time - start_time)
                FROM sessions
                WHERE end_time IS NOT NULL
            """
            )
            avg_duration = cursor.fetchone()[0] or 0

            return {
                "total_sessions": total_sessions,
                "status_breakdown": status_breakdown,
                "avg_session_duration_seconds": round(avg_duration, 2),
            }


# ============================================================================
# USAGE
# ============================================================================

if __name__ == "__main__":
    print("Session Logger Demo")
    print("=" * 60)

    logger = SessionLogger()

    # Start a session
    session_id = logger.start_session("Test session for demo")
    print(f"Started session: {session_id}")

    # Log some interactions
    logger.log_interaction("user", "Analyze this codebase", {"urgent": True})
    logger.log_interaction(
        "assistant", "I'll analyze the structure", {"tool_used": "CodeAnalyzer"}
    )

    # Log tool usage
    logger.log_tool_usage(
        tool_name="CodeAnalyzer",
        action="analyze_project",
        duration_ms=2345.0,
        success=True,
        parameters={"path": "D:\\Lilith"},
        result="Found 12 files, 3 classes",
    )

    # Log error
    logger.log_tool_usage(
        tool_name="WebBrowser",
        action="visit",
        duration_ms=523.0,
        success=False,
        error_message="Connection timeout",
        parameters={"url": "https://example.com"},
    )

    # End session
    logger.end_session("success", {"notes": "Demo completed successfully"})
    print("Session ended")

    # Show stats
    print("\n" + "=" * 60)
    print("SESSION STATISTICS:")
    stats = logger.get_overall_stats()
    for key, value in stats.items():
        print(f"  {key}: {value}")

    tool_stats = logger.get_tool_usage_stats()
    if tool_stats:
        print("\nTOOL USAGE:")
        for tool, data in tool_stats.items():
            print(f"  {tool}: {data}")

    print("\nâœ… Demo complete!")
