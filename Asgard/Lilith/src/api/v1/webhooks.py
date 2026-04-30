"""
Webhooks API - Endpoints para gestión de webhooks

v4.2.8: CRUD de webhooks y envío de eventos
"""
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field
from src.core.webhooks import get_webhook_manager
from src.core.webhooks.manager import WebhookEventType

router = APIRouter(prefix="/api/webhooks", tags=["webhooks"])


# Models
class WebhookCreateRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    url: str = Field(..., min_length=1, max_length=500)
    events: List[str]
    description: str = Field(default="", max_length=500)
    custom_headers: Dict[str, str] = Field(default_factory=dict)


class WebhookUpdateRequest(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    url: Optional[str] = Field(None, min_length=1, max_length=500)
    events: Optional[List[str]] = None
    enabled: Optional[bool] = None
    description: Optional[str] = Field(None, max_length=500)
    custom_headers: Optional[Dict[str, str]] = None


class WebhookResponse(BaseModel):
    success: bool
    data: Optional[Dict[str, Any]] = None
    message: str = ""


# Endpoints


@router.get("")
async def list_webhooks(event_type: Optional[str] = Query(None)):
    """Lista todos los webhooks configurados."""
    manager = get_webhook_manager()
    webhooks = manager.list_webhooks(event_type=event_type)

    return {
        "success": True,
        "data": [w.to_dict() for w in webhooks],
        "count": len(webhooks),
    }


@router.post("")
async def create_webhook(request: WebhookCreateRequest):
    """Crea un nuevo webhook."""
    manager = get_webhook_manager()

    try:
        webhook = manager.create_webhook(
            name=request.name,
            url=request.url,
            events=request.events,
            description=request.description,
            custom_headers=request.custom_headers,
        )

        return {
            "success": True,
            "data": webhook.to_dict(),
            "message": "Webhook creado exitosamente",
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/{webhook_id}")
async def get_webhook(webhook_id: str):
    """Obtiene un webhook por ID."""
    manager = get_webhook_manager()
    webhook = manager.get_webhook(webhook_id)

    if not webhook:
        raise HTTPException(status_code=404, detail="Webhook no encontrado")

    return {"success": True, "data": webhook.to_dict()}


@router.put("/{webhook_id}")
async def update_webhook(webhook_id: str, request: WebhookUpdateRequest):
    """Actualiza un webhook."""
    manager = get_webhook_manager()

    update_data = request.model_dump(exclude_unset=True)
    if not update_data:
        raise HTTPException(status_code=400, detail="No hay campos para actualizar")

    webhook = manager.update_webhook(webhook_id, **update_data)

    if not webhook:
        raise HTTPException(status_code=404, detail="Webhook no encontrado")

    return {
        "success": True,
        "data": webhook.to_dict(),
        "message": "Webhook actualizado",
    }


@router.delete("/{webhook_id}")
async def delete_webhook(webhook_id: str):
    """Elimina un webhook."""
    manager = get_webhook_manager()

    if manager.delete_webhook(webhook_id):
        return {"success": True, "message": "Webhook eliminado"}

    raise HTTPException(status_code=404, detail="Webhook no encontrado")


@router.post("/{webhook_id}/regenerate-secret")
async def regenerate_secret(webhook_id: str):
    """Regenera el secreto de un webhook."""
    manager = get_webhook_manager()

    secret = manager.regenerate_secret(webhook_id)
    if not secret:
        raise HTTPException(status_code=404, detail="Webhook no encontrado")

    return {
        "success": True,
        "data": {"secret": secret},
        "message": "Secreto regenerado. Guarda este valor, no se mostrará de nuevo.",
    }


@router.post("/{webhook_id}/test")
async def test_webhook(webhook_id: str):
    """Envía un evento de prueba al webhook."""
    manager = get_webhook_manager()

    delivery_id = await manager.test_webhook(webhook_id)
    if not delivery_id:
        raise HTTPException(status_code=404, detail="Webhook no encontrado")

    return {
        "success": True,
        "data": {"delivery_id": delivery_id},
        "message": "Evento de prueba enviado",
    }


@router.get("/{webhook_id}/deliveries")
async def get_webhook_deliveries(
    webhook_id: str, limit: int = Query(default=50, ge=1, le=100)
):
    """Obtiene historial de entregas para un webhook."""
    manager = get_webhook_manager()

    webhook = manager.get_webhook(webhook_id)
    if not webhook:
        raise HTTPException(status_code=404, detail="Webhook no encontrado")

    deliveries = manager.get_webhook_deliveries(webhook_id, limit)

    return {"success": True, "data": deliveries, "count": len(deliveries)}


@router.get("/deliveries/{delivery_id}")
async def get_delivery_status(delivery_id: str):
    """Obtiene el estado de una entrega específica."""
    manager = get_webhook_manager()

    status = manager.get_delivery_status(delivery_id)
    if not status:
        raise HTTPException(status_code=404, detail="Entrega no encontrada")

    return {"success": True, "data": status}


@router.get("/events/types")
async def list_event_types():
    """Lista todos los tipos de eventos disponibles."""
    events = [
        {"value": e.value, "description": e.name.replace("_", " ").title()}
        for e in WebhookEventType
    ]

    return {"success": True, "data": events}
