"""Configuration loader for Yggdrasil ecosystem."""

import os
from dataclasses import dataclass, field
from pathlib import Path

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
    openai_api_base: str | None = None
    openai_api_key: str | None = None

    # Security
    blocked_commands: list = field(
        default_factory=lambda: ["rm -rf", "format", "cipher", "shutdown"]
    )
    sensitive_files: list = field(default_factory=lambda: [".env", "*.key", "*.pem", "*.p12"])

    def __post_init__(self):
        load_dotenv(self.root / ".env")
        self.openai_api_base = os.getenv("OPENAI_API_BASE", self.openai_api_base)
        self.openai_api_key = os.getenv("OPENAI_API_KEY", self.openai_api_key)

    @classmethod
    def load(cls, path: Path | None = None) -> "YggdrasilConfig":
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
            self.root / r
            for r in [
                "Asgard",
                "Alfheim",
                "Vanaheim",
                "Muspelheim",
                "Niflheim",
                "Svartalfheim",
                "Midgard",
                "Helheim",
                "Jotunheim",
            ]
        ]


_config: YggdrasilConfig | None = None


def get_config() -> YggdrasilConfig:
    """Get or create global config singleton."""
    global _config
    if _config is None:
        _config = YggdrasilConfig.load()
    return _config
