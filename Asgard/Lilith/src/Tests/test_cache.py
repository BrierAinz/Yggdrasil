"""
Tests for Cache System

v4.2.8: Tests unitarios para el sistema de caching multi-nivel.
"""
import asyncio
from unittest.mock import AsyncMock, Mock, patch

import pytest
from src.core.cache import get_cache
from src.core.cache.backends import MemoryBackend
from src.core.cache.manager import CacheManager
from src.core.cache.strategies import LRUStrategy, TTLStrategy


class TestMemoryBackend:
    """Tests para el backend de memoria."""

    def setup_method(self):
        """Setup."""
        self.backend = MemoryBackend()

    @pytest.mark.asyncio
    async def test_get_set(self):
        """Test get/set básico."""
        await self.backend.set("key1", "value1", namespace="test")

        value = await self.backend.get("key1", namespace="test")

        assert value == "value1"

    @pytest.mark.asyncio
    async def test_get_nonexistent(self):
        """Test get de clave inexistente."""
        value = await self.backend.get("nonexistent", namespace="test")

        assert value is None

    @pytest.mark.asyncio
    async def test_delete(self):
        """Test eliminación."""
        await self.backend.set("key1", "value1", namespace="test")
        await self.backend.delete("key1", namespace="test")

        value = await self.backend.get("key1", namespace="test")

        assert value is None

    @pytest.mark.asyncio
    async def test_clear_namespace(self):
        """Test limpieza de namespace."""
        await self.backend.set("key1", "value1", namespace="test1")
        await self.backend.set("key2", "value2", namespace="test2")

        await self.backend.clear_namespace("test1")

        assert await self.backend.get("key1", namespace="test1") is None
        assert await self.backend.get("key2", namespace="test2") == "value2"

    @pytest.mark.asyncio
    async def test_namespaced_keys(self):
        """Test que las claves están aisladas por namespace."""
        await self.backend.set("key", "value1", namespace="ns1")
        await self.backend.set("key", "value2", namespace="ns2")

        assert await self.backend.get("key", namespace="ns1") == "value1"
        assert await self.backend.get("key", namespace="ns2") == "value2"


class TestTTLStrategy:
    """Tests para estrategia TTL."""

    def test_is_expired_true(self):
        """Test detección de expiración."""
        import time

        strategy = TTLStrategy()

        # Item creado hace 2 segundos con TTL de 1
        expired = strategy.is_expired(created_at=time.time() - 2, ttl=1)

        assert expired is True

    def test_is_expired_false(self):
        """Test item no expirado."""
        import time

        strategy = TTLStrategy()

        # Item creado hace 1 segundo con TTL de 60
        expired = strategy.is_expired(created_at=time.time() - 1, ttl=60)

        assert expired is False

    def test_is_expired_no_ttl(self):
        """Test item sin TTL nunca expira."""
        strategy = TTLStrategy()

        expired = strategy.is_expired(created_at=0, ttl=None)

        assert expired is False


class TestLRUStrategy:
    """Tests para estrategia LRU."""

    def test_eviction_order(self):
        """Test orden de evicción LRU."""
        strategy = LRUStrategy(max_size=3)
        items = {
            "key1": {"last_access": 100},
            "key2": {"last_access": 50},
            "key3": {"last_access": 150},
        }

        to_evict = strategy.get_eviction_candidates(items, 1)

        assert len(to_evict) == 1
        assert to_evict[0] == "key2"  # El menos recientemente usado

    def test_no_eviction_needed(self):
        """Test cuando no se necesita evicción."""
        strategy = LRUStrategy(max_size=10)
        items = {"key1": {}, "key2": {}}

        to_evict = strategy.get_eviction_candidates(items, 1)

        assert len(to_evict) == 0


class TestCacheManager:
    """Tests para el manager de caché."""

    def setup_method(self):
        """Setup."""
        self.manager = CacheManager()
        # Limpiar para tests
        self.manager._memory_cache = MemoryBackend()

    @pytest.mark.asyncio
    async def test_get_set_memory(self):
        """Test get/set en memoria."""
        await self.manager.set("key1", "value1", namespace="test", ttl=60)

        value = await self.manager.get("key1", namespace="test")

        assert value == "value1"

    @pytest.mark.asyncio
    async def test_get_with_fallback(self):
        """Test get con fallback entre niveles."""
        # Simular que está en L2 pero no en L1
        self.manager._L2_cache = Mock()
        self.manager._L2_cache.get = AsyncMock(return_value="from_L2")

        value = await self.manager.get("key1", namespace="test")

        assert value == "from_L2"

    @pytest.mark.asyncio
    async def test_delete(self):
        """Test eliminación en todos los niveles."""
        await self.manager.set("key1", "value1", namespace="test")

        await self.manager.delete("key1", namespace="test")

        value = await self.manager.get("key1", namespace="test")
        assert value is None

    @pytest.mark.asyncio
    async def test_clear_namespace(self):
        """Test limpieza de namespace."""
        await self.manager.set("key1", "value1", namespace="test")
        await self.manager.set("key2", "value2", namespace="other")

        await self.manager.clear_namespace("test")

        assert await self.manager.get("key1", namespace="test") is None
        assert await self.manager.get("key2", namespace="other") == "value2"

    @pytest.mark.asyncio
    async def test_get_stats(self):
        """Test obtención de estadísticas."""
        await self.manager.set("key1", "value1", namespace="test")
        await self.manager.set("key2", "value2", namespace="test")

        stats = self.manager.get_stats()

        assert "memory" in stats
        assert stats["memory"]["total_entries"] == 2


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
