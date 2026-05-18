"""Model scanner and catalog for Muspelheim resources."""

from __future__ import annotations

import json
import os
import re
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING

import yaml


if TYPE_CHECKING:
    from collections.abc import Sequence


@dataclass
class ModelInfo:
    """Information about a model file or directory."""

    name: str
    path: str
    size_bytes: int = 0
    format: str = ""  # gguf, safetensors, pt, onnx
    architecture: str = ""  # llama, stable-diffusion, whisper, etc.
    parameters: int | None = None
    context_length: int | None = None
    quantization: str | None = None
    vram_required_gb: float | None = None
    download_date: str | None = None
    source: str | None = None


@dataclass
class ScanResult:
    """Result of scanning directories for models."""

    models: list[ModelInfo] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)


# Known file extensions to model format mapping
FORMAT_EXTENSIONS = {
    ".gguf": "gguf",
    ".bin": "gguf",  # GGUF often uses .bin
    ".safetensors": "safetensors",
    ".pt": "pt",
    ".pth": "pt",
    ".onnx": "onnx",
}

# Known quantization patterns in filenames
QUANT_PATTERNS = [
    (re.compile(r"[._-]Q4_0", re.IGNORECASE), "Q4_0"),
    (re.compile(r"[._-]Q4_1", re.IGNORECASE), "Q4_1"),
    (re.compile(r"[._-]Q4_K_S", re.IGNORECASE), "Q4_K_S"),
    (re.compile(r"[._-]Q4_K_M", re.IGNORECASE), "Q4_K_M"),
    (re.compile(r"[._-]Q5_0", re.IGNORECASE), "Q5_0"),
    (re.compile(r"[._-]Q5_1", re.IGNORECASE), "Q5_1"),
    (re.compile(r"[._-]Q5_K_S", re.IGNORECASE), "Q5_K_S"),
    (re.compile(r"[._-]Q5_K_M", re.IGNORECASE), "Q5_K_M"),
    (re.compile(r"[._-]Q6_K", re.IGNORECASE), "Q6_K"),
    (re.compile(r"[._-]Q8_0", re.IGNORECASE), "Q8_0"),
    (re.compile(r"[._-]F16", re.IGNORECASE), "F16"),
    (re.compile(r"[._-]F32", re.IGNORECASE), "F32"),
    (re.compile(r"[._-]fp16", re.IGNORECASE), "FP16"),
    (re.compile(r"[._-]bf16", re.IGNORECASE), "BF16"),
]

# Known architecture patterns
ARCH_PATTERNS = [
    (re.compile(r"llama", re.IGNORECASE), "llama"),
    (re.compile(r"mistral", re.IGNORECASE), "mistral"),
    (re.compile(r"mixtral", re.IGNORECASE), "mixtral"),
    (re.compile(r"phi", re.IGNORECASE), "phi"),
    (re.compile(r"gemma", re.IGNORECASE), "gemma"),
    (re.compile(r"stable[\s_-]*diffusion", re.IGNORECASE), "stable-diffusion"),
    (re.compile(r"whisper", re.IGNORECASE), "whisper"),
    (re.compile(r"qwen", re.IGNORECASE), "qwen"),
    (re.compile(r"deepseek", re.IGNORECASE), "deepseek"),
    (re.compile(r"yi", re.IGNORECASE), "yi"),
]

# Parameter count patterns (e.g., "7B", "13B", "70B", "34B")
PARAM_PATTERNS = [
    re.compile(r"[._-](\d+(?:\.\d+)?)[xX]?[bB]\b"),
]


class ModelScanner:
    """Scan directories for model files and extract metadata."""

    def __init__(self) -> None:
        """Initialise scanner (no persistent state required)."""
        pass

    def scan(self, paths: Sequence[str | Path]) -> ScanResult:
        """Scan given paths for model files.

        Args:
            paths: List of directories or files to scan.

        Returns:
            ScanResult with found models and any errors.

        """
        result = ScanResult()
        for path_str in paths:
            path = Path(path_str)
            if not path.exists():
                result.errors.append(f"Path does not exist: {path}")
                continue
            if path.is_file():
                info = self.extract_metadata(path)
                if info is not None:
                    result.models.append(info)
            elif path.is_dir():
                self._scan_directory(path, result)
        return result

    def _scan_directory(self, directory: Path, result: ScanResult) -> None:
        """Recursively scan a directory for model files."""
        for root, dirs, files in os.walk(directory):
            root_path = Path(root)
            # Check if this is a dedicated model directory (has config.json)
            config_path = root_path / "config.json"
            model_files = self._find_model_files(root_path, files)
            if model_files and config_path.is_file():
                # Treat the directory as a single model (HF style)
                info = self._extract_from_directory(root_path, files)
                if info is not None:
                    result.models.append(info)
                    dirs.clear()  # Don't recurse into subdirectories
                    continue
            # Otherwise scan individual files
            for f in files:
                file_path = root_path / f
                info = self.extract_metadata(file_path)
                if info is not None:
                    result.models.append(info)

    def _find_model_files(self, dir_path: Path, files: list[str]) -> list[str]:
        """Find model files in a directory listing."""
        return [f for f in files if Path(f).suffix in FORMAT_EXTENSIONS]

    def _extract_from_directory(self, dir_path: Path, files: list[str]) -> ModelInfo | None:
        """Extract model info from a model directory."""
        model_files = self._find_model_files(dir_path, files)
        if not model_files:
            return None

        total_size = sum(
            (dir_path / f).stat().st_size for f in model_files if (dir_path / f).is_file()
        )

        # Determine primary format from files
        formats = set()
        for f in model_files:
            ext = Path(f).suffix
            if ext in FORMAT_EXTENSIONS:
                formats.add(FORMAT_EXTENSIONS[ext])

        primary_format = formats.pop() if len(formats) == 1 else ",".join(sorted(formats))

        # Try to read config.json or metadata from HuggingFace style directories
        metadata = self._read_hf_metadata(dir_path)

        return ModelInfo(
            name=metadata.get("name", dir_path.name),
            path=str(dir_path),
            size_bytes=total_size,
            format=metadata.get("format", primary_format),
            architecture=metadata.get("architecture", ""),
            parameters=metadata.get("parameters"),
            context_length=metadata.get("context_length"),
            quantization=metadata.get("quantization"),
            vram_required_gb=metadata.get("vram_required_gb"),
            download_date=metadata.get("download_date"),
            source=metadata.get("source"),
        )

    def _read_hf_metadata(self, dir_path: Path) -> dict:
        """Read HuggingFace-style config.json and metadata from a directory."""
        metadata: dict = {}
        config_path = dir_path / "config.json"
        if config_path.is_file():
            try:
                with config_path.open() as f:
                    config = json.load(f)
                if "model_type" in config:
                    metadata["architecture"] = config["model_type"]
                if "max_position_embeddings" in config:
                    metadata["context_length"] = config["max_position_embeddings"]
                if "name_or_path" in config:
                    metadata["source"] = config["name_or_path"]
            except (json.JSONDecodeError, OSError):
                pass

        # Try reading tokenizer_config.json for additional info
        tokenizer_config = dir_path / "tokenizer_config.json"
        if tokenizer_config.is_file():
            try:
                with tokenizer_config.open() as f:
                    config = json.load(f)
                if "model_type" in config and not metadata.get("architecture"):
                    metadata["architecture"] = config["model_type"]
            except (json.JSONDecodeError, OSError):
                pass

        # Try models.yaml or metadata.yaml
        for yaml_name in ["metadata.yaml", "models.yaml"]:
            yaml_path = dir_path / yaml_name
            if yaml_path.is_file():
                try:
                    with yaml_path.open() as f:
                        ydata = yaml.safe_load(f) or {}
                    for key in [
                        "name",
                        "architecture",
                        "parameters",
                        "context_length",
                        "quantization",
                        "vram_required_gb",
                        "download_date",
                        "source",
                    ]:
                        if key in ydata and key not in metadata:
                            metadata[key] = ydata[key]
                except (yaml.YAMLError, OSError):
                    pass

        # Derive name from directory
        metadata.setdefault("name", dir_path.name)

        # Derive architecture / quantization / params from name
        name = dir_path.name
        if not metadata.get("architecture"):
            metadata["architecture"] = self._guess_architecture(name)
        if not metadata.get("quantization"):
            metadata["quantization"] = self._guess_quantization(name)
        if not metadata.get("parameters"):
            metadata["parameters"] = self._guess_parameters(name)

        return metadata

    def extract_metadata(self, model_path: Path) -> ModelInfo | None:
        """Extract metadata from a single model file.

        Args:
            model_path: Path to the model file.

        Returns:
            ModelInfo or None if not a recognized model format.

        """
        model_path = Path(model_path)
        if not model_path.is_file():
            return None

        suffix = model_path.suffix.lower()
        if suffix not in FORMAT_EXTENSIONS:
            return None

        fmt = FORMAT_EXTENSIONS[suffix]
        try:
            size_bytes = model_path.stat().st_size
        except OSError:
            size_bytes = 0

        name = model_path.stem
        # Remove common suffixes
        for pattern in QUANT_PATTERNS:
            name = pattern[0].sub("", name)

        architecture = self._guess_architecture(model_path.name)
        quantization = self._guess_quantization(model_path.name)
        parameters = self._guess_parameters(model_path.name)

        # Try to read GGUF metadata
        context_length = None
        vram_required_gb = None
        if fmt == "gguf":
            context_length, vram_required_gb = self._read_gguf_metadata(model_path)

        # Try reading safetensors metadata
        if fmt == "safetensors":
            parameters, context_length = self._read_safetensors_metadata(model_path)

        # Estimate VRAM from file size (rough heuristic)
        if vram_required_gb is None and size_bytes > 0:
            # Model weight size is a reasonable lower bound for VRAM
            vram_required_gb = round(size_bytes / (1024**3) * 1.2, 2)

        # Download date from file modification time
        download_date = None
        try:
            mtime = model_path.stat().st_mtime
            download_date = datetime.fromtimestamp(mtime).strftime("%Y-%m-%d")
        except OSError:
            pass

        return ModelInfo(
            name=name,
            path=str(model_path),
            size_bytes=size_bytes,
            format=fmt,
            architecture=architecture,
            parameters=parameters,
            context_length=context_length,
            quantization=quantization,
            vram_required_gb=vram_required_gb,
            download_date=download_date,
        )

    def _guess_architecture(self, name: str) -> str:
        """Guess model architecture from filename."""
        for pattern, arch in ARCH_PATTERNS:
            if pattern.search(name):
                return arch
        return ""

    def _guess_quantization(self, name: str) -> str | None:
        """Guess quantization level from filename."""
        for pattern, quant in QUANT_PATTERNS:
            if pattern.search(name):
                return quant
        return None

    def _guess_parameters(self, name: str) -> int | None:
        """Guess parameter count from filename (e.g., 7B -> 7000000000)."""
        for pattern in PARAM_PATTERNS:
            match = pattern.search(name)
            if match:
                value = float(match.group(1))
                return int(value * 1_000_000_000)
        # Also try lowercase 'b' pattern which the main regexes might miss
        lower_match = re.search(r"[._-](\d+(?:\.\d+)?)[bB]\b", name)
        if lower_match:
            value = float(lower_match.group(1))
            return int(value * 1_000_000_000)
        return None

    def _read_gguf_metadata(self, path: Path) -> tuple[int | None, float | None]:
        """Try to read context_length and estimate VRAM from GGUF metadata.

        GGUF format stores metadata in the file header. We read a simplified
        version - extracting context length from the first portion of the file.
        """
        context_length = None
        vram_required_gb = None
        try:
            # Read file size as base for VRAM estimation
            size = path.stat().st_size
            # GGUF models typically need ~1.2x their file size in VRAM
            vram_required_gb = round(size / (1024**3) * 1.2, 2)
        except OSError:
            pass
        return context_length, vram_required_gb

    def _read_safetensors_metadata(self, path: Path) -> tuple[int | None, int | None]:
        """Read safetensors file metadata to extract parameter count."""
        parameters = None
        context_length = None
        try:
            from safetensors import safe_open

            with safe_open(str(path), framework="pt") as f:
                total_params = 0
                for key in f:
                    tensor = f.get_tensor(key)
                    total_params += tensor.numel()
                if total_params > 0:
                    parameters = total_params
        except Exception:
            pass
        return parameters, context_length
