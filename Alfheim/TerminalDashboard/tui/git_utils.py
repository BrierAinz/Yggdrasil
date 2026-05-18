"""Git activity utilities – run git log & status for each realm directory."""

from __future__ import annotations

import subprocess
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any


if TYPE_CHECKING:
    from pathlib import Path


@dataclass
class GitLogEntry:
    """A single git log entry."""

    hash: str = ""
    message: str = ""

    def to_dict(self) -> dict[str, str]:
        """Serializar entrada de log como diccionario.

        Returns:
            Dictionary with 'hash' and 'message' keys.

        """
        return {"hash": self.hash, "message": self.message}


@dataclass
class GitActivity:
    """Git activity information for a realm or project directory."""

    path: Path
    is_git_repo: bool = False
    branch: str = ""
    recent_commits: list[GitLogEntry] = field(default_factory=list)
    status_lines: list[str] = field(default_factory=list)

    @property
    def dirty(self) -> bool:
        """Whether there are uncommitted changes."""
        return len(self.status_lines) > 0

    @property
    def commit_count(self) -> int:
        """Number of recent commits retrieved."""
        return len(self.recent_commits)

    def to_dict(self) -> dict[str, Any]:
        """Serializar actividad git como diccionario.

        Returns:
            Dictionary with path, git status, branch, commits, and dirty flag.

        """
        return {
            "path": str(self.path),
            "is_git_repo": self.is_git_repo,
            "branch": self.branch,
            "recent_commits": [c.to_dict() for c in self.recent_commits],
            "status_lines": self.status_lines,
            "dirty": self.dirty,
        }


def get_git_activity(directory: Path, max_commits: int = 10) -> GitActivity:
    """Get git activity for a directory.

    Runs ``git log --oneline -N`` and ``git status --short`` in the
    given directory and returns a :class:`GitActivity` object.

    Args:
        directory: Path to the directory to inspect.
        max_commits: Maximum number of recent commits to return (default 10).

    Returns:
        GitActivity with branch, recent commits, and status lines.
        If the directory is not a git repo, returns GitActivity with
        ``is_git_repo=False`` and empty collections.

    """
    activity = GitActivity(path=directory)

    # Check if it's a git repo
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--is-inside-work-tree"],
            cwd=str(directory),
            capture_output=True,
            text=True,
            timeout=5,
        )
        if result.returncode != 0:
            return activity
    except (subprocess.TimeoutExpired, FileNotFoundError, OSError):
        return activity

    activity.is_git_repo = True

    # Get branch
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--abbrev-ref", "HEAD"],
            cwd=str(directory),
            capture_output=True,
            text=True,
            timeout=5,
        )
        if result.returncode == 0:
            activity.branch = result.stdout.strip()
    except (subprocess.TimeoutExpired, FileNotFoundError, OSError):
        pass

    # Get recent commits
    try:
        result = subprocess.run(
            ["git", "log", "--oneline", f"-{max_commits}"],
            cwd=str(directory),
            capture_output=True,
            text=True,
            timeout=5,
        )
        if result.returncode == 0:
            for line in result.stdout.strip().splitlines():
                if line:
                    parts = line.split(" ", 1)
                    entry = GitLogEntry(
                        hash=parts[0] if len(parts) >= 1 else "",
                        message=parts[1] if len(parts) >= 2 else "",
                    )
                    activity.recent_commits.append(entry)
    except (subprocess.TimeoutExpired, FileNotFoundError, OSError):
        pass

    # Get status
    try:
        result = subprocess.run(
            ["git", "status", "--short"],
            cwd=str(directory),
            capture_output=True,
            text=True,
            timeout=5,
        )
        if result.returncode == 0:
            activity.status_lines = [line for line in result.stdout.strip().splitlines() if line]
    except (subprocess.TimeoutExpired, FileNotFoundError, OSError):
        pass

    return activity


def get_realm_git_activities(realm_path: Path, max_commits: int = 10) -> dict[str, GitActivity]:
    """Get git activity for a realm and its project subdirectories.

    Args:
        realm_path: Path to the realm directory.
        max_commits: Maximum number of recent commits per directory.

    Returns:
        Dictionary mapping project names (or '__realm__' for the realm root)
        to their GitActivity objects.

    """
    activities: dict[str, GitActivity] = {}

    # Check the realm root itself
    realm_activity = get_git_activity(realm_path, max_commits)
    if realm_activity.is_git_repo:
        activities["__realm__"] = realm_activity

    # Check each project subdirectory
    if realm_path.is_dir():
        for child in sorted(realm_path.iterdir()):
            if not child.is_dir():
                continue
            if child.name.startswith(".") or child.name.startswith("__"):
                continue
            project_activity = get_git_activity(child, max_commits)
            if project_activity.is_git_repo:
                activities[child.name] = project_activity

    return activities
