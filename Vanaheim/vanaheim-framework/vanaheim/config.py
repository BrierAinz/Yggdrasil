import os
from pathlib import Path
from typing import Dict, Any
import json


class BotConfig:
    def __init__(self, bot_name: str, config_dir: Path = None):
        self.bot_name = bot_name
        self.config_dir = config_dir or Path.home() / ".vanaheim" / bot_name
        self.config_dir.mkdir(parents=True, exist_ok=True)
        self.config_file = self.config_dir / "config.json"
        self._data = self._load()

    def _load(self) -> Dict[str, Any]:
        if self.config_file.exists():
            return json.loads(self.config_file.read_text(encoding="utf-8"))
        return {}

    def get(self, key: str, default=None):
        return self._data.get(key, os.getenv(key.upper(), default))

    def set(self, key: str, value):
        self._data[key] = value
        self._save()

    def _save(self):
        self.config_file.write_text(
            json.dumps(self._data, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )
