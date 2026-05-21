"""Lilith Memory - Sistema de memoria hibrida."""

__version__ = "2.0.0"

from .backends import ChromaBackend, Mem0Backend, MemoryBackend, SQLiteBackend
from .consolidation import ExtractedFact, MemoryConsolidator
from .layers import EpisodicMemory, SemanticMemory, WorkingMemory
from .preferences import PreferenceStore
from .store import MemoryStore


__all__ = [
    "ChromaBackend",
    "EpisodicMemory",
    "ExtractedFact",
    "Mem0Backend",
    "MemoryBackend",
    "MemoryConsolidator",
    "MemoryStore",
    "PreferenceStore",
    "SemanticMemory",
    "SQLiteBackend",
    "WorkingMemory",
]
