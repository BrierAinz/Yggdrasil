# ForgeMaster

⚒️ Niflheim resource manager for LLM models, VRAM monitoring, and disk usage.

## Features

- **Model Scanner**: Find GGUF, safetensors, and PyTorch models across LM Studio, ComfyUI, and HuggingFace caches
- **VRAM Calculator**: Estimate GPU memory needed for inference
- **GPU Monitor**: Real-time nvidia-smi integration for RTX 3060 12GB
- **Disk Usage**: Find duplicates and suggest cleanup
- **Model Download**: Helper for HuggingFace model downloads

## Install

```bash
pip install -e ".[dev]"
```

## Usage

```bash
forgemaster scan          # Scan for models
forgemaster list          # List all models
forgemaster stats         # Disk usage statistics
forgemaster check llama-7b  # Can I run this model?
```
