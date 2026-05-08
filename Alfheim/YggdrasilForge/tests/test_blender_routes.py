"""Tests for Blender MCP bridge routes — status, scene, object, screenshot, execute."""

import pytest
from unittest.mock import AsyncMock

from backend.blender_client import BlenderMCPError


# ── /api/blender/status ───────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_blender_status_online(client):
    """Status returns online=True when health_check succeeds."""
    response = await client.get("/api/blender/status")
    assert response.status_code == 200
    data = response.json()
    assert data["blender_mcp_online"] is True


@pytest.mark.asyncio
async def test_blender_status_offline(client):
    """Status returns online=False when health_check fails."""
    # Reach into the patched mock to override the return value
    from backend.routes.blender import blender_client as bc

    bc.health_check = AsyncMock(return_value=False)

    response = await client.get("/api/blender/status")
    assert response.status_code == 200
    data = response.json()
    assert data["blender_mcp_online"] is False

    # Restore for other tests
    bc.health_check = AsyncMock(return_value=True)


# ── /api/blender/scene ────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_blender_scene_success(client):
    """Scene endpoint returns scene info from Blender MCP."""
    response = await client.get("/api/blender/scene")
    assert response.status_code == 200
    data = response.json()
    assert "scene" in data
    scene = data["scene"]
    assert scene["scene"]["name"] == "TestScene"
    assert "Cube" in scene["scene"]["objects"]


@pytest.mark.asyncio
async def test_blender_scene_mcp_error(client):
    """Scene endpoint returns 503 when BlenderMCPError is raised."""
    from backend.routes.blender import blender_client as bc

    bc.get_scene_info = AsyncMock(side_effect=BlenderMCPError(-32001, "Connection lost"))

    response = await client.get("/api/blender/scene")
    assert response.status_code == 503
    assert "Blender MCP error" in response.json()["detail"]

    # Restore
    bc.get_scene_info = AsyncMock(
        return_value={
            "scene": {
                "name": "TestScene",
                "objects": ["Cube", "Light", "Camera"],
                "renderer": "BLENDER_EEVEE_NEXT",
            }
        }
    )


# ── /api/blender/object/{object_name} ────────────────────────────────────


@pytest.mark.asyncio
async def test_blender_object_success(client):
    """Object endpoint returns object info for a valid name."""
    response = await client.get("/api/blender/object/Cube")
    assert response.status_code == 200
    data = response.json()
    assert "object" in data
    assert data["object"]["name"] == "Cube"


@pytest.mark.asyncio
async def test_blender_object_with_special_chars(client):
    """Object endpoint handles names with special characters via URL encoding."""
    from backend.routes.blender import blender_client as bc

    bc.get_object_info = AsyncMock(return_value={"name": "Cube.001", "type": "MESH"})

    response = await client.get("/api/blender/object/Cube.001")
    assert response.status_code == 200
    data = response.json()
    assert data["object"]["name"] == "Cube.001"


@pytest.mark.asyncio
async def test_blender_object_mcp_error(client):
    """Object endpoint returns 503 when BlenderMCPError is raised."""
    from backend.routes.blender import blender_client as bc

    bc.get_object_info = AsyncMock(
        side_effect=BlenderMCPError(-32001, "Object not found in Blender")
    )

    response = await client.get("/api/blender/object/NonExistent")
    assert response.status_code == 503
    assert "Blender MCP error" in response.json()["detail"]

    # Restore
    bc.get_object_info = AsyncMock(return_value={"name": "Cube", "type": "MESH"})


# ── /api/blender/screenshot ───────────────────────────────────────────────


@pytest.mark.asyncio
async def test_blender_screenshot_default(client):
    """Screenshot endpoint works with default max_size."""
    response = await client.get("/api/blender/screenshot")
    assert response.status_code == 200
    data = response.json()
    assert "screenshot" in data


@pytest.mark.asyncio
async def test_blender_screenshot_custom_size(client):
    """Screenshot endpoint accepts max_size query parameter."""
    from backend.routes.blender import blender_client as bc

    # Spy on the call to verify the argument is forwarded
    bc.get_viewport_screenshot = AsyncMock(return_value={"screenshot": "data:image/png;base64,..."})

    response = await client.get("/api/blender/screenshot?max_size=500")
    assert response.status_code == 200
    bc.get_viewport_screenshot.assert_awaited_once_with(max_size=500)

    # Restore
    bc.get_viewport_screenshot = AsyncMock(return_value={"screenshot": "data:image/png;base64,..."})


@pytest.mark.asyncio
async def test_blender_screenshot_mcp_error(client):
    """Screenshot endpoint returns 503 when BlenderMCPError is raised."""
    from backend.routes.blender import blender_client as bc

    bc.get_viewport_screenshot = AsyncMock(
        side_effect=BlenderMCPError(-32002, "Viewport capture failed")
    )

    response = await client.get("/api/blender/screenshot")
    assert response.status_code == 503
    assert "Blender MCP error" in response.json()["detail"]

    # Restore
    bc.get_viewport_screenshot = AsyncMock(return_value={"screenshot": "data:image/png;base64,..."})


# ── /api/blender/execute ──────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_blender_execute_success(client):
    """Execute endpoint runs Python code in Blender and returns result."""
    response = await client.post(
        "/api/blender/execute", json={"code": "import bpy; print(bpy.context.scene.name)"}
    )
    assert response.status_code == 200
    data = response.json()
    assert "result" in data


@pytest.mark.asyncio
async def test_blender_execute_empty_code_rejected(client):
    """Execute endpoint rejects empty code string (min_length=1 in model)."""
    response = await client.post("/api/blender/execute", json={"code": ""})
    assert response.status_code == 422  # Pydantic validation error


@pytest.mark.asyncio
async def test_blender_execute_missing_body(client):
    """Execute endpoint rejects request with no JSON body."""
    response = await client.post("/api/blender/execute")
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_blender_execute_mcp_error(client):
    """Execute endpoint returns 503 when BlenderMCPError is raised."""
    from backend.routes.blender import blender_client as bc

    bc.execute_blender_code = AsyncMock(
        side_effect=BlenderMCPError(-32001, "Script execution failed")
    )

    response = await client.post(
        "/api/blender/execute", json={"code": "raise RuntimeError('boom')"}
    )
    assert response.status_code == 503
    assert "Blender MCP error" in response.json()["detail"]

    # Restore
    bc.execute_blender_code = AsyncMock(return_value={"result": "ok"})
