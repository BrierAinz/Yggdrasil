"""System health monitoring – CPU, RAM, GPU, disk, and Python processes."""

from __future__ import annotations

import logging
import subprocess
from dataclasses import dataclass, field
from typing import Any

import psutil


logger = logging.getLogger(__name__)


@dataclass
class GPUInfo:
    """Information about a single GPU device."""

    name: str = "N/A"
    utilization_pct: float = 0.0
    memory_total_mb: float = 0.0
    memory_used_mb: float = 0.0
    memory_free_mb: float = 0.0
    temperature_c: float = 0.0
    fan_speed_pct: float = 0.0
    power_draw_w: float = 0.0
    power_limit_w: float = 0.0

    @property
    def memory_util_pct(self) -> float:
        """Return memory utilization as percentage."""
        if self.memory_total_mb <= 0:
            return 0.0
        return (self.memory_used_mb / self.memory_total_mb) * 100.0

    def to_dict(self) -> dict[str, Any]:
        """Serializar información de GPU como diccionario.

        Returns:
            Dictionary with GPU name, utilization, memory, temperature, and power.
        """
        return {
            "name": self.name,
            "utilization_pct": self.utilization_pct,
            "memory_total_mb": self.memory_total_mb,
            "memory_used_mb": self.memory_used_mb,
            "memory_free_mb": self.memory_free_mb,
            "memory_util_pct": self.memory_util_pct,
            "temperature_c": self.temperature_c,
            "fan_speed_pct": self.fan_speed_pct,
            "power_draw_w": self.power_draw_w,
            "power_limit_w": self.power_limit_w,
        }


@dataclass
class SystemHealth:
    """Complete system health snapshot."""

    cpu_pct: float = 0.0
    cpu_per_core: list[float] = field(default_factory=list)
    cpu_freq_mhz: float = 0.0
    ram_total_gb: float = 0.0
    ram_used_gb: float = 0.0
    ram_available_gb: float = 0.0
    ram_pct: float = 0.0
    swap_total_gb: float = 0.0
    swap_used_gb: float = 0.0
    swap_pct: float = 0.0
    disk_total_gb: float = 0.0
    disk_used_gb: float = 0.0
    disk_free_gb: float = 0.0
    disk_pct: float = 0.0
    disk_path: str = "/"
    gpus: list[GPUInfo] = field(default_factory=list)
    python_process_count: int = 0
    python_processes: list[dict[str, Any]] = field(default_factory=list)
    uptime_seconds: float = 0.0
    load_avg_1m: float = 0.0
    load_avg_5m: float = 0.0
    load_avg_15m: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        """Serializar snapshot de salud del sistema como diccionario.

        Returns:
            Dictionary with all SystemHealth fields including nested GPU info.
        """
        return {
            "cpu_pct": self.cpu_pct,
            "cpu_per_core": self.cpu_per_core,
            "cpu_freq_mhz": self.cpu_freq_mhz,
            "ram_total_gb": self.ram_total_gb,
            "ram_used_gb": self.ram_used_gb,
            "ram_available_gb": self.ram_available_gb,
            "ram_pct": self.ram_pct,
            "swap_total_gb": self.swap_total_gb,
            "swap_used_gb": self.swap_used_gb,
            "swap_pct": self.swap_pct,
            "disk_total_gb": self.disk_total_gb,
            "disk_used_gb": self.disk_used_gb,
            "disk_free_gb": self.disk_free_gb,
            "disk_pct": self.disk_pct,
            "disk_path": self.disk_path,
            "gpus": [g.to_dict() for g in self.gpus],
            "python_process_count": self.python_process_count,
            "python_processes": self.python_processes,
            "uptime_seconds": self.uptime_seconds,
            "load_avg_1m": self.load_avg_1m,
            "load_avg_5m": self.load_avg_5m,
            "load_avg_15m": self.load_avg_15m,
        }


class HealthMonitor:
    """Monitors system health using psutil and nvidia-smi."""

    def __init__(self, disk_path: str = "/", nvidia_smi_path: str = "nvidia-smi") -> None:
        """Initialize the health monitor.

        Args:
            disk_path: Filesystem path to monitor for disk usage.
            nvidia_smi_path: Path or command for nvidia-smi.
        """
        self.disk_path = disk_path
        self.nvidia_smi_path = nvidia_smi_path
        self._nvidia_available: bool | None = None

    def get_health(self) -> SystemHealth:
        """Collect a complete system health snapshot.

        Returns:
            SystemHealth with CPU, RAM, swap, disk, GPU, and process metrics.
        """
        cpu_pct = psutil.cpu_percent(interval=None)
        cpu_per_core = psutil.cpu_percent(interval=None, percpu=True)

        cpu_freq = psutil.cpu_freq()
        cpu_freq_mhz = cpu_freq.current if cpu_freq else 0.0

        mem = psutil.virtual_memory()
        ram_total_gb = mem.total / (1024**3)
        ram_used_gb = mem.used / (1024**3)
        ram_available_gb = mem.available / (1024**3)
        ram_pct = mem.percent

        swap = psutil.swap_memory()
        swap_total_gb = swap.total / (1024**3)
        swap_used_gb = swap.used / (1024**3)
        swap_pct = swap.percent

        try:
            disk = psutil.disk_usage(self.disk_path)
            disk_total_gb = disk.total / (1024**3)
            disk_used_gb = disk.used / (1024**3)
            disk_free_gb = disk.free / (1024**3)
            disk_pct = disk.percent
        except FileNotFoundError:
            disk_total_gb = disk_used_gb = disk_free_gb = disk_pct = 0.0

        gpus = self._get_gpu_info()

        python_procs = self._get_python_processes()

        uptime_seconds = psutil.boot_time() and (psutil.boot_time())

        try:
            load1, load5, load15 = psutil.getloadavg()
        except AttributeError:
            # Windows doesn't have getloadavg in older psutil
            load1 = load5 = load15 = 0.0

        import time

        uptime_seconds = time.time() - psutil.boot_time()

        return SystemHealth(
            cpu_pct=cpu_pct,
            cpu_per_core=cpu_per_core,
            cpu_freq_mhz=cpu_freq_mhz,
            ram_total_gb=round(ram_total_gb, 2),
            ram_used_gb=round(ram_used_gb, 2),
            ram_available_gb=round(ram_available_gb, 2),
            ram_pct=ram_pct,
            swap_total_gb=round(swap_total_gb, 2),
            swap_used_gb=round(swap_used_gb, 2),
            swap_pct=swap_pct,
            disk_total_gb=round(disk_total_gb, 2),
            disk_used_gb=round(disk_used_gb, 2),
            disk_free_gb=round(disk_free_gb, 2),
            disk_pct=disk_pct,
            disk_path=self.disk_path,
            gpus=gpus,
            python_process_count=len(python_procs),
            python_processes=python_procs,
            uptime_seconds=round(uptime_seconds, 1),
            load_avg_1m=round(load1, 2),
            load_avg_5m=round(load5, 2),
            load_avg_15m=round(load15, 2),
        )

    def _get_gpu_info(self) -> list[GPUInfo]:
        """Query nvidia-smi for GPU information.

        Returns:
            List of GPUInfo objects, or empty list if nvidia-smi unavailable.
        """
        if self._nvidia_available is False:
            return []

        try:
            result = subprocess.run(
                [
                    self.nvidia_smi_path,
                    "--query-gpu=name,utilization.gpu,memory.total,memory.used,"
                    "memory.free,temperature.gpu,fan.speed,power.draw,power.limit",
                    "--format=csv,noheader,nounits",
                ],
                capture_output=True,
                text=True,
                timeout=10,
            )
            if result.returncode != 0:
                self._nvidia_available = False
                return []

            self._nvidia_available = True
            gpus: list[GPUInfo] = []
            for line in result.stdout.strip().split("\n"):
                if not line.strip():
                    continue
                parts = [p.strip() for p in line.split(",")]
                if len(parts) < 9:
                    continue

                def safe_float(val: str) -> float:
                    try:
                        return float(val)
                    except (ValueError, TypeError):
                        return 0.0

                gpus.append(
                    GPUInfo(
                        name=parts[0],
                        utilization_pct=safe_float(parts[1]),
                        memory_total_mb=safe_float(parts[2]),
                        memory_used_mb=safe_float(parts[3]),
                        memory_free_mb=safe_float(parts[4]),
                        temperature_c=safe_float(parts[5]),
                        fan_speed_pct=safe_float(parts[6]),
                        power_draw_w=safe_float(parts[7]),
                        power_limit_w=safe_float(parts[8]),
                    )
                )
            return gpus

        except (subprocess.TimeoutExpired, FileNotFoundError, OSError) as exc:
            logger.debug("nvidia-smi not available: %s", exc)
            self._nvidia_available = False
            return []

    def _get_python_processes(self) -> list[dict[str, Any]]:
        """Get info about running Python processes.

        Returns:
            List of dicts with pid, name, cmdline, cpu_percent, memory_percent.
        """
        procs: list[dict[str, Any]] = []
        for proc in psutil.process_iter(
            ["pid", "name", "cmdline", "cpu_percent", "memory_percent"]
        ):
            try:
                info = proc.info
                name = info.get("name", "") or ""
                cmdline = info.get("cmdline", []) or []
                # Match python executables
                if name.lower().startswith("python") or (
                    cmdline and any("python" in str(c).lower() for c in cmdline)
                ):
                    cmd_str = " ".join(cmdline) if cmdline else name
                    # Truncate long command lines
                    if len(cmd_str) > 120:
                        cmd_str = cmd_str[:117] + "..."
                    procs.append(
                        {
                            "pid": info.get("pid", 0),
                            "name": name,
                            "command": cmd_str,
                            "cpu_pct": info.get("cpu_percent", 0.0) or 0.0,
                            "mem_pct": round(info.get("memory_percent", 0.0) or 0.0, 1),
                        }
                    )
            except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                continue
        # Sort by CPU usage descending
        procs.sort(key=lambda p: p["cpu_pct"], reverse=True)
        return procs

    @property
    def nvidia_available(self) -> bool | None:
        """Return whether nvidia-smi is available (None = not yet checked)."""
        return self._nvidia_available
