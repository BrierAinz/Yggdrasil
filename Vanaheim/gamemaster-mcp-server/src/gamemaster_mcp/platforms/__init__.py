"""Platform handlers for GameMaster — base class and specific implementations."""

from .base import BasePlatform
from .caveduck import CaveduckPlatform
from .tipsy import TipsyPlatform

__all__ = ["BasePlatform", "CaveduckPlatform", "TipsyPlatform"]
