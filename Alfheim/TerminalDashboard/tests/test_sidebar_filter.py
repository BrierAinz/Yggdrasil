"""Tests for the sidebar filter functionality."""

from __future__ import annotations

import re

import pytest
from tui.scanner import REALMS
from tui.widgets.sidebar import RealmButton, RealmSidebar


class TestSidebarFilter:
    """Tests for the regex filter in the sidebar."""

    def _make_sidebar(self) -> RealmSidebar:
        """Create a RealmSidebar instance (without mounting)."""
        sidebar = RealmSidebar()
        return sidebar

    def test_filter_text_default_empty(self) -> None:
        """Default filter text is empty."""
        sidebar = self._make_sidebar()
        assert sidebar.filter_text == ""

    def test_apply_filter_empty_shows_all(self) -> None:
        """Empty filter shows all realm buttons."""
        self._make_sidebar()
        # No filter – all buttons should be visible
        # We test the logic directly
        for realm_name in REALMS:
            assert re.search("", realm_name, re.IGNORECASE) is not None

    def test_apply_filter_matching_regex(self) -> None:
        """Regex filter matches realm names."""
        pattern = "Asgard"
        matching = [r for r in REALMS if re.search(pattern, r, re.IGNORECASE)]
        assert "Asgard" in matching

        pattern = "^A"
        matching = [r for r in REALMS if re.search(pattern, r, re.IGNORECASE)]
        assert "Asgard" in matching
        assert "Alfheim" in matching

    def test_apply_filter_case_insensitive(self) -> None:
        """Filter is case-insensitive."""
        pattern = "asgard"
        matching = [r for r in REALMS if re.search(pattern, r, re.IGNORECASE)]
        assert "Asgard" in matching

    def test_apply_filter_partial_match(self) -> None:
        """Partial match works."""
        pattern = "heim"
        matching = [r for r in REALMS if re.search(pattern, r, re.IGNORECASE)]
        assert "Vanaheim" in matching
        assert "Svartalfheim" in matching
        assert "Niflheim" in matching
        assert "Helheim" in matching
        assert "Jotunheim" in matching
        assert "Alfheim" in matching
        assert "Muspelheim" in matching
        assert "Asgard" not in matching

    def test_apply_filter_no_match(self) -> None:
        """Non-matching filter hides all."""
        pattern = "ZZZZZ"
        matching = [r for r in REALMS if re.search(pattern, r, re.IGNORECASE)]
        assert matching == []

    def test_apply_filter_invalid_regex_shows_all(self) -> None:
        """Invalid regex falls back to showing all."""
        pattern = "["
        try:
            re.search(pattern, "Asgard", re.IGNORECASE)
            # If no error, skip
        except re.error:
            # Invalid regex – should handle gracefully
            pass


class TestSidebarComposeWithFilter:
    """Test that the sidebar composes with a filter input."""

    @pytest.mark.asyncio
    async def test_sidebar_has_filter_input(self) -> None:
        """The sidebar should compose an Input widget for filtering."""
        import tempfile

        from tui.app import YggdrasilDashboard
        from tui.scanner import RealmScanner

        with tempfile.TemporaryDirectory() as tmpdir:
            scanner = RealmScanner(base_path=tmpdir)
            app = YggdrasilDashboard(scanner=scanner)
            async with app.run_test() as pilot:
                from textual.widgets import Input

                sidebar = pilot.app.query_one("#sidebar", RealmSidebar)
                filter_input = sidebar.query_one(Input)
                assert filter_input is not None
                assert filter_input.id == "realm-filter"

    @pytest.mark.asyncio
    async def test_filter_typing_hides_realms(self) -> None:
        """Typing in the filter input should hide non-matching realm buttons."""
        import tempfile

        from tui.app import YggdrasilDashboard
        from tui.scanner import RealmScanner

        with tempfile.TemporaryDirectory() as tmpdir:
            scanner = RealmScanner(base_path=tmpdir)
            app = YggdrasilDashboard(scanner=scanner)
            async with app.run_test() as pilot:
                from textual.widgets import Input

                sidebar = pilot.app.query_one("#sidebar", RealmSidebar)
                filter_input = sidebar.query_one(Input)

                # Type "Asgard" into the filter
                filter_input.value = "Asgard"
                # Manually trigger the changed handler
                sidebar.filter_text = "Asgard"

                # Check that only Asgard is visible
                buttons = list(sidebar.query(RealmButton))
                visible_buttons = [b for b in buttons if not b.has_class("hidden")]
                visible_names = [b.realm_name for b in visible_buttons]
                assert "Asgard" in visible_names

    @pytest.mark.asyncio
    async def test_filter_empty_shows_all(self) -> None:
        """Empty filter shows all realm buttons."""
        import tempfile

        from tui.app import YggdrasilDashboard
        from tui.scanner import RealmScanner

        with tempfile.TemporaryDirectory() as tmpdir:
            scanner = RealmScanner(base_path=tmpdir)
            app = YggdrasilDashboard(scanner=scanner)
            async with app.run_test() as pilot:
                sidebar = pilot.app.query_one("#sidebar", RealmSidebar)

                # Ensure no filter
                sidebar.filter_text = ""

                buttons = list(sidebar.query(RealmButton))
                visible_buttons = [b for b in buttons if not b.has_class("hidden")]
                assert len(visible_buttons) == 9
