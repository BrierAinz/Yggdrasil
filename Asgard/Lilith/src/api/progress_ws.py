"""
WebSocket /ws/progress — Streaming de progreso de tareas en tiempo real.
El cliente se conecta con ?request_id=<id> y recibe ProgressEvents JSON.
"""
from __future__ import annotations

import asyncio
import json
import logging
from typing import Optional

from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from src.core.progress_manager import get_progress_manager

logger = logging.getLogger("lilith.progress_ws")

router = APIRouter(tags=["progress"])


@router.websocket("/ws/progress")
async def progress_ws(websocket: WebSocket, request_id: Optional[str] = None) -> None:
    """
    WebSocket de progreso.
    Query param: request_id (obligatorio).
    Envía eventos JSON: {request_id, step, status, message, pct, timestamp}
    Termina cuando llega un evento con status="done" o status="error".
    """
    await websocket.accept()

    if not request_id:
        await websocket.send_text(json.dumps({"error": "Falta request_id"}))
        await websocket.close(code=1008)
        return

    pm = get_progress_manager()
    queue = pm.subscribe(request_id)
    logger.debug("progress_ws: suscripto a request_id=%s", request_id)

    try:
        while True:
            try:
                # Esperar evento con timeout de 120s (seguridad)
                evt = await asyncio.wait_for(queue.get(), timeout=120.0)
            except asyncio.TimeoutError:
                await websocket.send_text(json.dumps({"type": "keepalive"}))
                continue

            payload = evt.to_dict()
            payload["type"] = "progress"
            await websocket.send_text(json.dumps(payload, ensure_ascii=False))

            # Finalizar cuando el step principal completa
            if evt.status in ("done", "error") and evt.pct >= 1.0:
                break

    except WebSocketDisconnect:
        logger.debug("progress_ws: cliente desconectado request_id=%s", request_id)
    except Exception as e:
        logger.warning("progress_ws error request_id=%s: %s", request_id, e)
    finally:
        pm.unsubscribe(request_id, queue)
        try:
            await websocket.close()
        except Exception:
            pass
