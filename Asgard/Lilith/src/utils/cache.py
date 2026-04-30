"""
Cache utilities for Lilith v2.0
Simple LRU and TTL caching for performance
"""

import functools
import time
from collections import OrderedDict
from typing import Any, Callable, Optional


class SimpleCache:
    """Simple TTL + LRU cache for analysis results"""

    def __init__(self, max_size: int = 100, default_ttl: int = 300):  # 5 min default
        self.max_size = max_size
        self.default_ttl = default_ttl
        self._cache = OrderedDict()
        self._stats = {"hits": 0, "misses": 0, "evictions": 0}

    def get(self, key: str) -> Optional[Any]:
        """Get value from cache if not expired"""
        if key not in self._cache:
            self._stats["misses"] += 1
            return None

        value, expiry = self._cache[key]
        if time.time() > expiry:
            # Expired
            del self._cache[key]
            self._stats["misses"] += 1
            self._stats["evictions"] += 1
            return None

        # Cache hit - move to end (LRU)
        self._cache.move_to_end(key)
        self._stats["hits"] += 1
        return value

    def set(self, key: str, value: Any, ttl: Optional[int] = None):
        """Set value in cache with TTL"""
        if len(self._cache) >= self.max_size:
            # Evict oldest
            oldest_key = next(iter(self._cache))
            del self._cache[oldest_key]
            self._stats["evictions"] += 1

        ttl = ttl or self.default_ttl
        expiry = time.time() + ttl
        self._cache[key] = (value, expiry)
        self._cache.move_to_end(key)

    def clear(self):
        """Clear all cached values"""
        self._cache.clear()

    def stats(self) -> dict:
        """Return cache statistics"""
        total = self._stats["hits"] + self._stats["misses"]
        hit_rate = self._stats["hits"] / max(total, 1)
        return {**self._stats, "hit_rate": hit_rate, "size": len(self._cache)}


# Global cache instances
code_analysis_cache = SimpleCache(
    max_size=50, default_ttl=300
)  # 5 min for code analysis
planning_cache = SimpleCache(max_size=20, default_ttl=600)  # 10 min for plans


def cached_analysis(ttl: int = 300):
    """Decorator for caching analysis results"""

    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            # Create cache key
            key = f"{func.__name__}:{str(args)}:{str(sorted(kwargs.items()))}"

            # Check cache
            cached = code_analysis_cache.get(key)
            if cached is not None:
                return cached

            # Execute and cache
            result = func(*args, **kwargs)
            code_analysis_cache.set(key, result, ttl)
            return result

        return wrapper

    return decorator
