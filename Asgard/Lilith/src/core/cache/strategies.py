"""
Estrategias de Invalidación de Caché

Implementa diferentes políticas de expiración y eviction.
"""
import logging
import time
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional

from .manager import CacheEntry

logger = logging.getLogger("lilith.cache")


class CacheStrategy(ABC):
    """Estrategia abstracta de caché."""

    @abstractmethod
    def is_expired(self, entry: CacheEntry) -> bool:
        """Determina si una entrada expiró."""
        pass

    @abstractmethod
    def should_evict(
        self, entries: List[CacheEntry], new_entry: CacheEntry
    ) -> Optional[CacheEntry]:
        """Determina qué entrada evict (si alguna)."""
        pass


class TTLStrategy(CacheStrategy):
    """
    Estrategia Time-To-Live.

    Las entradas expiran después de un tiempo fijo.
    """

    def __init__(self, default_ttl: int = 300):
        """
        Args:
            default_ttl: TTL por defecto en segundos
        """
        self.default_ttl = default_ttl

    def is_expired(self, entry: CacheEntry) -> bool:
        """Verifica si la entrada expiró por TTL."""
        if entry.ttl is None:
            return False
        return time.time() - entry.created_at > entry.ttl

    def should_evict(
        self, entries: List[CacheEntry], new_entry: CacheEntry
    ) -> Optional[CacheEntry]:
        """
        Para TTL, evict entradas expiradas primero.
        """
        # Primero buscar entradas expiradas
        for entry in entries:
            if self.is_expired(entry):
                return entry
        return None

    def get_entry_ttl(self, custom_ttl: Optional[int] = None) -> Optional[int]:
        """Obtiene TTL efectivo para una entrada."""
        return custom_ttl if custom_ttl is not None else self.default_ttl


class LRUStrategy(CacheStrategy):
    """
    Estrategia Least Recently Used.

    Evict la entrada menos recientemente accedida.
    """

    def __init__(self, max_size: int = 1000):
        """
        Args:
            max_size: Número máximo de entradas
        """
        self.max_size = max_size

    def is_expired(self, entry: CacheEntry) -> bool:
        """LRU no expira por tiempo."""
        return False

    def should_evict(
        self, entries: List[CacheEntry], new_entry: CacheEntry
    ) -> Optional[CacheEntry]:
        """
        Evict la entrada con last_accessed más antiguo.
        """
        if len(entries) < self.max_size:
            return None

        # Encontrar LRU
        lru = min(entries, key=lambda e: e.last_accessed)
        return lru


class LFUStrategy(CacheStrategy):
    """
    Estrategia Least Frequently Used.

    Evict la entrada menos frecuentemente accedida.
    """

    def __init__(self, max_size: int = 1000):
        """
        Args:
            max_size: Número máximo de entradas
        """
        self.max_size = max_size

    def is_expired(self, entry: CacheEntry) -> bool:
        """LFU no expira por tiempo."""
        return False

    def should_evict(
        self, entries: List[CacheEntry], new_entry: CacheEntry
    ) -> Optional[CacheEntry]:
        """
        Evict la entrada con menor access_count.
        """
        if len(entries) < self.max_size:
            return None

        # Encontrar LFU
        lfu = min(entries, key=lambda e: e.access_count)
        return lfu


class AdaptiveTTLStrategy(CacheStrategy):
    """
    Estrategia TTL adaptativo.

    Ajusta TTL dinámicamente basado en patrones de acceso.
    """

    def __init__(self, min_ttl: int = 60, max_ttl: int = 3600, hit_threshold: int = 5):
        """
        Args:
            min_ttl: TTL mínimo en segundos
            max_ttl: TTL máximo en segundos
            hit_threshold: Umbral de hits para extender TTL
        """
        self.min_ttl = min_ttl
        self.max_ttl = max_ttl
        self.hit_threshold = hit_threshold

    def is_expired(self, entry: CacheEntry) -> bool:
        """Verifica expiración con TTL adaptativo."""
        effective_ttl = self._get_effective_ttl(entry)
        if effective_ttl is None:
            return False
        return time.time() - entry.created_at > effective_ttl

    def _get_effective_ttl(self, entry: CacheEntry) -> Optional[int]:
        """Calcula TTL efectivo basado en popularidad."""
        base_ttl = entry.ttl or self.min_ttl

        # Extender TTL para entradas populares
        if entry.access_count >= self.hit_threshold:
            extension = min(
                entry.access_count * 60, self.max_ttl - base_ttl  # 1 min extra por hit
            )
            return base_ttl + extension

        return base_ttl

    def should_evict(
        self, entries: List[CacheEntry], new_entry: CacheEntry
    ) -> Optional[CacheEntry]:
        """
        Evict entradas expiradas, luego la menos popular.
        """
        # Primero expiradas
        for entry in entries:
            if self.is_expired(entry):
                return entry

        # Luego menos popular (menos hits, más antigua)
        return min(entries, key=lambda e: (e.access_count, e.last_accessed))


class TagBasedInvalidation:
    """
    Sistema de invalidación basado en tags.

    Permite invalidar grupos de entradas por tags.
    """

    def __init__(self):
        self._tag_index: Dict[str, List[str]] = {}

    def add_to_index(self, entry: CacheEntry):
        """Agrega entrada al índice de tags."""
        for tag in entry.tags:
            if tag not in self._tag_index:
                self._tag_index[tag] = []
            if entry.key not in self._tag_index[tag]:
                self._tag_index[tag].append(entry.key)

    def remove_from_index(self, entry: CacheEntry):
        """Remueve entrada del índice."""
        for tag in entry.tags:
            if tag in self._tag_index:
                if entry.key in self._tag_index[tag]:
                    self._tag_index[tag].remove(entry.key)

    def get_keys_by_tag(self, tag: str) -> List[str]:
        """Obtiene todas las claves con un tag."""
        return self._tag_index.get(tag, []).copy()

    def invalidate_tag(self, tag: str) -> List[str]:
        """Invalida todas las entradas con un tag."""
        keys = self._tag_index.pop(tag, [])
        return keys
