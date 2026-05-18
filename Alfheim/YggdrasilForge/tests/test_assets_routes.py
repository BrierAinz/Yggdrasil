"""Tests for Asset library routes — PolyHaven, Sketchfab, and local asset history."""

from unittest.mock import AsyncMock

import pytest
from backend.blender_client import BlenderMCPError


# ── PolyHaven Status ──────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_polyhaven_status_success(client):
    """PolyHaven status returns provider info."""
    response = await client.get("/api/assets/polyhaven/status")
    assert response.status_code == 200
    data = response.json()
    assert data["provider"] == "polyhaven"
    assert "result" in data


@pytest.mark.asyncio
async def test_polyhaven_status_mcp_error(client):
    """PolyHaven status returns 503 when BlenderMCPError is raised."""
    from backend.routes.assets import blender_client as bc

    bc.get_polyhaven_status = AsyncMock(side_effect=BlenderMCPError(-32001, "MCP unavailable"))

    response = await client.get("/api/assets/polyhaven/status")
    assert response.status_code == 503

    # Restore
    bc.get_polyhaven_status = AsyncMock(return_value={"enabled": True})


# ── PolyHaven Categories ──────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_polyhaven_categories_default(client):
    """Categories endpoint defaults to 'hdris' asset_type."""
    response = await client.get("/api/assets/polyhaven/categories")
    assert response.status_code == 200
    data = response.json()
    assert "categories" in data


@pytest.mark.asyncio
async def test_polyhaven_categories_with_asset_type(client):
    """Categories endpoint forwards asset_type query parameter."""
    from backend.routes.assets import blender_client as bc

    response = await client.get("/api/assets/polyhaven/categories?asset_type=textures")
    assert response.status_code == 200
    bc.get_polyhaven_categories.assert_awaited_once_with(asset_type="textures")


@pytest.mark.asyncio
async def test_polyhaven_categories_mcp_error(client):
    """Categories endpoint returns 503 when BlenderMCPError is raised."""
    from backend.routes.assets import blender_client as bc

    bc.get_polyhaven_categories = AsyncMock(side_effect=BlenderMCPError(-32001, "MCP error"))

    response = await client.get("/api/assets/polyhaven/categories?asset_type=models")
    assert response.status_code == 503

    # Restore
    bc.get_polyhaven_categories = AsyncMock(
        return_value={"categories": ["nature", "architectural"]}
    )


# ── PolyHaven Search ──────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_polyhaven_search_success(client):
    """Search PolyHaven assets returns results."""
    response = await client.post(
        "/api/assets/polyhaven/search",
        json={
            "query": "rock",
            "source": "polyhaven",
            "asset_type": "models",
        },
    )
    assert response.status_code == 200
    data = response.json()
    assert "results" in data
    assert len(data["results"]) >= 1


@pytest.mark.asyncio
async def test_polyhaven_search_with_categories(client):
    """Search PolyHaven with categories filter forwards to client."""
    from backend.routes.assets import blender_client as bc

    response = await client.post(
        "/api/assets/polyhaven/search",
        json={
            "query": "brick",
            "source": "polyhaven",
            "asset_type": "textures",
            "categories": "architectural",
        },
    )
    assert response.status_code == 200
    # Verify the categories kwarg was passed through
    call_kwargs = bc.search_polyhaven.call_args
    assert call_kwargs.kwargs.get("categories") == "architectural" or (
        len(call_kwargs.args) > 1 and "architectural" in str(call_kwargs)
    )


@pytest.mark.asyncio
async def test_polyhaven_search_short_query_rejected(client):
    """Search rejects queries shorter than min_length=2."""
    response = await client.post(
        "/api/assets/polyhaven/search",
        json={
            "query": "a",
            "source": "polyhaven",
        },
    )
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_polyhaven_search_mcp_error(client):
    """Search returns 503 when BlenderMCPError is raised."""
    from backend.routes.assets import blender_client as bc

    bc.search_polyhaven = AsyncMock(side_effect=BlenderMCPError(-32001, "Search failed"))

    response = await client.post(
        "/api/assets/polyhaven/search",
        json={
            "query": "rock",
            "source": "polyhaven",
        },
    )
    assert response.status_code == 503

    # Restore
    bc.search_polyhaven = AsyncMock(
        return_value=[
            {"name": "rock_01", "type": "models", "categories": ["nature"]},
        ]
    )


# ── PolyHaven Download ───────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_polyhaven_download_success(client):
    """Download a PolyHaven asset and record it in DB."""
    response = await client.post(
        "/api/assets/polyhaven/download",
        json={
            "asset_id": "rock_01",
            "asset_type": "models",
            "resolution": "1k",
        },
    )
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert data["asset_id"] == "ph_rock_01"


@pytest.mark.asyncio
async def test_polyhaven_download_with_format(client):
    """Download with optional file_format passes it to client."""
    from backend.routes.assets import blender_client as bc

    response = await client.post(
        "/api/assets/polyhaven/download",
        json={
            "asset_id": "kloofendal",
            "asset_type": "hdris",
            "resolution": "2k",
            "file_format": "hdr",
        },
    )
    assert response.status_code == 200
    # Verify the file_format was forwarded
    call_kwargs = bc.download_polyhaven.call_args.kwargs
    assert call_kwargs.get("file_format") == "hdr"


@pytest.mark.asyncio
async def test_polyhaven_download_mcp_error(client):
    """Download returns 503 when BlenderMCPError is raised."""
    from backend.routes.assets import blender_client as bc

    bc.download_polyhaven = AsyncMock(side_effect=BlenderMCPError(-32001, "Download failed"))

    response = await client.post(
        "/api/assets/polyhaven/download",
        json={
            "asset_id": "missing_asset",
            "asset_type": "models",
        },
    )
    assert response.status_code == 503

    # Restore
    bc.download_polyhaven = AsyncMock(return_value={"status": "ok"})


# ── PolyHaven Apply Texture ───────────────────────────────────────────────


@pytest.mark.asyncio
async def test_apply_texture_success(client):
    """Apply a previously downloaded PolyHaven texture to an object."""
    response = await client.post(
        "/api/assets/polyhaven/apply-texture",
        json={
            "object_name": "Cube",
            "texture_id": "brick_wall",
        },
    )
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"


@pytest.mark.asyncio
async def test_apply_texture_missing_fields(client):
    """Apply texture rejects missing required fields."""
    response = await client.post(
        "/api/assets/polyhaven/apply-texture",
        json={
            "object_name": "Cube",
            # missing texture_id
        },
    )
    assert response.status_code == 422


# ── Sketchfab Status ──────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_sketchfab_status_success(client):
    """Sketchfab status returns provider info."""
    response = await client.get("/api/assets/sketchfab/status")
    assert response.status_code == 200
    data = response.json()
    assert data["provider"] == "sketchfab"
    assert "result" in data


# ── Sketchfab Search ──────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_sketchfab_search_success(client):
    """Search Sketchfab models returns results."""
    response = await client.post(
        "/api/assets/sketchfab/search",
        json={
            "query": "viking",
            "source": "sketchfab",
            "count": 5,
        },
    )
    assert response.status_code == 200
    data = response.json()
    assert "results" in data


@pytest.mark.asyncio
async def test_sketchfab_search_with_categories(client):
    """Sketchfab search forwards categories filter."""
    from backend.routes.assets import blender_client as bc

    response = await client.post(
        "/api/assets/sketchfab/search",
        json={
            "query": "shield",
            "source": "sketchfab",
            "categories": "weapons",
            "count": 10,
        },
    )
    assert response.status_code == 200
    call_kwargs = bc.search_sketchfab.call_args.kwargs
    assert call_kwargs.get("categories") == "weapons"


@pytest.mark.asyncio
async def test_sketchfab_search_mcp_error(client):
    """Sketchfab search returns 503 when BlenderMCPError is raised."""
    from backend.routes.assets import blender_client as bc

    bc.search_sketchfab = AsyncMock(side_effect=BlenderMCPError(-32001, "Search error"))

    response = await client.post(
        "/api/assets/sketchfab/search",
        json={
            "query": "viking",
            "source": "sketchfab",
        },
    )
    assert response.status_code == 503

    # Restore
    bc.search_sketchfab = AsyncMock(
        return_value=[
            {
                "name": "Viking Shield",
                "uid": "abc123",
                "thumbnail": "https://example.com/thumb.jpg",
            },
        ]
    )


# ── Sketchfab Download ────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_sketchfab_download_success(client):
    """Download a Sketchfab model and record it in DB."""
    response = await client.post(
        "/api/assets/sketchfab/download",
        json={
            "uid": "abc123",
            "target_size": 1.0,
        },
    )
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert data["asset_id"] == "sf_abc123"


@pytest.mark.asyncio
async def test_sketchfab_download_mcp_error(client):
    """Sketchfab download returns 503 when BlenderMCPError is raised."""
    from backend.routes.assets import blender_client as bc

    bc.download_sketchfab = AsyncMock(side_effect=BlenderMCPError(-32001, "Download failed"))

    response = await client.post(
        "/api/assets/sketchfab/download",
        json={
            "uid": "xyz789",
            "target_size": 2.5,
        },
    )
    assert response.status_code == 503

    # Restore
    bc.download_sketchfab = AsyncMock(return_value={"status": "ok"})


# ── Sketchfab Preview ─────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_sketchfab_preview_success(client):
    """Preview a Sketchfab model by UID."""
    response = await client.get("/api/assets/sketchfab/preview/testuid")
    assert response.status_code == 200
    data = response.json()
    assert "preview" in data


@pytest.mark.asyncio
async def test_sketchfab_preview_mcp_error(client):
    """Sketchfab preview returns 503 when BlenderMCPError is raised."""
    from backend.routes.assets import blender_client as bc

    bc.preview_sketchfab = AsyncMock(side_effect=BlenderMCPError(-32001, "Preview unavailable"))

    response = await client.get("/api/assets/sketchfab/preview/baduid")
    assert response.status_code == 503

    # Restore
    bc.preview_sketchfab = AsyncMock(return_value={"preview": "data:image/png;base64,..."})


# ── Asset History ──────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_asset_history_empty(client):
    """Asset history returns empty list when no assets downloaded."""
    response = await client.get("/api/assets/history")
    assert response.status_code == 200
    data = response.json()
    assert "items" in data
    assert "total" in data


@pytest.mark.asyncio
async def test_asset_history_after_download(client):
    """Asset history lists assets after a PolyHaven download."""
    await client.post(
        "/api/assets/polyhaven/download",
        json={
            "asset_id": "history_test_rock",
            "asset_type": "models",
            "resolution": "1k",
        },
    )

    response = await client.get("/api/assets/history")
    assert response.status_code == 200
    data = response.json()
    assert data["total"] >= 1


@pytest.mark.asyncio
async def test_asset_history_filter_by_provider(client):
    """Asset history can be filtered by provider."""
    response = await client.get("/api/assets/history?provider=polyhaven")
    assert response.status_code == 200
    data = response.json()
    assert "items" in data


@pytest.mark.asyncio
async def test_asset_get_by_id(client):
    """Get a specific asset by its ID from history."""
    # First download to create the asset in DB
    dl = await client.post(
        "/api/assets/polyhaven/download",
        json={
            "asset_id": "detail_rock",
            "asset_type": "models",
        },
    )
    asset_id = dl.json()["asset_id"]

    response = await client.get(f"/api/assets/history/{asset_id}")
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == asset_id


@pytest.mark.asyncio
async def test_asset_get_not_found(client):
    """Get a nonexistent asset returns 404."""
    response = await client.get("/api/assets/history/nonexistent_id")
    assert response.status_code == 404
