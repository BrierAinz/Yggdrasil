"""
Lilith 4.1 — A.3 Backups API.
Endpoints (owner): list, create, verify, restore snapshots.
"""
import logging
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel

logger = logging.getLogger("lilith.api.backups")

router = APIRouter(prefix="/api/backups", tags=["backups"])
_BASE_PATH = Path(__file__).resolve().parent.parent.parent


def _get_manager():
    from src.core.backup_manager import BackupManager

    return BackupManager(_BASE_PATH)


class RestoreRequest(BaseModel):
    snapshot_name: str
    dry_run: bool = False


@router.get("/list")
async def list_snapshots():
    """Lista snapshots disponibles."""
    mgr = _get_manager()
    return {"snapshots": mgr.list_snapshots()}


@router.post("/create")
async def create_snapshot():
    """Crea un snapshot manual inmediatamente."""
    import asyncio

    mgr = _get_manager()
    result = await asyncio.to_thread(mgr.create_snapshot)
    if not result.get("ok"):
        raise HTTPException(status_code=500, detail=result.get("reason", "Error"))
    return result


@router.post("/verify/{snapshot_name}")
async def verify_snapshot(snapshot_name: str):
    """Verifica integridad de un snapshot."""
    import asyncio

    mgr = _get_manager()
    backup_dir = mgr._backup_dir()
    path = backup_dir / snapshot_name
    if not path.exists():
        raise HTTPException(
            status_code=404, detail=f"Snapshot no encontrado: {snapshot_name}"
        )
    ok, msg = await asyncio.to_thread(mgr.verify_snapshot, path)
    return {"ok": ok, "message": msg}


@router.post("/restore")
async def restore_snapshot(req: RestoreRequest):
    """
    Restaura un snapshot. Si dry_run=True, solo verifica sin modificar archivos.
    ⚠️ Requiere confirmación previa del owner.
    """
    import asyncio

    mgr = _get_manager()
    backup_dir = mgr._backup_dir()
    path = backup_dir / req.snapshot_name
    if not path.exists():
        raise HTTPException(
            status_code=404, detail=f"Snapshot no encontrado: {req.snapshot_name}"
        )
    result = await asyncio.to_thread(mgr.restore_snapshot, path, req.dry_run)
    if not result.get("ok"):
        raise HTTPException(status_code=500, detail=result.get("reason", "Error"))
    return result


@router.get("/verify-all")
async def verify_all():
    """Verifica integridad de todos los snapshots."""
    import asyncio

    mgr = _get_manager()
    result = await asyncio.to_thread(mgr.verify_all_snapshots)
    return result
