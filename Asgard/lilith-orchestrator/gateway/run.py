"""
Lilith Gateway Runner
=====================
Entry point for starting the gateway server with production-ready defaults.
Supports uvloop for improved async performance on Unix systems.
"""

import os

# Install uvloop before importing the FastAPI app — it must be set before
# the asyncio event loop is created.  uvloop is optional and only available
# on Unix; if it's missing we silently fall back to the default event loop.
try:
    import uvloop

    uvloop.install()
    print("[run] uvloop installed — using high-performance event loop")
except ImportError:
    print("[run] uvloop not available — using default asyncio event loop")

import uvicorn

# ---------------------------------------------------------------------------
# Environment-driven configuration
# ---------------------------------------------------------------------------
HOST = os.environ.get("LILITH_HOST", "0.0.0.0")
PORT = int(os.environ.get("LILITH_PORT", "8000"))
WORKERS = int(os.environ.get("LILITH_WORKERS", "1"))
LOG_LEVEL = os.environ.get("LILITH_LOG_LEVEL", "info").lower()

# The import path for the FastAPI app object inside the gateway package.
APP_REF = "gateway.gateway:app"


def main() -> None:
    """Start the Lilith Gateway server."""
    print(f"[run] Starting Lilith Gateway on {HOST}:{PORT} ({WORKERS} worker(s))")
    uvicorn.run(
        APP_REF,
        host=HOST,
        port=PORT,
        workers=WORKERS,
        log_level=LOG_LEVEL,
        # Production niceties
        access_log=True,
        server_header=False,
    )


if __name__ == "__main__":
    main()
