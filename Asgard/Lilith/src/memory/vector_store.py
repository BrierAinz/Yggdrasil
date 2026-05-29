"""
Lilith Vector Memory - Vector Store Service
Manages ChromaDB collections for conversations, workflows, and documents
"""

import logging
import os
import time
import uuid
from typing import Any, Dict, List, Optional

import chromadb
from chromadb.api.models.Collection import Collection
from chromadb.config import Settings

from .embedding_service import EmbeddingService

logger = logging.getLogger("VectorStore")


class VectorStore:
    """
    Vector store using ChromaDB for semantic search over conversations, workflows, and docs.
    """

    def __init__(
        self,
        persist_directory: str = "D:\\Proyectos\\Lilith\\Core\\Memory\\vector_db",
        ollama_host: str = "http://localhost:11434",
    ):
        self.persist_directory = persist_directory
        self.embedding_service = EmbeddingService(ollama_host)

        # Initialize ChromaDB client
        self.client = chromadb.PersistentClient(
            path=self.persist_directory,
            settings=Settings(anonymized_telemetry=False, allow_reset=True),
        )

        # Collections
        self.collections = {}
        self._initialize_collections()

        logger.info(f"VectorStore initialized at {persist_directory}")

    def _initialize_collections(self):
        """Initialize all collections if they don't exist"""
        collection_configs = {
            "conversations": {
                "description": "User conversations and messages",
                "metadata_schema": {
                    "timestamp": "float",
                    "session_id": "str",
                    "message_type": "str",  # user, assistant, system, @git, @run, @plan
                    "provider": "str",
                    "model": "str",
                },
            },
            "workflows": {
                "description": "Workflow documentation and actions",
                "metadata_schema": {
                    "source_file": "str",
                    "last_updated": "float",
                    "workflow_id": "str",
                },
            },
            "project_docs": {
                "description": "Project documentation and state",
                "metadata_schema": {
                    "source_file": "str",
                    "doc_type": "str",  # roadmap, state, persona, etc.
                    "last_updated": "float",
                },
            },
            "session_summaries": {
                "description": "Session summaries (resumen, temas, decisiones)",
                "metadata_schema": {
                    "session_id": "str",
                    "generated_at": "str",
                    "temas": "str",
                    "has_decisiones": "str",
                    "has_archivos": "str",
                },
            },
        }

        for name, config in collection_configs.items():
            try:
                collection = self.client.get_or_create_collection(
                    name=name, metadata={"description": config["description"]}
                )
                self.collections[name] = collection
                logger.info(f"Collection '{name}' ready")

            except Exception as e:
                logger.error(f"Error initializing collection '{name}': {e}")

    def add_conversation(
        self,
        text: str,
        message_type: str = "user",
        session_id: Optional[str] = None,
        provider: Optional[str] = None,
        model: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> bool:
        """
        Add a conversation message to vector store.

        Args:
            text: The message text
            message_type: Type of message (user, assistant, system, @git, @run, @plan)
            session_id: Session identifier
            provider: LLM provider used
            model: Model name used
            metadata: Additional metadata

        Returns:
            True if successful
        """
        try:
            # Generate embedding
            embedding = self.embedding_service.generate_embedding(text)
            if not embedding:
                logger.error("Failed to generate embedding for conversation")
                return False

            # Prepare metadata
            doc_metadata = {
                "timestamp": time.time(),
                "session_id": session_id or str(uuid.uuid4()),
                "message_type": message_type,
                "provider": provider or "unknown",
                "model": model or "unknown",
            }

            if metadata:
                doc_metadata.update(metadata)

            # Generate document ID
            doc_id = f"conv_{time.time()}_{uuid.uuid4().hex[:8]}"

            # Add to collection
            self.collections["conversations"].add(
                embeddings=[embedding],
                documents=[text],
                metadatas=[doc_metadata],
                ids=[doc_id],
            )

            logger.debug(f"Added conversation: {doc_id} ({message_type})")
            return True

        except Exception as e:
            logger.error(f"Error adding conversation: {e}")
            return False

    def add_workflow_document(
        self, file_path: str, content: str, workflow_id: Optional[str] = None
    ) -> bool:
        """
        Add a workflow document to vector store.

        Args:
            file_path: Path to the workflow file
            content: Document content
            workflow_id: Optional workflow identifier

        Returns:
            True if successful
        """
        try:
            embedding = self.embedding_service.generate_embedding(content)
            if not embedding:
                logger.error("Failed to generate embedding for workflow")
                return False

            metadata = {
                "source_file": file_path,
                "last_updated": time.time(),
                "workflow_id": workflow_id or os.path.basename(file_path),
            }

            doc_id = f"wf_{os.path.basename(file_path)}_{time.time()}"

            self.collections["workflows"].add(
                embeddings=[embedding],
                documents=[content],
                metadatas=[metadata],
                ids=[doc_id],
            )

            logger.info(f"Indexed workflow: {file_path}")
            return True

        except Exception as e:
            logger.error(f"Error adding workflow: {e}")
            return False

    def add_project_document(
        self,
        file_path: str,
        content: str,
        doc_type: str = "documentation",
        **metadata_kwargs,
    ) -> bool:
        """
        Add a project document (roadmap, state, persona) to vector store.

        Args:
            file_path: Path to the document
            content: Document content
            doc_type: Type of document
            **metadata_kwargs: Additional metadata fields

        Returns:
            True if successful
        """
        try:
            embedding = self.embedding_service.generate_embedding(content)
            if not embedding:
                logger.error("Failed to generate embedding for project doc")
                return False

            metadata = {
                "source_file": file_path,
                "doc_type": doc_type,
                "last_updated": time.time(),
            }

            # Add any additional metadata (for chunking, etc.)
            if metadata_kwargs:
                metadata.update(metadata_kwargs)

            doc_id = f"doc_{doc_type}_{os.path.basename(file_path)}_{time.time()}"

            self.collections["project_docs"].add(
                embeddings=[embedding],
                documents=[content],
                metadatas=[metadata],
                ids=[doc_id],
            )

            logger.info(f"Indexed project document: {file_path}")
            return True

        except Exception as e:
            logger.error(f"Error adding project document: {e}")
            return False

    def add_session_summary(
        self,
        summary_text: str,
        session_id: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> bool:
        """
        Añade un resumen de sesión a la colección session_summaries.
        summary_text: texto del resumen (se embebe).
        session_id: ID de la sesión.
        metadata: dict con session_id, generated_at, temas (JSON string), has_decisiones, has_archivos.
        """
        try:
            if "session_summaries" not in self.collections:
                coll = self.client.get_or_create_collection(
                    name="session_summaries",
                    metadata={"description": "Session summaries"},
                )
                self.collections["session_summaries"] = coll
            text = summary_text or f"Session {session_id}"
            embedding = self.embedding_service.generate_embedding(text)
            if not embedding:
                logger.warning(
                    "No embedding for session summary; skipping ChromaDB add"
                )
                return False
            doc_meta = {
                "session_id": session_id or "",
                "generated_at": (metadata or {}).get("generated_at", ""),
                "temas": (metadata or {}).get("temas", "[]"),
                "has_decisiones": str((metadata or {}).get("has_decisiones", False)),
                "has_archivos": str((metadata or {}).get("has_archivos", False)),
            }
            doc_id = f"summary_{session_id}_{time.time()}"
            self.collections["session_summaries"].add(
                embeddings=[embedding],
                documents=[text],
                metadatas=[doc_meta],
                ids=[doc_id],
            )
            logger.debug("Added session summary to ChromaDB: %s", session_id)
            return True
        except Exception as e:
            logger.error("Error adding session summary to ChromaDB: %s", e)
            return False

    def search_conversations(
        self, query: str, limit: int = 20, time_filter_hours: Optional[float] = 24
    ) -> List[Dict[str, Any]]:
        """
        Search conversation history with semantic similarity.

        Args:
            query: Search query
            limit: Maximum results to return
            time_filter_hours: Filter by hours ago (None for all time)

        Returns:
            List of matching conversations with metadata
        """
        try:
            query_embedding = self.embedding_service.generate_embedding(query)
            if not query_embedding:
                logger.error("Failed to generate query embedding")
                return []

            # Build where clause for time filter
            where_clause = {}
            if time_filter_hours:
                cutoff_time = time.time() - (time_filter_hours * 3600)
                where_clause["timestamp"] = {"$gte": cutoff_time}

            # Search
            results = self.collections["conversations"].query(
                query_embeddings=[query_embedding],
                n_results=min(limit, 100),
                where=where_clause if where_clause else None,
            )

            # Format results
            formatted_results = []
            if results and results["ids"]:
                for i, doc_id in enumerate(results["ids"][0]):
                    formatted_results.append(
                        {
                            "id": doc_id,
                            "text": results["documents"][0][i],
                            "metadata": results["metadatas"][0][i],
                            "score": results["distances"][0][i],
                        }
                    )

            logger.debug(f"Search returned {len(formatted_results)} results")
            return formatted_results

        except Exception as e:
            logger.error(f"Error searching conversations: {e}")
            return []

    def search_workflows(self, query: str, limit: int = 10) -> List[Dict[str, Any]]:
        """Search workflow documents"""
        try:
            query_embedding = self.embedding_service.generate_embedding(query)
            if not query_embedding:
                return []

            results = self.collections["workflows"].query(
                query_embeddings=[query_embedding], n_results=limit
            )

            return self._format_search_results(results)

        except Exception as e:
            logger.error(f"Error searching workflows: {e}")
            return []

    def search_project_docs(self, query: str, limit: int = 10) -> List[Dict[str, Any]]:
        """Search project documentation"""
        try:
            query_embedding = self.embedding_service.generate_embedding(query)
            if not query_embedding:
                return []

            results = self.collections["project_docs"].query(
                query_embeddings=[query_embedding], n_results=limit
            )

            return self._format_search_results(results)

        except Exception as e:
            logger.error(f"Error searching project docs: {e}")
            return []

    def _format_search_results(self, results) -> List[Dict[str, Any]]:
        """Format ChromaDB results to consistent format"""
        formatted = []
        if results and results["ids"]:
            for i, doc_id in enumerate(results["ids"][0]):
                formatted.append(
                    {
                        "id": doc_id,
                        "text": results["documents"][0][i],
                        "metadata": results["metadatas"][0][i],
                        "score": results["distances"][0][i],
                    }
                )
        return formatted

    def get_stats(self) -> Dict[str, Any]:
        """Get statistics for all collections"""
        stats = {}
        try:
            for name, collection in self.collections.items():
                count = collection.count()
                stats[name] = {"document_count": count, "ready": True}
        except Exception as e:
            logger.error(f"Error getting stats: {e}")

        return stats


# ============================================================================
# TEST USAGE
# ============================================================================

if __name__ == "__main__":
    import sys

    print("Testing VectorStore...")
    print("=" * 60)

    # Initialize
    store = VectorStore()

    # Test adding conversation
    print("\n1. Testing conversation storage...")
    success = store.add_conversation(
        text="What is the status of the project?",
        message_type="user",
        session_id="test_session_001",
    )
    print(f"[{'OK' if success else 'FAIL'}] Added conversation")

    # Test adding workflow
    print("\n2. Testing workflow indexing...")
    success = store.add_workflow_document(
        file_path="workflows/test_workflow.md",
        content="This is a test workflow for parallel execution",
        workflow_id="WF-TEST-001",
    )
    print(f"[{'OK' if success else 'FAIL'}] Indexed workflow")

    # Test adding project doc
    print("\n3. Testing project doc indexing...")
    success = store.add_project_document(
        file_path="docs/test_doc.md",
        content="Project roadmap for Lilith v2.0 with memory expansion",
        doc_type="roadmap",
    )
    print(f"[{'OK' if success else 'FAIL'}] Indexed project doc")

    # Test search
    print("\n4. Testing semantic search...")
    results = store.search_conversations("project status")
    print(f"[OK] Search returned {len(results)} results")

    if results:
        print(f"[OK] Top result: {results[0]['text'][:60]}...")
        print(f"[OK] Score: {results[0]['score']:.3f}")

    # Test stats
    print("\n5. Testing stats...")
    stats = store.get_stats()
    print(f"[OK] Stats: {stats}")

    # Cleanup (optional)
    print("\n6. Cleanup...")
    # store.client.reset()  # Uncomment to clear all data

    print("\n" + "=" * 60)
    print("PRUEBAS COMPLETADAS!")
    print("VectorStore is functional")
    sys.exit(0)
