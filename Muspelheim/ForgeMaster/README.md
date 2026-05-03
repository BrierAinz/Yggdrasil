# ForgeMaster

⚒️ **ForgeMaster** v1.0.0 — a command-line tool for managing LLM model files, monitoring GPU VRAM, and tracking disk usage. It is part of the [Yggdrasil](https://github.com/nousresearch/yggdrasil) ecosystem — the Niflheim resource manager.

## Features

- **Model Scanner** — Recursively scan directories for model files (GGUF, safetensors, PyTorch, ONNX) with automatic metadata extraction (architecture, quantization, parameter count, VRAM estimation).
- **GPU Monitor** — Cross-platform GPU status: NVIDIA (nvidia-smi), AMD (rocm-smi), and Apple Silicon (system_profiler). Shows VRAM usage, temperature, utilization, and running processes.
- **Model Downloader** — Download models from HuggingFace Hub with resume support, Rich progress bars, and retry logic.
- **Disk Scanner** — Analyze disk usage: model bytes vs non-model bytes, per-directory breakdown, and model-size ranking.
- **Duplicate Finder** — Detect duplicate and near-duplicate models by name similarity, size tolerance, and SHA256 content hashing; Rich progress bars during scan; generate cleanup reports.
- **VRAM Calculator** — Estimate VRAM requirements for models with context length, batch size, and quantization awareness; suggest GPU/CPU offload strategies.
- **SQLite Catalog** — Persistent model database with CRUD, search, filtering, GPU profiles, and tagging/notes.
- **Structured Logging** — JSON-structured logging with configurable levels.

## Installation

```bash
# Clone the repository
git clone https://github.com/nousresearch/yggdrasil.git
cd yggdrasil/Muspelheim/ForgeMaster

# Install in editable mode
pip install -e .

# Or with dev dependencies
pip install -e ".[dev]"
```

## Configuration

### Environment Variable

ForgeMaster respects the `YGGDRASIL_ROOT` environment variable. When set, it is used as the base directory for default model scan paths and catalog storage.

```bash
export YGGDRASIL_ROOT=/path/to/yggdrasil
```

If `YGGDRASIL_ROOT` is not set, ForgeMaster defaults to common model cache locations:

- `~/.cache/huggingface`
- `~/.cache/lm-studio`

### Config File

ForgeMaster loads configuration from `~/.forgemaster/config.yaml`. If the file does not exist, sensible defaults are used.

Example configuration:

```yaml
scan_dirs:
  - ~/.cache/huggingface
  - ~/.cache/lm-studio
  - /mnt/d/Proyectos/comfy/ComfyUI/models
gpu_profile: RTX 3060
catalog_path: ~/.forgemaster/catalog.db
```

You can view and edit configuration with:

```bash
forgemaster config show
forgemaster config set scan_dirs.0 /new/model/path
```

## CLI Commands

ForgeMaster provides a Typer-based CLI with Rich-formatted output. Run any command with `--help` for details.

### `forgemaster scan`

Scan directories for model files.

```bash
# Scan default directories
forgemaster scan

# Scan specific paths
forgemaster scan --path /models/gguf --path /models/safetensors

# Scan and save results to catalog
forgemaster scan --catalog
```

### `forgemaster gpu`

Show GPU information and current utilization.

```bash
forgemaster gpu
```

Displays VRAM usage with a visual bar, temperature, utilization percentage, driver version, and running GPU processes. On multi-GPU systems, shows a panel for each GPU with a colored type badge (NVIDIA, AMD, or Apple Silicon).

For more details, see [Cross-Platform GPU Support](#cross-platform-gpu-support) below.

### `forgemaster download`

Download a model from HuggingFace Hub.

```bash
# Download a model
forgemaster download TheBloke/Llama-2-7B-GGUF

# Download to a specific directory
forgemaster download TheBloke/Llama-2-7B-GGUF --output ./models

# Force re-download
forgemaster download TheBloke/Llama-2-7B-GGUF --force

# Specify a revision/branch
forgemaster download TheBloke/Llama-2-7B-GGUF --revision main
```

### `forgemaster dupes`

Find duplicate or similar model files.

```bash
# Find duplicates in default directories
forgemaster dupes

# Find duplicates in specific paths
forgemaster dupes --path /models

# Also generate cleanup recommendations
forgemaster dupes --cleanup
```

### `forgemaster info`

Check if a model can run on the current GPU (VRAM compatibility).

```bash
# Check by model name (auto-detect GPU VRAM)
forgemaster check llama-7b-q4

# Check with a specific VRAM amount (in MB)
forgemaster check llama-7b-q4 --gpu-vram 12288
```

> **Note:** The CLI command is `check` (aliased as `info` in some contexts).

### `forgemaster config`

View and edit ForgeMaster configuration.

```bash
# Show current configuration
forgemaster config show

# Set a configuration value
forgemaster config set gpu_profile "RTX 4090"
forgemaster config set scan_dirs.0 /new/model/path
```

### `forgemaster benchmark`

Benchmark model loading and inference times (placeholder for future release).

### `forgemaster models`

List all cataloged models.

```bash
# List all models
forgemaster list

# Filter by format
forgemaster list --format gguf

# Filter by architecture
forgemaster list --arch llama
```

### `forgemaster version`

Show the current ForgeMaster version.

```bash
forgemaster version
```

### `forgemaster stats`

Show disk usage statistics and model distribution.

```bash
forgemaster stats --path /models
```

## Cross-Platform GPU Support

ForgeMaster detects GPUs using multiple backends, tried in order:

| Backend | Tool | Platform | Data Available |
|---------|------|----------|----------------|
| NVIDIA | `nvidia-smi` | Linux, Windows | Full: VRAM, temp, utilization, processes, driver |
| AMD | `rocm-smi` | Linux (ROCm) | Partial: VRAM, temp, utilization, product name |
| Apple Silicon | `system_profiler` | macOS | Limited: product name, VRAM (shared memory) |

- **NVIDIA** is tried first and provides the richest data (including GPU processes).
- **AMD** is tried when `nvidia-smi` is not available. Requires the ROCm toolkit.
- **Apple Silicon** is tried on macOS when neither NVIDIA nor AMD is detected. Uses system_profiler to read unified memory info.

If no GPU is detected, ForgeMaster shows a clear message with guidance on installing the appropriate driver or toolkit.

## Shell Completion

ForgeMaster uses Typer's built-in shell completion. Install completions for your shell with:

```bash
# Install completion for your current shell
forgemaster --install-completion

# Show the completion script for a specific shell
forgemaster --show-completion bash
forgemaster --show-completion zsh
forgemaster --show-completion fish
forgemaster --show-completion powershell
```

After running `--install-completion`, **restart your shell** (or open a new terminal) for the changes to take effect.

### Manual Installation

If automatic installation doesn't work, you can manually add the completion script to your shell:

**bash:**
```bash
eval "$(forgemaster --show-completion bash)"
```

**zsh:**
```bash
# Add to ~/.zshrc
eval "$(forgemaster --show-completion zsh)"
```

**fish:**
```fish
forgemaster --show-completion fish | source
```

**PowerShell:**
```powershell
# Add to $PROFILE
forgemaster --show-completion powershell | Out-String | Invoke-Expression
```

## Project Structure

```
ForgeMaster/
├── pyproject.toml
├── README.md
├── CHANGELOG.md
├── LICENSE
├── forgemaster/
│   ├── __init__.py
│   ├── cli.py          # Typer CLI application
│   ├── scanner.py      # Model file scanner
│   ├── gpu.py           # Cross-platform GPU monitor (NVIDIA/AMD/Apple)
│   ├── downloader.py    # HuggingFace model downloader
│   ├── disk.py          # Disk usage and duplicate finder
│   ├── vram.py          # VRAM calculator and offload strategies
│   ├── catalog.py       # SQLite model catalog
│   ├── logging.py       # Structured JSON logging
│   └── config.py        # Configuration management
└── tests/
    ├── conftest.py      # Shared test fixtures
    ├── test_scanner.py
    ├── test_gpu.py
    ├── test_downloader.py
    ├── test_disk.py
    ├── test_vram.py
    ├── test_catalog.py
    └── test_cli.py
```

## Yggdrasil Ecosystem

ForgeMaster is part of the **Yggdrasil** project — a collection of tools for working with LLMs:

- **ForgeMaster** (this tool) — Model management, VRAM monitoring, and disk usage
- More tools coming soon

## License

MIT License. See [LICENSE](LICENSE) for details.
