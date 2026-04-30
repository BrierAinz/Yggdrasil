"""
Lilith 4.1 — E.13 Plugin Management API.
Endpoints (solo owner): list, load, reload, unload plugins.
"""
import logging
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

logger = logging.getLogger("lilith.api.plugins")

router = APIRouter(prefix="/api/plugins", tags=["plugins"])

_BASE_PATH = Path(__file__).resolve().parent.parent.parent


def _get_manager():
    from src.core.plugin_manager import get_plugin_manager

    return get_plugin_manager(_BASE_PATH)


# ── Pydantic models ───────────────────────────────────────────────────────────


class PluginLoadRequest(BaseModel):
    name: str
    path: Optional[str] = None


class PluginNameRequest(BaseModel):
    name: str


# ── Endpoints ─────────────────────────────────────────────────────────────────


@router.get("/list")
async def list_plugins():
    """Lista todos los plugins activos con estado y metadata."""
    try:
        manager = _get_manager()
        plugins = manager.list_plugins()
        cfg = manager._load_config()
        registered = cfg.get("plugins", {})
        # Añadir plugins inactivos (registrados pero no cargados)
        inactive = []
        for pname, pdata in registered.items():
            if not manager.is_loaded(pname):
                inactive.append(
                    {
                        "name": pname,
                        "version": pdata.get("version", "?"),
                        "description": pdata.get("description", ""),
                        "status": "inactive",
                        "tools": [],
                        "personas": [],
                    }
                )
        return {"plugins": plugins + inactive, "total": len(plugins) + len(inactive)}
    except Exception as e:
        logger.error("[PluginsAPI] list error: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/load")
async def load_plugin(req: PluginLoadRequest):
    """Carga un plugin por nombre (y path opcional)."""
    try:
        manager = _get_manager()
        path = Path(req.path) if req.path else None
        ok, msg = manager.load_plugin(req.name, path)
        if not ok:
            raise HTTPException(status_code=400, detail=msg)
        return {"success": True, "message": msg}
    except HTTPException:
        raise
    except Exception as e:
        logger.error("[PluginsAPI] load error: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/reload")
async def reload_plugin(req: PluginNameRequest):
    """Hot-reload de un plugin sin reiniciar Lilith."""
    try:
        manager = _get_manager()
        ok, msg = manager.reload_plugin(req.name)
        if not ok:
            raise HTTPException(status_code=400, detail=msg)
        logger.info("[PluginsAPI] Plugin '%s' reloaded.", req.name)
        return {"success": True, "message": msg}
    except HTTPException:
        raise
    except Exception as e:
        logger.error("[PluginsAPI] reload error: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/unload")
async def unload_plugin(req: PluginNameRequest):
    """Descarga un plugin limpiando sus registros."""
    try:
        manager = _get_manager()
        ok, msg = manager.unload_plugin(req.name)
        if not ok:
            raise HTTPException(status_code=400, detail=msg)
        return {"success": True, "message": msg}
    except HTTPException:
        raise
    except Exception as e:
        logger.error("[PluginsAPI] unload error: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/status/{plugin_name}")
async def plugin_status(plugin_name: str):
    """Estado detallado de un plugin específico."""
    try:
        manager = _get_manager()
        loaded = manager.is_loaded(plugin_name)
        instance = manager.get_plugin(plugin_name)
        cfg = manager._load_config()
        reg = cfg.get("plugins", {}).get(plugin_name, {})
        return {
            "name": plugin_name,
            "loaded": loaded,
            "version": getattr(instance, "version", reg.get("version", "?")),
            "description": getattr(instance, "description", reg.get("description", "")),
            "path": reg.get("path", ""),
            "tools": manager._registered_tools.get(plugin_name, []),
            "personas": manager._registered_personas.get(plugin_name, []),
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
