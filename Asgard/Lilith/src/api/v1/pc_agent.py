import asyncio
import logging
from pathlib import Path

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import Response
from src.api.v1.bots.discord import _internal_token, _json_response, _project_root

logger = logging.getLogger("lilith.pc_agent_api")
router = APIRouter(prefix="/api/pc", tags=["pc_agent"])


def _verify(request: Request):
    token = _internal_token()
    got = (request.headers.get("X-Lilith-Token") or "").strip()
    if not token or got != token:
        raise HTTPException(status_code=403, detail="Token inválido.")


@router.get("/status")
async def pc_status(request: Request) -> Response:
    """Estado del PC Agent (kill switch, rate limits)."""
    _verify(request)

    from src.core.pc_agent import PCAgent

    agent = PCAgent(_project_root())

    return _json_response(
        {
            "enabled": agent.cfg.get("enabled", True),
            "kill_switch": agent.cfg.get("kill_switch", False),
            "network_default": agent.cfg.get("network_policy", {}).get(
                "default", False
            ),
            "confirm_timeout": agent.cfg.get("confirm_timeout_seconds", 60),
        }
    )


@router.post("/lock")
async def pc_lock(request: Request) -> Response:
    """Activa el kill switch (bloquea PC Agent)."""
    _verify(request)

    try:
        data = await request.json()
    except:
        data = {}

    user_id = str(data.get("user_id", ""))

    from src.core.pc_agent import PCAgent

    agent = PCAgent(_project_root())

    success = agent.toggle_kill_switch(True, user_id)

    return _json_response(
        {
            "success": success,
            "message": "PC Agent BLOQUEADO (kill switch activado)"
            if success
            else "Error al bloquear",
            "kill_switch": True,
        }
    )


@router.post("/unlock")
async def pc_unlock(request: Request) -> Response:
    """Desactiva el kill switch (desbloquea PC Agent)."""
    _verify(request)

    try:
        data = await request.json()
    except:
        data = {}

    user_id = str(data.get("user_id", ""))

    from src.core.pc_agent import PCAgent

    agent = PCAgent(_project_root())

    success = agent.toggle_kill_switch(False, user_id)

    return _json_response(
        {
            "success": success,
            "message": "PC Agent DESBLOQUEADO" if success else "Error al desbloquear",
            "kill_switch": False,
        }
    )


@router.post("/fs")
async def pc_fs(request: Request) -> Response:
    _verify(request)

    try:
        data = await request.json()
    except Exception as e:
        return _json_response({"error": f"JSON inválido: {e}"}, status_code=400)

    op = (data.get("op") or "").strip()
    user_id = str(data.get("user_id", ""))

    from src.core.pc_agent import PCAgent

    agent = PCAgent(_project_root())

    # Verificar si PC Agent está habilitado
    if not agent.cfg.get("enabled", True):
        return _json_response({"error": "PC Agent deshabilitado"}, status_code=403)

    # Verificar kill switch (excepto para status/unlock)
    if op not in ("status", "unlock"):
        if agent.cfg.get("kill_switch", False):
            return _json_response(
                {
                    "error": "PC Agent está bloqueado (kill switch activado). Usa /pc unlock para desbloquear.",
                    "kill_switch": True,
                },
                status_code=403,
            )

    try:
        if op == "list":
            r = agent.list_dir(data.get("path", ""), user_id)
        elif op == "mkdir":
            r = agent.make_dir(data.get("path", ""), user_id)
        elif op == "move":
            src = data.get("src", "") or data.get("path", "")
            dst = data.get("dst", "") or data.get("dst", "")
            r = agent.move_path(src, dst, user_id)
        elif op == "copy":
            src = data.get("src", "") or data.get("path", "")
            dst = data.get("dst", "") or data.get("dst", "")
            r = agent.copy_path(src, dst, user_id)
        elif op == "delete":
            r = agent.delete_path(data.get("path", ""), user_id)
        elif op == "write_file":
            r = agent.write_file(
                data.get("path", ""),
                data.get("content", ""),
                bool(data.get("overwrite", False)),
                user_id,
            )
        elif op == "batch":
            r = agent.batch(
                data.get("steps", []),
                user_id,
            )
        elif op == "exec":
            r = agent.exec_command(data.get("cmd", ""), user_id, data.get("cwd", ""))
        elif op == "confirm":
            r = agent.confirm_and_run(
                data.get("token", ""), user_id, data.get("phrase", "")
            )
        elif op == "status":
            return _json_response(
                {
                    "enabled": agent.cfg.get("enabled", True),
                    "kill_switch": agent.cfg.get("kill_switch", False),
                    "network_default": agent.cfg.get("network_policy", {}).get(
                        "default", False
                    ),
                }
            )
        else:
            return _json_response({"error": f"op desconocida: {op}"}, status_code=400)
    except Exception as e:
        logger.exception(f"Error en PC Agent op={op}")
        return _json_response({"error": f"Error interno: {e}"}, status_code=500)

    return _json_response(
        {
            "success": r.success,
            "output": r.output,
            "requires_confirm": r.requires_confirm,
            "confirm_token": r.confirm_token,
            "confirm_phrase": r.confirm_phrase,
            "dry_run_info": r.dry_run_info,
        }
    )
