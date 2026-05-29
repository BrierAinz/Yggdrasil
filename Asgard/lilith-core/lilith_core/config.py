<<<<<<< HEAD
"""Configuration loader for Yggdrasil ecosystem."""

import os
from pathlib import Path
from dataclasses import dataclass, field
from typing import Optional

import yaml
from dotenv import load_dotenv


@dataclass
class YggdrasilConfig:
    """Root configuration for the Yggdrasil ecosystem."""
    root: Path = field(default_factory=lambda: Path(os.getenv("YGGDRASIL_ROOT", ".")))
    version: str = "5.1.0"
    log_level: str = "INFO"
    log_file: str = "yggdrasil.log"
    
    # API
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    orchestrator_port: int = 8001
    memory_port: int = 8002
    
    # LLM Providers
    lm_studio_url: str = "http://localhost:1234/v1"
    openai_api_base: Optional[str] = None
    openai_api_key: Optional[str] = None
    
    # Security
    blocked_commands: list = field(default_factory=lambda: ["rm -rf", "format", "cipher", "shutdown"])
    sensitive_files: list = field(default_factory=lambda: [".env", "*.key", "*.pem", "*.p12"])
    
    def __post_init__(self):
        load_dotenv(self.root / ".env")
        self.openai_api_base = os.getenv("OPENAI_API_BASE", self.openai_api_base)
        self.openai_api_key = os.getenv("OPENAI_API_KEY", self.openai_api_key)
    
    @classmethod
    def load(cls, path: Optional[Path] = None) -> "YggdrasilConfig":
        """Load config from YAML or defaults."""
        cfg = cls()
        if path and path.exists():
            with open(path) as f:
                data = yaml.safe_load(f) or {}
            for k, v in data.items():
                if hasattr(cfg, k):
                    setattr(cfg, k, v)
        return cfg
    
    @property
    def asgard(self) -> Path:
        return self.root / "Asgard"
    
    @property
    def realms(self) -> list[Path]:
        return [
            self.root / r for r in [
                "Asgard", "Alfheim", "Vanaheim", "Muspelheim",
                "Niflheim", "Svartalfheim", "Midgard", "Helheim", "Jotunheim"
            ]
        ]


_config: Optional[YggdrasilConfig] = None

def get_config() -> YggdrasilConfig:
    """Get or create global config singleton."""
    global _config
    if _config is None:
        _config = YggdrasilConfig.load()
    return _config
=======
"""Central configuration management for the Lilith agent ecosystem."""

import json
from pathlib import Path
from typing import Any


class Config:
    """Configuracion centralizada de Lilith."""

    def __init__(self, root_path: Path | None = None) -> None:
        """Initialise Config with an optional root path.

        Args:
            root_path: Path to the Lilith config directory.
                       Defaults to ``~/.lilith``.

        """
        self.root = root_path or Path.home() / ".lilith"
        self.root.mkdir(parents=True, exist_ok=True)
        self.config_file = self.root / "config.json"
        self._data: dict[str, Any] = self._load()

    def _load(self) -> dict[str, Any]:
        """Load configuration from disk, falling back to defaults."""
        if self.config_file.exists():
            return json.loads(self.config_file.read_text(encoding="utf-8"))
        return self._defaults()

    def _defaults(self) -> dict[str, Any]:
        """Return sensible default configuration values."""
        return {
            "model": "auto",
            "lm_studio_url": "http://localhost:1234/v1",
            "max_context": 8192,
            "temperature": 0.7,
        }

    def get(self, key: str, default: Any = None) -> Any:
        """Recuperar un valor de configuración por clave."""
        return self._data.get(key, default)

    def set(self, key: str, value: Any) -> None:
        """Establecer un valor de configuración y guardar en disco."""
        self._data[key] = value
        self._save()

    def _save(self) -> None:
        """Persist the current configuration to disk as JSON."""
        self.config_file.write_text(
            json.dumps(self._data, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )
>>>>>>> origin/main
