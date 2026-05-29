"""Backward-compat shim — prefer importing from alfheim.dashboard instead."""

import warnings


warnings.warn(
    "Importing from 'dashboard' is deprecated; use 'alfheim.dashboard' instead.",
    DeprecationWarning,
    stacklevel=2,
)

from alfheim.dashboard.app import create_app


__version__ = "1.0.0"
__all__ = ["create_app"]
