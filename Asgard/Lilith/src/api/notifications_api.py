"""
Lilith v2.3 — Fase B: API de notificaciones.
GET /api/notifications, POST /api/notifications/{id}/read, DELETE /api/notifications/clear
Al listar, se ejecuta un chequeo de monitores para generar notificaciones (p. ej. error recurrente).
"""
import logging
from pathlib import Path

from fastapi import APIRouter, HTTPException
from src.notifications.notification_engine import NotificationEngine
from src.notifications.notification_store import NotificationStore

logger = logging.getLogger("NotificationsAPI")

router = APIRouter(prefix="/api/notifications", tags=["Notifications"])


def _root() -> Path:
    return Path(__file__).resolve().parent.parent.parent


def _store() -> NotificationStore:
    return NotificationStore(_root())


def _run_check_once():
    """Ejecuta los monitores una vez (error_history, etc.) para crear notificaciones si aplica."""
    try:
        engine = NotificationEngine(
            base_path=_root(),
            get_token_stats=lambda: {},
            send_event=lambda _: None,
        )
        engine.run_once()
    except Exception as e:
        logger.debug("Notification check: %s", e)


@router.get("")
async def list_notifications():
    """Lista notificaciones (no leídas primero). Ejecuta chequeo antes para crear nuevas."""
    try:
        _run_check_once()
        items = _store().get_all()
        return {"success": True, "data": items}
    except Exception as e:
        logger.exception("List notifications: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/unread-count")
async def unread_count():
    """Cantidad de no leídas (para badge). Ejecuta chequeo antes."""
    try:
        _run_check_once()
        n = _store().get_unread_count()
        return {"success": True, "count": n}
    except Exception as e:
        logger.exception("Unread count: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{notification_id}/read")
async def mark_read(notification_id: str):
    """Marca una notificación como leída."""
    try:
        ok = _store().mark_read(notification_id)
        return {"success": ok, "id": notification_id}
    except Exception as e:
        logger.exception("Mark read: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/clear")
async def clear_all():
    """Borra todas las notificaciones."""
    try:
        _store().clear()
        return {"success": True}
    except Exception as e:
        logger.exception("Clear notifications: %s", e)
        raise HTTPException(status_code=500, detail=str(e))
