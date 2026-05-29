"""Yggdrasil Terminal Dashboard – TUI for monitoring all realms."""

__version__ = "1.0.0"

from tui.app import YggdrasilDashboard
from tui.git_utils import GitActivity, GitLogEntry
from tui.health import GPUInfo, HealthMonitor, SystemHealth
from tui.scanner import (
    GitStatus,
    HealthStatus,
    ProjectInfo,
    ProjTestStatus,
    RealmScanner,
    RealmStatus,
)
from tui.updater import DashboardUpdater, UpdateResult


__all__ = [
    "DashboardUpdater",
    "GPUInfo",
    "GitActivity",
    "GitLogEntry",
    "GitStatus",
    "HealthMonitor",
    "HealthStatus",
    "ProjTestStatus",
    "ProjectInfo",
    "RealmScanner",
    "RealmStatus",
    "SystemHealth",
    "UpdateResult",
    "YggdrasilDashboard",
    "__version__",
]
