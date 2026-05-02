"""AutoSub CLI — Typer application with Rich progress."""

from __future__ import annotations

from pathlib import Path

import typer
from autosub.exporter import export_segments
from autosub.pipeline import Pipeline
from autosub.transcriber import Transcriber
from autosub.translator import Translator
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.table import Table

app = typer.Typer(help="🎬 AutoSub — Automatic subtitle generator")
console = Console()


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
    path = Path(input_file)
    if not path.exists():
        console.print(f"[red]Error: File not found: {input_file}[/]")
        raise typer.Exit(code=1)

    console.print(f"[bold green]AutoSub[/] v0.1.0 — Transcription")
    console.print(f"[dim]Input: {input_file} | Model: {model} | Format: {format}[/]")

    transcriber = Transcriber(model_size=model)

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
    ) as progress:
        task = progress.add_task("Transcribing...", total=None)
        segments = transcriber.transcribe(str(path), language=language)
        progress.update(task, completed=True)

    console.print(f"[green]Transcribed {len(segments)} segments[/]")

    result = export_segments(segments, fmt=format)

    if output:
        out_path = Path(output)
    else:
        out_path = path.with_suffix(f".{format}")

    out_path.write_text(result, encoding="utf-8")
    console.print(f"[green]Written to: {out_path}[/]")


@app.command()
def translate(
    input_srt: str = typer.Argument(..., help="Path to SRT/VTT file"),
    target_lang: str = typer.Option("es", "--to", "-t", help="Target language"),
    output: str = typer.Option(None, "--output", "-o", help="Output file path"),
):
    """Translate existing subtitles."""
    path = Path(input_srt)
    if not path.exists():
        console.print(f"[red]Error: File not found: {input_srt}[/]")
        raise typer.Exit(code=1)

    console.print(f"[bold green]AutoSub[/] — Translate")
    console.print(f"[dim]Input: {input_srt} | Target language: {target_lang}[/]")

    translator = Translator(target_lang=target_lang)

    content = path.read_text(encoding="utf-8")
    lines = content.strip().split("\n")
    translated_lines = []
    for line in lines:
        translated_lines.append(translator.translate_text(line))

    result = "\n".join(translated_lines)

    if output:
        out_path = Path(output)
    else:
        out_path = path.with_suffix(f".{target_lang}{path.suffix}")

    out_path.write_text(result, encoding="utf-8")
    console.print(f"[green]Written to: {out_path}[/]")


@app.command()
def pipeline(
    input_file: str = typer.Argument(..., help="Path to audio/video file"),
    language: str = typer.Option(None, "--lang", "-l", help="Source language"),
    target_lang: str = typer.Option(None, "--translate", "-t", help="Target language"),
    model: str = typer.Option("base", "--model", "-m", help="Whisper model size"),
    format: str = typer.Option(
        "srt", "--format", "-f", help="Output format: srt, vtt, txt"
    ),
    output: str = typer.Option(None, "--output", "-o", help="Output file path"),
):
    """Full pipeline: transcribe → translate → export."""
    pipe = Pipeline(model_size=model)
    try:
        result = pipe.run(
            input_path=input_file,
            language=language,
            target_lang=target_lang,
            output_format=format,
            output_path=output,
            console=console,
        )
        console.print(f"[bold green]✓ Pipeline complete[/]")
        console.print(f"  Segments: {result.segments_count}")
        console.print(f"  Output: {result.output_path}")
        if result.translated:
            console.print(f"  Translated to: {result.target_lang}")
    except FileNotFoundError as e:
        console.print(f"[red]Error: {e}[/]")
        raise typer.Exit(code=1)


@app.command()
def info():
    """Show AutoSub configuration and system info."""
    console.print("[bold green]AutoSub[/] v0.1.0")
    table = Table(title="System Info")
    table.add_column("Setting", style="cyan")
    table.add_column("Value", style="white")

    t = Transcriber()
    table.add_row("Default model", t.model_size)
    table.add_row("GPU available", str(t._has_gpu()))

    console.print(table)


if __name__ == "__main__":
    app()
