from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Dict

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import Response
from pydantic import BaseModel
from src.core.json_safe import safe_load

router = APIRouter(prefix="/api/proactive", tags=["proactive"])


def _project_root() -> Path:
    return Path(__file__).resolve().parent.parent.parent


def _internal_token() -> str:
    return (os.getenv("LILITH_INTERNAL_TOKEN", "") or "").strip()


def _require_token(request: Request) -> None:
    token = _internal_token()
    if not token:
        raise HTTPException(
            status_code=503, detail="LILITH_INTERNAL_TOKEN no está configurado."
        )
    got = (request.headers.get("X-Lilith-Token") or "").strip()
    if got != token:
        raise HTTPException(status_code=403, detail="Token inválido.")


def _cfg_path() -> Path:
    return _project_root() / "Config" / "proactive_mode.json"


def _read_cfg() -> Dict[str, Any]:
    raw = safe_load(_cfg_path(), default={})
    return raw if isinstance(raw, dict) else {}


def _write_cfg(cfg: Dict[str, Any]) -> None:
    p = _cfg_path()
    p.parent.mkdir(parents=True, exist_ok=True)
    import json

    p.write_text(json.dumps(cfg, ensure_ascii=False, indent=2), encoding="utf-8")


@router.get("/status")
async def proactive_status(request: Request) -> Response:
    _require_token(request)
    import time

    from src.core.proactive_engine import ProactiveEngine

    root = _project_root()
    cfg = _read_cfg()
    state = ProactiveEngine(root)._load_state()
    now = time.time()
    sent_this_hour = (
        len([t for t in (state.get("sent_timestamps") or []) if now - float(t) < 3600])
        if isinstance(state.get("sent_timestamps"), list)
        else 0
    )

    return Response(
        content=__import__("json").dumps(
            {
                "ok": True,
                "enabled": bool(cfg.get("enabled", True)),
                "last_run": state.get("last_run_ts"),
                "sent_this_hour": sent_this_hour,
                "max_per_hour": cfg.get("max_notifications_per_hour", 3),
                "config": cfg,
            },
            ensure_ascii=False,
        ),
        media_type="application/json",
    )


class EnableBody(BaseModel):
    enabled: bool


@router.post("/enable")
async def proactive_enable(body: EnableBody, request: Request) -> Response:
    _require_token(request)
    cfg = _read_cfg()
    cfg["enabled"] = bool(body.enabled)
    _write_cfg(cfg)

    # Best-effort: si el scheduler está vivo, recargar job
    try:
        from src.api import server as server_mod

        s = getattr(server_mod, "_task_scheduler", None)
        if s is not None and hasattr(s, "reload_proactive_mode"):
            try:
                s.reload_proactive_mode()
            except Exception:
                pass
    except Exception:
        pass

    return Response(content='{"ok": true}', media_type="application/json")


@router.post("/run_now")
async def proactive_run_now(request: Request) -> Response:
    _require_token(request)
    try:
        import asyncio

        from src.core.proactive_engine import ProactiveEngine

        asyncio.create_task(ProactiveEngine(_project_root()).run_once())
        return Response(content='{"status":"triggered"}', media_type="application/json")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
