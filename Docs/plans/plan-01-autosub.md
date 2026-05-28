# AutoSub — Generador Automático de Subtítulos

> **For Hermes:** Use subagent-driven-development skill to implement this plan task-by-task.

**Goal:** CLI que toma video/audio y genera subtítulos sincronizados con whisper, traduce a múltiples idiomas, y exporta SRT/VTT.

**Architecture:** Pipeline secuencial: whisper transcription → word-level alignment → traducción por segmento → export multi-formato. CLI-first con Rich para output, configuración via TOML.

**Tech Stack:** Python 3.11+, faster-whisper (CTranslate2 backend), pyannote-audio (diarization), deep-translator, Rich, Typer, SQLite para caché de traducciones.

**Realm:** Muspelheim/AutoSub/

---

## Task 1: Scaffold del proyecto

**Objective:** Crear estructura de proyecto con pyproject.toml, dependencias, y estructura de carpetas.

**Files:**
- Create: `Muspelheim/AutoSub/pyproject.toml`
- Create: `Muspelheim/AutoSub/autosub/__init__.py`
- Create: `Muspelheim/AutoSub/autosub/cli.py`
- Create: `Muspelheim/AutoSub/tests/__init__.py`

**Step 1:** Crear `pyproject.toml`

```toml
[project]
name = "autosub"
version = "0.1.0"
description = "Automatic subtitle generator with translation"
requires-python = ">=3.11"
dependencies = [
    "faster-whisper>=1.0",
    "deep-translator>=1.11",
    "rich>=13.0",
    "typer>=0.9",
    "pysubs2>=1.6",
]

[project.optional-dependencies]
dev = ["pytest>=7.0", "pytest-cov"]
gpu = ["pyannote-audio>=3.0"]

[project.scripts]
autosub = "autosub.cli:app"

[tool.pytest.ini_options]
testpaths = ["tests"]
```

**Step 2:** Crear módulos vacíos y tests vacíos.

**Step 3:** `pip install -e ".[dev]"` y verificar que `autosub --help` funciona.

**Step 4:** Commit: `feat(autosub): scaffold project structure`

---

## Task 2: Transcripción con faster-whisper

**Objective:** Módulo de transcripción que toma un path de audio/video y devuelve segmentos con timestamps.

**Files:**
- Create: `Muspelheim/AutoSub/autosub/transcriber.py`
- Create: `Muspelheim/AutoSub/tests/test_transcriber.py`

**Step 1:** Escribir test de transcripción

```python
# tests/test_transcriber.py
import pytest
from autosub.transcriber import Transcriber

def test_transcriber_accepts_audio_path(tmp_path):
    """Transcriber should accept a valid audio file path."""
    audio = tmp_path / "test.wav"
    audio.write_bytes(b"RIFF" + b"\x00" * 100)  # dummy WAV header
    t = Transcriber(model_size="tiny")
    assert t.model_size == "tiny"

def test_transcriber_invalid_path_raises():
    """Transcriber should raise on nonexistent file."""
    t = Transcriber(model_size="tiny")
    with pytest.raises(FileNotFoundError):
        t.transcribe("/nonexistent/file.wav")

def test_segment_dataclass():
    """Segment should hold text, start, end."""
    from autosub.transcriber import Segment
    s = Segment(text="hello", start=0.0, end=1.0)
    assert s.text == "hello"
    assert s.start == 0.0
```

**Step 2:** Ejecutar tests — deben fallar.

**Step 3:** Implementar `transcriber.py`

```python
# autosub/transcriber.py
from dataclasses import dataclass
from pathlib import Path

@dataclass
class Segment:
    text: str
    start: float
    end: float

class Transcriber:
    def __init__(self, model_size: str = "base", device: str = "auto", compute_type: str = "int8"):
        self.model_size = model_size
        self.device = device
        self.compute_type = compute_type
        self._model = None

    def _load_model(self):
        if self._model is None:
            from faster_whisper import WhisperModel
            self._model = WhisperModel(
                self.model_size,
                device=self.device if self.device != "auto" else "cuda" if self._has_gpu() else "cpu",
                compute_type=self.compute_type,
            )

    @staticmethod
    def _has_gpu() -> bool:
        try:
            import torch
            return torch.cuda.is_available()
        except ImportError:
            return False

    def transcribe(self, audio_path: str, language: str = None) -> list[Segment]:
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
        return [
            Segment(text=s.text.strip(), start=s.start, end=s.end)
            for s in segments_iter
        ]
```

**Step 4:** Tests pasan. Commit: `feat(autosub): add transcription module`

---

## Task 3: Export SRT/VTT

**Objective:** Convertir segmentos a formato SRT y VTT.

**Files:**
- Create: `Muspelheim/AutoSub/autosub/exporter.py`
- Create: `Muspelheim/AutoSub/tests/test_exporter.py`

**Step 1:** Test de formato SRT

```python
from autosub.transcriber import Segment
from autosub.exporter import export_srt, export_vtt

def test_srt_format():
    segments = [Segment(text="Hello world", start=0.0, end=2.5)]
    result = export_srt(segments)
    assert "1\n" in result
    assert "00:00:00,000 --> 00:00:02,500" in result
    assert "Hello world" in result

def test_vtt_format():
    segments = [Segment(text="Hello world", start=0.0, end=2.5)]
    result = export_vtt(segments)
    assert "WEBVTT" in result
    assert "00:00:00.000 --> 00:00:02.500" in result
```

**Step 2-3:** Implementar usando pysubs2, ejecutar tests.

**Step 4:** Commit: `feat(autosub): add SRT/VTT export`

---

## Task 4: Traducción multi-idioma

**Objective:** Traducir segmentos a múltiples idiomas con caché en SQLite.

**Files:**
- Create: `Muspelheim/AutoSub/autosub/translator.py`
- Create: `Muspelheim/AutoSub/tests/test_translator.py`

```python
# tests/test_translator.py
from autosub.translator import Translator

def test_translator_init():
    t = Translator(target_lang="es")
    assert t.target_lang == "es"

def test_translate_segment_caches(tmp_path):
    t = Translator(target_lang="es", cache_dir=tmp_path)
    result = t.translate_text("hello world")
    # First call hits API or local, second should use cache
    assert isinstance(result, str)
```

**Implementation:** `translator.py` con deep-translator (Google Translate gratis), SQLite cache para no retraducir, soporte para múltiples motores (Google, DeepL, local).

**Commit:** `feat(autosub): add translation module with cache`

---

## Task 5: CLI con Typer + Rich

**Objective:** Interfaz CLI completa con progreso visual.

**Files:**
- Modify: `Muspelheim/AutoSub/autosub/cli.py`

```python
# autosub/cli.py
import typer
from rich.console import Console
from rich.progress import Progress

app = typer.Typer(help="🎬 AutoSub — Automatic subtitle generator")
console = Console()

@app.command()
def transcribe(
    input_file: str = typer.Argument(..., help="Path to audio/video file"),
    language: str = typer.Option(None, "--lang", "-l", help="Source language (auto-detect)"),
    model: str = typer.Option("base", "--model", "-m", help="Whisper model size"),
    output: str = typer.Option(None, "--output", "-o", help="Output file path"),
    format: str = typer.Option("srt", "--format", "-f", help="Output format: srt, vtt, txt"),
):
    """Transcribe audio/video to subtitles."""
    ...

@app.command()
def translate(
    input_srt: str = typer.Argument(..., help="Path to SRT file"),
    target_lang: str = typer.Option("es", "--to", "-t", help="Target language"),
    output: str = typer.Option(None, "--output", "-o"),
):
    """Translate existing subtitles."""
    ...
```

**Commit:** `feat(autosub): add CLI with transcribe and translate commands`

---

## Task 6: Pipeline completo (transcribe + translate + export)

**Objective:** Comando `autosub pipeline` que ejecuta todo de un golpe.

**Files:**
- Modify: `Muspelheim/AutoSub/autosub/cli.py`
- Create: `Muspelheim/AutoSub/autosub/pipeline.py`

Pipeline orquesta: transcribir → alinear → traducir → exportar. Con Rich progress bars para cada paso.

**Commit:** `feat(autosub): add full pipeline command`

---

## Task 7: Alineación word-level

**Objective:** Alineación precisa a nivel de palabra para mejor sincronización.

**Files:**
- Create: `Muspelheim/AutoSub/autosub/aligner.py`

Usa `faster-whisper` word timestamps + ajuste fino con DTW si está disponible.

**Commit:** `feat(autosub): add word-level alignment`

---

## Task 8: Detección de idioma automática

**Objective:** Detectar idioma del audio y seleccionar modelo whisper apropiado.

**Files:**
- Modify: `Muspelheim/AutoSub/autosub/transcriber.py`

Usa `info.language` de faster-whisper para detectar, con `--lang auto` como default.

**Commit:** `feat(autosub): auto language detection`

---

## Task 9: Batch processing (múltiples archivos)

**Objective:** Procesar directorios completos de archivos.

**Files:**
- Modify: `Muspelheim/AutoSub/autosub/cli.py`
- Create: `Muspelheim/AutoSub/tests/test_batch.py`

Comando `autosub batch ./videos/ --lang es --format srt` que procesa todos los archivos de video en un directorio.

**Commit:** `feat(autosub): add batch processing`

---

## Task 10: Configuración TOML

**Objective:** Archivo de configuración `autosub.toml` con defaults.

**Files:**
- Create: `Muspelheim/AutoSub/autosub/config.py`
- Create: `Muspelheim/AutoSub/tests/test_config.py`

Defaults para modelo, idioma, formato de salida, directorio de caché, GPU settings.

**Commit:** `feat(autosub): add TOML configuration`

---

## Task 11: Integración de tests + CI

**Objective:** Tests de integración y pytest workflow.

**Files:**
- Modify: `Muspelheim/AutoSub/tests/`
- Create: `.github/workflows/autosub-ci.yml` (o agregar al existente)

Tests unitarios para cada módulo, test de integración con archivo WAV pequeño de prueba.

**Commit:** `ci(autosub): add test workflow`

---

## Resumen de Stack

| Componente | Tecnología |
|---|---|
| Transcripción | faster-whisper (CTranslate2, GPU-accel) |
| Diarización | pyannote-audio (opcional, GPU) |
| Traducción | deep-translator (Google, DeepL, local) |
| Export | pysubs2 (SRT, VTT, ASS, TXT) |
| CLI | Typer + Rich |
| Caché | SQLite |
| Config | TOML |
| Tests | pytest |
