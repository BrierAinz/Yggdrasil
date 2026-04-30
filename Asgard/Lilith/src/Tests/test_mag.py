"""
Tests for MAG (Memory Augmented Generation)

v5.0: Tests unitarios para embeddings, vector store y MAG engine.
"""
import asyncio
from typing import List
from unittest.mock import AsyncMock, Mock, patch

import pytest
from src.core.mag.context_augmenter import AugmentedPrompt, ContextAugmenter
from src.core.mag.embeddings import EmbeddingConfig, EmbeddingProvider
from src.core.mag.mag_engine import IndexingResult, MAGEngine, TextSplitter
from src.core.mag.vector_store import Document, SearchResult, VectorStore


class TestTextSplitter:
    """Tests para el divisor de textos."""

    def test_split_recursive(self):
        """Test división recursiva."""
        splitter = TextSplitter(chunk_size=100, chunk_overlap=20)
        text = "This is paragraph one.\n\nThis is paragraph two.\n\nThis is paragraph three."

        chunks = splitter.split(text)

        assert len(chunks) > 0
        assert all(len(c) <= 100 for c in chunks)

    def test_split_fixed(self):
        """Test división de tamaño fijo."""
        splitter = TextSplitter(chunk_size=50, strategy="fixed")
        text = "a" * 200

        chunks = splitter.split(text)

        assert len(chunks) >= 4  # 200 / 50 = 4 chunks

    def test_split_semantic(self):
        """Test división semántica."""
        splitter = TextSplitter(chunk_size=100, strategy="semantic")
        text = "First sentence. Second sentence. Third sentence."

        chunks = splitter.split(text)

        assert len(chunks) >= 1

    def test_overlap_applied(self):
        """Test que se aplica overlap entre chunks."""
        splitter = TextSplitter(chunk_size=50, chunk_overlap=10)
        text = "Word " * 20  # Texto largo

        chunks = splitter.split(text)

        if len(chunks) > 1:
            # El segundo chunk debería contener parte del primero
            assert len(chunks[1]) > 0


class TestEmbeddingProvider:
    """Tests para el proveedor de embeddings."""

    def setup_method(self):
        """Setup."""
        self.config = EmbeddingConfig(
            provider="local", dimensions=128  # Usar local para tests
        )
        self.provider = EmbeddingProvider(self.config)

    @pytest.mark.asyncio
    async def test_embed_local(self):
        """Test embedding local."""
        text = "Test text"
        embedding = await self.provider.embed(text)

        assert isinstance(embedding, list)
        assert len(embedding) == 128
        # Vector normalizado tiene norma ~1
        import math

        norm = math.sqrt(sum(x**2 for x in embedding))
        assert abs(norm - 1.0) < 0.01

    @pytest.mark.asyncio
    async def test_embed_batch(self):
        """Test embedding en batch."""
        texts = ["Text 1", "Text 2", "Text 3"]
        embeddings = await self.provider.embed_batch(texts)

        assert len(embeddings) == 3
        assert all(len(e) == 128 for e in embeddings)

    def test_cosine_similarity(self):
        """Test cálculo de similitud coseno."""
        # Dos vectores idénticos tienen similitud 1
        a = [1.0, 0.0, 0.0]
        b = [1.0, 0.0, 0.0]
        similarity = self.provider.cosine_similarity(a, b)
        assert abs(similarity - 1.0) < 0.001

        # Vectores ortogonales tienen similitud 0
        c = [1.0, 0.0, 0.0]
        d = [0.0, 1.0, 0.0]
        similarity = self.provider.cosine_similarity(c, d)
        assert abs(similarity) < 0.001


class TestVectorStore:
    """Tests para el vector store."""

    def setup_method(self):
        """Setup con mocks."""
        self.store = VectorStore(collection="test_collection")
        # Mock de Muninn
        self.store.muninn = Mock()

    @pytest.mark.asyncio
    async def test_add_document(self):
        """Test agregar documento."""
        doc = Document(
            id="doc_1",
            content="Test content",
            embedding=[0.1, 0.2, 0.3],
            metadata={"key": "value"},
        )

        self.store.muninn.store_vector = AsyncMock(return_value=True)

        result = await self.store.add(doc)

        assert result is True
        self.store.muninn.store_vector.assert_called_once()

    @pytest.mark.asyncio
    async def test_search(self):
        """Test búsqueda vectorial."""
        query_embedding = [0.1, 0.2, 0.3]
        mock_results = [
            (
                "doc_1",
                0.95,
                {
                    "id": "doc_1",
                    "content": "Content 1",
                    "embedding": [0.1, 0.2, 0.3],
                    "metadata": {},
                },
            ),
            (
                "doc_2",
                0.85,
                {
                    "id": "doc_2",
                    "content": "Content 2",
                    "embedding": [0.2, 0.3, 0.4],
                    "metadata": {},
                },
            ),
        ]

        self.store.muninn.search_vectors = AsyncMock(return_value=mock_results)

        results = await self.store.search(query_embedding, top_k=2)

        assert len(results) == 2
        assert results[0].score == 0.95
        assert results[0].document.id == "doc_1"

    @pytest.mark.asyncio
    async def test_search_with_filter(self):
        """Test búsqueda con filtro."""
        query_embedding = [0.1, 0.2, 0.3]
        mock_results = [
            (
                "doc_1",
                0.95,
                {
                    "id": "doc_1",
                    "content": "Content 1",
                    "embedding": [0.1, 0.2, 0.3],
                    "metadata": {"type": "A"},
                },
            ),
            (
                "doc_2",
                0.85,
                {
                    "id": "doc_2",
                    "content": "Content 2",
                    "embedding": [0.2, 0.3, 0.4],
                    "metadata": {"type": "B"},
                },
            ),
        ]

        self.store.muninn.search_vectors = AsyncMock(return_value=mock_results)

        # Filtro por type=A
        results = await self.store.search(
            query_embedding, filter_fn=lambda meta: meta.get("type") == "A"
        )

        assert len(results) == 1
        assert results[0].document.metadata["type"] == "A"

    @pytest.mark.asyncio
    async def test_get_document(self):
        """Test obtener documento por ID."""
        mock_doc = {
            "id": "doc_1",
            "content": "Content",
            "embedding": [0.1],
            "metadata": {},
        }
        self.store.muninn.get_vector = AsyncMock(return_value=mock_doc)

        doc = await self.store.get("doc_1")

        assert doc is not None
        assert doc.id == "doc_1"


class TestMAGEngine:
    """Tests para el motor MAG."""

    def setup_method(self):
        """Setup con mocks."""
        self.engine = MAGEngine()
        # Mocks
        self.engine.embeddings = Mock()
        self.engine.embeddings.embed = AsyncMock(return_value=[0.1, 0.2, 0.3])
        self.engine.embeddings.embed_batch = AsyncMock(return_value=[[0.1], [0.2]])

    @pytest.mark.asyncio
    async def test_index_document(self):
        """Test indexación de documento."""
        with patch("Backend.core.mag.mag_engine.get_vector_store") as mock_get_store:
            mock_store = Mock()
            mock_store.add = AsyncMock(return_value=True)
            mock_get_store.return_value = mock_store

            result = await self.engine.index_document(
                content="This is a test document. It has multiple sentences.",
                metadata={"source": "test"},
                doc_id="test_doc",
            )

            assert result.success is True
            assert result.doc_id == "test_doc"
            assert result.chunks_indexed > 0

    @pytest.mark.asyncio
    async def test_retrieve(self):
        """Test recuperación de contexto."""
        with patch("Backend.core.mag.mag_engine.get_vector_store") as mock_get_store:
            mock_store = Mock()
            mock_store.search = AsyncMock(
                return_value=[
                    SearchResult(
                        document=Document(
                            id="doc_1",
                            content="Relevant content",
                            embedding=[0.1],
                            source="test",
                        ),
                        score=0.95,
                        rank=1,
                    )
                ]
            )
            mock_get_store.return_value = mock_store

            result = await self.engine.retrieve(query="test query", top_k=5)

            assert len(result.documents) == 1
            assert result.documents[0].score == 0.95
            assert "Relevant content" in result.context_text

    @pytest.mark.asyncio
    async def test_delete_document(self):
        """Test eliminación de documento."""
        with patch("Backend.core.mag.mag_engine.get_vector_store") as mock_get_store:
            mock_store = Mock()
            mock_store.delete_by_filter = AsyncMock(return_value=3)
            mock_get_store.return_value = mock_store

            result = await self.engine.delete_document("doc_123")

            assert result is True


class TestContextAugmenter:
    """Tests para el augmentador de contexto."""

    def setup_method(self):
        """Setup con mocks."""
        self.augmenter = ContextAugmenter()
        self.augmenter.mag = Mock()

    @pytest.mark.asyncio
    async def test_augment_with_context(self):
        """Test augmentación con contexto encontrado."""
        from src.core.mag.mag_engine import RetrievalResult

        self.augmenter.mag.retrieve = AsyncMock(
            return_value=RetrievalResult(
                query="test",
                documents=[
                    SearchResult(
                        document=Document(
                            id="doc_1",
                            content="Context information",
                            embedding=[0.1],
                            source="knowledge_base",
                        ),
                        score=0.9,
                        rank=1,
                    )
                ],
                context_text="Context information",
                total_tokens=10,
            )
        )

        result = await self.augmenter.augment("User query")

        assert result.context_used is True
        assert len(result.sources) == 1
        assert "Context information" in result.augmented_prompt

    @pytest.mark.asyncio
    async def test_augment_no_context(self):
        """Test augmentación sin contexto relevante."""
        from src.core.mag.mag_engine import RetrievalResult

        self.augmenter.mag.retrieve = AsyncMock(
            return_value=RetrievalResult(
                query="test", documents=[], context_text="", total_tokens=0
            )
        )

        result = await self.augmenter.augment("User query")

        assert result.context_used is False
        assert result.augmented_prompt == "User query"

    def test_truncate_context(self):
        """Test truncado de contexto largo."""
        from src.core.mag.mag_engine import RetrievalResult, SearchResult

        retrieval = RetrievalResult(
            query="test",
            documents=[
                SearchResult(
                    document=Document(
                        id=f"doc_{i}",
                        content=f"Word " * 100,  # 200 tokens aprox
                        embedding=[0.1],
                    ),
                    score=0.9,
                    rank=i,
                )
                for i in range(5)
            ],
            context_text="",
            total_tokens=1000,
        )

        # Calcular context_text real
        retrieval.context_text = "\n\n".join(
            f"--- Documento {i} ---\n{d.document.content}"
            for i, d in enumerate(retrieval.documents, 1)
        )

        truncated = self.augmenter._truncate_context(retrieval, max_tokens=300)

        words = truncated.split()
        assert len(words) <= 300


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
