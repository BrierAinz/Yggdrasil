# Z-Image Generation via ai-toolkit — Black Image Bug

## Status
**BLOCKED** — ai-toolkit `job: generate` with Z-Image model produces 100% black images.

## Reproduction

### Config 1: With LoRA (`generate_ehyra_influencer.yaml`)
```yaml
job: generate
config:
  name: ehyra_influencer_generate
  device: cuda
process:
  - type: to_folder
    assistant_lora_path: /home/brierainz/comfy/ai-toolkit/output/ehyra_zimage_lora_v1/ehyra_zimage_lora_v1.safetensors
    lora_weight: 0.8
    folder: output/ehyra_influencer
    save_format: png
    push_to_hub: false
    generate:
      - prompt: "ehyra, a woman with long black hair..."
        width: 768
        height: 1344
        seed: 42
        steps: 25
        cfg: 3.0
        sampler: flowmatch
```
**Result**: 5 PNGs, each 3082 bytes, 768x1344, min=0/max=0/mean=0 (100% black)

### Config 2: Without LoRA (`generate_no_lora_test.yaml`)
```yaml
job: generate
config:
  name: ehyra_no_lora_test
  device: cuda
process:
  - type: to_folder
    folder: output/ehyra_no_lora_test
    save_format: png
    push_to_hub: false
    generate:
      - prompt: "a beautiful woman with black hair, portrait, detailed face"
        width: 768
        height: 512
        seed: 123
        steps: 25
        cfg: 3.0
        sampler: flowmatch
```
**Result**: 1 PNG, 1224 bytes, 768x512, min=0/max=0/mean=0 (100% black)

## Diagnosis

- Model loads correctly (transformer ~4min, quantization ~5sec, text encoder ~4min, total ~8-10min)
- Text encoder processes prompt without errors
- LoRA loads and merges ("Merging in assistant LoRA")
- Sampler runs to completion — no crashes, no errors
- **Output latents are all zeros** → VAE decodes to black

### Suspected causes:
1. **Sampler initialization bug**: ai-toolkit's Z-Image `GenerateProcess` may not properly initialize noise or the denoising loop
2. **uint4 quantization edge case**: The quantized model may produce zero-valued intermediate outputs under certain conditions
3. **FlowMatch scheduler misconfiguration**: The `sampler: flowmatch` config may not match ai-toolkit's expected format for Z-Image

### NOT the cause:
- Not a LoRA issue (base model without LoRA also produces black images)
- Not a resolution issue (tested 768x1344, 768x512, same result)
- Not a CUDA/VRAM issue (model loads and runs without OOM)

## Key Pitfalls Discovered

1. **`inference_lora_path` is WRONG** — causes `AttributeError: 'NoneType' object has no attribute 'is_active'` at `base_model.py:385`. Use `assistant_lora_path` instead.
2. **`device: cuda` required** — GenerateProcess defaults to CPU. Must set `device: cuda` in config section.
3. **Tool path**: ai-toolkit's generation code is in `toolkit/generation/generate_process.py` and model code in `toolkit/models/base_model.py`

## Workarounds

| Option | Platform | Ehyra Face? | Quality | Effort |
|--------|----------|-------------|---------|--------|
| A | PixAI (Z-Image/DiT.2) | ✅ Yes | Native | Low (upload LoRA) |
| B | CivitAI + ComfyUI (SDXL/Flux) | ❌ No | High | Medium |
| C | Debug ai-toolkit locally | Underlying bug fix | Unknown | High |

## Files
- Generated black images: `/home/brierainz/comfy/ai-toolkit/output/ehyra_influencer/` (5 PNGs)
- No-LoRA test: `/home/brierainz/comfy/ai-toolkit/output/ehyra_no_lora_test/` (1 PNG)
- Generate config: `/home/brierainz/comfy/ai-toolkit/config/generate_ehyra_influencer.yaml`
- No-LoRA config: `/home/brierainz/comfy/ai-toolkit/config/generate_no_lora_test.yaml`
- ai-toolkit source: `/home/brierainz/comfy/ai-toolkit/toolkit/`