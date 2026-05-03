"""
Memory Base Module
==================
Funciones y constantes compartidas entre todos los modulos de memoria.
Evita circular imports.
"""
from pathlib import Path
from typing import List, Optional

import numpy as np

# Ruta base del proyecto
_PROJECT_ROOT = Path(__file__).parent.parent.parent
_MEMORY_DIR = _PROJECT_ROOT / "memory"
_MEMORY_DIR.mkdir(exist_ok=True)

DB_PATH = _MEMORY_DIR / "lilith_memory.db"


def cosine_similarity(a: np.ndarray, b: np.ndarray) -> float:
    """Calcula similitud coseno entre dos vectores."""
    return float(np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b) + 1e-8))


class EmbeddingModel:
    """Modelo de embeddings con lazy loading. Singleton."""

    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._model = None
            cls._instance._initialized = False
        return cls._instance

    def _init(self):
        if self._initialized:
            return
        try:
            from sentence_transformers import SentenceTransformer

            self._model = SentenceTransformer("all-MiniLM-L6-v2")
            self._initialized = True
        except ImportError:
            print("[Memory] sentence-transformers no disponible")
            self._model = None

    def is_available(self) -> bool:
        self._init()
        return self._model is not None

    def encode(self, texts: List[str]) -> Optional[np.ndarray]:
        self._init()
        if self._model is None:
            return None
        return self._model.encode(texts, convert_to_numpy=True, show_progress_bar=False)

    @property
    def dimension(self) -> int:
        return 384
