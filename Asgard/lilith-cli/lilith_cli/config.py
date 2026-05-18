"""YAML configuration loader for Yggdrasil CLI v6.0.

Reads ``~/.yggdrasil/config.yaml``, supports ``${ENV_VAR}`` interpolation
for secrets, and auto-creates the config directory and default file on
first run.
"""

from __future__ import annotations

import os
import re
from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel, Field


# ── Pydantic models ────────────────────────────────────────────────


class ToolsConfig(BaseModel):
    """Feature flags for each tool category."""

    filesystem: bool = True
    coding: bool = True
    web_search: bool = True
    browser: bool = True
    system: bool = True


class MemoryConfig(BaseModel):
    """Memory store configuration."""

    enabled: bool = True
    db_path: str = "~/.yggdrasil/memory.db"


class HistoryConfig(BaseModel):
    """Conversation history configuration."""

    max_turns: int = 50
    save: bool = True


class ProviderProfile(BaseModel):
    """Optional per-provider profile overrides."""

    api_key: str | None = None
    base_url: str | None = None
    model: str | None = None
    temperature: float | None = None
    max_tokens: int | None = None


class YggdrasilConfig(BaseModel):
    """Root configuration model for the Yggdrasil CLI agent."""

    provider: str = "openai"
    model: str = "gpt-4o-mini"
    api_key: str | None = None
    base_url: str | None = None
    system_prompt: str = (
        "You are Lilith, an AI agent of the Yggdrasil ecosystem. "
        "You are wise, precise, and helpful. You assist with coding, "
        "analysis, research, and creative tasks. You think step-by-step "
        "and use tools when appropriate. Where Ancient Meets Digital."
    )
    temperature: float = 0.7
    max_tokens: int = 4096
    tools: ToolsConfig = Field(default_factory=ToolsConfig)
    memory: MemoryConfig = Field(default_factory=MemoryConfig)
    history: HistoryConfig = Field(default_factory=HistoryConfig)
    providers: dict[str, ProviderProfile] = Field(default_factory=dict)

    model_config = {"extra": "ignore"}  # Allow extra keys for forward-compatibility


# ── Env-var interpolation ──────────────────────────────────────────

_ENV_PATTERN = re.compile(r"\$\{([^}]+)\}")


def _interpolate_env(value: Any) -> Any:
    """Recursively replace ``${VAR}`` with the value of the environment
    variable *VAR*.  If the variable is not set the placeholder is left
    unchanged.
    """
    if isinstance(value, str):

        def _replacer(m: re.Match) -> str:
            env_val = os.environ.get(m.group(1))
            return env_val if env_val is not None else m.group(0)

        return _ENV_PATTERN.sub(_replacer, value)

    if isinstance(value, dict):
        return {k: _interpolate_env(v) for k, v in value.items()}

    if isinstance(value, list):
        return [_interpolate_env(v) for v in value]

    return value


# ── Default config YAML ─────────────────────────────────────────────

_DEFAULT_CONFIG_YAML = """\
# Yggdrasil CLI v6.0 configuration
# See https://github.com/BrierAinz/Yggdrasil for docs

provider: openai
model: gpt-4o-mini
api_key: ${OPENAI_API_KEY}
base_url: null

system_prompt: >
  You are Lilith, an AI agent of the Yggdrasil ecosystem.
  You are wise, precise, and helpful. You assist with coding,
  analysis, research, and creative tasks. You think step-by-step
  and use tools when appropriate. Where Ancient Meets Digital.

temperature: 0.7
max_tokens: 4096

tools:
  filesystem: true
  coding: true
  web_search: true
  browser: true
  system: true

memory:
  enabled: true
  db_path: ~/.yggdrasil/memory.db

history:
  max_turns: 50
  save: true

# Optional per-provider profiles
# providers:
#   anthropic:
#     api_key: ${ANTHROPIC_API_KEY}
#     model: claude-sonnet-4-20250514
#   ollama:
#     base_url: http://localhost:11434
#     model: llama3
#   local:
#     base_url: http://localhost:1234/v1
#     model: local-model
"""


# ── Config directory / file helpers ─────────────────────────────────

CONFIG_DIR = Path.home() / ".yggdrasil"
CONFIG_FILE = CONFIG_DIR / "config.yaml"


def _ensure_config_dir() -> None:
    """Create the config directory and write a default config file if
    none exists.
    """
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    if not CONFIG_FILE.exists():
        CONFIG_FILE.write_text(_DEFAULT_CONFIG_YAML, encoding="utf-8")


def load_config(config_path: Path | str | None = None) -> YggdrasilConfig:
    """Load and parse the YAML config, returning a validated
    :class:`YggdrasilConfig`.

    Parameters
    ----------
    config_path:
        Explicit path to a YAML file.  Falls back to
        ``~/.yggdrasil/config.yaml``.
    """
    path = Path(config_path) if config_path else CONFIG_FILE

    if not path.exists():
        # Bootstrap the default config so the user can edit it.
        _ensure_config_dir()
        if not path.exists():
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(_DEFAULT_CONFIG_YAML, encoding="utf-8")

    raw_text = path.read_text(encoding="utf-8")
    raw_yaml: dict[str, Any] = yaml.safe_load(raw_text) or {}

    # Interpolate environment variables.
    raw_yaml = _interpolate_env(raw_yaml)

    # Expand ~ in db_path.
    if "memory" in raw_yaml and isinstance(raw_yaml["memory"], dict):
        db_path = raw_yaml["memory"].get("db_path")
        if db_path and isinstance(db_path, str):
            raw_yaml["memory"]["db_path"] = str(Path(db_path).expanduser())

    return YggdrasilConfig(**raw_yaml)


def save_config(config: YggdrasilConfig, config_path: Path | str | None = None) -> None:
    """Serialize a :class:`YggdrasilConfig` back to YAML on disk.

    Environment-variable placeholders are **not** round-tripped;
    actual values are written.  This is intentional: the file is a
    snapshot, not a template.
    """
    path = Path(config_path) if config_path else CONFIG_FILE
    path.parent.mkdir(parents=True, exist_ok=True)

    data = config.model_dump()
    # Convert paths back to strings for YAML serialisation.
    db_path = data.get("memory", {}).get("db_path")
    if db_path:
        data["memory"]["db_path"] = str(db_path)

    path.write_text(yaml.dump(data, default_flow_style=False, allow_unicode=True), encoding="utf-8")
