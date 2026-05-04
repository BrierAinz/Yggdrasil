# AutoSub

> Born of Muspelheim's fire, forging words from the roar of chaos.

Automatic subtitle generator with translation — transcribe audio/video to SRT/VTT/TXT, then translate to any language, powered by faster-whisper and deep-translator.

## Installation

```bash
pip install -e .
```

## Usage

```bash
# Transcribe a video to SRT
autosub transcribe video.mp4 --lang en --format srt

# Full pipeline: transcribe and translate to Spanish
autosub pipeline video.mp4 --lang en --translate es --model base
```

Or use the Python API:

```python
from autosub.pipeline import Pipeline

pipe = Pipeline(model_size="base")
result = pipe.run(input_path="video.mp4", language="en", target_lang="es", output_format="srt")
print(f"Wrote {result.segments_count} segments to {result.output_path}")
```

## Architecture

This package is part of the Muspelheim realm in the Yggdrasil ecosystem.

## License

MIT
