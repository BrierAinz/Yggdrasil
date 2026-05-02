"""AutoSub CLI — Typer application."""

import typer

app = typer.Typer(help="🎬 AutoSub — Automatic subtitle generator")


@app.command()
def transcribe(
    input_file: str = typer.Argument(..., help="Path to audio/video file"),
    language: str = typer.Option(
        None, "--lang", "-l", help="Source language (auto-detect)"
    ),
    model: str = typer.Option("base", "--model", "-m", help="Whisper model size"),
    output: str = typer.Option(None, "--output", "-o", help="Output file path"),
    format: str = typer.Option(
        "srt", "--format", "-f", help="Output format: srt, vtt, txt"
    ),
):
    """Transcribe audio/video to subtitles."""
    from rich.console import Console

    console = Console()
    console.print(f"[bold green]AutoSub[/] v0.1.0")
    console.print(f"[dim]Input: {input_file} | Model: {model} | Format: {format}[/]")
    console.print("[yellow]Transcription not yet implemented[/]")


@app.command()
def translate(
    input_srt: str = typer.Argument(..., help="Path to SRT file"),
    target_lang: str = typer.Option("es", "--to", "-t", help="Target language"),
    output: str = typer.Option(None, "--output", "-o", help="Output file path"),
):
    """Translate existing subtitles."""
    from rich.console import Console

    console = Console()
    console.print(f"[bold green]AutoSub[/] — Translate")
    console.print(f"[dim]Input: {input_srt} | Target: {target_lang}[/]")
    console.print("[yellow]Translation not yet implemented[/]")


if __name__ == "__main__":
    app()
