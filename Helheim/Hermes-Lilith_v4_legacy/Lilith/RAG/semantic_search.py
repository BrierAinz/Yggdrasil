"""
Semantic Search for RAG
=======================
Busqueda semantica usando sentence-transformers (reutiliza EmbeddingModel
de EnhancedMemory). Fallback a keyword-matching si no hay embeddings.
"""
import json

# Importar desde enhanced memory
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import numpy as np

sys.path.insert(0, str(Path(__file__).parent.parent))
from Lilith.memory.enhanced import EmbeddingModel, cosine_similarity

EMBEDDINGS_DIR = Path(__file__).parent.parent / "Data" / "rag" / "embeddings"
EMBEDDINGS_DIR.mkdir(parents=True, exist_ok=True)


class SemanticSearcher:
    """Motor de busqueda semantica para chunks de documentos."""

    def __init__(self):
        self.embedder = EmbeddingModel()
        self.chunk_embeddings: Dict[str, np.ndarray] = {}
        self.chunk_metadata: Dict[str, Dict] = {}
        self._loaded = False
        self._load()

    def is_available(self) -> bool:
        return self.embedder.is_available()

    def add_chunk(self, chunk_id: str, content: str, metadata: Dict = None):
        """Agrega un chunk y computa su embedding."""
        if not self.is_available():
            return False
        emb = self.embedder.encode([content])
        if emb is None or len(emb) == 0:
            return False
        self.chunk_embeddings[chunk_id] = emb[0]
        self.chunk_metadata[chunk_id] = metadata or {}
        self._save_chunk(chunk_id, emb[0], metadata)
        return True

    def search(self, query: str, limit: int = 5) -> List[Tuple[str, float]]:
        """Busca chunks semanticamente similares. Retorna (chunk_id, score)."""
        if not self.is_available() or not self.chunk_embeddings:
            return []
        query_emb = self.embedder.encode([query])
        if query_emb is None or len(query_emb) == 0:
            return []
        query_vec = query_emb[0]

        scores = []
        for chunk_id, emb in self.chunk_embeddings.items():
            sim = cosine_similarity(query_vec, emb)
            scores.append((chunk_id, float(sim)))

        scores.sort(key=lambda x: x[1], reverse=True)
        return scores[:limit]

    def _save_chunk(self, chunk_id: str, embedding: np.ndarray, metadata: Dict):
        """Guarda embedding y metadata en disco."""
        emb_path = EMBEDDINGS_DIR / f"{chunk_id}.npy"
        meta_path = EMBEDDINGS_DIR / f"{chunk_id}.json"
        np.save(emb_path, embedding)
        with open(meta_path, "w", encoding="utf-8") as f:
            json.dump(metadata or {}, f, ensure_ascii=False)

    def _load(self):
        """Carga embeddings desde disco."""
        if self._loaded or not EMBEDDINGS_DIR.exists():
            return
        for emb_file in EMBEDDINGS_DIR.glob("*.npy"):
            chunk_id = emb_file.stem
            meta_file = emb_file.with_suffix(".json")
            try:
                emb = np.load(emb_file)
                meta = {}
                if meta_file.exists():
                    with open(meta_file, "r", encoding="utf-8") as f:
                        meta = json.load(f)
                self.chunk_embeddings[chunk_id] = emb
                self.chunk_metadata[chunk_id] = meta
            except Exception:
                continue
        self._loaded = True
        if self.chunk_embeddings:
            print(f"[RAG] {len(self.chunk_embeddings)} embeddings semanticos cargados")


_semantic_searcher: Optional[SemanticSearcher] = None


def get_semantic_searcher() -> SemanticSearcher:
    global _semantic_searcher
    if _semantic_searcher is None:
        _semantic_searcher = SemanticSearcher()
    return _semantic_searcher
