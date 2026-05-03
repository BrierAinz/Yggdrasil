"""Tests for the VRAM calculator."""

from __future__ import annotations

import pytest

from forgemaster.scanner import ModelInfo
from forgemaster.vram import GPUProfile, OffloadStrategy, VRAMCalculator, VRAMEstimate


@pytest.fixture
def calculator():
    return VRAMCalculator()


@pytest.fixture
def llama_7b_q4():
    return ModelInfo(
        name="llama-7b-q4_0",
        path="/models/llama-7b-q4_0.gguf",
        size_bytes=4_000_000_000,
        format="gguf",
        architecture="llama",
        parameters=7_000_000_000,
        quantization="Q4_0",
    )


@pytest.fixture
def llama_7b_fp16():
    return ModelInfo(
        name="llama-7b-fp16",
        path="/models/llama-7b-fp16.safetensors",
        size_bytes=14_000_000_000,
        format="safetensors",
        architecture="llama",
        parameters=7_000_000_000,
        quantization="FP16",
    )


@pytest.fixture
def rtx_4090():
    return GPUProfile(name="RTX 4090", vram_total_gb=24.0, vram_available_gb=22.0)


@pytest.fixture
def rtx_3060():
    return GPUProfile(name="RTX 3060", vram_total_gb=12.0, vram_available_gb=10.0)


class TestVRAMEstimate:
    def test_vram_estimate_defaults(self):
        estimate = VRAMEstimate()
        assert estimate.model_weights_gb == 0.0
        assert estimate.kv_cache_gb == 0.0
        assert estimate.overhead_gb == 0.0
        assert estimate.total_gb == 0.0
        assert estimate.context_length == 0
        assert estimate.batch_size == 1


class TestGPUProfile:
    def test_gpu_profile_defaults(self):
        profile = GPUProfile()
        assert profile.name == ""
        assert profile.vram_total_gb == 0.0
        assert profile.vram_available_gb == 0.0


class TestOffloadStrategy:
    def test_offload_strategy_defaults(self):
        strategy = OffloadStrategy()
        assert strategy.gpu_layers == 0
        assert strategy.cpu_layers == 0
        assert strategy.gpu_vram_used_gb == 0.0
        assert strategy.cpu_ram_used_gb == 0.0
        assert strategy.can_run is False
        assert strategy.description == ""


class TestVRAMCalculator:
    def test_calculate_gguf_q4(self, calculator, llama_7b_q4):
        estimate = calculator.calculate(llama_7b_q4, context_length=4096)
        assert estimate.model_weights_gb > 0
        assert estimate.kv_cache_gb > 0
        assert estimate.overhead_gb > 0
        assert estimate.total_gb > estimate.model_weights_gb
        assert estimate.context_length == 4096
        assert estimate.batch_size == 1

    def test_calculate_safetensors_fp16(self, calculator, llama_7b_fp16):
        estimate = calculator.calculate(llama_7b_fp16, context_length=4096)
        assert estimate.model_weights_gb > 0
        assert estimate.total_gb > 0

    def test_calculate_with_vram_required(self, calculator):
        model = ModelInfo(
            name="test",
            path="/test",
            vram_required_gb=5.0,
            format="gguf",
        )
        estimate = calculator.calculate(model)
        assert estimate.model_weights_gb > 0

    def test_calculate_with_batch_size(self, calculator, llama_7b_q4):
        estimate1 = calculator.calculate(llama_7b_q4, batch_size=1)
        estimate4 = calculator.calculate(llama_7b_q4, batch_size=4)
        # Larger batch should use more VRAM
        assert estimate4.kv_cache_gb > estimate1.kv_cache_gb
        assert estimate4.total_gb > estimate1.total_gb

    def test_can_run_fits(self, calculator, llama_7b_q4, rtx_4090):
        result = calculator.can_run(llama_7b_q4, rtx_4090, context_length=4096)
        # Q4_0 7B should fit on RTX 4090
        assert result is True

    def test_can_run_too_large(self, calculator):
        large_model = ModelInfo(
            name="llama-70b-fp32",
            path="/models/llama-70b.pt",
            size_bytes=280_000_000_000,
            format="pt",
            parameters=70_000_000_000,
            quantization="F32",
        )
        rtx_3060 = GPUProfile(
            name="RTX 3060", vram_total_gb=12.0, vram_available_gb=10.0
        )
        result = calculator.can_run(large_model, rtx_3060)
        assert result is False

    def test_suggest_offload_fully_fits(self, calculator, llama_7b_q4, rtx_4090):
        strategy = calculator.suggest_offload(llama_7b_q4, rtx_4090)
        assert strategy.can_run is True
        assert strategy.cpu_layers == 0
        assert strategy.gpu_layers > 0

    def test_suggest_offload_partial(self, calculator):
        large_model = ModelInfo(
            name="llama-70b-q4",
            path="/models/llama-70b-q4.gguf",
            size_bytes=40_000_000_000,
            format="gguf",
            parameters=70_000_000_000,
            quantization="Q4_0",
        )
        rtx_3060 = GPUProfile(
            name="RTX 3060", vram_total_gb=12.0, vram_available_gb=10.0
        )
        strategy = calculator.suggest_offload(large_model, rtx_3060)
        # Should suggest partial offload
        assert strategy.cpu_layers > 0
        assert strategy.gpu_layers > 0

    def test_suggest_offload_no_fit(self, calculator):
        huge_model = ModelInfo(
            name="huge",
            path="/huge",
            size_bytes=500_000_000_000,
            format="pt",
            parameters=175_000_000_000,
        )
        tiny_gpu = GPUProfile(name="Tiny", vram_total_gb=4.0, vram_available_gb=3.0)
        strategy = calculator.suggest_offload(huge_model, tiny_gpu)
        assert strategy.can_run is False

    def test_stable_diffusion_no_kv_cache(self, calculator):
        sd_model = ModelInfo(
            name="sd-v1.5",
            path="/models/sd.safetensors",
            size_bytes=4_000_000_000,
            format="safetensors",
            architecture="stable-diffusion",
            parameters=860_000_000,
        )
        estimate = calculator.calculate(sd_model)
        assert estimate.kv_cache_gb == 0.0

    def test_estimate_comfyui(self, calculator):
        sd_model = ModelInfo(
            name="sd-v1.5",
            path="/models/sd.safetensors",
            size_bytes=4_000_000_000,
            format="safetensors",
            architecture="stable-diffusion",
            parameters=860_000_000,
        )
        comfyui_vram = calculator.estimate_comfyui(sd_model)
        # Should be higher than the base model
        base_estimate = calculator.calculate(sd_model)
        assert comfyui_vram > base_estimate.total_gb

    def test_calculate_custom_context_length(self, calculator, llama_7b_q4):
        short = calculator.calculate(llama_7b_q4, context_length=1024)
        long = calculator.calculate(llama_7b_q4, context_length=8192)
        # Longer context should use more KV cache
        assert long.kv_cache_gb > short.kv_cache_gb

    def test_unknown_format_overhead(self, calculator):
        model = ModelInfo(
            name="test",
            path="/test",
            size_bytes=1_000_000_000,
            format="unknown",
        )
        estimate = calculator.calculate(model)
        assert estimate.overhead_gb > 0

    def test_empty_model(self, calculator):
        model = ModelInfo(name="empty", path="/empty")
        estimate = calculator.calculate(model)
        # Should still produce a valid estimate (possibly 0)
        assert estimate.total_gb >= 0

    def test_different_quantizations(self, calculator):
        q4 = ModelInfo(
            name="model-q4",
            path="/m1",
            parameters=7_000_000_000,
            format="gguf",
            quantization="Q4_0",
        )
        q8 = ModelInfo(
            name="model-q8",
            path="/m2",
            parameters=7_000_000_000,
            format="gguf",
            quantization="Q8_0",
        )
        fp16 = ModelInfo(
            name="model-fp16",
            path="/m3",
            parameters=7_000_000_000,
            format="safetensors",
            quantization="FP16",
        )

        est_q4 = calculator.calculate(q4)
        est_q8 = calculator.calculate(q8)
        est_fp16 = calculator.calculate(fp16)

        # Less quantized models use more VRAM
        assert est_fp16.total_gb > est_q8.total_gb
        assert est_q8.total_gb > est_q4.total_gb
