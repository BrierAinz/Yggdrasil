from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any, Dict, Tuple

from pydantic import ValidationError

from .config_schema import AppConfig

# Default path relative to this file: sebas_core/core/config_manager.py -> ../../config/settings.json
CONFIG_PATH = Path(__file__).parent.parent.parent / "Config" / "settings.json"


class ConfigError(Exception):
    def __init__(self, code: str, message: str, details: Any = None):
        super().__init__(message)
        self.code = code
        self.message = message
        self.details = details

    def to_dict(self) -> dict:
        return {"code": self.code, "message": self.message, "details": self.details}


def deep_merge(a: dict, b: dict) -> dict:
    out = dict(a)
    for k, v in b.items():
        if isinstance(v, dict) and isinstance(out.get(k), dict):
            out[k] = deep_merge(out[k], v)
        else:
            out[k] = v
    return out


class ConfigManager:
    def __init__(self, path: Path = CONFIG_PATH):
        self.path = path
        self._cfg = self.load()

    def get(self) -> AppConfig:
        return self._cfg

    def load(self) -> AppConfig:
        if not self.path.exists():
            cfg = AppConfig()
            self._write_atomic(cfg)
            return cfg

        try:
            raw = json.loads(self.path.read_text(encoding="utf-8"))
        except Exception as e:
            # Fallback or error? For now error to prevent overwriting with default on read fail
            print(f"Error reading config: {e}")
            raise ConfigError(
                "CONFIG_READ_FAILED", "Failed to read settings.json", str(e)
            )

        # Legacy detection (missing version)
        if isinstance(raw, dict) and "config_version" not in raw:
            print("Legacy config detected. Migrating...")
            migrated, changed = self._migrate_legacy_to_v1(raw)
            try:
                cfg = AppConfig.model_validate(migrated)
            except ValidationError as e:
                raise ConfigError(
                    "CONFIG_MIGRATION_INVALID",
                    "Legacy migration produced invalid config",
                    e.errors(),
                )
            if changed:
                self._write_atomic(cfg)
            return cfg

        try:
            return AppConfig.model_validate(raw)
        except ValidationError as e:
            raise ConfigError(
                "CONFIG_INVALID", "settings.json is invalid for AppConfig", e.errors()
            )

    def update(self, patch: dict) -> AppConfig:
        current = self._cfg.model_dump()
        merged = deep_merge(current, patch)
        try:
            candidate = AppConfig.model_validate(merged)
        except ValidationError as e:
            raise ConfigError(
                "CONFIG_PATCH_INVALID", "Update would make config invalid", e.errors()
            )
        self._write_atomic(candidate)
        self._cfg = candidate
        return candidate

    def _write_atomic(self, cfg: AppConfig) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        tmp = self.path.with_suffix(".tmp")
        tmp.write_text(json.dumps(cfg.model_dump(), indent=2), encoding="utf-8")
        try:
            tmp.replace(self.path)
        except Exception as e:
            print(f"Error writing atomic config: {e}")
            # Windows might fail convert if file strictly locked?
            # Retry or unlink? replace should be atomic-ish in Py3
            if self.path.exists():
                os.remove(self.path)
            tmp.rename(self.path)

    def _migrate_legacy_to_v1(
        self, legacy: Dict[str, Any]
    ) -> Tuple[Dict[str, Any], bool]:
        changed = False

        llm_legacy = legacy.get("llm") if isinstance(legacy.get("llm"), dict) else {}
        default_provider = llm_legacy.get("default_provider")
        models = (
            llm_legacy.get("models")
            if isinstance(llm_legacy.get("models"), dict)
            else {}
        )

        memory_window = legacy.get("memory_window")
        if isinstance(memory_window, int):
            changed = True

        # pick model: try provider-specific list/dict if present
        selected_model = None
        if isinstance(default_provider, str) and default_provider in models:
            val = models.get(default_provider)
            if isinstance(val, str):
                selected_model = val
            elif isinstance(val, list) and val:
                selected_model = str(val[0])
            elif isinstance(val, dict) and val:
                # If it was a dict of models?
                selected_model = sorted([str(k) for k in val.keys()])[0]

        migrated = {
            "config_version": 1,
            "llm": {
                "provider": default_provider or "ollama",
                "model": selected_model or "llama3",
                "providers": {},
            },
            "system": {
                "memory_window": memory_window
                if isinstance(memory_window, int)
                else 40,
                "max_tool_runtime_sec": 120,
            },
            "safety": {"approval_timeout_sec": 45, "block_on_pending_approval": True},
        }

        return migrated, True
