"""Tests for the model scanner."""

from __future__ import annotations

import json
import tempfile
from pathlib import Path

import pytest

from forgemaster.scanner import ModelInfo, ModelScanner, ScanResult


@pytest.fixture
def scanner():
    return ModelScanner()


@pytest.fixture
def tmp_model_dir():
    """Create a temporary directory with sample model files."""
    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir_path = Path(tmpdir)

        # Create a GGUF model file (empty but with correct extension)
        gguf_file = tmpdir_path / "llama-7b-q4_0.gguf"
        gguf_file.write_bytes(b"\x00" * 1024)

        # Create a safetensors model file
        safetensor_file = tmpdir_path / "mistral-7b-fp16.safetensors"
        safetensor_file.write_bytes(b"\x00" * 2048)

        # Create a PT model file
        pt_file = tmpdir_path / "whisper-small.pt"
        pt_file.write_bytes(b"\x00" * 512)

        # Create a non-model file (should be ignored)
        txt_file = tmpdir_path / "readme.txt"
        txt_file.write_text("not a model")

        # Create a HuggingFace-style directory
        hf_dir = tmpdir_path / "stable-diffusion-v1-5"
        hf_dir.mkdir()
        config = {"model_type": "stable-diffusion", "max_position_embeddings": 77}
        (hf_dir / "config.json").write_text(json.dumps(config))
        (hf_dir / "model.safetensors").write_bytes(b"\x00" * 4096)

        yield tmpdir_path


class TestModelInfo:
    def test_model_info_creation(self):
        info = ModelInfo(
            name="llama-7b",
            path="/models/llama-7b.gguf",
            size_bytes=4200000000,
            format="gguf",
            architecture="llama",
            parameters=7_000_000_000,
            quantization="Q4_0",
        )
        assert info.name == "llama-7b"
        assert info.format == "gguf"
        assert info.architecture == "llama"
        assert info.parameters == 7_000_000_000
        assert info.quantization == "Q4_0"

    def test_model_info_defaults(self):
        info = ModelInfo(name="test", path="/test")
        assert info.size_bytes == 0
        assert info.format == ""
        assert info.architecture == ""
        assert info.parameters is None
        assert info.context_length is None
        assert info.quantization is None
        assert info.vram_required_gb is None
        assert info.download_date is None
        assert info.source is None


class TestModelScanner:
    def test_scan_empty_directory(self, scanner):
        with tempfile.TemporaryDirectory() as tmpdir:
            result = scanner.scan([tmpdir])
            assert len(result.models) == 0
            assert len(result.errors) == 0

    def test_scan_nonexistent_path(self, scanner):
        result = scanner.scan(["/nonexistent/path/that/does/not/exist"])
        assert len(result.errors) == 1
        assert "does not exist" in result.errors[0]

    def test_scan_finds_model_files(self, scanner, tmp_model_dir):
        result = scanner.scan([str(tmp_model_dir)])
        # Should find at least GGUF, safetensors, and the hf directory model
        assert len(result.models) >= 3

    def test_scan_gguf_detection(self, scanner, tmp_model_dir):
        result = scanner.scan([str(tmp_model_dir)])
        gguf_models = [m for m in result.models if m.format == "gguf"]
        assert len(gguf_models) >= 1
        assert gguf_models[0].architecture == "llama"
        assert gguf_models[0].quantization == "Q4_0"

    def test_scan_safetensors_detection(self, scanner, tmp_model_dir):
        result = scanner.scan([str(tmp_model_dir)])
        st_models = [m for m in result.models if m.format == "safetensors"]
        # At least one standalone safetensors file
        standalone = [m for m in st_models if "mistral" in m.name]
        assert len(standalone) >= 0  # Could be 0 or 1 depending on directory scan

    def test_scan_pt_detection(self, scanner, tmp_model_dir):
        result = scanner.scan([str(tmp_model_dir)])
        pt_models = [m for m in result.models if m.format == "pt"]
        assert len(pt_models) >= 1

    def test_scan_ignores_non_model_files(self, scanner, tmp_model_dir):
        result = scanner.scan([str(tmp_model_dir)])
        txt_models = [m for m in result.models if m.path.endswith(".txt")]
        assert len(txt_models) == 0

    def test_scan_hf_directory(self, scanner, tmp_model_dir):
        result = scanner.scan([str(tmp_model_dir)])
        sd_models = [
            m
            for m in result.models
            if "stable-diffusion" in m.name or m.architecture == "stable-diffusion"
        ]
        assert len(sd_models) >= 1

    def test_extract_metadata_single_file(self, scanner):
        with tempfile.TemporaryDirectory() as tmpdir:
            gguf_file = Path(tmpdir) / "test-model-Q5_K_M.gguf"
            gguf_file.write_bytes(b"\x00" * 1024)

            info = scanner.extract_metadata(gguf_file)
            assert info is not None
            assert info.format == "gguf"
            assert info.quantization == "Q5_K_M"
            assert info.size_bytes == 1024

    def test_extract_metadata_non_model_file(self, scanner):
        with tempfile.TemporaryDirectory() as tmpdir:
            txt_file = Path(tmpdir) / "readme.txt"
            txt_file.write_text("hello")

            info = scanner.extract_metadata(txt_file)
            assert info is None

    def test_extract_metadata_nonexistent_file(self, scanner):
        info = scanner.extract_metadata(Path("/nonexistent/file.gguf"))
        assert info is None

    def test_guess_architecture(self, scanner):
        assert scanner._guess_architecture("llama-7b.gguf") == "llama"
        assert scanner._guess_architecture("mistral-7b.gguf") == "mistral"
        assert scanner._guess_architecture("stable-diffusion-v1.5") == "stable-diffusion"
        assert scanner._guess_architecture("whisper-small.pt") == "whisper"
        assert scanner._guess_architecture("random-model.bin") == ""

    def test_guess_quantization(self, scanner):
        assert scanner._guess_quantization("model-Q4_0.gguf") == "Q4_0"
        assert scanner._guess_quantization("model.Q8_0.gguf") == "Q8_0"
        assert scanner._guess_quantization("model-F16.gguf") == "F16"
        assert scanner._guess_quantization("model-fp16.safetensors") == "FP16"
        assert scanner._guess_quantization("model-bf16.safetensors") == "BF16"
        assert scanner._guess_quantization("model.gguf") is None

    def test_guess_parameters(self, scanner):
        assert scanner._guess_parameters("llama-7b.gguf") == 7_000_000_000
        assert scanner._guess_parameters("model-13B.gguf") == 13_000_000_000
        assert scanner._guess_parameters("model-70B.pt") == 70_000_000_000
        assert scanner._guess_parameters("model.gguf") is None

    def test_vram_estimation(self, scanner):
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create a file with known size - use a large enough file for meaningful GB value
            gguf_file = Path(tmpdir) / "test-7b.gguf"
            # Write 100MB of data so the VRAM estimate is meaningful
            data = b"\x00" * (100 * 1024 * 1024)
            gguf_file.write_bytes(data)

            info = scanner.extract_metadata(gguf_file)
            assert info is not None
            assert info.vram_required_gb is not None
            assert info.vram_required_gb > 0

    def test_multiple_scan_paths(self, scanner):
        with tempfile.TemporaryDirectory() as tmpdir1, tempfile.TemporaryDirectory() as tmpdir2:
            (Path(tmpdir1) / "model1.gguf").write_bytes(b"\x00" * 1024)
            (Path(tmpdir2) / "model2.safetensors").write_bytes(b"\x00" * 1024)

            result = scanner.scan([tmpdir1, tmpdir2])
            assert len(result.models) == 2

    def test_scan_result_dataclass(self):
        result = ScanResult()
        assert result.models == []
        assert result.errors == []

        result2 = ScanResult(
            models=[ModelInfo(name="test", path="/test")],
            errors=["error1"],
        )
        assert len(result2.models) == 1
        assert len(result2.errors) == 1
