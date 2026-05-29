"""ForgeMaster — Muspelheim resource manager for LLM models, VRAM, and disk."""

__version__ = "1.0.0"

from forgemaster.catalog import Catalog
from forgemaster.config import Config, load_config, save_config, set_config_value
from forgemaster.disk import (
    CleanupAction,
    CleanupReport,
    DiskScanner,
    DiskUsage,
    DuplicateFinder,
    DuplicateGroup,
)
from forgemaster.downloader import (
    DownloadConfig,
    DownloadError,
    DownloadProgress,
    DownloadStatus,
    ModelDownloader,
)
from forgemaster.gpu import GPUInfo, GPUMonitor, GPUProcess
from forgemaster.logging import configure_logging, get_logger
from forgemaster.metadata import (
    get_model_metadata,
    read_gguf_metadata,
    read_hf_config,
    read_safetensors_metadata,
)
from forgemaster.scanner import ModelInfo, ModelScanner, ScanResult
from forgemaster.vram import GPUProfile, VRAMCalculator, VRAMEstimate


__all__ = [
    "Catalog",
    "CleanupAction",
    "CleanupReport",
    "Config",
    "DiskScanner",
    "DiskUsage",
    "DownloadConfig",
    "DownloadError",
    "DownloadProgress",
    "DownloadStatus",
    "DuplicateFinder",
    "DuplicateGroup",
    "GPUInfo",
    "GPUMonitor",
    "GPUProcess",
    "GPUProfile",
    "ModelDownloader",
    "ModelInfo",
    "ModelScanner",
    "ScanResult",
    "VRAMCalculator",
    "VRAMEstimate",
    "configure_logging",
    "get_logger",
    "get_model_metadata",
    "load_config",
    "read_gguf_metadata",
    "read_hf_config",
    "read_safetensors_metadata",
    "save_config",
    "set_config_value",
]
