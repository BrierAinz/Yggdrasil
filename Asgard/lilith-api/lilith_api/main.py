"""Lilith API – FastAPI application with lazy init, DI, and orjson."""

from __future__ import annotations

import threading
from typing import Any

from fastapi import Depends, FastAPI, Query
from pydantic import BaseModel


# ---------------------------------------------------------------------------
# orjson integration – faster JSON serialisation with stdlib fallback
# ---------------------------------------------------------------------------
try:
    import orjson

    def _orjson_dumps(obj: Any) -> str:
        return orjson.dumps(obj).decode()

    class ORJSONResponse:
        """Drop-in replacement that uses orjson under the hood."""

        from starlette.responses import JSONResponse as _Base

        def __init_subclass__(cls, **kwargs: Any) -> None:
            """Register subclass for orjson serialization."""
            super().__init_subclass__(**kwargs)

        @classmethod
        def _serialize(cls, obj: Any) -> str:
            return _orjson_dumps(obj)

    _HAS_ORJSON = True
except ImportError:  # pragma: no cover
    _HAS_ORJSON = False

try:
    from fastapi.responses import JSONResponse as FastAPIJSONResponse

    if _HAS_ORJSON:

        class _ORJSONResponse(FastAPIJSONResponse):
            """FastAPI response class using orjson for faster JSON serialization."""

            media_type = "application/json"

            def render(self, content: Any) -> bytes:
                return orjson.dumps(content)

        DefaultResponse = _ORJSONResponse
    else:
        DefaultResponse = FastAPIJSONResponse
except Exception:  # pragma: no cover
    DefaultResponse = None  # type: ignore[assignment,misc]

# ---------------------------------------------------------------------------
# Application factory
# ---------------------------------------------------------------------------
app = FastAPI(
    title="Lilith API",
    version="2.2.0",
    default_response_class=DefaultResponse,
)

# CORS – restrict to localhost for dev environments
from starlette.middleware.cors import CORSMiddleware


app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost",
        "http://localhost:3000",
        "http://localhost:8000",
        "http://127.0.0.1",
        "http://127.0.0.1:3000",
        "http://127.0.0.1:8000",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------------------------------------------------------------------------
# Lazy singletons – created once on first request, never at import time
# ---------------------------------------------------------------------------
_lock = threading.Lock()


class _LazyState:
    """Holds lazily-initialised application state behind a lock."""

    __slots__ = ("config", "engine", "memory", "tools")

    def __init__(self) -> None:
        self.config: Any | None = None
        self.memory: Any | None = None
        self.engine: Any | None = None
        self.tools: Any | None = None

    def _ensure_config(self) -> Any:
        if self.config is None:
            from lilith_core.config import Config

            self.config = Config()
        return self.config

    def _ensure_memory(self) -> Any:
        if self.memory is None:
            from lilith_memory.store import MemoryStore

            cfg = self._ensure_config()
            self.memory = MemoryStore(cfg.root / "memory.db")
        return self.memory

    def _ensure_engine(self) -> Any:
        if self.engine is None:
            from lilith_orchestrator.engine import LilithEngine

            cfg = self._ensure_config()
            mem = self._ensure_memory()
            self.engine = LilithEngine(cfg, mem)
        return self.engine

    def _ensure_tools(self) -> Any:
        if self.tools is None:
            from lilith_tools.registry import ToolRegistry

            self.tools = ToolRegistry
        return self.tools


_state = _LazyState()


# ---------------------------------------------------------------------------
# FastAPI dependency injection helpers
# ---------------------------------------------------------------------------
def get_memory() -> Any:
    """Return the lazily-created MemoryStore singleton."""
    with _lock:
        return _state._ensure_memory()


def get_engine() -> Any:
    """Return the lazily-created LilithEngine singleton."""
    with _lock:
        return _state._ensure_engine()


def get_config() -> Any:
    """Return the lazily-created Config singleton."""
    with _lock:
        return _state._ensure_config()


def get_tools() -> Any:
    """Return the lazily-created ToolRegistry class reference."""
    with _lock:
        return _state._ensure_tools()


# ---------------------------------------------------------------------------
# Request / response models
# ---------------------------------------------------------------------------
class ChatRequest(BaseModel):
    """Request body for the /chat endpoint."""

    message: str
    model: str | None = None


class ChatResponse(BaseModel):
    """Response body for the /chat endpoint."""

    response: str
    context_used: list[str]
    tool_call: dict[str, Any]


class ToolCallRequest(BaseModel):
    """Request body for the /tools/execute endpoint."""

    tool: str
    params: dict[str, Any] = {}


class MemoryStoreRequest(BaseModel):
    """Request body for the POST /memory endpoint."""

    text: str
    metadata: dict[str, Any] = {}


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------
@app.post("/chat", response_model=ChatResponse)
async def chat(
    req: ChatRequest,
    engine: Any = Depends(get_engine),
) -> ChatResponse:
    """Process a chat message through the Lilith engine and return the response."""
    result = engine.process(req.message)
    response_text = f"Recibido: {req.message}"
    if result["tool_call"]:
        response_text += f" (tool detectado: {result['tool_call']})"
    return ChatResponse(
        response=response_text,
        context_used=[c["content"] for c in result["context"]],
        tool_call=result["tool_call"],
    )


@app.post("/tools/execute")
async def execute_tool(
    req: ToolCallRequest,
    engine: Any = Depends(get_engine),
) -> dict[str, Any]:
    """Execute a named tool with the given parameters."""
    return engine.execute_tool(req.tool, req.params)


@app.get("/tools")
async def list_tools(
    tools: Any = Depends(get_tools),
) -> dict[str, str]:
    """List all registered tools (name → description)."""
    return tools.list_tools()


@app.get("/health")
async def health() -> dict[str, Any]:
    """Lightweight health-check endpoint – no heavy initialisation required."""
    conf = get_config()
    tools = get_tools()
    return {
        "status": "ok",
        "version": "2.2.0",
        "tools": len(tools.list_tools()),
        "model": conf.get("model", "auto"),
    }


@app.get("/status")
async def status(
    memory: Any = Depends(get_memory),
) -> dict[str, Any]:
    """Detailed status endpoint with memory and tool counts."""
    conf = get_config()
    tools = get_tools()
    return {
        "version": "2.2.0",
        "model": conf.get("model", "auto"),
        "tools_available": len(tools.list_tools()),
        "memory_entries": memory.count_entries(),
    }


@app.get("/memory")
async def memory_recall(
    query: str = Query(...),
    k: int = 5,
    memory: Any = Depends(get_memory),
) -> list[dict[str, Any]]:
    """Search stored memories by semantic similarity to *query*."""
    return memory.search(query, k=k)


@app.post("/memory")
async def memory_store(
    req: MemoryStoreRequest,
    memory: Any = Depends(get_memory),
) -> dict[str, str]:
    """Store a new memory entry with optional metadata."""
    memory.store(req.text, req.metadata)
    return {"status": "stored", "text": req.text[:100]}
