"""
API Endpoints para Modos de Personalidad y Stack de Atención.

Endpoints:
- POST /api/session/mode - Cambiar modo
- GET /api/session/mode - Obtener modo actual
- GET /api/modes - Listar modos disponibles
- GET /api/session/stack - Obtener stack
- POST /api/session/stack/add - Añadir item
- POST /api/session/stack/complete - Completar item
- POST /api/session/stack/remove - Eliminar item
"""
import logging
from typing import Any, Dict, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from src.auth.security import verify_internal_token
from src.core.attention_stack import AttentionStack, ItemStatus, get_attention_stack
from src.core.persona.manager import (
    PersonalityModeManager,
    get_personality_mode_manager,
)

logger = logging.getLogger("lilith.api.mode_stack")

router = APIRouter(prefix="/api", tags=["mode-stack"])


# ============ Schemas ============


class SetModeRequest(BaseModel):
    session_id: str
    mode_name: str
    user_id: Optional[str] = None


class StackAddRequest(BaseModel):
    session_id: str
    description: str
    priority: int = 3
    dependencies: Optional[list] = None


class StackItemRequest(BaseModel):
    session_id: str
    item_id: str


class StackClearRequest(BaseModel):
    session_id: str


# ============ Mode Endpoints ============


@router.post("/session/mode")
async def set_mode(
    request: SetModeRequest, _: str = Depends(verify_internal_token)
) -> Dict[str, Any]:
    """
    Cambia el modo de personalidad para una sesión.
    """
    try:
        manager = get_personality_mode_manager()
        success = manager.set_mode(
            request.session_id, request.mode_name, reason="manual"
        )

        if not success:
            raise HTTPException(status_code=400, detail="Invalid mode name")

        mode_info = manager.get_current_mode_info(request.session_id)

        return {
            "status": "ok",
            "session_id": request.session_id,
            "mode": request.mode_name,
            "mode_info": mode_info,
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error("[API] Error setting mode: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/session/mode")
async def get_mode(
    session_id: str, _: str = Depends(verify_internal_token)
) -> Dict[str, Any]:
    """
    Obtiene el modo de personalidad actual.
    """
    try:
        manager = get_personality_mode_manager()
        mode_info = manager.get_current_mode_info(session_id)

        return {"status": "ok", "session_id": session_id, "mode": mode_info}

    except Exception as e:
        logger.error("[API] Error getting mode: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/modes")
async def list_modes(_: str = Depends(verify_internal_token)) -> Dict[str, Any]:
    """
    Lista todos los modos de personalidad disponibles.
    """
    try:
        manager = get_personality_mode_manager()
        modes = manager.list_available_modes()

        return {"status": "ok", "modes": modes}

    except Exception as e:
        logger.error("[API] Error listing modes: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/modes/{mode_name}")
async def get_mode_details(
    mode_name: str, _: str = Depends(verify_internal_token)
) -> Dict[str, Any]:
    """
    Obtiene detalles de un modo específico.
    """
    try:
        manager = get_personality_mode_manager()

        if mode_name not in manager.modes:
            raise HTTPException(status_code=404, detail="Mode not found")

        mode = manager.modes[mode_name]

        return {
            "status": "ok",
            "mode": {
                "key": mode_name,
                "name": mode.name,
                "description": mode.description,
                "overlay": mode.overlay,
                "triggers": mode.triggers,
                "tone": mode.tone,
                "emoji": mode.emoji,
                "color": mode.color,
                "sticky_minutes": mode.sticky_minutes,
            },
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error("[API] Error getting mode details: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/session/mode/history")
async def get_mode_history(
    session_id: str, limit: int = 10, _: str = Depends(verify_internal_token)
) -> Dict[str, Any]:
    """
    Obtiene historial de cambios de modo para una sesión.
    """
    try:
        manager = get_personality_mode_manager()
        transitions = manager.get_mode_history(session_id, limit)

        return {
            "status": "ok",
            "session_id": session_id,
            "transitions": [
                {
                    "from_mode": t.from_mode,
                    "to_mode": t.to_mode,
                    "timestamp": t.timestamp,
                    "reason": t.reason,
                }
                for t in transitions
            ],
        }

    except Exception as e:
        logger.error("[API] Error getting mode history: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


# ============ Stack Endpoints ============


@router.get("/session/stack")
async def get_stack(
    session_id: str, include_done: bool = False, _: str = Depends(verify_internal_token)
) -> Dict[str, Any]:
    """
    Obtiene el stack de atención para una sesión.
    """
    try:
        stack = get_attention_stack(session_id)
        items = stack.get_all(include_done=include_done)
        stats = stack.get_stats()

        return {
            "status": "ok",
            "session_id": session_id,
            "items": [item.to_dict() for item in items],
            "stats": stats,
        }

    except Exception as e:
        logger.error("[API] Error getting stack: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/session/stack/add")
async def add_stack_item(
    request: StackAddRequest, _: str = Depends(verify_internal_token)
) -> Dict[str, Any]:
    """
    Añade un item al stack de atención.
    """
    try:
        stack = get_attention_stack(request.session_id)
        item = stack.push(
            description=request.description,
            priority=request.priority,
            dependencies=request.dependencies,
        )

        return {
            "status": "ok",
            "session_id": request.session_id,
            "item_id": item.id,
            "item": item.to_dict(),
        }

    except Exception as e:
        logger.error("[API] Error adding stack item: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/session/stack/complete")
async def complete_stack_item(
    request: StackItemRequest, _: str = Depends(verify_internal_token)
) -> Dict[str, Any]:
    """
    Marca un item del stack como completado.
    """
    try:
        stack = get_attention_stack(request.session_id)
        success = stack.pop(request.item_id, ItemStatus.DONE.value)

        if not success:
            raise HTTPException(status_code=404, detail="Item not found")

        return {
            "status": "ok",
            "session_id": request.session_id,
            "item_id": request.item_id,
            "success": True,
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error("[API] Error completing stack item: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/session/stack/remove")
async def remove_stack_item(
    request: StackItemRequest, _: str = Depends(verify_internal_token)
) -> Dict[str, Any]:
    """
    Elimina (cancela) un item del stack.
    """
    try:
        stack = get_attention_stack(request.session_id)
        success = stack.pop(request.item_id, ItemStatus.CANCELLED.value)

        if not success:
            raise HTTPException(status_code=404, detail="Item not found")

        return {
            "status": "ok",
            "session_id": request.session_id,
            "item_id": request.item_id,
            "success": True,
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error("[API] Error removing stack item: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/session/stack/clear")
async def clear_stack(
    request: StackClearRequest, _: str = Depends(verify_internal_token)
) -> Dict[str, Any]:
    """
    Limpia items completados del stack.
    """
    try:
        stack = get_attention_stack(request.session_id)
        count = stack.clear_completed()

        return {"status": "ok", "session_id": request.session_id, "count": count}

    except Exception as e:
        logger.error("[API] Error clearing stack: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/session/stack/update-priority")
async def update_item_priority(
    session_id: str,
    item_id: str,
    priority: int,
    _: str = Depends(verify_internal_token),
) -> Dict[str, Any]:
    """
    Actualiza la prioridad de un item.
    """
    try:
        stack = get_attention_stack(session_id)
        success = stack.update_priority(item_id, priority)

        if not success:
            raise HTTPException(status_code=404, detail="Item not found")

        return {
            "status": "ok",
            "session_id": session_id,
            "item_id": item_id,
            "priority": priority,
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error("[API] Error updating priority: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


def register_routes(app):
    """Registra las rutas en la aplicación FastAPI."""
    app.include_router(router)
    logger.info("[API] Mode and Stack routes registered")
