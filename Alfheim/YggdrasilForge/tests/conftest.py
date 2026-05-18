"""Pytest configuration — shared fixtures and Blender MCP mock."""

# Set test environment before importing app
import os
from unittest.mock import AsyncMock, patch

import pytest_asyncio
from httpx import ASGITransport, AsyncClient


os.environ["BLENDER_MCP_URL"] = "http://mock:9999"
os.environ["DB_PATH"] = "/tmp/forge_test.db"
os.environ["DATA_DIR"] = "/tmp/forge_test_data"

# ── Mock Blender MCP responses ────────────────────────────────────────────

MOCK_SCENE_INFO = {
    "scene": {
        "name": "TestScene",
        "objects": ["Cube", "Light", "Camera"],
        "renderer": "BLENDER_EEVEE_NEXT",
    }
}

MOCK_HUNYUAN_RESPONSE = {
    "job_id": "job_test123",
    "status": "RUN",
}

MOCK_HUNYUAN_DONE = {
    "status": "DONE",
    "ResultFile3Ds": "https://example.com/model.zip",
}

MOCK_RODIN_RESPONSE = {
    "subscription_key": "rodin_test_key",
    "request_id": "req_test_456",
    "status": "processing",
}

MOCK_POLYHAVEN_SEARCH = [
    {"name": "rock_01", "type": "models", "categories": ["nature"]},
    {"name": "brick_wall", "type": "textures", "categories": ["architectural"]},
]

MOCK_SKETCHFAB_SEARCH = [
    {"name": "Viking Shield", "uid": "abc123", "thumbnail": "https://example.com/thumb.jpg"},
]


# ── Build a one-stop mock client ──────────────────────────────────────────


def _make_mock_client() -> AsyncMock:
    """Create a fully mocked BlenderMCPClient."""
    c = AsyncMock()
    c.health_check = AsyncMock(return_value=True)
    c.get_scene_info = AsyncMock(return_value=MOCK_SCENE_INFO)
    c.get_object_info = AsyncMock(return_value={"name": "Cube", "type": "MESH"})
    c.get_viewport_screenshot = AsyncMock(return_value={"screenshot": "data:image/png;base64,..."})
    c.generate_hunyuan3d = AsyncMock(return_value=MOCK_HUNYUAN_RESPONSE)
    c.poll_hunyuan_status = AsyncMock(return_value=MOCK_HUNYUAN_DONE)
    c.import_hunyuan_asset = AsyncMock(return_value={"name": "forge_test", "status": "ok"})
    c.generate_rodin_text = AsyncMock(return_value=MOCK_RODIN_RESPONSE)
    c.generate_rodin_image = AsyncMock(return_value=MOCK_RODIN_RESPONSE)
    c.poll_rodin_status = AsyncMock(return_value={"status": "Done"})
    c.import_rodin_asset = AsyncMock(return_value={"name": "forge_rodin_test", "status": "ok"})
    c.search_polyhaven = AsyncMock(return_value=MOCK_POLYHAVEN_SEARCH)
    c.download_polyhaven = AsyncMock(return_value={"status": "ok"})
    c.set_texture = AsyncMock(return_value={"status": "ok"})
    c.search_sketchfab = AsyncMock(return_value=MOCK_SKETCHFAB_SEARCH)
    c.download_sketchfab = AsyncMock(return_value={"status": "ok"})
    c.preview_sketchfab = AsyncMock(return_value={"preview": "data:image/png;base64,..."})
    c.execute_blender_code = AsyncMock(return_value={"result": "ok"})
    c.get_polyhaven_status = AsyncMock(return_value={"enabled": True})
    c.get_sketchfab_status = AsyncMock(return_value={"enabled": True})
    c.get_polyhaven_categories = AsyncMock(return_value={"categories": ["nature", "architectural"]})
    c.get_hunyuan3d_status = AsyncMock(return_value={"enabled": True})
    c.get_hyper3d_status = AsyncMock(return_value={"enabled": True})
    return c


# ── Fixture ───────────────────────────────────────────────────────────────


@pytest_asyncio.fixture
async def client():
    """Async test client with mocked Blender MCP."""
    from backend.database import close_db, init_db

    mock_client = _make_mock_client()

    # Patch the singleton in blender_client module AND all route modules
    # that import it at module level.
    patch_targets = [
        "backend.blender_client.blender_client",
        "backend.routes.generation.blender_client",
        "backend.routes.assets.blender_client",
        "backend.routes.blender.blender_client",
        "backend.routes.render.blender_client",
    ]
    patches = [patch(t, mock_client) for t in patch_targets]
    for p in patches:
        p.start()

    # main.py imports inside lifespan(), so it picks up the patched module-level one
    from backend.main import app

    await init_db("/tmp/forge_test.db")
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
    await close_db()

    for p in patches:
        p.stop()

    # Cleanup
    if os.path.exists("/tmp/forge_test.db"):
        os.remove("/tmp/forge_test.db")
