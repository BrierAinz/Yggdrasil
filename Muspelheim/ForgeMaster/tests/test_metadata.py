"""Tests for forgemaster.metadata — model metadata readers."""

from __future__ import annotations

import json
import struct
from typing import TYPE_CHECKING

from forgemaster.metadata import (
    get_model_metadata,
    read_gguf_metadata,
    read_hf_config,
    read_safetensors_metadata,
)


if TYPE_CHECKING:
    from pathlib import Path


# ── Helpers ──────────────────────────────────────────────────────────────────


def _write_gguf_file(path: Path, kv_pairs: dict[str, object] | None = None) -> None:
    """Write a minimal valid GGUFv3 file at *path* with the given KV pairs."""
    if kv_pairs is None:
        kv_pairs = {}

    # Build KV data
    kv_data = b""
    for key, value in kv_pairs.items():
        # Key string
        key_bytes = key.encode("utf-8")
        kv_data += struct.pack("<Q", len(key_bytes)) + key_bytes
        # Value type + value
        if isinstance(value, str):
            kv_data += struct.pack("<I", 8)  # STRING type
            val_bytes = value.encode("utf-8")
            kv_data += struct.pack("<Q", len(val_bytes)) + val_bytes
        elif isinstance(value, bool):
            kv_data += struct.pack("<I", 7)  # BOOL type
            kv_data += struct.pack("<B", 1 if value else 0)
        elif isinstance(value, int):
            kv_data += struct.pack("<I", 9)  # UINT64 type
            kv_data += struct.pack("<Q", value)
        elif isinstance(value, float):
            kv_data += struct.pack("<I", 6)  # FLOAT32 type
            kv_data += struct.pack("<f", value)

    # GGUF header: magic(4) + version(4) + tensor_count(8) + metadata_kv_count(8)
    header = struct.pack("<I", 0x46475547)  # GGUF magic
    header += struct.pack("<I", 3)  # version 3
    header += struct.pack("<Q", 0)  # tensor_count = 0
    header += struct.pack("<Q", len(kv_pairs))  # metadata_kv_count

    path.write_bytes(header + kv_data)


def _write_safetensors_file(path: Path, tensors: dict | None = None) -> None:
    """Write a minimal safetensors file at *path*."""
    if tensors is None:
        tensors = {
            "model.weight": {
                "dtype": "F32",
                "shape": [2, 2],
                "data_offsets": [0, 16],
            },
            "__metadata__": {"model_type": "llama"},
        }
    header_json = json.dumps(tensors, separators=(",", ":")).encode("utf-8")
    header_bytes = struct.pack("<Q", len(header_json)) + header_json
    # Add some padding data for the tensors
    data_padding = b"\x00" * 32
    path.write_bytes(header_bytes + data_padding)


def _write_hf_config_dir(dir_path: Path, config: dict | None = None) -> None:
    """Write a HF-style model directory with config.json."""
    if config is None:
        config = {
            "model_type": "llama",
            "max_position_embeddings": 4096,
            "architectures": ["LlamaForCausalLM"],
        }
    dir_path.mkdir(parents=True, exist_ok=True)
    (dir_path / "config.json").write_text(json.dumps(config))


# ── read_gguf_metadata ───────────────────────────────────────────────────────


class TestReadGGUFMetadata:
    def test_gguf_with_architecture(self, tmp_path: Path):
        gguf_file = tmp_path / "model.gguf"
        _write_gguf_file(
            gguf_file,
            {
                "general.architecture": "llama",
                "llama.context_length": 8192,
                "llama.parameter_count": 7000000000,
            },
        )
        result = read_gguf_metadata(gguf_file)
        assert result["format"] == "gguf"
        assert result["architecture"] == "llama"
        assert result["context_length"] == 8192
        assert result["parameter_count"] == 7000000000

    def test_gguf_with_generic_keys(self, tmp_path: Path):
        gguf_file = tmp_path / "model.gguf"
        _write_gguf_file(
            gguf_file,
            {
                "general.context_length": 4096,
                "general.parameter_count": 3000000000,
            },
        )
        result = read_gguf_metadata(gguf_file)
        assert result["context_length"] == 4096
        assert result["parameter_count"] == 3000000000

    def test_gguf_empty_kv(self, tmp_path: Path):
        gguf_file = tmp_path / "model.gguf"
        _write_gguf_file(gguf_file, {})
        result = read_gguf_metadata(gguf_file)
        assert result["format"] == "gguf"
        assert result["architecture"] is None

    def test_gguf_nonexistent_file(self):
        result = read_gguf_metadata("/nonexistent/path/model.gguf")
        assert result["format"] == "gguf"
        assert result["architecture"] is None

    def test_gguf_not_a_gguf_file(self, tmp_path: Path):
        fake = tmp_path / "fake.gguf"
        fake.write_text("this is not a gguf file at all")
        result = read_gguf_metadata(fake)
        assert result["format"] == "gguf"
        assert result["architecture"] is None

    def test_gguf_too_short(self, tmp_path: Path):
        tiny = tmp_path / "tiny.gguf"
        tiny.write_bytes(b"GGUF" + b"\x00" * 4)  # only 8 bytes, too short
        result = read_gguf_metadata(tiny)
        assert result["format"] == "gguf"
        assert result["architecture"] is None

    def test_gguf_metadata_dict_present(self, tmp_path: Path):
        gguf_file = tmp_path / "model.gguf"
        _write_gguf_file(gguf_file, {"general.architecture": "mistral"})
        result = read_gguf_metadata(gguf_file)
        assert "metadata" in result
        assert result["metadata"]["general.architecture"] == "mistral"


# ── read_safetensors_metadata ────────────────────────────────────────────────


class TestReadSafetensorsMetadata:
    def test_basic_safetensors(self, tmp_path: Path):
        st_file = tmp_path / "model.safetensors"
        _write_safetensors_file(st_file)
        result = read_safetensors_metadata(st_file)
        assert result["format"] == "safetensors"
        assert len(result["tensors"]) == 1
        assert result["tensors"][0]["name"] == "model.weight"
        assert result["tensors"][0]["shape"] == [2, 2]
        assert result["metadata"]["model_type"] == "llama"

    def test_safetensors_empty_metadata(self, tmp_path: Path):
        st_file = tmp_path / "model.safetensors"
        tensors = {
            "layer.0.weight": {
                "dtype": "F16",
                "shape": [1024, 1024],
                "data_offsets": [0, 2097152],
            },
        }
        _write_safetensors_file(st_file, tensors)
        result = read_safetensors_metadata(st_file)
        assert result["format"] == "safetensors"
        assert result["metadata"] == {}
        assert result["tensors"][0]["dtype"] == "F16"

    def test_safetensors_nonexistent_file(self):
        result = read_safetensors_metadata("/nonexistent/model.safetensors")
        assert result["format"] == "safetensors"
        assert result["tensors"] == []

    def test_safetensors_truncated_file(self, tmp_path: Path):
        bad = tmp_path / "truncated.safetensors"
        bad.write_bytes(b"\x00" * 4)  # too short for a valid header
        result = read_safetensors_metadata(bad)
        assert result["format"] == "safetensors"
        assert result["tensors"] == []


# ── read_hf_config ───────────────────────────────────────────────────────────


class TestReadHfConfig:
    def test_hf_directory(self, tmp_path: Path):
        model_dir = tmp_path / "llama-7b"
        _write_hf_config_dir(
            model_dir,
            {
                "model_type": "llama",
                "max_position_embeddings": 2048,
                "architectures": ["LlamaForCausalLM"],
            },
        )
        result = read_hf_config(model_dir)
        assert result["format"] == "huggingface"
        assert result["architecture"] == "llama"
        assert result["context_length"] == 2048

    def test_hf_config_file_directly(self, tmp_path: Path):
        config_file = tmp_path / "config.json"
        config_file.write_text(
            json.dumps(
                {
                    "model_type": "gpt2",
                    "max_position_embeddings": 1024,
                }
            )
        )
        result = read_hf_config(config_file)
        assert result["architecture"] == "gpt2"
        assert result["context_length"] == 1024

    def test_hf_config_with_max_sequence_length(self, tmp_path: Path):
        model_dir = tmp_path / "mistral-7b"
        _write_hf_config_dir(
            model_dir,
            {
                "model_type": "mistral",
                "max_sequence_length": 32768,
            },
        )
        result = read_hf_config(model_dir)
        assert result["context_length"] == 32768

    def test_hf_config_missing_dir(self, tmp_path: Path):
        result = read_hf_config(tmp_path / "nonexistent")
        assert result["format"] == "huggingface"
        assert result["architecture"] is None

    def test_hf_config_invalid_json(self, tmp_path: Path):
        model_dir = tmp_path / "broken"
        model_dir.mkdir()
        (model_dir / "config.json").write_text("{invalid json")
        result = read_hf_config(model_dir)
        assert result["format"] == "huggingface"
        assert result["architecture"] is None

    def test_hf_config_architectures_list(self, tmp_path: Path):
        model_dir = tmp_path / "multiarch"
        _write_hf_config_dir(
            model_dir,
            {
                "architectures": ["LlamaForCausalLM", "LlamaForSequenceClassification"],
            },
        )
        result = read_hf_config(model_dir)
        assert result["architecture"] == "LlamaForCausalLM"

    def test_hf_config_num_params(self, tmp_path: Path):
        model_dir = tmp_path / "bigmodel"
        _write_hf_config_dir(
            model_dir,
            {
                "model_type": "llama",
                "num_params": 7000000000,
            },
        )
        result = read_hf_config(model_dir)
        assert result["parameter_count"] == 7000000000

    def test_hf_config_raw_config_in_result(self, tmp_path: Path):
        model_dir = tmp_path / "rawtest"
        _write_hf_config_dir(
            model_dir,
            {
                "model_type": "qwen",
                "hidden_size": 4096,
            },
        )
        result = read_hf_config(model_dir)
        assert "config" in result
        assert result["config"]["hidden_size"] == 4096


# ── get_model_metadata (dispatcher) ──────────────────────────────────────────


class TestGetModelMetadata:
    def test_dispatch_gguf(self, tmp_path: Path):
        gguf_file = tmp_path / "model.gguf"
        _write_gguf_file(gguf_file, {"general.architecture": "phi"})
        result = get_model_metadata(gguf_file)
        assert result["format"] == "gguf"
        assert result["architecture"] == "phi"

    def test_dispatch_safetensors(self, tmp_path: Path):
        st_file = tmp_path / "model.safetensors"
        _write_safetensors_file(st_file)
        result = get_model_metadata(st_file)
        assert result["format"] == "safetensors"

    def test_dispatch_hf_directory(self, tmp_path: Path):
        model_dir = tmp_path / "hf-model"
        _write_hf_config_dir(model_dir)
        result = get_model_metadata(model_dir)
        assert result["format"] == "huggingface"
        assert result["architecture"] == "llama"

    def test_dispatch_directory_with_safetensors(self, tmp_path: Path):
        model_dir = tmp_path / "st-model"
        model_dir.mkdir()
        st_file = model_dir / "model.safetensors"
        _write_safetensors_file(st_file)
        result = get_model_metadata(model_dir)
        assert result["format"] == "safetensors"

    def test_dispatch_unknown_directory(self, tmp_path: Path):
        empty_dir = tmp_path / "empty"
        empty_dir.mkdir()
        result = get_model_metadata(empty_dir)
        assert result["format"] == "unknown"

    def test_dispatch_unknown_extension(self, tmp_path: Path):
        unknown = tmp_path / "model.xyz"
        unknown.write_text("not a model")
        result = get_model_metadata(unknown)
        assert result["format"] == "unknown"

    def test_dispatch_bin_with_gguf_magic(self, tmp_path: Path):
        bin_file = tmp_path / "model.bin"
        _write_gguf_file(bin_file, {"general.architecture": "llama"})
        result = get_model_metadata(bin_file)
        assert result["format"] == "gguf"
        assert result["architecture"] == "llama"

    def test_dispatch_bin_without_gguf_magic(self, tmp_path: Path):
        bin_file = tmp_path / "model.bin"
        bin_file.write_text("random data")
        result = get_model_metadata(bin_file)
        assert result["format"] == "unknown"
