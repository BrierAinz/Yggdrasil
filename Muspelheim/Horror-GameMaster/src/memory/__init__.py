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

from .embeddings import (
    EmbeddingConfig,
    EmbeddingPipeline,
    get_embedding_pipeline,
)
from .player_memory import (
    ActionType,
    EventCategory,
    FearDimension,
    FearFingerprint,
    GameEvent,
    HabituationTracker,
    MemoryQueryResult,
    PlayerFearProfile,
    PlayerMemoryStore,
    ResponsePattern,
    SessionMemory,
)


__all__ = [
    "ActionType",
    "EmbeddingConfig",
    # Embeddings
    "EmbeddingPipeline",
    "EventCategory",
    "FearDimension",
    # Models
    "FearFingerprint",
    "GameEvent",
    "HabituationTracker",
    "MemoryQueryResult",
    "PlayerFearProfile",
    # Store
    "PlayerMemoryStore",
    "ResponsePattern",
    "SessionMemory",
    "get_embedding_pipeline",
]
