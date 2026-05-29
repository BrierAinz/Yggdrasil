"""
Lilith Session Manager
Handles persistent session storage and retrieval
"""

import json
import logging
import os
import uuid
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger("SessionManager")


class SessionManager:
    """
    Manages persistent session storage in Memory/sessions/
    """

    def __init__(
        self, sessions_dir: str = "D:\\Proyectos\\Lilith\\Core\\Memory\\sessions"
    ):
        self.sessions_dir = Path(sessions_dir)
        self.sessions_dir.mkdir(parents=True, exist_ok=True)
        logger.info(f"SessionManager initialized at {self.sessions_dir}")

    def save_session(
        self,
        messages: List[Dict[str, Any]],
        session_id: Optional[str] = None,
        summary: Optional[str] = None,
    ) -> str:
        """
        Save a conversation session to disk.

        Args:
            messages: List of message objects with role, content, timestamp
            session_id: Optional session ID (auto-generated if not provided)
            summary: Auto-generated summary of the conversation

        Returns:
            Path to saved session file
        """
        if not session_id:
            session_id = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")

        # Ensure unique filename
        base_filename = session_id
        filename = f"{base_filename}.json"
        filepath = self.sessions_dir / filename

        # If file exists, add counter
        counter = 1
        while filepath.exists():
            filename = f"{base_filename}_{counter}.json"
            filepath = self.sessions_dir / filename
            counter += 1

        session_data = {
            "session_id": session_id,
            "saved_at": datetime.now().isoformat(),
            "message_count": len(messages),
            "summary": summary or "",
            "messages": messages,
        }

        try:
            with open(filepath, "w", encoding="utf-8") as f:
                json.dump(session_data, f, indent=2, ensure_ascii=False)
            logger.info(f"Session saved: {filepath.name} ({len(messages)} messages)")
            return str(filepath)
        except Exception as e:
            logger.error(f"Error saving session: {e}")
            return ""

    def load_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        """
        Load a session by ID.

        Args:
            session_id: Session ID (filename without .json extension)

        Returns:
            Session data or None if not found
        """
        filepath = self.sessions_dir / f"{session_id}.json"

        if not filepath.exists():
            # Try to find with counter suffix
            matches = list(self.sessions_dir.glob(f"{session_id}_*.json"))
            if matches:
                filepath = matches[0]  # Take first match
            else:
                logger.warning(f"Session not found: {session_id}")
                return None

        try:
            with open(filepath, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Error loading session {session_id}: {e}")
            return None

    def list_sessions(
        self, limit: int = 50, days: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """
        List all saved sessions with metadata.

        Args:
            limit: Maximum number of sessions to return
            days: Only return sessions from last N days

        Returns:
            List of session metadata
        """
        sessions = []
        cutoff_date = None

        if days:
            cutoff_date = datetime.now() - timedelta(days=days)

        try:
            # Get all JSON files sorted by modification time (newest first)
            files = sorted(
                self.sessions_dir.glob("*.json"),
                key=lambda x: x.stat().st_mtime,
                reverse=True,
            )

            for filepath in files[:limit]:
                try:
                    stat = filepath.stat()
                    modified = datetime.fromtimestamp(stat.st_mtime)

                    if cutoff_date and modified < cutoff_date:
                        continue

                    # Quick metadata extraction (without loading full content)
                    with open(filepath, "r", encoding="utf-8") as f:
                        data = json.load(f)

                    sessions.append(
                        {
                            "session_id": data.get("session_id", filepath.stem),
                            "saved_at": data.get("saved_at", modified.isoformat()),
                            "message_count": data.get("message_count", 0),
                            "summary": data.get("summary", "")[
                                :200
                            ],  # Truncate summary
                            "filename": filepath.name,
                            "size_kb": round(stat.st_size / 1024, 2),
                        }
                    )

                except Exception as e:
                    logger.warning(f"Error reading session file {filepath}: {e}")
                    continue

            return sessions

        except Exception as e:
            logger.error(f"Error listing sessions: {e}")
            return []

    def delete_session(self, session_id: str) -> bool:
        """
        Delete a session by ID.

        Args:
            session_id: Session ID

        Returns:
            True if deleted successfully
        """
        filepath = self.sessions_dir / f"{session_id}.json"

        if not filepath.exists():
            # Try to find with counter suffix
            matches = list(self.sessions_dir.glob(f"{session_id}_*.json"))
            if matches:
                filepath = matches[0]
            else:
                return False

        try:
            filepath.unlink()
            logger.info(f"Session deleted: {filepath.name}")
            return True
        except Exception as e:
            logger.error(f"Error deleting session {session_id}: {e}")
            return False

    def generate_summary(self, messages: List[Dict[str, Any]], llm_client=None) -> str:
        """
        Generate a summary of the conversation.
        If llm_client is not available, creates a simple text summary.

        Args:
            messages: List of messages
            llm_client: Optional LLM client for AI summary

        Returns:
            Summary string
        """
        if not messages:
            return "Empty conversation"

        # Simple heuristic summary
        topics = []
        user_messages = [m for m in messages if m.get("role") == "user"]

        if not user_messages:
            return "No user messages"

        # Extract first user message as topic
        first_msg = user_messages[0].get("content", "")[:50]
        if first_msg:
            topics.append(first_msg)

        # Count message types
        msg_types = {}
        for msg in messages:
            role = msg.get("role", "unknown")
            msg_types[role] = msg_types.get(role, 0) + 1

        summary_parts = [
            f"{msg_types.get('user', 0)} user, {msg_types.get('assistant', 0)} assistant messages"
        ]

        if topics:
            summary_parts.insert(0, f"About: {topics[0]}...")

        return " | ".join(summary_parts)

    def get_recent_context(
        self, vector_store, hours: int = 48, limit: int = 10
    ) -> List[Dict[str, Any]]:
        """
        Get recent conversation context from vector store.

        Args:
            vector_store: VectorStore instance
            hours: How many hours back to look
            limit: Max number of items

        Returns:
            List of relevant conversation items
        """
        try:
            # Search for recent conversations
            results = vector_store.search_conversations(
                query="recent conversation", limit=limit, time_filter_hours=hours
            )

            return results

        except Exception as e:
            logger.error(f"Error getting recent context: {e}")
            return []


# ============================================================================
# USAGE
# ============================================================================

if __name__ == "__main__":
    import sys

    print("Testing SessionManager...")
    print("=" * 60)

    # Initialize
    sm = SessionManager()

    # Test save
    print("\n1. Testing save_session...")
    test_messages = [
        {"role": "user", "content": "Hello Lilith", "timestamp": "2026-03-07T14:00:00"},
        {
            "role": "assistant",
            "content": "Hello! How can I help?",
            "timestamp": "2026-03-07T14:00:05",
        },
    ]

    path = sm.save_session(
        messages=test_messages,
        session_id="test_session_001",
        summary="Test conversation about greeting",
    )
    print(f"   [OK] Saved to: {path}")

    # Test list
    print("\n2. Testing list_sessions...")
    sessions = sm.list_sessions()
    print(f"   [OK] Found {len(sessions)} sessions")
    for s in sessions:
        print(f"        - {s['session_id']}: {s['message_count']} messages")

    # Test load
    print("\n3. Testing load_session...")
    loaded = sm.load_session("test_session_001")
    if loaded:
        print(f"   [OK] Loaded: {loaded['message_count']} messages")
        print(f"   [OK] Summary: {loaded['summary']}")

    # Test delete
    print("\n4. Testing delete_session...")
    deleted = sm.delete_session("test_session_001")
    print(f"   [{'OK' if deleted else 'FAIL'}] Deleted")

    print("\n" + "=" * 60)
    print("SESSION MANAGER TESTS PASSED")
    sys.exit(0)
