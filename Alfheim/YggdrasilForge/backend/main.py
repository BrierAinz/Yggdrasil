"""YggdrasilForge — Viking 3D Asset Studio. FastAPI backend."""

import uvicorn
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.config import settings
from backend.database import init_db, close_db
from backend.routes import generation, assets, blender, render


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup: create data dirs + DB. Shutdown: close connections."""
    Path(settings.OUTPUT_DIR).mkdir(parents=True, exist_ok=True)
    Path(settings.DB_PATH).parent.mkdir(parents=True, exist_ok=True)
    await init_db(settings.DB_PATH)
    yield
    await close_db()


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
    """Check service health + Blender MCP connectivity."""
    from backend.blender_client import blender_client

    blender_online = await blender_client.health_check()
    return {
        "status": "rooted",
        "version": "0.1.0",
        "services": {
            "blender_mcp": {
                "url": settings.BLENDER_MCP_URL,
                "online": blender_online,
            },
            "hunyuan3d": {"enabled": settings.HUNYUAN3D_ENABLED},
            "rodin": {"enabled": settings.RODIN_ENABLED},
            "polyhaven": {"enabled": settings.POLYHAVEN_ENABLED},
            "sketchfab": {"enabled": settings.SKETCHFAB_ENABLED},
        },
    }


def main():
    """Entry point for forge-server script."""
    uvicorn.run(
        "backend.main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.DEBUG,
    )


if __name__ == "__main__":
    main()
