"""ForgeMaster structured logging with RichHandler integration.

Configures logging once at startup based on verbosity flags:
  --verbose   → DEBUG level
  (default)   → INFO level
  --quiet     → WARNING level

Usage:
    from forgemaster.logging import configure_logging, get_logger

    configure_logging(verbose=False, quiet=False)
    log = get_logger(__name__)
    log.info("Scan complete")
"""

from __future__ import annotations

import logging
from typing import Optional

from rich.logging import RichHandler

# Module-level flag so we only configure once
_CONFIGURED = False

# Map (verbose, quiet) → logging level
_LEVEL_MAP: dict[tuple[bool, bool], int] = {
    (True, False): logging.DEBUG,
    (False, False): logging.INFO,
    (False, True): logging.WARNING,
    (True, True): logging.DEBUG,  # verbose wins over quiet
}


def configure_logging(
    verbose: bool = False,
    quiet: bool = False,
    level: Optional[int] = None,
) -> None:
    """Configure the root ForgeMaster logger with a RichHandler.

    This should be called once at CLI startup (via the ``--verbose`` /
    ``--quiet`` flags).  Subsequent calls are no-ops.

    Args:
        verbose: If True, set level to DEBUG.
        quiet: If True, set level to WARNING.
        level: Explicit logging level (overrides verbose/quiet).
    """
    global _CONFIGURED
    if _CONFIGURED:
        return
    _CONFIGURED = True

    if level is not None:
        effective_level = level
    else:
        effective_level = _LEVEL_MAP.get((verbose, quiet), logging.INFO)

    handler = RichHandler(
        show_time=False,
        show_path=False,
        markup=True,
        rich_tracebacks=True,
    )
    handler.setLevel(effective_level)

    logger = logging.getLogger("forgemaster")
    logger.setLevel(effective_level)
    logger.handlers.clear()
    logger.addHandler(handler)
    logger.propagate = False

    # If verbose, also bump the root logger so third-party noise is visible
    if verbose:
        root = logging.getLogger()
        root.setLevel(logging.WARNING)


def get_logger(name: str) -> logging.Logger:
    """Return a child logger under the ``forgemaster`` namespace.

    Args:
        name: Typically ``__name__`` of the calling module.

    Returns:
        A ``logging.Logger`` configured under ``forgemaster``.
    """
    if not name.startswith("forgemaster"):
        name = f"forgemaster.{name}"
    return logging.getLogger(name)
