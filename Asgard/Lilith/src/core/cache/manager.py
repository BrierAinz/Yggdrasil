"""
Cache Manager - Sistema de caching multi-nivel

Features:
- Múltiples backends (Memory, MuninnDB)
- Estrategias de invalidación (TTL, LRU)
- Métricas de hit/miss rate
- Invalidación por patrones
"""
import asyncio
import hashlib
import json
import logging
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Set

from src.core.json_safe import safe_load

logger = logging.getLogger("lilith.cache")


@dataclass
class CacheEntry:
    """Entrada de caché con metadata."""

    key: str
    value: Any
    created_at: float
    ttl: Optional[int] = None  # segundos
    tags: Set[str] = field(default_factory=set)
    access_count: int = 0
    last_accessed: float = field(default_factory=time.time)

    def is_expired(self) -> bool:
        """Verifica si la entrada expiró."""
        if self.ttl is None:
            return False
        return time.time() - self.created_at > self.ttl

    def touch(self):
        """Actualiza último acceso."""
        self.access_count += 1
        self.last_accessed = time.time()


@dataclass
class CacheMetrics:
    """Métricas de caché."""

    hits: int = 0
    misses: int = 0
    sets: int = 0
    deletes: int = 0
    evictions: int = 0
    hit_rate: float = 0.0

    def record_hit(self):
        self.hits += 1
        self._update_hit_rate()

    def record_miss(self):
        self.misses += 1
        self._update_hit_rate()

    def _update_hit_rate(self):
        total = self.hits + self.misses
        if total > 0:
            self.hit_rate = self.hits / total


class CacheBackend(ABC):
    """Backend abstracto de caché."""

    @abstractmethod
    async def get(self, key: str) -> Optional[CacheEntry]:
        pass

    @abstractmethod
    async def set(self, entry: CacheEntry) -> bool:
        pass

    @abstractmethod
    async def delete(self, key: str) -> bool:
        pass

    @abstractmethod
    async def clear(self) -> bool:
        pass

    @abstractmethod
    async def keys(self) -> List[str]:
        pass

    @abstractmethod
    def get_metrics(self) -> Dict[str, Any]:
        pass


class CacheManager:
    """
    Manager de caché multi-nivel.

    Estrategia:
    1. L1: Memoria (rápido, volátil)
    2. L2: MuninnDB (persistente, más lento)
    """

    _instance: Optional["CacheManager"] = None
    _lock = asyncio.Lock()

    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self, base_path: Optional[Path] = None):
        if self._initialized:
            return

        self.base_path = (
            Path(base_path) if base_path else Path(__file__).resolve().parents[3]
        )
        self.config = self._load_config()
        self.enabled = self.config.get("enabled", True)

        # Backends
        self.backends: Dict[str, CacheBackend] = {}
        self._init_backends()

        # Métricas
        self.metrics = CacheMetrics()

        # Callbacks de invalidación
        self._invalidation_hooks: List[Callable[[str], None]] = []

        # Iniciar cleanup periódico
        self._cleanup_task: Optional[asyncio.Task] = None
        if self.enabled:
            self._start_cleanup_task()

        self._initialized = True
        logger.info(
            "[CacheManager] Inicializado. Backends: %s", list(self.backends.keys())
        )

    def _load_config(self) -> dict:
        """Carga configuración de caché."""
        config_path = self.base_path / "Config" / "cache.json"
        return safe_load(
            config_path,
            default={
                "enabled": True,
                "default_ttl": 300,
                "cleanup_interval": 300,
                "backends": {
                    "memory": {"enabled": True, "max_size": 1000, "ttl": 300},
                    "muninn": {"enabled": True, "ttl": 3600},
                },
            },
        )

    def _init_backends(self):
        """Inicializa backends configurados."""
        from .backends import MemoryBackend, MuninnBackend

        backends_config = self.config.get("backends", {})

        if backends_config.get("memory", {}).get("enabled", True):
            self.backends["memory"] = MemoryBackend(
                max_size=backends_config["memory"].get("max_size", 1000)
            )

        if backends_config.get("muninn", {}).get("enabled", True):
            self.backends["muninn"] = MuninnBackend(
                base_path=self.base_path, ttl=backends_config["muninn"].get("ttl", 3600)
            )

    def _start_cleanup_task(self):
        """Inicia tarea de limpieza periódica."""
        interval = self.config.get("cleanup_interval", 300)

        async def cleanup_loop():
            while True:
                try:
                    await asyncio.sleep(interval)
                    await self._cleanup_expired()
                except asyncio.CancelledError:
                    break
                except Exception as e:
                    logger.error("[CacheManager] Error en cleanup: %s", e)

        self._cleanup_task = asyncio.create_task(cleanup_loop())

    async def _cleanup_expired(self):
        """Limpia entradas expiradas de todos los backends."""
        for name, backend in self.backends.items():
            try:
                keys = await backend.keys()
                expired = 0
                for key in keys:
                    entry = await backend.get(key)
                    if entry and entry.is_expired():
                        await backend.delete(key)
                        expired += 1
                if expired > 0:
                    logger.debug(
                        "[CacheManager] %s: %d entradas expiradas limpiadas",
                        name,
                        expired,
                    )
            except Exception as e:
                logger.error("[CacheManager] Error limpiando %s: %s", name, e)

    def _make_key(self, *parts: str) -> str:
        """Genera una clave de caché hash."""
        combined = ":".join(str(p) for p in parts)
        return hashlib.sha256(combined.encode()).hexdigest()[:32]

    async def get(self, key: str, namespace: str = "default") -> Optional[Any]:
        """
        Obtiene un valor de caché.

        Busca en orden: L1 (memory) → L2 (muninn)
        """
        if not self.enabled:
            return None

        full_key = f"{namespace}:{key}"

        # Buscar en L1 primero
        if "memory" in self.backends:
            entry = await self.backends["memory"].get(full_key)
            if entry:
                if entry.is_expired():
                    await self.backends["memory"].delete(full_key)
                else:
                    entry.touch()
                    self.metrics.record_hit()
                    logger.debug("[CacheManager] L1 HIT: %s", full_key[:16])
                    return entry.value

        # Buscar en L2
        for backend_name in ["muninn"]:
            if backend_name in self.backends:
                entry = await self.backends[backend_name].get(full_key)
                if entry:
                    if entry.is_expired():
                        await self.backends[backend_name].delete(full_key)
                    else:
                        entry.touch()
                        # Promover a L1
                        if "memory" in self.backends:
                            await self.backends["memory"].set(entry)
                        self.metrics.record_hit()
                        logger.debug(
                            "[CacheManager] L2 HIT (%s): %s",
                            backend_name,
                            full_key[:16],
                        )
                        return entry.value

        self.metrics.record_miss()
        logger.debug("[CacheManager] MISS: %s", full_key[:16])
        return None

    async def set(
        self,
        key: str,
        value: Any,
        namespace: str = "default",
        ttl: Optional[int] = None,
        tags: Optional[Set[str]] = None,
        backend: Optional[str] = None,
    ) -> bool:
        """
        Almacena un valor en caché.

        Args:
            key: Clave de caché
            value: Valor a almacenar
            namespace: Namespace para aislamiento
            ttl: Tiempo de vida en segundos (None = infinito)
            tags: Tags para invalidación por grupo
            backend: Backend específico (None = todos)
        """
        if not self.enabled:
            return False

        full_key = f"{namespace}:{key}"

        if ttl is None:
            ttl = self.config.get("default_ttl", 300)

        entry = CacheEntry(
            key=full_key,
            value=value,
            created_at=time.time(),
            ttl=ttl,
            tags=tags or set(),
        )

        success = True
        target_backends = [backend] if backend else list(self.backends.keys())

        for name in target_backends:
            if name in self.backends:
                try:
                    result = await self.backends[name].set(entry)
                    if not result:
                        success = False
                except Exception as e:
                    logger.error("[CacheManager] Error en %s.set: %s", name, e)
                    success = False

        if success:
            self.metrics.sets += 1
            logger.debug("[CacheManager] SET: %s (ttl=%s)", full_key[:16], ttl)

        return success

    async def delete(self, key: str, namespace: str = "default") -> bool:
        """Elimina una entrada de caché."""
        if not self.enabled:
            return False

        full_key = f"{namespace}:{key}"
        success = True

        for name, backend in self.backends.items():
            try:
                result = await backend.delete(full_key)
                if not result:
                    success = False
            except Exception as e:
                logger.error("[CacheManager] Error en %s.delete: %s", name, e)
                success = False

        if success:
            self.metrics.deletes += 1
            logger.debug("[CacheManager] DELETE: %s", full_key[:16])

        return success

    async def invalidate_by_tag(self, tag: str) -> int:
        """Invalida todas las entradas con un tag específico."""
        if not self.enabled:
            return 0

        count = 0
        for name, backend in self.backends.items():
            try:
                keys = await backend.keys()
                for key in keys:
                    entry = await backend.get(key)
                    if entry and tag in entry.tags:
                        await backend.delete(key)
                        count += 1
            except Exception as e:
                logger.error("[CacheManager] Error invalidando en %s: %s", name, e)

        logger.info("[CacheManager] Invalidadas %d entradas con tag '%s'", count, tag)
        return count

    async def invalidate_by_pattern(self, pattern: str) -> int:
        """Invalida entradas cuya clave contenga el patrón."""
        if not self.enabled:
            return 0

        count = 0
        for name, backend in self.backends.items():
            try:
                keys = await backend.keys()
                for key in keys:
                    if pattern in key:
                        await backend.delete(key)
                        count += 1
            except Exception as e:
                logger.error(
                    "[CacheManager] Error invalidando patrón en %s: %s", name, e
                )

        logger.info(
            "[CacheManager] Invalidadas %d entradas con patrón '%s'", count, pattern
        )
        return count

    async def clear(self) -> bool:
        """Limpia toda la caché."""
        success = True
        for name, backend in self.backends.items():
            try:
                result = await backend.clear()
                if not result:
                    success = False
            except Exception as e:
                logger.error("[CacheManager] Error limpiando %s: %s", name, e)
                success = False

        self.metrics = CacheMetrics()
        logger.info("[CacheManager] Caché limpiada")
        return success

    def get_metrics(self) -> Dict[str, Any]:
        """Obtiene métricas de caché."""
        backend_metrics = {}
        for name, backend in self.backends.items():
            backend_metrics[name] = backend.get_metrics()

        return {
            "enabled": self.enabled,
            "global": {
                "hits": self.metrics.hits,
                "misses": self.metrics.misses,
                "sets": self.metrics.sets,
                "deletes": self.metrics.deletes,
                "hit_rate": round(self.metrics.hit_rate, 4),
            },
            "backends": backend_metrics,
        }

    def register_invalidation_hook(self, hook: Callable[[str], None]):
        """Registra un callback para invalidaciones."""
        self._invalidation_hooks.append(hook)

    async def close(self):
        """Cierra el manager y libera recursos."""
        if self._cleanup_task:
            self._cleanup_task.cancel()
            try:
                await self._cleanup_task
            except asyncio.CancelledError:
                pass

        for backend in self.backends.values():
            if hasattr(backend, "close"):
                await backend.close()

        logger.info("[CacheManager] Cerrado")


# Singleton
_cache_manager: Optional[CacheManager] = None


def get_cache(base_path: Optional[Path] = None) -> CacheManager:
    """Obtiene instancia del CacheManager."""
    global _cache_manager
    if _cache_manager is None:
        _cache_manager = CacheManager(base_path)
    return _cache_manager


__all__ = ["CacheManager", "get_cache", "CacheEntry", "CacheMetrics"]
