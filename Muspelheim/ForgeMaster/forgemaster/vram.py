"""VRAM calculator for model inference requirements."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING


if TYPE_CHECKING:
    from forgemaster.scanner import ModelInfo


@dataclass
class GPUProfile:
    """GPU profile for VRAM calculations."""

    name: str = ""
    vram_total_gb: float = 0.0
    vram_available_gb: float = 0.0


@dataclass
class VRAMEstimate:
    """VRAM usage estimate for a model."""

    model_weights_gb: float = 0.0
    kv_cache_gb: float = 0.0
    overhead_gb: float = 0.0
    total_gb: float = 0.0
    context_length: int = 0
    batch_size: int = 1


@dataclass
class OffloadStrategy:
    """Strategy for offloading model layers to fit within VRAM."""

    gpu_layers: int = 0
    cpu_layers: int = 0
    gpu_vram_used_gb: float = 0.0
    cpu_ram_used_gb: float = 0.0
    can_run: bool = False
    description: str = ""


# VRAM overhead multipliers by format
FORMAT_OVERHEAD = {
    "gguf": 1.15,  # GGUF has ~15% overhead
    "safetensors": 1.25,  # safetensors need dequantization buffers
    "pt": 1.30,  # PyTorch has more overhead
    "onnx": 1.20,  # ONNX overhead
}

# Default overhead for unknown formats
DEFAULT_OVERHEAD = 1.20

# Bytes per parameter for different quantizations
QUANT_BYTES_PER_PARAM = {
    "Q4_0": 0.5,
    "Q4_1": 0.5,
    "Q4_K_S": 0.5,
    "Q4_K_M": 0.55,
    "Q5_0": 0.625,
    "Q5_1": 0.625,
    "Q5_K_S": 0.625,
    "Q5_K_M": 0.65,
    "Q6_K": 0.75,
    "Q8_0": 1.0,
    "F16": 2.0,
    "FP16": 2.0,
    "BF16": 2.0,
    "F32": 4.0,
}

# Default bytes per parameter (FP16)
DEFAULT_BYTES_PER_PARAM = 2.0

# KV cache: bytes per token per layer per head dimension
# Approximate: 2 bytes per element (FP16),hidden_dim * num_layers
# Simplified: ~0.5MB per 1K context for a 7B model
KV_CACHE_PER_TOKEN_BYTES = {
    "llama": 0.0005,  # ~0.5KB per token per billion params
    "mistral": 0.0005,
    "mixtral": 0.0015,  # MoE has more overhead
    "stable-diffusion": 0.0001,  # SD doesn't use KV cache same way
    "whisper": 0.0002,
}

DEFAULT_KV_PER_TOKEN = 0.0005

# ComfyUI additional model loading overhead (additional LoRA, VAE, etc.)
COMFYUI_OVERHEAD_GB = 2.0


class VRAMCalculator:
    """Calculate VRAM requirements for model inference."""

    def calculate(
        self,
        model: ModelInfo,
        context_length: int = 4096,
        batch_size: int = 1,
    ) -> VRAMEstimate:
        """Calculate VRAM estimate for a model.

        Args:
            model: ModelInfo describing the model.
            context_length: Maximum context length to calculate for.
            batch_size: Batch size for inference.

        Returns:
            VRAMEstimate with detailed breakdown.

        """
        # Model weights
        model_weights_gb = self._estimate_weights_gb(model)

        overhead_multiplier = FORMAT_OVERHEAD.get(model.format, DEFAULT_OVERHEAD)
        overhead_gb = model_weights_gb * (overhead_multiplier - 1.0)

        # KV cache estimation
        kv_cache_gb = self._estimate_kv_cache_gb(model, context_length, batch_size)

        total_gb = model_weights_gb + kv_cache_gb + overhead_gb

        return VRAMEstimate(
            model_weights_gb=round(model_weights_gb, 3),
            kv_cache_gb=round(kv_cache_gb, 3),
            overhead_gb=round(overhead_gb, 3),
            total_gb=round(total_gb, 3),
            context_length=context_length,
            batch_size=batch_size,
        )

    def can_run(self, model: ModelInfo, gpu: GPUProfile, context_length: int = 4096) -> bool:
        """Check if a model can run on a given GPU.

        Args:
            model: ModelInfo describing the model.
            gpu: GPUProfile describing available VRAM.
            context_length: Maximum context length.

        Returns:
            True if the model fits in available VRAM.

        """
        estimate = self.calculate(model, context_length)
        return estimate.total_gb <= gpu.vram_available_gb

    def suggest_offload(
        self,
        model: ModelInfo,
        gpu: GPUProfile,
        context_length: int = 4096,
    ) -> OffloadStrategy:
        """Suggest an offload strategy for running a model on limited VRAM.

        Args:
            model: ModelInfo describing the model.
            gpu: GPUProfile describing available VRAM.
            context_length: Maximum context length.

        Returns:
            OffloadStrategy with layer split recommendation.

        """
        estimate = self.calculate(model, context_length)
        available_gb = gpu.vram_available_gb

        # If it fits entirely on GPU
        if estimate.total_gb <= available_gb:
            total_layers = self._estimate_total_layers(model)
            return OffloadStrategy(
                gpu_layers=total_layers,
                cpu_layers=0,
                gpu_vram_used_gb=estimate.total_gb,
                cpu_ram_used_gb=0.0,
                can_run=True,
                description=(
                    f"Model fits entirely on GPU ({estimate.total_gb:.1f}GB / {available_gb:.1f}GB)"
                ),
            )

        # Calculate how many layers can fit on GPU
        total_layers = self._estimate_total_layers(model)
        weights_gb = estimate.model_weights_gb
        kv_and_overhead_gb = estimate.kv_cache_gb + estimate.overhead_gb

        # Space available for weights after KV cache and overhead
        weights_budget = max(0, available_gb - kv_and_overhead_gb)

        if weights_budget <= 0:
            return OffloadStrategy(
                gpu_layers=0,
                cpu_layers=total_layers,
                gpu_vram_used_gb=available_gb,
                cpu_ram_used_gb=estimate.total_gb,
                can_run=False,
                description=(
                    f"Not enough VRAM even for KV cache "
                    f"({kv_and_overhead_gb:.1f}GB needed, "
                    f"{available_gb:.1f}GB available)"
                ),
            )

        # Proportional layer split
        gpu_ratio = min(weights_budget / weights_gb, 1.0) if weights_gb > 0 else 0.0
        gpu_layers = max(1, int(total_layers * gpu_ratio))
        cpu_layers = total_layers - gpu_layers

        gpu_vram = estimate.kv_cache_gb + estimate.overhead_gb + (weights_gb * gpu_ratio)
        cpu_ram = weights_gb * (1 - gpu_ratio)

        can_run = gpu_layers > 0
        description = (
            f"Offload {cpu_layers}/{total_layers} layers to CPU. "
            f"GPU: {gpu_vram:.1f}GB / {available_gb:.1f}GB, "
            f"CPU RAM needed: {cpu_ram:.1f}GB"
        )

        return OffloadStrategy(
            gpu_layers=gpu_layers,
            cpu_layers=cpu_layers,
            gpu_vram_used_gb=round(gpu_vram, 3),
            cpu_ram_used_gb=round(cpu_ram, 3),
            can_run=can_run,
            description=description,
        )

    def _estimate_weights_gb(self, model: ModelInfo) -> float:
        """Estimate model weight size in GB."""
        if model.vram_required_gb and model.vram_required_gb > 0:
            # Use the pre-calculated estimate
            # But strip the overhead to get raw weights
            overhead_multiplier = FORMAT_OVERHEAD.get(model.format, DEFAULT_OVERHEAD)
            return model.vram_required_gb / overhead_multiplier

        # Estimate from file size
        if model.size_bytes > 0:
            return model.size_bytes / (1024**3)

        # Estimate from parameter count
        if model.parameters:
            bytes_per_param = QUANT_BYTES_PER_PARAM.get(
                model.quantization or "", DEFAULT_BYTES_PER_PARAM
            )
            if model.quantization is None and model.format == "gguf":
                bytes_per_param = DEFAULT_BYTES_PER_PARAM
            return (model.parameters * bytes_per_param) / (1024**3)

        return 0.0

    def _estimate_kv_cache_gb(
        self, model: ModelInfo, context_length: int, batch_size: int
    ) -> float:
        """Estimate KV cache size in GB."""
        # For stable-diffusion, no KV cache
        if model.architecture == "stable-diffusion":
            return 0.0

        params_b = (model.parameters or 7_000_000_000) / 1_000_000_000

        # Bytes per token per billion parameters
        kv_per_token = KV_CACHE_PER_TOKEN_BYTES.get(model.architecture, DEFAULT_KV_PER_TOKEN)

        # KV cache = per_token * context_length * batch_size * params_b
        kv_cache_bytes = kv_per_token * context_length * batch_size * params_b * 1024 * 1024

        return kv_cache_bytes / (1024**3)

    def _estimate_total_layers(self, model: ModelInfo) -> int:
        """Estimate total number of layers in a model."""
        params = model.parameters or 7_000_000_000

        # Rough heuristic based on parameter count
        if params <= 1_500_000_000:  # ~1.5B
            return 24
        if params <= 7_000_000_000:  # ~7B
            return 32
        if params <= 13_000_000_000:  # ~13B
            return 40
        if params <= 34_000_000_000:  # ~34B
            return 48
        if params <= 70_000_000_000:  # ~70B
            return 64
        return 80

    def estimate_comfyui(self, model: ModelInfo) -> float:
        """Estimate VRAM needed for ComfyUI model loading.

        ComfyUI loads additional components (VAE, CLIP, etc.).

        Args:
            model: ModelInfo describing the SD model.

        Returns:
            Estimated total VRAM in GB.

        """
        estimate = self.calculate(model, context_length=77, batch_size=1)
        return round(estimate.total_gb + COMFYUI_OVERHEAD_GB, 3)
