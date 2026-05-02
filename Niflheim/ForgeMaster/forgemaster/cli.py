"""ForgeMaster CLI - manage Niflheim resources."""

import typer

app = typer.Typer(
    name="forgemaster",
    help="CLI tool for managing Niflheim resources: LLM models, datasets, checkpoints, VRAM monitoring, disk usage.",
)


@app.command()
def version():
    """Show ForgeMaster version."""
    from forgemaster import __version__

    typer.echo(f"ForgeMaster v{__version__}")


if __name__ == "__main__":
    app()
