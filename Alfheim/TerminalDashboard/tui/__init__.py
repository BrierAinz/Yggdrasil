"""Yggdrasil Terminal Dashboard – TUI for monitoring all realms."""

__version__ = "1.0.0"

from tui.app import YggdrasilDashboard
from tui.scanner import HealthStatus, ProjectInfo, ProjTestStatus, RealmStatus
from tui.updater import DashboardUpdater, UpdateResult


__all__ = [
    "DashboardUpdater",
    "HealthStatus",
    "ProjTestStatus",
    "ProjectInfo",
    "RealmStatus",
    "UpdateResult",
    "YggdrasilDashboard",
    "__version__",
]
