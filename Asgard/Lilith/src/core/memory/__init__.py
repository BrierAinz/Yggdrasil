"""
Lilith 3.0/5.0 — Memoria multi-capa.
MemoryManager: interfaz única. semantic / episodic / procedural.
LongTermMemory: archivado, resúmenes y recuperación histórica.
"""
from .episodic import EpisodicStore, InteractionLog
from .long_term import ConversationSummary, LongTermMemory, get_long_term_memory
from .manager import MemoryManager
from .procedural import LearnedPattern, ProceduralStore
from .semantic import SemanticStore

__all__ = [
    "MemoryManager",
    "SemanticStore",
    "EpisodicStore",
    "ProceduralStore",
    "InteractionLog",
    "LearnedPattern",
    # v5.0 Long-term memory
    "LongTermMemory",
    "ConversationSummary",
    "get_long_term_memory",
]
