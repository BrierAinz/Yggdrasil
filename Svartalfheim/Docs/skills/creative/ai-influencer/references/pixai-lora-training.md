# PixAI LoRA Training Reference

PixAI (https://pixai.art) is a cloud-based LoRA training platform — alternative
to local Kohya/AI-Toolkit when GPU VRAM is limited or when the local model (e.g.
Z-Image) has NaN issues.

## When to Use PixAI

- Local Z-Image produces black/NaN images (RTX 3060 uint4 bug)
- No local GPU at all, or want to train without killing ComfyUI
- Need a pre-trained anime-style model (Tsubaki.2) that doesn't exist locally
- Quick iteration: train, test on multiple checkpoints, download LoRA

## Available Training Models (as of May 2026)

| Model | Style | Notes |
|-------|-------|-------|
| **Tsubaki.2** | Anime stylized | The only model available. Not photorealistic. |

PixAI may add more base models over time. Tsubaki.2 produces anime-styled output.

## Key Differences from Local SDXL Training

1. **Anime style, not photorealistic** — Tsubaki.2 is anime-styled. LoRAs
   trained on it will produce anime-style generations. Positive prompts should
   include `anime style, masterpiece, best quality`. Negative prompts should
   include `photorealistic, photo, realistic` to prevent style bleed.

2. **Trigger word** — Use a short, unique token (e.g. `ehyra`) at the start of
   every training caption and generation prompt. PixAI DiT.2 triggers needed
   30+ chars describing visual features, but Tsubaki.2 works with shorter triggers.

3. **Dataset upload** — Upload images directly on PixAI's web UI. Supported
   formats: JPG, PNG. Recommended 16-61 images. Captions are auto-generated
   by PixAI but can be edited manually.

4. **Training params** — PixAI handles all hyperparameters. Users specify:
   - Number of training steps (e.g. 3000)
   - LoRA strength at generation time (0.7-0.85 recommended)
   - No dim/alpha/LR configuration exposed

5. **Output** — Downloads as `.safetensors` LoRA file (~82MB for 3000 steps).
   Can also be tested directly on PixAI with various checkpoint models.

## PixAI LoRA Testing

After training, PixAI lets you test your LoRA against multiple checkpoint models
simultaneously. The test generates one image per checkpoint with the same prompt.
Example checkpoint results from Ehyra XL LoRA test:

- Airtist Realistic XL
- CyberRealisticPony
- RealDream
- RealisticStockPhoto

All tested at 50 steps, CFG 6, Euler a sampler.

**Note:** Even "Realistic" checkpoints produce anime-styled output when the LoRA
was trained on Tsubaki.2. The LoRA's style dominates.

## Prompt Format for Tsubaki.2 LoRAs

### Base prompt template

```
[trigger_word], 1girl, [physical_traits], [outfit], [pose], [setting],
[lighting], anime style, detailed face, masterpiece, best quality
```

### Example — Ehyra

```
ehyra, 1girl, short voluminous black hair, blunt bangs, dark brown eyes,
sharp winged eyeliner, round thin-framed glasses, fair pale skin, small
black tattoo on upper chest, confident playful expression, slightly
parted lips, dark outfit, choker, moody atmosphere, dramatic lighting,
anime style, detailed face, masterpiece, best quality
```

### Negative prompt

```
photorealistic, photo, realistic, 3d render, blurry, low quality, deformed,
extra limbs, bad anatomy, watermark, text, signature, monochrome
```

### Style variants

| Variant | Key additions to positive | Key addition to negatives |
|---------|--------------------------|--------------------------|
| Neon/cyberpunk | `glowing cyan accents, neon-lit alley, rain reflections` | `bright, cheerful, daylight` |
| Casual/daylight | `white crop top, warm soft lighting, indoor scene` | `dark, moody, neon` |
| Gothic/dark fantasy | `gothic black dress, choker, moody shadows, candlelit` | `bright, modern, casual` |
| Mirror selfie | `phone in hand, mirror selfie, partial reflection` | `multiple people, group` |

## Downloaded LoRA Files

PixAI downloads go to the user's Windows Downloads folder by default.
Move them to ComfyUI for local use:

```bash
# Example: Ehyra LoRA
cp "/mnt/e/Users/Game_/Downloads/Ehyra_XL/checkpoint-e36_s684.safetensors" \
   ~/comfy/ComfyUI/models/loras/ehyra_xl.safetensors
```

## LoRAs Trained on PixAI

| LoRA | Trigger | Steps | Size | Model | Notes |
|------|---------|-------|------|-------|-------|
| Ehyra XL | `ehyra` | ~3000 | ~82MB | Tsubaki.2 | Anime-styled, 61 img dataset |
| KNQ_V1 | `knq` | — | — | Tsubaki.2 | — |
| RGTA_V1 | `rgta` | — | — | Tsubaki.2 | — |

Dataset for Ehyra: `~/comfy/ai-toolkit/dataset/images/ehyra_dataset/` (61 imgs, 85MB)
Download location: `E:\Users\Game_\Downloads\Ehyra_XL\`

## Pitfalls

- **Tsubaki.2 is anime-only** — You cannot get photorealistic output from a
  LoRA trained on Tsubaki.2, even with "realistic" checkpoint models at test
  time. The LoRA's learned style dominates.
- **No LoRA dim/alpha control** — PixAI doesn't expose network_dim or
  network_alpha. You get what the platform gives. For fine control, use local
  Kohya or AI-Toolkit.
- **Auto-captions may be generic** — PixAI auto-generates captions during
  upload. Always review and edit them to include your trigger word and
  specific physical traits.
- **Z-Image black output on RTX 3060** — Z-Image generation produces all-black
  images (NaN in uint4 quantization) on RTX 3060. Use PixAI or ComfyUI with
  Juggernaut/Pony instead.