"""ForgeMaster model metadata readers.

Reads metadata from various model file formats:
  - GGUF: parses binary header for architecture, context_length, parameter count
  - safetensors: reads JSON header for tensor metadata
  - HuggingFace directories: reads config.json

Usage:
    from forgemaster.metadata import get_model_metadata

    info = get_model_metadata("/path/to/model.gguf")
    print(info["architecture"], info["context_length"])
"""

from __future__ import annotations

import json
import struct
from pathlib import Path
from typing import Any


# ─── GGUF constants ──────────────────────────────────────────────────────────

GGUF_MAGIC = 0x46475547  # "GGUF" in little-endian

# GGUF value types (subset)
GGUF_TYPE_UINT8 = 0
GGUF_TYPE_INT8 = 1
GGUF_TYPE_UINT16 = 2
GGUF_TYPE_INT16 = 3
GGUF_TYPE_UINT32 = 4
GGUF_TYPE_INT32 = 5
GGUF_TYPE_FLOAT32 = 6
GGUF_TYPE_BOOL = 7
GGUF_TYPE_STRING = 8
GGUF_TYPE_UINT64 = 9
GGUF_TYPE_INT64 = 10
GGUF_TYPE_FLOAT64 = 11
GGUF_TYPE_ARRAY = 12

# Well-known GGUF metadata keys
GGUF_KEYS_ARCH = "general.architecture"
GGUF_KEYS_CONTEXT = "{arch}.context_length"
GGUF_KEYS_PARAM_COUNT = "{arch}.parameter_count"


def _read_gguf_string(data: bytes, offset: int) -> tuple[str, int]:
    """Read a GGUF string (uint64 length + bytes) from *data* at *offset*.

    Returns (string_value, new_offset).
    """
    length = struct.unpack_from("<Q", data, offset)[0]
    offset += 8
    value = data[offset : offset + length].decode("utf-8", errors="replace")
    offset += length
    return value, offset


def _read_gguf_value(data: bytes, offset: int, vtype: int) -> tuple[Any, int]:
    """Read a single GGUF metadata value of *vtype* from *data* at *offset*.

    Returns (value, new_offset).
    """
    if vtype == GGUF_TYPE_UINT8:
        return struct.unpack_from("<B", data, offset)[0], offset + 1
    elif vtype == GGUF_TYPE_INT8:
        return struct.unpack_from("<b", data, offset)[0], offset + 1
    elif vtype == GGUF_TYPE_UINT16:
        return struct.unpack_from("<H", data, offset)[0], offset + 2
    elif vtype == GGUF_TYPE_INT16:
        return struct.unpack_from("<h", data, offset)[0], offset + 2
    elif vtype == GGUF_TYPE_UINT32:
        return struct.unpack_from("<I", data, offset)[0], offset + 4
    elif vtype == GGUF_TYPE_INT32:
        return struct.unpack_from("<i", data, offset)[0], offset + 4
    elif vtype == GGUF_TYPE_FLOAT32:
        return struct.unpack_from("<f", data, offset)[0], offset + 4
    elif vtype == GGUF_TYPE_BOOL:
        return struct.unpack_from("<B", data, offset)[0] != 0, offset + 1
    elif vtype == GGUF_TYPE_STRING:
        return _read_gguf_string(data, offset)
    elif vtype == GGUF_TYPE_UINT64:
        return struct.unpack_from("<Q", data, offset)[0], offset + 8
    elif vtype == GGUF_TYPE_INT64:
        return struct.unpack_from("<q", data, offset)[0], offset + 8
    elif vtype == GGUF_TYPE_FLOAT64:
        return struct.unpack_from("<d", data, offset)[0], offset + 8
    elif vtype == GGUF_TYPE_ARRAY:
        # array: uint32 elem_type, uint64 count, then count values
        elem_type = struct.unpack_from("<I", data, offset)[0]
        offset += 4
        count = struct.unpack_from("<Q", data, offset)[0]
        offset += 8
        items: list[Any] = []
        for _ in range(count):
            item, offset = _read_gguf_value(data, offset, elem_type)
            items.append(item)
        return items, offset
    else:
        # Unknown type — skip nothing, return None
        return None, offset


def read_gguf_metadata(path: str | Path) -> dict[str, Any]:
    """Parse a GGUF file header and extract metadata.

    Reads the KV metadata store and returns architecture,
    context_length, and parameter_count when available.

    Args:
        path: Path to the ``.gguf`` file.

    Returns:
        Dict with keys ``format``, ``architecture``, ``context_length``,
        ``parameter_count``, and any other KV pairs found.

    """
    path = Path(path)
    result: dict[str, Any] = {
        "format": "gguf",
        "architecture": None,
        "context_length": None,
        "parameter_count": None,
    }

    try:
        data = path.read_bytes()
    except OSError:
        return result

    if len(data) < 12:
        return result

    magic = struct.unpack_from("<I", data, 0)[0]
    if magic != GGUF_MAGIC:
        return result

    version = struct.unpack_from("<I", data, 4)[0]
    if version < 2:
        return result

    _tensor_count = struct.unpack_from("<Q", data, 8)[0]
    metadata_kv_count = struct.unpack_from("<Q", data, 16)[0]

    offset = 24  # After header

    # Read all KV pairs
    raw_kv: dict[str, Any] = {}
    for _ in range(metadata_kv_count):
        try:
            key, offset = _read_gguf_string(data, offset)
            vtype = struct.unpack_from("<I", data, offset)[0]
            offset += 4
            value, offset = _read_gguf_value(data, offset, vtype)
            raw_kv[key] = value
        except (struct.error, IndexError):
            break

    # Extract well-known keys
    arch = raw_kv.get(GGUF_KEYS_ARCH)
    if arch:
        result["architecture"] = arch
        # Architecture-specific keys
        ctx_key = GGUF_KEYS_CONTEXT.format(arch=arch)
        param_key = GGUF_KEYS_PARAM_COUNT.format(arch=arch)
        if ctx_key in raw_kv:
            result["context_length"] = int(raw_kv[ctx_key])
        if param_key in raw_kv:
            result["parameter_count"] = int(raw_kv[param_key])

    # Also check generic keys
    if result["context_length"] is None and "general.context_length" in raw_kv:
        result["context_length"] = int(raw_kv["general.context_length"])
    if result["parameter_count"] is None and "general.parameter_count" in raw_kv:
        result["parameter_count"] = int(raw_kv["general.parameter_count"])

    # Store all raw KV for power users
    result["metadata"] = raw_kv
    return result


def read_safetensors_metadata(path: str | Path) -> dict[str, Any]:
    """Read the JSON header from a safetensors file.

    The safetensors format begins with an 8-byte little-endian header length
    followed by a JSON object containing tensor names, dtypes, shapes, and
    optional ``__metadata__``.

    Args:
        path: Path to the ``.safetensors`` file.

    Returns:
        Dict with keys ``format``, ``tensors`` (list of tensor names and
        shapes), and ``metadata`` (the ``__metadata__`` dict if present).

    """
    path = Path(path)
    result: dict[str, Any] = {
        "format": "safetensors",
        "tensors": [],
        "metadata": {},
    }

    try:
        with path.open("rb") as f:
            header_len_bytes = f.read(8)
            if len(header_len_bytes) < 8:
                return result
            header_len = struct.unpack("<Q", header_len_bytes)[0]
            header_json = f.read(header_len)
            if len(header_json) < header_len:
                # Truncated header — still parse what we have
                pass
            header = json.loads(header_json)
    except (OSError, json.JSONDecodeError, struct.error):
        return result

    # Extract tensor info
    for name, info in header.items():
        if name == "__metadata__":
            result["metadata"] = info
        elif isinstance(info, dict) and "shape" in info:
            result["tensors"].append(
                {
                    "name": name,
                    "dtype": info.get("dtype", ""),
                    "shape": info["shape"],
                }
            )

    return result


def read_hf_config(path: str | Path) -> dict[str, Any]:
    """Read a ``config.json`` from a HuggingFace model directory.

    Args:
        path: Path to the model directory (must contain ``config.json``)
              or a direct path to ``config.json``.

    Returns:
        Dict with keys ``format``, ``architecture``, ``context_length``,
        ``parameter_count``, and any other config keys found.

    """
    path = Path(path)

    # If path points to config.json directly, use it; otherwise look inside dir
    if path.is_dir():
        config_path = path / "config.json"
    else:
        config_path = path

    result: dict[str, Any] = {
        "format": "huggingface",
        "architecture": None,
        "context_length": None,
        "parameter_count": None,
    }

    if not config_path.is_file():
        return result

    try:
        with config_path.open("r") as f:
            config = json.load(f)
    except (json.JSONDecodeError, OSError):
        return result

    # Map well-known config keys
    if "model_type" in config:
        result["architecture"] = config["model_type"]
    elif "architectures" in config:
        arch_list = config["architectures"]
        if isinstance(arch_list, list) and arch_list:
            result["architecture"] = arch_list[0]

    if "max_position_embeddings" in config:
        result["context_length"] = int(config["max_position_embeddings"])
    elif "max_sequence_length" in config:
        result["context_length"] = int(config["max_sequence_length"])

    # Parameter count is not usually in config.json directly,
    # but some models provide it
    if "num_params" in config:
        result["parameter_count"] = int(config["num_params"])

    # Store raw config for advanced use
    result["config"] = config
    return result


def get_model_metadata(path: str | Path) -> dict[str, Any]:
    """Auto-detect file type and read metadata.

    Dispatches to the appropriate reader based on file extension or
    directory contents:
      - ``.gguf``              → :func:`read_gguf_metadata`
      - ``.safetensors``       → :func:`read_safetensors_metadata`
      - Directory with
        ``config.json``        → :func:`read_hf_config`

    Args:
        path: Path to a model file or directory.

    Returns:
        Metadata dict (contents vary by format).

    """
    path = Path(path)

    if path.is_dir():
        if (path / "config.json").is_file():
            return read_hf_config(path)
        # Check for safetensors inside
        st_files = list(path.glob("*.safetensors"))
        if st_files:
            return read_safetensors_metadata(st_files[0])
        return {"format": "unknown", "error": "No recognized model files in directory"}

    suffix = path.suffix.lower()

    if suffix == ".gguf":
        return read_gguf_metadata(path)
    elif suffix == ".safetensors":
        return read_safetensors_metadata(path)

    # For .bin files, try GGUF first, then fall back
    if suffix == ".bin":
        meta = read_gguf_metadata(path)
        if meta.get("architecture") is not None:
            return meta
        return {"format": "unknown", "path": str(path)}

    return {"format": "unknown", "path": str(path)}
