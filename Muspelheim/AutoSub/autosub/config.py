"""AutoSub configuration module — TOML-based settings."""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

try:
    import tomllib
except ImportError:
    import tomli as tomllib  # type: ignore[no-redef]


DEFAULT_CONFIG_NAME = "autosub.toml"


@dataclass
class AutoSubConfig:
    """Configuration for AutoSub."""

    model_size: str = "base"
    device: str = "auto"
    compute_type: str = "int8"
    default_language: str | None = None
    default_translate_to: str | None = None
    default_format: str = "srt"
    cache_dir: str = ""
    output_dir: str = ""
    batch_recursive: bool = False

    @classmethod
    def from_toml(cls, path: str | Path) -> "AutoSubConfig":
        """Load configuration from a TOML file.

        Args:
            path: Path to the TOML configuration file.

        Returns:
            AutoSubConfig with values from the file.

        Raises:
            FileNotFoundError: If the config file does not exist.
        """
        path = Path(path)
        if not path.exists():
            raise FileNotFoundError(f"Config file not found: {path}")

        with open(path, "rb") as f:
            data = tomllib.load(f)

        # Extract [autosub] section if present, otherwise use root
        section = data.get("autosub", data)

        defaults = cls()
        return cls(
            model_size=section.get("model_size", defaults.model_size),
            device=section.get("device", defaults.device),
            compute_type=section.get("compute_type", defaults.compute_type),
            default_language=section.get("default_language"),
            default_translate_to=section.get("default_translate_to"),
            default_format=section.get("default_format", defaults.default_format),
            cache_dir=section.get("cache_dir", defaults.cache_dir),
            output_dir=section.get("output_dir", defaults.output_dir),
            batch_recursive=section.get("batch_recursive", defaults.batch_recursive),
        )

    @classmethod
    def find_config(cls) -> "AutoSubConfig":
        """Search for config file in standard locations.

        Looks in:
        1. Current directory (autosub.toml)
        2. ~/.config/autosub/autosub.toml
        3. ~/.autosub.toml

        Returns:
            AutoSubConfig from first found config, or defaults.
        """
        search_paths = [
            Path(DEFAULT_CONFIG_NAME),
            Path.home() / ".config" / "autosub" / DEFAULT_CONFIG_NAME,
            Path.home() / f".{DEFAULT_CONFIG_NAME}",
        ]

        for path in search_paths:
            if path.exists():
                return cls.from_toml(path)

        return cls()

    def to_toml_dict(self) -> dict:
        """Convert config to a TOML-serializable dictionary."""
        return {
            "autosub": {
                "model_size": self.model_size,
                "device": self.device,
                "compute_type": self.compute_type,
                "default_language": self.default_language,
                "default_translate_to": self.default_translate_to,
                "default_format": self.default_format,
                "cache_dir": self.cache_dir,
                "output_dir": self.output_dir,
                "batch_recursive": self.batch_recursive,
            }
        }
