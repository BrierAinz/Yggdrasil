"""
Vector Store - Almacenamiento y búsqueda de vectores

v5.0: Vector store basado en MuninnDB con índice HNSW para búsqueda eficiente.
Soporta: add, search, delete, y filtrado por metadata.
"""
import json
import logging
import secrets
from dataclasses import asdict, dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

from src.core.muninn import get_muninn

logger = logging.getLogger("lilith.mag.vector_store")


@dataclass
class Document:
    """Documento con embedding vectorial."""

    id: str
    content: str
    embedding: List[float]
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    updated_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    source: str = ""  # Origen del documento (archivo, url, etc.)
    chunk_index: int = 0  # Índice del chunk si es parte de un documento grande
    total_chunks: int = 1

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "content": self.content,
            "embedding": self.embedding,
            "metadata": self.metadata,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "source": self.source,
            "chunk_index": self.chunk_index,
            "total_chunks": self.total_chunks,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Document":
        return cls(
            id=data["id"],
            content=data["content"],
            embedding=data["embedding"],
            metadata=data.get("metadata", {}),
            created_at=data.get("created_at", datetime.utcnow().isoformat()),
            updated_at=data.get("updated_at", datetime.utcnow().isoformat()),
            source=data.get("source", ""),
            chunk_index=data.get("chunk_index", 0),
            total_chunks=data.get("total_chunks", 1),
        )


@dataclass
class SearchResult:
    """Resultado de búsqueda vectorial."""

    document: Document
    score: float  # Similitud coseno (0-1)
    rank: int


class VectorStore:
    """
    Almacenamiento de vectores con búsqueda por similitud.

    Features:
    - Almacenamiento en MuninnDB
    - Búsqueda por similitud coseno
    - Filtrado por metadata
    - Indexación por colecciones
    """

    def __init__(self, collection: str = "default"):
        self.collection = collection
        self.muninn = get_muninn()
        self._dimension: Optional[int] = None

    async def add(self, document: Document) -> bool:
        """
        Añade un documento al vector store.

        Args:
            document: Documento con embedding

        Returns:
            True si se añadió exitosamente
        """
        try:
            # Almacenar en MuninnDB
            await self.muninn.store_vector(
                collection=self.collection,
                doc_id=document.id,
                vector=document.embedding,
                payload=document.to_dict(),
            )

            logger.debug(f"Documento {document.id} añadido a {self.collection}")
            return True

        except Exception as e:
            logger.error(f"Error añadiendo documento: {e}")
            return False

    async def add_batch(self, documents: List[Document]) -> int:
        """
        Añade múltiples documentos en batch.

        Args:
            documents: Lista de documentos

        Returns:
            Número de documentos añadidos
        """
        count = 0
        for doc in documents:
            if await self.add(doc):
                count += 1
        return count

    async def search(
        self,
        query_embedding: List[float],
        top_k: int = 5,
        min_score: float = 0.0,
        filter_fn: Optional[Callable[[Dict], bool]] = None,
    ) -> List[SearchResult]:
        """
        Busca documentos similares a un embedding.

        Args:
            query_embedding: Vector de consulta
            top_k: Número máximo de resultados
            min_score: Score mínimo (0-1)
            filter_fn: Función de filtrado por metadata

        Returns:
            Lista de resultados ordenados por relevancia
        """
        try:
            # Buscar en MuninnDB
            results = await self.muninn.search_vectors(
                collection=self.collection,
                query_vector=query_embedding,
                top_k=top_k * 2,  # Pedir más para aplicar filtros
            )

            search_results = []
            for idx, (doc_id, score, payload) in enumerate(results):
                # Aplicar filtro si existe
                if filter_fn and not filter_fn(payload.get("metadata", {})):
                    continue

                # Verificar score mínimo
                if score < min_score:
                    continue

                doc = Document.from_dict(payload)
                search_results.append(
                    SearchResult(
                        document=doc, score=score, rank=len(search_results) + 1
                    )
                )

                if len(search_results) >= top_k:
                    break

            return search_results

        except Exception as e:
            logger.error(f"Error en búsqueda vectorial: {e}")
            return []

    async def search_similar(self, doc_id: str, top_k: int = 5) -> List[SearchResult]:
        """
        Busca documentos similares a uno existente.

        Args:
            doc_id: ID del documento de referencia
            top_k: Número de resultados

        Returns:
            Lista de documentos similares
        """
        # Obtener documento
        doc = await self.get(doc_id)
        if not doc:
            return []

        # Buscar similares (excluyendo el mismo)
        results = await self.search(doc.embedding, top_k=top_k + 1)
        return [r for r in results if r.document.id != doc_id][:top_k]

    async def get(self, doc_id: str) -> Optional[Document]:
        """
        Obtiene un documento por ID.

        Args:
            doc_id: ID del documento

        Returns:
            Documento o None
        """
        try:
            result = await self.muninn.get_vector(
                collection=self.collection, doc_id=doc_id
            )
            if result:
                return Document.from_dict(result)
            return None
        except Exception as e:
            logger.error(f"Error obteniendo documento: {e}")
            return None

    async def delete(self, doc_id: str) -> bool:
        """
        Elimina un documento.

        Args:
            doc_id: ID del documento

        Returns:
            True si se eliminó
        """
        try:
            await self.muninn.delete_vector(collection=self.collection, doc_id=doc_id)
            return True
        except Exception as e:
            logger.error(f"Error eliminando documento: {e}")
            return False

    async def delete_by_filter(self, filter_fn: Callable[[Dict], bool]) -> int:
        """
        Elimina documentos que cumplan un criterio.

        Args:
            filter_fn: Función de filtrado

        Returns:
            Número de documentos eliminados
        """
        # Obtener todos los documentos y filtrar
        # Nota: Esto es ineficiente para grandes volúmenes
        count = 0
        try:
            all_docs = await self.muninn.get_all_vectors(self.collection)
            for doc_data in all_docs:
                if filter_fn(doc_data.get("metadata", {})):
                    if await self.delete(doc_data["id"]):
                        count += 1
            return count
        except Exception as e:
            logger.error(f"Error en delete_by_filter: {e}")
            return count

    async def update(self, doc_id: str, **kwargs) -> bool:
        """
        Actualiza un documento.

        Args:
            doc_id: ID del documento
            **kwargs: Campos a actualizar

        Returns:
            True si se actualizó
        """
        doc = await self.get(doc_id)
        if not doc:
            return False

        # Actualizar campos permitidos
        allowed = {"content", "embedding", "metadata", "source"}
        for key, value in kwargs.items():
            if key in allowed:
                setattr(doc, key, value)

        doc.updated_at = datetime.utcnow().isoformat()

        # Re-indexar
        return await self.add(doc)

    async def count(self) -> int:
        """
        Obtiene el número de documentos en la colección.

        Returns:
            Conteo de documentos
        """
        try:
            return await self.muninn.count_vectors(self.collection)
        except Exception as e:
            logger.error(f"Error contando documentos: {e}")
            return 0

    async def clear(self) -> bool:
        """
        Limpia todos los documentos de la colección.

        Returns:
            True si se limpió
        """
        try:
            await self.muninn.clear_collection(self.collection)
            return True
        except Exception as e:
            logger.error(f"Error limpiando colección: {e}")
            return False

    async def get_stats(self) -> Dict[str, Any]:
        """
        Obtiene estadísticas de la colección.

        Returns:
            Diccionario con estadísticas
        """
        count = await self.count()

        # Calcular estadísticas de embeddings si hay documentos
        if count > 0:
            try:
                sample = await self.muninn.get_sample_vectors(
                    self.collection, limit=100
                )
                dimensions = len(sample[0]["embedding"]) if sample else 0
            except:
                dimensions = 0
        else:
            dimensions = 0

        return {
            "collection": self.collection,
            "document_count": count,
            "dimensions": dimensions,
            "status": "active" if count > 0 else "empty",
        }


# Cache de stores por colección
_store_cache: Dict[str, VectorStore] = {}


def get_vector_store(collection: str = "default") -> VectorStore:
    """
    Obtiene instancia de VectorStore para una colección.

    Args:
        collection: Nombre de la colección

    Returns:
        VectorStore
    """
    if collection not in _store_cache:
        _store_cache[collection] = VectorStore(collection)
    return _store_cache[collection]
