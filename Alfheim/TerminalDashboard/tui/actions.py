"""Quick action handlers for keyboard shortcuts in the terminal dashboard."""

from __future__ import annotations

import logging
import subprocess
import webbrowser
from dataclasses import dataclass
from pathlib import Path
from typing import Any


logger = logging.getLogger(__name__)


@dataclass
class ActionResult:
    """Result from executing a quick action."""

    success: bool
    action: str
    message: str
    details: dict[str, Any] | None = None


class QuickActions:
    """Handles quick action keyboard shortcuts for the dashboard.

    Shortcuts:
        t - Run tests
        g - Open git status/summary
        h - Show health panel
        o - Open in VS Code
        d - Open docs
    """

    # Mapping from key to action name
    KEY_MAP: dict[str, str] = {
        "t": "tests",
        "g": "git",
        "h": "health",
        "o": "vscode",
        "d": "docs",
    }

    def __init__(
        self,
        project_path: str | Path | None = None,
        docs_url: str = "https://github.com/user/yggdrasil",
    ) -> None:
        """Initialize quick actions.

        Args:
            project_path: Path to the current project directory.
            docs_url: URL for the documentation page.
        """
        if project_path is None:
            project_path = Path.cwd()
        self.project_path = Path(project_path)
        self.docs_url = docs_url

    def execute(self, key: str) -> ActionResult:
        """Execute the action associated with a key press.

        Args:
            key: The keyboard shortcut key pressed.

        Returns:
            ActionResult with success status and message.
        """
        action_name = self.KEY_MAP.get(key)
        if action_name is None:
            return ActionResult(
                success=False,
                action=key,
                message=f"Unknown shortcut: '{key}'",
            )

        handler = getattr(self, f"_action_{action_name}", None)
        if handler is None:
            return ActionResult(
                success=False,
                action=action_name,
                message=f"No handler for action: {action_name}",
            )

        try:
            return handler()
        except Exception as exc:
            logger.exception("Action %s failed: %s", action_name, exc)
            return ActionResult(
                success=False,
                action=action_name,
                message=f"Action '{action_name}' failed: {exc}",
            )

    def _action_tests(self) -> ActionResult:
        """Run project tests."""
        project = self.project_path
        # Try common test commands
        test_commands = [
            ["python", "-m", "pytest", "tests/", "-v"],
            ["python", "-m", "pytest", "-v"],
            ["make", "test"],
        ]

        for cmd in test_commands:
            # Check if the test directory/command makes sense
            if (
                "pytest" in " ".join(cmd)
                and not (project / "tests").exists()
                and not (project / "test").exists()
            ):
                continue

            try:
                result = subprocess.run(
                    cmd,
                    cwd=str(project),
                    capture_output=True,
                    text=True,
                    timeout=120,
                )
                output = result.stdout[-500:] if len(result.stdout) > 500 else result.stdout
                success = result.returncode == 0
                return ActionResult(
                    success=success,
                    action="tests",
                    message=f"Tests {'passed' if success else 'failed'}",
                    details={
                        "returncode": result.returncode,
                        "output": output,
                        "command": " ".join(cmd),
                    },
                )
            except (subprocess.TimeoutExpired, FileNotFoundError):
                continue

        return ActionResult(
            success=False,
            action="tests",
            message="No test runner found",
        )

    def _action_git(self) -> ActionResult:
        """Show git status summary."""
        project = self.project_path
        try:
            # Get branch
            branch_result = subprocess.run(
                ["git", "rev-parse", "--abbrev-ref", "HEAD"],
                cwd=str(project),
                capture_output=True,
                text=True,
                timeout=10,
            )
            branch = branch_result.stdout.strip() if branch_result.returncode == 0 else "unknown"

            # Get short status
            status_result = subprocess.run(
                ["git", "status", "--short", "--branch"],
                cwd=str(project),
                capture_output=True,
                text=True,
                timeout=10,
            )
            status_output = status_result.stdout.strip() if status_result.returncode == 0 else "N/A"

            # Get recent commits
            log_result = subprocess.run(
                ["git", "log", "--oneline", "-5"],
                cwd=str(project),
                capture_output=True,
                text=True,
                timeout=10,
            )
            recent_commits = log_result.stdout.strip() if log_result.returncode == 0 else ""

            # Count ahead/behind
            ahead_behind = ""
            try:
                ab_result = subprocess.run(
                    [
                        "git",
                        "rev-list",
                        "--left-right",
                        "--count",
                        "@{upstream}...HEAD",
                    ],
                    cwd=str(project),
                    capture_output=True,
                    text=True,
                    timeout=10,
                )
                if ab_result.returncode == 0:
                    parts = ab_result.stdout.strip().split()
                    if len(parts) == 2:
                        ahead_behind = f"{parts[0]} behind, {parts[1]} ahead"
            except (subprocess.TimeoutExpired, FileNotFoundError, OSError):
                pass

            return ActionResult(
                success=True,
                action="git",
                message=f"Branch: {branch}",
                details={
                    "branch": branch,
                    "status": status_output,
                    "recent_commits": recent_commits,
                    "ahead_behind": ahead_behind,
                },
            )
        except (subprocess.TimeoutExpired, FileNotFoundError, OSError) as exc:
            return ActionResult(
                success=False,
                action="git",
                message=f"Git command failed: {exc}",
            )

    def _action_health(self) -> ActionResult:
        """Show health panel – delegates to HealthMonitor."""
        from tui.health import HealthMonitor

        monitor = HealthMonitor()
        try:
            health = monitor.get_health()
            return ActionResult(
                success=True,
                action="health",
                message=f"CPU: {health.cpu_pct}% | RAM: {health.ram_pct}% | "
                f"Disk: {health.disk_pct}% | Python procs: {health.python_process_count}",
                details=health.to_dict(),
            )
        except Exception as exc:
            return ActionResult(
                success=False,
                action="health",
                message=f"Health check failed: {exc}",
            )

    def _action_vscode(self) -> ActionResult:
        """Open project in VS Code."""
        project = self.project_path
        # Look for VS Code variants
        editors = ["code", "code-insiders", "codium"]

        for editor in editors:
            try:
                subprocess.run(
                    [editor, str(project)],
                    cwd=str(project),
                    capture_output=True,
                    timeout=10,
                    # Detach – we don't want to block
                    start_new_session=True,
                )
                return ActionResult(
                    success=True,
                    action="vscode",
                    message=f"Opened {project} in {editor}",
                    details={"editor": editor, "path": str(project)},
                )
            except FileNotFoundError:
                continue
            except (subprocess.TimeoutExpired, OSError) as exc:
                logger.debug("Editor %s failed: %s", editor, exc)
                continue

        return ActionResult(
            success=False,
            action="vscode",
            message="No VS Code editor found (tried: " + ", ".join(editors) + ")",
        )

    def _action_docs(self) -> ActionResult:
        """Open documentation in the browser."""
        try:
            webbrowser.open(self.docs_url)
            return ActionResult(
                success=True,
                action="docs",
                message=f"Opened docs: {self.docs_url}",
                details={"url": self.docs_url},
            )
        except Exception as exc:
            return ActionResult(
                success=False,
                action="docs",
                message=f"Failed to open browser: {exc}",
            )

    @classmethod
    def available_actions(cls) -> dict[str, str]:
        """Return a mapping of available shortcut keys and their descriptions."""
        return {
            "t": "Run tests",
            "g": "Git status",
            "h": "Health panel",
            "o": "Open in VS Code",
            "d": "Open docs",
        }
