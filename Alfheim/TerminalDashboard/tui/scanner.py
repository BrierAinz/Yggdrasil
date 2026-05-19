"""Realm status scanner – scans Yggdrasil realm directories for project info."""

from __future__ import annotations

import subprocess
from dataclasses import dataclass, field
from enum import StrEnum
from pathlib import Path
from typing import Any


class GitStatus(StrEnum):
    """Git status for a realm or project."""

    CLEAN = "clean"
    DIRTY = "dirty"
    NO_REPO = "no_repo"


class ProjTestStatus(StrEnum):
    """Test status for a realm or project."""

    PASS = "pass"
    FAIL = "fail"
    UNKNOWN = "unknown"


class HealthStatus(StrEnum):
    """Overall health of a realm."""

    HEALTHY = "healthy"
    DEGRADED = "degraded"
    DOWN = "down"


# The 9 realms of Yggdrasil and their descriptions
REALMS: dict[str, str] = {
    "Asgard": "Core tech (Lilith)",
    "Vanaheim": "AI agents",
    "Alfheim": "UI prototypes",
    "Svartalfheim": "Docs/knowledge",
    "Muspelheim": "Active dev/WIP",
    "Niflheim": "Resources/assets",
    "Helheim": "Graveyard/archive",
    "Jotunheim": "Massive projects",
    "Midgard": "Personal apps",
}


@dataclass
class ProjectInfo:
    """Information about a single project inside a realm."""

    name: str
    path: Path
    branch: str = ""
    uncommitted_changes: bool = False
    test_pass_rate: float = 0.0
    last_commit: str = ""

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for serialization.

        Returns:
            Dictionary with all ProjectInfo fields.

        """
        return {
            "name": self.name,
            "path": str(self.path),
            "branch": self.branch,
            "uncommitted_changes": self.uncommitted_changes,
            "test_pass_rate": self.test_pass_rate,
            "last_commit": self.last_commit,
        }


@dataclass
class RealmStatus:
    """Aggregated status for a Yggdrasil realm."""

    name: str
    path: Path
    project_count: int = 0
    git_status: GitStatus = GitStatus.NO_REPO
    test_status: ProjTestStatus = ProjTestStatus.UNKNOWN
    last_commit_date: str = ""
    health: HealthStatus = HealthStatus.DOWN
    projects: list[ProjectInfo] = field(default_factory=list)

    @property
    def description(self) -> str:
        """Return the realm description."""
        return REALMS.get(self.name, "Unknown realm")

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for serialization.

        Returns:
            Dictionary with realm name, path, description, and nested project dicts.

        """
        return {
            "name": self.name,
            "path": str(self.path),
            "description": self.description,
            "project_count": self.project_count,
            "git_status": self.git_status.value,
            "test_status": self.test_status.value,
            "last_commit_date": self.last_commit_date,
            "health": self.health.value,
            "projects": [p.to_dict() for p in self.projects],
        }


class RealmScanner:
    """Scans Yggdrasil realm directories for project status information."""

    def __init__(self, base_path: str | Path | None = None) -> None:
        """Initialize scanner with base path to Yggdrasil root.

        Args:
            base_path: Path to the Yggdrasil root directory. Defaults to
                the YGGDRASIL_ROOT env var or auto-detection by walking up from
                this file's location to find a directory named 'Yggdrasil'.

        """
        if base_path is None:
            import os

            env_val = os.environ.get("YGGDRASIL_ROOT")
            base_path = env_val or self._find_yggdrasil_root(Path(__file__).resolve().parent)
        self.base_path = Path(base_path)

    @staticmethod
    def _find_yggdrasil_root(start: Path) -> Path:
        """Walk up from *start* to find a directory named 'Yggdrasil'.

        Returns:
            Path to the Yggdrasil root directory.

        """
        current = start
        for _ in range(20):  # safety limit
            if current.name == "Yggdrasil":
                return current
            parent = current.parent
            if parent == current:
                break
            current = parent
        # Fallback: return wherever we ended up
        return current

    def scan_all(self) -> dict[str, RealmStatus]:
        """Scan all 9 realms and return their statuses.

        Returns:
            Dictionary mapping realm names to RealmStatus objects.

        """
        results: dict[str, RealmStatus] = {}
        for realm_name in REALMS:
            results[realm_name] = self.scan_realm(realm_name)
        return results

    def scan_realm(self, realm_name: str) -> RealmStatus:
        """Scan a single realm directory for status information.

        Args:
            realm_name: Name of the realm (e.g. 'Asgard', 'Vanaheim').

        Returns:
            RealmStatus with aggregated information about the realm.

        """
        realm_path = self.base_path / realm_name

        if not realm_path.exists():
            return RealmStatus(
                name=realm_name,
                path=realm_path,
                health=HealthStatus.DOWN,
            )

        # Collect subdirectories that look like projects
        projects = self._scan_projects(realm_path)
        project_count = len(projects)

        # Aggregate git status
        git_status = self._aggregate_git_status(projects, realm_path)

        # Aggregate test status
        test_status = self._aggregate_test_status(projects)

        # Last commit date
        last_commit_date = self._get_last_commit_date(realm_path)

        # Determine overall health
        health = self._determine_health(git_status, test_status, projects)

        return RealmStatus(
            name=realm_name,
            path=realm_path,
            project_count=project_count,
            git_status=git_status,
            test_status=test_status,
            last_commit_date=last_commit_date,
            health=health,
            projects=projects,
        )

    def _scan_projects(self, realm_path: Path) -> list[ProjectInfo]:
        """Scan a realm directory for project subdirectories.

        Returns:
            List of ProjectInfo for each non-hidden subdirectory.

        """
        projects: list[ProjectInfo] = []

        if not realm_path.is_dir():
            return projects

        for child in sorted(realm_path.iterdir()):
            if not child.is_dir():
                continue
            # Skip hidden dirs and common non-project dirs
            if child.name.startswith(".") or child.name.startswith("__"):
                continue

            project = self._get_project_info(child)
            projects.append(project)

        return projects

    def _get_project_info(self, project_path: Path) -> ProjectInfo:
        """Get information about a single project directory.

        Returns:
            ProjectInfo with name, branch, uncommitted status, and last commit date.

        """
        name = project_path.name
        branch = self._get_git_branch(project_path)
        uncommitted = self._has_uncommitted_changes(project_path)
        last_commit = self._get_last_commit_date(project_path)

        return ProjectInfo(
            name=name,
            path=project_path,
            branch=branch,
            uncommitted_changes=uncommitted,
            test_pass_rate=0.0,  # Would need to run tests to determine
            last_commit=last_commit,
        )

    def _get_git_branch(self, path: Path) -> str:
        """Get the current git branch for a project.

        Returns:
            Branch name string, or empty string if git is unavailable.

        """
        try:
            result = subprocess.run(
                ["git", "rev-parse", "--abbrev-ref", "HEAD"],
                cwd=str(path),
                capture_output=True,
                text=True,
                timeout=5,
                check=False,
            )
            if result.returncode == 0:
                return result.stdout.strip()
        except (subprocess.TimeoutExpired, FileNotFoundError, OSError):
            pass
        return ""

    def _has_uncommitted_changes(self, path: Path) -> bool:
        """Check if a project has uncommitted git changes.

        Returns:
            True if there are uncommitted changes, False otherwise.

        """
        try:
            result = subprocess.run(
                ["git", "status", "--porcelain"],
                cwd=str(path),
                capture_output=True,
                text=True,
                timeout=5,
                check=False,
            )
            if result.returncode == 0:
                return bool(result.stdout.strip())
        except (subprocess.TimeoutExpired, FileNotFoundError, OSError):
            pass
        return False

    def _get_last_commit_date(self, path: Path) -> str:
        """Get the date of the last commit in a directory.

        Returns:
            Short date string (YYYY-MM-DD), or empty string if unavailable.

        """
        try:
            result = subprocess.run(
                ["git", "log", "-1", "--format=%cd", "--date=short"],
                cwd=str(path),
                capture_output=True,
                text=True,
                timeout=5,
                check=False,
            )
            if result.returncode == 0:
                return result.stdout.strip()
        except (subprocess.TimeoutExpired, FileNotFoundError, OSError):
            pass
        return ""

    def _aggregate_git_status(self, projects: list[ProjectInfo], realm_path: Path) -> GitStatus:
        """Aggregate git status from all projects in a realm.

        Returns:
            GitStatus.CLEAN if all projects are clean, DIRTY if any has
            uncommitted changes, NO_REPO if no projects and no .git directory.

        """
        if not projects:
            # Check if the realm itself is a git repo
            git_dir = realm_path / ".git"
            if git_dir.exists():
                return GitStatus.CLEAN
            return GitStatus.NO_REPO

        dirty_count = sum(1 for p in projects if p.uncommitted_changes)
        if dirty_count == 0:
            return GitStatus.CLEAN
        return GitStatus.DIRTY

    def _aggregate_test_status(self, projects: list[ProjectInfo]) -> ProjTestStatus:
        """Aggregate test status from all projects in a realm.

        Since running tests is expensive, we default to UNKNOWN unless
        we find pytest results caches.

        Returns:
            ProjTestStatus — currently always UNKNOWN (placeholder).

        """
        return ProjTestStatus.UNKNOWN

    def _determine_health(
        self,
        git_status: GitStatus,
        test_status: ProjTestStatus,
        projects: list[ProjectInfo],
    ) -> HealthStatus:
        """Determine overall health based on git and test status.

        Returns:
            HealthStatus.HEALTHY if clean, DEGRADED if dirty or failing,
            DOWN if no projects and no git repo.

        """
        if not projects and git_status == GitStatus.NO_REPO:
            return HealthStatus.DOWN

        if git_status == GitStatus.DIRTY:
            return HealthStatus.DEGRADED

        if test_status == ProjTestStatus.FAIL:
            return HealthStatus.DEGRADED

        return HealthStatus.HEALTHY
