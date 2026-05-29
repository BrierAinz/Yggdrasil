"""
Learning API - Endpoints REST para Auto-Discovery & Learning

v5.0-Fase4B: Patrones, sugerencias y analytics.
"""
import logging
from typing import List, Optional

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
from src.core.learning import (
    PatternConfidence,
    PatternType,
    SuggestionPriority,
    SuggestionType,
    get_analytics,
    get_pattern_discovery,
    get_suggestion_engine,
)

logger = logging.getLogger("lilith.api.learning")
router = APIRouter(prefix="/api/learning", tags=["learning"])


# ============= Schemas =============


class RecordActionRequest(BaseModel):
    user_id: str
    action_type: str
    action_name: str
    params: Optional[dict] = None
    context: Optional[dict] = None
    session_id: Optional[str] = None


class PatternResponse(BaseModel):
    id: str
    type: str
    name: str
    description: str
    confidence: str
    frequency: int
    first_seen: str
    last_seen: str


class SuggestionResponse(BaseModel):
    id: str
    type: str
    title: str
    description: str
    priority: int
    confidence: float
    created_at: str
    expires_at: Optional[str]
    action: dict


class InsightResponse(BaseModel):
    type: str
    title: str
    description: str
    data: dict


# ============= Pattern Endpoints =============


@router.get("/patterns", response_model=List[PatternResponse])
async def get_patterns(
    user_id: str,
    pattern_type: Optional[str] = None,
    min_confidence: Optional[str] = "medium",
):
    """Obtiene patrones detectados para un usuario."""
    discovery = get_pattern_discovery()

    pt = None
    if pattern_type:
        try:
            pt = PatternType(pattern_type)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid pattern type")

    mc = PatternConfidence.MEDIUM
    if min_confidence:
        try:
            mc = PatternConfidence(min_confidence)
        except ValueError:
            pass

    patterns = discovery.get_patterns_for_user(user_id, pt, mc)

    return [
        PatternResponse(
            id=p.id,
            type=p.type.value,
            name=p.name,
            description=p.description,
            confidence=p.confidence.value,
            frequency=p.frequency,
            first_seen=p.first_seen,
            last_seen=p.last_seen,
        )
        for p in patterns
    ]


@router.get("/patterns/suggested-workflows")
async def get_suggested_workflows(user_id: str):
    """Obtiene workflows sugeridos basados en patrones."""
    discovery = get_pattern_discovery()
    suggestions = discovery.get_suggested_workflows(user_id)
    return {"suggestions": suggestions}


@router.post("/patterns/analyze")
async def analyze_patterns(user_id: str):
    """Ejecuta análisis de patrones manualmente."""
    discovery = get_pattern_discovery()
    patterns = await discovery.analyze_user_patterns(user_id)

    return {
        "patterns_found": len(patterns),
        "patterns": [
            {
                "id": p.id,
                "type": p.type.value,
                "name": p.name,
                "confidence": p.confidence.value,
            }
            for p in patterns
        ],
    }


@router.get("/patterns/insights")
async def get_insights(user_id: str):
    """Obtiene insights personalizados."""
    discovery = get_pattern_discovery()
    insights = await discovery.generate_insights(user_id)
    return {"insights": insights}


# ============= Suggestion Endpoints =============


@router.get("/suggestions", response_model=List[SuggestionResponse])
async def get_suggestions(
    user_id: str, include_dismissed: bool = False, limit: int = 10
):
    """Obtiene sugerencias activas para un usuario."""
    engine = get_suggestion_engine()
    suggestions = engine.get_suggestions_for_user(user_id, include_dismissed, limit)

    return [
        SuggestionResponse(
            id=s.id,
            type=s.type.value,
            title=s.title,
            description=s.description,
            priority=s.priority.value,
            confidence=s.confidence,
            created_at=s.created_at,
            expires_at=s.expires_at,
            action=s.action,
        )
        for s in suggestions
    ]


@router.post("/suggestions/generate")
async def generate_suggestions(user_id: str):
    """Genera nuevas sugerencias manualmente."""
    engine = get_suggestion_engine()
    new_suggestions = await engine.generate_suggestions(user_id)

    return {
        "generated": len(new_suggestions),
        "suggestions": [
            {"id": s.id, "title": s.title, "type": s.type.value}
            for s in new_suggestions
        ],
    }


@router.post("/suggestions/{suggestion_id}/dismiss")
async def dismiss_suggestion(suggestion_id: str, reason: Optional[str] = None):
    """Descarta una sugerencia."""
    engine = get_suggestion_engine()
    success = await engine.dismiss_suggestion(suggestion_id, reason)

    if not success:
        raise HTTPException(status_code=404, detail="Suggestion not found")

    return {"success": True}


@router.post("/suggestions/{suggestion_id}/apply")
async def apply_suggestion(suggestion_id: str):
    """Marca una sugerencia como aplicada."""
    engine = get_suggestion_engine()
    success = await engine.apply_suggestion(suggestion_id)

    if not success:
        raise HTTPException(status_code=404, detail="Suggestion not found")

    return {"success": True}


@router.post("/suggestions/{suggestion_id}/feedback")
async def feedback_suggestion(
    suggestion_id: str, helpful: bool, feedback: Optional[str] = None
):
    """Registra feedback sobre una sugerencia."""
    engine = get_suggestion_engine()
    await engine.record_feedback(suggestion_id, helpful, feedback)
    return {"success": True}


@router.get("/suggestions/stats")
async def get_suggestion_stats(user_id: str):
    """Obtiene estadísticas de sugerencias."""
    engine = get_suggestion_engine()
    return engine.get_suggestion_stats(user_id)


@router.post("/suggestions/contextual")
async def get_contextual_suggestions(user_id: str, context: dict):
    """Obtiene sugerencias contextuales en tiempo real."""
    engine = get_suggestion_engine()
    suggestions = await engine.get_contextual_suggestions(user_id, context)

    return {
        "suggestions": [
            {
                "id": s.id,
                "title": s.title,
                "description": s.description,
                "action": s.action,
            }
            for s in suggestions
        ]
    }


# ============= Action Recording =============


@router.post("/actions/record")
async def record_action(request: RecordActionRequest):
    """Registra una acción para análisis."""
    discovery = get_pattern_discovery()
    analytics = get_analytics()

    await discovery.record_action(
        user_id=request.user_id,
        action_type=request.action_type,
        action_name=request.action_name,
        params=request.params,
        context=request.context,
        session_id=request.session_id,
    )

    analytics.record_event(
        event_type=f"{request.action_type}:{request.action_name}",
        user_id=request.user_id,
        metadata=request.context,
    )

    return {"success": True}


# ============= Analytics Endpoints =============


@router.get("/analytics/daily")
async def get_daily_analytics(days: int = 7):
    """Obtiene resumen diario de analytics."""
    analytics = get_analytics()
    return {"data": analytics.get_daily_summary(days)}


@router.get("/analytics/users/{user_id}")
async def get_user_analytics(user_id: str):
    """Obtiene analytics de un usuario."""
    analytics = get_analytics()
    return analytics.get_user_engagement(user_id)


@router.get("/analytics/report")
async def get_analytics_report(
    start_date: Optional[str] = None, end_date: Optional[str] = None
):
    """Genera un reporte de analytics."""
    analytics = get_analytics()
    return analytics.generate_report(start_date, end_date)
