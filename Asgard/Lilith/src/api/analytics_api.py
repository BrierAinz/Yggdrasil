"""
Analytics API - Endpoints para métricas y estadísticas

v4.2.4: API de analytics
"""
from typing import Optional

from fastapi import APIRouter, Query

router = APIRouter(prefix="/api/analytics", tags=["analytics"])


@router.get("/stats")
async def get_global_stats(days: int = Query(default=7, ge=1, le=90)):
    """
    Obtener estadísticas globales del sistema.

    v4.2.8: Agregado caché de 5 minutos para agregaciones.

    Args:
        days: Período en días (1-90)

    Returns:
        Estadísticas globales
    """
    # v4.2.8: Verificar caché primero
    cache_key = f"analytics:stats:{days}"
    try:
        from src.core.cache import get_cache

        cache = get_cache()
        cached = await cache.get(cache_key, namespace="analytics")
        if cached:
            return {"success": True, "data": cached, "cached": True}
    except Exception:
        pass

    from src.core.analytics import get_analytics_manager

    analytics = get_analytics_manager()
    stats = analytics.get_global_stats(days=days)

    # v4.2.8: Guardar en caché
    try:
        await cache.set(
            cache_key,
            stats,
            namespace="analytics",
            ttl=300,  # 5 minutos
            tags={"analytics", "stats"},
        )
    except Exception:
        pass

    return {"success": True, "data": stats, "cached": False}


@router.get("/agents/{agent_name}")
async def get_agent_stats(agent_name: str, days: int = Query(default=7, ge=1, le=90)):
    """
    Obtener estadísticas de un agente específico.

    Args:
        agent_name: Nombre del agente (eva, adan, lilith, etc.)
        days: Período en días

    Returns:
        Estadísticas del agente
    """
    from src.core.analytics import get_analytics_manager

    analytics = get_analytics_manager()
    stats = analytics.get_agent_stats(agent_name, days=days)

    return {"success": True, "data": stats}


@router.get("/queries/top")
async def get_top_queries(
    limit: int = Query(default=10, ge=1, le=50),
    days: int = Query(default=7, ge=1, le=30),
):
    """
    Obtener las queries más frecuentes.

    Args:
        limit: Número máximo de queries
        days: Período en días

    Returns:
        Lista de queries más frecuentes
    """
    from src.core.analytics import get_analytics_manager

    analytics = get_analytics_manager()
    queries = analytics.get_top_queries(limit=limit, days=days)

    return {"success": True, "data": queries}


@router.get("/endpoints")
async def get_endpoint_stats():
    """
    Obtener estadísticas de endpoints API.

    Returns:
        Métricas por endpoint
    """
    from src.core.analytics import get_analytics_manager

    analytics = get_analytics_manager()
    stats = analytics.get_endpoint_stats()

    return {"success": True, "data": stats}


@router.get("/daily")
async def get_daily_summary(days: int = Query(default=7, ge=1, le=30)):
    """
    Obtener resumen diario.

    Args:
        days: Número de días

    Returns:
        Resumen por día
    """
    from src.core.analytics import get_analytics_manager

    analytics = get_analytics_manager()
    summary = analytics.get_daily_summary(days=days)

    return {"success": True, "data": summary}


@router.get("/health")
async def get_analytics_health():
    """
    Obtener estado del sistema de analytics.

    Returns:
        Estadísticas internas del manager
    """
    from src.core.analytics import get_analytics_manager

    analytics = get_analytics_manager()
    stats = analytics.get_stats()

    return {"success": True, "data": stats}
