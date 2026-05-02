# AutoSub — Generador Automático de Subtítulos

> **Realm:** Muspelheim | **Status:** En desarrollo

CLI que toma video/audio y genera subtítulos sincronizados con Whisper, traduce a múltiples idiomas, y exporta SRT/VTT.

## Stack

| Componente | Tecnología |
|---|---|
| Transcripción | faster-whisper (CTranslate2, GPU-accel) |
| Diarización | pyannote-audio (opcional, GPU) |
| Traducción | deep-translator (Google, DeepL, local) |
| Export | pysubs2 (SRT, VTT, ASS, TXT) |
| CLI | Typer + Rich |
| Caché | SQLite |
| Config | TOML |

## Instalación

```bash
cd Muspelheim/AutoSub
pip install -e ".[dev]"
```

## Uso

```bash
autosub transcribe video.mp4 --lang es --format srt
autosub translate subtitles.srt --to es
autosub pipeline video.mp4 --lang en --translate es --format srt
autosub batch ./videos/ --lang es --format srt
```

## Tests

```bash
pytest
```
