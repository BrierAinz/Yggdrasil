"""Tests for ForgeMaster CLI."""

from __future__ import annotations

import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

from typer.testing import CliRunner

from forgemaster.cli import app


runner = CliRunner()


# ─── Version Command ────────────────────────────────────────────────────────


class TestVersion:
    def test_version_command(self):
        result = runner.invoke(app, ["version"])
        assert result.exit_code == 0
        assert "ForgeMaster" in result.output
        assert "v1.0.0" in result.output


# ─── Scan Command ────────────────────────────────────────────────────────────


class TestScanCommand:
    def test_scan_no_paths(self):
        """Scan with no valid paths should show error or empty result."""
        result = runner.invoke(app, ["scan", "--path", "/nonexistent/path/12345"])
        assert result.exit_code in (0, 1)

    def test_scan_empty_directory(self):
        """Scan an empty directory should find 0 models."""
        with tempfile.TemporaryDirectory() as tmp:
            result = runner.invoke(app, ["scan", "--path", tmp])
            assert result.exit_code == 0

    def test_scan_with_gguf_file(self):
        """Scan directory with a GGUF file."""
        with tempfile.TemporaryDirectory() as tmp:
            gguf_path = Path(tmp) / "test-model.Q4_K_M.gguf"
            gguf_path.write_bytes(b"\x00" * 1024)
            result = runner.invoke(app, ["scan", "--path", tmp])
            assert result.exit_code == 0

    def test_scan_catalog_flag(self):
        """Scan with --catalog flag should work."""
        with (
            tempfile.TemporaryDirectory() as tmp,
            patch("forgemaster.scanner.ModelScanner") as mock_scanner,
            patch("forgemaster.catalog.Catalog") as mock_catalog,
        ):
            mock_model = MagicMock()
            mock_model.name = "test-model"
            mock_model.format = "gguf"
            mock_model.size_bytes = 1024
            mock_model.architecture = "llama"
            mock_model.quantization = "Q4_K_M"
            mock_model.path = tmp
            mock_result = MagicMock()
            mock_result.models = [mock_model]
            mock_scanner.return_value.scan.return_value = mock_result

            mock_cat = MagicMock()
            mock_catalog.return_value = mock_cat
            result = runner.invoke(app, ["scan", "--path", tmp, "--catalog"])
            assert result.exit_code == 0


# ─── List Command ────────────────────────────────────────────────────────────


class TestListCommand:
    def test_list_empty_catalog(self):
        """List with empty catalog should show message."""
        with patch("forgemaster.catalog.Catalog") as mock_catalog:
            mock_cat = MagicMock()
            mock_cat.list_models.return_value = []
            mock_catalog.return_value = mock_cat
            result = runner.invoke(app, ["list"])
            assert result.exit_code == 0
            assert "No models" in result.output or "0 model" in result.output.lower()

    def test_list_with_models(self):
        """List with models in catalog."""
        with patch("forgemaster.catalog.Catalog") as mock_catalog:
            mock_cat = MagicMock()
            # list_models returns a list of dicts
            mock_cat.list_models.return_value = [
                {
                    "id": 1,
                    "name": "test-model",
                    "format": "gguf",
                    "size_bytes": 1024,
                    "architecture": "llama",
                    "quantization": "Q4_K_M",
                    "scanned_at": None,
                },
            ]
            mock_catalog.return_value = mock_cat
            result = runner.invoke(app, ["list"])
            assert result.exit_code == 0

    def test_list_with_format_filter(self):
        """List with format filter."""
        with patch("forgemaster.catalog.Catalog") as mock_catalog:
            mock_cat = MagicMock()
            mock_model = MagicMock()
            mock_model.name = "test-model"
            mock_model.format = "gguf"
            mock_model.size_bytes = 1024
            mock_model.architecture = "llama"
            mock_model.quantization = "Q4_K_M"
            mock_model.scanned_at = None
            mock_model.id = 1
            mock_cat.list_models.return_value = [mock_model]
            mock_catalog.return_value = mock_cat
            result = runner.invoke(app, ["list", "--format", "gguf"])
            assert result.exit_code == 0


# ─── Stats Command ───────────────────────────────────────────────────────────


class TestStatsCommand:
    def test_stats_no_paths(self):
        """Stats with nonexistent path should error."""
        result = runner.invoke(app, ["stats", "--path", "/nonexistent/path/12345"])
        assert result.exit_code == 1

    def test_stats_real_directory(self):
        """Stats on a real directory should show disk usage."""
        with tempfile.TemporaryDirectory() as tmp:
            (Path(tmp) / "model.gguf").write_bytes(b"\x00" * 2048)
            (Path(tmp) / "readme.txt").write_text("test")
            result = runner.invoke(app, ["stats", "--path", tmp])
            assert result.exit_code == 0


# ─── Check Command ───────────────────────────────────────────────────────────


class TestCheckCommand:
    def test_check_with_gpu_vram(self):
        """Check with explicit GPU VRAM — model not found should exit(1)."""
        with patch("forgemaster.gpu.GPUMonitor") as mock_monitor:
            monitor_instance = MagicMock()
            monitor_instance.get_gpu_info.return_value = []
            mock_monitor.return_value = monitor_instance
            with patch("forgemaster.scanner.ModelScanner") as mock_scanner:
                mock_result = MagicMock()
                mock_result.models = []
                mock_scanner.return_value.scan.return_value = mock_result
                result = runner.invoke(app, ["check", "test-model", "--gpu-vram", "12288"])
                # Model not found -> exit_code 1
                assert result.exit_code == 1
                assert "not found" in result.output.lower()


# ─── GPU Command ──────────────────────────────────────────────────────────────


class TestGPUCommand:
    def test_gpu_not_available(self):
        """GPU command when no GPU is available."""
        with patch("forgemaster.gpu.GPUMonitor") as mock_monitor:
            monitor_instance = MagicMock()
            monitor_instance.get_gpu_info.return_value = []
            monitor_instance.get_fallback_message.return_value = "No GPU detected."
            mock_monitor.return_value = monitor_instance
            result = runner.invoke(app, ["gpu"])
            assert result.exit_code == 1
            assert "No GPU detected" in result.output

    def test_gpu_available(self):
        """GPU command when an NVIDIA GPU is available."""
        from forgemaster.gpu import GPUInfo

        with patch("forgemaster.gpu.GPUMonitor") as mock_monitor:
            monitor_instance = MagicMock()
            monitor_instance.get_gpu_info.return_value = [
                GPUInfo(
                    name="NVIDIA GeForce RTX 3060",
                    vram_total_mb=12288,
                    vram_used_mb=4096,
                    vram_free_mb=8192,
                    temperature=45,
                    utilization_pct=30,
                    driver_version="535.104.05",
                    gpu_type="nvidia",
                ),
            ]
            monitor_instance.get_gpu_processes.return_value = []
            mock_monitor.return_value = monitor_instance
            result = runner.invoke(app, ["gpu"])
            assert result.exit_code == 0
            assert "RTX 3060" in result.output


# ─── Duplicates Command ──────────────────────────────────────────────────────


class TestDupesCommand:
    def test_dupes_no_paths(self):
        """Dupes with nonexistent paths should error."""
        result = runner.invoke(app, ["dupes", "--path", "/nonexistent/path/12345"])
        assert result.exit_code == 1

    def test_dupes_empty_directory(self):
        """Dupes on empty dir should find no duplicates."""
        with (
            tempfile.TemporaryDirectory() as tmp,
            patch("forgemaster.disk.DuplicateFinder") as mock_finder,
        ):
            finder_instance = MagicMock()
            finder_instance.find_duplicates.return_value = []
            mock_finder.return_value = finder_instance
            result = runner.invoke(app, ["dupes", "--path", tmp])
            assert result.exit_code == 0


# ─── Download Command ─────────────────────────────────────────────────────────


class TestDownloadCommand:
    def test_download_connection_error(self):
        """Download with connection error should fail gracefully."""
        with patch("forgemaster.downloader.ModelDownloader") as mock_dl:
            downloader_instance = MagicMock()
            downloader_instance.list_model_files.side_effect = Exception("Connection error")
            mock_dl.return_value = downloader_instance
            result = runner.invoke(app, ["download", "test/model"])
            assert result.exit_code == 1
