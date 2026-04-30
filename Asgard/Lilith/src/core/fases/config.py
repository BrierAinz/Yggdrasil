"""
Config stub for Fases A-E modules
Provides compatibility with existing code
"""

import os
from pathlib import Path


class Config:
    """Simple config stub"""

    def __init__(self):
        self.project_path = Path(os.getcwd())
        self.session_dir = Path.home() / ".lilith" / "sessions"
        self.patterns_dir = Path.home() / ".lilith" / "patterns"

    def get(self, key, default=None):
        """Get config value"""
        return getattr(self, key, default)


# Global config instance
config = Config()
