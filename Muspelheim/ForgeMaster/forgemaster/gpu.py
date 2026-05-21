"""GPU monitoring via nvidia-smi, rocm-smi, and system_profiler (Apple Silicon).

Provides GPUMonitor that tries multiple backends:
  1. NVIDIA via nvidia-smi (Linux/Windows with NVIDIA driver)
  2. AMD via rocm-smi (Linux with ROCm)
  3. Apple Silicon via system_profiler (macOS)

Each backend populates GPUInfo with as much data as it can provide.
When a backend is unavailable the monitor falls back gracefully without
crashing.
"""

from __future__ import annotations

import logging
import platform
import re
import subprocess
from dataclasses import dataclass


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
    gpu_type: str = ""  # "nvidia", "amd", "apple"

    @property
    def vram_total_gb(self) -> float:
        """Total VRAM in gigabytes (derived from ``vram_total_mb``)."""
        return round(self.vram_total_mb / 1024, 2)

    @property
    def vram_used_gb(self) -> float:
        """Used VRAM in gigabytes (derived from ``vram_used_mb``)."""
        return round(self.vram_used_mb / 1024, 2)

    @property
    def vram_free_gb(self) -> float:
        """Free VRAM in gigabytes (derived from ``vram_free_mb``)."""
        return round(self.vram_free_mb / 1024, 2)


@dataclass
class GPUProcess:
    """A process using GPU memory."""

    pid: int = 0
    name: str = ""
    gpu_memory_mb: int = 0

    @property
    def gpu_memory_gb(self) -> float:
        """GPU memory usage in gigabytes (derived from ``gpu_memory_mb``)."""
        return round(self.gpu_memory_mb / 1024, 2)


class GPUMonitor:
    """Monitor GPU status by parsing nvidia-smi, rocm-smi, or system_profiler output.

    Detection order:
      1. NVIDIA (nvidia-smi)
      2. AMD (rocm-smi)
      3. Apple Silicon (system_profiler on macOS)

    Falls back gracefully if no GPU is detected.
    """

    def __init__(self) -> None:
        """Initialise monitor with cached availability state cleared."""
        self._available: bool | None = None
        self._driver_version: str | None = None

    # ------------------------------------------------------------------
    # NVIDIA GPU detection
    # ------------------------------------------------------------------

    def is_available(self) -> bool:
        """Check if any GPU backend is available.

        Tries nvidia-smi first, then rocm-smi, then Apple Silicon detection.

        Returns:
            True if at least one GPU backend is detected, False otherwise.

        """
        if self._available is not None:
            return self._available

        if self._check_nvidia() or self._check_amd() or self._check_apple():
            self._available = True
        else:
            self._available = False

        if not self._available:
            logger.debug("No GPU detected by any backend")

        return self._available

    def _check_nvidia(self) -> bool:
        """Check if nvidia-smi is available and a GPU is detected."""
        try:
            result = subprocess.run(
                ["nvidia-smi", "--query-gpu=name", "--format=csv,noheader,nounits"],
                capture_output=True,
                text=True,
                timeout=10,
                check=False,
            )
            if result.returncode == 0 and result.stdout.strip():
                return True
            logger.debug("nvidia-smi returned no GPU data")
        except FileNotFoundError:
            logger.debug("nvidia-smi not found on PATH")
        except subprocess.TimeoutExpired:
            logger.debug("nvidia-smi timed out")
        except Exception as exc:
            logger.debug("nvidia-smi unavailable: %s", exc)
        return False

    def _check_amd(self) -> bool:
        """Check if rocm-smi is available and an AMD GPU is detected."""
        try:
            result = subprocess.run(
                ["rocm-smi", "--showproductname"],
                capture_output=True,
                text=True,
                timeout=10,
                check=False,
            )
            if result.returncode == 0 and result.stdout.strip():
                return True
        except FileNotFoundError:
            logger.debug("rocm-smi not found on PATH")
        except subprocess.TimeoutExpired:
            logger.debug("rocm-smi timed out")
        except Exception as exc:
            logger.debug("rocm-smi unavailable: %s", exc)
        return False

    def _check_apple(self) -> bool:
        """Check if this is macOS with Apple Silicon GPU."""
        if platform.system() != "Darwin":
            return False
        try:
            result = subprocess.run(
                ["system_profiler", "SPDisplaysDataType", "-json"],
                capture_output=True,
                text=True,
                timeout=15,
                check=False,
            )
            if result.returncode == 0 and "chipset" in result.stdout.lower():
                return True
            # Also accept if any GPU is listed in the output
            if result.returncode == 0 and "display" in result.stdout.lower():
                return True
        except FileNotFoundError:
            logger.debug("system_profiler not found")
        except subprocess.TimeoutExpired:
            logger.debug("system_profiler timed out")
        except Exception as exc:
            logger.debug("system_profiler unavailable: %s", exc)
        return False

    # ------------------------------------------------------------------
    # GPU info collection — tries all backends
    # ------------------------------------------------------------------

    def get_gpu_info(self) -> list[GPUInfo]:
        """Query GPU information from all available backends.

        Returns:
            List of GPUInfo objects, one per detected GPU.
            Returns empty list if no GPU backend is available.

        """
        gpus: list[GPUInfo] = []

        # Try NVIDIA first (richest data)
        nvidia_gpus = self._get_nvidia_gpu_info()
        if nvidia_gpus:
            gpus.extend(nvidia_gpus)

        # Try AMD if no NVIDIA GPUs found
        if not gpus:
            amd_gpus = self._get_amd_gpu_info()
            gpus.extend(amd_gpus)

        # Try Apple Silicon if nothing else found
        if not gpus:
            apple_gpus = self._get_apple_gpu_info()
            gpus.extend(apple_gpus)

        return gpus

    def get_gpu_processes(self) -> list[GPUProcess]:
        """Query GPU processes via nvidia-smi.

        Returns:
            List of GPUProcess objects representing processes using GPU memory.
            Returns empty list if nvidia-smi is unavailable.

        """
        if not self._check_nvidia():
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
                check=False,
            )
        except (subprocess.TimeoutExpired, FileNotFoundError):
            return []

        if result.returncode != 0:
            return []

        processes: list[GPUProcess] = []
        for raw_line in result.stdout.strip().splitlines():
            line = raw_line.strip()
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
                logger.warning("Failed to parse nvidia-smi process line: %s (%s)", line, exc)
                continue

        return processes

    def get_driver_version(self) -> str | None:
        """Get the GPU driver version.

        Returns:
            Driver version string, or None if unavailable.

        """
        gpus = self.get_gpu_info()
        if gpus and gpus[0].driver_version:
            return gpus[0].driver_version
        return None

    def get_fallback_message(self) -> str:
        """Return a user-friendly message when no NVIDIA GPU is detected.

        Checks for AMD or Apple Silicon availability and provides
        appropriate guidance.
        """
        if self._check_amd():
            return (
                "No NVIDIA GPU detected. An AMD GPU was found via rocm-smi. "
                "Use 'forgemaster gpu' to see AMD GPU details. "
                "For full NVIDIA support, install NVIDIA drivers."
            )
        if self._check_apple():
            return (
                "No NVIDIA GPU detected. Apple Silicon GPU detected. "
                "Use 'forgemaster gpu' to see Apple GPU details. "
                "NVIDIA-specific features (process monitoring) are not available "
                "on Apple Silicon."
            )
        return (
            "No GPU detected. Supported backends:\n"
            "  • NVIDIA: install nvidia-smi (NVIDIA driver)\n"
            "  • AMD: install rocm-smi (ROCm toolkit)\n"
            "  • Apple Silicon: runs on macOS automatically\n"
            "See https://github.com/nousresearch/yggdrasil for more info."
        )

    def refresh(self) -> None:
        """Force re-detection of GPU availability (e.g. after driver install)."""
        self._available = None
        self._driver_version = None

    # ------------------------------------------------------------------
    # NVIDIA backend
    # ------------------------------------------------------------------

    def _get_nvidia_gpu_info(self) -> list[GPUInfo]:
        """Query NVIDIA GPU information via nvidia-smi."""
        if not self._check_nvidia():
            return []

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
                check=False,
            )
        except (subprocess.TimeoutExpired, FileNotFoundError):
            return []

        if result.returncode != 0:
            return []

        gpus: list[GPUInfo] = []
        for raw_line in result.stdout.strip().splitlines():
            line = raw_line.strip()
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
                    gpu_type="nvidia",
                )
                gpus.append(gpu)
            except (ValueError, IndexError) as exc:
                logger.warning("Failed to parse nvidia-smi line: %s (%s)", line, exc)
                continue

        return gpus

    # ------------------------------------------------------------------
    # AMD backend (rocm-smi)
    # ------------------------------------------------------------------

    @staticmethod
    def _run_rocm_smi(*args: str) -> subprocess.CompletedProcess[str] | None:
        """Run a rocm-smi subcommand, returning None on failure."""
        try:
            return subprocess.run(
                ["rocm-smi", *args],
                capture_output=True,
                text=True,
                timeout=10,
                check=False,
            )
        except (subprocess.TimeoutExpired, FileNotFoundError):
            return None

    @staticmethod
    def _parse_amd_names(output: str) -> list[str]:
        """Extract GPU names from rocm-smi --showproductname output."""
        names: list[str] = []
        for line in output.strip().splitlines():
            match = re.search(r"(?:GPU\[\d+\]|card\d+)\s*:\s*(.+)", line)
            if match:
                names.append(match.group(1).strip())
        return names

    @staticmethod
    def _parse_amd_vram(output: str) -> tuple[list[int], list[int]]:
        """Extract (totals, useds) VRAM lists from rocm-smi --showmeminfo vram output."""
        totals: list[int] = []
        useds: list[int] = []
        for line in output.strip().splitlines():
            stripped = line.strip()
            total_m = re.search(r"Total VRAM.*?:\s*(\d+)\s*(?:MB|MIB)", stripped, re.IGNORECASE)
            if total_m:
                totals.append(int(total_m.group(1)))
            used_m = re.search(r"Used VRAM.*?:\s*(\d+)\s*(?:MB|MIB)", stripped, re.IGNORECASE)
            if used_m:
                useds.append(int(used_m.group(1)))
        return totals, useds

    @staticmethod
    def _parse_amd_utilization(output: str) -> list[int]:
        """Extract GPU utilization percentages from rocm-smi --showgpuuse output."""
        pcts: list[int] = []
        for line in output.strip().splitlines():
            match = re.search(r"(?:GPU\[\d+\]|card\d+).*?(\d+)%", line)
            if match:
                pcts.append(int(match.group(1)))
        return pcts

    @staticmethod
    def _parse_amd_temps(output: str) -> list[int]:
        """Extract temperatures from rocm-smi --showtemp output."""
        temps: list[int] = []
        for line in output.strip().splitlines():
            match = re.search(r"(\d+)\s*°?[cC]", line)
            if match:
                temps.append(int(match.group(1)))
        return temps

    def _get_amd_gpu_info(self) -> list[GPUInfo]:
        r"""Query AMD GPU information via rocm-smi.

        rocm-smi output format (--showproductname):
            GPU[0]\t\t: gfx900
            ...
        rocm-smi output format (--showmeminfo vram):
            Total VRAM: xxxxx MB
            Used VRAM: xxxxx MB
        """
        if not self._check_amd():
            return []

        # Collect raw output from all rocm-smi subcommands
        name_result = self._run_rocm_smi("--showproductname")
        vram_result = self._run_rocm_smi("--showmeminfo", "vram")
        util_result = self._run_rocm_smi("--showgpuuse")
        temp_result = self._run_rocm_smi("--showtemp")

        if not any(
            r and r.returncode == 0 for r in (name_result, vram_result, util_result, temp_result)
        ):
            return []

        # Parse each subcommand's output
        gpu_names = (
            self._parse_amd_names(name_result.stdout)
            if name_result and name_result.returncode == 0
            else []
        )
        vram_totals, vram_useds = (
            self._parse_amd_vram(vram_result.stdout)
            if vram_result and vram_result.returncode == 0
            else ([], [])
        )
        util_pcts = (
            self._parse_amd_utilization(util_result.stdout)
            if util_result and util_result.returncode == 0
            else []
        )
        temps = (
            self._parse_amd_temps(temp_result.stdout)
            if temp_result and temp_result.returncode == 0
            else []
        )

        # Assemble GPUInfo objects
        gpus = self._assemble_amd_gpus(gpu_names, vram_totals, vram_useds, util_pcts, temps)

        # If we could detect AMD but parsing failed, return at least a placeholder
        if not gpus:
            gpus.append(GPUInfo(name="AMD GPU (details unavailable)", gpu_type="amd"))

        return gpus

    @staticmethod
    def _assemble_amd_gpus(
        names: list[str],
        vram_totals: list[int],
        vram_useds: list[int],
        util_pcts: list[int],
        temps: list[int],
    ) -> list[GPUInfo]:
        """Build GPUInfo list from parsed AMD telemetry data."""
        gpus: list[GPUInfo] = []
        gpu_count = max(len(names), len(vram_totals), 1)
        for i in range(gpu_count):
            vram_total = vram_totals[i] if i < len(vram_totals) else 0
            vram_used = vram_useds[i] if i < len(vram_useds) else 0
            gpus.append(
                GPUInfo(
                    name=names[i] if i < len(names) else f"AMD GPU {i}",
                    vram_total_mb=vram_total,
                    vram_used_mb=vram_used,
                    vram_free_mb=vram_total - vram_used,
                    temperature=temps[i] if i < len(temps) else 0,
                    utilization_pct=util_pcts[i] if i < len(util_pcts) else 0,
                    driver_version="",
                    gpu_type="amd",
                ),
            )
        return gpus

    # ------------------------------------------------------------------
    # Apple Silicon backend
    # ------------------------------------------------------------------

    def _get_apple_gpu_info(self) -> list[GPUInfo]:
        """Query Apple Silicon GPU information via system_profiler.

        On macOS, system_profiler SPDisplaysDataType -json returns JSON
        with GPU details including VRAM (shared memory for Apple Silicon).
        """
        if platform.system() != "Darwin":
            return []

        try:
            result = subprocess.run(
                ["system_profiler", "SPDisplaysDataType", "-json"],
                capture_output=True,
                text=True,
                timeout=15,
                check=False,
            )
        except (subprocess.TimeoutExpired, FileNotFoundError):
            return []

        if result.returncode != 0:
            return []

        import json

        gpus: list[GPUInfo] = []
        try:
            data = json.loads(result.stdout)
            displays_data = data.get("SPDisplaysDataType", [])
            if isinstance(displays_data, list):
                for entry in displays_data:
                    name = entry.get("spdisplays_ndrvs", entry.get("_name", "Apple Silicon GPU"))
                    # Apple Silicon uses unified memory; spdisplays_vram is a string
                    vram_str = entry.get("spdisplays_vram", "")
                    vram_total_mb = self._parse_vram_string(vram_str)

                    gpu = GPUInfo(
                        name=name,
                        vram_total_mb=vram_total_mb,
                        vram_used_mb=0,  # Not available via system_profiler
                        vram_free_mb=0,
                        temperature=0,
                        utilization_pct=0,
                        driver_version=entry.get("spdisplays_gmux-version", ""),
                        gpu_type="apple",
                    )
                    gpus.append(gpu)
        except (json.JSONDecodeError, KeyError) as exc:
            logger.warning("Failed to parse system_profiler output: %s", exc)

        # Fallback: if JSON parsing fails, try plain text
        if not gpus and result.stdout:
            for line in result.stdout.splitlines():
                # Look for "Chipset Model: Apple M1 Pro" etc.
                chipset_match = re.search(r"Chipset Model:\s*(.+)", line)
                if chipset_match:
                    gpus.append(
                        GPUInfo(
                            name=chipset_match.group(1).strip(),
                            gpu_type="apple",
                        ),
                    )

        return gpus

    @staticmethod
    def _parse_vram_string(vram_str: str) -> int:
        """Parse a VRAM string like '16 GB' or '16384 MB' into MB."""
        if not vram_str:
            return 0
        vram_str = vram_str.strip().upper()
        # Match patterns like "16 GB", "16384 MB", "16GB"
        gb_match = re.search(r"(\d+(?:\.\d+)?)\s*GB", vram_str)
        if gb_match:
            return int(float(gb_match.group(1)) * 1024)
        mb_match = re.search(r"(\d+(?:\.\d+)?)\s*MB", vram_str)
        if mb_match:
            return int(float(mb_match.group(1)))
        # Just a number, assume MB
        num_match = re.search(r"(\d+)", vram_str)
        if num_match:
            return int(num_match.group(1))
        return 0
