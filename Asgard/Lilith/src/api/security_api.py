from __future__ import annotations

import os
import shutil
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, Optional

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, field_validator

from ..core.security_guard import SecurityGuard

router = APIRouter(prefix="/api/security", tags=["security"])


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


class GrantTempScopeRequest(BaseModel):
    agent: str
    operation: str
    target_path: str
    ttl_seconds: int = 3600

    @field_validator("agent")
    @classmethod
    def _agent(cls, v: str) -> str:
        v = (v or "").strip().lower()
        if v not in ("adan", "eva", "lucifer", "odin", "owner"):
            raise ValueError("agent inválido")
        return v

    @field_validator("operation")
    @classmethod
    def _op(cls, v: str) -> str:
        v = (v or "").strip().lower()
        if v not in ("read", "list", "edit", "write", "delete"):
            raise ValueError("operation inválida")
        return v

    @field_validator("ttl_seconds")
    @classmethod
    def _ttl(cls, v: int) -> int:
        try:
            v = int(v)
        except Exception:
            v = 3600
        return max(60, min(24 * 3600, v))

    @field_validator("target_path")
    @classmethod
    def _path(cls, v: str) -> str:
        v = (v or "").strip()
        if not v:
            raise ValueError("target_path requerido")
        return v


@router.post("/grant_temp_scope")
async def grant_temp_scope(
    payload: GrantTempScopeRequest, request: Request
) -> Dict[str, Any]:
    """
    Otorga un allow temporal (TTL) sin modificar agent_scopes.json.
    Importante: NO puede anular denies explícitos permanentes (deny-overrides).
    """
    _require_token(request)
    root = _project_root()
    guard = SecurityGuard(root)
    grant = guard.grant_temp_scope(
        agent=payload.agent,
        op=payload.operation,
        target_path=payload.target_path,
        ttl_seconds=payload.ttl_seconds,
    )
    if not grant.get("ok"):
        raise HTTPException(
            status_code=400,
            detail=grant.get("error") or "No se pudo otorgar scope temporal.",
        )
    return grant


class MoveToScratchRequest(BaseModel):
    source_path: str
    dest_name: Optional[str] = None

    @field_validator("source_path")
    @classmethod
    def _src(cls, v: str) -> str:
        v = (v or "").strip()
        if not v:
            raise ValueError("source_path requerido")
        return v

    @field_validator("dest_name")
    @classmethod
    def _dest(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return None
        vv = (v or "").strip()
        if not vv:
            return None
        # Solo nombre de archivo (sin directorios)
        return Path(vv).name


@router.post("/move_to_scratch")
async def move_to_scratch(
    payload: MoveToScratchRequest, request: Request
) -> Dict[str, Any]:
    """
    Copia un archivo a Core/scratch/ como acción privilegiada del Owner.
    """
    _require_token(request)
    root = _project_root()
    base = root
    src_abs = (base / payload.source_path).expanduser().resolve(strict=False)
    # Fail-closed: no permitir salir de Core/
    try:
        src_abs.relative_to(base.resolve())
    except Exception:
        raise HTTPException(status_code=400, detail="source_path fuera del proyecto.")
    if not src_abs.exists() or not src_abs.is_file():
        raise HTTPException(status_code=404, detail="Archivo no encontrado.")

    scratch_dir = base / "scratch"
    scratch_dir.mkdir(parents=True, exist_ok=True)
    dest_name = payload.dest_name or src_abs.name
    dest_abs = (scratch_dir / Path(dest_name).name).resolve(strict=False)
    shutil.copy2(str(src_abs), str(dest_abs))

    try:
        rel = dest_abs.relative_to(base.resolve()).as_posix()
    except Exception:
        rel = f"scratch/{dest_abs.name}"
    return {"ok": True, "new_path": rel, "file": dest_abs.name}
