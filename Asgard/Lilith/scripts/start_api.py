"""
Arranque de la API en Windows con event loop compatible con Playwright (subprocess).
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

if sys.platform.startswith("win"):
    import asyncio

    try:
        asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())
    except Exception:
        pass

if __name__ == "__main__":
    import uvicorn

    os.chdir(ROOT)
    reload_enabled = (os.getenv("LILITH_RELOAD") or "").strip().lower() in (
        "1",
        "true",
        "yes",
        "on",
    )
    port = int(os.environ.get("LILITH_API_PORT") or os.environ.get("PORT") or "8000")

    run_kwargs: dict = {
        "app": "src.api.server:app",
        "host": os.environ.get("LILITH_API_HOST", "127.0.0.1"),
        "port": port,
        "reload": reload_enabled,
    }
    if reload_enabled:
        run_kwargs["reload_dirs"] = [str(ROOT / "src")]

    uvicorn.run(**run_kwargs)
