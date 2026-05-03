"""ForgeMaster CLI — Typer application with Rich output."""

from __future__ import annotations

import typer

app = typer.Typer(help="⚒️  ForgeMaster — Niflheim resource manager")


@app.command()
def scan(
    path: list[str] = typer.Option(
        [], "--path", "-p", help="Additional paths to scan"
    ),
):
    """Scan directories for model files."""
    from rich.console import Console

    console = Console()
    console.print("[bold green]ForgeMaster[/] v0.1.0 — Scan")


@app.command()
def list_models(
    model_type: str = typer.Option(
        "all", "--type", "-t", help="Filter: llm, diffusion, all"
    ),
):
    """List all cataloged models."""
    from rich.console import Console

    console = Console()
    console.print("[bold green]ForgeMaster[/] v0.1.0 — List Models")


@app.command()
def stats():
    """Show disk usage and model statistics."""
    from rich.console import Console

    console = Console()
    console.print("[bold green]ForgeMaster[/] v0.1.0 — Stats")


@app.command()
def check(model_name: str = typer.Argument(..., help="Model name to check")):
    """Check if a model can run on current GPU."""
    from rich.console import Console

    console = Console()
    console.print(f"[bold green]ForgeMaster[/] — Checking {model_name}")


if __name__ == "__main__":
    app()
