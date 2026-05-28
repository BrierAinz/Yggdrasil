"""
Horror GameMaster — Memory & Embeddings Module

Provides player memory persistence, fear profile management, and
semantic embeddings for context-aware procedural horror generation.

Architecture:
    - LanceDB (primary) / ChromaDB (fallback) for vector storage
    - sentence-transformers (all-MiniLM-L6-v2) for embeddings
    - SQLite for structured player profile metadata
    - Pydantic v2 for data modeling and validation

Target: RTX 3060 12GB, fully offline, no cloud APIs.
"""

from .player_memory import (
    PlayerMemoryStore,
    FearFingerprint,
    ResponsePattern,
    HabituationTracker,
    SessionMemory,
    PlayerFearProfile,
    GameEvent,
    MemoryQueryResult,
    FearDimension,
    ActionType,
    EventCategory,
)
from .embeddings import (
    EmbeddingPipeline,
    EmbeddingConfig,
    get_embedding_pipeline,
)

__all__ = [
    # Store
    "PlayerMemoryStore",
    # Models
    "FearFingerprint",
    "ResponsePattern",
    "HabituationTracker",
    "SessionMemory",
    "PlayerFearProfile",
    "GameEvent",
    "MemoryQueryResult",
    "FearDimension",
    "ActionType",
    "EventCategory",
    # Embeddings
    "EmbeddingPipeline",
    "EmbeddingConfig",
    "get_embedding_pipeline",
]
