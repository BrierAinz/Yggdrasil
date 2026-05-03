"""GPU monitoring via nvidia-smi subprocess."""

from __future__ import annotations

import logging
import re
import subprocess
from dataclasses import dataclass
from typing import Optional

logger = logging.getLogger(__name__)


@dataclass
class GPUInfo:
    """Information about a single GPU."""

    name: str = ""
    vram_total_mb: int = 0
    vram_used_mb: int = 0
    vram_free_mb: int = 0
    temperature: int = 0
    utilization_pct: int = 0
    driver_version: str = ""

    @property
    def vram_total_gb(self) -> float:
        return round(self.vram_total_mb / 1024, 2)

    @property
    def vram_used_gb(self) -> float:
        return round(self.vram_used_mb / 1024, 2)

    @property
    def vram_free_gb(self) -> float:
        return round(self.vram_free_mb / 1024, 2)


@dataclass
class GPUProcess:
    """A process using GPU memory."""

    pid: int = 0
    name: str = ""
    gpu_memory_mb: int = 0

    @property
    def gpu_memory_gb(self) -> float:
        return round(self.gpu_memory_mb / 1024, 2)


class GPUMonitor:
    """Monitor GPU status by parsing nvidia-smi output."""

    def __init__(self) -> None:
        self._available: Optional[bool] = None
        self._driver_version: Optional[str] = None

    def is_available(self) -> bool:
        """Check if nvidia-smi is available and a GPU is detected.

        Returns:
            True if nvidia-smi runs successfully, False otherwise.
        """
        if self._available is not None:
            return self._available

        try:
            result = subprocess.run(
                ["nvidia-smi", "--query-gpu=name", "--format=csv,noheader,nounits"],
                capture_output=True,
                text=True,
                timeout=10,
            )
            self._available = result.returncode == 0 and bool(result.stdout.strip())
            if not self._available:
                logger.debug("nvidia-smi returned no GPU data")
        except FileNotFoundError:
            logger.debug("nvidia-smi not found on PATH")
            self._available = False
        except subprocess.TimeoutExpired:
            logger.debug("nvidia-smi timed out")
            self._available = False
        except Exception as exc:
            logger.debug("nvidia-smi unavailable: %s", exc)
            self._available = False

        return self._available

    def get_gpu_info(self) -> list[GPUInfo]:
        """Query GPU information via nvidia-smi.

        Returns:
            List of GPUInfo objects, one per detected GPU.
            Returns empty list if nvidia-smi is unavailable.
        """
        if not self.is_available():
            return []

        # Query multiple GPU properties at once
        query_fields = (
            "name,memory.total,memory.used,memory.free,"
            "temperature.gpu,utilization.gpu,driver_version"
        )
        try:
            result = subprocess.run(
                [
                    "nvidia-smi",
                    f"--query-gpu={query_fields}",
                    "--format=csv,noheader,nounits",
                ],
                capture_output=True,
                text=True,
                timeout=10,
            )
        except (subprocess.TimeoutExpired, FileNotFoundError):
            return []

        if result.returncode != 0:
            return []

        gpus: list[GPUInfo] = []
        for line in result.stdout.strip().splitlines():
            line = line.strip()
            if not line:
                continue
            parts = [p.strip() for p in line.split(",")]
            if len(parts) < 7:
                continue

            try:
                gpu = GPUInfo(
                    name=parts[0],
                    vram_total_mb=int(float(parts[1])),
                    vram_used_mb=int(float(parts[2])),
                    vram_free_mb=int(float(parts[3])),
                    temperature=int(float(parts[4])),
                    utilization_pct=int(float(parts[5])),
                    driver_version=parts[6],
                )
                gpus.append(gpu)
            except (ValueError, IndexError) as exc:
                logger.warning("Failed to parse nvidia-smi line: %s (%s)", line, exc)
                continue

        return gpus

    def get_gpu_processes(self) -> list[GPUProcess]:
        """Query GPU processes via nvidia-smi.

        Returns:
            List of GPUProcess objects representing processes using GPU memory.
            Returns empty list if nvidia-smi is unavailable.
        """
        if not self.is_available():
            return []

        try:
            result = subprocess.run(
                [
                    "nvidia-smi",
                    "--query-compute-apps=pid,process_name,used_gpu_memory",
                    "--format=csv,noheader,nounits",
                ],
                capture_output=True,
                text=True,
                timeout=10,
            )
        except (subprocess.TimeoutExpired, FileNotFoundError):
            return []

        if result.returncode != 0:
            return []

        processes: list[GPUProcess] = []
        for line in result.stdout.strip().splitlines():
            line = line.strip()
            if not line:
                continue
            parts = [p.strip() for p in line.split(",")]
            if len(parts) < 3:
                # Sometimes nvidia-smi returns "No running compute processes found"
                continue

            try:
                proc = GPUProcess(
                    pid=int(parts[0]),
                    name=parts[1],
                    gpu_memory_mb=int(float(parts[2])),
                )
                processes.append(proc)
            except (ValueError, IndexError) as exc:
                logger.warning(
                    "Failed to parse nvidia-smi process line: %s (%s)", line, exc
                )
                continue

        return processes

    def get_driver_version(self) -> Optional[str]:
        """Get the NVIDIA driver version.

        Returns:
            Driver version string, or None if unavailable.
        """
        if not self.is_available():
            return None

        gpus = self.get_gpu_info()
        if gpus:
            return gpus[0].driver_version
        return None

    def refresh(self) -> None:
        """Force re-detection of GPU availability (e.g. after driver install)."""
        self._available = None
        self._driver_version = None
