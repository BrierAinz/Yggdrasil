"""Configuration for the Hermes Bridge."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field


class BridgeConfig(BaseModel):
    """Configuration for the Hermes-Yggdrasil bridge."""

    # ── Bridge server ──────────────────────────────────────────────
    host: str = "0.0.0.0"
    port: int = 9001
    auth_token: str | None = None
    cors_origins: list[str] = Field(
        default_factory=lambda: [
            "http://localhost",
            "http://localhost:3000",
            "http://localhost:8000",
            "http://localhost:9000",
            "http://127.0.0.1",
        ],
    )

    # ── Hermes connection ──────────────────────────────────────────
    hermes_url: str = "http://localhost:8080"
    hermes_api_key: str | None = None
    hermes_timeout: float = 120.0
    hermes_max_retries: int = 3

    # ── MCP connection (alternative to HTTP) ────────────────────────
    hermes_mcp_command: list[str] = Field(default_factory=lambda: ["hermes", "mcp", "serve"])
    hermes_mcp_url: str | None = None

    # ── Lilith engine ───────────────────────────────────────────────
    lilith_memory_db: str = "~/.yggdrasil/bridge_memory.db"
    lilith_skills_dir: str | None = None  # Auto-detected if None

    # ── Behavior ────────────────────────────────────────────────────
    max_history_turns: int = 20
    default_model: str = "auto"  # Let Hermes choose
    enable_streaming: bool = True

    model_config = {"extra": "ignore"}

    def resolve_skills_dir(self) -> Path | None:
        """Resolve the skills directory path.

        If not explicitly set, tries to auto-detect from the monorepo.
        """
        if self.lilith_skills_dir:
            return Path(self.lilith_skills_dir).expanduser()

        # Auto-detect: look for Svartalfheim/Docs/skills in parent dirs.
        candidates = [
            Path(__file__).parent.parent.parent.parent / "Svartalfheim" / "Docs" / "skills",
            Path.home() / ".yggdrasil" / "skills",
        ]
        for candidate in candidates:
            if candidate.exists():
                return candidate
        return None

    def resolve_memory_db(self) -> Path:
        """Resolve the memory database path."""
        return Path(self.lilith_memory_db).expanduser()


def load_bridge_config(yaml_path: Path | str | None = None) -> BridgeConfig:
    """Load bridge configuration from YAML.

    Falls back to ``~/.yggdrasil/config.yaml`` and extracts the ``bridge:``
    section. If no config exists, returns defaults.
    """
    import re

    try:
        import yaml
    except ImportError:
        return BridgeConfig()

    if yaml_path is None:
        yaml_path = Path.home() / ".yggdrasil" / "config.yaml"

    path = Path(yaml_path)
    if not path.exists():
        return BridgeConfig()

    raw_text = path.read_text(encoding="utf-8")

    # Interpolate environment variables.
    def _replace_env(match: re.Match) -> str:
        import os

        val = os.environ.get(match.group(1))
        return val if val is not None else match.group(0)

    raw_text = re.sub(r"\$\{([^}]+)\}", _replace_env, raw_text)

    data: dict[str, Any] = yaml.safe_load(raw_text) or {}
    bridge_data = data.get("bridge", {})

    # Also pull API key from top-level if not in bridge section.
    if not bridge_data.get("hermes_api_key"):
        bridge_data["hermes_api_key"] = data.get("api_key")

    return BridgeConfig(**bridge_data)
