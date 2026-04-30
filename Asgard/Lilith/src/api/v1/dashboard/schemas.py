"""
Dashboard API - Endpoints para modelos y cost tracking.

Provides:
- Model usage statistics
- Cost tracking and savings
- Complexity distribution
"""
import logging
from typing import Any, Dict, List

from fastapi import APIRouter, Depends, HTTPException
from src.auth.security import verify_internal_token
from src.llm.cost_tracker_extended import get_cost_tracker_v2
from src.llm.model_cache import get_model_cache
from src.llm.model_selector import get_model_selector

logger = logging.getLogger("lilith.dashboard.models")

router = APIRouter(prefix="/api/dashboard", tags=["dashboard"])


@router.get("/models")
async def get_model_stats(_: str = Depends(verify_internal_token)) -> Dict[str, Any]:
    """
    Obtiene estadísticas de uso de modelos.
    """
    try:
        tracker = get_cost_tracker_v2()
        report = tracker.get_savings_report(days=30)

        if "error" in report:
            return {"status": "error", "message": report["error"]}

        return {
            "status": "success",
            "period_days": report["period_days"],
            "total_calls": report["total_calls"],
            "total_cost": report["actual_cost"],
            "baseline_cost": report["baseline_cost"],
            "savings": {
                "amount": report["savings"],
                "percentage": report["savings_percentage"],
            },
            "by_model": report["by_model"],
            "by_complexity": report["by_complexity"],
            "total_tokens": {
                "input": report["total_input_tokens"],
                "output": report["total_output_tokens"],
            },
        }

    except Exception as e:
        logger.error("[DashboardAPI] Error getting model stats: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/models/daily")
async def get_daily_model_stats(
    days: int = 7, _: str = Depends(verify_internal_token)
) -> Dict[str, Any]:
    """
    Obtiene estadísticas diarias de modelos.
    """
    try:
        tracker = get_cost_tracker_v2()
        daily = tracker.get_daily_costs(days=days)

        return {"status": "success", "period_days": days, "daily_data": daily}

    except Exception as e:
        logger.error("[DashboardAPI] Error getting daily stats: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/models/cache")
async def get_cache_stats(_: str = Depends(verify_internal_token)) -> Dict[str, Any]:
    """
    Obtiene estadísticas del cache de modelos.
    """
    try:
        cache = get_model_cache()
        stats = cache.get_stats()
        savings = cache.get_savings_estimate()

        return {"status": "success", "cache_stats": stats, "estimated_savings": savings}

    except Exception as e:
        logger.error("[DashboardAPI] Error getting cache stats: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/models/cache/invalidate")
async def invalidate_cache(
    pattern: str = None, _: str = Depends(verify_internal_token)
) -> Dict[str, Any]:
    """
    Invalida entradas del cache.

    Args:
        pattern: Patrón para invalidar (None = todo)
    """
    try:
        cache = get_model_cache()
        count = cache.invalidate(pattern)

        return {
            "status": "success",
            "invalidated_count": count,
            "pattern": pattern or "all",
        }

    except Exception as e:
        logger.error("[DashboardAPI] Error invalidating cache: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/models/efficiency")
async def get_model_efficiency(
    days: int = 30, _: str = Depends(verify_internal_token)
) -> Dict[str, Any]:
    """
    Obtiene métricas de eficiencia por modelo.
    """
    try:
        tracker = get_cost_tracker_v2()
        efficiency = tracker.get_model_efficiency(days=days)

        return {
            "status": "success",
            "period_days": days,
            "models": efficiency.get("models", []),
        }

    except Exception as e:
        logger.error("[DashboardAPI] Error getting efficiency: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/models/available")
async def get_available_models(
    _: str = Depends(verify_internal_token),
) -> Dict[str, Any]:
    """
    Lista modelos disponibles con información.
    """
    try:
        selector = get_model_selector()
        models = selector.list_available_models()

        return {"status": "success", "models_count": len(models), "models": models}

    except Exception as e:
        logger.error("[DashboardAPI] Error listing models: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/models/analyze")
async def analyze_task_complexity(
    task: str, _: str = Depends(verify_internal_token)
) -> Dict[str, Any]:
    """
    Analiza complejidad de una tarea.
    """
    from src.core.complexity_analyzer import estimate_complexity

    try:
        result = estimate_complexity(task)
        selection = get_model_selector().select(task, user_role="owner")

        return {
            "status": "success",
            "task": task[:200] + ("..." if len(task) > 200 else ""),
            "complexity": {
                "level": result.level.value,
                "confidence": result.confidence,
                "estimated_tokens": result.estimated_tokens,
                "factors": result.factors,
                "reasoning": result.reasoning,
            },
            "recommended_model": {
                "model": selection.model,
                "estimated_cost": selection.estimated_cost,
                "fallback_chain": selection.fallback_chain,
            },
        }

    except Exception as e:
        logger.error("[DashboardAPI] Error analyzing complexity: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


def register_routes(app):
    """Registra las rutas del dashboard."""
    app.include_router(router)
