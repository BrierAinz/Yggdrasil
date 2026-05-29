"""
Cache API - Endpoints para gestión de caché

Features:
- Métricas de hit/miss rate
- Invalidación por namespace/tag
- Configuración dinámica
"""
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
from src.core.cache import get_cache

router = APIRouter(prefix="/api/cache", tags=["cache"])


class CacheSetRequest(BaseModel):
    key: str
    value: Any
    namespace: str = "default"
    ttl: Optional[int] = None
    tags: List[str] = []


class CacheResponse(BaseModel):
    success: bool
    message: str


class CacheMetricsResponse(BaseModel):
    enabled: bool
    global_metrics: Dict[str, Any]
    backends: Dict[str, Any]


@router.get("/metrics", response_model=CacheMetricsResponse)
async def get_cache_metrics():
    """Obtiene métricas de caché."""
    cache = get_cache()
    return CacheMetricsResponse(**cache.get_metrics())


@router.get("/get/{namespace}/{key}")
async def get_cached_value(namespace: str, key: str):
    """Obtiene un valor de caché."""
    cache = get_cache()
    value = await cache.get(key, namespace=namespace)

    if value is None:
        raise HTTPException(status_code=404, detail="Key not found or expired")

    return {"key": key, "namespace": namespace, "value": value}


@router.post("/set", response_model=CacheResponse)
async def set_cached_value(request: CacheSetRequest):
    """Almacena un valor en caché."""
    cache = get_cache()
    success = await cache.set(
        key=request.key,
        value=request.value,
        namespace=request.namespace,
        ttl=request.ttl,
        tags=set(request.tags),
    )

    return CacheResponse(
        success=success,
        message="Value cached successfully" if success else "Failed to cache value",
    )


@router.delete("/delete/{namespace}/{key}")
async def delete_cached_value(namespace: str, key: str):
    """Elimina una entrada de caché."""
    cache = get_cache()
    success = await cache.delete(key, namespace=namespace)

    if not success:
        raise HTTPException(status_code=404, detail="Key not found")

    return {"success": True, "message": "Key deleted"}


@router.post("/invalidate/tag/{tag}")
async def invalidate_by_tag(tag: str):
    """Invalida todas las entradas con un tag específico."""
    cache = get_cache()
    count = await cache.invalidate_by_tag(tag)

    return {"success": True, "invalidated_count": count, "tag": tag}


@router.post("/invalidate/pattern")
async def invalidate_by_pattern(
    pattern: str = Query(..., description="Pattern to match in keys")
):
    """Invalida entradas cuya clave contenga el patrón."""
    cache = get_cache()
    count = await cache.invalidate_by_pattern(pattern)

    return {"success": True, "invalidated_count": count, "pattern": pattern}


@router.post("/clear")
async def clear_cache():
    """Limpia toda la caché."""
    cache = get_cache()
    success = await cache.clear()

    return CacheResponse(
        success=success,
        message="Cache cleared successfully" if success else "Failed to clear cache",
    )


@router.get("/namespaces")
async def get_namespaces():
    """Lista namespaces configurados."""
    cache = get_cache()
    namespaces = cache.config.get("namespaces", {})

    return {
        "namespaces": [{"name": name, **config} for name, config in namespaces.items()]
    }


@router.post("/warm/{namespace}")
async def warm_cache(namespace: str, keys: List[str]):
    """
    Precalienta caché con valores.

    Útil para cargar datos frecuentes en startup.
    """
    # Esta función sería extendida según necesidades específicas
    return {
        "success": True,
        "message": f"Cache warming started for namespace '{namespace}'",
        "keys_requested": len(keys),
    }
