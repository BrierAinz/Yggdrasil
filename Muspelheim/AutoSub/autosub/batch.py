"""AutoSub batch processing — process multiple files at once."""

from __future__ import annotations

from pathlib import Path

from rich.console import Console
from rich.progress import Progress

from autosub.exporter import export_segments
from autosub.pipeline import PipelineResult
from autosub.transcriber import Transcriber
from autosub.translator import Translator

# Supported audio/video extensions
AUDIO_EXTENSIONS = {".mp3", ".wav", ".flac", ".ogg", ".m4a", ".aac", ".wma"}
VIDEO_EXTENSIONS = {".mp4", ".mkv", ".avi", ".mov", ".webm", ".flv", ".wmv"}
SUPPORTED_EXTENSIONS = AUDIO_EXTENSIONS | VIDEO_EXTENSIONS


class BatchProcessor:
    """Process multiple audio/video files for subtitle generation."""

    def __init__(
        self,
        model_size: str = "base",
        device: str = "auto",
        compute_type: str = "int8",
    ):
        self.model_size = model_size
        self.device = device
        self.compute_type = compute_type

    def scan_directory(self, directory: str, recursive: bool = False) -> list[Path]:
        """Scan a directory for supported audio/video files.

        Args:
            directory: Path to scan.
            recursive: Whether to scan subdirectories.

        Returns:
            Sorted list of file paths.

        """
        path = Path(directory)
        if not path.exists():
            raise FileNotFoundError(f"Directory not found: {directory}")
        if not path.is_dir():
            raise ValueError(f"Not a directory: {directory}")

        pattern = "**/*" if recursive else "*"
        files = []
        for f in path.glob(pattern):
            if f.is_file() and f.suffix.lower() in SUPPORTED_EXTENSIONS:
                files.append(f)

        return sorted(files)

    def process_batch(
        self,
        directory: str,
        language: str | None = None,
        target_lang: str | None = None,
        output_format: str = "srt",
        output_dir: str | None = None,
        recursive: bool = False,
        console: Console | None = None,
    ) -> list[PipelineResult]:
        """Process all supported files in a directory.

        Args:
            directory: Path to directory to scan.
            language: Source language (None for auto-detect).
            target_lang: Target language for translation (None = no translation).
            output_format: Output format — srt, vtt, txt.
            output_dir: Output directory (None = same as input files).
            recursive: Scan subdirectories.
            console: Rich console for progress.

        Returns:
            List of PipelineResult objects.

        """
        if console is None:
            console = Console()

        files = self.scan_directory(directory, recursive=recursive)

        if not files:
            console.print("[yellow]No supported audio/video files found.[/]")
            return []

        console.print(f"[bold green]AutoSub[/] — Found {len(files)} file(s)")

        transcriber = Transcriber(
            model_size=self.model_size,
            device=self.device,
            compute_type=self.compute_type,
        )
        translator = Translator(target_lang=target_lang) if target_lang else None

        results = []
        with Progress(console=console) as progress:
            task = progress.add_task("Processing...", total=len(files))

            for file_path in files:
                try:
                    # Transcribe
                    result = transcriber.transcribe(str(file_path), language=language)

                    # Handle auto-detect tuple return
                    if isinstance(result, tuple):
                        segments, lang_info = result
                        console.print(
                            f"  [dim]Detected: {lang_info.language} "
                            f"({lang_info.language_probability:.0%})[/]"
                        )
                    else:
                        segments = result

                    # Translate if translator is configured
                    translated = False
                    if translator:
                        segments = translator.translate_segments(segments)
                        translated = True

                    # Export
                    content = export_segments(segments, fmt=output_format)

                    # Determine output path
                    if output_dir:
                        out_path = Path(output_dir) / f"{file_path.stem}.{output_format}"
                    else:
                        suffix = f".{target_lang}" if target_lang else ""
                        out_path = file_path.with_suffix(f"{suffix}.{output_format}")

                    out_path.parent.mkdir(parents=True, exist_ok=True)
                    out_path.write_text(content, encoding="utf-8")

                    results.append(
                        PipelineResult(
                            input_path=str(file_path),
                            segments_count=len(segments),
                            output_path=str(out_path),
                            format=output_format,
                            translated=translated,
                            target_lang=target_lang,
                        )
                    )
                except Exception as e:
                    console.print(f"[red]Error processing {file_path}: {e}[/]")

                progress.advance(task)

        console.print(
            f"[bold green]✓ Batch complete: {len(results)}/{len(files)} files processed[/]"
        )
        return results
