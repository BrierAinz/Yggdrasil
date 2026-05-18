"""Lilith API — FastAPI REST interface with lazy init, DI, and orjson.

Provides the HTTP API for the Lilith agent engine, with endpoints for
chat, tool execution, memory, health checks, and status.

Key patterns:
- Lazy initialization via ``_LazyState`` — heavy modules load on first request only.
- Dependency injection via FastAPI ``Depends()`` for all stateful routes.
- orjson for JSON serialization when available (~10x faster than stdlib).
- CORS restricted to localhost origins.
"""

from .main import app, get_config, get_engine, get_memory, get_tools


__version__ = "2.2.0"

__all__ = [
    "app",
    "get_config",
    "get_engine",
    "get_memory",
    "get_tools",
]
