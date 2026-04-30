from __future__ import annotations

import os
from typing import Any, Dict, Optional

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import Response
from pydantic import BaseModel, field_validator

router = APIRouter(prefix="/api/scheduler", tags=["scheduler"])


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


def _get_scheduler():
    # Evitar imports circulares fuertes; server.py mantiene el global
    from src.api import server as server_mod

    s = getattr(server_mod, "_task_scheduler", None)
    if s is not None:
        return s
    # Lazy init (útil para TestClient sin lifespan)
    try:
        from pathlib import Path

        from src.core.task_scheduler import TaskScheduler

        root = Path(__file__).resolve().parent.parent.parent
        s = TaskScheduler(root)
        s.start()
        setattr(server_mod, "_task_scheduler", s)
        return s
    except Exception:
        return None


class JobActionRequest(BaseModel):
    job_id: str

    @field_validator("job_id")
    @classmethod
    def _job_id(cls, v: str) -> str:
        v = (v or "").strip()
        if not v:
            raise ValueError("job_id requerido")
        return v[:200]


@router.get("/jobs")
async def list_jobs(request: Request) -> Response:
    """Lista jobs cargados (tareas cron + monitores interval)."""
    _require_token(request)
    s = _get_scheduler()
    if not s:
        return Response(
            content='{"jobs": [], "count": 0, "error": "scheduler_not_initialized"}',
            media_type="application/json",
        )
    data = s.list_jobs()
    return Response(content=data, media_type="application/json")


@router.post("/pause")
async def pause_job(payload: JobActionRequest, request: Request) -> Response:
    _require_token(request)
    s = _get_scheduler()
    if not s:
        raise HTTPException(status_code=503, detail="scheduler_not_initialized")
    ok = s.pause_job(payload.job_id)
    return Response(
        content=f'{{"ok": {str(bool(ok)).lower()}, "job_id": "{payload.job_id}"}}',
        media_type="application/json",
    )


@router.post("/resume")
async def resume_job(payload: JobActionRequest, request: Request) -> Response:
    _require_token(request)
    s = _get_scheduler()
    if not s:
        raise HTTPException(status_code=503, detail="scheduler_not_initialized")
    ok = s.resume_job(payload.job_id)
    return Response(
        content=f'{{"ok": {str(bool(ok)).lower()}, "job_id": "{payload.job_id}"}}',
        media_type="application/json",
    )


@router.post("/run_now")
async def run_now(payload: JobActionRequest, request: Request) -> Response:
    _require_token(request)
    s = _get_scheduler()
    if not s:
        raise HTTPException(status_code=503, detail="scheduler_not_initialized")
    ok = s.run_now(payload.job_id)
    return Response(
        content=f'{{"ok": {str(bool(ok)).lower()}, "job_id": "{payload.job_id}"}}',
        media_type="application/json",
    )
