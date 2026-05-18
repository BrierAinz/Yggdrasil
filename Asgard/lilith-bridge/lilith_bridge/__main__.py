"""Lilith Bridge — CLI entry point."""

from __future__ import annotations

import argparse
import logging
from typing import TYPE_CHECKING

import uvicorn


if TYPE_CHECKING:
    from fastapi import FastAPI


def main() -> None:
    """Start the Hermes Bridge server."""
    parser = argparse.ArgumentParser(
        prog="lilith-bridge",
        description="Bidirectional gateway connecting Yggdrasil to Hermes Agent",
    )
    parser.add_argument("--host", default=None, help="Bind host (default: from config or 0.0.0.0)")
    parser.add_argument(
        "--port", type=int, default=None, help="Bind port (default: from config or 9001)"
    )
    parser.add_argument("--reload", action="store_true", help="Enable auto-reload for development")
    parser.add_argument(
        "--log-level",
        default="info",
        choices=["debug", "info", "warning", "error"],
        help="Log level",
    )
    parser.add_argument("--config", default=None, help="Path to Yggdrasil config.yaml")
    args = parser.parse_args()

    # Configure logging.
    logging.basicConfig(
        level=getattr(logging, args.log_level.upper()),
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )
    logger = logging.getLogger("lilith-bridge")

    # Load config.
    from .config import load_bridge_config

    config = load_bridge_config(args.config)

    host = args.host or config.host
    port = args.port or config.port

    logger.info("Starting Hermes Bridge on %s:%d", host, port)
    logger.info("Hermes endpoint: %s", config.hermes_url)

    # Run the server.
    app = create_app()

    uvicorn.run(
        app,
        host=host,
        port=port,
        log_level=args.log_level,
        reload=args.reload,
    )


def create_app() -> FastAPI:
    """Factory function for uvicorn import string."""
    from .app import create_app as _create
    from .config import load_bridge_config

    config = load_bridge_config()
    return _create(config)


if __name__ == "__main__":
    main()
