"""AutoSub pipeline — orchestrates transcribe → align → translate → export."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from rich.console import Console
from rich.progress import (
    BarColumn,
    Progress,
    SpinnerColumn,
    TextColumn,
    TimeElapsedColumn,
)

from autosub.exporter import export_segments
from autosub.transcriber import Transcriber
from autosub.translator import Translator


@dataclass
class PipelineResult:
    """Result of a pipeline run."""

    input_path: str
    segments_count: int
    output_path: str
    format: str
    translated: bool
    target_lang: str | None = None


class Pipeline:
    """Orchestrate the full subtitle generation pipeline."""

    def __init__(
        self,
        model_size: str = "base",
        device: str = "auto",
        compute_type: str = "int8",
    ):
        self.model_size = model_size
        self.device = device
        self.compute_type = compute_type

    def run(
        self,
        input_path: str,
        language: str | None = None,
        target_lang: str | None = None,
        output_format: str = "srt",
        output_path: str | None = None,
        console: Console | None = None,
    ) -> PipelineResult:
        """Run the full pipeline: transcribe → (optional) translate → export.

        Args:
            input_path: Path to audio/video file.
            language: Source language (None for auto-detect).
            target_lang: Target language for translation (None = no translation).
            output_format: Output format — srt, vtt, txt.
            output_path: Custom output path (None = auto-generate).
            console: Rich console for progress output.

        Returns:
            PipelineResult with details of the run.
        """
        if console is None:
            console = Console()

        transcriber = Transcriber(
            model_size=self.model_size,
            device=self.device,
            compute_type=self.compute_type,
        )

        path = Path(input_path)
        if not path.exists():
            raise FileNotFoundError(f"Input file not found: {input_path}")

        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TimeElapsedColumn(),
            console=console,
        ) as progress:
            # Step 1: Transcribe
            task = progress.add_task("Transcribing audio...", total=100)
            segments = transcriber.transcribe(str(path), language=language)
            progress.update(task, completed=100)

            # Step 2: Translate (optional)
            translated = False
            if target_lang:
                task = progress.add_task(f"Translating to {target_lang}...", total=100)
                translator = Translator(target_lang=target_lang)
                segments = translator.translate_segments(segments)
                translated = True
                progress.update(task, completed=100)

        # Step 3: Export
        result_text = export_segments(segments, fmt=output_format)

        if output_path:
            out = Path(output_path)
        else:
            suffix = f".{target_lang}" if target_lang else ""
            out = path.with_suffix(f"{suffix}.{output_format}")

        out.write_text(result_text, encoding="utf-8")

        return PipelineResult(
            input_path=str(path),
            segments_count=len(segments),
            output_path=str(out),
            format=output_format,
            translated=translated,
            target_lang=target_lang,
        )
