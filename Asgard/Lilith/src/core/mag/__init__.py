"""
Memory Augmented Generation (MAG) - Sistema de memoria semántica

v5.0: Sistema de embeddings + vector store para búsqueda semántica.
Permite recuperar contexto relevante basado en similitud semántica.
"""
from .chat_integration import ChatContext, MAGChatIntegration, get_mag_chat_integration
from .context_augmenter import ContextAugmenter, get_context_augmenter
from .embeddings import EmbeddingProvider, get_embedding_provider
from .mag_engine import MAGEngine, get_mag_engine
from .vector_store import Document, SearchResult, VectorStore

__all__ = [
    "EmbeddingProvider",
    "get_embedding_provider",
    "VectorStore",
    "Document",
    "SearchResult",
    "MAGEngine",
    "get_mag_engine",
    "ContextAugmenter",
    "get_context_augmenter",
    # Integración chat
    "MAGChatIntegration",
    "get_mag_chat_integration",
    "ChatContext",
]
