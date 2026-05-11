# Face Consistency Research for AI Influencers

Validated model comparison testing for consistent character generation, conducted May 2026.

## Summary

For AI influencers requiring consistent facial identity across images, **SD1.5 + ChilloutMix** is the community gold standard for Asian face characters. All tested SDXL models produce inconsistent faces or bad body composition.

## Model Comparison (Validated)

| Model | Architecture | Face Consistency | Body Consistency | Overall | Notes |
|-------|-------------|-----------------|------------------|---------|-------|
| **Flux.1 Dev Q8_0 GGUF** | Flux (local) | 9/10 | 10/10 | **Best local** | Photorealistic, correct body types, 1536×640 full-body |
| **PixAI PhotoPedia XL** | SDXL (cloud) | 9/10 | 8/10 | **Best cloud** | Cloud-only, can't run locally |
| **ChilloutMix NiPrunedFp16Fix** | SD1.5 | 8/10 | 7/10 | **Excellent** | Community gold standard for Asian faces |
| RealVisXL V4.0 | SDXL | 8/10 | 2/10 | Poor | Good face, terrible body (crops mid-thigh) |
| Multi-LoRA RealVisXL + Face+Body | SDXL | 7/10 | 5/10 | Mixed | Stacking helps body but introduces artifacts |
| Juggernaut XL v9 | SDXL | 6/10 | 3/10 | Poor | Inconsistent faces, painterly artistic style |

## SD1.5 + ChilloutMix Technical Details

- **Model**: ChilloutMix NiPrunedFp16Fix (~2GB)
- **CivitAI**: Model ID 6424, version download `/api/download/models/11732`
- **Native resolution**: 512×768 (portrait) — NOT 768×1344 like SDXL
- **Required VAE**: `vae-ft-mse-840000.safetensors` (SD1.5 VAE, NOT SDXL VAE)
  - Download from HuggingFace: `stabilityai/sd-vae-ft-mse-original`
  - Note: Use the `ema-pruned` variant URL; regular URL may redirect to HTML
  - Place in `models/vae/`
- **KSampler settings**: dpmpp_2m scheduler, karras, 25-30 steps, CFG 7-8

## Cross-Architecture LoRA Weight Reduction

SDXL-trained LoRAs can be used on SD1.5 checkpoints, but **weights must be reduced** to avoid artifacts:

| Weight Type | SDXL (native) | SD1.5 (cross-arch) |
|------------|---------------|-------------------|
| Face LoRA | 0.8 | 0.6 |
| Body LoRA | 0.6 | 0.5 |

Always test in 0.3-0.7 range when crossing architectures. Higher weights cause:
- Color distortion
- Over-smoothing / plastic skin
- Feature bleeding between LoRAs

**Best practice**: Train a dedicated SD1.5 LoRA on ChilloutMix base for the character. Cross-architecture LoRA use is a stopgap, not a production solution.

## Multi-LoRA Stacking on SD1.5

Successfully tested stacking Face LoRA (0.6) + Body LoRA (0.5) on ChilloutMix:
- Better face consistency than any single-SDXL-model approach
- Body improvement over single LoRA, but still not perfect
- Reduced weights prevent the severe artifacts seen at SDXL-native weights

## Recommended Pipeline for Asian AI Influencer Characters

1. **Best overall**: Flux.1 Dev Q8_0 GGUF — 10/10 photorealism, 10/10 body type accuracy, 10/10 full-body composition at 1536×640. Requires 12GB+ VRAM. See `references/flux-gguf-migration.md` for setup.
2. **Asian face specialist**: ChilloutMix (SD1.5) + dedicated SD1.5 LoRA — community gold standard for consistent Asian faces at low VRAM cost (6GB+)
3. **Cloud fallback**: PixAI PhotoPedia XL (best consistency but cloud-only)
4. **Stopgap**: ChilloutMix (SD1.5) + reduced-weight SDXL LoRAs (face 0.6, body 0.5)
5. **NOT recommended**: Juggernaut XL, RealVisXL, or any SDXL model tested — all produce inconsistent faces or crop body composition

## Current Project: Freya (Flux.1 Dev Q8_0 GGUF)

Freya uses Flux.1 Dev Q8_0 GGUF as the base model — superior to all tested SDXL/SD1.5 models for photorealistic body generation and face consistency. Face candidates A-E generated at 1024×1024 (seeds 50001-50389), awaiting user selection before full dataset generation.

## Ehyra Character (Superseded — Reference Only)

- **Current LoRAs**: `ehyra_xl_lora.safetensors` (face, 245MB, SDXL) and `ehyra_body_lora_v1.safetensors` (body, SDXL)
- **PixAI**: Model 1701440086941361361 (PhotoPedia XL), LoRA 2010111271331364248 (DiT.2)
- **Optimal local path**: Train new SD1.5 LoRA on ChilloutMix base for best local consistency
- **PixAI DiT.2 trigger words**: Need 30+ characters describing visual features (NOT artist names)