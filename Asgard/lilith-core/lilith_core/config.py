import json
from pathlib import Path
from typing import Any


class Config:
    """Configuracion centralizada de Lilith."""

    def __init__(self, root_path: Path | None = None) -> None:
        self.root = root_path or Path.home() / ".lilith"
        self.root.mkdir(parents=True, exist_ok=True)
        self.config_file = self.root / "config.json"
        self._data: dict[str, Any] = self._load()

    def _load(self) -> dict[str, Any]:
        if self.config_file.exists():
            return json.loads(self.config_file.read_text(encoding="utf-8"))
        return self._defaults()

    def _defaults(self) -> dict[str, Any]:
        return {
            "model": "auto",
            "lm_studio_url": "http://localhost:1234/v1",
            "max_context": 8192,
            "temperature": 0.7,
        }

    def get(self, key: str, default: Any = None) -> Any:
        return self._data.get(key, default)

    def set(self, key: str, value: Any) -> None:
        self._data[key] = value
        self._save()

    def _save(self) -> None:
        self.config_file.write_text(
            json.dumps(self._data, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )
