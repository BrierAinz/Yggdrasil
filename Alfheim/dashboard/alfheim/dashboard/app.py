"""
Alfheim Dashboard - FastAPI application with HTMX + Alpine.js + Jinja2.

This is a frontend dashboard that currently serves mock data.
Real backend integration is pending — API route stubs raise
NotImplementedError until the backend services are connected.
"""

import asyncio
import json
import logging
from datetime import UTC, datetime
from pathlib import Path

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from jinja2 import Environment, FileSystemLoader
from sse_starlette.sse import EventSourceResponse


logger = logging.getLogger("alfheim-dashboard")

# --- Paths ---
BASE_DIR = Path(__file__).resolve().parent
TEMPLATES_DIR = BASE_DIR / "templates"
STATIC_DIR = BASE_DIR / "static"

# --- Jinja2 setup ---
jinja_env = Environment(
    loader=FileSystemLoader(str(TEMPLATES_DIR)),
    autoescape=True,
)


# =============================================================================
# Mock Data — backend integration pending
# =============================================================================

MOCK_REALMS = {
    "asgard": {
        "emoji": "🏛️",
        "status": "active",
        "file_count": 142,
        "dir_count": 23,
        "has_rules": True,
    },
    "alfheim": {
        "emoji": "🎨",
        "status": "active",
        "file_count": 89,
        "dir_count": 17,
        "has_rules": True,
    },
    "midgard": {
        "emoji": "🌍",
        "status": "active",
        "file_count": 312,
        "dir_count": 45,
        "has_rules": True,
    },
    "svartalfheim": {
        "emoji": "📚",
        "status": "idle",
        "file_count": 67,
        "dir_count": 12,
        "has_rules": True,
    },
    "vanaheim": {
        "emoji": "🌿",
        "status": "active",
        "file_count": 34,
        "dir_count": 8,
        "has_rules": False,
    },
    "jotunheim": {
        "emoji": "🏔️",
        "status": "idle",
        "file_count": 156,
        "dir_count": 31,
        "has_rules": True,
    },
    "muspelheim": {
        "emoji": "🔥",
        "status": "active",
        "file_count": 91,
        "dir_count": 19,
        "has_rules": True,
    },
    "niflheim": {
        "emoji": "🌫️",
        "status": "offline",
        "file_count": 23,
        "dir_count": 5,
        "has_rules": False,
    },
    "helheim": {
        "emoji": "⚰️",
        "status": "offline",
        "file_count": 12,
        "dir_count": 3,
        "has_rules": False,
    },
}

MOCK_AGENTS = {
    "eva": {
        "emoji": "👁️",
        "status": "active",
        "total_calls": 1247,
        "success_rate": 0.97,
        "avg_latency": 1.23,
    },
    "adan": {
        "emoji": "🔧",
        "status": "active",
        "total_calls": 893,
        "success_rate": 0.94,
        "avg_latency": 2.15,
    },
    "odin": {
        "emoji": "🧠",
        "status": "active",
        "total_calls": 2104,
        "success_rate": 0.99,
        "avg_latency": 0.89,
    },
    "lucifer": {
        "emoji": "🔥",
        "status": "idle",
        "total_calls": 567,
        "success_rate": 0.91,
        "avg_latency": 3.42,
    },
    "crystal": {
        "emoji": "💎",
        "status": "active",
        "total_calls": 342,
        "success_rate": 0.95,
        "avg_latency": 1.67,
    },
    "shalltear": {
        "emoji": "🩸",
        "status": "active",
        "total_calls": 421,
        "success_rate": 0.93,
        "avg_latency": 2.88,
    },
    "archivero": {
        "emoji": "📚",
        "status": "active",
        "total_calls": 189,
        "success_rate": 0.98,
        "avg_latency": 0.45,
    },
}

MOCK_MEMORY = {
    "semantic": {
        "total": 4821,
        "recent": 156,
        "size_mb": 124.5,
        "collections": ["concepts", "relations", "entities"],
    },
    "episodic": {
        "total": 1523,
        "recent": 42,
        "size_mb": 45.2,
        "collections": ["events", "interactions", "decisions"],
    },
    "muninn": {
        "total": 789,
        "recent": 23,
        "size_mb": 18.7,
        "collections": ["reflections", "patterns", "insights"],
    },
}

MOCK_TASKS = [
    {
        "id": "task-001",
        "name": "Análisis de dependencias",
        "agent": "odin",
        "status": "running",
        "progress": 0.72,
        "started_at": "2026-05-02T14:30:00Z",
        "priority": "high",
        "realm": "midgard",
    },
    {
        "id": "task-002",
        "name": "Indexación de documentos",
        "agent": "archivero",
        "status": "running",
        "progress": 0.45,
        "started_at": "2026-05-02T14:15:00Z",
        "priority": "medium",
        "realm": "svartalfheim",
    },
    {
        "id": "task-003",
        "name": "Monitoreo de servicios",
        "agent": "eva",
        "status": "pending",
        "progress": 0.0,
        "started_at": None,
        "priority": "low",
        "realm": "asgard",
    },
    {
        "id": "task-004",
        "name": "Optimización de memoria",
        "agent": "shalltear",
        "status": "completed",
        "progress": 1.0,
        "started_at": "2026-05-02T13:00:00Z",
        "priority": "medium",
        "realm": "niflheim",
    },
    {
        "id": "task-005",
        "name": "Generación de reportes",
        "agent": "crystal",
        "status": "running",
        "progress": 0.88,
        "started_at": "2026-05-02T14:00:00Z",
        "priority": "high",
        "realm": "alfheim",
    },
]

MOCK_LOGS = [
    {
        "timestamp": "2026-05-02T15:19:42Z",
        "level": "INFO",
        "source": "odin",
        "message": "Análisis de dependencias completado al 72%",
    },
    {
        "timestamp": "2026-05-02T15:19:38Z",
        "level": "INFO",
        "source": "eva",
        "message": "Monitoreo activo - todos los servicios operacionales",
    },
    {
        "timestamp": "2026-05-02T15:19:35Z",
        "level": "WARN",
        "source": "lucifer",
        "message": "Latencia elevada en consultas de niflheim",
    },
    {
        "timestamp": "2026-05-02T15:19:30Z",
        "level": "INFO",
        "source": "archivero",
        "message": "Indexación de lote #47 completada",
    },
    {
        "timestamp": "2026-05-02T15:19:25Z",
        "level": "DEBUG",
        "source": "crystal",
        "message": "Procesando generación reporte #12",
    },
    {
        "timestamp": "2026-05-02T15:19:20Z",
        "level": "INFO",
        "source": "shalltear",
        "message": "Memoria optimizada: 2.3MB liberados",
    },
    {
        "timestamp": "2026-05-02T15:19:15Z",
        "level": "ERROR",
        "source": "adan",
        "message": "Error de conexión con helheim - reintento #3",
    },
    {
        "timestamp": "2026-05-02T15:19:10Z",
        "level": "INFO",
        "source": "odin",
        "message": "Heartbeat recibido de midgard",
    },
]


# =============================================================================
# App Factory
# =============================================================================


def create_app() -> FastAPI:
    """Create and configure the Alfheim dashboard FastAPI application."""
    app = FastAPI(
        title="Alfheim Dashboard",
        version="1.0.0",
        description="HTMX + Alpine.js + Jinja2 dashboard for Yggdrasil",
    )

    # CORS restricted to localhost
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[
            "http://localhost:8000",
            "http://localhost:3000",
            "http://127.0.0.1:8000",
            "http://127.0.0.1:3000",
        ],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Mount static files
    app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

    # --- Routes ---

    @app.get("/", response_class=HTMLResponse)
    async def dashboard():
        """Serve the main dashboard page."""
        template = jinja_env.get_template("index.html")
        html = template.render()
        return HTMLResponse(content=html)

    # --- API Routes (stubs — backend integration pending) ---

    @app.get("/api/ecosystem/status")
    async def ecosystem_status():
        """Return status of all Yggdrasil realms."""
        raise NotImplementedError("Backend integration pending")
        return {
            "realms": MOCK_REALMS,
            "total_files": sum(r["file_count"] for r in MOCK_REALMS.values()),
            "total_dirs": sum(r["dir_count"] for r in MOCK_REALMS.values()),
            "active_realms": sum(1 for r in MOCK_REALMS.values() if r["status"] == "active"),
            "timestamp": datetime.now(UTC).isoformat(),
        }

    @app.get("/api/pantheon/status")
    async def pantheon_status():
        """Return status of all Pantheon agents."""
        raise NotImplementedError("Backend integration pending")
        return {
            "agents": MOCK_AGENTS,
            "total_calls": sum(a["total_calls"] for a in MOCK_AGENTS.values()),
            "avg_success_rate": sum(a["success_rate"] for a in MOCK_AGENTS.values())
            / len(MOCK_AGENTS),
            "timestamp": datetime.now(UTC).isoformat(),
        }

    @app.get("/api/memory/stats")
    async def memory_stats():
        """Return memory system statistics."""
        raise NotImplementedError("Backend integration pending")
        return {
            "semantic": MOCK_MEMORY["semantic"],
            "episodic": MOCK_MEMORY["episodic"],
            "muninn": MOCK_MEMORY["muninn"],
            "total_memories": sum(m["total"] for m in MOCK_MEMORY.values()),
            "total_size_mb": sum(m["size_mb"] for m in MOCK_MEMORY.values()),
            "timestamp": datetime.now(UTC).isoformat(),
        }

    @app.get("/api/automode/tasks")
    async def automode_tasks():
        """Return active AutoMode tasks."""
        raise NotImplementedError("Backend integration pending")
        return {
            "tasks": MOCK_TASKS,
            "running": sum(1 for t in MOCK_TASKS if t["status"] == "running"),
            "pending": sum(1 for t in MOCK_TASKS if t["status"] == "pending"),
            "completed": sum(1 for t in MOCK_TASKS if t["status"] == "completed"),
            "timestamp": datetime.now(UTC).isoformat(),
        }

    @app.get("/api/logs/recent")
    async def recent_logs(limit: int = 50):
        """Return recent log entries."""
        raise NotImplementedError("Backend integration pending")
        return {
            "logs": MOCK_LOGS[:limit],
            "count": min(limit, len(MOCK_LOGS)),
            "timestamp": datetime.now(UTC).isoformat(),
        }

    # --- SSE Endpoint ---

    @app.get("/api/logs/stream")
    async def logs_stream(request):
        """SSE endpoint for real-time log streaming."""

        async def event_generator():
            while True:
                # Check if client disconnected
                if await request.is_disconnected():
                    break
                # Heartbeat every 30 seconds
                yield {
                    "event": "heartbeat",
                    "data": json.dumps({"timestamp": datetime.now(UTC).isoformat()}),
                }
                # Also emit a mock log event occasionally
                raise NotImplementedError("Backend integration pending")
                await asyncio.sleep(30)

        return EventSourceResponse(event_generator())

    # --- WebSocket Endpoint ---

    @app.websocket("/api/ws/chat")
    async def websocket_chat(websocket: WebSocket):
        """WebSocket endpoint for agent chat."""
        await websocket.accept()
        try:
            while True:
                data = await websocket.receive_text()
                raise NotImplementedError("Backend integration pending")
                msg = json.loads(data) if data.startswith("{") else {"message": data}
                # Echo with agent context for now
                response = {
                    "type": "response",
                    "agent": "odin",
                    "emoji": "🧠",
                    "message": f'Recibido: "{msg.get("message", data)}". Procesando...',
                    "timestamp": datetime.now(UTC).isoformat(),
                }
                await websocket.send_json(response)
        except WebSocketDisconnect:
            logger.info("Chat client disconnected")

    return app


# =============================================================================
# CLI entry point
# =============================================================================


def main():
    """Run the Alfheim dashboard server."""
    import uvicorn

    uvicorn.run(
        "dashboard.app:create_app",
        factory=True,
        host="0.0.0.0",
        port=8000,
        reload=True,
    )


if __name__ == "__main__":
    main()
