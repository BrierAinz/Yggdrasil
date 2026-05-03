"""Shared test fixtures for ForgeMaster tests."""

from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from forgemaster.gpu import GPUInfo, GPUMonitor
from forgemaster.scanner import ModelInfo

# ─── Temporary model directories ───────────────────────────────────────────────


@pytest.fixture
def tmp_model_dir():
    """Create a temporary directory with sample model files of various formats."""
    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir_path = Path(tmpdir)

        # GGUF model file
        gguf_file = tmpdir_path / "llama-7b-Q4_K_M.gguf"
        gguf_file.write_bytes(b"\x00" * 2048)

        # Safetensors model file
        safetensor_file = tmpdir_path / "mistral-7b-fp16.safetensors"
        safetensor_file.write_bytes(b"\x00" * 4096)

        # PyTorch model file
        pt_file = tmpdir_path / "whisper-small.pt"
        pt_file.write_bytes(b"\x00" * 1024)

        # Non-model file (should be ignored by scanner)
        txt_file = tmpdir_path / "readme.txt"
        txt_file.write_text("not a model")

        # HuggingFace-style directory
        hf_dir = tmpdir_path / "stable-diffusion-v1-5"
        hf_dir.mkdir()
        config = {"model_type": "stable-diffusion", "max_position_embeddings": 77}
        (hf_dir / "config.json").write_text(json.dumps(config))
        (hf_dir / "model.safetensors").write_bytes(b"\x00" * 8192)

        yield tmpdir_path


@pytest.fixture
def tmp_empty_dir():
    """Create a temporary empty directory."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def tmp_config_dir():
    """Create a temporary directory for config file tests.

    Yields the directory path and cleans up afterwards.
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


# ─── Mock GPU / nvidia-smi ────────────────────────────────────────────────────


FAKE_GPU_CSV = "NVIDIA GeForce RTX 3060, 12288, 4096, 8192, 45, 12, 535.129.06"

FAKE_GPU_CSV_MULTI = (
    "NVIDIA GeForce RTX 3060, 12288, 4096, 8192, 45, 12, 535.129.06\n"
    "NVIDIA GeForce RTX 4090, 24576, 8192, 16384, 55, 30, 535.129.06"
)

FAKE_PROCESS_CSV = "1234, python3, 2048\n5678, llama.cpp, 4096"


@pytest.fixture
def mock_gpu_available():
    """Patch GPUMonitor to report a single available RTX 3060 GPU."""
    with patch("forgemaster.gpu.subprocess.run") as mock_run:
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = FAKE_GPU_CSV
        mock_result.stderr = ""
        mock_run.return_value = mock_result
        yield mock_run


@pytest.fixture
def mock_gpu_unavailable():
    """Patch GPUMonitor to report nvidia-smi not found."""
    with patch("forgemaster.gpu.subprocess.run") as mock_run:
        mock_run.side_effect = FileNotFoundError("nvidia-smi not found")
        yield mock_run


@pytest.fixture
def mock_multi_gpu():
    """Patch GPUMonitor to report two GPUs (RTX 3060 + RTX 4090)."""
    with patch("forgemaster.gpu.subprocess.run") as mock_run:
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = FAKE_GPU_CSV_MULTI
        mock_result.stderr = ""
        mock_run.return_value = mock_result
        yield mock_run


@pytest.fixture
def rtx_3060_gpu_info():
    """Return a sample GPUInfo for an RTX 3060 12GB."""
    return GPUInfo(
        name="NVIDIA GeForce RTX 3060",
        vram_total_mb=12288,
        vram_used_mb=4096,
        vram_free_mb=8192,
        temperature=45,
        utilization_pct=12,
        driver_version="535.129.06",
    )


@pytest.fixture
def rtx_4090_gpu_info():
    """Return a sample GPUInfo for an RTX 4090 24GB."""
    return GPUInfo(
        name="NVIDIA GeForce RTX 4090",
        vram_total_mb=24576,
        vram_used_mb=8192,
        vram_free_mb=16384,
        temperature=55,
        utilization_pct=30,
        driver_version="535.129.06",
    )


# ─── Sample ModelInfo fixtures ────────────────────────────────────────────────


@pytest.fixture
def sample_models():
    """Return a list of sample ModelInfo objects for unit tests."""
    return [
        ModelInfo(
            name="llama-7b-Q4_0",
            path="/models/llama-7b-Q4_0.gguf",
            size_bytes=4_000_000_000,
            format="gguf",
            architecture="llama",
            parameters=7_000_000_000,
            quantization="Q4_0",
        ),
        ModelInfo(
            name="mistral-7b-fp16",
            path="/models/mistral-7b-fp16.safetensors",
            size_bytes=14_000_000_000,
            format="safetensors",
            architecture="mistral",
            parameters=7_000_000_000,
            quantization="FP16",
        ),
        ModelInfo(
            name="whisper-small",
            path="/models/whisper-small.pt",
            size_bytes=500_000_000,
            format="pt",
            architecture="whisper",
        ),
    ]


# ─── Config fixtures ──────────────────────────────────────────────────────────


@pytest.fixture
def isolated_config(tmp_path):
    """Provide an isolated config directory and env for config tests.

    Sets YGGDRASIL_ROOT to a temp dir and config path to a temp file.
    Restores environment after the test.
    """
    config_file = tmp_path / "config.yaml"
    catalog_dir = tmp_path / ".forgemaster"
    catalog_dir.mkdir(parents=True, exist_ok=True)

    old_ygg_root = os.environ.pop("YGGDRASIL_ROOT", None)
    os.environ["YGGDRASIL_ROOT"] = str(tmp_path)

    yield {
        "config_file": config_file,
        "catalog_dir": catalog_dir,
        "yggdrasil_root": str(tmp_path),
    }

    # Restore env
    if old_ygg_root is not None:
        os.environ["YGGDRASIL_ROOT"] = old_ygg_root
    else:
        os.environ.pop("YGGDRASIL_ROOT", None)
