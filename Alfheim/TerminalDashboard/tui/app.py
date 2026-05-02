"""Yggdrasil TUI Dashboard application."""

from textual.app import App, ComposeResult
from textual.widgets import Footer, Header


class YggdrasilDashboard(App):
    """The Yggdrasil Terminal Dashboard – monitor all realms."""

    TITLE = "Yggdrasil Dashboard"
    SUB_TITLE = "Norse-themed AI agent ecosystem"
    CSS_PATH = "styles.tcss"

    BINDINGS = [
        ("q", "quit", "Quit"),
        ("r", "refresh", "Refresh"),
    ]

    def compose(self) -> ComposeResult:
        """Create child widgets for the app."""
        yield Header()
        yield Footer()

    def action_refresh(self) -> None:
        """Refresh realm data."""
        self.refresh()


def main() -> None:
    """Entry point for the TUI dashboard."""
    app = YggdrasilDashboard()
    app.run()


if __name__ == "__main__":
    main()
