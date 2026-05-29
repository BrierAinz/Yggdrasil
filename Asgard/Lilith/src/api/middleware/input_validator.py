from __future__ import annotations

import json
import logging
from typing import Any, Dict

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse, Response

logger = logging.getLogger("InputValidator")


class InputValidationMiddleware(BaseHTTPMiddleware):
    """
    Middleware de validación de entrada:
    - Limita tamaño de body.
    - Valida Content-Type básico para JSON.
    - Rechaza cuerpos claramente malformados antes de llegar a los endpoints.
    """

    MAX_BODY_SIZE = 1_000_000  # 1 MB

    async def dispatch(self, request: Request, call_next) -> Response:
        try:
            if request.method in {"POST", "PUT", "PATCH"}:
                # 1) Tamaño máximo de body (si el servidor expone el header)
                content_length = request.headers.get("content-length")
                if content_length is not None:
                    try:
                        length = int(content_length)
                        if length > self.MAX_BODY_SIZE:
                            logger.warning(
                                "Request rechazado por tamaño: %s bytes > %s",
                                length,
                                self.MAX_BODY_SIZE,
                            )
                            return JSONResponse(
                                status_code=413,
                                content={"detail": "Body demasiado grande"},
                            )
                    except ValueError:
                        logger.warning(
                            "Header Content-Length inválido: %r", content_length
                        )

                # 2) Validar JSON cuando el Content-Type es application/json
                content_type = request.headers.get("content-type", "")
                if "application/json" in content_type:
                    body = await request.body()
                    if len(body) > self.MAX_BODY_SIZE:
                        logger.warning(
                            "Request rechazado por tamaño real: %s bytes > %s",
                            len(body),
                            self.MAX_BODY_SIZE,
                        )
                        return JSONResponse(
                            status_code=413,
                            content={"detail": "Body demasiado grande"},
                        )
                    if body:
                        try:
                            json.loads(body.decode("utf-8", errors="replace"))
                        except Exception as e:
                            logger.warning(
                                "JSON malformado en petición a %s: %s",
                                request.url.path,
                                e,
                            )
                            return JSONResponse(
                                status_code=400,
                                content={"detail": "JSON malformado"},
                            )
                    request._body = body  # type: ignore[attr-defined]
        except Exception as e:
            logger.error(
                "Error en validación de entrada (middleware): %s", e, exc_info=True
            )
            return JSONResponse(
                status_code=500,
                content={"detail": "Error interno de validación de entrada"},
            )
        response = await call_next(request)
        return response


def validate_ws_message(data: Dict[str, Any]) -> tuple[bool, str]:
    """
    Validar mensaje WebSocket antes de procesarlo.
    Protege contra tipos desconocidos y mensajes vacíos/excesivos.
    """
    if not isinstance(data, dict):
        return False, "Mensaje WS debe ser un objeto JSON"

    if "type" not in data:
        return False, "Falta campo 'type'"

    msg_type = data.get("type")

    # Solo validamos contenido para mensajes de chat.
    # Otros tipos (ping, approval, get_status, etc.) se permiten tal cual.
    if msg_type == "message":
        text = str(data.get("text", "") or "")
        text_stripped = text.strip()
        if not text_stripped:
            return False, "Mensaje vacío"
        if len(text_stripped) > 50_000:
            return False, "Mensaje demasiado largo"

    return True, ""
