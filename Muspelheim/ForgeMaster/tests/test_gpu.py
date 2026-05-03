"""Tests for the GPU monitoring module."""

from __future__ import annotations

import subprocess
from unittest.mock import MagicMock, patch

import pytest

from forgemaster.gpu import GPUInfo, GPUMonitor, GPUProcess

# ---------------------------------------------------------------------------
# Sample nvidia-smi output mocks
# ---------------------------------------------------------------------------

FAKE_GPU_CSV = "NVIDIA GeForce RTX 3060, 12288, 4096, 8192, 45, 12, 535.129.06"

FAKE_GPU_CSV_MULTILINE = (
    "NVIDIA GeForce RTX 3060, 12288, 4096, 8192, 45, 12, 535.129.06\n"
    "NVIDIA GeForce RTX 4090, 24576, 8192, 16384, 55, 30, 535.129.06"
)

FAKE_GPU_CSV_NOHEADER = "NVIDIA GeForce RTX 3060, 12288, 4096, 8192, 45, 12, 535.129.06"

FAKE_PROCESS_CSV = "1234, python3, 2048\n5678, llama.cpp, 4096"

FAKE_PROCESS_EMPTY = "No running compute processes found"

FAKE_GPU_NAME_CSV = "NVIDIA GeForce RTX 3060"

FAKE_GPU_NAME_MULTILINE = "NVIDIA GeForce RTX 3060\nNVIDIA GeForce RTX 4090"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _mock_run(stdout: str, returncode: int = 0):
    """Create a mock subprocess.run that returns the given stdout."""
    mock = MagicMock()
    mock.returncode = returncode
    mock.stdout = stdout
    mock.stderr = ""
    return mock


# ---------------------------------------------------------------------------
# GPUInfo tests
# ---------------------------------------------------------------------------


class TestGPUInfo:
    def test_defaults(self):
        info = GPUInfo()
        assert info.name == ""
        assert info.vram_total_mb == 0
        assert info.vram_used_mb == 0
        assert info.vram_free_mb == 0
        assert info.temperature == 0
        assert info.utilization_pct == 0
        assert info.driver_version == ""

    def test_vram_total_gb(self):
        info = GPUInfo(name="RTX 3060", vram_total_mb=12288)
        assert info.vram_total_gb == 12.0

    def test_vram_used_gb(self):
        info = GPUInfo(vram_used_mb=4096)
        assert info.vram_used_gb == 4.0

    def test_vram_free_gb(self):
        info = GPUInfo(vram_free_mb=8192)
        assert info.vram_free_gb == 8.0

    def test_partial_values(self):
        info = GPUInfo(
            name="RTX 3060",
            vram_total_mb=12288,
            vram_used_mb=4096,
            vram_free_mb=8192,
            temperature=45,
            utilization_pct=12,
            driver_version="535.129.06",
        )
        assert info.name == "RTX 3060"
        assert info.vram_total_mb == 12288
        assert info.vram_used_mb == 4096
        assert info.vram_free_mb == 8192
        assert info.temperature == 45
        assert info.utilization_pct == 12
        assert info.driver_version == "535.129.06"


# ---------------------------------------------------------------------------
# GPUProcess tests
# ---------------------------------------------------------------------------


class TestGPUProcess:
    def test_defaults(self):
        proc = GPUProcess()
        assert proc.pid == 0
        assert proc.name == ""
        assert proc.gpu_memory_mb == 0

    def test_gpu_memory_gb(self):
        proc = GPUProcess(pid=1234, name="python3", gpu_memory_mb=2048)
        assert proc.gpu_memory_gb == 2.0

    def test_full_values(self):
        proc = GPUProcess(pid=5678, name="llama.cpp", gpu_memory_mb=4096)
        assert proc.pid == 5678
        assert proc.name == "llama.cpp"
        assert proc.gpu_memory_mb == 4096
        assert proc.gpu_memory_gb == 4.0


# ---------------------------------------------------------------------------
# GPUMonitor.is_available()
# ---------------------------------------------------------------------------


class TestGPUMonitorIsAvailable:
    @patch("forgemaster.gpu.subprocess.run")
    def test_available_when_nvidia_smi_succeeds(self, mock_run):
        mock_run.return_value = _mock_run(FAKE_GPU_NAME_CSV)
        monitor = GPUMonitor()
        assert monitor.is_available() is True

    @patch("forgemaster.gpu.subprocess.run")
    def test_not_available_when_nvidia_smi_not_found(self, mock_run):
        mock_run.side_effect = FileNotFoundError("nvidia-smi not found")
        monitor = GPUMonitor()
        assert monitor.is_available() is False

    @patch("forgemaster.gpu.subprocess.run")
    def test_not_available_when_nvidia_smi_fails(self, mock_run):
        mock_run.return_value = _mock_run("", returncode=1)
        monitor = GPUMonitor()
        assert monitor.is_available() is False

    @patch("forgemaster.gpu.subprocess.run")
    def test_not_available_when_nvidia_smi_empty(self, mock_run):
        mock_run.return_value = _mock_run("")
        monitor = GPUMonitor()
        assert monitor.is_available() is False

    @patch("forgemaster.gpu.subprocess.run")
    def test_not_available_on_timeout(self, mock_run):
        mock_run.side_effect = subprocess.TimeoutExpired(cmd="nvidia-smi", timeout=10)
        monitor = GPUMonitor()
        assert monitor.is_available() is False

    @patch("forgemaster.gpu.subprocess.run")
    def test_caches_availability(self, mock_run):
        mock_run.return_value = _mock_run(FAKE_GPU_NAME_CSV)
        monitor = GPUMonitor()
        _ = monitor.is_available()
        _ = monitor.is_available()
        # subprocess.run should only be called once due to caching
        assert mock_run.call_count == 1

    @patch("forgemaster.gpu.subprocess.run")
    def test_refresh_clears_cache(self, mock_run):
        mock_run.return_value = _mock_run(FAKE_GPU_NAME_CSV)
        monitor = GPUMonitor()
        assert monitor.is_available() is True
        monitor.refresh()
        # After refresh, is_available should call nvidia-smi again
        assert monitor.is_available() is True
        assert mock_run.call_count == 2


# ---------------------------------------------------------------------------
# GPUMonitor.get_gpu_info()
# ---------------------------------------------------------------------------


class TestGPUMonitorGetGpuInfo:
    @patch("forgemaster.gpu.subprocess.run")
    def test_single_gpu(self, mock_run):
        # First call: is_available check
        # Second call: get_gpu_info query
        mock_run.return_value = _mock_run(FAKE_GPU_CSV)
        monitor = GPUMonitor()
        gpus = monitor.get_gpu_info()
        assert len(gpus) == 1
        gpu = gpus[0]
        assert gpu.name == "NVIDIA GeForce RTX 3060"
        assert gpu.vram_total_mb == 12288
        assert gpu.vram_used_mb == 4096
        assert gpu.vram_free_mb == 8192
        assert gpu.temperature == 45
        assert gpu.utilization_pct == 12
        assert gpu.driver_version == "535.129.06"

    @patch("forgemaster.gpu.subprocess.run")
    def test_multiple_gpus(self, mock_run):
        mock_run.return_value = _mock_run(FAKE_GPU_CSV_MULTILINE)
        monitor = GPUMonitor()
        gpus = monitor.get_gpu_info()
        assert len(gpus) == 2
        assert gpus[0].name == "NVIDIA GeForce RTX 3060"
        assert gpus[0].vram_total_mb == 12288
        assert gpus[1].name == "NVIDIA GeForce RTX 4090"
        assert gpus[1].vram_total_mb == 24576

    @patch("forgemaster.gpu.subprocess.run")
    def test_returns_empty_when_unavailable(self, mock_run):
        mock_run.side_effect = FileNotFoundError("nvidia-smi not found")
        monitor = GPUMonitor()
        gpus = monitor.get_gpu_info()
        assert gpus == []

    @patch("forgemaster.gpu.subprocess.run")
    def test_returns_empty_on_nonzero_returncode(self, mock_run):
        # is_available succeeds but get_gpu_info query fails
        # Setup: first call (is_available) succeeds, second call (get_gpu_info) fails
        mock_run.side_effect = [
            _mock_run(FAKE_GPU_NAME_CSV),  # is_available
            _mock_run("", returncode=1),  # get_gpu_info query
        ]
        monitor = GPUMonitor()
        gpus = monitor.get_gpu_info()
        assert gpus == []

    @patch("forgemaster.gpu.subprocess.run")
    def test_skips_malformed_lines(self, mock_run):
        csv_output = (
            "NVIDIA GeForce RTX 3060, 12288, 4096, 8192, 45, 12, 535.129.06\nbadline"
        )
        mock_run.return_value = _mock_run(csv_output)
        monitor = GPUMonitor()
        gpus = monitor.get_gpu_info()
        assert len(gpus) == 1
        assert gpus[0].name == "NVIDIA GeForce RTX 3060"

    @patch("forgemaster.gpu.subprocess.run")
    def test_handles_timeout(self, mock_run):
        mock_run.side_effect = [
            _mock_run(FAKE_GPU_NAME_CSV),  # is_available succeeds
            subprocess.TimeoutExpired(cmd="nvidia-smi", timeout=10),  # query times out
        ]
        monitor = GPUMonitor()
        gpus = monitor.get_gpu_info()
        assert gpus == []


# ---------------------------------------------------------------------------
# GPUMonitor.get_gpu_processes()
# ---------------------------------------------------------------------------


class TestGPUMonitorGetGpuProcesses:
    @patch("forgemaster.gpu.subprocess.run")
    def test_with_running_processes(self, mock_run):
        # is_available succeeds, then process query returns results
        mock_run.return_value = _mock_run(FAKE_PROCESS_CSV)
        monitor = GPUMonitor()
        procs = monitor.get_gpu_processes()
        assert len(procs) == 2
        assert procs[0].pid == 1234
        assert procs[0].name == "python3"
        assert procs[0].gpu_memory_mb == 2048
        assert procs[1].pid == 5678
        assert procs[1].name == "llama.cpp"
        assert procs[1].gpu_memory_mb == 4096

    @patch("forgemaster.gpu.subprocess.run")
    def test_no_processes(self, mock_run):
        # nvidia-smi returns empty output for processes
        mock_run.return_value = _mock_run("")
        monitor = GPUMonitor()
        procs = monitor.get_gpu_processes()
        assert procs == []

    @patch("forgemaster.gpu.subprocess.run")
    def test_no_running_compute_message(self, mock_run):
        # nvidia-smi sometimes prints a "No running compute processes" message
        mock_run.return_value = _mock_run(FAKE_PROCESS_EMPTY)
        monitor = GPUMonitor()
        procs = monitor.get_gpu_processes()
        # The message doesn't parse as a valid process (not enough fields or non-int PID)
        assert procs == []

    @patch("forgemaster.gpu.subprocess.run")
    def test_returns_empty_when_unavailable(self, mock_run):
        mock_run.side_effect = FileNotFoundError("nvidia-smi not found")
        monitor = GPUMonitor()
        procs = monitor.get_gpu_processes()
        assert procs == []

    @patch("forgemaster.gpu.subprocess.run")
    def test_handles_timeout(self, mock_run):
        mock_run.side_effect = [
            _mock_run(FAKE_GPU_NAME_CSV),  # is_available succeeds
            subprocess.TimeoutExpired(cmd="nvidia-smi", timeout=10),  # query times out
        ]
        monitor = GPUMonitor()
        procs = monitor.get_gpu_processes()
        assert procs == []


# ---------------------------------------------------------------------------
# GPUMonitor.get_driver_version()
# ---------------------------------------------------------------------------


class TestGPUMonitorGetDriverVersion:
    @patch("forgemaster.gpu.subprocess.run")
    def test_returns_driver_version(self, mock_run):
        mock_run.return_value = _mock_run(FAKE_GPU_CSV)
        monitor = GPUMonitor()
        version = monitor.get_driver_version()
        assert version == "535.129.06"

    @patch("forgemaster.gpu.subprocess.run")
    def test_returns_none_when_unavailable(self, mock_run):
        mock_run.side_effect = FileNotFoundError("nvidia-smi not found")
        monitor = GPUMonitor()
        assert monitor.get_driver_version() is None

    @patch("forgemaster.gpu.subprocess.run")
    def test_returns_none_when_no_gpus(self, mock_run):
        # is_available succeeds but no GPU data returned
        mock_run.side_effect = [
            _mock_run(FAKE_GPU_NAME_CSV, returncode=1),  # is_available fails
        ]
        monitor = GPUMonitor()
        assert monitor.get_driver_version() is None


# ---------------------------------------------------------------------------
# GPUMonitor.refresh()
# ---------------------------------------------------------------------------


class TestGPUMonitorRefresh:
    @patch("forgemaster.gpu.subprocess.run")
    def test_refresh_resets_cache(self, mock_run):
        mock_run.return_value = _mock_run(FAKE_GPU_NAME_CSV)
        monitor = GPUMonitor()
        assert monitor.is_available() is True
        monitor.refresh()
        # After refresh, _available should be None
        assert monitor._available is None
        # Re-check triggers a new subprocess call
        assert monitor.is_available() is True
        assert mock_run.call_count == 2

    @patch("forgemaster.gpu.subprocess.run")
    def test_refresh_allows_re_detection(self, mock_run):
        # First: nvidia-smi missing; after refresh: it's available
        call_count = [0]

        def side_effect(*args, **kwargs):
            call_count[0] += 1
            if call_count[0] == 1:
                raise FileNotFoundError("nvidia-smi not found")
            return _mock_run(FAKE_GPU_NAME_CSV)

        mock_run.side_effect = side_effect
        monitor = GPUMonitor()
        assert monitor.is_available() is False
        monitor.refresh()
        assert monitor.is_available() is True


# ---------------------------------------------------------------------------
# Integration-style: GPUMonitor with real-ish nvidia-smi output
# ---------------------------------------------------------------------------


class TestGPUMonitorIntegration:
    @patch("forgemaster.gpu.subprocess.run")
    def test_full_workflow_rtx_3060(self, mock_run):
        """Simulate full workflow on an RTX 3060 12GB."""
        # Sequence of calls:
        # 1. is_available (for get_gpu_info)
        # 2. get_gpu_info query
        # 3. (cached is_available) for get_gpu_processes
        # 4. get_gpu_processes query
        rtx3060_gpu = "NVIDIA GeForce RTX 3060, 12288, 4096, 8192, 45, 12, 535.129.06"
        rtx3060_procs = "1234, llama-server, 3840\n9876, python3, 256"

        mock_run.side_effect = [
            _mock_run(FAKE_GPU_NAME_CSV),  # is_available
            _mock_run(rtx3060_gpu),  # get_gpu_info
            # is_available is cached now
            _mock_run(rtx3060_procs),  # get_gpu_processes
        ]

        monitor = GPUMonitor()
        assert monitor.is_available() is True

        gpus = monitor.get_gpu_info()
        assert len(gpus) == 1
        assert gpus[0].name == "NVIDIA GeForce RTX 3060"
        assert gpus[0].vram_total_mb == 12288
        assert gpus[0].vram_total_gb == 12.0
        assert gpus[0].vram_used_mb == 4096
        assert gpus[0].vram_free_mb == 8192
        assert gpus[0].temperature == 45
        assert gpus[0].utilization_pct == 12

        procs = monitor.get_gpu_processes()
        assert len(procs) == 2
        assert procs[0].pid == 1234
        assert procs[0].name == "llama-server"
        assert procs[0].gpu_memory_mb == 3840
        assert procs[1].gpu_memory_mb == 256

    @patch("forgemaster.gpu.subprocess.run")
    def test_float_values_in_csv(self, mock_run):
        """nvidia-smi may return float values even with nounits."""
        csv_output = (
            "NVIDIA GeForce RTX 3060, 12288.0, 4096.5, 8191.5, 45, 12, 535.129.06"
        )
        mock_run.return_value = _mock_run(csv_output)
        monitor = GPUMonitor()
        gpus = monitor.get_gpu_info()
        assert len(gpus) == 1
        assert gpus[0].vram_total_mb == 12288
        assert gpus[0].vram_used_mb == 4096
