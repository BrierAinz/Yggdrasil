"""
Embedding Pipeline — Generates semantic embeddings for horror game content.

Uses sentence-transformers with all-MiniLM-L6-v2 (384-dim, ~80MB model)
as the default. Designed for RTX 3060 GPU acceleration with CPU fallback.
Fully offline — no cloud API calls.

Supported backends:
    - sentence-transformers (primary, GPU-accelerated via PyTorch)
    - Ollama nomic-embed-text (optional, if Ollama is running locally)
"""

from __future__ import annotations

import hashlib
import threading
from dataclasses import dataclass, field
from typing import Optional, Sequence

import numpy as np


@dataclass
class EmbeddingConfig:
    """Configuration for the embedding pipeline."""

    model_name: str = "all-MiniLM-L6-v2"
    device: str = "cuda"  # "cuda", "cpu", or "auto"
    batch_size: int = 32
    normalize: bool = True
    embedding_dim: int = 384  # all-MiniLM-L6-v2 output dimension
    cache_embeddings: bool = True  # Hash-based cache to avoid re-embedding
    fallback_to_ollama: bool = True  # Fall back to Ollama if sentence-transformers unavailable


class EmbeddingPipeline:
    """
    Embedding pipeline for horror game content.

    Produces normalized 384-dim embeddings for:
        - Game events (scenes, encounters, narrative beats)
        - Player actions (what the player did)
        - Narrative chunks (LLM-generated text)
        - Fear descriptors (types of horror content)

    Usage:
        pipeline = EmbeddingPipeline()
        embedding = pipeline.embed("A dark corridor stretches into nothingness...")
    """

    def __init__(self, config: Optional[EmbeddingConfig] = None):
        self.config = config or EmbeddingConfig()
        self._model = None
        self._lock = threading.Lock()
        self._cache: dict[str, np.ndarray] = {}

    # ── lazy model loading ──────────────────────────────────────────

    @property
    def model(self):
        """Lazy-load the sentence-transformers model (thread-safe)."""
        if self._model is not None:
            return self._model

        with self._lock:
            if self._model is not None:
                return self._model

            try:
                from sentence_transformers import SentenceTransformer

                device = self.config.device
                if device == "auto":
                    try:
                        import torch
                        device = "cuda" if torch.cuda.is_available() else "cpu"
                    except ImportError:
                        device = "cpu"

                self._model = SentenceTransformer(
                    self.config.model_name,
                    device=device,
                )
                return self._model

            except ImportError:
                if self.config.fallback_to_ollama:
                    return None  # Will use Ollama fallback
                raise RuntimeError(
                    "sentence-transformers not installed and Ollama fallback disabled. "
                    "Install with: pip install sentence-transformers"
                )

    def _ensure_model(self):
        """Ensure model is loaded and usable."""
        if self._model is None:
            _ = self.model  # trigger lazy load
        return self._model

    # ── embedding methods ───────────────────────────────────────────

    def embed(self, text: str) -> np.ndarray:
        """
        Embed a single text string into a 384-dim vector.

        Returns a float32 numpy array of shape (384,).
        """
        if not text or not text.strip():
            return np.zeros(self.config.embedding_dim, dtype=np.float32)

        # Check cache
        cache_key = self._cache_key(text)
        if self.config.cache_embeddings and cache_key in self._cache:
            return self._cache[cache_key].copy()

        # Try sentence-transformers
        model = self._ensure_model()
        if model is not None:
            embedding = model.encode(
                text,
                normalize_embeddings=self.config.normalize,
                show_progress_bar=False,
            )
        else:
            # Fallback to Ollama
            embedding = self._embed_via_ollama(text)

        if self.config.cache_embeddings:
            self._cache[cache_key] = embedding.copy()

        return embedding

    def embed_batch(self, texts: Sequence[str]) -> np.ndarray:
        """
        Embed multiple texts at once.

        Returns a float32 array of shape (len(texts), 384).
        """
        if not texts:
            return np.empty((0, self.config.embedding_dim), dtype=np.float32)

        # Split cached vs uncached
        uncached_indices = []
        uncached_texts = []
        results = [None] * len(texts)

        for i, text in enumerate(texts):
            if not text or not text.strip():
                results[i] = np.zeros(self.config.embedding_dim, dtype=np.float32)
                continue

            cache_key = self._cache_key(text)
            if self.config.cache_embeddings and cache_key in self._cache:
                results[i] = self._cache[cache_key].copy()
            else:
                uncached_indices.append(i)
                uncached_texts.append(text)

        if uncached_texts:
            model = self._ensure_model()
            if model is not None:
                new_embeddings = model.encode(
                    uncached_texts,
                    normalize_embeddings=self.config.normalize,
                    batch_size=self.config.batch_size,
                    show_progress_bar=False,
                )
            else:
                new_embeddings = np.array(
                    [self._embed_via_ollama(t) for t in uncached_texts],
                    dtype=np.float32,
                )

            for idx, emb in zip(uncached_indices, new_embeddings):
                results[idx] = emb
                if self.config.cache_embeddings:
                    original_text: str = texts[idx]  # type: ignore[index]
                    cache_key = self._cache_key(original_text)
                    self._cache[cache_key] = emb.copy()

        return np.stack(results)  # type: ignore[arg-type]

    def embed_event(self, event_description: str, event_category: str = "") -> np.ndarray:
        """
        Embed a game event with category-aware weighting.

        Prepends the category to help the embedding model distinguish
        between different types of horror content.
        """
        if event_category:
            text = f"[{event_category}] {event_description}"
        else:
            text = event_description
        return self.embed(text)

    def embed_player_action(
        self, action: str, context: str = ""
    ) -> np.ndarray:
        """
        Embed a player action with optional context.

        Combines the action and its surrounding context for richer embeddings.
        """
        if context:
            text = f"Player action: {action}. Context: {context}"
        else:
            text = f"Player action: {action}"
        return self.embed(text)

    def similarity(self, a: np.ndarray, b: np.ndarray) -> float:
        """
        Cosine similarity between two embedding vectors.

        Assumes vectors are already normalized (unit length).
        """
        return float(np.dot(a, b))

    def similarity_matrix(
        self, query: np.ndarray, candidates: np.ndarray
    ) -> np.ndarray:
        """
        Cosine similarities between a query vector and candidate vectors.

        query: shape (D,) or (1, D)
        candidates: shape (N, D)
        Returns: shape (N,) float array
        """
        query = np.asarray(query, dtype=np.float32).reshape(-1)
        candidates = np.asarray(candidates, dtype=np.float32)
        return np.dot(candidates, query)

    # ── Ollama fallback ─────────────────────────────────────────────

    def _embed_via_ollama(self, text: str) -> np.ndarray:
        """Use Ollama's nomic-embed-text as fallback embedding model."""
        try:
            import requests
        except ImportError:
            raise RuntimeError(
                "Neither sentence-transformers nor requests is available. "
                "Install: pip install sentence-transformers"
            )

        try:
            resp = requests.post(
                "http://localhost:11434/api/embeddings",
                json={"model": "nomic-embed-text", "prompt": text},
                timeout=30,
            )
            resp.raise_for_status()
            data = resp.json()
            emb = np.array(data["embedding"], dtype=np.float32)

            # nomic-embed-text outputs 768-dim; pad/truncate to config dim
            if len(emb) != self.config.embedding_dim:
                if len(emb) > self.config.embedding_dim:
                    emb = emb[: self.config.embedding_dim]
                else:
                    emb = np.pad(emb, (0, self.config.embedding_dim - len(emb)))

            return emb

        except Exception as e:
            raise RuntimeError(
                f"Failed to get embeddings from Ollama: {e}. "
                f"Install sentence-transformers: pip install sentence-transformers"
            )

    # ── cache helpers ───────────────────────────────────────────────

    def _cache_key(self, text: str) -> str:
        """Deterministic hash key for caching embeddings."""
        return hashlib.sha256(text.encode("utf-8")).hexdigest()

    def clear_cache(self) -> None:
        """Clear the embedding cache."""
        self._cache.clear()

    def cache_stats(self) -> dict:
        """Return cache statistics."""
        return {
            "cached_entries": len(self._cache),
            "enabled": self.config.cache_embeddings,
        }


# ── module-level singleton ──────────────────────────────────────────

_pipeline: Optional[EmbeddingPipeline] = None
_pipeline_lock = threading.Lock()


def get_embedding_pipeline(config: Optional[EmbeddingConfig] = None) -> EmbeddingPipeline:
    """Get or create the module-level embedding pipeline singleton."""
    global _pipeline
    if _pipeline is None:
        with _pipeline_lock:
            if _pipeline is None:
                _pipeline = EmbeddingPipeline(config)
    return _pipeline
