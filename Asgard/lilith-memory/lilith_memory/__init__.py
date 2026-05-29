<<<<<<< HEAD
"""Lilith Memory - Vector memory store with SQLite backend."""

__version__ = "1.0.0"

from lilith_memory.store import MemoryStore

__all__ = ["MemoryStore"]
=======
"""Lilith Memory - Sistema de memoria hibrida."""

__version__ = "2.0.0"

from .backends import MemoryBackend, SQLiteBackend
from .consolidation import ExtractedFact, MemoryConsolidator
from .layers import EpisodicMemory, SemanticMemory, WorkingMemory
from .preferences import PreferenceStore
from .store import MemoryStore


try:
    from .backends import ChromaBackend
except ImportError:  # chromadb not installed
    ChromaBackend = None  # type: ignore[assignment,misc]

try:
    from .backends import Mem0Backend
except ImportError:  # mem0ai not installed
    Mem0Backend = None  # type: ignore[assignment,misc]


__all__ = [
    "EpisodicMemory",
    "ExtractedFact",
    "MemoryBackend",
    "MemoryConsolidator",
    "MemoryStore",
    "PreferenceStore",
    "SQLiteBackend",
    "SemanticMemory",
    "WorkingMemory",
]
if ChromaBackend is not None:
    __all__.append("ChromaBackend")
if Mem0Backend is not None:
    __all__.append("Mem0Backend")
>>>>>>> origin/main
