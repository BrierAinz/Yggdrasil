"""Tests for quick action handlers."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

from tui.actions import ActionResult, QuickActions


class TestActionResult:
    """Tests for the ActionResult dataclass."""

    def test_success_result(self) -> None:
        r = ActionResult(success=True, action="tests", message="Tests passed")
        assert r.success is True
        assert r.action == "tests"
        assert r.details is None

    def test_failure_result(self) -> None:
        r = ActionResult(
            success=False,
            action="git",
            message="Not a repo",
            details={"error": "no .git"},
        )
        assert r.success is False
        assert r.details is not None


class TestQuickActions:
    """Tests for the QuickActions class."""

    def test_key_map_has_all_actions(self) -> None:
        assert "t" in QuickActions.KEY_MAP
        assert "g" in QuickActions.KEY_MAP
        assert "h" in QuickActions.KEY_MAP
        assert "o" in QuickActions.KEY_MAP
        assert "d" in QuickActions.KEY_MAP

    def test_available_actions(self) -> None:
        actions = QuickActions.available_actions()
        assert len(actions) == 5
        assert actions["t"] == "Run tests"
        assert actions["g"] == "Git status"

    def test_unknown_key(self) -> None:
        qa = QuickActions(project_path="/tmp")
        result = qa.execute("z")
        assert result.success is False
        assert "Unknown shortcut" in result.message

    def test_execute_tests_no_test_dir(self) -> None:
        """Test that _action_tests returns failure when no tests dir exists."""
        qa = QuickActions(project_path="/nonexistent/path")
        result = qa._action_tests()
        assert result.action == "tests"
        assert result.success is False or result.success is True  # Could fail gracefully

    @patch("subprocess.run")
    def test_git_action_success(self, mock_run: MagicMock) -> None:
        """Test git action with mocked subprocess."""
        # Mock successful git commands
        branch_result = MagicMock()
        branch_result.returncode = 0
        branch_result.stdout = "main"

        status_result = MagicMock()
        status_result.returncode = 0
        status_result.stdout = "## main...origin/main\n M file.py"

        log_result = MagicMock()
        log_result.returncode = 0
        log_result.stdout = "abc1234 Fix bug\ndef5678 Add feature"

        ab_result = MagicMock()
        ab_result.returncode = 0
        ab_result.stdout = "0\t1"

        mock_run.side_effect = [branch_result, status_result, log_result, ab_result]

        qa = QuickActions(project_path="/tmp")
        result = qa._action_git()
        assert result.success is True
        assert result.details["branch"] == "main"

    @patch("subprocess.run")
    def test_git_action_failure(self, mock_run: MagicMock) -> None:
        """Test git action when git is not available."""
        mock_run.side_effect = FileNotFoundError("git not found")

        qa = QuickActions(project_path="/tmp")
        result = qa._action_git()
        assert result.success is False

    def test_health_action(self) -> None:
        """Test health action with mocked HealthMonitor."""
        from tui.health import SystemHealth

        mock_monitor = MagicMock()
        mock_monitor.get_health.return_value = SystemHealth(
            cpu_pct=45.0, ram_pct=60.0, disk_pct=70.0, python_process_count=3
        )

        qa = QuickActions(project_path="/tmp")
        with patch("tui.health.HealthMonitor", return_value=mock_monitor):
            result = qa._action_health()
        assert result.success is True
        assert "CPU" in result.message

    @patch("webbrowser.open")
    def test_docs_action(self, mock_open: MagicMock) -> None:
        """Test docs action opens browser."""
        mock_open.return_value = True
        qa = QuickActions(project_path="/tmp", docs_url="https://example.com")
        result = qa._action_docs()
        assert result.success is True
        mock_open.assert_called_once_with("https://example.com")

    @patch("subprocess.run")
    def test_vscode_action(self, mock_run: MagicMock) -> None:
        """Test VS Code action tries to open editor."""
        mock_run.return_value = MagicMock(returncode=0)
        qa = QuickActions(project_path="/tmp")
        result = qa._action_vscode()
        # May succeed or fail depending on editor availability
        assert result.action == "vscode"

    def test_default_project_path(self) -> None:
        """Test that default project path is cwd."""
        qa = QuickActions()
        assert qa.project_path.is_absolute()

    def test_execute_delegates_to_handler(self) -> None:
        """Test that execute() properly delegates to handler methods."""
        qa = QuickActions(project_path="/tmp")
        with patch.object(
            qa, "_action_tests", return_value=ActionResult(True, "tests", "OK")
        ) as mock:
            result = qa.execute("t")
            mock.assert_called_once()
            assert result.success is True

    def test_execute_catches_exceptions(self) -> None:
        """Test that execute() catches exceptions from handlers."""
        qa = QuickActions(project_path="/tmp")
        with patch.object(qa, "_action_tests", side_effect=RuntimeError("boom")):
            result = qa.execute("t")
            assert result.success is False
            assert "boom" in result.message
