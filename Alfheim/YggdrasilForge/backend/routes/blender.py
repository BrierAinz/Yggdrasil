"""Blender bridge routes — scene info, object info, viewport screenshots, code execution."""

from __future__ import annotations

import logging

from fastapi import APIRouter, HTTPException

from backend.blender_client import BlenderMCPError, blender_client
from backend.models import BlenderCodeRequest


router = APIRouter()
logger = logging.getLogger("forge.blender")


@router.get("/status")
async def blender_status():
    """Check if Blender MCP addon is reachable and responding."""
    online = await blender_client.health_check()
    return {"blender_mcp_online": online}


@router.get("/scene")
async def get_scene_info():
    """Get detailed information about the current Blender scene."""
    try:
        result = await blender_client.get_scene_info()
        return {"scene": result}
    except BlenderMCPError as e:
        raise HTTPException(503, f"Blender MCP error: {e.message}")


@router.get("/object/{object_name}")
async def get_object_info(object_name: str):
    """Get detailed information about a specific Blender object."""
    try:
        result = await blender_client.get_object_info(object_name)
        return {"object": result}
    except BlenderMCPError as e:
        raise HTTPException(503, f"Blender MCP error: {e.message}")


@router.get("/screenshot")
async def viewport_screenshot(max_size: int = 1000):
    """Capture a screenshot of the current Blender 3D viewport."""
    try:
        result = await blender_client.get_viewport_screenshot(max_size=max_size)
        return {"screenshot": result}
    except BlenderMCPError as e:
        raise HTTPException(503, f"Blender MCP error: {e.message}")


@router.post("/execute")
async def execute_blender_code(req: BlenderCodeRequest):
    """Execute arbitrary Python code in Blender.

    WARNING: This is extremely powerful and should be protected by auth in production.
    """
    try:
        result = await blender_client.execute_blender_code(req.code)
        return {"result": result}
    except BlenderMCPError as e:
        raise HTTPException(503, f"Blender MCP error: {e.message}")
