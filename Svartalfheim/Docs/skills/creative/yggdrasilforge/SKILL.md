---
name: yggdrasilforge
description: >
  YggdrasilForge — Viking 3D Asset Studio. FastAPI backend + React frontend
  that connects to Blender via MCP for AI-powered 3D generation (Hunyuan3D,
  Hyper3D Rodin), asset browsing (PolyHaven, Sketchfab), texturing, and rendering.
  The 3D counterpart to YggdrasilStudio (2D/image generation).
version: 0.1.0
tags: [3d, blender, mcp, forge, yggdrasil, alfheim]
trigger: >
  When working on YggdrasilForge, 3D asset generation, Blender MCP integration,
  PolyHaven/Sketchfab asset browsing, or any task related to Alfheim/YggdrasilForge/.
---

# YggdrasilForge — Viking 3D Asset Studio

## Architecture

```
YggdrasilForge (3D)           YggdrasilStudio (2D)
FastAPI :8081                  FastAPI :8080
Blender MCP :9897              ComfyUI :8188
React+Vite :5174               React+Vite :5173
```

**Location:** `Alfheim/YggdrasilForge/`
**Plan:** `Svartalfheim/plans/plan-20-yggdrasilforge.md`

## Blender MCP Connection

- Blender MCP addon runs on port **9897** (NOT the default 9876)
- On WSL2, cannot reach Windows `127.0.0.1` — must set addon host to `0.0.0.0` in Blender preferences, then use Windows IP or `localhost`
- Backend `blender_client.py` communicates via HTTP JSON-RPC to Blender MCP
- If direct MCP calls fail, fall back to using Hermes as MCP proxy

## Free Services (No API Keys)

| Service | Type | MCP Tool | Notes |
|---------|------|----------|-------|
| Hunyuan3D | Text/Image → 3D | `generate_hunyuan3d_model`, `poll_hunyuan_job_status`, `import_generated_asset_hunyuan` | Free, rate-limited. Returns job_id, poll until DONE, then import with zip_file_url |
| Hyper3D Rodin | Text/Image → 3D | `generate_hyper3d_model_via_text`, `generate_hyper3d_model_via_images`, `poll_rodin_job_status`, `import_generated_asset` | Free trial (MAIN_SITE mode). Returns subscription_key, poll until Done |
| PolyHaven | HDRIs, Textures, Models | `search_polyhaven_assets`, `download_polyhaven_asset`, `set_texture`, `get_polyhaven_categories` | CC0, fully free. Resolution options: 1k, 2k, 4k |
| Sketchfab | Search/Download Models | `search_sketchfab_models`, `download_sketchfab_model`, `get_sketchfab_model_preview`, `get_sketchfab_status` | Logged in as gameoverhf12. Filter downloadable=True |

## Generation Flow (Text-to-3D)

1. User submits prompt + provider (Hunyuan3D or Rodin) via frontend
2. Backend creates generation record (status=queued) in SQLite
3. Background task calls `blender_client.generate_hunyuan3d(prompt)` or `generate_rodin_text(prompt)`
4. Gets `job_id` back, updates record (status=processing)
5. Poll loop checks status every 5s via `poll_hunyuan_status` or `poll_rodin_status`
6. On DONE: calls `import_hunyuan_asset(name, zip_url)` or `import_rodin_asset(name, task_uuid)`, updates record (status=completed)
7. Frontend polls `/api/generation/{id}/status` for progress

## Hunyuan3D Flow Detail

```python
# Step 1: Generate
result = await blender_client.generate_hunyuan3d(text_prompt="a viking shield")
job_id = result["job_id"]  # e.g., "job_xxx"

# Step 2: Poll (loop every 5s)
status = await blender_client.poll_hunyuan_status(job_id)
# status["status"] → "RUN" (keep polling) or "DONE" (complete)

# Step 3: Import (when DONE)
import_result = await blender_client.import_hunyuan_asset(
    name="viking_shield",
    zip_file_url=status["ResultFile3Ds"][...]  # URL from DONE response
)
```

## Rodin Flow Detail

```python
# Step 1: Generate
result = await blender_client.generate_rodin_text(
    text_prompt="a viking longship",
    bbox_condition=[3.0, 0.5, 1.0]  # optional [L, W, H] ratio
)
subscription_key = result["subscription_key"]

# Step 2: Poll (loop every 5s)
status = await blender_client.poll_rodin_status(subscription_key=subscription_key)
# status → list of {"status": "Done"} when complete

# Step 3: Import
import_result = await blender_client.import_rodin_asset(
    name="viking_longship",
    task_uuid=subscription_key
)
```

## YggdrasilStudio Bridge

Studio's Gallery can send generated images to Forge via:
- `POST http://localhost:8081/api/generation/from-studio?image_path=/path/to/comfyui/output.png`
- This takes a ComfyUI output image and generates a 3D model from it

## Nordic UI Theme

Same theme as YggdrasilStudio:
- Colors: midnight (#0a0e1a), gold (#c9a84c), bifrost (#7dd3fc), blood (#8b0000)
- Fonts: Inter (body) + JetBrains Mono (code) + Cinzel (headings)
- CSS classes: `.btn-nordic`, `.card-frost`, `.card-rune`, `.heading-runic`
- Buttons: gold gradient, runic style
- Progress: rune progress bars, aurora animations

## Status

- **Backend**: FastAPI scaffolded, all routes working (`config`, `models`, `database`, `blender_client`, generation CRUD, asset browsing)
- **Frontend**: React+Vite+TailwindCSS scaffolded, pages for `Generate`, `Gallery`, `Models`, `Settings`, `History`
- **Status**: Now fully tracked in git (May 2026). Previously blocked by blanket `.gitignore` rule; now uses specific excludes (node_modules/, dist/, build/, __pycache__/, .vite/).
- **Tests**: 62/62 passing with 0 warnings (conftest.py patches `backend.blender_client.blender_client` singleton). test_api (21), test_blender_routes (14), test_assets_routes (27)
- **Python venv**: `backend/.venv/` with FastAPI, SQLAlchemy, httpx, pytest
- **Node deps**: `frontend/node_modules/` installed

### Testing Pattern (conftest.py)

Mock the **module-level singleton**, not individual route imports. The `blender_client` is imported into each route module at module-load time, so per-route `patch("routes.xxx.blender_client")` doesn't catch all references. Instead:

```python
# conftest.py — correct pattern
@pytest.fixture(autouse=True)
def mock_blender():
    with patch("backend.blender_client.blender_client") as mock:
        mock.get_scene_info.return_value = {"name": "TestScene"}
        yield mock
```

This patches the singleton object before routes import it, so all `from backend.blender_client import blender_client` references throughout the app resolve to the mock.

## Pitfalls

- **Blender MCP port is 9897 NOT 9876**: The addon is configured on port 9897. Default is 9876 but we changed it.
- **WSL2 can't reach Windows 127.0.0.1**: Must set Blender MCP addon host to `0.0.0.0` in Blender preferences, then connect from WSL2 using the Windows IP or `localhost`.
- **Hunyuan3D returns job_id**: Must poll until status is "DONE", then extract zip_file_url from ResultFile3Ds.
- **Rodin returns subscription_key (MAIN_SITE mode)**: Poll with subscription_key, get list of statuses. Import with task_uuid parameter.
- **Generated models have normalized size**: Rodin models come in normalized size — may need rescaling via Blender code execution.
- **Sketchfab target_size is required**: When downloading Sketchfab models, must specify target_size in meters (e.g., chair=1.0, person=1.7, car=4.5).
- **PolyHaven resolution options**: 1k, 2k, 4k — higher res takes longer to download.
- **Blender execute_blender_code is powerful**: Arbitrary Python execution in Blender. Production deployments should add auth.
- **Same React + Vite stack as Studio**: Use port 5174 (not 5173) to avoid conflict.
- **build-backend must be `hatchling.build` not `hatchling.backends`**: The correct entry point for hatchling is `hatchling.build`. Using `hatchling.backends` causes `ModuleNotFoundError` during `uv sync --all-packages`.
- **Hatchling needs `packages = ["backend"]` in pyproject.toml**: Since the package code lives in `backend/` (not `src/`), you must add `[tool.hatch.build.targets.wheel] packages = ["backend"]`. Without this, hatchling can't find the code.
- **pytest needs `pythonpath = ["."]` per sub-package**: Each sub-package's `pyproject.toml` should have `[tool.pytest.ini_options] pythonpath = ["."]` so `from backend.xxx` imports work when running from the sub-package directory.
- **uv doesn't auto-resolve hatchling as build dependency**: Add `[tool.uv.extra-build-dependencies] hatchling = ["hatchling"]` to the root `pyproject.toml` so `uv sync --all-packages` can build workspace members that use hatchling.