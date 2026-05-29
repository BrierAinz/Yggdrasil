#!/usr/bin/env python
"""Entry-point for Lilith API with uvloop (if available) for maximum throughput."""

import logging
import sys


logger = logging.getLogger(__name__)


def main() -> None:
    """Start the Lilith API server with uvloop acceleration (if available)."""
    import uvicorn

    # Try to install uvloop as the event-loop policy for maximum async perf.
    try:
        import uvloop

        uvloop.install()
        logger.info("uvloop event loop installed")
    except ImportError:
        logger.info("uvloop not available – falling back to asyncio")

    uvicorn.run(
        "lilith_api.main:app",
        host="0.0.0.0",
        port=8000,
        reload="--reload" in sys.argv or "--dev" in sys.argv,
        loop="auto",  # uvloop will be used automatically if installed
        http="auto",  # let uvicorn pick httptools if available
    )


if __name__ == "__main__":
    main()
