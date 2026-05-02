# ForgeMaster

CLI tool for managing Niflheim resources: LLM models, datasets, checkpoints, VRAM monitoring, and disk usage.

## Features

- **Model Scanner**: Scan directories for LLM models and extract metadata
- **SQLite Catalog**: Persistent storage for model metadata
- **VRAM Calculator**: Estimate VRAM requirements for model inference
- **Disk Analyzer**: Find duplicates and suggest cleanup actions
- **GPU Monitor**: Real-time GPU status via nvidia-smi
- **Model Downloader**: Search and download models from HuggingFace
- **Rich CLI**: Colored tables and formatted output

## Installation

```bash
pip install -e ".[dev]"
```

## Usage

```bash
forgemaster --help
forgemaster scan /path/to/models
forgemaster list
forgemaster stats
forgemaster gpu-status
```

## Development

```bash
pip install -e ".[dev]"
pytest tests/ -v
```
