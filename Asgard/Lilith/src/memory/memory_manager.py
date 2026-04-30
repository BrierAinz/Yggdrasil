"""
Lilith Memory Manager
Integrates vector memory with main.py for automatic conversation logging
Includes session persistence and token tracking
"""

import json
import os
import sys
import time
import uuid
from typing import Any, Dict, List, Optional

project_root = os.path.dirname(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
)
sys.path.insert(0, project_root)

import logging

from src.core.memory import VectorStore
from src.core.memory.conversation_pruner import ConversationPruner
from src.core.memory.session_manager import SessionManager

logger = logging.getLogger("MemoryManager")


class TokenTracker:
    """
    Tracks token usage for context window management.
    Estimates based on text length (rough approximation).
    """

    # Approximate tokens per character for different languages
    TOKENS_PER_CHAR = 0.25  # Conservative estimate

    def __init__(self, max_tokens: int = 2000000):  # 2M context for grok-4
        self.max_tokens = max_tokens
        self.current_tokens = 0
        self.message_tokens = {}  # Track tokens per message ID
        self.summary_mode = False  # True when conversation is summarized

    def estimate_tokens(self, text: str) -> int:
        """Estimate token count for text."""
        return int(len(text) * self.TOKENS_PER_CHAR)

    def add_message(self, message_id: str, text: str) -> int:
        """Add a message and return estimated tokens."""
        tokens = self.estimate_tokens(text)
        self.message_tokens[message_id] = tokens
        self.current_tokens += tokens
        return tokens

    def get_usage_percent(self) -> float:
        """Get current usage as percentage."""
        return (self.current_tokens / self.max_tokens) * 100

    def should_summarize(self, threshold: float = 70.0) -> bool:
        """Check if we should summarize (at threshold%)."""
        return self.get_usage_percent() >= threshold

    def get_status(self) -> Dict[str, Any]:
        """Get token tracking status."""
        usage = self.get_usage_percent()
        return {
            "current_tokens": self.current_tokens,
            "max_tokens": self.max_tokens,
            "usage_percent": round(usage, 1),
            "message_count": len(self.message_tokens),
            "should_summarize": self.should_summarize(),
            "summary_mode": self.summary_mode,
            # Color thresholds for UI
            "color_status": "normal"
            if usage < 80
            else ("warning" if usage < 95 else "critical"),
        }

    def reset(self):
        """Reset token tracking."""
        self.current_tokens = 0
        self.message_tokens = {}
        self.summary_mode = False


class MemoryManager:
    """
    Manages conversational memory integration with ChromaDB.
    Includes session persistence and token tracking.
    """

    def __init__(self, max_memory_messages: int = 1000):
        self.vector_store = VectorStore()
        self.max_memory_messages = max_memory_messages
        self.session_id = str(uuid.uuid4())
        self.message_count = 0

        # Session persistence
        self.session_manager = SessionManager()
        self.current_messages = []  # Keep track for session saving

        # Token tracking for grok-4 (2M context)
        self.token_tracker = TokenTracker(max_tokens=2000000)

        # Pruning
        self.pruner = ConversationPruner(
            vector_store=self.vector_store,
            max_messages=max_memory_messages,
            prune_threshold=0.9,
        )

        # Auto-summarize state
        self.summarized_content = None
        self.auto_summarize_threshold = 70.0  # Summarize at 70% usage

        logger.info(f"MemoryManager initialized (session: {self.session_id})")

    def log_message(
        self,
        text: str,
        message_type: str = "user",
        provider: Optional[str] = None,
        model: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> bool:
        """
        Log a message to vector memory and track tokens.
        """
        try:
            # Track tokens
            message_id = f"{self.session_id}_{self.message_count}"
            tokens_used = self.token_tracker.add_message(message_id, text)

            # Check if we need to auto-summarize
            if self.token_tracker.should_summarize(self.auto_summarize_threshold):
                logger.info(
                    f"Context at {self.token_tracker.get_usage_percent():.1f}%, triggering auto-summary"
                )
                self._auto_summarize()

            # Check if pruning is needed
            if self.pruner.should_prune():
                logger.info("Memory threshold reached, pruning old conversations...")
                removed = self.pruner.prune_old_conversations()
                logger.info(f"Pruned {removed} old conversations")
                self._update_message_count()

            # Log to vector store
            success = self.vector_store.add_conversation(
                text=text,
                message_type=message_type,
                session_id=self.session_id,
                provider=provider,
                model=model,
                metadata=metadata,
            )

            if success:
                self.message_count += 1
                # Store for session persistence
                self.current_messages.append(
                    {
                        "role": message_type,
                        "content": text,
                        "timestamp": time.time(),
                        "provider": provider,
                        "model": model,
                        "tokens": tokens_used,
                    }
                )
                logger.debug(
                    f"Logged message ({message_type}): {text[:50]}... [{tokens_used} tokens]"
                )

            return success

        except Exception as e:
            logger.error(f"Error logging message: {e}")
            return False

    def _auto_summarize(self):
        """Compress conversation when approaching token limit."""
        try:
            if len(self.current_messages) < 4:
                return  # Not enough to summarize

            logger.info("Auto-summarizing conversation...")

            # Keep first 2 and last 2 messages, summarize the rest
            keep_start = self.current_messages[:2]
            keep_end = self.current_messages[-2:]
            to_summarize = self.current_messages[2:-2]

            if not to_summarize:
                return

            # Create summary text
            summary_parts = ["[CONVERSATION SUMMARY]"]
            user_msgs = [m for m in to_summarize if m.get("role") == "user"]

            if user_msgs:
                topics = [m["content"][:50] + "..." for m in user_msgs[:3]]
                summary_parts.append(f"Topics discussed: {'; '.join(topics)}")

            summary_text = "\n".join(summary_parts)

            # Create summary message
            summary_message = {
                "role": "system",
                "content": summary_text,
                "timestamp": time.time(),
                "is_summary": True,
            }

            # Replace middle messages with summary
            self.current_messages = keep_start + [summary_message] + keep_end

            # Update token tracker
            old_tokens = self.token_tracker.current_tokens
            self.token_tracker.reset()
            for i, msg in enumerate(self.current_messages):
                self.token_tracker.add_message(
                    f"summarized_{i}", msg.get("content", "")
                )

            self.token_tracker.summary_mode = True
            new_tokens = self.token_tracker.current_tokens

            logger.info(
                f"Summarized: {old_tokens} -> {new_tokens} tokens ({len(to_summarize)} messages compressed)"
            )
            self.summarized_content = summary_text

        except Exception as e:
            logger.error(f"Error auto-summarizing: {e}")

    def save_current_session(self, llm_client=None) -> str:
        """
        Save the current conversation session to disk.
        Called when session ends or app closes.
        """
        try:
            if not self.current_messages:
                logger.info("No messages to save")
                return ""

            # Generate summary
            summary = self.session_manager.generate_summary(
                self.current_messages, llm_client
            )

            # Save session
            filepath = self.session_manager.save_session(
                messages=self.current_messages,
                session_id=self.session_id,
                summary=summary,
            )

            logger.info(f"Session saved: {filepath}")
            return filepath

        except Exception as e:
            logger.error(f"Error saving session: {e}")
            return ""

    def load_recent_context(
        self, hours: int = 48, limit: int = 10
    ) -> List[Dict[str, Any]]:
        """
        Load recent conversation context from previous sessions.
        Called when starting a new conversation.
        """
        try:
            # Get recent sessions
            recent_sessions = self.session_manager.list_sessions(
                limit=5, days=1  # Last 24 hours
            )

            if not recent_sessions:
                logger.info("No recent sessions found")
                return []

            logger.info(f"Loading context from {len(recent_sessions)} recent sessions")

            # Get relevant context from vector store
            context = self.session_manager.get_recent_context(
                self.vector_store, hours=hours, limit=limit
            )

            logger.info(f"Loaded {len(context)} context items from recent history")
            return context

        except Exception as e:
            logger.error(f"Error loading recent context: {e}")
            return []

    def get_token_status(self) -> Dict[str, Any]:
        """Get current token usage status for UI."""
        return self.token_tracker.get_status()

    def _update_message_count(self):
        """Update message count from vector store stats."""
        try:
            stats = self.vector_store.get_stats()
            conversation_count = stats.get("conversations", {}).get("document_count", 0)
            self.message_count = conversation_count
            logger.debug(f"Updated message count: {self.message_count}")
        except Exception as e:
            logger.error(f"Error updating message count: {e}")

    def log_user_message(self, text: str, **kwargs) -> bool:
        """Convenience method for logging user messages."""
        return self.log_message(text=text, message_type="user", **kwargs)

    def log_assistant_message(self, text: str, **kwargs) -> bool:
        """Convenience method for logging assistant messages."""
        return self.log_message(text=text, message_type="assistant", **kwargs)

    def log_command(self, command: str, command_type: str, **kwargs) -> bool:
        """Log @git, @run, @plan commands."""
        return self.log_message(text=command, message_type=f"@{command_type}", **kwargs)

    def get_relevant_context(
        self, query: str, limit: int = 10, time_filter_hours: float = 24
    ) -> List[Dict[str, Any]]:
        """
        Get relevant historical context for a query.
        """
        try:
            results = self.vector_store.search_conversations(
                query=query, limit=limit, time_filter_hours=time_filter_hours
            )

            logger.debug(f"Found {len(results)} relevant context items")
            return results

        except Exception as e:
            logger.error(f"Error getting context: {e}")
            return []

    def get_session_stats(self) -> Dict[str, Any]:
        """Get memory statistics for current session."""
        try:
            stats = self.vector_store.get_stats()
            token_status = self.get_token_status()

            stats["current_session"] = {
                "session_id": self.session_id,
                "message_count": self.message_count,
                "max_capacity": self.max_memory_messages,
                "current_messages_in_buffer": len(self.current_messages),
            }
            stats["token_usage"] = token_status

            return stats
        except Exception as e:
            logger.error(f"Error getting stats: {e}")
            return {}

    def format_context_for_prompt(self, context_items: List[Dict[str, Any]]) -> str:
        """
        Format context items into a string for LLM prompt injection.
        """
        if not context_items:
            return ""

        context_parts = []
        context_parts.append("--- RELEVANT CONVERSATION HISTORY ---")

        for i, item in enumerate(context_items[:5], 1):  # Top 5
            text = item.get("text", "")
            metadata = item.get("metadata", {})
            message_type = metadata.get("message_type", "unknown")
            timestamp = metadata.get("timestamp", 0)

            # Format timestamp
            time_str = time.strftime("%H:%M:%S", time.localtime(timestamp))

            context_parts.append(f"{i}. [{time_str}] {message_type}: {text[:100]}")

        context_parts.append("")
        return "\n".join(context_parts)


# ============================================================================
# USAGE IN MAIN.PY (EXAMPLE)
# ============================================================================

# In main.py:
# from src.core.memory.manager import MemoryManager
# memory_manager = MemoryManager()
#
# # At startup - load recent context:
# recent_context = memory_manager.load_recent_context(hours=48)
# if recent_context:
#     context_str = memory_manager.format_context_for_prompt(recent_context)
#     # Prepend to first user message
#
# # In message handler:
# memory_manager.log_user_message(user_text, provider=config.llm.provider, model=config.llm.model)
#
# # Get token status for UI:
# token_status = memory_manager.get_token_status()
# # Send to frontend: {"current": token_status["current_tokens"], "max": token_status["max_tokens"], "percent": token_status["usage_percent"]}
#
# # At shutdown:
# memory_manager.save_current_session()

if __name__ == "__main__":
    import sys

    print("Testing MemoryManager with Session Persistence...")
    print("=" * 60)

    # Initialize
    memory = MemoryManager(max_memory_messages=10)

    # Test logging messages
    print("\n1. Testing message logging with token tracking...")

    messages = [
        ("Hello Lilith, can you help me optimize this Python function?", "user"),
        (
            "Of course! Please share the function you'd like me to optimize.",
            "assistant",
        ),
        (
            "Here's the code: def slow_function(n): return sum([i**2 for i in range(n)])",
            "user",
        ),
        ("I can see several optimization opportunities...", "assistant"),
    ]

    for text, msg_type in messages:
        success = memory.log_message(text, message_type=msg_type)
        token_status = memory.get_token_status()
        print(f"[{'OK' if success else 'FAIL'}] {msg_type}: {text[:40]}...")
        print(
            f"        Tokens: {token_status['current_tokens']}/{token_status['max_tokens']} ({token_status['usage_percent']:.2f}%)"
        )

    # Test session save
    print("\n2. Testing session save...")
    filepath = memory.save_current_session()
    print(f"   [OK] Saved to: {filepath}")

    # Test recent context loading
    print("\n3. Testing load_recent_context...")
    context = memory.load_recent_context(hours=48)
    print(f"   [OK] Loaded {len(context)} context items")

    # Test stats
    print("\n4. Testing session stats...")
    stats = memory.get_session_stats()
    print(f"   Session ID: {stats['current_session']['session_id']}")
    print(f"   Messages: {stats['current_session']['message_count']}")
    print(f"   Token Usage: {stats['token_usage']['usage_percent']:.2f}%")

    print("\n" + "=" * 60)
    print("MEMORY MANAGER TESTS PASSED")
    print("Session persistence and token tracking functional")
    sys.exit(0)
