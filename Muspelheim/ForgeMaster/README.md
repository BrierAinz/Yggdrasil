# ForgeMaster

> The smiths of Muspelheim tend their forges, cataloging every blade in the armory.

Niflheim resource manager: LLM models inventory, VRAM and GPU monitoring, disk usage analysis, Safetensors inspection, and HuggingFace model downloading.

## Installation

```bash
pip install -e .
```

## Usage

```bash
# Scan local directories for model files
forgemaster scan --path ~/.cache/huggingface

# Check if a model fits in your GPU VRAM
forgemaster check llama-2-7b

# Show GPU status and VRAM usage
forgemaster gpu
```

Or use the Python API:

```python
from forgemaster.scanner import ModelScanner
from forgemaster.gpu import GPUMonitor

scanner = ModelScanner()
result = scanner.scan([Path("~/.cache/huggingface")])

monitor = GPUMonitor()
for gpu in monitor.get_gpu_info():
    print(f"{gpu.name}: {gpu.vram_used_mb}/{gpu.vram_total_mb} MB VRAM")
```

## Architecture

This package is part of the Muspelheim realm in the Yggdrasil ecosystem.

## License

MIT
