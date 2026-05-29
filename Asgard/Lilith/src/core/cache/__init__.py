"""
Sistema de Caching Inteligente - Lilith v4.2.8

Capa de caching multi-nivel para reducir llamadas a APIs externas.
"""
from .backends import MemoryBackend, MuninnBackend
from .manager import CacheManager, get_cache
from .strategies import LRUStrategy, TTLStrategy

__all__ = [
    "CacheManager",
    "get_cache",
    "MemoryBackend",
    "MuninnBackend",
    "TTLStrategy",
    "LRUStrategy",
]
