"""ForgeMaster — Niflheim resource manager for LLM models, VRAM, and disk."""

__version__ = "0.1.0"

from forgemaster.catalog import Catalog
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
from forgemaster.scanner import ModelInfo, ModelScanner, ScanResult
from forgemaster.vram import GPUProfile, VRAMCalculator, VRAMEstimate

__all__ = [
    "ModelScanner",
    "ModelInfo",
    "ScanResult",
    "Catalog",
    "VRAMCalculator",
    "GPUProfile",
    "VRAMEstimate",
    "DiskScanner",
    "DuplicateFinder",
    "DiskUsage",
    "DuplicateGroup",
    "CleanupAction",
    "CleanupReport",
    "GPUMonitor",
    "GPUInfo",
    "GPUProcess",
    "ModelDownloader",
    "DownloadProgress",
    "DownloadConfig",
    "DownloadStatus",
    "DownloadError",
]
