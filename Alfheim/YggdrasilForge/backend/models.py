"""Pydantic models for YggdrasilForge API."""

from __future__ import annotations

from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel, Field


# ── Enums ──────────────────────────────────────────────────────────────────


class GenerationType(StrEnum):
    TEXT_TO_3D = "text_to_3d"
    IMAGE_TO_3D = "image_to_3d"
    TEXTURE_APPLY = "texture_apply"
    MODEL_SEARCH = "model_search"
    RENDER = "render"


class AIProvider(StrEnum):
    HUNYUAN3D = "hunyuan3d"
    RODIN = "rodin"
    POLYHAVEN = "polyhaven"
    SKETCHFAB = "sketchfab"
    BLENDER_LOCAL = "blender_local"


class GenerationStatus(StrEnum):
    QUEUED = "queued"
    PROCESSING = "processing"
    IMPORTING = "importing"
    COMPLETED = "completed"
    FAILED = "failed"


class AssetType(StrEnum):
    MODEL = "model"
    TEXTURE = "texture"
    HDRI = "hdri"
    SCENE = "scene"


class RenderEngine(StrEnum):
    EEVEE = "eevee"
    CYCLES = "cycles"


# ── Request models ─────────────────────────────────────────────────────────


class TextTo3DRequest(BaseModel):
    """Generate a 3D model from a text prompt."""

    prompt: str = Field(
        ..., min_length=3, max_length=500, description="Text description of the 3D model"
    )
    provider: AIProvider = AIProvider.HUNYUAN3D
    bbox_condition: list[float] | None = Field(
        None, description="[Length, Width, Height] ratio for Rodin provider"
    )
    auto_import: bool = True


class ImageTo3DRequest(BaseModel):
    """Generate a 3D model from an image reference."""

    image_path: str | None = Field(None, description="Local path to reference image")
    image_url: str | None = Field(None, description="URL to reference image")
    prompt: str | None = Field(None, description="Optional text prompt alongside image")
    provider: AIProvider = AIProvider.HUNYUAN3D
    bbox_condition: list[float] | None = None
    auto_import: bool = True


class TextureApplyRequest(BaseModel):
    """Apply a PolyHaven texture to a Blender object."""

    object_name: str = Field(..., description="Blender object name to texture")
    texture_id: str = Field(..., description="PolyHaven texture ID")
    resolution: str = Field("1k", description="Texture resolution: 1k, 2k, 4k")


class AssetSearchRequest(BaseModel):
    """Search for assets on PolyHaven or Sketchfab."""

    query: str = Field(..., min_length=2)
    source: AIProvider = AIProvider.SKETCHFAB
    asset_type: str = "models"
    categories: str | None = None
    count: int = Field(10, ge=1, le=50)


class SketchfabDownloadRequest(BaseModel):
    """Download and import a Sketchfab model."""

    uid: str = Field(..., description="Sketchfab model UID")
    target_size: float = Field(1.0, gt=0, description="Target size in meters for largest dimension")


class PolyHavenDownloadRequest(BaseModel):
    """Download a PolyHaven asset and optionally import it."""

    asset_id: str = Field(..., description="PolyHaven asset ID")
    asset_type: str = Field("models", description="Type: hdris, textures, models")
    resolution: str = Field("1k", description="Resolution: 1k, 2k, 4k")
    file_format: str | None = None
    import_to_scene: bool = True


class RenderRequest(BaseModel):
    """Render the current Blender scene."""

    engine: RenderEngine = RenderEngine.EEVEE
    resolution_x: int = Field(1920, ge=1, le=8192)
    resolution_y: int = Field(1080, ge=1, le=8192)
    output_path: str | None = None


class BlenderCodeRequest(BaseModel):
    """Execute arbitrary Python code in Blender."""

    code: str = Field(..., min_length=1, description="Python code to execute in Blender")


# ── Response models ─────────────────────────────────────────────────────────


class Generation(BaseModel):
    """A 3D generation record."""

    id: str
    type: GenerationType
    provider: AIProvider
    status: GenerationStatus = GenerationStatus.QUEUED
    prompt: str | None = None
    input_image: str | None = None
    result_object: str | None = None
    result_path: str | None = None
    error: str | None = None
    provider_job_id: str | None = None
    provider_data: dict | None = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    completed_at: datetime | None = None


class AssetMetadata(BaseModel):
    """Metadata for a downloaded/cached 3D asset."""

    id: str
    name: str
    provider: AIProvider
    asset_type: AssetType
    source_id: str | None = None
    file_path: str | None = None
    thumbnail: str | None = None
    tags: list[str] = []
    metadata: dict | None = None
    created_at: datetime = Field(default_factory=datetime.utcnow)


class HealthResponse(BaseModel):
    """Health check response."""

    status: str = "rooted"
    version: str = "0.1.0"
    services: dict = {}


class GenerationListResponse(BaseModel):
    """Paginated generation history."""

    items: list[Generation]
    total: int
    offset: int
    limit: int
