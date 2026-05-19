"""Tests for the Yggdrasil Dashboard TUI application.

Uses Textual's headless testing via ``app.run_test()``.
"""

from __future__ import annotations

import tempfile
from pathlib import Path

import pytest
from tui.app import _REALM_KEYS, YggdrasilDashboard
from tui.scanner import (
    REALMS,
    GitStatus,
    HealthStatus,
    ProjTestStatus,
    RealmScanner,
    RealmStatus,
)
from tui.widgets.detail import RealmDetailView
from tui.widgets.sidebar import REALM_ICONS, RealmButton, RealmSidebar


# ── Helpers ────────────────────────────────────────────────────────


def _make_status(name: str) -> RealmStatus:
    """Create a minimal RealmStatus for testing."""
    return RealmStatus(
        name=name,
        path=Path(f"/tmp/Yggdrasil/{name}"),
        project_count=0,
        git_status=GitStatus.NO_REPO,
        test_status=ProjTestStatus.UNKNOWN,
        health=HealthStatus.DOWN,
    )


def _make_app() -> YggdrasilDashboard:
    """Create an app instance with a scanner pointed at a temp dir."""
    tmpdir = tempfile.mkdtemp()
    scanner = RealmScanner(base_path=tmpdir)
    return YggdrasilDashboard(scanner=scanner)


# ── App composition tests ──────────────────────────────────────


class TestAppComposition:
    """Test that the app composes all expected widgets."""

    @pytest.mark.asyncio
    async def test_app_mounts_header(self) -> None:
        async with _make_app().run_test() as pilot:
            app = pilot.app
            assert app.query_one("#app-header") is not None

    @pytest.mark.asyncio
    async def test_app_mounts_sidebar(self) -> None:
        async with _make_app().run_test() as pilot:
            app = pilot.app
            sidebar = app.query_one("#sidebar", RealmSidebar)
            assert sidebar is not None
            # Sidebar should contain a button per realm
            buttons = sidebar.query(RealmButton)
            assert buttons is not None

    @pytest.mark.asyncio
    async def test_app_mounts_detail_view(self) -> None:
        async with _make_app().run_test() as pilot:
            app = pilot.app
            detail = app.query_one("#content-area", RealmDetailView)
            assert detail is not None

    @pytest.mark.asyncio
    async def test_app_mounts_footer(self) -> None:
        async with _make_app().run_test() as pilot:
            from textual.widgets import Footer

            app = pilot.app
            footer = app.query_one(Footer)
            assert footer is not None

    @pytest.mark.asyncio
    async def test_sidebar_has_nine_realm_buttons(self) -> None:
        async with _make_app().run_test() as pilot:
            sidebar = pilot.app.query_one("#sidebar", RealmSidebar)
            buttons = list(sidebar.query(RealmButton))
            assert len(buttons) == 9

    @pytest.mark.asyncio
    async def test_initial_selected_realm_is_asgard(self) -> None:
        async with _make_app().run_test() as pilot:
            sidebar = pilot.app.query_one("#sidebar", RealmSidebar)
            assert sidebar.selected_realm == "Asgard"


# ── Realm key mapping tests ────────────────────────────────────


class TestRealmKeyMapping:
    """Test the 1-9 key to realm mapping."""

    def test_nine_mappings(self) -> None:
        assert len(_REALM_KEYS) == 9

    def test_key_1_maps_to_asgard(self) -> None:
        assert _REALM_KEYS["1"] == "Asgard"

    def test_key_9_maps_to_midgard(self) -> None:
        assert _REALM_KEYS["9"] == "Midgard"

    def test_all_realms_represented(self) -> None:
        assert set(_REALM_KEYS.values()) == set(REALMS.keys())


# ── Realm switching tests ──────────────────────────────────────


class TestRealmSwitching:
    """Test realm switching via number keys and sidebar clicks."""

    @pytest.mark.asyncio
    async def test_key_2_switches_to_vanaheim(self) -> None:
        async with _make_app().run_test() as pilot:
            sidebar = pilot.app.query_one("#sidebar", RealmSidebar)
            detail = pilot.app.query_one("#content-area", RealmDetailView)

            await pilot.press("2")
            assert sidebar.selected_realm == "Vanaheim"
            assert detail.selected_realm == "Vanaheim"

    @pytest.mark.asyncio
    async def test_key_5_switches_to_muspelheim(self) -> None:
        async with _make_app().run_test() as pilot:
            sidebar = pilot.app.query_one("#sidebar", RealmSidebar)
            detail = pilot.app.query_one("#content-area", RealmDetailView)

            await pilot.press("5")
            assert sidebar.selected_realm == "Muspelheim"
            assert detail.selected_realm == "Muspelheim"

    @pytest.mark.asyncio
    async def test_key_9_switches_to_midgard(self) -> None:
        async with _make_app().run_test() as pilot:
            sidebar = pilot.app.query_one("#sidebar", RealmSidebar)
            detail = pilot.app.query_one("#content-area", RealmDetailView)

            await pilot.press("9")
            assert sidebar.selected_realm == "Midgard"
            assert detail.selected_realm == "Midgard"

    @pytest.mark.asyncio
    async def test_sequential_realm_switching(self) -> None:
        """Verify switching realms multiple times in a row."""
        async with _make_app().run_test() as pilot:
            sidebar = pilot.app.query_one("#sidebar", RealmSidebar)
            detail = pilot.app.query_one("#content-area", RealmDetailView)

            for key, expected_name in [
                ("3", "Alfheim"),
                ("7", "Helheim"),
                ("1", "Asgard"),
            ]:
                await pilot.press(key)
                assert sidebar.selected_realm == expected_name
                assert detail.selected_realm == expected_name


# ── Sidebar active state tests ─────────────────────────────────


class TestSidebarActiveState:
    """Test that the sidebar highlights the active realm."""

    @pytest.mark.asyncio
    async def test_active_button_has_css_class(self) -> None:
        async with _make_app().run_test() as pilot:
            sidebar = pilot.app.query_one("#sidebar", RealmSidebar)
            buttons = list(sidebar.query(RealmButton))

            # Initially Asgard (key 1) should be active
            asgard_btn = next(b for b in buttons if b.realm_name == "Asgard")
            assert asgard_btn.has_class("active")

            # Switch to Vanaheim (key 2)
            await pilot.press("2")
            assert not asgard_btn.has_class("active")
            vanaheim_btn = next(b for b in buttons if b.realm_name == "Vanaheim")
            assert vanaheim_btn.has_class("active")


# ── Detail view content tests ──────────────────────────────────


class TestDetailViewContent:
    """Test that the detail view shows realm information."""

    @pytest.mark.asyncio
    async def test_detail_view_renders_selected_realm(self) -> None:
        async with _make_app().run_test() as pilot:
            detail = pilot.app.query_one("#content-area", RealmDetailView)

            # After mount, the detail view should show some content
            content = detail.render()
            # The content should reference the selected realm
            assert "Asgard" in str(content)

    @pytest.mark.asyncio
    async def test_detail_view_updates_on_realm_switch(self) -> None:
        async with _make_app().run_test() as pilot:
            detail = pilot.app.query_one("#content-area", RealmDetailView)

            await pilot.press("6")  # Niflheim
            # Allow the UI to update
            await pilot.pause()
            content = str(detail.render())
            assert "Niflheim" in content


# ── Health indicator tests ─────────────────────────────────────


class TestHealthIndicators:
    """Test that health indicators are rendered correctly in the sidebar."""

    @pytest.mark.asyncio
    async def test_update_health_indicators_populates_labels(self) -> None:
        async with _make_app().run_test() as pilot:
            sidebar = pilot.app.query_one("#sidebar", RealmSidebar)
            buttons = list(sidebar.query(RealmButton))

            # After mount (which calls _load_realms), buttons should exist
            assert len(buttons) == 9

            # Each button label should contain its realm name
            for btn in buttons:
                assert btn.realm_name in str(btn.label)


# ── Widget constants tests ────────────────────────────────────


class TestWidgetConstants:
    """Test sidebar widget constants."""

    def test_realm_icons_has_nine_entries(self) -> None:
        assert len(REALM_ICONS) == 9

    def test_realm_icons_match_realms(self) -> None:
        assert set(REALM_ICONS.keys()) == set(REALMS.keys())

    def test_realm_icons_are_strings(self) -> None:
        for icon in REALM_ICONS.values():
            assert isinstance(icon, str)
            assert len(icon) > 0


# ── Refresh action test ────────────────────────────────────────


class TestRefreshAction:
    """Test the refresh keybinding."""

    @pytest.mark.asyncio
    async def test_refresh_does_not_crash(self) -> None:
        async with _make_app().run_test() as pilot:
            await pilot.press("r")
            # Should not raise any exceptions
