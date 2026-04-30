"""
SPA Serving - Version with proper UTF-8 encoding
"""
import os
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse, HTMLResponse, Response
from fastapi.staticfiles import StaticFiles

SPA_PATH = str(Path(__file__).parent.parent.parent / "Frontend" / "spa" / "dist")


def setup_spa_mounts(app: FastAPI):
    """Setup SPA static mounts - call this BEFORE API routes"""

    if not os.path.exists(SPA_PATH):
        print(f"SPA not found at {SPA_PATH}")
        return False

    print(f"Serving SPA assets from {SPA_PATH}")

    # 1. Mount static assets (JS, CSS, fonts)
    app.mount("/js", StaticFiles(directory=os.path.join(SPA_PATH, "js")), name="js")
    app.mount("/css", StaticFiles(directory=os.path.join(SPA_PATH, "css")), name="css")
    app.mount(
        "/fonts", StaticFiles(directory=os.path.join(SPA_PATH, "fonts")), name="fonts"
    )

    # 2. Favicon
    @app.get("/lilith-icon.svg")
    async def favicon():
        return FileResponse(os.path.join(SPA_PATH, "lilith-icon.svg"))

    # 3. Root path - serve index.html with UTF-8 encoding
    @app.get("/", response_class=HTMLResponse)
    async def serve_root():
        index_path = os.path.join(SPA_PATH, "index.html")
        if os.path.exists(index_path):
            with open(index_path, "r", encoding="utf-8") as f:
                content = f.read()
            return Response(
                content=content,
                media_type="text/html",
                headers={"Content-Type": "text/html; charset=utf-8"},
            )
        raise HTTPException(status_code=404, detail="index.html not found")

    return True


def setup_spa_catch_all(app: FastAPI):
    """
    Setup SPA catch-all route - call this AFTER all API routes!
    This must go last so it doesn't capture /api/* or /ws/*
    """

    @app.get("/{full_path:path}")
    async def serve_spa_catch_all(full_path: str):
        # Skip API and WebSocket routes
        if full_path.startswith("api/") or full_path.startswith("ws/"):
            raise HTTPException(status_code=404)

        # If path looks like a file with extension, 404
        # (real files are served by mounts)
        if "." in full_path.split("/")[-1]:
            raise HTTPException(status_code=404)

        # Return index.html for React Router with UTF-8 encoding
        index_path = os.path.join(SPA_PATH, "index.html")
        if os.path.exists(index_path):
            with open(index_path, "r", encoding="utf-8") as f:
                content = f.read()
            return Response(
                content=content,
                media_type="text/html",
                headers={"Content-Type": "text/html; charset=utf-8"},
            )
        raise HTTPException(status_code=404, detail="index.html not found")
