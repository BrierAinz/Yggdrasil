"""Tests for the git_utils module."""

from __future__ import annotations

import subprocess
from pathlib import Path
from unittest.mock import MagicMock, patch

from tui.git_utils import (
    GitActivity,
    GitLogEntry,
    get_git_activity,
    get_realm_git_activities,
)


class TestGitLogEntry:
    """Tests for the GitLogEntry dataclass."""

    def test_default_values(self) -> None:
        entry = GitLogEntry()
        assert entry.hash == ""
        assert entry.message == ""

    def test_custom_values(self) -> None:
        entry = GitLogEntry(hash="abc1234", message="Fix bug")
        assert entry.hash == "abc1234"
        assert entry.message == "Fix bug"

    def test_to_dict(self) -> None:
        entry = GitLogEntry(hash="abc1234", message="Fix bug")
        d = entry.to_dict()
        assert d == {"hash": "abc1234", "message": "Fix bug"}


class TestGitActivity:
    """Tests for the GitActivity dataclass."""

    def test_default_values(self) -> None:
        activity = GitActivity(path=Path("/tmp/test"))
        assert activity.is_git_repo is False
        assert activity.branch == ""
        assert activity.recent_commits == []
        assert activity.status_lines == []

    def test_dirty_property_false(self) -> None:
        activity = GitActivity(path=Path("/tmp/test"), status_lines=[])
        assert activity.dirty is False

    def test_dirty_property_true(self) -> None:
        activity = GitActivity(path=Path("/tmp/test"), status_lines=[" M file.py"])
        assert activity.dirty is True

    def test_commit_count(self) -> None:
        commits = [
            GitLogEntry(hash="a", message="m1"),
            GitLogEntry(hash="b", message="m2"),
        ]
        activity = GitActivity(path=Path("/tmp/test"), recent_commits=commits)
        assert activity.commit_count == 2

    def test_to_dict(self) -> None:
        activity = GitActivity(
            path=Path("/tmp/test"),
            is_git_repo=True,
            branch="main",
            recent_commits=[GitLogEntry(hash="abc", message="msg")],
            status_lines=[" M file.py"],
        )
        d = activity.to_dict()
        assert d["path"] == "/tmp/test"
        assert d["is_git_repo"] is True
        assert d["branch"] == "main"
        assert d["dirty"] is True
        assert len(d["recent_commits"]) == 1


class TestGetGitActivity:
    """Tests for the get_git_activity function."""

    def test_nonexistent_directory(self) -> None:
        """Non-existent directory returns non-repo GitActivity."""
        activity = get_git_activity(Path("/nonexistent/path"))
        assert activity.is_git_repo is False
        assert activity.recent_commits == []
        assert activity.status_lines == []

    def test_not_a_git_repo(self, tmp_path: Path) -> None:
        """Directory without .git returns non-repo GitActivity."""
        activity = get_git_activity(tmp_path)
        assert activity.is_git_repo is False

    @patch("tui.git_utils.subprocess.run")
    def test_git_repo_with_commits(self, mock_run: MagicMock, tmp_path: Path) -> None:
        """Mocked git repo with branch, commits, and status."""
        # rev-parse --is-inside-work-tree
        rev_parse_result = MagicMock()
        rev_parse_result.returncode = 0
        rev_parse_result.stdout = "true\n"

        # rev-parse --abbrev-ref HEAD
        branch_result = MagicMock()
        branch_result.returncode = 0
        branch_result.stdout = "main\n"

        # git log --oneline -10
        log_result = MagicMock()
        log_result.returncode = 0
        log_result.stdout = "abc1234 Fix bug\ndef5678 Add feature\n"

        # git status --short
        status_result = MagicMock()
        status_result.returncode = 0
        status_result.stdout = " M file.py\n"

        mock_run.side_effect = [
            rev_parse_result,
            branch_result,
            log_result,
            status_result,
        ]

        activity = get_git_activity(tmp_path, max_commits=10)
        assert activity.is_git_repo is True
        assert activity.branch == "main"
        assert len(activity.recent_commits) == 2
        assert activity.recent_commits[0].hash == "abc1234"
        assert activity.recent_commits[0].message == "Fix bug"
        assert activity.dirty is True
        assert len(activity.status_lines) == 1

    @patch("tui.git_utils.subprocess.run")
    def test_git_repo_clean(self, mock_run: MagicMock, tmp_path: Path) -> None:
        """Mocked clean git repo (no uncommitted changes)."""
        rev_parse_result = MagicMock()
        rev_parse_result.returncode = 0
        rev_parse_result.stdout = "true\n"

        branch_result = MagicMock()
        branch_result.returncode = 0
        branch_result.stdout = "main\n"

        log_result = MagicMock()
        log_result.returncode = 0
        log_result.stdout = "abc1234 Initial commit\n"

        status_result = MagicMock()
        status_result.returncode = 0
        status_result.stdout = ""

        mock_run.side_effect = [
            rev_parse_result,
            branch_result,
            log_result,
            status_result,
        ]

        activity = get_git_activity(tmp_path)
        assert activity.is_git_repo is True
        assert activity.dirty is False
        assert activity.status_lines == []

    @patch("tui.git_utils.subprocess.run")
    def test_git_repo_rev_parse_fails(self, mock_run: MagicMock, tmp_path: Path) -> None:
        """When rev-parse fails, return non-repo activity."""
        rev_parse_result = MagicMock()
        rev_parse_result.returncode = 128
        rev_parse_result.stdout = ""

        mock_run.return_value = rev_parse_result

        activity = get_git_activity(tmp_path)
        assert activity.is_git_repo is False

    @patch("tui.git_utils.subprocess.run")
    def test_git_repo_timeout(self, mock_run: MagicMock, tmp_path: Path) -> None:
        """When subprocess times out, return non-repo activity gracefully."""
        mock_run.side_effect = subprocess.TimeoutExpired(cmd="git", timeout=5)

        activity = get_git_activity(tmp_path)
        assert activity.is_git_repo is False

    @patch("tui.git_utils.subprocess.run")
    def test_git_not_found(self, mock_run: MagicMock, tmp_path: Path) -> None:
        """When git is not installed, return non-repo activity gracefully."""
        mock_run.side_effect = FileNotFoundError("git not found")

        activity = get_git_activity(tmp_path)
        assert activity.is_git_repo is False

    @patch("tui.git_utils.subprocess.run")
    def test_max_commits_parameter(self, mock_run: MagicMock, tmp_path: Path) -> None:
        """Verify max_commits is passed to git log command."""
        rev_parse_result = MagicMock()
        rev_parse_result.returncode = 0
        rev_parse_result.stdout = "true\n"

        branch_result = MagicMock()
        branch_result.returncode = 0
        branch_result.stdout = "main\n"

        log_result = MagicMock()
        log_result.returncode = 0
        log_result.stdout = "a1 b1\n"

        status_result = MagicMock()
        status_result.returncode = 0
        status_result.stdout = ""

        mock_run.side_effect = [
            rev_parse_result,
            branch_result,
            log_result,
            status_result,
        ]

        get_git_activity(tmp_path, max_commits=5)
        # Check that git log was called with the correct limit
        log_call = mock_run.call_args_list[2]
        assert "-5" in log_call[0][0] or "-5" in str(log_call)


class TestGetRealmGitActivities:
    """Tests for get_realm_git_activities function."""

    def test_nonexistent_realm_path(self, tmp_path: Path) -> None:
        """Non-existent realm path returns empty dict."""
        activities = get_realm_git_activities(tmp_path / "nonexistent")
        assert activities == {}

    @patch("tui.git_utils.get_git_activity")
    def test_realm_root_is_git_repo(self, mock_get_activity: MagicMock, tmp_path: Path) -> None:
        """When realm root is a git repo, include __realm__ entry."""
        realm_dir = tmp_path / "Asgard"
        realm_dir.mkdir()

        mock_get_activity.side_effect = lambda path, max_commits=10: GitActivity(
            path=path,
            is_git_repo=True,
            branch="main",
        )

        activities = get_realm_git_activities(realm_dir)
        assert "__realm__" in activities
        assert activities["__realm__"].branch == "main"

    @patch("tui.git_utils.get_git_activity")
    def test_project_subdirs_included(self, mock_get_activity: MagicMock, tmp_path: Path) -> None:
        """When project subdirs are git repos, they are included."""
        realm_dir = tmp_path / "Asgard"
        realm_dir.mkdir()
        (realm_dir / "lilith-core").mkdir()
        (realm_dir / "provider-openai").mkdir()

        # Realm root is not a repo, but projects are
        def mock_activity(path: Path, max_commits: int = 10) -> GitActivity:
            if path == realm_dir:
                return GitActivity(path=path, is_git_repo=False)
            return GitActivity(path=path, is_git_repo=True, branch="dev")

        mock_get_activity.side_effect = mock_activity

        activities = get_realm_git_activities(realm_dir)
        assert "lilith-core" in activities
        assert "provider-openai" in activities

    @patch("tui.git_utils.get_git_activity")
    def test_hidden_dirs_excluded(self, mock_get_activity: MagicMock, tmp_path: Path) -> None:
        """Hidden dirs and __pycache__ should be excluded."""
        realm_dir = tmp_path / "Asgard"
        realm_dir.mkdir()
        (realm_dir / ".hidden").mkdir()
        (realm_dir / "__pycache__").mkdir()
        (realm_dir / "visible-project").mkdir()

        mock_get_activity.return_value = GitActivity(path=Path(), is_git_repo=True)

        activities = get_realm_git_activities(realm_dir)
        assert ".hidden" not in activities
        assert "__pycache__" not in activities
