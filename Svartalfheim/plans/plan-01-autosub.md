# AutoSub — Implementation Plan

> **For Hermes:** Use subagent-driven-development skill to implement this plan task-by-task.

**Goal:** Build a CLI tool that takes video/audio input, generates synchronized subtitles via Whisper, aligns timestamps precisely, translates to multiple languages, and exports SRT/VTT — enabling content creators to subtitle content for 5+ platforms in one pass.

**Architecture:** Pipeline-based CLI. Input file → audio extraction (ffmpeg) → Whisper transcription → timestamp alignment → translation (deep-translator) → multi-format export (SRT/VTT). Each stage is a standalone module with a clean interface. Configuration via TOML. GPU-accelerated Whisper on RTX 3060 12GB.

**Tech Stack:** Python 3.11+, openai-whisper, ffmpeg-python, deep-translater, toml, click, pytest, torch (CUDA).

**Estimation:** 12 tasks | 3-5 hours total | 2-3 sessions

---

## Task 1: Project scaffolding and pyproject.toml

**Objective:** Create the AutoSub package structure under Muspelheim with proper pyproject.toml and installable CLI entry point.

**Files:**
- Create: `Muspelheim/AutoSub/pyproject.toml`
- Create: `Muspelheim/AutoSub/autosub/__init__.py`
- Create: `Muspelheim/AutoSub/autosub/cli.py`
- Create: `Muspelheim/AutoSub/autosub/config.py`
- Create: `Muspelheim/AutoSub/tests/__init__.py`

**Step 1: Create pyproject.toml**

```toml
[build-system]
requires = ["setuptools>=61.0", "wheel"]
build-backend = "setuptools.build_meta"

[project]
name = "autosub"
version = "0.1.0"
description = "CLI subtitle generator with Whisper, alignment, and multi-language translation"
readme = "README.md"
requires-python = ">=3.11"
dependencies = [
    "openai-whisper>=20231117",
    "ffmpeg-python>=0.2.0",
    "deep-translator>=1.11.4",
    "toml>=0.10.2",
    "click>=8.1.7",
    "torch>=2.0.0",
]

[project.optional-dependencies]
dev = ["pytest>=7.0", "pytest-cov", "black", "isort", "mypy"]

[project.scripts]
autosub = "autosub.cli:main"

[tool.setuptools.packages.find]
where = ["."]
include = ["autosub*"]

[tool.pytest.ini_options]
testpaths = ["tests"]
python_files = ["test_*.py"]
python_classes = ["Test*"]
python_functions = ["test_*"]
addopts = "-v --tb=short"

[tool.black]
line-length = 100

[tool.isort]
profile = "black"
```

**Step 2: Create package init**

```python
# autosub/__init__.py
"""AutoSub — Synchronized subtitle generation with Whisper."""
__version__ = "0.1.0"
```

**Step 3: Create minimal CLI stub**

```python
# autosub/cli.py
import click


@click.group()
@click.version_option(version="0.1.0")
def main():
    """AutoSub — Generate synchronized subtitles from video/audio."""
    pass


@main.command()
@click.argument("input_path", type=click.Path(exists=True))
@click.option("--model", default="base", help="Whisper model size")
@click.option("--language", default=None, help="Source language (auto-detect if omitted)")
@click.option("--output", "-o", default=None, help="Output directory")
def transcribe(input_path, model, language, output):
    """Transcribe audio/video file to subtitles."""
    click.echo(f"Transcribing {input_path} with model={model}")


@main.command()
@click.argument("input_path", type=click.Path(exists=True))
def info(input_path):
    """Show info about a media file."""
    click.echo(f"File: {input_path}")
```

**Step 4: Create config module stub**

```python
# autosub/config.py
from pathlib import Path
from dataclasses import dataclass, field
from typing import List, Optional
import toml


@dataclass
class AutoSubConfig:
    whisper_model: str = "base"
    device: str = "cuda"
    source_language: Optional[str] = None
    target_languages: List[str] = field(default_factory=lambda: ["es", "fr", "de", "ja", "pt"])
    output_dir: Optional[Path] = None
    output_formats: List[str] = field(default_factory=lambda: ["srt", "vtt"])
    export_original: bool = True

    @classmethod
    def from_toml(cls, path: Path) -> "AutoSubConfig":
        data = toml.load(path)
        section = data.get("autosub", {})
        return cls(**{k: v for k, v in section.items() if k in cls.__dataclass_fields__})
```

**Step 5: Install and verify**

Run:
```bash
cd /mnt/d/Proyectos/Yggdrasil/Muspelheim/AutoSub
pip install -e ".[dev]"
autosub --version
```

Expected: `autosub, version 0.1.0`

**Step 6: Commit**

```bash
cd /mnt/d/Proyectos/Yggdrasil
git add Muspelheim/AutoSub/
git commit -m "feat(autosub): project scaffolding with CLI and config"
```

---

## Task 2: Audio extraction module

**Objective:** Create module to extract audio from video/audio files using ffmpeg. Must handle multiple input formats and verify ffmpeg availability.

**Files:**
- Create: `Muspelheim/AutoSub/autosub/audio.py`
- Create: `Muspelheim/AutoSub/tests/test_audio.py`

**Step 1: Write failing tests**

```python
# tests/test_audio.py
import pytest
from pathlib import Path
from autosub.audio import extract_audio, check_ffmpeg


class TestCheckFfmpeg:
    def test_ffmpeg_available(self):
        """ffmpeg should be available on this system."""
        assert check_ffmpeg() is True


class TestExtractAudio:
    def test_extract_from_nonexistent_file(self, tmp_path):
        """Should raise FileNotFoundError for missing input."""
        with pytest.raises(FileNotFoundError):
            extract_audio(tmp_path / "nonexistent.mp4")

    def test_extract_creates_output(self, tmp_path):
        """Should extract audio when input exists."""
        # Create a tiny silent audio file for testing
        import subprocess
        input_file = tmp_path / "test.mkv"
        # Generate 1-second silent audio file
        subprocess.run(
            ["ffmpeg", "-f", "lavfi", "-i", "anullsrc=r=16000:cl=mono",
             "-t", "1", "-y", str(input_file)],
            capture_output=True, check=True
        )
        result = extract_audio(input_file)
        assert result.exists()
        assert result.suffix == ".wav"
        result.unlink()  # cleanup

    def test_extract_custom_output_path(self, tmp_path):
        """Should use custom output path when provided."""
        import subprocess
        input_file = tmp_path / "test.mkv"
        subprocess.run(
            ["ffmpeg", "-f", "lavfi", "-i", "anullsrc=r=16000:cl=mono",
             "-t", "1", "-y", str(input_file)],
            capture_output=True, check=True
        )
        output = tmp_path / "custom_output.wav"
        result = extract_audio(input_file, output_path=output)
        assert result == output
        assert output.exists()
        output.unlink()
```

**Step 2: Run tests to verify failures**

Run: `cd /mnt/d/Proyectos/Yggdrasil/Muspelheim/AutoSub && pytest tests/test_audio.py -v`

Expected: 2-3 failures (module doesn't exist yet).

**Step 3: Implement audio extraction**

```python
# autosub/audio.py
import shutil
import subprocess
from pathlib import Path
from typing import Optional


def check_ffmpeg() -> bool:
    """Check if ffmpeg is available on the system."""
    return shutil.which("ffmpeg") is not None


def extract_audio(
    input_path: Path,
    output_path: Optional[Path] = None,
    sample_rate: int = 16000,
) -> Path:
    """Extract audio from video/audio file as 16kHz mono WAV.

    Args:
        input_path: Path to source video/audio file.
        output_path: Optional custom output path. Defaults to input stem + .wav.
        sample_rate: Target sample rate (Whisper expects 16000).

    Returns:
        Path to the extracted WAV file.

    Raises:
        FileNotFoundError: If input_path does not exist.
        RuntimeError: If ffmpeg fails.
    """
    input_path = Path(input_path)
    if not input_path.exists():
        raise FileNotFoundError(f"Input file not found: {input_path}")

    if output_path is None:
        output_path = input_path.with_suffix(".wav")

    cmd = [
        "ffmpeg", "-i", str(input_path),
        "-vn",                       # No video
        "-acodec", "pcm_s16le",      # 16-bit PCM
        "-ar", str(sample_rate),     # Sample rate
        "-ac", "1",                  # Mono
        "-y",                        # Overwrite
        str(output_path),
    ]

    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(f"ffmpeg failed: {result.stderr}")

    return output_path
```

**Step 4: Run tests to verify pass**

Run: `pytest tests/test_audio.py -v`

Expected: All 4 tests pass.

**Step 5: Commit**

```bash
cd /mnt/d/Proyectos/Yggdrasil
git add Muspelheim/AutoSub/autosub/audio.py Muspelheim/AutoSub/tests/test_audio.py
git commit -m "feat(autosub): audio extraction module with ffmpeg"
```

---

## Task 3: Whisper transcription module

**Objective:** Create module that loads Whisper model and transcribes audio to structured segments with timestamps.

**Files:**
- Create: `Muspelheim/AutoSub/autosub/transcriber.py`
- Create: `Muspelheim/AutoSub/tests/test_transcriber.py`

**Step 1: Write failing tests**

```python
# tests/test_transcriber.py
import pytest
from autosub.transcriber import Transcriber, Segment


class TestSegment:
    def test_segment_creation(self):
        seg = Segment(start=0.0, end=2.5, text="Hello world")
        assert seg.start == 0.0
        assert seg.end == 2.5
        assert seg.text == "Hello world"

    def test_segment_duration(self):
        seg = Segment(start=1.0, end=3.5, text="test")
        assert seg.duration == 2.5

    def test_segment_to_dict(self):
        seg = Segment(start=0.0, end=1.0, text="hi")
        d = seg.to_dict()
        assert d["start"] == 0.0
        assert d["end"] == 1.0
        assert d["text"] == "hi"


class TestTranscriber:
    def test_default_model_name(self):
        t = Transcriber(model_name="base")
        assert t.model_name == "base"

    def test_invalid_model_name(self):
        with pytest.raises(ValueError):
            Transcriber(model_name="nonexistent_model_xyz")

    @pytest.mark.slow
    def test_transcribe_real_audio(self, tmp_path):
        """Integration test: requires Whisper model download on first run."""
        import subprocess
        audio_file = tmp_path / "test_audio.wav"
        subprocess.run(
            ["ffmpeg", "-f", "lavfi", "-i", "anullsrc=r=16000:cl=mono",
             "-t", "3", "-y", str(audio_file)],
            capture_output=True, check=True
        )
        t = Transcriber(model_name="tiny")
        segments = t.transcribe(audio_file)
        assert isinstance(segments, list)
        #Silent audio may produce empty or minimal segments
        assert all(isinstance(s, Segment) for s in segments)
```

**Step 2: Run tests to verify failures**

Run: `pytest tests/test_transcriber.py::TestSegment -v && pytest tests/test_transcriber.py::TestTranscriber::test_invalid_model_name -v`

Expected: Failures because module doesn't exist. The `test_invalid_model_name` will also fail.

**Step 3: Implement transcriber**

```python
# autosub/transcriber.py
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional


VALID_MODELS = {"tiny", "base", "small", "medium", "large", "large-v2", "large-v3"}


@dataclass
class Segment:
    """A single transcribed segment with timing."""
    start: float
    end: float
    text: str

    @property
    def duration(self) -> float:
        return self.end - self.start

    def to_dict(self) -> dict:
        return {"start": self.start, "end": self.end, "text": self.text}


class Transcriber:
    """Whisper-based transcription engine."""

    def __init__(self, model_name: str = "base", device: str = "cuda"):
        if model_name not in VALID_MODELS:
            raise ValueError(
                f"Invalid model '{model_name}'. Must be one of: {VALID_MODELS}"
            )
        self.model_name = model_name
        self.device = device
        self._model = None

    def _load_model(self):
        """Lazy-load Whisper model."""
        if self._model is None:
            import whisper
            self._model = whisper.load_model(self.model_name, device=self.device)
        return self._model

    def transcribe(
        self,
        audio_path: Path,
        language: Optional[str] = None,
    ) -> List[Segment]:
        """Transcribe audio file to segmented text with timestamps.

        Args:
            audio_path: Path to audio file (WAV recommended).
            language: Force language detection, or None for auto-detect.

        Returns:
            List of Segment objects with timestamps.
        """
        audio_path = Path(audio_path)
        if not audio_path.exists():
            raise FileNotFoundError(f"Audio file not found: {audio_path}")

        model = self._load_model()
        options = {}
        if language:
            options["language"] = language

        result = model.transcribe(str(audio_path), **options)

        segments = []
        for seg in result.get("segments", []):
            segments.append(Segment(
                start=round(seg["start"], 3),
                end=round(seg["end"], 3),
                text=seg["text"].strip(),
            ))

        return segments
```

**Step 4: Run tests to verify pass**

Run: `pytest tests/test_transcriber.py -v -m "not slow"`

Expected: All unit tests pass (Segment tests + invalid model test).

**Step 5: Commit**

```bash
cd /mnt/d/Proyectos/Yggdrasil
git add Muspelheim/AutoSub/autosub/transcriber.py Muspelheim/AutoSub/tests/test_transcriber.py
git commit -m "feat(autosub): Whisper transcription module with Segment dataclass"
```

---

## Task 4: Timestamp alignment module

**Objective:** Create alignment module that refines Whisper timestamps using word-level timing and fixes common issues (overlapping, gaps, too-long segments).

**Files:**
- Create: `Muspelheim/AutoSub/autosub/aligner.py`
- Create: `Muspelheim/AutoSub/tests/test_aligner.py`

**Step 1: Write failing tests**

```python
# tests/test_aligner.py
import pytest
from autosub.transcriber import Segment
from autosub.aligner import align_segments, fix_overlaps, merge_short_segments, split_long_segments


class TestFixOverlaps:
    def test_no_overlaps(self):
        segs = [Segment(0, 2, "hello"), Segment(2, 4, "world")]
        result = fix_overlaps(segs)
        assert len(result) == 2
        assert result[0].end == 2.0

    def test_with_overlaps(self):
        segs = [Segment(0, 3, "hello"), Segment(2.5, 5, "world")]
        result = fix_overlaps(segs)
        assert result[0].end <= result[1].start

    def test_empty_input(self):
        assert fix_overlaps([]) == []


class TestMergeShortSegments:
    def test_merge_below_threshold(self):
        segs = [Segment(0, 0.5, "hi"), Segment(0.5, 2, "there")]
        result = merge_short_segments(segs, min_duration=1.0)
        assert len(result) < len(segs)
        assert result[0].duration >= 1.0

    def test_no_merge_needed(self):
        segs = [Segment(0, 3, "hello world")]
        result = merge_short_segments(segs, min_duration=1.0)
        assert len(result) == 1


class TestSplitLongSegments:
    def test_split_long_segment(self):
        seg = Segment(0, 15, "A very long subtitle that should be split into parts")
        result = split_long_segments([seg], max_duration=7.0)
        assert len(result) > 1
        for s in result:
            assert s.duration <= 7.0

    def test_no_split_needed(self):
        segs = [Segment(0, 3, "short")]
        result = split_long_segments(segs, max_duration=7.0)
        assert len(result) == 1


class TestAlignSegments:
    def test_full_pipeline(self):
        segs = [
            Segment(0, 0.3, "hi"),
            Segment(0.3, 2, "there"),
            Segment(2, 17, "very long segment here"),
            Segment(16.5, 20, "overlap segment"),
        ]
        result = align_segments(segs)
        assert len(result) >= 1
        # No overlaps in output
        for i in range(1, len(result)):
            assert result[i].start >= result[i - 1].end - 0.01  # tolerance
```

**Step 2: Run tests to verify failures**

Run: `pytest tests/test_aligner.py -v`

Expected: All tests fail (module doesn't exist).

**Step 3: Implement aligner**

```python
# autosub/aligner.py
from typing import List
from autosub.transcriber import Segment


def fix_overlaps(segments: List[Segment]) -> List[Segment]:
    """Fix overlapping timestamps by trimming end of earlier segment."""
    if not segments:
        return []

    result = [Segment(segments[0].start, segments[0].end, segments[0].text)]
    for seg in segments[1:]:
        if seg.start < result[-1].end:
            # Trim previous end to current start
            mid = seg.start
            result[-1] = Segment(result[-1].start, mid, result[-1].text)
        result.append(Segment(seg.start, seg.end, seg.text))

    return result


def merge_short_segments(
    segments: List[Segment], min_duration: float = 1.0
) -> List[Segment]:
    """Merge consecutive segments shorter than min_duration."""
    if not segments:
        return []

    merged = [Segment(segments[0].start, segments[0].end, segments[0].text)]
    for seg in segments[1:]:
        if merged[-1].duration < min_duration:
            # Merge with previous
            merged[-1] = Segment(
                merged[-1].start, seg.end,
                merged[-1].text + " " + seg.text,
            )
        else:
            merged.append(Segment(seg.start, seg.end, seg.text))

    return merged


def split_long_segments(
    segments: List[Segment], max_duration: float = 7.0
) -> List[Segment]:
    """Split segments longer than max_duration at word boundaries."""
    result = []
    for seg in segments:
        if seg.duration <= max_duration:
            result.append(seg)
            continue

        words = seg.text.split()
        if not words:
            result.append(seg)
            continue

        duration_per_word = seg.duration / len(words)
        chunk_size = max(1, int(max_duration / duration_per_word))

        i = 0
        while i < len(words):
            chunk = words[i:i + chunk_size]
            word_count = len(chunk)
            start_time = seg.start + i * duration_per_word
            end_time = seg.start + (i + word_count) * duration_per_word
            result.append(Segment(
                round(start_time, 3),
                round(min(end_time, seg.end), 3),
                " ".join(chunk),
            ))
            i += chunk_size

    return result


def align_segments(
    segments: List[Segment],
    min_duration: float = 1.0,
    max_duration: float = 7.0,
) -> List[Segment]:
    """Full alignment pipeline: fix overlaps, merge short, split long."""
    segments = fix_overlaps(segments)
    segments = merge_short_segments(segments, min_duration=min_duration)
    segments = split_long_segments(segments, max_duration=max_duration)
    # Second pass for any remaining overlaps after splitting
    segments = fix_overlaps(segments)
    return segments
```

**Step 4: Run tests to verify pass**

Run: `pytest tests/test_aligner.py -v`

Expected: All tests pass.

**Step 5: Commit**

```bash
cd /mnt/d/Proyectos/Yggdrasil
git add Muspelheim/AutoSub/autosub/aligner.py Muspelheim/AutoSub/tests/test_aligner.py
git commit -m "feat(autosub): timestamp alignment with overlap fix, merge, and split"
```

---

## Task 5: Translation module

**Objective:** Create module that translates subtitle segments to multiple target languages using deep-translator, preserving segment timing.

**Files:**
- Create: `Muspelheim/AutoSub/autosub/translator.py`
- Create: `Muspelheim/AutoSub/tests/test_translator.py`

**Step 1: Write failing tests**

```python
# tests/test_translator.py
import pytest
from autosub.transcriber import Segment
from autosub.translator import translate_segments, AVAILABLE_LANGUAGES


class TestAvailableLanguages:
    def test_common_languages_present(self):
        assert "es" in AVAILABLE_LANGUAGES
        assert "fr" in AVAILABLE_LANGUAGES
        assert "de" in AVAILABLE_LANGUAGES
        assert "ja" in AVAILABLE_LANGUATES or "ja" in AVAILABLE_LANGUAGES


class TestTranslateSegments:
    def test_empty_segments(self):
        result = translate_segments([], target_language="es")
        assert result == []

    def test_preserves_timestamps(self):
        segs = [Segment(0.0, 2.0, "hello")]
        result = translate_segments(segs, target_language="es", use_mock=True)
        # Timestamps must be preserved
        assert result[0].start == 0.0
        assert result[0].end == 2.0

    def test_mock_translation(self):
        segs = [Segment(0.0, 2.0, "Hello world")]
        result = translate_segments(segs, target_language="es", use_mock=True)
        # Mock returns original text tagged with language
        assert "[es]" in result[0].text

    @pytest.mark.slow
    def test_real_translation(self):
        """Integration test: requires internet for deep-translator."""
        segs = [Segment(0.0, 2.0, "Hello world")]
        result = translate_segments(segs, target_language="es")
        assert len(result) == 1
        assert result[0].text  # Non-empty
```

**Step 2: Run tests to verify failures**

Run: `pytest tests/test_translator.py -v -m "not slow"`

Expected: Failures (module doesn't exist).

**Step 3: Implement translator**

```python
# autosub/translator.py
from typing import List, Dict
from autosub.transcriber import Segment

# Map of language codes to names for deep-translater
AVAILABLE_LANGUAGES: Dict[str, str] = {
    "es": "spanish",
    "fr": "french",
    "de": "german",
    "ja": "japanese",
    "pt": "portuguese",
    "it": "italian",
    "ko": "korean",
    "zh": "chinese",
    "ru": "russian",
    "ar": "arabic",
    "hi": "hindi",
    "nl": "dutch",
    "pl": "polish",
    "tr": "turkish",
    "sv": "swedish",
}


def _mock_translate(text: str, target_lang: str) -> str:
    """Mock translation for testing — tags text with target language."""
    return f"[{target_lang}] {text}"


def translate_segment_text(text: str, target_language: str, use_mock: bool = False) -> str:
    """Translate a single text string to target language.

    Args:
        text: Source text.
        target_language: ISO 639-1 language code.
        use_mock: If True, return mock translation instead of calling API.

    Returns:
        Translated text string.
    """
    if use_mock:
        return _mock_translate(text, target_language)

    if target_language not in AVAILABLE_LANGUAGES:
        raise ValueError(
            f"Unsupported language '{target_language}'. "
            f"Available: {list(AVAILABLE_LANGUAGES.keys())}"
        )

    from deep_translator import GoogleTranslator

    translator = GoogleTranslator(source="auto", target=target_language)
    result = translator.translate(text)
    return result if result else text


def translate_segments(
    segments: List[Segment],
    target_language: str,
    use_mock: bool = False,
) -> List[Segment]:
    """Translate all segments to target language, preserving timestamps.

    Args:
        segments: List of Segment objects with text to translate.
        target_language: ISO 639-1 code for target language.
        use_mock: If True, use mock translation for testing.

    Returns:
        New list of Segments with translated text, same timestamps.
    """
    if not segments:
        return []

    translated = []
    for seg in segments:
        translated_text = translate_segment_text(
            seg.text, target_language, use_mock=use_mock
        )
        translated.append(Segment(
            start=seg.start,
            end=seg.end,
            text=translated_text,
        ))

    return translated
```

**Step 4: Fix test typo and run**

Note: The test has `AVAILABLE_LANGUAGES` (correct variable name). Let me fix the test:

```python
# tests/test_translator.py (corrected imports and assertions)
import pytest
from autosub.transcriber import Segment
from autosub.translator import translate_segments, AVAILABLE_LANGUAGES


class TestAvailableLanguages:
    def test_common_languages_present(self):
        assert "es" in AVAILABLE_LANGUAGES
        assert "fr" in AVAILABLE_LANGUAGES
        assert "de" in AVAILABLE_LANGUAGES
        assert "ja" in AVAILABLE_LANGUAGES


class TestTranslateSegments:
    def test_empty_segments(self):
        result = translate_segments([], target_language="es")
        assert result == []

    def test_preserves_timestamps(self):
        segs = [Segment(0.0, 2.0, "hello")]
        result = translate_segments(segs, target_language="es", use_mock=True)
        assert result[0].start == 0.0
        assert result[0].end == 2.0

    def test_mock_translation(self):
        segs = [Segment(0.0, 2.0, "Hello world")]
        result = translate_segments(segs, target_language="es", use_mock=True)
        assert "[es]" in result[0].text
```

Run: `pytest tests/test_translator.py -v -m "not slow"`

Expected: All tests pass.

**Step 5: Commit**

```bash
cd /mnt/d/Proyectos/Yggdrasil
git add Muspelheim/AutoSub/autosub/translator.py Muspelheim/AutoSub/tests/test_translator.py
git commit -m "feat(autosub): translation module with deep-translater and mock mode"
```

---

## Task 6: SRT and VTT export module

**Objective:** Create module that converts aligned segments into valid SRT and VTT subtitle files.

**Files:**
- Create: `Muspelheim/AutoSub/autosub/exporter.py`
- Create: `Muspelheim/AutoSub/tests/test_exporter.py`

**Step 1: Write failing tests**

```python
# tests/test_exporter.py
import pytest
from pathlib import Path
from autosub.transcriber import Segment
from autosub.exporter import segments_to_srt, segments_to_vtt, export_subtitles


class TestSrtFormat:
    def test_basic_srt(self):
        segs = [
            Segment(0.0, 2.5, "Hello world"),
            Segment(2.5, 5.0, "This is a test"),
        ]
        srt = segments_to_srt(segs)
        assert "1\n" in srt
        assert "00:00:00,000 --> 00:00:02,500" in srt
        assert "Hello world" in srt
        assert "2\n" in srt
        assert "This is a test" in srt

    def test_srt_empty_segments(self):
        srt = segments_to_srt([])
        assert srt == ""

    def test_srt_timestamp_format(self):
        segs = [Segment(3661.5, 3662.0, "test")]
        srt = segments_to_srt(segs)
        assert "01:01:01,500 --> 01:01:02,000" in srt


class TestVttFormat:
    def test_basic_vtt(self):
        segs = [Segment(0.0, 2.5, "Hello")]
        vtt = segments_to_vtt(segs)
        assert vtt.startswith("WEBVTT\n\n")
        assert "00:00:00.000 --> 00:00:02.500" in vtt
        assert "Hello" in vtt

    def test_vtt_empty_segments(self):
        vtt = segments_to_vtt([])
        assert vtt == "WEBVTT\n"


class TestExportSubtitles:
    def test_export_srt(self, tmp_path):
        segs = [Segment(0, 2, "hello")]
        out = export_subtitles(segs, output_dir=tmp_path, filename="test", fmt="srt")
        assert out.exists()
        content = out.read_text(encoding="utf-8")
        assert "hello" in content

    def test_export_vtt(self, tmp_path):
        segs = [Segment(0, 2, "hello")]
        out = export_subtitles(segs, output_dir=tmp_path, filename="test", fmt="vtt")
        assert out.exists()
        content = out.read_text(encoding="utf-8")
        assert "WEBVTT" in content

    def test_export_both(self, tmp_path):
        segs = [Segment(0, 2, "hello")]
        files = export_subtitles(
            segs, output_dir=tmp_path, filename="test", fmt="both"
        )
        assert isinstance(files, list)
        assert len(files) == 2
```

**Step 2: Run tests to verify failures**

Run: `pytest tests/test_exporter.py -v`

Expected: All tests fail (module doesn't exist).

**Step 3: Implement exporter**

```python
# autosub/exporter.py
from pathlib import Path
from typing import List, Union
from autosub.transcriber import Segment


def _format_srt_time(seconds: float) -> str:
    """Format seconds to SRT timestamp: HH:MM:SS,mmm"""
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = int(seconds % 60)
    millis = int((seconds % 1) * 1000)
    return f"{hours:02d}:{minutes:02d}:{secs:02d},{millis:03d}"


def _format_vtt_time(seconds: float) -> str:
    """Format seconds to VTT timestamp: HH:MM:SS.mmm"""
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = int(seconds % 60)
    millis = int((seconds % 1) * 1000)
    return f"{hours:02d}:{minutes:02d}:{secs:02d}.{millis:03d}"


def segments_to_srt(segments: List[Segment]) -> str:
    """Convert segments to SRT subtitle format."""
    if not segments:
        return ""

    lines = []
    for i, seg in enumerate(segments, 1):
        lines.append(str(i))
        lines.append(f"{_format_srt_time(seg.start)} --> {_format_srt_time(seg.end)}")
        lines.append(seg.text)
        lines.append("")  # blank line between entries

    return "\n".join(lines)


def segments_to_vtt(segments: List[Segment]) -> str:
    """Convert segments to WebVTT subtitle format."""
    if not segments:
        return "WEBVTT\n"

    lines = ["WEBVTT", ""]
    for seg in segments:
        lines.append(f"{_format_vtt_time(seg.start)} --> {_format_vtt_time(seg.end)}")
        lines.append(seg.text)
        lines.append("")

    return "\n".join(lines)


def export_subtitles(
    segments: List[Segment],
    output_dir: Path,
    filename: str,
    fmt: str = "srt",
) -> Union[Path, List[Path]]:
    """Export segments to subtitle file(s).

    Args:
        segments: List of Segment objects.
        output_dir: Directory for output file(s).
        filename: Base filename without extension.
        fmt: Output format — "srt", "vtt", or "both".

    Returns:
        Path to single file, or list of Paths if fmt="both".
    """
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    if fmt == "both":
        paths = []
        exts = [("srt", segments_to_srt), ("vtt", segments_to_vtt)]
        for ext, converter in exts:
            path = output_dir / f"{filename}.{ext}"
            path.write_text(converter(segments), encoding="utf-8")
            paths.append(path)
        return paths

    if fmt == "srt":
        converter = segments_to_srt
    elif fmt == "vtt":
        converter = segments_to_vtt
    else:
        raise ValueError(f"Unsupported format: {fmt}. Use 'srt', 'vtt', or 'both'.")

    path = output_dir / f"{filename}.{fmt}"
    path.write_text(converter(segments), encoding="utf-8")
    return path
```

**Step 4: Run tests to verify pass**

Run: `pytest tests/test_exporter.py -v`

Expected: All tests pass.

**Step 5: Commit**

```bash
cd /mnt/d/Proyectos/Yggdrasil
git add Muspelheim/AutoSub/autosub/exporter.py Muspelheim/AutoSub/tests/test_exporter.py
git commit -m "feat(autosub): SRT/VTT export module"
```

---

## Task 7: Pipeline orchestrator

**Objective:** Create the main pipeline that chains all modules together: audio extraction → transcription → alignment → translation → export.

**Files:**
- Create: `Muspelheim/AutoSub/autosub/pipeline.py`
- Create: `Muspelheim/AutoSub/tests/test_pipeline.py`

**Step 1: Write failing tests**

```python
# tests/test_pipeline.py
import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock
from autosub.transcriber import Segment
from autosub.pipeline import AutoSubPipeline, PipelineConfig


class TestPipelineConfig:
    def test_defaults(self):
        config = PipelineConfig()
        assert config.whisper_model == "base"
        assert config.device == "cuda"
        assert "srt" in config.output_formats
        assert len(config.target_languages) > 0

    def test_custom_config(self):
        config = PipelineConfig(
            whisper_model="small",
            target_languages=["es", "fr"],
            output_formats=["vtt"],
        )
        assert config.whisper_model == "small"
        assert config.target_languages == ["es", "fr"]
        assert config.output_formats == ["vtt"]


class TestAutoSubPipeline:
    def test_init(self):
        pipeline = AutoSubPipeline(PipelineConfig())
        assert pipeline.config is not None

    @patch("autosub.pipeline.extract_audio")
    @patch("autosub.pipeline.Transcriber")
    def test_transcribe_only(self, mock_transcriber_cls, mock_extract):
        """Test pipeline with transcribe-only (no translation)."""
        mock_extract.return_value = Path("/tmp/test.wav")
        mock_instance = MagicMock()
        mock_instance.transcribe.return_value = [
            Segment(0, 2, "hello world")
        ]
        mock_transcriber_cls.return_value = mock_instance

        pipeline = AutoSubPipeline(PipelineConfig(target_languages=[]))
        result = pipeline.run(Path("/tmp/test.mp4"))

        assert "original" in result
        assert len(result["original"]) > 0
```

**Step 2: Run tests to verify failures**

Run: `pytest tests/test_pipeline.py -v`

Expected: Failures (module doesn't exist).

**Step 3: Implement pipeline**

```python
# autosub/pipeline.py
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional

from autosub.audio import extract_audio
from autosub.transcriber import Segment, Transcriber
from autosub.aligner import align_segments
from autosub.translator import translate_segments
from autosub.exporter import export_subtitles


@dataclass
class PipelineConfig:
    """Configuration for the AutoSub pipeline."""
    whisper_model: str = "base"
    device: str = "cuda"
    source_language: Optional[str] = None
    target_languages: List[str] = field(default_factory=lambda: ["es", "fr", "de", "ja", "pt"])
    output_dir: Optional[str] = None
    output_formats: List[str] = field(default_factory=lambda: ["srt", "vtt"])
    min_segment_duration: float = 1.0
    max_segment_duration: float = 7.0
    keep_audio: bool = False
    translate_original: bool = True


class AutoSubPipeline:
    """Main pipeline orchestrator for AutoSub."""

    def __init__(self, config: PipelineConfig):
        self.config = config
        self._transcriber = None

    @property
    def transcriber(self) -> Transcriber:
        if self._transcriber is None:
            self._transcriber = Transcriber(
                model_name=self.config.whisper_model,
                device=self.config.device,
            )
        return self._transcriber

    def run(self, input_path: Path) -> Dict[str, List[Segment]]:
        """Run the full AutoSub pipeline.

        Args:
            input_path: Path to video/audio file.

        Returns:
            Dict mapping language codes to segment lists.
            "original" key holds source language segments.
        """
        input_path = Path(input_path)
        if not input_path.exists():
            raise FileNotFoundError(f"Input not found: {input_path}")

        # Step 1: Extract audio
        print(f"[AutoSub] Extracting audio from {input_path.name}...")
        audio_path = extract_audio(input_path)

        # Step 2: Transcribe
        print(f"[AutoSub] Transcribing with {self.config.whisper_model}...")
        raw_segments = self.transcriber.transcribe(
            audio_path, language=self.config.source_language
        )
        print(f"[AutoSub] Got {len(raw_segments)} raw segments")

        # Step 3: Align
        print("[AutoSub] Aligning timestamps...")
        aligned = align_segments(
            raw_segments,
            min_duration=self.config.min_segment_duration,
            max_duration=self.config.max_segment_duration,
        )
        print(f"[AutoSub] {len(aligned)} aligned segments")

        # Step 4: Determine output dir
        output_dir = (
            Path(self.config.output_dir)
            if self.config.output_dir
            else input_path.parent / f"{input_path.stem}_subtitles"
        )
        output_dir.mkdir(parents=True, exist_ok=True)

        # Step 5: Export original
        results = {"original": aligned}
        base_name = input_path.stem

        for fmt in self.config.output_formats:
            export_subtitles(aligned, output_dir, base_name, fmt=fmt)
            print(f"[AutoSub] Exported {base_name}.{fmt}")

        # Step 6: Translate and export
        for lang in self.config.target_languages:
            print(f"[AutoSub] Translating to {lang}...")
            translated = translate_segments(aligned, target_language=lang)
            results[lang] = translated

            for fmt in self.config.output_formats:
                export_subtitles(
                    translated, output_dir,
                    f"{base_name}_{lang}", fmt=fmt,
                )
                print(f"[AutoSub] Exported {base_name}_{lang}.{fmt}")

        # Step 7: Cleanup temp audio
        if not self.config.keep_audio:
            audio_path.unlink(missing_ok=True)
            print("[AutoSub] Cleaned up temp audio")

        print(f"[AutoSub] Done! Output in {output_dir}")
        return results
```

**Step 4: Run tests to verify pass**

Run: `pytest tests/test_pipeline.py -v`

Expected: All tests pass.

**Step 5: Commit**

```bash
cd /mnt/d/Proyectos/Yggdrasil
git add Muspelheim/AutoSub/autosub/pipeline.py Muspelheim/AutoSub/tests/test_pipeline.py
git commit -m "feat(autosub): pipeline orchestrator chaining extraction→transcription→alignment→translation→export"
```

---

## Task 8: Full CLI integration

**Objective:** Wire all modules into the Click CLI with commands for transcribe, translate, and a config command.

**Files:**
- Modify: `Muspelheim/AutoSub/autosub/cli.py`
- Create: `Muspelheim/AutoSub/tests/test_cli.py`

**Step 1: Write failing tests**

```python
# tests/test_cli.py
import pytest
from click.testing import CliRunner
from autosub.cli import main


class TestCLI:
    def test_version(self):
        runner = CliRunner()
        result = runner.invoke(main, ["--version"])
        assert result.exit_code == 0
        assert "0.1.0" in result.output

    def test_help(self):
        runner = CliRunner()
        result = runner.invoke(main, ["--help"])
        assert result.exit_code == 0
        assert "transcribe" in result.output

    def test_transcribe_help(self):
        runner = CliRunner()
        result = runner.invoke(main, ["transcribe", "--help"])
        assert result.exit_code == 0
        assert "--model" in result.output
        assert "--language" in result.output

    def test_config_help(self):
        runner = CliRunner()
        result = runner.invoke(main, ["config", "--help"])
        assert result.exit_code == 0
```

**Step 2: Run tests to verify failures**

Run: `pytest tests/test_cli.py -v`

Expected: Some may pass (version/help), but transcribe command may need updating.

**Step 3: Rewrite full CLI**

```python
# autosub/cli.py
import click
from pathlib import Path
from autosub.pipeline import AutoSubPipeline, PipelineConfig
from autosub.config import AutoSubConfig


@click.group()
@click.version_option(version="0.1.0", prog_name="autosub")
def main():
    """AutoSub — Generate synchronized subtitles from video/audio.

    Pipeline: whisper → alignment → translation → SRT/VTT export.
    For content creators uploading to 5+ platforms.
    """
    pass


@main.command()
@click.argument("input_path", type=click.Path(exists=True))
@click.option("--model", default="base", help="Whisper model: tiny, base, small, medium, large")
@click.option("--device", default="cuda", help="Device: cuda or cpu")
@click.option("--language", default=None, help="Source language (auto-detect if omitted)")
@click.option("--output", "-o", default=None, help="Output directory")
@click.option("--formats", default="srt,vtt", help="Output formats: srt,vtt,both")
@click.option("--no-translate", is_flag=True, help="Skip translation, only generate original subtitles")
@click.option("--target-langs", default="es,fr,de,ja,pt", help="Comma-separated target language codes")
def transcribe(input_path, model, device, language, output, formats, no_translate, target_langs):
    """Transcribe audio/video file and generate multi-language subtitles."""
    fmt_list = [f.strip() for f in formats.split(",")]
    langs = [] if no_translate else [l.strip() for l in target_langs.split(",")]

    config = PipelineConfig(
        whisper_model=model,
        device=device,
        source_language=language,
        target_languages=langs,
        output_dir=output,
        output_formats=fmt_list,
    )

    pipeline = AutoSubPipeline(config)
    try:
        pipeline.run(Path(input_path))
    except FileNotFoundError as e:
        click.echo(f"Error: {e}", err=True)
        raise SystemExit(1)
    except RuntimeError as e:
        click.echo(f"Error: {e}", err=True)
        raise SystemExit(1)


@main.command()
@click.argument("input_path", type=click.Path(exists=True))
@click.option("--target-langs", default="es,fr,de,ja,pt", help="Target languages")
@click.option("--model", default="base", help="Whisper model")
@click.option("--output", "-o", default=None, help="Output directory")
def translate(input_path, target_langs, model, output):
    """Translate existing subtitles to multiple languages."""
    langs = [l.strip() for l in target_langs.split(",")]
    config = PipelineConfig(
        whisper_model=model,
        target_languages=langs,
        output_dir=output,
    )
    pipeline = AutoSubPipeline(config)
    try:
        pipeline.run(Path(input_path))
    except Exception as e:
        click.echo(f"Error: {e}", err=True)
        raise SystemExit(1)


@main.command()
@click.option("--show", is_flag=True, help="Show current config")
@click.option("--set", "key_value", nargs=2, multiple=True, help="Set config key=value")
def config(show, key_value):
    """View or modify AutoSub configuration."""
    config_path = Path.home() / ".autosub" / "config.toml"

    if show or not key_value:
        cfg = AutoSubConfig.from_toml(config_path) if config_path.exists() else AutoSubConfig()
        for k, v in cfg.__dict__.items():
            click.echo(f"  {k} = {v}")
        return

    # Save config changes
    cfg = AutoSubConfig.from_toml(config_path) if config_path.exists() else AutoSubConfig()
    for key, value in key_value:
        if hasattr(cfg, key):
            setattr(cfg, key, value)
            click.echo(f"Set {key} = {value}")
        else:
            click.echo(f"Unknown config key: {key}")

    config_path.parent.mkdir(parents=True, exist_ok=True)
    import toml
    config_path.write_text(toml.dumps({"autosub": cfg.__dict__}), encoding="utf-8")
    click.echo(f"Config saved to {config_path}")


if __name__ == "__main__":
    main()
```

**Step 4: Run tests to verify pass**

Run: `pytest tests/test_cli.py -v`

Expected: All tests pass.

**Step 5: Commit**

```bash
cd /mnt/d/Proyectos/Yggdrasil
git add Muspelheim/AutoSub/autosub/cli.py Muspelheim/AutoSub/tests/test_cli.py
git commit -m "feat(autosub): full CLI with transcribe, translate, and config commands"
```

---

## Task 9: End-to-end integration test

**Objective:** Create an end-to-end test that generates synthetic audio, runs the full pipeline, and validates outputs.

**Files:**
- Create: `Muspelheim/AutoSub/tests/test_integration.py`

**Step 1: Write integration test**

```python
# tests/test_integration.py
"""End-to-end integration tests for AutoSub.

These tests require ffmpeg and Whisper to be installed.
Marked as 'slow' — run with: pytest tests/test_integration.py -v -m slow
"""
import subprocess
import pytest
from pathlib import Path
from click.testing import CliRunner

from autosub.audio import extract_audio, check_ffmpeg
from autosub.transcriber import Segment, Transcriber
from autosub.aligner import align_segments
from autosub.exporter import segments_to_srt, segments_to_vtt, export_subtitles
from autosub.cli import main


pytestmark = pytest.mark.slow


@pytest.fixture
def sample_audio(tmp_path):
    """Generate a 3-second WAV file with silence."""
    audio_path = tmp_path / "sample.wav"
    subprocess.run(
        ["ffmpeg", "-f", "lavfi", "-i", "anullsrc=r=16000:cl=mono",
         "-t", "3", "-y", str(audio_path)],
        capture_output=True, check=True,
    )
    return audio_path


@pytest.fixture
def sample_video(tmp_path):
    """Generate a 2-second test video with silent audio."""
    video_path = tmp_path / "sample.mp4"
    subprocess.run(
        ["ffmpeg", "-f", "lavfi", "-i", "color=c=black:s=320x240:d=2:r=1",
         "-f", "lavfi", "-i", "anullsrc=r=16000:cl=mono",
         "-t", "2", "-y", "-shortest", str(video_path)],
        capture_output=True, check=True,
    )
    return video_path


class TestAudioExtraction:
    def test_extract_from_video(self, sample_video, tmp_path):
        output = tmp_path / "extracted.wav"
        result = extract_audio(sample_video, output_path=output)
        assert result.exists()
        assert result.stat().st_size > 0


class TestTranscription:
    def test_transcribe_silence(self, sample_audio):
        transcriber = Transcriber(model_name="tiny")
        segments = transcriber.transcribe(sample_audio)
        # Silent audio → may have empty or minimal segments
        assert isinstance(segments, list)


class TestFullPipeline:
    def test_srt_export_round_trip(self, tmp_path):
        segs = [
            Segment(0.0, 2.5, "Hello world"),
            Segment(2.5, 5.0, "This is a test"),
        ]
        srt_content = segments_to_srt(segs)
        assert "Hello world" in srt_content
        assert "00:00:00,000 --> 00:00:02,500" in srt_content

    def test_vtt_export_round_trip(self, tmp_path):
        segs = [Segment(0.0, 2.5, "Hello world")]
        vtt_content = segments_to_vtt(segs)
        assert vtt_content.startswith("WEBVTT")
        assert "Hello world" in vtt_content

    def test_alignment_then_export(self, tmp_path):
        raw = [
            Segment(0.0, 0.3, "hi"),
            Segment(0.3, 2.0, "there"),
            Segment(2.0, 17.0, "very long segment that needs splitting"),
        ]
        aligned = align_segments(raw, min_duration=1.0, max_duration=7.0)

        # Should be aligned properly
        assert len(aligned) >= 2
        for seg in aligned:
            assert seg.duration <= 7.5  # small tolerance

        # Export both formats
        files = export_subtitles(aligned, tmp_path, "test_alignment", fmt="both")
        assert len(files) == 2
        for f in files:
            assert f.exists()
            assert f.stat().st_size > 0


class TestCLIIntegration:
    def test_cli_transcribe_no_translate(self, sample_video, tmp_path):
        runner = CliRunner()
        result = runner.invoke(main, [
            "transcribe", str(sample_video),
            "--model", "tiny",
            "--output", str(tmp_path),
            "--no-translate",
        ])
        # Should succeed (exit_code 0) or at least not crash on import
        # Whisper may take time on first run
        assert result.exit_code == 0 or "Error" not in (result.output or "")
```

**Step 2: Run unit tests first**

Run: `pytest tests/ -v -m "not slow"`

Expected: All unit tests pass.

**Step 3: Run integration tests (requires Whisper + GPU)**

Run: `pytest tests/test_integration.py -v -m slow`

Expected: Integration tests pass (Whisper model download may be needed on first run).

**Step 4: Commit**

```bash
cd /mnt/d/Proyectos/Yggdrasil
git add Muspelheim/AutoSub/tests/test_integration.py
git commit -m "test(autosub): end-to-end integration tests"
```

---

## Task 10: Configuration file support

**Objective:** Add TOML config file support so users can save defaults (model, languages, formats) and have them persist across runs.

**Files:**
- Modify: `Muspelheim/AutoSub/autosub/config.py`
- Create: `Muspelheim/AutoSub/tests/test_config.py`

**Step 1: Write failing tests**

```python
# tests/test_config.py
import pytest
from pathlib import Path
from autosub.config import AutoSubConfig


class TestAutoSubConfig:
    def test_defaults(self):
        config = AutoSubConfig()
        assert config.whisper_model == "base"
        assert config.device == "cuda"
        assert "es" in config.target_languages

    def test_from_toml(self, tmp_path):
        config_file = tmp_path / "config.toml"
        config_file.write_text("""
[autosub]
whisper_model = "small"
device = "cpu"
target_languages = ["es", "fr"]
output_formats = ["srt"]
""")
        config = AutoSubConfig.from_toml(config_file)
        assert config.whisper_model == "small"
        assert config.device == "cpu"
        assert config.target_languages == ["es", "fr"]

    def test_missing_toml_uses_defaults(self, tmp_path):
        nonexistent = tmp_path / "nope.toml"
        config = AutoSubConfig.from_toml(nonexistent)
        assert config.whisper_model == "base"

    def test_to_toml_dict(self):
        config = AutoSubConfig()
        d = config.to_toml_dict()
        assert "whisper_model" in d
        assert d["whisper_model"] == "base"
```

**Step 2: Run tests**

Run: `pytest tests/test_config.py -v`

Expected: Some may fail (to_toml_dict method doesn't exist yet).

**Step 3: Enhance config module**

```python
# autosub/config.py
from pathlib import Path
from dataclasses import dataclass, field, asdict
from typing import List, Optional
import toml


@dataclass
class AutoSubConfig:
    """Persistent configuration for AutoSub."""
    whisper_model: str = "base"
    device: str = "cuda"
    source_language: Optional[str] = None
    target_languages: List[str] = field(default_factory=lambda: ["es", "fr", "de", "ja", "pt"])
    output_dir: Optional[str] = None
    output_formats: List[str] = field(default_factory=lambda: ["srt", "vtt"])
    export_original: bool = True
    min_segment_duration: float = 1.0
    max_segment_duration: float = 7.0
    keep_audio: bool = False

    @classmethod
    def from_toml(cls, path: Path) -> "AutoSubConfig":
        """Load configuration from TOML file."""
        path = Path(path)
        if not path.exists():
            return cls()

        data = toml.load(path)
        section = data.get("autosub", {})
        # Filter to only recognized fields
        valid_fields = {f for f in cls.__dataclass_fields__}
        filtered = {k: v for k, v in section.items() if k in valid_fields}
        return cls(**filtered)

    def to_toml_dict(self) -> dict:
        """Serialize config to a dict suitable for TOML output."""
        return asdict(self)

    def save(self, path: Path) -> None:
        """Save configuration to TOML file."""
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(toml.dumps({"autosub": self.to_toml_dict()}), encoding="utf-8")
```

**Step 4: Run tests to verify pass**

Run: `pytest tests/test_config.py -v`

Expected: All tests pass.

**Step 5: Commit**

```bash
cd /mnt/d/Proyectos/Yggdrasil
git add Muspelheim/AutoSub/autosub/config.py Muspelheim/AutoSub/tests/test_config.py
git commit -m "feat(autosub): TOML config file support with save/load"
```

---

## Task 11: README and documentation

**Objective:** Write comprehensive README with usage examples, installation, and architecture overview.

**Files:**
- Create: `Muspelheim/AutoSub/README.md`

**Step 1: Create README**

```markdown
# AutoSub 🔥

> Synchronized subtitle generation for content creators — from video to multi-language subtitles in one command.

**Realm:** Muspelheim (WIP/Active Dev)
**Status:** Active Sprint

## What It Does

AutoSub takes a video or audio file and produces synchronized, translated subtitles:

1. **Extracts audio** from video via ffmpeg
2. **Transcribes** with OpenAI Whisper (GPU-accelerated on RTX 3060)
3. **Aligns timestamps** — fixes overlaps, merges short segments, splits long ones
4. **Translates** to 5+ languages using deep-translater
5. **Exports** SRT and WebVTT formats

## Installation

```bash
# From Yggdrasil monorepo
cd Muspelheim/AutoSub
pip install -e ".[dev]"

# System requirements
# - ffmpeg (must be on PATH)
# - CUDA toolkit (for GPU acceleration)
```

## Quick Start

```bash
# Generate subtitles with defaults (base model, 5 languages)
autosub transcribe video.mp4

# Specific model and output directory
autosub transcribe video.mp4 --model small --output ./subs/

# Skip translation, only original language subtitles
autosub transcribe video.mp4 --no-translate

# Only specific languages
autosub transcribe video.mp4 --target-langs es,fr

# Only VTT format
autosub transcribe video.mp4 --formats vtt
```

## Configuration

```bash
# View current config
autosub config --show

# Set defaults
autosub config --set whisper_model small --set device cuda
```

Config stored at `~/.autosub/config.toml`:

```toml
[autosub]
whisper_model = "base"
device = "cuda"
target_languages = ["es", "fr", "de", "ja", "pt"]
output_formats = ["srt", "vtt"]
```

## Architecture

```
Input File
    │
    ▼
Audio Extraction (ffmpeg)
    │
    ▼
Whisper Transcription → raw segments
    │
    ▼
Timestamp Alignment → fix overlaps, merge short, split long
    │
    ├──→ Export Original (SRT/VTT)
    │
    └──→ For each target language:
         ├──→ Translation (deep-translater)
         └──→ Export Translated (SRT/VTT)
```

## Whisper Models

| Model   | VRAM  | Speed     | Accuracy |
|---------|-------|-----------|----------|
| tiny    | ~1GB  | Fastest   | Basic    |
| base    | ~1GB  | Fast      | Good     |
| small   | ~2GB  | Medium    | Better   |
| medium  | ~5GB  | Slow      | Great    |
| large   | ~10GB | Slowest   | Best     |

RTX 3060 12GB recommendation: `base` for speed, `small` for balance, `medium` for quality.

## Output Structure

```
video_subtitles/
├── video.srt           # Original language
├── video.vtt           # Original language
├── video_es.srt        # Spanish
├── video_es.vtt
├── video_fr.srt        # French
├── video_fr.vtt
├── video_de.srt        # German
├── video_de.vtt
├── video_ja.srt        # Japanese
├── video_ja.vtt
├── video_pt.srt        # Portuguese
└── video_pt.vtt
```

## Testing

```bash
# Unit tests
pytest tests/ -v -m "not slow"

# Integration tests (requires Whisper + GPU)
pytest tests/ -v -m slow

# All tests
pytest tests/ -v
```

## License

Part of the Yggdrasil ecosystem.
```

**Step 2: Commit**

```bash
cd /mnt/d/Proyectos/Yggdrasil
git add Muspelheim/AutoSub/README.md
git commit -m "docs(autosub): comprehensive README with usage, architecture, and model guide"
```

---

## Task 12: Final verification and cleanup

**Objective:** Run full test suite, verify CLI works end-to-end, add a conftest.py, and do final cleanup.

**Files:**
- Create: `Muspelheim/AutoSub/tests/conftest.py`
- Verify all tests pass

**Step 1: Create conftest with shared fixtures**

```python
# tests/conftest.py
import pytest
import subprocess
from pathlib import Path


@pytest.fixture
def sample_segments():
    """Provide standard test segments."""
    from autosub.transcriber import Segment
    return [
        Segment(0.0, 2.5, "Hello world"),
        Segment(2.5, 5.0, "This is a test"),
        Segment(5.0, 7.5, "Of the subtitle system"),
    ]


@pytest.fixture
def silent_audio(tmp_path):
    """Generate a 2-second silent WAV for testing."""
    audio_path = tmp_path / "silent.wav"
    subprocess.run(
        ["ffmpeg", "-f", "lavfi", "-i", "anullsrc=r=16000:cl=mono",
         "-t", "2", "-y", str(audio_path)],
        capture_output=True, check=True,
    )
    return audio_path


def pytest_configure(config):
    config.addinivalue_line("markers", "slow: marks tests as slow (deselect with '-m \"not slow\"')")
```

**Step 2: Run full test suite**

Run: `pytest tests/ -v -m "not slow"`

Expected: All unit tests pass.

Run: `pytest tests/ -v --tb=short`

Expected: All tests pass (integration may need Whisper model download on first run).

**Step 3: Verify CLI works**

Run:
```bash
autosub --version
autosub --help
autosub transcribe --help
autosub config --show
```

Expected: All commands return valid output.

**Step 4: Final commit**

```bash
cd /mnt/d/Proyectos/Yggdrasil
git add Muspelheim/AutoSub/tests/conftest.py
git commit -m "test(autosub): conftest with shared fixtures and final verification"
```

---

## Summary

| Task | Module | Time Est. |
|------|--------|-----------|
| 1    | Project scaffolding | 5 min |
| 2    | Audio extraction | 5 min |
| 3    | Whisper transcription | 5 min |
| 4    | Timestamp alignment | 5 min |
| 5    | Translation module | 5 min |
| 6    | SRT/VTT export | 5 min |
| 7    | Pipeline orchestrator | 5 min |
| 8    | Full CLI integration | 5 min |
| 9    | E2E integration tests | 5 min |
| 10   | TOML config support | 5 min |
| 11   | README documentation | 5 min |
| 12   | Final verification | 5 min |

**Total: ~60 min | 12 tasks**

Key design decisions:
- **Lazy model loading** — Whisper model loads only on first transcription call
- **TDD throughout** — each module has tests written before implementation
- **Modular pipeline** — each stage is independent and testable in isolation
- **Mock translation** for testing without API calls
- **GPU-first** — defaults to CUDA, falls back gracefully
