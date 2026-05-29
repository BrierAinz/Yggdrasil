"""
Backends de Caché - Implementaciones concretas
"""
import json
import logging
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

from .manager import CacheBackend, CacheEntry, CacheMetrics

logger = logging.getLogger("lilith.cache")


class MemoryBackend(CacheBackend):
    """
    Backend de caché en memoria.

    Rápido pero volátil. Ideal para L1 cache.
    """

    def __init__(self, max_size: int = 1000):
        self.max_size = max_size
        self._store: Dict[str, CacheEntry] = {}
        self._metrics = CacheMetrics()

    async def get(self, key: str) -> Optional[CacheEntry]:
        """Obtiene entrada de caché."""
        entry = self._store.get(key)
        if entry:
            self._metrics.record_hit()
        else:
            self._metrics.record_miss()
        return entry

    async def set(self, entry: CacheEntry) -> bool:
        """Almacena entrada. Implementa LRU si excede max_size."""
        try:
            # Evict si es necesario (LRU simple)
            if len(self._store) >= self.max_size:
                # Encontrar entrada menos usada
                lru_key = min(
                    self._store.keys(), key=lambda k: self._store[k].last_accessed
                )
                del self._store[lru_key]
                self._metrics.evictions += 1
                logger.debug("[MemoryBackend] LRU eviction: %s", lru_key[:16])

            self._store[entry.key] = entry
            self._metrics.sets += 1
            return True
        except Exception as e:
            logger.error("[MemoryBackend] Error en set: %s", e)
            return False

    async def delete(self, key: str) -> bool:
        """Elimina entrada."""
        if key in self._store:
            del self._store[key]
            self._metrics.deletes += 1
            return True
        return False

    async def clear(self) -> bool:
        """Limpia todas las entradas."""
        self._store.clear()
        return True

    async def keys(self) -> List[str]:
        """Lista todas las claves."""
        return list(self._store.keys())

    def get_metrics(self) -> Dict[str, Any]:
        """Obtiene métricas del backend."""
        return {
            "type": "memory",
            "size": len(self._store),
            "max_size": self.max_size,
            "utilization": len(self._store) / self.max_size if self.max_size > 0 else 0,
            "hits": self._metrics.hits,
            "misses": self._metrics.misses,
            "hit_rate": round(self._metrics.hit_rate, 4),
            "evictions": self._metrics.evictions,
        }


class MuninnBackend(CacheBackend):
    """
    Backend de caché usando MuninnDB.

    Persistente pero más lento. Ideal para L2 cache.
    """

    def __init__(self, base_path: Path, ttl: int = 3600):
        self.base_path = base_path
        self.ttl = ttl
        self._metrics = CacheMetrics()
        self._vault = "lilith_cache"

        # Cache file-based fallback
        self._cache_dir = base_path / "Data" / "cache_v2"
        self._cache_dir.mkdir(parents=True, exist_ok=True)

    def _entry_path(self, key: str) -> Path:
        """Genera path para entrada."""
        # Sanitize key para filename
        safe_key = key.replace(":", "_").replace("/", "_")[:64]
        return self._cache_dir / f"{safe_key}.json"

    async def get(self, key: str) -> Optional[CacheEntry]:
        """Obtiene entrada de caché."""
        try:
            path = self._entry_path(key)
            if not path.exists():
                self._metrics.record_miss()
                return None

            data = json.loads(path.read_text(encoding="utf-8"))

            # Reconstruir entrada
            entry = CacheEntry(
                key=data["key"],
                value=data["value"],
                created_at=data["created_at"],
                ttl=data.get("ttl"),
                tags=set(data.get("tags", [])),
                access_count=data.get("access_count", 0),
                last_accessed=data.get("last_accessed", data["created_at"]),
            )

            self._metrics.record_hit()
            return entry

        except Exception as e:
            logger.debug("[MuninnBackend] Error en get: %s", e)
            self._metrics.record_miss()
            return None

    async def set(self, entry: CacheEntry) -> bool:
        """Almacena entrada."""
        try:
            path = self._entry_path(entry.key)
            data = {
                "key": entry.key,
                "value": entry.value,
                "created_at": entry.created_at,
                "ttl": entry.ttl,
                "tags": list(entry.tags),
                "access_count": entry.access_count,
                "last_accessed": entry.last_accessed,
            }
            path.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
            self._metrics.sets += 1
            return True
        except Exception as e:
            logger.error("[MuninnBackend] Error en set: %s", e)
            return False

    async def delete(self, key: str) -> bool:
        """Elimina entrada."""
        try:
            path = self._entry_path(key)
            if path.exists():
                path.unlink()
                self._metrics.deletes += 1
                return True
            return False
        except Exception as e:
            logger.error("[MuninnBackend] Error en delete: %s", e)
            return False

    async def clear(self) -> bool:
        """Limpia todas las entradas."""
        try:
            for path in self._cache_dir.glob("*.json"):
                path.unlink()
            return True
        except Exception as e:
            logger.error("[MuninnBackend] Error en clear: %s", e)
            return False

    async def keys(self) -> List[str]:
        """Lista todas las claves."""
        try:
            keys = []
            for path in self._cache_dir.glob("*.json"):
                try:
                    data = json.loads(path.read_text(encoding="utf-8"))
                    keys.append(data["key"])
                except:
                    continue
            return keys
        except Exception as e:
            logger.error("[MuninnBackend] Error listando keys: %s", e)
            return []

    def get_metrics(self) -> Dict[str, Any]:
        """Obtiene métricas del backend."""
        try:
            size = len(list(self._cache_dir.glob("*.json")))
        except:
            size = 0

        return {
            "type": "muninn",
            "size": size,
            "cache_dir": str(self._cache_dir),
            "hits": self._metrics.hits,
            "misses": self._metrics.misses,
            "hit_rate": round(self._metrics.hit_rate, 4),
        }


class RedisBackend(CacheBackend):
    """
    Backend de caché usando Redis (opcional).

    Requiere: pip install redis
    """

    def __init__(self, host: str = "localhost", port: int = 6379, db: int = 0):
        self.host = host
        self.port = port
        self.db = db
        self._metrics = CacheMetrics()
        self._client = None

        try:
            import redis

            self._client = redis.Redis(
                host=host, port=port, db=db, decode_responses=True
            )
            self._client.ping()
            logger.info("[RedisBackend] Conectado a Redis")
        except ImportError:
            logger.warning("[RedisBackend] redis no instalado. Usando fallback.")
        except Exception as e:
            logger.warning("[RedisBackend] No se pudo conectar: %s", e)

    async def get(self, key: str) -> Optional[CacheEntry]:
        """Obtiene entrada de caché."""
        if not self._client:
            self._metrics.record_miss()
            return None

        try:
            data = self._client.get(f"lilith:cache:{key}")
            if not data:
                self._metrics.record_miss()
                return None

            parsed = json.loads(data)
            entry = CacheEntry(**parsed)
            self._metrics.record_hit()
            return entry
        except Exception as e:
            logger.debug("[RedisBackend] Error en get: %s", e)
            self._metrics.record_miss()
            return None

    async def set(self, entry: CacheEntry) -> bool:
        """Almacena entrada."""
        if not self._client:
            return False

        try:
            data = {
                "key": entry.key,
                "value": entry.value,
                "created_at": entry.created_at,
                "ttl": entry.ttl,
                "tags": list(entry.tags),
                "access_count": entry.access_count,
                "last_accessed": entry.last_accessed,
            }

            ttl = entry.ttl or self.ttl
            self._client.setex(
                f"lilith:cache:{entry.key}", ttl, json.dumps(data, ensure_ascii=False)
            )
            self._metrics.sets += 1
            return True
        except Exception as e:
            logger.error("[RedisBackend] Error en set: %s", e)
            return False

    async def delete(self, key: str) -> bool:
        """Elimina entrada."""
        if not self._client:
            return False

        try:
            result = self._client.delete(f"lilith:cache:{key}")
            if result:
                self._metrics.deletes += 1
            return result > 0
        except Exception as e:
            logger.error("[RedisBackend] Error en delete: %s", e)
            return False

    async def clear(self) -> bool:
        """Limpia todas las entradas."""
        if not self._client:
            return False

        try:
            pattern = "lilith:cache:*"
            keys = self._client.scan_iter(match=pattern)
            for key in keys:
                self._client.delete(key)
            return True
        except Exception as e:
            logger.error("[RedisBackend] Error en clear: %s", e)
            return False

    async def keys(self) -> List[str]:
        """Lista todas las claves."""
        if not self._client:
            return []

        try:
            pattern = "lilith:cache:*"
            keys = self._client.scan_iter(match=pattern)
            return [k.decode().replace("lilith:cache:", "") for k in keys]
        except Exception as e:
            logger.error("[RedisBackend] Error listando keys: %s", e)
            return []

    def get_metrics(self) -> Dict[str, Any]:
        """Obtiene métricas del backend."""
        info = {"type": "redis", "connected": self._client is not None}

        if self._client:
            try:
                info["size"] = self._client.dbsize()
            except:
                info["size"] = 0

        info.update(
            {
                "hits": self._metrics.hits,
                "misses": self._metrics.misses,
                "hit_rate": round(self._metrics.hit_rate, 4),
                "host": self.host,
                "port": self.port,
            }
        )

        return info
