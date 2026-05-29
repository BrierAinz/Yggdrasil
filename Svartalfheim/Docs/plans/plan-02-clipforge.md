# ClipForge — Detector de Clips Virales

> **For Hermes:** Use subagent-driven-development skill to implement this plan task-by-task.

**Goal:** Dado un video largo (stream, podcast), detecta segmentos de alto impacto y los recorta con formato vertical automático.

**Architecture:** Pipeline: extracción de audio → análisis de energía/vad → transcripción whisper → scoring de viralidad → recorte ffmpeg con reframe vertical. CLI-first.

**Tech Stack:** Python 3.11+, faster-whisper, pyannote-audio (speaker diarization), librosa (audio analysis), ffmpeg-python, Rich/Typer.

**Realm:** Muspelheim/ClipForge/

---

## Task 1: Scaffold del proyecto

**Objective:** Estructura de proyecto con pyproject.toml.

**Files:**
- Create: `Muspelheim/ClipForge/pyproject.toml`
- Create: `Muspelheim/ClipForge/clipforge/__init__.py`
- Create: `Muspelheim/ClipForge/clipforge/cli.py`
- Create: `Muspelheim/ClipForge/tests/__init__.py`

```toml
[project]
name = "clipforge"
version = "0.1.0"
description = "AI-powered viral clip detector from long videos"
requires-python = ">=3.11"
dependencies = [
    "faster-whisper>=1.0",
    "librosa>=0.10",
    "ffmpeg-python>=0.2",
    "rich>=13.0",
    "typer>=0.9",
    "numpy>=1.24",
    "scipy>=1.11",
    "pyannote-audio>=3.0",
]

[project.optional-dependencies]
dev = ["pytest>=7.0", "pytest-cov"]

[project.scripts]
clipforge = "clipforge.cli:app"
```

**Commit:** `feat(clipforge): scaffold project`

---

## Task 2: Extracción y análisis de audio

**Objective:** Módulo que extrae audio de video y analiza energía/RMS.

**Files:**
- Create: `Muspelheim/ClipForge/clipforge/audio.py`
- Create: `Muspelheim/ClipForge/tests/test_audio.py`

```python
# clipforge/audio.py
from pathlib import Path
import numpy as np

class AudioExtractor:
    def extract(self, video_path: str, output_path: str = None) -> str:
        """Extract audio from video file using ffmpeg."""
        ...

class EnergyAnalyzer:
    def compute_rms(self, audio: np.ndarray, frame_length: int = 2048, hop_length: int = 512) -> np.ndarray:
        """Compute RMS energy per frame."""
        ...

    def detect_peaks(self, rms: np.ndarray, threshold: float = 2.0) -> list[tuple[float, float]]:
        """Detect energy peaks above threshold * std."""
        ...
```

**Tests:** Verificar extracción con ffmpeg, RMS compute con señal sinusoidal, peak detection con señal sintética.

**Commit:** `feat(clipforge): audio extraction and energy analysis`

---

## Task 3: Transcripción con timestamps granulares

**Objective:** Transcribir con word-level timestamps para sincronización precisa.

**Files:**
- Create: `Muspelheim/ClipForge/clipforge/transcriber.py`
- Create: `Muspelheim/ClipForge/tests/test_transcriber.py`

Wrap de faster-whisper con word timestamps. Devuelve lista de `(text, start, end)`.

**Commit:** `feat(clipforge): transcription with word timestamps`

---

## Task 4: Scoring de viralidad

**Objective:** Algoritmo que puntúa segmentos por potencial viral.

**Files:**
- Create: `Muspelheim/ClipForge/clipforge/scorer.py`
- Create: `Muspelheim/ClipForge/tests/test_scorer.py`

Factores de scoring:
- **Energía de audio**: picos de energía = momentos emocionales
- **Densidad de palabras**: habla rápida = emoción/intensidad
- **Keywords**: detección de exclamaciones, risas, swore words
- **Cambio de hablante**: transiciones = momentos interesantes
- **Duración óptima**: preferencia por clips de 30-90 segundos

Score final = weighted sum de factores, normalizado 0-100.

```python
class ViralScorer:
    def __init__(self, energy_weight=0.3, speech_weight=0.25, keyword_weight=0.2, speaker_weight=0.15, duration_weight=0.1):
        ...

    def score_segments(self, segments, audio_analysis, speaker_segments) -> list[ScoredSegment]:
        ...

    def rank_top(self, scored_segments, n=5, min_gap_seconds=30) -> list[ScoredSegment]:
        """Return top N segments with minimum gap between them."""
        ...
```

**Commit:** `feat(clipforge): viral scoring algorithm`

---

## Task 5: Recorte y reframing vertical (9:16)

**Objective:** Cortar segmentos y convertir a formato vertical con ffmpeg.

**Files:**
- Create: `Muspelheim/ClipForge/clipforge/cutter.py`
- Create: `Muspelheim/ClipForge/tests/test_cutter.py`

Usa ffmpeg para:
1. Cortar segmento temporal con `-ss` y `-to`
2. Reframe a vertical (9:16) con crop inteligente centrado en hablante
3. Añadir subtítulos quemados opcionales
4. Output: MP4 con H.264, audio AAC

```python
class ClipCutter:
    def cut_vertical(self, video_path, start, end, output_path, width=1080, height=1920) -> str:
        """Cut segment and reframe to vertical format."""
        ...

    def burn_subtitles(self, video_path, srt_path, output_path) -> str:
        """Burn subtitles into video."""
        ...
```

**Commit:** `feat(clipforge): vertical clip cutting with ffmpeg`

---

## Task 6: Pipeline completo (analyze → score → cut)

**Objective:** Comando `clipforge analyze` que ejecuta todo el pipeline.

**Files:**
- Modify: `Muspelheim/ClipForge/clipforge/cli.py`
- Create: `Muspelheim/ClipForge/clipforge/pipeline.py`

```python
@app.command()
def analyze(
    input_video: str = typer.Argument(..., help="Path to long video"),
    top_n: int = typer.Option(5, "--top", "-n", help="Number of clips to extract"),
    min_duration: float = typer.Option(30.0, "--min-duration", help="Minimum clip duration in seconds"),
    max_duration: float = typer.Option(90.0, "--max-duration", help="Maximum clip duration in seconds"),
    output_dir: str = typer.Option("./clips", "--output", "-o"),
    format: str = typer.Option("vertical", "--format", "-f", help="Output format: vertical, horizontal, square"),
    subtitles: bool = typer.Option(True, "--subs/--no-subs", help="Burn subtitles"),
):
    """Analyze video and extract viral clips."""
    ...
```

**Commit:** `feat(clipforge): full analysis pipeline`

---

## Task 7: Detección de eventos (risas, aplausos, exclamaciones)

**Objective:** Clasificador de eventos de audio para mejor scoring.

**Files:**
- Create: `Muspelheim/ClipForge/clipforge/events.py`
- Create: `Muspelheim/ClipForge/tests/test_events.py`

Usa pyannote-audio para detección de eventos de audio. Mapea emociones a tipos de clip viral.

**Commit:** `feat(clipforge): audio event detection`

---

## Task 8: Speaker diarization

**Objective:** Identificar quién habla cuándo para mejor framing y scoring.

**Files:**
- Create: `Muspelheim/ClipForge/clipforge/diarizer.py`

Usa pyannote-audio con modelo preentrenado. Desde CLI es opcional (require GPU).

**Commit:** `feat(clipforge): speaker diarization`

---

## Task 9: Config TOML + presets

**Objective:** Configuración persistente y presets para diferentes tipos de contenido.

**Files:**
- Create: `Muspelheim/ClipForge/clipforge/config.py`

Presets: `twitch-stream`, `podcast`, `lecture`, `interview`. Cada uno con pesos diferentes para scoring.

**Commit:** `feat(clipforge): add config and content presets`

---

## Task 10: Preview y reporte

**Objective:** Generar HTML con thumbnails de clips detectados para preview.

**Files:**
- Create: `Muspelheim/ClipForge/clipforge/report.py`

Genera HTML con Rich console output + thumbnail images de cada clip con score, timestamps y justificación.

**Commit:** `feat(clipforge): HTML preview report`

---

## Task 11: Tests de integración + CI

**Objective:** Tests completos y CI workflow.

**Commit:** `ci(clipforge): add test workflow`

---

## Resumen de Stack

| Componente | Tecnología |
|---|---|
| Audio extraction | ffmpeg-python |
| Audio analysis | librosa (RMS, spectral) |
| Transcripción | faster-whisper |
| Event detection | pyannote-audio |
| Speaker diarization | pyannote-audio |
| Video cutting | ffmpeg (crop, reframe) |
| Scoring | numpy, scipy (peaks) |
| CLI | Typer + Rich |
| Config | TOML |
