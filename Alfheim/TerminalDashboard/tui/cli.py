"""Yggdrasil Dashboard CLI – Typer-based command-line interface.

Provides the ``yggdrasil-dashboard`` entry point with shell completion
support via Typer's built-in ``--install-completion`` / ``--show-completion``
flags.
"""

from __future__ import annotations

import typer
from rich.console import Console

from tui import __version__


app = typer.Typer(
    name="yggdrasil-dashboard",
    help="☵ Yggdrasil Terminal Dashboard – monitor all realms from one screen.",
    no_args_is_help=False,
    rich_markup_mode="rich",
)

_console = Console()


def _version_callback(value: bool) -> None:
    """Print the version and exit.

    Raises:
        typer.Exit: Always raised when value is True.

    """
    if value:
        _console.print(f"[bold #c8a23e]☵ Yggdrasil Dashboard[/]  [dim]v{__version__}[/]")
        raise typer.Exit()


@app.command()
def dashboard(
    _version: bool = typer.Option(
        False,
        "--version",
        "-v",
        help="Show the dashboard version and exit.",
        callback=_version_callback,
        is_eager=True,
    ),
) -> None:
    """Launch the Yggdrasil Terminal Dashboard TUI.

    The dashboard provides a full-screen, interactive overview of all nine
    Yggdrasil realms with keyboard shortcuts for navigation, git status,
    health monitoring, and quick actions.
    """
    from tui.app import YggdrasilDashboard

    typer.echo("☵  Launching Yggdrasil Dashboard…")
    app_instance = YggdrasilDashboard()
    app_instance.run()


if __name__ == "__main__":
    app()
