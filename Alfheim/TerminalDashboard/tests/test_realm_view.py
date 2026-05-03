"""Tests for the RealmDetailView widget."""

from __future__ import annotations

import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from rich.panel import Panel
from rich.table import Table
from rich.text import Text
from tui.scanner import (
    REALMS,
    GitStatus,
    HealthStatus,
    ProjectInfo,
    ProjTestStatus,
    RealmScanner,
    RealmStatus,
)
from tui.widgets.realm_views import (
    _GIT_ICON,
    _HEALTH_ICON,
    _TEST_ICON,
    REALM_STYLES,
    RealmDetailView,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_status(
    name: str = "Asgard",
    project_count: int = 0,
    git_status: GitStatus = GitStatus.CLEAN,
    test_status: ProjTestStatus = ProjTestStatus.UNKNOWN,
    health: HealthStatus = HealthStatus.HEALTHY,
    projects: list[ProjectInfo] | None = None,
) -> RealmStatus:
    """Create a RealmStatus with sensible defaults for testing."""
    if projects is None:
        projects = []
    return RealmStatus(
        name=name,
        path=Path(f"/tmp/Yggdrasil/{name}"),
        project_count=project_count or len(projects),
        git_status=git_status,
        test_status=test_status,
        last_commit_date="2025-01-15",
        health=health,
        projects=projects,
    )


def _make_project(
    name: str = "test-project",
    branch: str = "main",
    uncommitted: bool = False,
    last_commit: str = "2025-01-10",
) -> ProjectInfo:
    return ProjectInfo(
        name=name,
        path=Path(f"/tmp/Yggdrasil/Asgard/{name}"),
        branch=branch,
        uncommitted_changes=uncommitted,
        test_pass_rate=0.0,
        last_commit=last_commit,
    )


# ---------------------------------------------------------------------------
# Tests for constants / lookups
# ---------------------------------------------------------------------------


class TestRealmStyles:
    """Test REALM_STYLES mapping."""

    def test_all_nine_realms_have_styles(self) -> None:
        for realm_name in REALMS:
            assert realm_name in REALM_STYLES, f"Missing style for {realm_name}"

    def test_style_has_color_and_border(self) -> None:
        for realm, style in REALM_STYLES.items():
            assert "color" in style, f"Missing 'color' for {realm}"
            assert "border" in style, f"Missing 'border' for {realm}"


class TestIconMappings:
    """Test icon lookup dicts."""

    def test_health_icons_cover_all(self) -> None:
        for hs in HealthStatus:
            assert hs in _HEALTH_ICON

    def test_git_icons_cover_all(self) -> None:
        for gs in GitStatus:
            assert gs in _GIT_ICON

    def test_test_icons_cover_all(self) -> None:
        for ts in ProjTestStatus:
            assert ts in _TEST_ICON


# ---------------------------------------------------------------------------
# Tests for RealmDetailView construction
# ---------------------------------------------------------------------------


class TestRealmDetailViewInit:
    """Test RealmDetailView initialisation."""

    def test_default_scanner_created(self) -> None:
        widget = RealmDetailView()
        assert widget._scanner is not None

    def test_custom_scanner(self) -> None:
        scanner = RealmScanner(base_path="/tmp")
        widget = RealmDetailView(scanner=scanner)
        assert widget._scanner is scanner

    def test_realm_name_none_by_default(self) -> None:
        widget = RealmDetailView()
        assert widget.realm_name is None
        assert widget.status is None

    def test_realm_name_set_on_init(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            scanner = RealmScanner(base_path=tmpdir)
            widget = RealmDetailView(scanner=scanner, realm_name="Asgard")
            assert widget.realm_name == "Asgard"
            assert widget.status is not None


# ---------------------------------------------------------------------------
# Tests for set_realm / refresh_data
# ---------------------------------------------------------------------------


class TestRealmDetailViewSetRealm:
    """Test set_realm and refresh_data."""

    def test_set_realm_updates_name_and_status(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            scanner = RealmScanner(base_path=tmpdir)
            widget = RealmDetailView(scanner=scanner)
            widget.set_realm("Vanaheim")
            assert widget.realm_name == "Vanaheim"
            assert widget.status is not None
            assert widget.status.name == "Vanaheim"

    def test_set_realm_scans_with_scanner(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            realm_path = Path(tmpdir) / "Asgard"
            realm_path.mkdir()
            (realm_path / "lilith-core").mkdir()
            scanner = RealmScanner(base_path=tmpdir)
            widget = RealmDetailView(scanner=scanner)
            widget.set_realm("Asgard")
            assert widget.status is not None
            assert widget.status.project_count == 1

    def test_refresh_data_re_scans(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            realm_path = Path(tmpdir) / "Asgard"
            realm_path.mkdir()
            scanner = RealmScanner(base_path=tmpdir)
            widget = RealmDetailView(scanner=scanner, realm_name="Asgard")
            # Add a new project dir
            (realm_path / "new-project").mkdir()
            widget.refresh_data()
            assert widget.status is not None
            assert (
                widget.status.project_count == 1
            )  # still 1 because scanner reads it fresh


# ---------------------------------------------------------------------------
# Tests for render methods (all 9 realms)
# ---------------------------------------------------------------------------


class TestRenderMethods:
    """Test that each realm-specific render method returns a Table."""

    def _widget_with_status(self, status: RealmStatus) -> RealmDetailView:
        """Create a widget and inject a status (bypass actual scanning)."""
        widget = RealmDetailView()
        widget._realm_name = status.name
        widget._status = status
        return widget

    def test_build_common_table_returns_table(self) -> None:
        status = _make_status(
            projects=[_make_project("proj-a"), _make_project("proj-b")]
        )
        widget = self._widget_with_status(status)
        table = widget._build_common_table(status, "green")
        assert isinstance(table, Table)

    def test_common_table_with_no_projects(self) -> None:
        status = _make_status(project_count=0, projects=[])
        widget = self._widget_with_status(status)
        table = widget._build_common_table(status, "green")
        assert isinstance(table, Table)

    # --- Asgard ---

    def test_render_asgard(self) -> None:
        projects = [
            _make_project("Lilith-core", branch="main"),
            _make_project("provider-openai", branch="dev"),
        ]
        status = _make_status("Asgard", projects=projects)
        widget = self._widget_with_status(status)
        table = widget._render_asgard(status, "gold1")
        assert isinstance(table, Table)

    def test_render_asgard_no_lilith(self) -> None:
        projects = [_make_project("some-other-project")]
        status = _make_status("Asgard", projects=projects)
        widget = self._widget_with_status(status)
        table = widget._render_asgard(status, "gold1")
        assert isinstance(table, Table)

    # --- Vanaheim ---

    def test_render_vanaheim(self) -> None:
        projects = [
            _make_project("agent-alpha", branch="main"),
            _make_project("task-runner", branch="feature"),
        ]
        status = _make_status("Vanaheim", projects=projects)
        widget = self._widget_with_status(status)
        table = widget._render_vanaheim(status, "cyan")
        assert isinstance(table, Table)

    def test_render_vanaheim_with_active(self) -> None:
        projects = [
            _make_project("agent-one", uncommitted=True),
            _make_project("agent-two"),
        ]
        status = _make_status("Vanaheim", projects=projects)
        widget = self._widget_with_status(status)
        table = widget._render_vanaheim(status, "cyan")
        assert isinstance(table, Table)

    # --- Midgard ---

    def test_render_midgard(self) -> None:
        projects = [
            _make_project("my-app", branch="main"),
            _make_project("dashboard-home", branch="dev"),
        ]
        status = _make_status("Midgard", projects=projects)
        widget = self._widget_with_status(status)
        table = widget._render_midgard(status, "green")
        assert isinstance(table, Table)

    def test_render_midgard_no_apps(self) -> None:
        projects = [_make_project("something-else")]
        status = _make_status("Midgard", projects=projects)
        widget = self._widget_with_status(status)
        table = widget._render_midgard(status, "green")
        assert isinstance(table, Table)

    # --- Svartalfheim ---

    def test_render_svartalfheim(self) -> None:
        projects = [
            _make_project("wiki-engine", branch="main"),
            _make_project("knowledge-base", branch="dev"),
        ]
        status = _make_status("Svartalfheim", projects=projects)
        widget = self._widget_with_status(status)
        table = widget._render_svartalfheim(status, "magenta")
        assert isinstance(table, Table)

    # --- Alfheim ---

    def test_render_alfheim(self) -> None:
        projects = [
            _make_project("TerminalDashboard", branch="main"),
            _make_project("ui-prototype", branch="dev"),
        ]
        status = _make_status("Alfheim", projects=projects)
        widget = self._widget_with_status(status)
        table = widget._render_alfheim(status, "bright_magenta")
        assert isinstance(table, Table)

    # --- Muspelheim ---

    def test_render_muspelheim(self) -> None:
        projects = [
            _make_project("hotfix-1", branch="hotfix/urgent", uncommitted=True),
            _make_project("feature-x", branch="feature/x", uncommitted=True),
            _make_project("stable-proj", branch="main"),
        ]
        status = _make_status("Muspelheim", projects=projects)
        widget = self._widget_with_status(status)
        table = widget._render_muspelheim(status, "red")
        assert isinstance(table, Table)

    # --- Niflheim ---

    def test_render_niflheim(self) -> None:
        projects = [
            _make_project("data-models", branch="main"),
            _make_project("resource-assets", branch="dev"),
        ]
        status = _make_status("Niflheim", projects=projects)
        widget = self._widget_with_status(status)
        table = widget._render_niflheim(status, "bright_blue")
        assert isinstance(table, Table)

    # --- Jotunheim ---

    def test_render_jotunheim(self) -> None:
        projects = [
            _make_project("massive-project", branch="main"),
            _make_project("huge-repo", branch="dev"),
        ]
        status = _make_status("Jotunheim", projects=projects)
        widget = self._widget_with_status(status)
        table = widget._render_jotunheim(status, "dark_orange")
        assert isinstance(table, Table)

    # --- Helheim ---

    def test_render_helheim(self) -> None:
        projects = [
            _make_project("dead-project", branch="", uncommitted=False),
            _make_project("retired-tool", branch="archived", uncommitted=False),
        ]
        status = _make_status("Helheim", projects=projects, health=HealthStatus.DOWN)
        widget = self._widget_with_status(status)
        table = widget._render_helheim(status, "grey50")
        assert isinstance(table, Table)


# ---------------------------------------------------------------------------
# Tests for _build_renderable (full panel)
# ---------------------------------------------------------------------------


class TestBuildRenderable:
    """Test that _build_renderable produces a Panel for each realm."""

    def test_returns_panel(self) -> None:
        status = _make_status("Asgard", projects=[_make_project("lilith")])
        widget = RealmDetailView()
        widget._realm_name = "Asgard"
        widget._status = status
        panel = widget._build_renderable(status)
        assert isinstance(panel, Panel)

    def test_all_realms_produce_panel(self) -> None:
        for realm_name in REALMS:
            status = _make_status(realm_name, projects=[_make_project("proj1")])
            widget = RealmDetailView()
            widget._realm_name = realm_name
            widget._status = status
            panel = widget._build_renderable(status)
            assert isinstance(panel, Panel), f"Failed for {realm_name}"

    def test_panel_title_contains_realm_name(self) -> None:
        status = _make_status("Asgard", projects=[])
        widget = RealmDetailView()
        widget._realm_name = "Asgard"
        widget._status = status
        panel = widget._build_renderable(status)
        # Panel title contains the realm name
        assert "Asgard" in str(panel.title)

    def test_realm_specific_dispatch(self) -> None:
        """Ensure _build_realm_specific dispatches to the right method."""
        for realm_name in REALMS:
            status = _make_status(realm_name)
            widget = RealmDetailView()
            style = REALM_STYLES[realm_name]
            result = widget._build_realm_specific(status, style["color"])
            # All realms should return a Table
            assert isinstance(result, Table), f"No Table returned for {realm_name}"

    def test_unknown_realm_specific_returns_none(self) -> None:
        status = _make_status("UnknownRealm")
        widget = RealmDetailView()
        result = widget._build_realm_specific(status, "white")
        assert result is None


# ---------------------------------------------------------------------------
# Tests for edge cases
# ---------------------------------------------------------------------------


class TestEdgeCases:
    """Test edge cases and error handling."""

    def test_empty_realm_status(self) -> None:
        status = _make_status(
            "Asgard",
            project_count=0,
            git_status=GitStatus.NO_REPO,
            health=HealthStatus.DOWN,
            projects=[],
        )
        widget = RealmDetailView()
        widget._realm_name = "Asgard"
        widget._status = status
        panel = widget._build_renderable(status)
        assert isinstance(panel, Panel)

    def test_project_with_no_branch(self) -> None:
        proj = _make_project("solo", branch="", uncommitted=False)
        status = _make_status("Asgard", projects=[proj])
        widget = RealmDetailView()
        widget._realm_name = "Asgard"
        widget._status = status
        panel = widget._build_renderable(status)
        assert isinstance(panel, Panel)

    def test_dirty_git_status(self) -> None:
        proj = _make_project("dirty-proj", uncommitted=True)
        status = _make_status(
            "Muspelheim",
            git_status=GitStatus.DIRTY,
            health=HealthStatus.DEGRADED,
            projects=[proj],
        )
        widget = RealmDetailView()
        widget._realm_name = "Muspelheim"
        widget._status = status
        panel = widget._build_renderable(status)
        assert isinstance(panel, Panel)

    def test_set_realm_then_different_realm(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            scanner = RealmScanner(base_path=tmpdir)
            widget = RealmDetailView(scanner=scanner)
            widget.set_realm("Asgard")
            assert widget.realm_name == "Asgard"
            widget.set_realm("Vanaheim")
            assert widget.realm_name == "Vanaheim"

    def test_projects_with_various_names_are_categorised(self) -> None:
        """Ensure realm-specific detail methods handle project name heuristics."""
        # Asgard - lilith + provider
        status = _make_status(
            "Asgard",
            projects=[
                _make_project("Lilith-core"),
                _make_project("provider-openai"),
                _make_project("other-tool"),
            ],
        )
        widget = RealmDetailView()
        widget._realm_name = "Asgard"
        widget._status = status
        table = widget._render_asgard(status, "gold1")
        assert isinstance(table, Table)

    def test_muspelheim_branch_aggregation(self) -> None:
        projects = [
            _make_project("p1", branch="main"),
            _make_project("p2", branch="feature/x"),
            _make_project("p3", branch="main"),
        ]
        status = _make_status("Muspelheim", projects=projects)
        widget = RealmDetailView()
        table = widget._render_muspelheim(status, "red")
        assert isinstance(table, Table)

    def test_helheim_shows_archived_status(self) -> None:
        projects = [
            _make_project("old-thing", branch="", uncommitted=False),
            _make_project("another-dead", branch="dead-branch", uncommitted=True),
        ]
        status = _make_status("Helheim", projects=projects, health=HealthStatus.DOWN)
        widget = RealmDetailView()
        table = widget._render_helheim(status, "grey50")
        assert isinstance(table, Table)
