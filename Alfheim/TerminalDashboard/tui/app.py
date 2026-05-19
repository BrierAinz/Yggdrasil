"""Yggdrasil TUI Dashboard application."""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal
from textual.widgets import Footer, Static

from tui.scanner import REALMS, RealmScanner, RealmStatus
from tui.widgets.detail import RealmDetailView
from tui.widgets.sidebar import RealmSidebar


if TYPE_CHECKING:
    from textual import events


# Mapping of number keys (1-9) to realm names
_REALM_KEYS: dict[str, str] = {str(i): name for i, name in enumerate(REALMS, start=1)}


class DashboardHeader(Static):
    """Custom header with Yggdrasil logo and live timestamp."""

    DEFAULT_CSS = """
    DashboardHeader {
        height: 3;
        background: #1a1b26;
        color: #e0e0e0;
        padding: 0 1;
    }
    """

    def render(self) -> str:
        """Renderizar el header con timestamp en vivo.

        Returns:
            Rich-formatted string with logo and live clock.

        """
        ts = datetime.now().strftime("%Y-%m-%d %H:%M")
        return (
            " [bold #c8a23e]☵ Yggdrasil Dashboard[/]"
            f"    [dim]Norse-themed AI agent ecosystem[/]"
            f"\n [dim]Monitoring {len(REALMS)} realms[/]"
            f"                                        {ts}"
        )


class YggdrasilDashboard(App):
    """The Yggdrasil Terminal Dashboard – monitor all realms."""

    TITLE = "Yggdrasil Dashboard"
    SUB_TITLE = "Norse-themed AI agent ecosystem"
    CSS_PATH = "styles.tcss"

    BINDINGS = [
        Binding("q", "quit", "Quit", show=True),
        Binding("r", "refresh", "Refresh", show=True),
        # Number keys 1-9 for realm switching
        Binding("1", "select_realm", "Asgard", show=True),
        Binding("2", "select_realm", "Vanaheim", show=True),
        Binding("3", "select_realm", "Alfheim", show=True),
        Binding("4", "select_realm", "Svartalfheim", show=True),
        Binding("5", "select_realm", "Muspelheim", show=True),
        Binding("6", "select_realm", "Niflheim", show=True),
        Binding("7", "select_realm", "Helheim", show=True),
        Binding("8", "select_realm", "Jotunheim", show=True),
        Binding("9", "select_realm", "Midgard", show=True),
    ]

    def __init__(self, scanner: RealmScanner | None = None, **kwargs: object) -> None:
        super().__init__(**kwargs)
        self._scanner = scanner or RealmScanner()
        self._realm_data: dict[str, RealmStatus] = {}

    # ── Composition ──────────────────────────────────────────

    def compose(self) -> ComposeResult:
        """Create child widgets for the app.

        Yields:
            DashboardHeader, RealmSidebar, RealmDetailView, and Footer widgets.

        """
        yield DashboardHeader(id="app-header")
        with Horizontal(id="main-grid"):
            yield RealmSidebar(id="sidebar")
            yield RealmDetailView(id="content-area")
        yield Footer()

    # ── Lifecycle ─────────────────────────────────────────────

    def on_mount(self) -> None:
        """Perform initial realm scan on startup."""
        self._load_realms()

    # ── Data loading ──────────────────────────────────────────

    def _load_realms(self) -> None:
        """Scan all realms and update child widgets."""
        self._realm_data = self._scanner.scan_all()

        sidebar = self.query_one("#sidebar", RealmSidebar)
        detail = self.query_one("#content-area", RealmDetailView)

        sidebar.update_health_indicators(self._realm_data)
        detail.realm_data = self._realm_data
        detail.selected_realm = sidebar.selected_realm

    # ── Actions ───────────────────────────────────────────────

    def action_refresh(self) -> None:
        """Refresh realm data."""
        self._load_realms()

    def action_select_realm(self) -> None:
        """Select a realm based on the key that triggered this action.

        Since Textual bindings map a key to an action name without
        parameters, we look up the originally-pressed key to
        determine which realm was requested.
        """
        # self.pressured_key is not available; we intercept via on_key below.

    # ── Key handling ──────────────────────────────────────────

    def on_key(self, event: events.Key) -> None:  # type: ignore[override]
        """Handle number keys 1-9 for realm switching."""
        realm_name = _REALM_KEYS.get(event.key)
        if realm_name:
            self._switch_realm(realm_name)

    # ── Realm message from sidebar click ──────────────────────

    def on_realm_sidebar_realm_selected(self, message: RealmSidebar.RealmSelected) -> None:
        """Handle realm selection from the sidebar buttons."""
        self._switch_realm(message.realm_name)

    # ── Internal ──────────────────────────────────────────────

    def _switch_realm(self, realm_name: str) -> None:
        """Switch the dashboard to show the given realm."""
        sidebar = self.query_one("#sidebar", RealmSidebar)
        detail = self.query_one("#content-area", RealmDetailView)
        sidebar.selected_realm = realm_name
        detail.selected_realm = realm_name


# ── Entry point ────────────────────────────────────────────────


def main() -> None:
    """Entry point for the TUI dashboard."""
    app = YggdrasilDashboard()
    app.run()


if __name__ == "__main__":
    main()
