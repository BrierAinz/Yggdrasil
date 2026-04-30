"""
Model Cache - D.12: Response caching per model with TTL.

Features:
- Cache by model and complexity
- TTL based on complexity level
- Cache invalidation on context change
- Cost savings tracking
"""
import hashlib
import json
import logging
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

from src.core.complexity_analyzer import ComplexityLevel
from src.core.json_safe import safe_load

logger = logging.getLogger("lilith.model_cache")


@dataclass
class CacheEntry:
    """Entrada de cache."""

    key: str
    response: str
    model: str
    complexity: ComplexityLevel
    timestamp: float
    ttl_seconds: int
    hit_count: int = 0


class ModelCache:
    """
    Cache de respuestas por modelo con TTL basado en complejidad.
    """

    def __init__(self, base_path: Optional[Path] = None):
        self.base_path = (
            Path(base_path) if base_path else Path(__file__).resolve().parents[3]
        )
        self.config = self._load_config()

        # TTL por complejidad
        self._ttl_by_complexity = self.config.get("cache", {}).get(
            "ttl_by_complexity",
            {
                "TRIVIAL": 86400,  # 24h
                "SIMPLE": 3600,  # 1h
                "MODERATE": 1800,  # 30min
                "COMPLEX": 600,  # 10min
                "EXPERT": 300,  # 5min
            },
        )

        # Max entries
        self._max_entries = self.config.get("cache", {}).get("max_entries", 1000)

        # In-memory cache
        self._cache: Dict[str, CacheEntry] = {}
        self._hits = 0
        self._misses = 0

        logger.info("[ModelCache] Inicializado. Max entries: %d", self._max_entries)

    def _load_config(self) -> dict:
        """Carga configuración desde model_selector.json."""
        config_path = self.base_path / "Config" / "model_selector.json"
        return safe_load(config_path, default={})

    def _generate_key(self, task: str, model: str, context_hash: str = "") -> str:
        """Genera key de cache."""
        # Normalizar task
        normalized = task.strip().lower()
        # Hash compuesto
        key_data = f"{normalized}:{model}:{context_hash}"
        return hashlib.sha256(key_data.encode()).hexdigest()[:32]

    def get(
        self, task: str, model: str, context: Optional[Dict] = None
    ) -> Optional[str]:
        """
        Obtiene respuesta de cache si existe y es válida.

        Args:
            task: Tarea/prompt
            model: Modelo usado
            context: Contexto adicional

        Returns:
            Respuesta cacheada o None
        """
        if not self.config.get("cache", {}).get("enabled", True):
            return None

        context_hash = self._hash_context(context)
        key = self._generate_key(task, model, context_hash)

        entry = self._cache.get(key)
        if not entry:
            self._misses += 1
            return None

        # Verificar TTL
        if time.time() - entry.timestamp > entry.ttl_seconds:
            # Expirado
            del self._cache[key]
            self._misses += 1
            return None

        # Cache hit
        entry.hit_count += 1
        self._hits += 1

        logger.debug("[ModelCache] Hit for %s (hits: %d)", key[:8], entry.hit_count)
        return entry.response

    def set(
        self,
        task: str,
        model: str,
        response: str,
        complexity: ComplexityLevel,
        context: Optional[Dict] = None,
    ) -> None:
        """
        Guarda respuesta en cache.

        Args:
            task: Tarea/prompt
            model: Modelo usado
            response: Respuesta a cachear
            complexity: Nivel de complejidad (determina TTL)
            context: Contexto adicional
        """
        if not self.config.get("cache", {}).get("enabled", True):
            return

        # Limpiar si estamos cerca del límite
        if len(self._cache) >= self._max_entries:
            self._cleanup()

        context_hash = self._hash_context(context)
        key = self._generate_key(task, model, context_hash)

        ttl = self._ttl_by_complexity.get(complexity.value, 1800)

        entry = CacheEntry(
            key=key,
            response=response,
            model=model,
            complexity=complexity,
            timestamp=time.time(),
            ttl_seconds=ttl,
        )

        self._cache[key] = entry
        logger.debug("[ModelCache] Set for %s (TTL: %ds)", key[:8], ttl)

    def _hash_context(self, context: Optional[Dict]) -> str:
        """Genera hash del contexto para invalidación."""
        if not context:
            return ""

        # Solo hash de partes relevantes del contexto
        relevant = {
            "user_id": context.get("user_id"),
            "role": context.get("role"),
            "tools": sorted(context.get("tools", [])) if context.get("tools") else [],
        }

        context_str = json.dumps(relevant, sort_keys=True)
        return hashlib.sha256(context_str.encode()).hexdigest()[:16]

    def _cleanup(self) -> None:
        """Limpia entradas expiradas y antiguas."""
        now = time.time()

        # Eliminar expirados
        expired = [
            k for k, v in self._cache.items() if now - v.timestamp > v.ttl_seconds
        ]
        for k in expired:
            del self._cache[k]

        # Si aún estamos cerca del límite, eliminar menos usados
        if len(self._cache) >= self._max_entries * 0.9:
            # Ordenar por hit_count y timestamp
            sorted_entries = sorted(
                self._cache.items(),
                key=lambda x: (x[1].hit_count, -(now - x[1].timestamp)),
            )

            # Eliminar el 20% menos usado
            to_remove = int(self._max_entries * 0.2)
            for k, _ in sorted_entries[:to_remove]:
                del self._cache[k]

        logger.debug(
            "[ModelCache] Cleanup: %d expired removed, %d remaining",
            len(expired),
            len(self._cache),
        )

    def invalidate(self, pattern: Optional[str] = None) -> int:
        """
        Invalida entradas de cache.

        Args:
            pattern: Patrón para invalidar (si None, limpia todo)

        Returns:
            Número de entradas invalidadas
        """
        if pattern is None:
            count = len(self._cache)
            self._cache.clear()
            logger.info("[ModelCache] All entries invalidated (%d)", count)
            return count

        # Invalidar por patrón
        to_remove = [k for k in self._cache if pattern in k]
        for k in to_remove:
            del self._cache[k]

        logger.info(
            "[ModelCache] Invalidated %d entries matching '%s'", len(to_remove), pattern
        )
        return len(to_remove)

    def get_stats(self) -> Dict[str, Any]:
        """Obtiene estadísticas del cache."""
        total = len(self._cache)
        if total == 0:
            return {
                "total_entries": 0,
                "hits": self._hits,
                "misses": self._misses,
                "hit_rate": 0.0,
                "by_complexity": {},
            }

        by_complexity = {}
        for entry in self._cache.values():
            level = entry.complexity.value
            if level not in by_complexity:
                by_complexity[level] = {"count": 0, "hits": 0}
            by_complexity[level]["count"] += 1
            by_complexity[level]["hits"] += entry.hit_count

        total_requests = self._hits + self._misses
        hit_rate = (self._hits / total_requests * 100) if total_requests > 0 else 0

        return {
            "total_entries": total,
            "hits": self._hits,
            "misses": self._misses,
            "hit_rate": round(hit_rate, 2),
            "by_complexity": by_complexity,
        }

    def get_savings_estimate(self) -> Dict[str, float]:
        """Estima ahorros por uso de cache."""
        # Asumir costo promedio de $0.005 por request
        avg_cost_per_request = 0.005

        saved_requests = self._hits
        estimated_savings = saved_requests * avg_cost_per_request

        return {
            "cache_hits": self._hits,
            "estimated_savings_usd": round(estimated_savings, 4),
            "avg_cost_per_request": avg_cost_per_request,
        }


# Singleton
_cache_instance: Optional[ModelCache] = None


def get_model_cache(base_path: Optional[Path] = None) -> ModelCache:
    """Obtiene instancia singleton del ModelCache."""
    global _cache_instance
    if _cache_instance is None:
        _cache_instance = ModelCache(base_path)
    return _cache_instance


def get_cached_response(
    task: str, model: str, context: Optional[Dict] = None
) -> Optional[str]:
    """Función conveniencia para obtener de cache."""
    cache = get_model_cache()
    return cache.get(task, model, context)


def cache_response(
    task: str,
    model: str,
    response: str,
    complexity: ComplexityLevel,
    context: Optional[Dict] = None,
) -> None:
    """Función conveniencia para guardar en cache."""
    cache = get_model_cache()
    cache.set(task, model, response, complexity, context)


__all__ = [
    "CacheEntry",
    "ModelCache",
    "get_model_cache",
    "get_cached_response",
    "cache_response",
]
