"""Tests for YggdrasilForge — health, generation, assets, blender, render."""

import pytest


# ── Health ────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_health(client):
    response = await client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "rooted"
    assert "services" in data
    assert data["services"]["blender_mcp"]["online"] is True


# ── Generation ────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_text_to_3d_hunyuan(client):
    response = await client.post(
        "/api/generation/text-to-3d",
        json={
            "prompt": "A viking shield with runes",
            "provider": "hunyuan3d",
        },
    )
    assert response.status_code == 200
    data = response.json()
    assert data["id"]
    assert data["type"] == "text_to_3d"
    assert data["provider"] == "hunyuan3d"
    assert data["status"] == "queued"


@pytest.mark.asyncio
async def test_text_to_3d_rodin(client):
    response = await client.post(
        "/api/generation/text-to-3d",
        json={
            "prompt": "Norse rune stone",
            "provider": "rodin",
            "bbox_condition": [1.0, 0.5, 2.0],
        },
    )
    assert response.status_code == 200
    data = response.json()
    assert data["provider"] == "rodin"


@pytest.mark.asyncio
async def test_image_to_3d(client):
    response = await client.post(
        "/api/generation/image-to-3d",
        json={
            "image_url": "https://example.com/shield.jpg",
            "prompt": "A shield",
            "provider": "hunyuan3d",
        },
    )
    assert response.status_code == 200
    data = response.json()
    assert data["type"] == "image_to_3d"


@pytest.mark.asyncio
async def test_list_generations(client):
    # Create one first
    await client.post(
        "/api/generation/text-to-3d",
        json={
            "prompt": "test model",
            "provider": "hunyuan3d",
        },
    )

    response = await client.get("/api/generation/")
    assert response.status_code == 200
    data = response.json()
    assert "items" in data
    assert data["total"] >= 1


@pytest.mark.asyncio
async def test_get_generation(client):
    create = await client.post(
        "/api/generation/text-to-3d",
        json={
            "prompt": "another test",
            "provider": "rodin",
        },
    )
    gen_id = create.json()["id"]

    response = await client.get(f"/api/generation/{gen_id}")
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == gen_id


@pytest.mark.asyncio
async def test_generation_not_found(client):
    response = await client.get("/api/generation/nonexistent_id")
    assert response.status_code == 404


# ── Assets ────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_polyhaven_status(client):
    response = await client.get("/api/assets/polyhaven/status")
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_polyhaven_categories(client):
    response = await client.get("/api/assets/polyhaven/categories?asset_type=hdris")
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_polyhaven_search(client):
    response = await client.post(
        "/api/assets/polyhaven/search",
        json={
            "query": "rock",
            "source": "polyhaven",
            "asset_type": "models",
        },
    )
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_sketchfab_status(client):
    response = await client.get("/api/assets/sketchfab/status")
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_sketchfab_search(client):
    response = await client.post(
        "/api/assets/sketchfab/search",
        json={
            "query": "viking",
            "source": "sketchfab",
            "count": 5,
        },
    )
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_sketchfab_download(client):
    response = await client.post(
        "/api/assets/sketchfab/download",
        json={
            "uid": "abc123",
            "target_size": 1.0,
        },
    )
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_asset_history_empty(client):
    response = await client.get("/api/assets/history")
    assert response.status_code == 200
    # May have items from download tests
    assert "items" in response.json()


# ── Blender Bridge ─────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_blender_status(client):
    response = await client.get("/api/blender/status")
    assert response.status_code == 200
    assert response.json()["blender_mcp_online"] is True


@pytest.mark.asyncio
async def test_blender_scene(client):
    response = await client.get("/api/blender/scene")
    assert response.status_code == 200
    assert "scene" in response.json()


@pytest.mark.asyncio
async def test_blender_object(client):
    response = await client.get("/api/blender/object/Cube")
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_blender_screenshot(client):
    response = await client.get("/api/blender/screenshot")
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_blender_execute(client):
    response = await client.post(
        "/api/blender/execute", json={"code": "import bpy; print(bpy.context.scene.name)"}
    )
    assert response.status_code == 200


# ── Render ─────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_render_engines(client):
    response = await client.get("/api/render/engines")
    assert response.status_code == 200
    engines = response.json()["engines"]
    assert len(engines) >= 2


@pytest.mark.asyncio
async def test_render_scene(client):
    response = await client.post(
        "/api/render/",
        json={
            "engine": "eevee",
            "resolution_x": 640,
            "resolution_y": 480,
        },
    )
    assert response.status_code == 200
