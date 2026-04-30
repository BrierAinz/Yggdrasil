"""
SPA Static Files Handler - SoluciÃ³n robusta para servir la SPA React
"""
import mimetypes
from pathlib import Path

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import FileResponse, HTMLResponse, Response

# Paths
SPA_PATH = Path(__file__).parent.parent.parent / "Frontend" / "spa" / "dist"
JS_PATH = SPA_PATH / "js"
CSS_PATH = SPA_PATH / "css"
FONTS_PATH = SPA_PATH / "fonts"

# MIME types
mimetypes.init()
mimetypes.add_type("application/javascript", ".js")
mimetypes.add_type("text/css", ".css")

# Create router
spa_router = APIRouter()


def get_content_type(file_path: Path) -> str:
    """Get MIME type for file"""
    ext = file_path.suffix.lower()
    if ext == ".js":
        return "application/javascript"
    if ext == ".css":
        return "text/css"
    if ext == ".svg":
        return "image/svg+xml"
    if ext == ".ttf":
        return "font/ttf"
    content_type, _ = mimetypes.guess_type(str(file_path))
    return content_type or "application/octet-stream"


@spa_router.get("/js/{filepath:path}")
async def serve_js(filepath: str):
    """Serve JavaScript files"""
    file_path = JS_PATH / filepath
    if not file_path.exists() or not file_path.is_file():
        raise HTTPException(status_code=404, detail="JS not found")
    return FileResponse(
        path=str(file_path),
        media_type="application/javascript",
        headers={"Cache-Control": "public, max-age=3600"},
    )


@spa_router.get("/css/{filepath:path}")
async def serve_css(filepath: str):
    """Serve CSS files"""
    file_path = CSS_PATH / filepath
    if not file_path.exists() or not file_path.is_file():
        raise HTTPException(status_code=404, detail="CSS not found")
    return FileResponse(
        path=str(file_path),
        media_type="text/css",
        headers={"Cache-Control": "public, max-age=3600"},
    )


@spa_router.get("/fonts/{filepath:path}")
async def serve_fonts(filepath: str):
    """Serve font files"""
    file_path = FONTS_PATH / filepath
    if not file_path.exists() or not file_path.is_file():
        raise HTTPException(status_code=404, detail="Font not found")
    return FileResponse(
        path=str(file_path),
        media_type="font/ttf",
        headers={"Cache-Control": "public, max-age=86400"},
    )


@spa_router.get("/lilith-icon.svg")
async def serve_favicon():
    """Serve favicon"""
    favicon_path = SPA_PATH / "lilith-icon.svg"
    if favicon_path.exists():
        return FileResponse(path=str(favicon_path), media_type="image/svg+xml")
    raise HTTPException(status_code=404)


@spa_router.get("/")
async def serve_index():
    """Serve index.html for root path"""
    index_path = SPA_PATH / "index.html"
    if index_path.exists():
        content = index_path.read_text(encoding="utf-8")
        return HTMLResponse(content=content)
    raise HTTPException(
        status_code=404, detail="SPA not built. Run 'npm run build' in Frontend/spa"
    )


@spa_router.get("/{path:path}")
async def serve_catch_all(path: str, request: Request):
    """Serve index.html for all other routes (React Router)"""
    # Skip API and WebSocket routes
    if path.startswith("api/") or path.startswith("ws/"):
        raise HTTPException(status_code=404)

    # Skip static files (handled by specific routes above)
    if path.startswith("js/") or path.startswith("css/") or path.startswith("fonts/"):
        raise HTTPException(status_code=404)

    # Try to serve as static file from root
    file_path = SPA_PATH / path
    if file_path.exists() and file_path.is_file():
        content_type = get_content_type(file_path)
        return FileResponse(path=str(file_path), media_type=content_type)

    # Otherwise serve index.html for client-side routing
    index_path = SPA_PATH / "index.html"
    if index_path.exists():
        content = index_path.read_text(encoding="utf-8")
        return HTMLResponse(content=content)

    raise HTTPException(status_code=404, detail="Not found")
