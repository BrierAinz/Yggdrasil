import json
import os
import time
from datetime import datetime, timezone
from typing import Any, Dict


class StatsTracker:
    def __init__(self, stats_path: str = "Memory/stats.json"):
        # Resolve path relative to project root if needed, or use absolute.
        # Assuming run from project root or handling logic elsewhere.
        # Better to make it robust relative to this file?
        # Let's use the one passed or default relative to cwd for now, consistent with ConfigManager.
        self.stats_path = stats_path
        self.stats = self._load_stats()

        # Runtime session tracking
        self.session_start = time.perf_counter()

    def _load_stats(self) -> Dict[str, Any]:
        if not os.path.exists(self.stats_path):
            return self._get_default_stats()

        try:
            with open(self.stats_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except (IOError, json.JSONDecodeError):
            return self._get_default_stats()

    def _get_default_stats(self) -> Dict[str, Any]:
        now_iso = datetime.now(timezone.utc).isoformat()
        return {
            "total_messages_sent": 0,
            "total_tokens_received": 0,  # Placeholder if we can't get exact tokens yet
            "llm_usage_time_seconds": 0.0,
            "commands_executed": {"git": 0, "system": 0},
            "session_start_time_iso": now_iso,  # When the stats file was created/reset
            "last_activity_iso": now_iso,
        }

    def _update_activity(self):
        self.stats["last_activity_iso"] = datetime.now(timezone.utc).isoformat()

    def record_message(self):
        self.stats["total_messages_sent"] += 1
        self._update_activity()
        self.save()

    def record_command(self, command_type: str):
        if "commands_executed" not in self.stats:
            self.stats["commands_executed"] = {"git": 0, "system": 0}

        if command_type not in self.stats["commands_executed"]:
            self.stats["commands_executed"][command_type] = 0

        self.stats["commands_executed"][command_type] += 1
        self._update_activity()
        self.save()

    def add_tokens(self, token_count: int):
        self.stats["total_tokens_received"] += token_count
        # Don't save on every token chunk, maybe caller handles save or we save periodically?
        # For safety/simplicity, save now. Optimization later.
        self.save()

    def add_llm_time(self, seconds: float):
        self.stats["llm_usage_time_seconds"] += seconds
        self.save()

    def save(self):
        try:
            os.makedirs(os.path.dirname(self.stats_path), exist_ok=True)
            with open(self.stats_path, "w", encoding="utf-8") as f:
                json.dump(self.stats, f, indent=2)
        except IOError as e:
            print(f"Error saving stats: {e}")

    def get_all(self) -> Dict[str, Any]:
        return self.stats
