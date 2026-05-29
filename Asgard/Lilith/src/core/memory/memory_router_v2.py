"""
Memory Router con aislamiento por transporte

Separa memoria por fuente:
- discord_public: Crystal y canales públicos
- discord_owner: Lilith en DM con owner
- telegram: Operaciones de PC y control remoto

Evita contaminación cruzada.
"""

import logging
from enum import Enum
from typing import Any, Dict, List, Optional, Set

logger = logging.getLogger(__name__)


class MemorySource(str, Enum):
    """Fuentes de memoria para aislamiento"""

    DISCORD_PUBLIC = "discord_public"
    DISCORD_OWNER = "discord_owner"
    TELEGRAM = "telegram"
    INTERNAL = "internal"


class MemoryRouter:
    """
    Router de memoria con aislamiento por transporte

    Garantiza que:
    - Crystal solo ve discord_public
    - Telegram solo ve telegram + internal
    - Owner ve todo excepto restricciones explícitas
    """

    def __init__(self):
        # Tags por fuente
        self.source_tags: Dict[MemorySource, Set[str]] = {
            MemorySource.DISCORD_PUBLIC: {"discord", "public", "crystal"},
            MemorySource.DISCORD_OWNER: {"discord", "owner", "private"},
            MemorySource.TELEGRAM: {"telegram", "pc_ops", "operator"},
            MemorySource.INTERNAL: {"internal", "system"},
        }

        # Exclusiones: qué NO puede ver cada fuente
        self.exclusions: Dict[MemorySource, Set[str]] = {
            MemorySource.DISCORD_PUBLIC: {
                "telegram",
                "pc_ops",
                "owner",
                "sensitive",
                "internal",
                "private",
            },
            MemorySource.DISCORD_OWNER: set(),  # Owner ve todo
            MemorySource.TELEGRAM: {"discord", "public", "crystal"},
            MemorySource.INTERNAL: set(),
        }

    def write_memory(
        self,
        content: str,
        source: MemorySource,
        memory_store,  # SemanticStore o VectorStore
        metadata: Optional[Dict[str, Any]] = None,
    ) -> bool:
        """
        Escribir a memoria con tags apropiados por fuente

        Args:
            content: Contenido a guardar
            source: Fuente (discord_public, telegram, etc.)
            memory_store: Store de memoria
            metadata: Metadata adicional

        Returns:
            True si exitoso
        """
        # Agregar tags de fuente
        tags = list(self.source_tags[source])

        if metadata is None:
            metadata = {}

        # Merge tags existentes
        existing_tags = metadata.get("tags", [])
        metadata["tags"] = list(set(tags + existing_tags))

        # Agregar source
        metadata["source"] = source.value

        try:
            memory_store.store(content=content, metadata=metadata)
            logger.debug(
                f"Wrote memory with source={source.value}, tags={metadata['tags']}"
            )
            return True

        except Exception as e:
            logger.error(f"Failed to write memory: {e}")
            return False

    def search_memory(
        self, query: str, source: MemorySource, memory_store, max_results: int = 10
    ) -> List[Dict[str, Any]]:
        """
        Buscar en memoria con filtrado por fuente

        Args:
            query: Query de búsqueda
            source: Fuente que busca
            memory_store: Store de memoria
            max_results: Máximo de resultados

        Returns:
            Lista de hechos filtrados
        """
        try:
            # Buscar sin filtro primero
            results = memory_store.search(query=query, max_results=max_results * 2)

            # Filtrar por exclusiones
            filtered = self._filter_by_source(results, source)

            return filtered[:max_results]

        except Exception as e:
            logger.error(f"Memory search failed: {e}")
            return []

    def _filter_by_source(
        self, results: List[Dict[str, Any]], source: MemorySource
    ) -> List[Dict[str, Any]]:
        """
        Filtrar resultados según exclusiones de la fuente

        Args:
            results: Resultados crudos
            source: Fuente que busca

        Returns:
            Resultados filtrados
        """
        excluded_tags = self.exclusions[source]

        if not excluded_tags:
            return results  # Owner ve todo

        filtered = []

        for result in results:
            tags = set(result.get("metadata", {}).get("tags", []))

            # Excluir si tiene algún tag prohibido
            if tags & excluded_tags:
                continue

            filtered.append(result)

        return filtered

    def get_allowed_tags(self, source: MemorySource) -> List[str]:
        """Obtener tags permitidos para una fuente"""
        return list(self.source_tags[source])

    def get_excluded_tags(self, source: MemorySource) -> List[str]:
        """Obtener tags excluidos para una fuente"""
        return list(self.exclusions[source])


# Singleton global
_memory_router: Optional[MemoryRouter] = None


def get_memory_router() -> MemoryRouter:
    """Obtener instancia singleton del router de memoria"""
    global _memory_router
    if _memory_router is None:
        _memory_router = MemoryRouter()
    return _memory_router
