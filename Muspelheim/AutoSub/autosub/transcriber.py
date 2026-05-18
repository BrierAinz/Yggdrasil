"""AutoSub transcription module — Whisper-based audio transcription."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass
class Segment:
    """A transcribed text segment with timing information."""

    text: str
    start: float
    end: float

    def __str__(self) -> str:
        return f"[{self.start:.2f}s → {self.end:.2f}s] {self.text}"


@dataclass
class LanguageInfo:
    """Detected language information from transcription."""

    language: str
    language_probability: float


class Transcriber:
    """Transcribe audio/video files using faster-whisper."""

    def __init__(
        self,
        model_size: str = "base",
        device: str = "auto",
        compute_type: str = "int8",
    ):
        self.model_size = model_size
        self.device = device
        self.compute_type = compute_type
        self._model = None

    def _load_model(self) -> None:
        """Lazily load the whisper model."""
        if self._model is None:
            from faster_whisper import WhisperModel

            effective_device = self.device
            if effective_device == "auto":
                effective_device = "cuda" if self._has_gpu() else "cpu"

            self._model = WhisperModel(
                self.model_size,
                device=effective_device,
                compute_type=self.compute_type,
            )

    @staticmethod
    def _has_gpu() -> bool:
        """Check if a CUDA GPU is available."""
        try:
            import torch

            return torch.cuda.is_available()
        except ImportError:
            return False

    def detect_language(self, audio_path: str) -> LanguageInfo:
        """Detect the language of an audio file without full transcription.

        Args:
            audio_path: Path to the audio/video file.

        Returns:
            LanguageInfo with detected language and confidence.

        Raises:
            FileNotFoundError: If the audio file does not exist.

        """
        path = Path(audio_path)
        if not path.exists():
            raise FileNotFoundError(f"Audio file not found: {audio_path}")

        self._load_model()
        segments_iter, info = self._model.transcribe(
            str(path),
            word_timestamps=False,
            vad_filter=True,
        )
        # Consume iterator to trigger language detection
        _ = list(segments_iter)

        return LanguageInfo(
            language=info.language,
            language_probability=info.language_probability,
        )

    def transcribe(
        self, audio_path: str, language: str | None = None
    ) -> list[Segment] | tuple[list[Segment], LanguageInfo]:
        """Transcribe an audio/video file and return timed segments.

        Args:
            audio_path: Path to the audio/video file.
            language: Language code (e.g. 'en', 'es'). None for auto-detect.

        Returns:
            If language is specified: list of Segment objects.
            If language is None: tuple of (segments, LanguageInfo).

        Raises:
            FileNotFoundError: If the audio file does not exist.

        """
        path = Path(audio_path)
        if not path.exists():
            raise FileNotFoundError(f"Audio file not found: {audio_path}")

        self._load_model()
        segments_iter, info = self._model.transcribe(
            str(path),
            language=language,
            word_timestamps=True,
            vad_filter=True,
        )
        segments = [Segment(text=s.text.strip(), start=s.start, end=s.end) for s in segments_iter]

        # If language was auto-detected, include detection info
        if language is None:
            lang_info = LanguageInfo(
                language=info.language,
                language_probability=info.language_probability,
            )
            return segments, lang_info

        return segments
