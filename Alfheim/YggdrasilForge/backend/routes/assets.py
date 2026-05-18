"""Asset routes — PolyHaven search/download + Sketchfab search/download + texture apply."""

from __future__ import annotations

import logging

from fastapi import APIRouter, HTTPException

from backend import database as db
from backend.blender_client import BlenderMCPError, blender_client
from backend.models import (
    AIProvider,
    AssetSearchRequest,
    AssetType,
    PolyHavenDownloadRequest,
    SketchfabDownloadRequest,
    TextureApplyRequest,
)


router = APIRouter()
logger = logging.getLogger("forge.assets")


# ── PolyHaven ─────────────────────────────────────────────────────────────


@router.get("/polyhaven/status")
async def polyhaven_status():
    """Check if PolyHaven integration is enabled in Blender."""
    try:
        result = await blender_client.get_polyhaven_status()
        return {"provider": "polyhaven", "result": result}
    except BlenderMCPError as e:
        raise HTTPException(503, f"Blender MCP error: {e.message}")


@router.get("/polyhaven/categories")
async def polyhaven_categories(asset_type: str = "hdris"):
    """Get categories for a specific asset type on PolyHaven."""
    try:
        result = await blender_client.get_polyhaven_categories(asset_type=asset_type)
        return {"categories": result}
    except BlenderMCPError as e:
        raise HTTPException(503, f"Blender MCP error: {e.message}")


@router.post("/polyhaven/search")
async def search_polyhaven(req: AssetSearchRequest):
    """Search PolyHaven assets with optional filtering."""
    try:
        result = await blender_client.search_polyhaven(
            asset_type=req.asset_type or "all",
            categories=req.categories,
        )
        return {"results": result}
    except BlenderMCPError as e:
        raise HTTPException(503, f"Blender MCP error: {e.message}")


@router.post("/polyhaven/download")
async def download_polyhaven(req: PolyHavenDownloadRequest):
    """Download and optionally import a PolyHaven asset."""
    try:
        result = await blender_client.download_polyhaven(
            asset_id=req.asset_id,
            asset_type=req.asset_type,
            resolution=req.resolution,
            file_format=req.file_format,
        )

        # Save to local DB
        asset_id = f"ph_{req.asset_id}"
        await db.create_asset(
            id=asset_id,
            name=req.asset_id,
            provider=AIProvider.POLYHAVEN.value,
            asset_type=AssetType.TEXTURE.value
            if req.asset_type == "textures"
            else AssetType.MODEL.value,
            source_id=req.asset_id,
        )

        return {"status": "ok", "asset_id": asset_id, "result": result}
    except BlenderMCPError as e:
        raise HTTPException(503, f"Blender MCP error: {e.message}")


@router.post("/polyhaven/apply-texture")
async def apply_texture(req: TextureApplyRequest):
    """Apply a previously downloaded PolyHaven texture to a Blender object."""
    try:
        result = await blender_client.set_texture(
            object_name=req.object_name,
            texture_id=req.texture_id,
        )
        return {"status": "ok", "result": result}
    except BlenderMCPError as e:
        raise HTTPException(503, f"Blender MCP error: {e.message}")


# ── Sketchfab ──────────────────────────────────────────────────────────────


@router.get("/sketchfab/status")
async def sketchfab_status():
    """Check if Sketchfab integration is enabled in Blender."""
    try:
        result = await blender_client.get_sketchfab_status()
        return {"provider": "sketchfab", "result": result}
    except BlenderMCPError as e:
        raise HTTPException(503, f"Blender MCP error: {e.message}")


@router.post("/sketchfab/search")
async def search_sketchfab(req: AssetSearchRequest):
    """Search Sketchfab models with optional filtering."""
    try:
        result = await blender_client.search_sketchfab(
            query=req.query,
            categories=req.categories,
            count=req.count,
        )
        return {"results": result}
    except BlenderMCPError as e:
        raise HTTPException(503, f"Blender MCP error: {e.message}")


@router.post("/sketchfab/download")
async def download_sketchfab(req: SketchfabDownloadRequest):
    """Download and import a Sketchfab model into Blender."""
    try:
        result = await blender_client.download_sketchfab(
            uid=req.uid,
            target_size=req.target_size,
        )

        # Save to local DB
        asset_id = f"sf_{req.uid}"
        await db.create_asset(
            id=asset_id,
            name=f"sketchfab_{req.uid}",
            provider=AIProvider.SKETCHFAB.value,
            asset_type=AssetType.MODEL.value,
            source_id=req.uid,
        )

        return {"status": "ok", "asset_id": asset_id, "result": result}
    except BlenderMCPError as e:
        raise HTTPException(503, f"Blender MCP error: {e.message}")


@router.get("/sketchfab/preview/{uid}")
async def preview_sketchfab(uid: str):
    """Get a preview thumbnail of a Sketchfab model."""
    try:
        result = await blender_client.preview_sketchfab(uid)
        return {"preview": result}
    except BlenderMCPError as e:
        raise HTTPException(503, f"Blender MCP error: {e.message}")


# ── Local Asset History ───────────────────────────────────────────────────


@router.get("/history")
async def list_assets(
    provider: str | None = None,
    asset_type: str | None = None,
    limit: int = 50,
    offset: int = 0,
):
    """List locally cached/downloaded asset history."""
    items, total = await db.list_assets(
        provider=provider, asset_type=asset_type, limit=limit, offset=offset
    )
    return {"items": items, "total": total, "offset": offset, "limit": limit}


@router.get("/history/{asset_id}")
async def get_asset(asset_id: str):
    """Get details of a locally cached asset."""
    asset = await db.get_asset(asset_id)
    if not asset:
        raise HTTPException(404, f"Asset {asset_id} not found")
    return asset
