"""
API — Endpoint para callbacks de triggers de MuninnDB.
MuninnDB llama a POST /api/muninn/trigger cuando activa una memoria relevante.
"""
import json
import logging
import os
from pathlib import Path

from fastapi import APIRouter, Request
from fastapi.responses import Response

router = APIRouter(prefix="/api/muninn", tags=["muninn"])
logger = logging.getLogger("lilith.muninn_trigger_api")


def _project_root() -> Path:
    return Path(__file__).resolve().parent.parent.parent


def _internal_token() -> str:
    return (os.getenv("LILITH_INTERNAL_TOKEN", "") or "").strip()


def _json_response(data: dict, status_code: int = 200) -> Response:
    body = json.dumps(data, ensure_ascii=False).encode("utf-8")
    return Response(
        content=body,
        status_code=status_code,
        media_type="application/json; charset=utf-8",
    )


def _verify(request: Request) -> bool:
    """Verifica token interno o token de Muninn (MUNINN_TOKEN)."""
    muninn_token = (os.getenv("MUNINN_TOKEN", "") or "").strip()
    internal_token = _internal_token()
    got = (
        request.headers.get("X-Lilith-Token")
        or request.headers.get("Authorization")
        or ""
    ).strip()
    # Acepta "Bearer <token>" o el token directo
    if got.startswith("Bearer "):
        got = got[7:].strip()
    valid_tokens = {t for t in [internal_token, muninn_token] if t}
    if not valid_tokens:
        return False
    return got in valid_tokens


@router.post("/trigger")
async def muninn_trigger(request: Request) -> Response:
    """
    Recibe un callback de trigger desde MuninnDB.
    Payload esperado (flexible):
      {
        "type": "activation" | "new_memory" | "hebbian" | "custom",
        "vault": "lilith",
        "concept": "...",
        "content": "...",
        "score": 0.75,
        "tags": ["tag1", "tag2"],
        "why": {"bm25": 0.3, "hebbian": 0.4, "temporal": 0.3, "total": 1.0},
        "timestamp": 1710000000.0
      }
    """
    if not _verify(request):
        logger.warning("muninn_trigger: token inválido desde %s", request.client)
        return _json_response({"ok": False, "error": "Unauthorized"}, 401)

    try:
        body = await request.json()
    except Exception:
        return _json_response({"ok": False, "error": "Invalid JSON"}, 400)

    if not isinstance(body, dict):
        return _json_response({"ok": False, "error": "Body must be a JSON object"}, 400)

    try:
        from src.core.muninn_triggers import get_trigger_engine

        engine = get_trigger_engine(_project_root())
        result = await engine.handle(body)
        if result:
            logger.info(
                "muninn_trigger: notificación enviada (%s)", (result or "")[:80]
            )
            return _json_response(
                {"ok": True, "notified": True, "preview": (result or "")[:200]}
            )
        else:
            return _json_response({"ok": True, "notified": False})
    except Exception as e:
        logger.error("muninn_trigger: error inesperado: %s", e)
        return _json_response({"ok": False, "error": str(e)}, 500)
