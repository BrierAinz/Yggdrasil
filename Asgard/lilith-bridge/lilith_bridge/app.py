"""Hermes Bridge — FastAPI application entry-point.

This module is a thin wrapper.  All bridge logic lives in
``bifrost_integration.create_standalone_app()``.  Running this module
directly starts the bridge as a standalone server on port 9001.

Usage::

    python -m lilith_bridge.app               # default host/port
    uvicorn lilith_bridge.app:app --port 9001 # via uvicorn
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import uvicorn


if TYPE_CHECKING:
    from fastapi import FastAPI

from .bifrost_integration import BridgeConfig, create_standalone_app


app = create_standalone_app()


def create_app(config: BridgeConfig | None = None) -> FastAPI:
    """Factory function for uvicorn import string and CLI entry-point."""
    return create_standalone_app(config)


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=9001)
