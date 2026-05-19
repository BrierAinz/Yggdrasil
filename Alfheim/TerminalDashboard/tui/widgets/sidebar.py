"""Realm sidebar navigation widget with project filter."""

from __future__ import annotations

import re
from typing import TYPE_CHECKING

from textual.containers import VerticalScroll
from textual.message import Message
from textual.reactive import reactive
from textual.widgets import Button, Input, Static

from tui.scanner import REALMS, HealthStatus, RealmStatus


if TYPE_CHECKING:
    from textual.app import ComposeResult


# Norse-themed icons for each realm
REALM_ICONS: dict[str, str] = {
    "Asgard": "🏔",
    "Vanaheim": "🌿",
    "Alfheim": "✨",
    "Svartalfheim": "🔨",
    "Muspelheim": "🔥",
    "Niflheim": "❄",
    "Helheim": "💀",
    "Jotunheim": "👹",
    "Midgard": "🌍",
}

# Health status dot indicators
HEALTH_MARKERS: dict[HealthStatus, str] = {
    HealthStatus.HEALTHY: "[bold green]●[/]",
    HealthStatus.DEGRADED: "[bold yellow]●[/]",
    HealthStatus.DOWN: "[bold red]○[/]",
}


class RealmButton(Button):
    """A button representing a single realm in the sidebar."""

    def __init__(self, realm_name: str, index: int, **kwargs: object) -> None:
        """Initialize the realm button with icon and label."""
        icon = REALM_ICONS.get(realm_name, "◆")
        label = f" {index}. {icon} {realm_name}"
        super().__init__(label, id=f"realm-{realm_name.lower()}", **kwargs)
        self.realm_name = realm_name
        self.index = index


class RealmSidebar(VerticalScroll):
    """Sidebar showing all 9 Yggdrasil realms for navigation."""

    DEFAULT_CSS = """
    RealmSidebar {
        width: 28;
        background: $surface-darken-3;
        border-right: thick $accent;
        padding: 1 0;
    }
    RealmSidebar > .sidebar-title {
        text-align: center;
        text-style: bold;
        padding: 0 1;
        color: $accent;
    }
    RealmSidebar > .sidebar-subtitle {
        text-align: center;
        padding: 0 1 1 0;
        color: $text-muted;
    }
    RealmSidebar > .filter-label {
        padding: 0 1;
        color: $text-muted;
    }
    RealmSidebar > Input {
        margin: 0 1;
    }
    RealmSidebar > RealmButton {
        width: 100%;
        height: 3;
    }
    RealmSidebar > RealmButton.active {
        background: $accent 20%;
        text-style: bold;
    }
    RealmSidebar > RealmButton.hidden {
        display: none;
    }
    """

    selected_realm: reactive[str] = reactive("Asgard")
    filter_text: reactive[str] = reactive("")

    class RealmSelected(Message):
        """Message posted when a realm is selected."""

        def __init__(self, realm_name: str) -> None:
            """Initialize the realm selection message."""
            super().__init__()
            self.realm_name = realm_name

    def compose(self) -> ComposeResult:
        """Construir el sidebar con título, filtro y botones de reinos.

        Yields:
            Static widgets for title, subtitle, filter input, and realm buttons.

        """
        yield Static("☵ Yggdrasil", classes="sidebar-title")
        yield Static("Realms", classes="sidebar-subtitle")
        yield Static("Filter:", classes="filter-label")
        yield Input(placeholder="regex filter…", id="realm-filter")
        for i, realm_name in enumerate(REALMS, start=1):
            yield RealmButton(realm_name, i)

    def on_mount(self) -> None:
        """Inicializar el resaltado del botón activo al montar."""
        self._highlight_active()

    def watch_selected_realm(self, new_realm: str) -> None:
        """React to selection changes – highlight active button."""
        self._highlight_active()

    def watch_filter_text(self, new_filter: str) -> None:
        """React to filter changes – show/hide realm buttons."""
        self._apply_filter(new_filter)

    def on_input_changed(self, event: Input.Changed) -> None:
        """Handle changes to the filter input."""
        if event.input.id == "realm-filter":
            self.filter_text = event.value

    def _apply_filter(self, pattern: str) -> None:
        """Show/hide realm buttons based on regex filter pattern."""
        for btn in self.query(RealmButton):
            if not pattern:
                btn.remove_class("hidden")
            else:
                try:
                    if re.search(pattern, btn.realm_name, re.IGNORECASE):
                        btn.remove_class("hidden")
                    else:
                        btn.add_class("hidden")
                except re.error:
                    # Invalid regex – show all
                    btn.remove_class("hidden")

    def _highlight_active(self) -> None:
        """Set the 'active' CSS class on the currently selected button."""
        for btn in self.query(RealmButton):
            btn.set_class(btn.realm_name == self.selected_realm, "active")

    def select_realm(self, realm_name: str) -> None:
        """Programmatically select a realm and post a message."""
        if realm_name in REALMS:
            self.selected_realm = realm_name
            self.post_message(self.RealmSelected(realm_name))

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Manejar clic en botón de reino y seleccionarlo."""
        if isinstance(event.button, RealmButton):
            self.select_realm(event.button.realm_name)

    def update_health_indicators(self, realm_statuses: dict[str, RealmStatus]) -> None:
        """Refresh button labels to include health dots."""
        for btn in self.query(RealmButton):
            status = realm_statuses.get(btn.realm_name)
            if status:
                icon = REALM_ICONS.get(btn.realm_name, "◆")
                marker = HEALTH_MARKERS.get(status.health, "[dim]○[/]")
                btn.label = f" {btn.index}. {icon} {btn.realm_name} {marker}"
