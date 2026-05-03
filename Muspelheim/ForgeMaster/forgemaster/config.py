"""ForgeMaster configuration management.

Supports loading configuration from:
1. YGGDRASIL_ROOT environment variable
2. ~/.forgemaster/config.yaml
3. Built-in defaults

Usage:
    from forgemaster.config import Config, load_config

    cfg = load_config()
    print(cfg.scan_dirs)
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

# ─── Default paths ────────────────────────────────────────────────────────────

DEFAULT_CONFIG_DIR = Path.home() / ".forgemaster"
DEFAULT_CONFIG_FILE = DEFAULT_CONFIG_DIR / "config.yaml"
DEFAULT_CATALOG_PATH = DEFAULT_CONFIG_DIR / "catalog.db"

DEFAULT_SCAN_DIRS = [
    str(Path.home() / ".cache" / "huggingface"),
    str(Path.home() / ".cache" / "lm-studio"),
]

DEFAULT_GPU_PROFILE = "RTX 3060"


# ─── Config dataclass ─────────────────────────────────────────────────────────


@dataclass
class Config:
    """ForgeMaster configuration."""

    scan_dirs: list[str] = field(default_factory=lambda: list(DEFAULT_SCAN_DIRS))
    gpu_profile: str = DEFAULT_GPU_PROFILE
    catalog_path: str = str(DEFAULT_CATALOG_PATH)

    # Derived from YGGDRASIL_ROOT if set
    yggdrasil_root: str | None = None

    def resolve_scan_dirs(self) -> list[Path]:
        """Return scan_dirs as resolved Path objects, expanding ~ and env vars."""
        resolved = []
        for d in self.scan_dirs:
            p = Path(os.path.expandvars(os.path.expanduser(d)))
            if p.exists():
                resolved.append(p)
        return resolved

    def resolve_catalog_path(self) -> Path:
        """Return catalog_path as a resolved Path."""
        return Path(os.path.expandvars(os.path.expanduser(self.catalog_path)))


# ─── Load / save ──────────────────────────────────────────────────────────────


def load_config(config_path: str | Path | None = None) -> Config:
    """Load configuration from YAML file with environment variable support.

    Priority:
        1. YGGDRASIL_ROOT env var (overrides scan_dirs and catalog_path)
        2. Config file at ``config_path`` or ``~/.forgemaster/config.yaml``
        3. Built-in defaults

    If the config file does not exist, returns a Config with defaults.
    """
    yggdrasil_root = os.environ.get("YGGDRASIL_ROOT")

    # Determine config file path
    if config_path is not None:
        cfg_file = Path(os.path.expandvars(os.path.expanduser(str(config_path))))
    else:
        cfg_file = DEFAULT_CONFIG_FILE

    # Start with defaults
    cfg_dict: dict[str, Any] = {}

    # Load YAML if it exists
    if cfg_file.exists():
        with open(cfg_file, "r") as f:
            raw = yaml.safe_load(f)
            if isinstance(raw, dict):
                cfg_dict = raw

    # Build Config from dict
    scan_dirs = cfg_dict.get("scan_dirs", list(DEFAULT_SCAN_DIRS))
    gpu_profile = cfg_dict.get("gpu_profile", DEFAULT_GPU_PROFILE)
    catalog_path = cfg_dict.get("catalog_path", str(DEFAULT_CATALOG_PATH))

    # If YGGDRASIL_ROOT is set, prepend it to scan_dirs and adjust catalog_path
    if yggdrasil_root:
        root = Path(yggdrasil_root)
        # Add YGGDRASIL_ROOT/models as a scan dir if not already present
        models_dir = str(root / "models")
        if models_dir not in scan_dirs:
            scan_dirs.insert(0, models_dir)
        # Override catalog path to be inside YGGDRASIL_ROOT
        catalog_path = str(root / ".forgemaster" / "catalog.db")

    return Config(
        scan_dirs=scan_dirs,
        gpu_profile=gpu_profile,
        catalog_path=catalog_path,
        yggdrasil_root=yggdrasil_root,
    )


def save_config(cfg: Config, config_path: str | Path | None = None) -> Path:
    """Save configuration to a YAML file.

    Args:
        cfg: The Config object to save.
        config_path: Target file path. Defaults to ``~/.forgemaster/config.yaml``.

    Returns:
        The path where the config was saved.
    """
    if config_path is not None:
        cfg_file = Path(os.path.expandvars(os.path.expanduser(str(config_path))))
    else:
        cfg_file = DEFAULT_CONFIG_FILE

    cfg_file.parent.mkdir(parents=True, exist_ok=True)

    data = {
        "scan_dirs": cfg.scan_dirs,
        "gpu_profile": cfg.gpu_profile,
        "catalog_path": cfg.catalog_path,
    }

    with open(cfg_file, "w") as f:
        yaml.dump(data, f, default_flow_style=False, sort_keys=False)

    return cfg_file


def set_config_value(
    key: str, value: str, config_path: str | Path | None = None
) -> Config:
    """Set a single configuration value and save.

    Supports dotted keys like ``scan_dirs.0`` to set list items by index.

    Args:
        key: Dotted config key (e.g. ``gpu_profile``, ``scan_dirs.0``).
        value: The new value as a string.
        config_path: Optional config file path.

    Returns:
        The updated Config object.
    """
    cfg = load_config(config_path)

    parts = key.split(".")
    if len(parts) == 1:
        # Simple key
        if parts[0] == "scan_dirs":
            # Treat as comma-separated list
            cfg.scan_dirs = [v.strip() for v in value.split(",")]
        else:
            setattr(cfg, parts[0], value)
    elif len(parts) == 2 and parts[0] == "scan_dirs" and parts[1].isdigit():
        # List index assignment like scan_dirs.0
        idx = int(parts[1])
        while len(cfg.scan_dirs) <= idx:
            cfg.scan_dirs.append("")
        cfg.scan_dirs[idx] = value
    else:
        raise ValueError(f"Unsupported config key: {key}")

    save_config(cfg, config_path)
    return cfg
