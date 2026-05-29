"""
MAG Engine - Motor de Memory Augmented Generation

v5.0: Orquesta embeddings, vector store y procesamiento de documentos.
Proporciona una API de alto nivel para indexar y buscar conocimiento.
"""
import asyncio
import logging
import secrets
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, AsyncIterator, Callable, Dict, List, Optional

from .embeddings import EmbeddingConfig, EmbeddingProvider, get_embedding_provider
from .vector_store import Document, SearchResult, VectorStore, get_vector_store

logger = logging.getLogger("lilith.mag.engine")


@dataclass
class IndexingResult:
    """Resultado de indexación de documento."""

    doc_id: str
    chunks_indexed: int
    success: bool
    error: Optional[str] = None


@dataclass
class RetrievalResult:
    """Resultado de recuperación de contexto."""

    query: str
    documents: List[SearchResult]
    context_text: str
    total_tokens: int


class TextSplitter:
    """
    Divide textos en chunks para indexación.

    Estrategias:
    - recursive: División recursiva por separadores
    - fixed: Chunks de tamaño fijo
    - semantic: División por oraciones/párrafos
    """

    def __init__(
        self,
        chunk_size: int = 1000,
        chunk_overlap: int = 200,
        strategy: str = "recursive",
    ):
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.strategy = strategy

    def split(self, text: str) -> List[str]:
        """Divide texto en chunks."""
        if self.strategy == "recursive":
            return self._split_recursive(text)
        elif self.strategy == "fixed":
            return self._split_fixed(text)
        elif self.strategy == "semantic":
            return self._split_semantic(text)
        else:
            return self._split_recursive(text)

    def _split_recursive(self, text: str) -> List[str]:
        """División recursiva por separadores."""
        separators = ["\n\n", "\n", ". ", " ", ""]
        return self._split_recursive_helper(text, separators)

    def _split_recursive_helper(self, text: str, separators: List[str]) -> List[str]:
        """Helper recursivo para división."""
        if not text:
            return []

        if len(text) <= self.chunk_size:
            return [text]

        if not separators:
            return [text[: self.chunk_size]]

        separator = separators[0]
        parts = text.split(separator)

        chunks = []
        current_chunk = ""

        for part in parts:
            if len(current_chunk) + len(part) + len(separator) <= self.chunk_size:
                current_chunk += part + separator
            else:
                if current_chunk:
                    chunks.append(current_chunk.strip())
                # Si la parte es muy grande, dividir recursivamente
                if len(part) > self.chunk_size:
                    sub_chunks = self._split_recursive_helper(part, separators[1:])
                    chunks.extend(sub_chunks)
                else:
                    current_chunk = part + separator

        if current_chunk:
            chunks.append(current_chunk.strip())

        # Aplicar overlap
        return self._apply_overlap(chunks)

    def _split_fixed(self, text: str) -> List[str]:
        """División en chunks de tamaño fijo."""
        chunks = []
        for i in range(0, len(text), self.chunk_size - self.chunk_overlap):
            chunk = text[i : i + self.chunk_size]
            if chunk:
                chunks.append(chunk)
        return chunks

    def _split_semantic(self, text: str) -> List[str]:
        """División por oraciones/párrafos."""
        import re

        # Dividir por oraciones
        sentences = re.split(r"(?<=[.!?])\s+", text)

        chunks = []
        current_chunk = ""

        for sentence in sentences:
            if len(current_chunk) + len(sentence) <= self.chunk_size:
                current_chunk += sentence + " "
            else:
                if current_chunk:
                    chunks.append(current_chunk.strip())
                current_chunk = sentence + " "

        if current_chunk:
            chunks.append(current_chunk.strip())

        return chunks

    def _apply_overlap(self, chunks: List[str]) -> List[str]:
        """Aplica overlap entre chunks."""
        if len(chunks) <= 1 or self.chunk_overlap <= 0:
            return chunks

        result = [chunks[0]]
        for i in range(1, len(chunks)):
            prev_chunk = chunks[i - 1]
            current_chunk = chunks[i]

            # Calcular overlap
            overlap_text = prev_chunk[-self.chunk_overlap :]
            result.append(overlap_text + current_chunk)

        return result


class MAGEngine:
    """
    Motor de Memory Augmented Generation.

    Features:
    - Indexación de documentos con chunking automático
    - Búsqueda semántica de contexto relevante
    - Integración con múltiples colecciones
    - Streaming de resultados
    """

    def __init__(
        self,
        embedding_provider: Optional[EmbeddingProvider] = None,
        text_splitter: Optional[TextSplitter] = None,
        default_collection: str = "knowledge",
    ):
        self.embeddings = embedding_provider or get_embedding_provider()
        self.splitter = text_splitter or TextSplitter()
        self.default_collection = default_collection

    async def index_document(
        self,
        content: str,
        metadata: Optional[Dict[str, Any]] = None,
        source: str = "",
        doc_id: Optional[str] = None,
        collection: Optional[str] = None,
    ) -> IndexingResult:
        """
        Indexa un documento en el vector store.

        Args:
            content: Contenido del documento
            metadata: Metadata adicional
            source: Origen del documento
            doc_id: ID opcional (si no se proporciona, se genera)
            collection: Colección destino

        Returns:
            Resultado de indexación
        """
        doc_id = doc_id or secrets.token_hex(8)
        collection = collection or self.default_collection

        try:
            # Dividir en chunks
            chunks = self.splitter.split(content)

            if not chunks:
                return IndexingResult(
                    doc_id=doc_id,
                    chunks_indexed=0,
                    success=False,
                    error="No se generaron chunks del documento",
                )

            # Generar embeddings para cada chunk
            embeddings = await self.embeddings.embed_batch(chunks)

            # Crear documentos y almacenar
            store = get_vector_store(collection)

            for idx, (chunk_text, embedding) in enumerate(zip(chunks, embeddings)):
                chunk_doc = Document(
                    id=f"{doc_id}_chunk_{idx}",
                    content=chunk_text,
                    embedding=embedding,
                    metadata={
                        **(metadata or {}),
                        "parent_doc_id": doc_id,
                        "chunk_index": idx,
                        "total_chunks": len(chunks),
                    },
                    source=source,
                    chunk_index=idx,
                    total_chunks=len(chunks),
                )

                await store.add(chunk_doc)

            logger.info(f"Documento {doc_id} indexado: {len(chunks)} chunks")

            return IndexingResult(
                doc_id=doc_id, chunks_indexed=len(chunks), success=True
            )

        except Exception as e:
            logger.error(f"Error indexando documento: {e}")
            return IndexingResult(
                doc_id=doc_id, chunks_indexed=0, success=False, error=str(e)
            )

    async def index_batch(
        self, documents: List[Dict[str, Any]], collection: Optional[str] = None
    ) -> List[IndexingResult]:
        """
        Indexa múltiples documentos.

        Args:
            documents: Lista de dicts con 'content', 'metadata', 'source'
            collection: Colección destino

        Returns:
            Lista de resultados
        """
        results = []
        for doc in documents:
            result = await self.index_document(
                content=doc["content"],
                metadata=doc.get("metadata"),
                source=doc.get("source", ""),
                collection=collection,
            )
            results.append(result)
        return results

    async def retrieve(
        self,
        query: str,
        top_k: int = 5,
        min_score: float = 0.7,
        collection: Optional[str] = None,
        filter_fn: Optional[Callable[[Dict], bool]] = None,
    ) -> RetrievalResult:
        """
        Recupera contexto relevante para una consulta.

        Args:
            query: Consulta del usuario
            top_k: Número de documentos a recuperar
            min_score: Score mínimo de similitud
            collection: Colección a buscar
            filter_fn: Filtro opcional por metadata

        Returns:
            Resultado de recuperación con contexto formateado
        """
        collection = collection or self.default_collection

        try:
            # Generar embedding de la consulta
            query_embedding = await self.embeddings.embed(query)

            # Buscar documentos similares
            store = get_vector_store(collection)
            results = await store.search(
                query_embedding=query_embedding,
                top_k=top_k,
                min_score=min_score,
                filter_fn=filter_fn,
            )

            # Formatear contexto
            context_parts = []
            for idx, result in enumerate(results, 1):
                source_info = (
                    f"[Fuente: {result.document.source}]"
                    if result.document.source
                    else ""
                )
                context_parts.append(
                    f"--- Documento {idx} {source_info} (relevancia: {result.score:.2f}) ---\n"
                    f"{result.document.content}\n"
                )

            context_text = "\n".join(context_parts)

            # Estimar tokens (aproximación simple)
            total_tokens = len(context_text.split())

            return RetrievalResult(
                query=query,
                documents=results,
                context_text=context_text,
                total_tokens=total_tokens,
            )

        except Exception as e:
            logger.error(f"Error en recuperación: {e}")
            return RetrievalResult(
                query=query, documents=[], context_text="", total_tokens=0
            )

    async def retrieve_stream(
        self, query: str, top_k: int = 5, collection: Optional[str] = None
    ) -> AsyncIterator[SearchResult]:
        """
        Recupera resultados en streaming.

        Args:
            query: Consulta
            top_k: Número de resultados
            collection: Colección

        Yields:
            SearchResult individual
        """
        collection = collection or self.default_collection

        query_embedding = await self.embeddings.embed(query)
        store = get_vector_store(collection)
        results = await store.search(query_embedding, top_k=top_k)

        for result in results:
            yield result

    async def delete_document(
        self, doc_id: str, collection: Optional[str] = None
    ) -> bool:
        """
        Elimina un documento y todos sus chunks.

        Args:
            doc_id: ID del documento padre
            collection: Colección

        Returns:
            True si se eliminó
        """
        collection = collection or self.default_collection
        store = get_vector_store(collection)

        try:
            # Buscar todos los chunks del documento
            # Esto requiere un índice por parent_doc_id
            # Por ahora, usamos delete_by_filter si está disponible
            deleted = await store.delete_by_filter(
                lambda meta: meta.get("parent_doc_id") == doc_id
            )
            return deleted > 0
        except Exception as e:
            logger.error(f"Error eliminando documento: {e}")
            return False

    async def get_stats(self, collection: Optional[str] = None) -> Dict[str, Any]:
        """
        Obtiene estadísticas del engine.

        Args:
            collection: Colección específica o None para todas

        Returns:
            Estadísticas
        """
        if collection:
            store = get_vector_store(collection)
            return await store.get_stats()

        # Stats de todas las colecciones
        # Esto requiere enumerar colecciones en MuninnDB
        return {
            "default_collection": self.default_collection,
            "chunk_size": self.splitter.chunk_size,
            "chunk_overlap": self.splitter.chunk_overlap,
        }


# Singleton global
_mag_engine: Optional[MAGEngine] = None


def get_mag_engine() -> MAGEngine:
    """Obtiene instancia singleton del MAG Engine."""
    global _mag_engine
    if _mag_engine is None:
        _mag_engine = MAGEngine()
    return _mag_engine


def initialize_mag_engine(
    embedding_config: Optional[EmbeddingConfig] = None,
    chunk_size: int = 1000,
    chunk_overlap: int = 200,
):
    """Inicializa el MAG Engine con configuración personalizada."""
    global _mag_engine

    provider = get_embedding_provider(embedding_config) if embedding_config else None
    splitter = TextSplitter(chunk_size=chunk_size, chunk_overlap=chunk_overlap)

    _mag_engine = MAGEngine(embedding_provider=provider, text_splitter=splitter)
