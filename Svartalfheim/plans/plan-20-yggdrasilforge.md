# YggdrasilForge — Viking 3D Asset Studio

> **For Hermes:** Use subagent-driven-development skill to implement this plan task-by-task.

**Goal:** Build a 3D asset creation and management studio — the "altar of forja" — that connects to Blender via MCP, generates models from text/image prompts using free AI services (Hunyuan3D, Hyper3D Rodin), and catalogs assets from PolyHaven and Sketchfab. This is the 3D counterpart to YggdrasilStudio (2D/image generation).

**Architecture:** FastAPI backend (port 8081) serves a REST API for 3D generation, asset search, and Blender Bridge commands. React + Vite + TailwindCSS frontend (port 5174) with the same Nordic dark fantasy theme as YggdrasilStudio. Blender MCP (port 9897) handles local 3D manipulation — model import, texturing, rendering, and export. All generation goes through the backend which orchestrates AI services and Blender MCP commands.

**Tech Stack:** Python 3.11+ / FastAPI / httpx / aiosqlite / React 18 / Vite / TailwindCSS / Blender MCP / Hunyuan3D API / Hyper3D Rodin API / PolyHaven API / Sketchfab API

**Realm:** Alfheim/YggdrasilForge/

---

## Integraciones Disponibles (GRATUITAS)

| Servicio | Tipo | Costo | Notas |
|----------|------|-------|-------|
| Hunyuan3D | Text-to-3D, Image-to-3D | Gratuito (rate-limited) | Vía Blender MCP, genera GLB con materiales |
| Hyper3D Rodin | Text-to-3D, Image-to-3D | Free trial (MAIN_SITE) | Vía Blender MCP, bbox_condition para proporciones |
| PolyHaven | HDRIs, Texturas, Modelos 3D | Gratuito (CC0) | Vía Blender MCP, alta calidad |
| Sketchfab | Buscar/descargar modelos | Gratuito (logged: gameoverhf12) | Vía Blender MCP, filtrar por descargable |
| Blender MCP | Manipulación 3D local | Gratuito (addon Blender) | Puerto 9897, no 9876 (default) |

**NO INCLUIDAS (sin capital):** Meshy API (Pro $20/mes), Tripo3D API, CF Studio. Se pueden agregar después como providers intercambiables.

---

## Task 1: Project Scaffold — Backend FastAPI

**Files:**
- Create: `Alfheim/YggdrasilForge/backend/__init__.py`
- Create: `Alfheim/YggdrasilForge/backend/main.py`
- Create: `Alfheim/YggdrasilForge/backend/config.py`
- Create: `Alfheim/YggdrasilForge/backend/models.py`
- Create: `Alfheim/YggdrasilForge/backend/pyproject.toml`

**Step 1:** Create project directory structure

```bash
mkdir -p Alfheim/YggdrasilForge/backend/routes
mkdir -p Alfheim/YggdrasilForge/frontend/src/{api,components,pages,hooks,theme,utils}
mkdir -p Alfheim/YggdrasilForge/frontend/public
mkdir -p Alfheim/YggdrasilForge/tests
```

**Step 2:** Create `backend/config.py` — Settings with Pydantic BaseSettings

```python
from pydantic_settings import BaseSettings
from pathlib import Path

class Settings(BaseSettings):
    # Server
    HOST: str = "0.0.0.0"
    PORT: int = 8081
    DEBUG: bool = False

    # Blender MCP
    BLENDER_MCP_URL: str = "http://127.0.0.1:9897"

    # AI Services (via Blender MCP — no direct API keys needed)
    HUNYUAN3D_ENABLED: bool = True
    RODIN_ENABLED: bool = True
    POLYHAVEN_ENABLED: bool = True
    SKETCHFAB_ENABLED: bool = True

    # Database
    DB_PATH: str = str(Path(__file__).parent.parent / "data" / "forge.db")
    OUTPUT_DIR: str = str(Path(__file__).parent.parent / "data" / "outputs")

    # CORS
    CORS_ORIGINS: list[str] = [
        "http://localhost:5174",
        "http://localhost:3000",
        "http://127.0.0.1:5174",
    ]

    class Config:
        env_file = ".env"

settings = Settings()
```

**Step 3:** Create `backend/models.py` — Pydantic models for 3D generation

```python
from pydantic import BaseModel, Field
from enum import Enum
from datetime import datetime

class GenerationType(str, Enum):
    TEXT_TO_3D = "text_to_3d"
    IMAGE_TO_3D = "image_to_3d"
    TEXTURE_APPLY = "texture_apply"
    MODEL_SEARCH = "model_search"
    RENDER = "render"

class AIProvider(str, Enum):
    HUNYUAN3D = "hunyuan3d"
    RODIN = "rodin"
    POLYHAVEN = "polyhaven"
    SKETCHFAB = "sketchfab"
    BLENDER_LOCAL = "blender_local"

class GenerationStatus(str, Enum):
    QUEUED = "queued"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"

class TextTo3DRequest(BaseModel):
    prompt: str = Field(..., min_length=3, max_length=500)
    provider: AIProvider = AIProvider.HUNYUAN3D
    bbox_condition: list[float] | None = Field(None, description="[L, W, H] ratio for Rodin")
    auto_import: bool = True

class ImageTo3DRequest(BaseModel):
    image_path: str | None = Field(None, description="Local path to reference image")
    image_url: str | None = Field(None, description="URL to reference image")
    prompt: str | None = Field(None, description="Optional text prompt alongside image")
    provider: AIProvider = AIProvider.HUNYUAN3D
    auto_import: bool = True

class TextureApplyRequest(BaseModel):
    object_name: str = Field(..., description="Blender object name")
    texture_id: str = Field(..., description="PolyHaven texture ID")
    resolution: str = Field("1k", description="Texture resolution: 1k, 2k, 4k")

class ModelSearchRequest(BaseModel):
    query: str = Field(..., min_length=2)
    source: AIProvider = AIProvider.SKETCHFAB
    asset_type: str = "models"  # models, hdris, textures
    categories: str | None = None
    count: int = Field(10, ge=1, le=50)

class RenderRequest(BaseModel):
    scene_name: str | None = None
    engine: str = "eevee"  # eevee, cycles
    resolution_x: int = 1920
    resolution_y: int = 1080
    output_path: str | None = None

class AssetMetadata(BaseModel):
    id: str
    name: str
    provider: AIProvider
    asset_type: str  # model, texture, hdri, scene
    source_id: str | None = None  # PolyHaven/Sketchfab ID
    file_path: str | None = None
    thumbnail: str | None = None
    tags: list[str] = []
    created_at: datetime = Field(default_factory=datetime.utcnow)

class Generation(BaseModel):
    id: str
    type: GenerationType
    provider: AIProvider
    status: GenerationStatus = GenerationStatus.QUEUED
    prompt: str | None = None
    input_image: str | None = None
    result_object: str | None = None  # Blender object name after import
    result_path: str | None = None  # File path if exported
    error: str | None = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    completed_at: datetime | None = None
```

**Step 4:** Create `backend/main.py` — FastAPI app with CORS, health, routers

```python
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

from config import settings
from routes import generation, assets, blender, render

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: ensure data dirs exist
    from pathlib import Path
    Path(settings.OUTPUT_DIR).mkdir(parents=True, exist_ok=True)
    Path(settings.DB_PATH).parent.mkdir(parents=True, exist_ok=True)
    yield

app = FastAPI(
    title="YggdrasilForge",
    description="Viking 3D Asset Studio — AI generation + Blender Bridge",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(generation.router, prefix="/api/generation", tags=["generation"])
app.include_router(assets.router, prefix="/api/assets", tags=["assets"])
app.include_router(blender.router, prefix="/api/blender", tags=["blender"])
app.include_router(render.router, prefix="/api/render", tags=["render"])

@app.get("/health")
async def health():
    return {
        "status": "rooted",
        "version": "0.1.0",
        "services": {
            "blender_mcp": {"url": settings.BLENDER_MCP_URL, "online": False},  # checked dynamically
        }
    }
```

**Step 5:** Create `backend/pyproject.toml`

```toml
[project]
name = "yggdrasil-forge"
version = "0.1.0"
description = "Viking 3D Asset Studio — AI generation + Blender Bridge"
requires-python = ">=3.11"
dependencies = [
    "fastapi>=0.110",
    "uvicorn[standard]>=0.29",
    "httpx>=0.27",
    "aiosqlite>=0.20",
    "pydantic>=2.6",
    "pydantic-settings>=2.2",
    "python-multipart>=0.0.9",
    "orjson>=3.10",
]

[project.scripts]
forge-server = "backend.main:main"

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.backends"
```

**Verification:** `cd Alfheim/YggdrasilForge && python3 -m venv .venv && source .venv/bin/activate && pip install fastapi uvicorn httpx aiosqlite pydantic pydantic-settings python-multipart orjson`

**Commit:** `[ALFHEIM] feat(forge): scaffold backend project structure`

---

## Task 2: Blender MCP Client — Async HTTP Bridge

**Files:**
- Create: `Alfheim/YggdrasilForge/backend/blender_client.py`

**Step 1:** Create the async MCP client that calls Blender MCP tools via HTTP

```python
import httpx
import asyncio
from typing import Any
from config import settings

class BlenderMCPClient:
    """Async client for Blender MCP addon (port 9897)."""

    def __init__(self, base_url: str | None = None):
        self.base_url = base_url or settings.BLENDER_MCP_URL
        self._client: httpx.AsyncClient | None = None

    async def _get_client(self) -> httpx.AsyncClient:
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(base_url=self.base_url, timeout=120.0)
        return self._client

    async def close(self):
        if self._client and not self._client.is_closed:
            await self._client.aclose()

    async def _call_tool(self, tool_name: str, arguments: dict[str, Any] = None) -> dict:
        """Call a Blender MCP tool via JSON-RPC."""
        client = await self._get_client()
        payload = {
            "jsonrpc": "2.0",
            "method": "tools/call",
            "params": {
                "name": tool_name,
                "arguments": arguments or {}
            },
            "id": 1
        }
        response = await client.post("/", json=payload)
        response.raise_for_status()
        data = response.json()
        if "error" in data:
            raise BlenderMCPError(data["error"])
        return data.get("result", {})

    async def health_check(self) -> bool:
        """Check if Blender MCP is reachable."""
        try:
            client = await self._get_client()
            resp = await client.get("/", timeout=5.0)
            return resp.status_code == 200
        except (httpx.ConnectError, httpx.TimeoutException):
            return False

    # Scene operations
    async def get_scene_info(self) -> dict:
        return await self._call_tool("get_scene_info", {"user_prompt": "forge_scene_info"})

    async def get_object_info(self, object_name: str) -> dict:
        return await self._call_tool("get_object_info", {"object_name": object_name})

    # 3D Generation — Hunyuan3D
    async def generate_hunyuan3d(self, text_prompt: str | None = None, image_url: str | None = None) -> dict:
        args = {"user_prompt": text_prompt or "forge_generation"}
        if text_prompt:
            args["text_prompt"] = text_prompt
        if image_url:
            args["input_image_url"] = image_url
        return await self._call_tool("generate_hunyuan3d_model", args)

    async def poll_hunyuan_status(self, job_id: str) -> dict:
        return await self._call_tool("poll_hunyuan_job_status", {"job_id": job_id})

    async def import_hunyuan_asset(self, name: str, zip_file_url: str) -> dict:
        return await self._call_tool("import_generated_asset_hunyuan", {
            "name": name, "zip_file_url": zip_file_url
        })

    # 3D Generation — Hyper3D Rodin
    async def generate_rodin_text(self, text_prompt: str, bbox_condition: list[float] | None = None) -> dict:
        args = {"text_prompt": text_prompt, "user_prompt": text_prompt}
        if bbox_condition:
            args["bbox_condition"] = bbox_condition
        return await self._call_tool("generate_hyper3d_model_via_text", args)

    async def generate_rodin_image(self, image_paths: list[str] | None = None,
                                     image_urls: list[str] | None = None,
                                     bbox_condition: list[float] | None = None) -> dict:
        args = {"user_prompt": "forge_image_to_3d"}
        if image_paths:
            args["input_image_paths"] = image_paths
        if image_urls:
            args["input_image_urls"] = image_urls
        if bbox_condition:
            args["bbox_condition"] = bbox_condition
        return await self._call_tool("generate_hyper3d_model_via_images", args)

    async def poll_rodin_status(self, subscription_key: str | None = None,
                                  request_id: str | None = None) -> dict:
        args = {}
        if subscription_key:
            args["subscription_key"] = subscription_key
        if request_id:
            args["request_id"] = request_id
        return await self._call_tool("poll_rodin_job_status", args)

    async def import_rodin_asset(self, name: str, task_uuid: str | None = None,
                                   request_id: str | None = None) -> dict:
        args = {"name": name}
        if task_uuid:
            args["task_uuid"] = task_uuid
        if request_id:
            args["request_id"] = request_id
        return await self._call_tool("import_generated_asset", args)

    # PolyHaven
    async def search_polyhaven(self, asset_type: str = "all", categories: str | None = None) -> dict:
        args = {"asset_type": asset_type, "user_prompt": "forge_search"}
        if categories:
            args["categories"] = categories
        return await self._call_tool("search_polyhaven_assets", args)

    async def download_polyhaven(self, asset_id: str, asset_type: str, resolution: str = "1k") -> dict:
        return await self._call_tool("download_polyhaven_asset", {
            "asset_id": asset_id, "asset_type": asset_type,
            "resolution": resolution, "user_prompt": f"forge_download_{asset_id}"
        })

    async def set_texture(self, object_name: str, texture_id: str) -> dict:
        return await self._call_tool("set_texture", {
            "object_name": object_name, "texture_id": texture_id,
            "user_prompt": f"forge_texture_{texture_id}"
        })

    # Sketchfab
    async def search_sketchfab(self, query: str, categories: str | None = None,
                                count: int = 10, downloadable: bool = True) -> dict:
        args = {"query": query, "count": count, "downloadable": downloadable,
                "user_prompt": f"forge_search_{query}"}
        if categories:
            args["categories"] = categories
        return await self._call_tool("search_sketchfab_models", args)

    async def download_sketchfab(self, uid: str, target_size: float = 1.0) -> dict:
        return await self._call_tool("download_sketchfab_model", {
            "uid": uid, "target_size": target_size,
            "user_prompt": f"forge_download_{uid}"
        })

    async def preview_sketchfab(self, uid: str) -> dict:
        return await self._call_tool("get_sketchfab_model_preview", {"uid": uid})

    # Blender code execution
    async def execute_blender_code(self, code: str) -> dict:
        return await self._call_tool("execute_blender_code", {
            "code": code, "user_prompt": "forge_execute"
        })

    # Viewport screenshot
    async def get_viewport_screenshot(self, max_size: int = 1000) -> dict:
        return await self._call_tool("get_viewport_screenshot", {
            "max_size": max_size, "user_prompt": "forge_screenshot"
        })


class BlenderMCPError(Exception):
    """Error from Blender MCP tool call."""
    def __init__(self, data: dict):
        self.code = data.get("code", -1)
        self.message = data.get("message", "Unknown Blender MCP error")
        super().__init__(self.message)
```

**Note on MCP Protocol:** The Blender MCP addon exposes tools via JSON-RPC on port 9897. The client above wraps the Hermes MCP tools into async HTTP calls. If the addon uses a different protocol (SSE or stdio), we'll need to adapt. The initial implementation uses direct HTTP POST with JSON-RPC payload. If that doesn't work, we'll switch to using Hermes as the MCP proxy — calling Blender MCP tools through the Hermes agent rather than directly.

**Verification:** Unit test that the client initializes without errors.

**Commit:** `[ALFHEIM] feat(forge): add Blender MCP async client`

---

## Task 3: Database — Asset & Generation History

**Files:**
- Create: `Alfheim/YggdrasilForge/backend/database.py`

**Step 1:** Create SQLite database with aiosqlite

```python
import aiosqlite
import json
from pathlib import Path
from datetime import datetime
from config import settings

SCHEMA = """
CREATE TABLE IF NOT EXISTS generations (
    id TEXT PRIMARY KEY,
    type TEXT NOT NULL,
    provider TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'queued',
    prompt TEXT,
    input_image TEXT,
    result_object TEXT,
    result_path TEXT,
    error TEXT,
    provider_job_id TEXT,
    provider_data TEXT,
    created_at TEXT NOT NULL,
    completed_at TEXT
);

CREATE TABLE IF NOT EXISTS assets (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    provider TEXT NOT NULL,
    asset_type TEXT NOT NULL,
    source_id TEXT,
    file_path TEXT,
    thumbnail TEXT,
    tags TEXT,
    metadata TEXT,
    created_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_generations_status ON generations(status);
CREATE INDEX IF NOT EXISTS idx_generations_provider ON generations(provider);
CREATE INDEX IF NOT EXISTS idx_assets_provider ON assets(provider);
CREATE INDEX IF NOT EXISTS idx_assets_type ON assets(asset_type);
"""

async def init_db(db_path: str | None = None) -> aiosqlite.Connection:
    path = db_path or settings.DB_PATH
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    db = await aiosqlite.connect(path)
    db.row_factory = aiosqlite.Row
    await db.executescript(SCHEMA)
    await db.commit()
    return db

async def get_db() -> aiosqlite.Connection:
    """Get a database connection (call init_db first)."""
    return await aiosqlite.connect(settings.DB_PATH)
```

**Commit:** `[ALFHEIM] feat(forge): add SQLite database with generations and assets tables`

---

## Task 4: Generation Routes — Text-to-3D, Image-to-3D

**Files:**
- Create: `Alfheim/YggdrasilForge/backend/routes/__init__.py`
- Create: `Alfheim/YggdrasilForge/backend/routes/generation.py`

**Step 1:** Create generation router with endpoints for:

- `POST /api/generation/text-to-3d` — Submit text prompt, choose provider (hunyuan3d/rodin), returns generation ID
- `POST /api/generation/image-to-3d` — Submit image + optional prompt, choose provider
- `GET /api/generation/{id}/status` — Poll generation status
- `GET /api/generation/{id}/result` — Get result (object name, file path, thumbnail)
- `GET /api/generation/history` — List past generations with filters

**Key flow for text-to-3D:**
1. User submits prompt + provider via frontend
2. Backend creates generation record (status=queued)
3. Background task calls `blender_client.generate_hunyuan3d(prompt)` or `generate_rodin_text(prompt)`
4. Gets `job_id` back, updates record (status=processing)
5. Poll loop checks `poll_hunyuan_status(job_id)` every 5s
6. On completion: calls `import_hunyuan_asset(name, zip_url)`, updates record (status=completed)
7. Frontend polls `/api/generation/{id}/status` or connects via WebSocket

**Commit:** `[ALFHEIM] feat(forge): add generation routes for text-to-3D and image-to-3D`

---

## Task 5: Asset Routes — Search & Download (PolyHaven, Sketchfab)

**Files:**
- Create: `Alfheim/YggdrasilForge/backend/routes/assets.py`

**Endpoints:**
- `GET /api/assets/search?query=...&source=sketchfab|polyhaven&type=models|hdris|textures&categories=...` — Search assets
- `POST /api/assets/download` — Download asset (PolyHaven texture/model/Sketchfab model)
- `POST /api/assets/texture/apply` — Apply PolyHaven texture to Blender object
- `GET /api/assets/categories?type=hdris|textures|models` — Get PolyHaven categories
- `GET /api/assets/{id}` — Get asset details from DB

**Key flows:**
- PolyHaven search → `search_polyhaven_assets` → paginate results
- Sketchfab search → `search_sketchfab_models` → show thumbnails + download button
- Apply texture → first `download_polyhaven_asset` then `set_texture` on selected object
- All downloads get cataloged in the assets DB

**Commit:** `[ALFHEIM] feat(forge): add asset search and download routes`

---

## Task 6: Blender Routes — Scene Info, Execute Code, Screenshot

**Files:**
- Create: `Alfheim/YggdrasilForge/backend/routes/blender.py`

**Endpoints:**
- `GET /api/blender/scene` — Get current Blender scene info
- `GET /api/blender/object/{name}` — Get object details
- `POST /api/blender/execute` — Execute arbitrary Python in Blender
- `GET /api/blender/screenshot?max_size=800` — Get viewport screenshot
- `GET /api/blender/status` — Quick check if Blender MCP is reachable
- `POST /api/blender/export` — Export scene/objects to GLB/OBJ/FBX

**Note:** The execute endpoint is powerful (arbitrary Python in Blender). In production, this should be behind auth. For local dev, it's the primary way to manipulate objects, set up scenes, and run render pipelines.

**Commit:** `[ALFHEIM] feat(forge): add Blender bridge routes`

---

## Task 7: Render Routes — Eevee/Cycles Rendering

**Files:**
- Create: `Alfheim/YggdrasilForge/backend/routes/render.py`

**Endpoints:**
- `POST /api/render/viewport` — Quick viewport screenshot (already available via blender routes)
- `POST /api/render/scene` — Full scene render with Eevee or Cycles

**Render pipeline via Blender code execution:**
```python
# Example Blender render code
import bpy
bpy.context.scene.render.engine = 'BLENDER_EEVEE_NEXT'  # or 'CYCLES'
bpy.context.scene.render.resolution_x = 1920
bpy.context.scene.render.resolution_y = 1080
bpy.context.scene.render.filepath = '/tmp/forge_render.png'
bpy.ops.render.render(write_still=True)
```

**Commit:** `[ALFHEIM] feat(forge): add render routes`

---

## Task 8: Frontend Scaffold — React + Vite + TailwindCSS

**Files:**
- Create: `Alfheim/YggdrasilForge/frontend/package.json`
- Create: `Alfheim/YggdrasilForge/frontend/vite.config.js`
- Create: `Alfheim/YggdrasilForge/frontend/tailwind.config.js`
- Create: `Alfheim/YggdrasilForge/frontend/index.html`
- Create: `Alfheim/YggdrasilForge/frontend/src/App.jsx`
- Create: `Alfheim/YggdrasilForge/frontend/src/main.jsx`
- Create: `Alfheim/YggdrasilForge/frontend/src/index.css`

**Key config:**
- Vite dev server on port 5174 (avoid conflict with Studio on 5173)
- Proxy `/api` and `/health` to backend `:8081`
- Same Nordic dark fantasy theme as YggdrasilStudio (shared CSS variables, fonts)
- React.lazy code splitting for pages

**Pages (initial):**
1. **Forge** (home) — Text-to-3D generation form, provider selection, progress
2. **Library** — Asset library (PolyHaven search, Sketchfab browse, downloaded assets)
3. **Viewport** — Blender viewport screenshot + object list
4. **History** — Past generations with status, re-render, re-import

**Commit:** `[ALFHEIM] feat(forge): scaffold React + Vite + TailwindCSS frontend`

---

## Task 9: Frontend — Forge Page (Text-to-3D Generation)

**Files:**
- Create: `Alfheim/YggdrasilForge/frontend/src/pages/Forge.jsx`
- Create: `Alfheim/YggdrasilForge/frontend/src/components/GenerationForm.jsx`
- Create: `Alfheim/YggdrasilForge/frontend/src/components/ProviderSelect.jsx`
- Create: `Alfheim/YggdrasilForge/frontend/src/components/GenerationProgress.jsx`

**Generation Form features:**
- Text prompt textarea (3-500 chars)
- Provider dropdown: Hunyuan3D (default), Rodin
- Optional bbox_condition sliders for Rodin (length, width, height ratio)
- "Forge Model" button (gold gradient, runic style — same btn-nordic as Studio)
- Progress indicator with status polling (queued → processing → completed)
- On completion: show viewport screenshot of imported model
- "Open in Blender" visual indicator (model is already in Blender via MCP)

**Commit:** `[ALFHEIM] feat(forge): add Forge page with generation form`

---

## Task 10: Frontend — Library Page (PolyHaven + Sketchfab)

**Files:**
- Create: `Alfheim/YggdrasilForge/frontend/src/pages/Library.jsx`
- Create: `Alfheim/YggdrasilForge/frontend/src/components/AssetSearch.jsx`
- Create: `Alfheim/YggdrasilForge/frontend/src/components/AssetGrid.jsx`
- Create: `Alfheim/YggdrasilForge/frontend/src/components/AssetCard.jsx`

**Library features:**
- Tab selector: PolyHaven (HDRI/Textures/Models) | Sketchfab (Models)
- Search bar with debounced queries (300ms like Studio)
- Category filter dropdown (loaded from `/api/assets/categories`)
- Resolution selector for PolyHaven (1k/2k/4k)
- Asset grid with thumbnails (3-column responsive grid)
- Asset card: thumbnail, name, provider badge, download/apply button
- For textures: "Apply to selected object" button (needs Blender object name)
- For models: "Download & Import" button (calls Sketchfab download or PolyHaven model download)
- For HDRIs: "Set as world HDRI" button

**Commit:** `[ALFHEIM] feat(forge): add Library page with PolyHaven and Sketchfab browsing`

---

## Task 11: Frontend — Viewport & History Pages

**Files:**
- Create: `Alfheim/YggdrasilForge/frontend/src/pages/Viewport.jsx`
- Create: `Alfheim/YggdrasilForge/frontend/src/pages/History.jsx`
- Create: `Alfheim/YggdrasilForge/frontend/src/components/ViewportPanel.jsx`
- Create: `Alfheim/YggdrasilForge/frontend/src/components/GenerationHistory.jsx`

**Viewport page:**
- Live viewport screenshot (polls `/api/blender/screenshot` on interval or on-demand)
- Scene info panel (objects, materials, cameras)
- Object list with selection
- Quick actions: Delete selected, Apply HDRI, Add primitive

**History page:**
- Table of past generations (like Studio's History page)
- Status badges (queued/processing/completed/failed) with Nordic colors
- Re-import button (re-runs import for completed generations)
- Filter by provider, type, date range

**Commit:** `[ALFHEIM] feat(forge): add Viewport and History pages`

---

## Task 12: Image-to-3D Integration — YggdrasilStudio Bridge

**Files:**
- Modify: `Alfheim/YggdrasilForge/backend/routes/generation.py`

**Step 1:** Add image upload endpoint

```python
@router.post("/image-to-3d")
async def image_to_3d(request: ImageTo3DRequest, file: UploadFile | None = None):
    """Generate 3D model from image (from YggdrasilStudio or upload)."""
    # Save uploaded image to OUTPUT_DIR
    # Call blender_client.generate_hunyuan3d(image_url=...) or generate_rodin_image(...)
    # If auto_import: poll and import when done
    ...
```

**Step 2:** Add cross-service endpoint that YggdrasilStudio can call

```python
@router.post("/from-studio")
async def from_studio(image_path: str, prompt: str | None = None):
    """Bridge from YggdrasilStudio — takes a ComfyUI output image and generates 3D."""
    # Image comes from ComfyUI output dir (same machine)
    # Generate 3D model from the image
    ...
```

**YggdrasilStudio integration:** Studio's Gallery page will get a "Forge 3D" button on each generated image that calls `http://localhost:8081/api/generation/from-studio?image_path=...`, sending the image to Forge for 3D generation.

**Commit:** `[ALFHEIM] feat(forge): add image-to-3D and YggdrasilStudio bridge endpoint`

---

## Task 13: Startup Script & Documentation

**Files:**
- Create: `Alfheim/YggdrasilForge/start.sh`
- Create: `Alfheim/YggdrasilForge/start.bat` (Windows via WSL)
- Create: `Alfheim/YggdrasilForge/README.md`
- Create: `Alfheim/YggdrasilForge/.env.example`

**start.sh:** Check Blender MCP is running, install backend deps, build frontend if needed, start uvicorn on :8081
**README.md:** Full project documentation — setup, architecture, API reference, Blender MCP connection guide
**.env.example:** BLENDER_MCP_URL, DB_PATH, OUTPUT_DIR, CORS_ORIGINS

**Commit:** `[ALFHEIM] docs(forge): add startup scripts, README, and .env.example`

---

## Task 14: Tests — Backend API + Blender Client

**Files:**
- Create: `Alfheim/YggdrasilForge/tests/conftest.py`
- Create: `Alfheim/YggdrasilForge/tests/test_generation.py`
- Create: `Alfheim/YggdrasilForge/tests/test_assets.py`
- Create: `Alfheim/YggdrasilForge/tests/test_blender_client.py`
- Create: `Alfheim/YggdrasilForge/tests/test_database.py`

**Test coverage targets:**
- Blender client: mock httpx responses, test all tool call methods
- Generation routes: test submit, poll status, history
- Asset routes: test search, download, texture apply (mocked)
- Database: CRUD operations on generations and assets tables
- Health endpoint: verify /health returns status

**Commit:** `[ALFHEIM] test(forge): add backend API and client tests`

---

## Dependency Map

```
Task 1 (scaffold) → Task 2 (client) → Task 3 (database) → Task 4 (generation routes)
                                                          → Task 5 (asset routes)
                                                          → Task 6 (blender routes)
                                                          → Task 7 (render routes)
Task 1 → Task 8 (frontend scaffold)
Task 8 → Task 9 (Forge page)
Task 8 → Task 10 (Library page)
Task 8 → Task 11 (Viewport + History)
Task 4, 5, 12 → Task 12 (image-to-3D bridge)
All backend → Task 13 (startup + docs)
All backend → Task 14 (tests)
```

## Integration with YggdrasilStudio

```
YggdrasilStudio (2D)          YggdrasilForge (3D)
:8080                         :8081
ComfyUI port 8188             Blender MCP port 9897
  │                              │
  ├── Generate image ──────────────┤ Image → 3D model
  │   (txt2img, img2img)           │ (via /from-studio endpoint)
  │                                │
  ├── Gallery "Forge 3D" button ───┤
  │                                │
  ├── SQLite (generations) ────────┤ Shared asset catalog?
  │                                │
  └────────────────────────────────┘ Same Nordic UI theme
```

## Future Enhancements (NOT in v0.1)

- Meshy API integration (when budget available) — same interface, just add provider
- Tripo3D API integration — same pattern
- ComfyUI → Forge pipeline (automated: generate character in ComfyUI, send to Forge for 3D)
- Animation rigging (Mixamo integration?)
- Batch generation (multiple prompts in sequence)
- WebSocket for real-time generation progress (like Studio)
- Asset versioning (multiple generations of same concept)
- Export pipeline (GLB → game engine, USDZ → AR, OBJ → 3D print)