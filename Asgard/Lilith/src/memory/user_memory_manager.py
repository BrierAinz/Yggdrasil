"""
User Memory Manager - Persistent user preferences and context
Part of Lilith v2.2+ memory system
"""

import json
import logging
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class UserMemoryManager:
    def __init__(self, db_path: str = None):
        self.db_path = Path(
            db_path or "D:\\Proyectos\\Lilith\\Core\\memory\\user_profiles.db"
        )
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_database()
        self.current_user_id = "demo_user"  # Default for now

    def _init_database(self):
        """Initialize DB schema if not exists"""
        setup_script = """
        CREATE TABLE IF NOT EXISTS user_profiles (
            user_id TEXT PRIMARY KEY,
            name TEXT,
            preferred_tone TEXT DEFAULT 'casual',
            favorite_tools TEXT,
            avg_session_duration INTEGER DEFAULT 0,
            success_rate REAL DEFAULT 0.0,
            total_interactions INTEGER DEFAULT 0,
            last_interaction DATETIME,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS user_preferences (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id TEXT,
            key TEXT,
            value TEXT,
            updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS session_context (
            session_id TEXT PRIMARY KEY,
            user_id TEXT,
            active_files TEXT,
            working_directory TEXT,
            recent_urls TEXT,
            pending_tasks TEXT,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        );
        """

        with sqlite3.connect(self.db_path) as conn:
            conn.executescript(setup_script)

    def update_user_profile(self, user_id: str, **kwargs) -> bool:
        """Update user profile with new data"""
        valid_fields = {
            "name",
            "preferred_tone",
            "favorite_tools",
            "avg_session_duration",
            "success_rate",
            "total_interactions",
        }

        fields_to_update = {k: v for k, v in kwargs.items() if k in valid_fields}
        if not fields_to_update:
            return False

        set_clause = ", ".join([f"{k} = ?" for k in fields_to_update.keys()])
        values = list(fields_to_update.values()) + [user_id]

        query = f"""
            UPDATE user_profiles
            SET {set_clause}, last_interaction = CURRENT_TIMESTAMP
            WHERE user_id = ?
        """

        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.execute(query, values)
                if cursor.rowcount == 0:
                    # User doesn't exist, insert
                    fields = ["user_id"] + list(fields_to_update.keys())
                    placeholders = ", ".join(["?" for _ in fields])
                    insert_query = f"""
                        INSERT INTO user_profiles ({', '.join(fields)})
                        VALUES ({placeholders})
                    """
                    insert_values = [user_id] + list(fields_to_update.values())
                    conn.execute(insert_query, insert_values)
                conn.commit()
            return True
        except Exception as e:
            logger.error(f"Error updating user profile: {e}")
            return False

    def get_user_profile(self, user_id: str) -> Optional[Dict[str, Any]]:
        """Get complete user profile"""
        query = "SELECT * FROM user_profiles WHERE user_id = ?"

        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.execute(query, (user_id,))
                row = cursor.fetchone()

                if row:
                    profile = dict(row)
                    # Parse JSON fields
                    if profile.get("favorite_tools"):
                        try:
                            profile["favorite_tools"] = json.loads(
                                profile["favorite_tools"]
                            )
                        except:
                            profile["favorite_tools"] = []
                    return profile
        except Exception as e:
            logger.error(f"Error getting user profile: {e}")
        return None

    def set_preference(self, user_id: str, key: str, value: str) -> bool:
        """Set or update a user preference"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                # Delete existing
                conn.execute(
                    "DELETE FROM user_preferences WHERE user_id = ? AND key = ?",
                    (user_id, key),
                )
                # Insert new
                conn.execute(
                    "INSERT INTO user_preferences (user_id, key, value) VALUES (?, ?, ?)",
                    (user_id, key, value),
                )
                conn.commit()
            return True
        except Exception as e:
            logger.error(f"Error setting preference: {e}")
            return False

    def get_preference(self, user_id: str, key: str) -> Optional[str]:
        """Get user preference"""
        query = "SELECT value FROM user_preferences WHERE user_id = ? AND key = ?"

        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.execute(query, (user_id, key))
                row = cursor.fetchone()
                return row[0] if row else None
        except Exception as e:
            logger.error(f"Error getting preference: {e}")
        return None

    def update_session_context(
        self, session_id: str, user_id: str, context: Dict[str, Any]
    ) -> bool:
        """Update or insert session context"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                # Serialize JSON fields
                active_files = json.dumps(context.get("active_files", []))
                recent_urls = json.dumps(context.get("recent_urls", []))
                pending_tasks = json.dumps(context.get("pending_tasks", []))

                # Try update first
                cursor = conn.execute(
                    """
                    UPDATE session_context
                    SET active_files = ?, working_directory = ?, recent_urls = ?, pending_tasks = ?
                    WHERE session_id = ?
                    """,
                    (
                        active_files,
                        context.get("working_directory"),
                        recent_urls,
                        pending_tasks,
                        session_id,
                    ),
                )

                if cursor.rowcount == 0:
                    # Insert new
                    conn.execute(
                        """
                        INSERT INTO session_context (session_id, user_id, active_files, working_directory, recent_urls, pending_tasks)
                        VALUES (?, ?, ?, ?, ?, ?)
                        """,
                        (
                            session_id,
                            user_id,
                            active_files,
                            context.get("working_directory"),
                            recent_urls,
                            pending_tasks,
                        ),
                    )

                conn.commit()
            return True
        except Exception as e:
            logger.error(f"Error updating session context: {e}")
            return False

    def get_session_context(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Get session context for user"""
        query = "SELECT * FROM session_context WHERE session_id = ?"

        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.execute(query, (session_id,))
                row = cursor.fetchone()

                if row:
                    context = dict(row)
                    # Parse JSON fields
                    try:
                        context["active_files"] = json.loads(
                            context.get("active_files", "[]")
                        )
                    except:
                        context["active_files"] = []

                    try:
                        context["recent_urls"] = json.loads(
                            context.get("recent_urls", "[]")
                        )
                    except:
                        context["recent_urls"] = []

                    try:
                        context["pending_tasks"] = json.loads(
                            context.get("pending_tasks", "[]")
                        )
                    except:
                        context["pending_tasks"] = []

                    return context
        except Exception as e:
            logger.error(f"Error getting session context: {e}")
        return None

    def track_interaction(self, user_id: str, success: bool, duration_ms: int):
        """Track user interaction to update stats"""
        try:
            profile = self.get_user_profile(user_id)
            if not profile:
                # Create default profile
                self.update_user_profile(
                    user_id,
                    total_interactions=1,
                    success_rate=1.0 if success else 0.0,
                    avg_session_duration=duration_ms,
                )
                return

            total = profile.get("total_interactions", 0) + 1
            current_success = profile.get("success_rate", 0.0)
            # Calculate new success rate (moving average)
            new_success_rate = (
                (current_success * (total - 1)) + (1.0 if success else 0.0)
            ) / total

            # Update avg duration with exponential smoothing
            current_avg = profile.get("avg_session_duration", 0)
            new_avg = int((current_avg * 0.9) + (duration_ms * 0.1))

            self.update_user_profile(
                user_id,
                total_interactions=total,
                success_rate=new_success_rate,
                avg_session_duration=new_avg,
                last_interaction=datetime.now().isoformat(),
            )
        except Exception as e:
            logger.error(f"Error tracking interaction: {e}")
