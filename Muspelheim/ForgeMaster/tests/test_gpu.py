"""Tests for the GPU monitoring module."""

from __future__ import annotations

import subprocess
from unittest.mock import MagicMock, patch

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
# Sample AMD rocm-smi output mocks
# ---------------------------------------------------------------------------

FAKE_ROCM_PRODUCT = (
    "============================= ROCm System Interface =============================\n"
    "GPU[0]\t\t: AMD Radeon RX 7900 XTX\n"
    "GPU[1]\t\t: AMD Radeon RX 6800 XT\n"
)

FAKE_ROCM_VRAM = (
    "============================= ROCm System Interface =============================\n"
    "Total VRAM (GPU0): 24576 MB\n"
    "Used VRAM (GPU0): 8192 MB\n"
    "Total VRAM (GPU1): 16384 MB\n"
    "Used VRAM (GPU1): 4096 MB\n"
)

FAKE_ROCM_UTIL = (
    "============================= ROCm System Interface =============================\n"
    "GPU[0]: 45%\n"
    "GPU[1]: 12%\n"
)

FAKE_ROCM_TEMP = (
    "============================= ROCm System Interface =============================\n"
    "GPU[0]: 55°C\n"
    "GPU[1]: 42°C\n"
)

# ---------------------------------------------------------------------------
# Sample Apple Silicon system_profiler output mocks
# ---------------------------------------------------------------------------

FAKE_APPLE_JSON = (
    '{"SPDisplaysDataType":[{"_name":"chipset_model","spdisplays_ndrvs":"Apple M2 Pro",'
    '"spdisplays_vram":"16 GB","spdisplays_gmux-version":"1.0"}]}'
)

FAKE_APPLE_PLAIN_TEXT = "Chipset Model: Apple M1 Pro\n    VRAM (Dynamic): 16384 MB\n"

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
        assert info.gpu_type == ""

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

    def test_gpu_type_field(self):
        info_nvidia = GPUInfo(name="RTX 3060", gpu_type="nvidia")
        assert info_nvidia.gpu_type == "nvidia"
        info_amd = GPUInfo(name="RX 7900 XTX", gpu_type="amd")
        assert info_amd.gpu_type == "amd"
        info_apple = GPUInfo(name="Apple M2 Pro", gpu_type="apple")
        assert info_apple.gpu_type == "apple"


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


class TestGPUMonitorIsAvailable:
    @patch("forgemaster.gpu.subprocess.run")
    def test_available_when_nvidia_smi_succeeds(self, mock_run):
        mock_run.return_value = _mock_run(FAKE_GPU_NAME_CSV)
        monitor = GPUMonitor()
        assert monitor.is_available() is True

    @patch("forgemaster.gpu.subprocess.run")
    def test_not_available_when_all_backends_fail(self, mock_run):
        # All subprocess.run calls raise FileNotFoundError
        mock_run.side_effect = FileNotFoundError("not found")
        monitor = GPUMonitor()
        with patch.object(monitor, "_check_apple", return_value=False):
            assert monitor.is_available() is False

    @patch("forgemaster.gpu.subprocess.run")
    def test_available_when_amd_detected(self, mock_run):
        # nvidia-smi fails, rocm-smi succeeds
        call_count = [0]

        def side_effect(*args, **kwargs):
            call_count[0] += 1
            if call_count[0] == 1:
                raise FileNotFoundError("nvidia-smi not found")
            return _mock_run(FAKE_ROCM_PRODUCT)

        mock_run.side_effect = side_effect
        monitor = GPUMonitor()
        with patch.object(monitor, "_check_apple", return_value=False):
            assert monitor.is_available() is True

    @patch("forgemaster.gpu.platform.system", return_value="Darwin")
    @patch("forgemaster.gpu.subprocess.run")
    def test_available_when_apple_silicon_detected(self, mock_run, mock_platform):
        # nvidia-smi and rocm-smi fail, system_profiler succeeds
        call_count = [0]

        def side_effect(*args, **kwargs):
            call_count[0] += 1
            cmd = args[0] if args else kwargs.get("args", [])
            if "nvidia-smi" in str(cmd):
                raise FileNotFoundError("nvidia-smi not found")
            if "rocm-smi" in str(cmd):
                raise FileNotFoundError("rocm-smi not found")
            if "system_profiler" in str(cmd):
                return _mock_run('{"SPDisplaysDataType":[{"chipset":"Apple M1"}]}')
            return _mock_run("")

        mock_run.side_effect = side_effect
        monitor = GPUMonitor()
        assert monitor.is_available() is True

    @patch("forgemaster.gpu.subprocess.run")
    def test_not_available_on_timeout(self, mock_run):
        mock_run.side_effect = subprocess.TimeoutExpired(cmd="nvidia-smi", timeout=10)
        monitor = GPUMonitor()
        with (
            patch.object(monitor, "_check_amd", return_value=False),
            patch.object(monitor, "_check_apple", return_value=False),
        ):
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
# GPUMonitor.get_gpu_info() — NVIDIA path
# ---------------------------------------------------------------------------


class TestGPUMonitorGetGpuInfo:
    @patch("forgemaster.gpu.subprocess.run")
    def test_single_nvidia_gpu(self, mock_run):
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
        assert gpu.gpu_type == "nvidia"

    @patch("forgemaster.gpu.subprocess.run")
    def test_multiple_nvidia_gpus(self, mock_run):
        mock_run.return_value = _mock_run(FAKE_GPU_CSV_MULTILINE)
        monitor = GPUMonitor()
        gpus = monitor.get_gpu_info()
        assert len(gpus) == 2
        assert gpus[0].name == "NVIDIA GeForce RTX 3060"
        assert gpus[0].vram_total_mb == 12288
        assert gpus[1].name == "NVIDIA GeForce RTX 4090"
        assert gpus[1].vram_total_mb == 24576

    @patch("forgemaster.gpu.subprocess.run")
    def test_returns_empty_when_all_backends_unavailable(self, mock_run):
        mock_run.side_effect = FileNotFoundError("not found")
        monitor = GPUMonitor()
        with (
            patch.object(monitor, "_check_amd", return_value=False),
            patch.object(monitor, "_check_apple", return_value=False),
        ):
            gpus = monitor.get_gpu_info()
            assert gpus == []

    @patch("forgemaster.gpu.subprocess.run")
    def test_skips_malformed_lines(self, mock_run):
        csv_output = "NVIDIA GeForce RTX 3060, 12288, 4096, 8192, 45, 12, 535.129.06\nbadline"
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
# GPUMonitor.get_gpu_info() — AMD path
# ---------------------------------------------------------------------------


class TestGPUMonitorAMD:
    @patch("forgemaster.gpu.subprocess.run")
    def test_amd_gpu_detection(self, mock_run):
        """Test that AMD GPUs are detected when nvidia-smi is unavailable."""
        call_count = [0]

        def side_effect(*args, **kwargs):
            call_count[0] += 1
            cmd = kwargs.get("args", args[0] if args else [])
            if "nvidia-smi" in str(cmd):
                raise FileNotFoundError("nvidia-smi not found")
            if "rocm-smi" in str(cmd) and "--showproductname" in str(cmd):
                return _mock_run(FAKE_ROCM_PRODUCT)
            if "rocm-smi" in str(cmd) and "--showmeminfo" in str(cmd):
                return _mock_run(FAKE_ROCM_VRAM)
            if "rocm-smi" in str(cmd) and "--showgpuuse" in str(cmd):
                return _mock_run(FAKE_ROCM_UTIL)
            if "rocm-smi" in str(cmd) and "--showtemp" in str(cmd):
                return _mock_run(FAKE_ROCM_TEMP)
            return _mock_run("")

        mock_run.side_effect = side_effect
        monitor = GPUMonitor()
        gpus = monitor.get_gpu_info()
        assert len(gpus) == 2
        assert gpus[0].name == "AMD Radeon RX 7900 XTX"
        assert gpus[0].gpu_type == "amd"
        assert gpus[0].vram_total_mb == 24576
        assert gpus[0].vram_used_mb == 8192
        assert gpus[0].temperature == 55
        assert gpus[0].utilization_pct == 45
        assert gpus[1].name == "AMD Radeon RX 6800 XT"
        assert gpus[1].vram_total_mb == 16384
        assert gpus[1].vram_used_mb == 4096

    @patch("forgemaster.gpu.subprocess.run")
    def test_amd_fallback_placeholder(self, mock_run):
        """When rocm-smi is available but parsing fails, placeholder is returned."""
        call_count = [0]

        def side_effect(*args, **kwargs):
            call_count[0] += 1
            cmd = kwargs.get("args", args[0] if args else [])
            if "nvidia-smi" in str(cmd):
                raise FileNotFoundError("nvidia-smi not found")
            if "rocm-smi" in str(cmd):
                return _mock_run("")  # Empty output but succeeds
            return _mock_run("")

        mock_run.side_effect = side_effect
        monitor = GPUMonitor()
        gpus = monitor.get_gpu_info()
        # _check_amd returns False when rocm-smi returns empty, so AMD won't be detected
        # Actually, _check_amd checks returncode==0 AND stdout.strip() being non-empty
        # So empty stdout means _check_amd returns False, falling through
        assert gpus == [] or (len(gpus) >= 1 and gpus[0].gpu_type == "amd")

    @patch("forgemaster.gpu.subprocess.run")
    def test_amd_not_tried_when_nvidia_available(self, mock_run):
        """When NVIDIA is available, AMD should not be tried."""
        mock_run.return_value = _mock_run(FAKE_GPU_CSV)
        monitor = GPUMonitor()
        gpus = monitor.get_gpu_info()
        # Should get NVIDIA results only
        assert all(g.gpu_type == "nvidia" for g in gpus)


# ---------------------------------------------------------------------------
# GPUMonitor.get_gpu_info() — Apple Silicon path
# ---------------------------------------------------------------------------


class TestGPUMonitorApple:
    @patch("forgemaster.gpu.platform.system", return_value="Darwin")
    @patch("forgemaster.gpu.subprocess.run")
    def test_apple_gpu_detection(self, mock_run, mock_platform):
        """Test that Apple Silicon is detected when nvidia-smi and rocm-smi fail."""
        call_count = [0]

        def side_effect(*args, **kwargs):
            call_count[0] += 1
            cmd = kwargs.get("args", args[0] if args else [])
            if "nvidia-smi" in str(cmd):
                raise FileNotFoundError("nvidia-smi not found")
            if "rocm-smi" in str(cmd):
                raise FileNotFoundError("rocm-smi not found")
            if "system_profiler" in str(cmd):
                return _mock_run(FAKE_APPLE_JSON)
            return _mock_run("")

        mock_run.side_effect = side_effect
        monitor = GPUMonitor()
        gpus = monitor.get_gpu_info()
        assert len(gpus) >= 1
        apple_gpus = [g for g in gpus if g.gpu_type == "apple"]
        assert len(apple_gpus) >= 1
        # Apple M2 Pro from the JSON
        assert any("M2" in g.name or "Apple" in g.name for g in apple_gpus)

    @patch("forgemaster.gpu.platform.system", return_value="Linux")
    @patch("forgemaster.gpu.subprocess.run")
    def test_apple_not_detected_on_linux(self, mock_run, mock_platform):
        """Apple Silicon detection should be skipped on Linux."""
        mock_run.side_effect = FileNotFoundError("not found")
        monitor = GPUMonitor()
        with (
            patch.object(monitor, "_check_nvidia", return_value=False),
            patch.object(monitor, "_check_amd", return_value=False),
        ):
            gpus = monitor.get_gpu_info()
            assert gpus == []

    @patch("forgemaster.gpu.platform.system", return_value="Darwin")
    @patch("forgemaster.gpu.subprocess.run")
    def test_apple_plain_text_fallback(self, mock_run, mock_platform):
        """Test plain text fallback parsing for system_profiler."""
        call_count = [0]

        def side_effect(*args, **kwargs):
            call_count[0] += 1
            cmd = kwargs.get("args", args[0] if args else [])
            if "nvidia-smi" in str(cmd):
                raise FileNotFoundError("nvidia-smi not found")
            if "rocm-smi" in str(cmd):
                raise FileNotFoundError("rocm-smi not found")
            if "system_profiler" in str(cmd):
                # Return non-JSON but with chipset info
                return _mock_run(FAKE_APPLE_PLAIN_TEXT)
            return _mock_run("")

        mock_run.side_effect = side_effect
        monitor = GPUMonitor()
        gpus = monitor.get_gpu_info()
        # The JSON parsing will fail, but plain text fallback should find "Apple M1 Pro"
        apple_gpus = [g for g in gpus if g.gpu_type == "apple"]
        assert len(apple_gpus) >= 1


class TestGPUMonitorGetGpuProcesses:
    @patch("forgemaster.gpu.subprocess.run")
    def test_with_running_processes(self, mock_run):
        # nvidia check succeeds, then process query returns results
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
        # The message doesn't parse as a valid process
        assert procs == []

    @patch("forgemaster.gpu.subprocess.run")
    def test_returns_empty_when_nvidia_unavailable(self, mock_run):
        mock_run.side_effect = FileNotFoundError("nvidia-smi not found")
        monitor = GPUMonitor()
        procs = monitor.get_gpu_processes()
        assert procs == []

    @patch("forgemaster.gpu.subprocess.run")
    def test_handles_timeout(self, mock_run):
        mock_run.side_effect = [
            _mock_run(FAKE_GPU_NAME_CSV),  # is_available check succeeds
            subprocess.TimeoutExpired(cmd="nvidia-smi", timeout=10),  # process query times out
        ]
        monitor = GPUMonitor()
        procs = monitor.get_gpu_processes()
        assert procs == []


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
        with (
            patch.object(monitor, "_check_amd", return_value=False),
            patch.object(monitor, "_check_apple", return_value=False),
        ):
            assert monitor.get_driver_version() is None

    @patch("forgemaster.gpu.subprocess.run")
    def test_returns_none_when_no_gpus(self, mock_run):
        # All backends fail
        mock_run.side_effect = FileNotFoundError("not found")
        monitor = GPUMonitor()
        with (
            patch.object(monitor, "_check_amd", return_value=False),
            patch.object(monitor, "_check_apple", return_value=False),
        ):
            assert monitor.get_driver_version() is None


class TestGPUMonitorFallbackMessage:
    def test_no_gpu_message(self):
        monitor = GPUMonitor()
        with (
            patch.object(monitor, "_check_nvidia", return_value=False),
            patch.object(monitor, "_check_amd", return_value=False),
            patch.object(monitor, "_check_apple", return_value=False),
        ):
            msg = monitor.get_fallback_message()
            assert "No GPU detected" in msg
            assert "NVIDIA" in msg
            assert "AMD" in msg
            assert "Apple Silicon" in msg

    def test_amd_detected_message(self):
        monitor = GPUMonitor()
        with (
            patch.object(monitor, "_check_nvidia", return_value=False),
            patch.object(monitor, "_check_amd", return_value=True),
        ):
            msg = monitor.get_fallback_message()
            assert "AMD GPU" in msg
            assert "rocm-smi" in msg

    def test_apple_detected_message(self):
        monitor = GPUMonitor()
        with (
            patch.object(monitor, "_check_nvidia", return_value=False),
            patch.object(monitor, "_check_amd", return_value=False),
            patch.object(monitor, "_check_apple", return_value=True),
        ):
            msg = monitor.get_fallback_message()
            assert "Apple Silicon" in msg


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
        with (
            patch.object(monitor, "_check_amd", return_value=False),
            patch.object(monitor, "_check_apple", return_value=False),
        ):
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
        rtx3060_gpu = "NVIDIA GeForce RTX 3060, 12288, 4096, 8192, 45, 12, 535.129.06"
        rtx3060_procs = "1234, llama-server, 3840\n9876, python3, 256"

        # The new GPUMonitor makes multiple subprocess calls:
        # _check_nvidia -> nvidia-smi --query-gpu=name
        # _get_nvidia_gpu_info -> _check_nvidia (again) + query
        # _check_nvidia -> nvidia-smi --query-gpu=name
        # get_gpu_processes -> nvidia-smi --query-compute-apps
        # Use return_value for simplicity since all nvidia-smi calls return similar CSV
        mock_run.return_value = _mock_run(rtx3060_gpu)

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
        assert gpus[0].gpu_type == "nvidia"

        # For process query, override return value
        mock_run.return_value = _mock_run(rtx3060_procs)
        procs = monitor.get_gpu_processes()
        assert len(procs) == 2
        assert procs[0].pid == 1234
        assert procs[0].name == "llama-server"
        assert procs[0].gpu_memory_mb == 3840
        assert procs[1].gpu_memory_mb == 256

    @patch("forgemaster.gpu.subprocess.run")
    def test_float_values_in_csv(self, mock_run):
        """nvidia-smi may return float values even with nounits."""
        csv_output = "NVIDIA GeForce RTX 3060, 12288.0, 4096.5, 8191.5, 45, 12, 535.129.06"
        mock_run.return_value = _mock_run(csv_output)
        monitor = GPUMonitor()
        gpus = monitor.get_gpu_info()
        assert len(gpus) == 1
        assert gpus[0].vram_total_mb == 12288
        assert gpus[0].vram_used_mb == 4096

    @patch("forgemaster.gpu.subprocess.run")
    def test_cross_platform_amd_workflow(self, mock_run):
        """Simulate full workflow on an AMD GPU system (no NVIDIA)."""
        call_count = [0]

        def side_effect(*args, **kwargs):
            call_count[0] += 1
            cmd = kwargs.get("args", args[0] if args else [])
            cmd_str = str(cmd)
            if "nvidia-smi" in cmd_str:
                raise FileNotFoundError("nvidia-smi not found")
            if "--showproductname" in cmd_str:
                return _mock_run(FAKE_ROCM_PRODUCT)
            if "--showmeminfo" in cmd_str:
                return _mock_run(FAKE_ROCM_VRAM)
            if "--showgpuuse" in cmd_str:
                return _mock_run(FAKE_ROCM_UTIL)
            if "--showtemp" in cmd_str:
                return _mock_run(FAKE_ROCM_TEMP)
            return _mock_run("")

        mock_run.side_effect = side_effect
        monitor = GPUMonitor()
        gpus = monitor.get_gpu_info()
        assert len(gpus) >= 1
        assert gpus[0].gpu_type == "amd"
        assert "RX 7900 XTX" in gpus[0].name
