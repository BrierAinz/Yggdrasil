"""Render routes — Eevee and Cycles rendering via Blender."""

from __future__ import annotations

import logging

from fastapi import APIRouter, HTTPException

from backend.blender_client import BlenderMCPError, blender_client
from backend.models import RenderEngine, RenderRequest


router = APIRouter()
logger = logging.getLogger("forge.render")


# Blender Python code templates for rendering

RENDER_CODE_TEMPLATE = """
import bpy

# Set render engine
engine_name = {engine!r}
bpy.context.scene.render.engine = engine_name

# Set resolution
bpy.context.scene.render.resolution_x = {res_x}
bpy.context.scene.render.resolution_y = {res_y}

# Set output path
output_path = {output_path!r}
if output_path:
    bpy.context.scene.render.filepath = output_path

# Render
bpy.ops.render.render(write_still=bool(output_path))

result = {{
    "engine": engine_name,
    "resolution": [{res_x}, {res_y}],
    "output_path": output_path,
    "status": "completed"
}}
result
"""

SCREENSHOT_CODE_TEMPLATE = """
import bpy
import os

# Save viewport screenshot to temp path
screenshot_path = {output_path!r}
bpy.ops.screen.screenshot(filepath=screenshot_path)

result = {{"screenshot_path": screenshot_path, "status": "ok"}}
result
"""


@router.post("/")
async def render_scene(req: RenderRequest):
    """Render the current Blender scene with Eevee or Cycles.

    This executes render code in Blender via the MCP execute endpoint.
    """
    try:
        # Determine engine name in Blender
        engine_map = {
            RenderEngine.EEVEE: "BLENDER_EEVEE_NEXT",
            RenderEngine.CYCLES: "CYCLES",
        }
        engine_name = engine_map.get(req.engine, "BLENDER_EEVEE_NEXT")

        # Default output path
        output_path = req.output_path or "/tmp/forge_render.png"

        code = RENDER_CODE_TEMPLATE.format(
            engine=engine_name,
            res_x=req.resolution_x,
            res_y=req.resolution_y,
            output_path=output_path,
        )

        result = await blender_client.execute_blender_code(code)
        return {"status": "rendered", "engine": engine_name, "result": result}

    except BlenderMCPError as e:
        raise HTTPException(503, f"Blender MCP error: {e.message}")


@router.post("/screenshot")
async def render_screenshot(max_size: int = 1920):
    """Take a viewport screenshot via Blender code (alternative to MCP screenshot)."""
    try:
        output_path = "/tmp/forge_screenshot.png"
        code = SCREENSHOT_CODE_TEMPLATE.format(output_path=output_path)
        result = await blender_client.execute_blender_code(code)
        return {"status": "ok", "path": output_path, "result": result}
    except BlenderMCPError as e:
        raise HTTPException(503, f"Blender MCP error: {e.message}")


@router.get("/engines")
async def list_render_engines():
    """List available render engines."""
    return {
        "engines": [
            {"id": "eevee", "name": "Eevee Next", "description": "Fast real-time rendering"},
            {"id": "cycles", "name": "Cycles", "description": "Path-tracing production rendering"},
        ],
    }
