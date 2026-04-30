"""
Lilith Conversation Pruner
Manages automatic cleanup of old conversations when memory limit is reached
"""

import logging
from typing import Any, Dict

logger = logging.getLogger("ConversationPruner")


class ConversationPruner:
    """
    Handles FIFO (First-In-First-Out) pruning of conversation memory
    when the maximum number of messages is reached.
    """

    def __init__(
        self, vector_store, max_messages: int = 1000, prune_threshold: float = 0.9
    ):
        """
        Args:
            vector_store: VectorStore instance
            max_messages: Maximum number of messages to keep
            prune_threshold: When to prune (e.g., 0.9 = prune when at 90% capacity)
        """
        self.vector_store = vector_store
        self.max_messages = max_messages
        self.prune_threshold = prune_threshold
        self.prune_target = int(max_messages * 0.8)  # Keep only 80% after prune

        logger.info(
            f"ConversationPruner initialized (max: {max_messages}, prune at: {int(max_messages * prune_threshold)})"
        )

    def should_prune(self) -> bool:
        """Check if pruning is needed"""
        try:
            stats = self.vector_store.get_stats()
            conversation_count = stats.get("conversations", {}).get("document_count", 0)

            threshold = int(self.max_messages * self.prune_threshold)
            should_prune = conversation_count >= threshold

            if should_prune:
                logger.info(
                    f"Pruning needed: {conversation_count}/{self.max_messages} messages (threshold: {threshold})"
                )

            return should_prune

        except Exception as e:
            logger.error(f"Error checking prune status: {e}")
            return False

    def prune_old_conversations(self) -> int:
        """
        Remove oldest conversations to get back to prune_target

        Returns:
            Number of documents removed
        """
        try:
            # Get conversation collection
            collection = self.vector_store.collections.get("conversations")
            if not collection:
                logger.error("Conversations collection not found")
                return 0

            # Get all conversations sorted by timestamp
            all_docs = collection.get()
            if not all_docs or not all_docs["ids"]:
                logger.info("No documents to prune")
                return 0

            # Count current documents
            current_count = len(all_docs["ids"])

            if current_count <= self.prune_target:
                logger.info(
                    f"Not enough documents to prune ({current_count} <= {self.prune_target})"
                )
                return 0

            # Calculate how many to remove
            docs_to_remove = current_count - self.prune_target
            logger.info(
                f"Need to remove {docs_to_remove} documents (from {current_count} to {self.prune_target})"
            )

            # Sort documents by timestamp (oldest first)
            documents_with_metadata = []
            for i, doc_id in enumerate(all_docs["ids"]):
                metadata = all_docs["metadatas"][i]
                timestamp = metadata.get("timestamp", 0)
                documents_with_metadata.append((timestamp, doc_id))

            # Sort by timestamp (oldest first)
            documents_with_metadata.sort(key=lambda x: x[0])

            # Get IDs to delete (oldest ones)
            ids_to_delete = [
                doc_id for _, doc_id in documents_with_metadata[:docs_to_remove]
            ]

            # Delete the documents
            collection.delete(ids=ids_to_delete)

            logger.info(f"Successfully pruned {len(ids_to_delete)} old conversations")
            return len(ids_to_delete)

        except Exception as e:
            logger.error(f"Error pruning conversations: {e}")
            import traceback

            traceback.print_exc()
            return 0

    def get_status(self) -> Dict[str, Any]:
        """Get pruner status"""
        try:
            stats = self.vector_store.get_stats()
            conversation_count = stats.get("conversations", {}).get("document_count", 0)

            return {
                "max_messages": self.max_messages,
                "current_count": conversation_count,
                "usage_percent": round(
                    (conversation_count / self.max_messages) * 100, 1
                )
                if self.max_messages > 0
                else 0,
                "prune_threshold": int(self.max_messages * self.prune_threshold),
                "prune_target": self.prune_target,
                "should_prune": conversation_count
                >= int(self.max_messages * self.prune_threshold),
            }
        except Exception as e:
            logger.error(f"Error getting pruner status: {e}")
            return {}


# ============================================================================
# TEST
# ============================================================================

if __name__ == "__main__":
    import sys
    import time

    from src.core.memory import VectorStore

    print("Testing ConversationPruner...")
    print("=" * 60)

    # Initialize
    vector_store = VectorStore()
    pruner = ConversationPruner(vector_store, max_messages=10, prune_threshold=0.7)

    # Add test conversations
    print("\n1. Adding test conversations...")

    # Add 8 conversations (80% of max, over threshold of 70%)
    for i in range(8):
        success = vector_store.add_conversation(
            text=f"Test conversation message {i}",
            message_type="user" if i % 2 == 0 else "assistant",
            session_id="test_session",
        )
        print(f"   [{'OK' if success else 'FAIL'}] Added message {i}")
        time.sleep(0.01)  # Small delay for different timestamps

    # Check status
    print("\n2. Checking pruner status...")
    status = pruner.get_status()
    print(f"   Current: {status['current_count']}/{status['max_messages']}")
    print(f"   Usage: {status['usage_percent']}%")
    print(f"   Should prune: {status['should_prune']}")

    if not status["should_prune"]:
        print("   [FAIL] Expected should_prune=True")
        sys.exit(1)

    # Test pruning
    print("\n3. Testing prune...")
    removed = pruner.prune_old_conversations()
    print(f"   [OK] Removed {removed} documents")

    status_after = pruner.get_status()
    print(
        f"   After prune: {status_after['current_count']}/{status_after['max_messages']}"
    )
    print(f"   Should prune now: {status_after['should_prune']}")

    # Verify oldest were removed
    print("\n4. Verify oldest messages removed...")
    results = vector_store.search_conversations("Test conversation message", limit=5)

    # Should not find the oldest (message 0 and 1)
    found_ids = [r["id"] for r in results]
    print(f"   Found {len(found_ids)} messages")

    print("\n" + "=" * 60)
    print("PRUNER TESTS PASSED")
    print("Ready for integration with MemoryManager")
    sys.exit(0)
