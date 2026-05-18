"""Tests for lilith-cli — Yggdrasil Agent CLI."""

import sys
from pathlib import Path


# Ensure lilith_cli is importable
_PKG_DIR = str(Path(__file__).resolve().parent.parent)
if _PKG_DIR not in sys.path:
    sys.path.insert(0, _PKG_DIR)

from lilith_cli import __version__


def test_version_constant():
    """Module-level __version__ should be '3.0.0'."""
    assert __version__ == "3.0.0"


def test_app_instance():
    """Cyclopts App should be created with correct name and version."""
    from lilith_cli.main import app

    # Cyclopts name can be a tuple or string
    name = app.name if isinstance(app.name, str) else app.name[0]
    assert name == "yggdrasil"
    assert app.version == "3.0.0"


def test_config_loads():
    """Config module should be importable and have expected attributes."""
    from lilith_cli.config import CONFIG_DIR, load_config, save_config

    assert callable(load_config)
    assert callable(save_config)
    assert isinstance(CONFIG_DIR, Path)


def test_is_wsl():
    """_is_wsl should return a boolean."""
    from lilith_cli.main import _is_wsl

    result = _is_wsl()
    assert isinstance(result, bool)


def test_resolve_yggdrasil_root():
    """_resolve_yggdrasil_root should return a Path pointing to the workspace."""
    from lilith_cli.main import _resolve_yggdrasil_root

    root = _resolve_yggdrasil_root()
    assert isinstance(root, Path)
    assert (root / "pyproject.toml").exists()
