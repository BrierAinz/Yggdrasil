# Changelog

All notable changes to ForgeMaster will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.0.0] - 2025-05-03

### Added

- **Cross-Platform GPU Support**: GPU detection now tries three backends in order — NVIDIA (nvidia-smi), AMD (rocm-smi), and Apple Silicon (system_profiler on macOS). Graceful fallback with clear info messages when no GPU is detected.
- **Progress Bars**: Rich progress bars added to the `dupes` command (file count + hash computation) and the `download` command (file size, transfer speed, and download percentage via `DownloadColumn`/`TransferSpeedColumn`).
- **Shell Completion**: Typer's built-in `--install-completion` and `--show-completion` flags are documented for bash, zsh, fish, and PowerShell.
- **Structured Logging**: JSON-structured logging module (`forgemaster/logging.py`) with configurable levels and output to stderr.
- **Metadata Reading**: Automatic metadata extraction for GGUF, safetensors, and PyTorch model files in the scanner.
- **Type Checking**: Full mypy/pyright type annotations throughout the codebase.
- **CI**: GitHub Actions workflow for linting, type-checking, and testing.
- **Benchmark Command**: CLI command for benchmarking model inference performance.
- **Models Command**: CLI command for browsing and searching the HuggingFace model catalog.
- **Info Command**: CLI command for displaying detailed model metadata and VRAM requirements.
- **Config Command**: `config show` and `config set` subcommands for managing ForgeMaster configuration via YAML and environment variables.

### Changed

- **GPU Command**: Now shows GPU type badge (NVIDIA/AMD/Apple Silicon) and only displays process table for NVIDIA GPUs.
- **Version bumped** from 0.1.0 to 1.0.0.

## [0.1.0] - 2025-05-03

### Added

- **Model Scanner**: Recursively scan directories for LLM model files (GGUF, safetensors, PyTorch, ONNX) with automatic metadata extraction (architecture, quantization, parameter count, VRAM estimation).
- **GPU Monitor**: Query NVIDIA GPU status via `nvidia-smi` — list GPUs, VRAM usage, running processes, driver version, and temperature.
- **Model Downloader**: Download models from HuggingFace Hub with resume support, progress callbacks, retry logic, and cancellation.
- **Disk Scanner**: Analyze disk usage by model vs non-model files, per-directory breakdown, and model-size ranking.
- **Duplicate Finder**: Detect duplicate and near-duplicate models by name similarity, size tolerance, and SHA256 content hashing; generate cleanup reports.
- **VRAM Calculator**: Estimate VRAM requirements for models given context length, batch size, and quantization; suggest GPU/CPU offload strategies; special ComfyUI estimation mode.
- **SQLite Catalog**: Persistent model database with CRUD operations, search, filtering by format/architecture, GPU profile storage, and tagging/notes.
- **CLI**: Full Typer-based command-line interface with Rich-formatted output for `scan`, `list`, `stats`, `check`, `gpu`, `dupes`, `download`, `benchmark`, `models`, `info`, and `version` commands.
- **Configuration**: `forgemaster/config.py` module with `Config` dataclass, `YGGDRASIL_ROOT` environment variable support, and YAML config file at `~/.forgemaster/config.yaml`.
- **Test Suite**: Comprehensive test coverage for scanner, GPU monitor, downloader, disk scanner, VRAM calculator, catalog, and CLI.

### Changed

- Initial release.
