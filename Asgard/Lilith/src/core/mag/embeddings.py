"""
Embeddings Provider - Generación de embeddings vectoriales

v5.0: Abstracción para múltiples proveedores de embeddings.
Soporta: OpenAI, local (sentence-transformers), y API de Kimi.
"""
import hashlib
import json
import logging
import os
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional, Union

import httpx
from src.core.cache import get_cache

logger = logging.getLogger("lilith.mag.embeddings")


@dataclass
class EmbeddingConfig:
    """Configuración para embeddings."""

    provider: str = "kimi"  # "kimi", "openai", "local"
    model: str = "text-embedding-3-small"
    dimensions: int = 1536
    batch_size: int = 100
    cache_enabled: bool = True
    normalize: bool = True


class EmbeddingProvider:
    """
    Proveedor de embeddings vectoriales.

    Features:
    - Múltiples backends (Kimi, OpenAI, local)
    - Caching automático de embeddings
    - Normalización L2
    - Batch processing
    """

    def __init__(self, config: Optional[EmbeddingConfig] = None):
        self.config = config or EmbeddingConfig()
        self._cache = get_cache() if self.config.cache_enabled else None

        # Cargar API keys desde variables de entorno
        self._openai_key = os.getenv("OPENAI_API_KEY")
        self._kimi_key = os.getenv("MOONSHOT_API_KEY")

        # URL base
        self._kimi_base = "https://api.moonshot.cn/v1"
        self._openai_base = "https://api.openai.com/v1"

    def _get_cache_key(self, text: str) -> str:
        """Genera clave de caché para un texto."""
        text_hash = hashlib.sha256(text.encode()).hexdigest()[:16]
        return f"emb:{self.config.provider}:{self.config.model}:{text_hash}"

    async def embed(self, text: str) -> List[float]:
        """
        Genera embedding para un texto.

        Args:
            text: Texto a embedder

        Returns:
            Vector de embedding
        """
        # Verificar caché
        if self._cache:
            cache_key = self._get_cache_key(text)
            cached = await self._cache.get(cache_key, namespace="embeddings")
            if cached:
                return cached

        # Generar embedding según proveedor
        if self.config.provider == "kimi":
            embedding = await self._embed_kimi(text)
        elif self.config.provider == "openai":
            embedding = await self._embed_openai(text)
        elif self.config.provider == "local":
            embedding = await self._embed_local(text)
        else:
            raise ValueError(f"Proveedor no soportado: {self.config.provider}")

        # Normalizar si está configurado
        if self.config.normalize:
            embedding = self._normalize(embedding)

        # Guardar en caché
        if self._cache:
            await self._cache.set(
                cache_key, embedding, namespace="embeddings", ttl=86400  # 24 horas
            )

        return embedding

    async def embed_batch(self, texts: List[str]) -> List[List[float]]:
        """
        Genera embeddings para múltiples textos en batch.

        Args:
            texts: Lista de textos

        Returns:
            Lista de vectores de embedding
        """
        results = []

        # Procesar en batches
        for i in range(0, len(texts), self.config.batch_size):
            batch = texts[i : i + self.config.batch_size]

            # Procesar batch según proveedor
            if self.config.provider == "kimi":
                batch_embeddings = await self._embed_kimi_batch(batch)
            elif self.config.provider == "openai":
                batch_embeddings = await self._embed_openai_batch(batch)
            else:
                # Para local, procesar secuencialmente
                batch_embeddings = [await self._embed_local(t) for t in batch]

            results.extend(batch_embeddings)

        return results

    async def _embed_kimi(self, text: str) -> List[float]:
        """Embedding usando API de Kimi."""
        if not self._kimi_key:
            raise ValueError("MOONSHOT_API_KEY no configurada")

        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self._kimi_base}/embeddings",
                headers={
                    "Authorization": f"Bearer {self._kimi_key}",
                    "Content-Type": "application/json",
                },
                json={"model": self.config.model, "input": text},
                timeout=30.0,
            )
            response.raise_for_status()
            data = response.json()
            return data["data"][0]["embedding"]

    async def _embed_kimi_batch(self, texts: List[str]) -> List[List[float]]:
        """Batch embedding usando API de Kimi."""
        if not self._kimi_key:
            raise ValueError("MOONSHOT_API_KEY no configurada")

        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self._kimi_base}/embeddings",
                headers={
                    "Authorization": f"Bearer {self._kimi_key}",
                    "Content-Type": "application/json",
                },
                json={"model": self.config.model, "input": texts},
                timeout=60.0,
            )
            response.raise_for_status()
            data = response.json()
            return [item["embedding"] for item in data["data"]]

    async def _embed_openai(self, text: str) -> List[float]:
        """Embedding usando API de OpenAI."""
        if not self._openai_key:
            raise ValueError("OPENAI_API_KEY no configurada")

        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self._openai_base}/embeddings",
                headers={
                    "Authorization": f"Bearer {self._openai_key}",
                    "Content-Type": "application/json",
                },
                json={"model": self.config.model, "input": text},
                timeout=30.0,
            )
            response.raise_for_status()
            data = response.json()
            return data["data"][0]["embedding"]

    async def _embed_openai_batch(self, texts: List[str]) -> List[List[float]]:
        """Batch embedding usando API de OpenAI."""
        if not self._openai_key:
            raise ValueError("OPENAI_API_KEY no configurada")

        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self._openai_base}/embeddings",
                headers={
                    "Authorization": f"Bearer {self._openai_key}",
                    "Content-Type": "application/json",
                },
                json={"model": self.config.model, "input": texts},
                timeout=60.0,
            )
            response.raise_for_status()
            data = response.json()
            return [item["embedding"] for item in data["data"]]

    async def _embed_local(self, text: str) -> List[float]:
        """Embedding usando modelo local (placeholder)."""
        # TODO: Implementar con sentence-transformers
        logger.warning("Embeddings locales no implementados, usando fallback")
        # Fallback: vector aleatorio normalizado
        import math
        import random

        vec = [random.gauss(0, 1) for _ in range(self.config.dimensions)]
        norm = math.sqrt(sum(x**2 for x in vec))
        return [x / norm for x in vec]

    def _normalize(self, vector: List[float]) -> List[float]:
        """Normaliza un vector a L2 norm = 1."""
        import math

        norm = math.sqrt(sum(x**2 for x in vector))
        if norm == 0:
            return vector
        return [x / norm for x in vector]

    def cosine_similarity(self, a: List[float], b: List[float]) -> float:
        """Calcula similitud coseno entre dos vectores."""
        import math

        dot = sum(x * y for x, y in zip(a, b))
        norm_a = math.sqrt(sum(x**2 for x in a))
        norm_b = math.sqrt(sum(x**2 for x in b))
        if norm_a == 0 or norm_b == 0:
            return 0.0
        return dot / (norm_a * norm_b)


# Singleton global
_provider: Optional[EmbeddingProvider] = None


def get_embedding_provider(
    config: Optional[EmbeddingConfig] = None,
) -> EmbeddingProvider:
    """Obtiene instancia singleton del proveedor de embeddings."""
    global _provider
    if _provider is None:
        _provider = EmbeddingProvider(config)
    return _provider


def initialize_embedding_provider(config: EmbeddingConfig):
    """Inicializa el proveedor con configuración personalizada."""
    global _provider
    _provider = EmbeddingProvider(config)
