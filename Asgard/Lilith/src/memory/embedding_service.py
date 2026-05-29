"""
Lilith Vector Memory - Embedding Service
Generates embeddings using Ollama for ChromaDB integration
"""

import logging
from typing import Any, Dict, List, Optional

import numpy as np
import requests

logger = logging.getLogger("EmbeddingService")


class EmbeddingService:
    """
    Service for generating text embeddings using Ollama.
    Uses nomic-embed-text model as recommended.
    """

    def __init__(self, ollama_host: str = "http://localhost:11434"):
        self.ollama_host = ollama_host
        self.model = "nomic-embed-text:latest"  # Recommended by Ainz
        self.dimension = 768  # Output dimension for nomic-embed-text

        # Test connection on init
        self._test_connection()

    def _test_connection(self):
        """Test Ollama connection and model availability"""
        try:
            response = requests.get(f"{self.ollama_host}/api/tags", timeout=5)
            if response.status_code == 200:
                models = response.json().get("models", [])
                available_models = [m["name"] for m in models]

                if self.model not in available_models:
                    logger.warning(
                        f"Model {self.model} not found. Available: {available_models}"
                    )
                    logger.warning(f"Run: ollama pull {self.model}")
                else:
                    logger.info(f"Embedding service ready with model: {self.model}")
            else:
                logger.warning(f"Ollama not accessible at {self.ollama_host}")
        except Exception as e:
            logger.error(f"Error testing Ollama connection: {e}")

    def generate_embedding(self, text: str) -> Optional[List[float]]:
        """
        Generate embedding for a single text string.

        Args:
            text: Text to embed

        Returns:
            List of floats (embedding vector) or None if failed
        """
        try:
            response = requests.post(
                f"{self.ollama_host}/api/embeddings",
                json={"model": self.model, "prompt": text},
                timeout=30,
            )

            if response.status_code == 200:
                embedding = response.json().get("embedding", [])
                logger.debug(f"Generated embedding: {len(embedding)} dimensions")
                return embedding
            else:
                logger.error(f"Embedding API error: {response.status_code}")
                return None

        except Exception as e:
            logger.error(f"Error generating embedding: {e}")
            return None

    def generate_embeddings_batch(
        self, texts: List[str]
    ) -> List[Optional[List[float]]]:
        """
        Generate embeddings for multiple texts in batch.

        Args:
            texts: List of texts to embed

        Returns:
            List of embeddings (in same order as input)
        """
        embeddings = []

        for i, text in enumerate(texts):
            logger.debug(f"Processing batch {i+1}/{len(texts)}")
            embedding = self.generate_embedding(text)
            embeddings.append(embedding)

        return embeddings

    def get_similarity(self, embedding1: List[float], embedding2: List[float]) -> float:
        """
        Calculate cosine similarity between two embeddings.

        Args:
            embedding1: First embedding vector
            embedding2: Second embedding vector

        Returns:
            Cosine similarity score (0-1)
        """
        if not embedding1 or not embedding2:
            return 0.0

        try:
            vec1 = np.array(embedding1)
            vec2 = np.array(embedding2)

            # Normalize vectors
            vec1_norm = vec1 / np.linalg.norm(vec1)
            vec2_norm = vec2 / np.linalg.norm(vec2)

            # Cosine similarity
            similarity = np.dot(vec1_norm, vec2_norm)
            return float(similarity)

        except Exception as e:
            logger.error(f"Error calculating similarity: {e}")
            return 0.0


# ============================================================================
# TEST USAGE
# ============================================================================

if __name__ == "__main__":
    import sys

    print("Testing EmbeddingService...")
    print("=" * 60)

    service = EmbeddingService()

    # Test single embedding
    test_text = "Lilith is an AI assistant for code and system operations"
    embedding = service.generate_embedding(test_text)

    if embedding:
        print(f"[OK] Generated embedding: {len(embedding)} dimensions")
        print(f"[OK] Sample (first 5 values): {embedding[:5]}")

        # Test similarity
        test_text2 = "Lilith helps with programming and system tasks"
        embedding2 = service.generate_embedding(test_text2)

        if embedding2:
            similarity = service.get_similarity(embedding, embedding2)
            print(f"[OK] Similarity score: {similarity:.3f}")
            print(f"[OK] Texts are semantically similar: {similarity > 0.7}")

        # Test batch
        print("\nTesting batch generation...")
        batch_texts = [
            "Planning engine with Chain-of-Thought",
            "Tool registry for unified management",
            "CodeAnalyzer with AST parsing",
        ]

        batch_embeddings = service.generate_embeddings_batch(batch_texts)
        print(f"[OK] Batch completed: {len(batch_embeddings)} embeddings")

        successful = sum(1 for emb in batch_embeddings if emb is not None)
        print(f"[OK] Successful: {successful}/{len(batch_embeddings)}")

        if successful == len(batch_embeddings):
            print("\n" + "=" * 60)
            print("TODAS LAS PRUEBAS PASARON!")
            print("EmbeddingService is functional")
            sys.exit(0)
        else:
            print("\n[FAIL] Some embeddings failed")
            sys.exit(1)
    else:
        print("[FAIL] Could not generate embedding")
        sys.exit(1)
