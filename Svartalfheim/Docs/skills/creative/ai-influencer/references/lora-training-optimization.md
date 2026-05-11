# SDXL LoRA Training Optimization (2025-2026 Findings)

## Proven Parameters for Character LoRA (RTX 3060 12GB)

Based on iterative training of the Eir Niflheimr character LoRA and
analysis of community best practices (Reddit r/StableDiffusion, CivitAI
discussions, Kohya sd-scripts issues, 2025-2026).

### Recommended Config (AdamW — WORKS on CUDA 13/WSL)

```toml
[Network]
network_module = "networks.lora"
network_dim = 32
network_alpha = 16          # alpha = dim/2 → effective LR balance
network_dropout = 0.1       # prevents overfitting on small datasets

[Optimizer]
optimizer_type = "AdamW"    # NOT AdamW8bit — bitsandbytes broken on CUDA 13
learning_rate = 2e-4        # UNet LR
text_encoder_lr = 1e-4      # TE LR (half of UNet)
unet_lr = 2e-4
weight_decay = 0.01

[LR Schedule]
lr_scheduler = "cosine"
lr_warmup_steps = 100       # ~5-6% of total steps
min_lr_ratio = 0.1

[Training]
max_train_steps = 1800      # ~11 epochs × 16 images × 20 repeats
save_every_n_steps = 100    # granular checkpoint selection
train_batch_size = 1
gradient_checkpointing = true
mixed_precision = "bf16"
# NOTE: Do NOT use --full_bf16 — it is NOT a valid Kohya flag.

[Dataset]
resolution = "1024,1024"
enable_bucket = true
bucket_reso_steps = 64
min_bucket_reso = 512
max_bucket_reso = 2048
cache_latents = true
# ⚠️ DO NOT set cache_text_encoder_outputs = true when using
# shuffle_caption, keep_tokens, or caption_tag_dropout_rate.
# These augmentations modify captions per step, requiring fresh
# TEC outputs each step. Caching silently disables augmentation.
# For v2 optimized training, REMOVE cache_text_encoder_outputs
# and accept ~20% slower training for better quality.
keep_tokens = 1              # trigger word ALWAYS first
shuffle_caption = true
caption_tag_dropout_rate = 0.05  # 5% dropout → forced trigger dependency
                                 # NOT "tag_dropout" — that flag does not exist

[Noise]
min_snr_gamma = 5           # reduces noise bias in SDXL
```

### Alternative: Prodigy (adaptive LR — converges faster)

```toml
optimizer_type = "Prodigy"
learning_rate = 1.0
network_alpha = 1.0          # Prodigy NEEDS alpha=1.0
weight_decay = 0.01
max_train_steps = 1200       # Prodigy converges faster
```

Use Prodigy if AdamW doesn't converge after 800 steps. Prodigy adapts
its LR automatically but needs alpha=1.0 (not dim/2).

## Invalid / Non-existent Kohya CLI Flags

These flags do NOT exist in Kohya sd-scripts and will silently fail or error:

| Wrong Flag | Correct Alternative | Note |
|------------|---------------------|------|
| `--tag_dropout 0.05` | `--caption_tag_dropout_rate 0.05` | Different name entirely |
| `--weight_decay 0.01` | `--optimizer_args weight_decay=0.01` | Must be nested under optimizer_args |
| `--full_bf16` | `--mixed_precision bf16` | bf16 mixed precision is the flag; there is no "full bf16" |
| `--persistent_workers` | Omit it | Not supported by Kohya's data loader |
| `--min_lr_ratio 0.1` | `--lr_scheduler_args min_lr_rate=0.1` | Different argparse path |
| `--train_text_encoder=false` | `--network_train_unet_only` | Not a valid flag; use the shorthand |

Using any of these will either crash training or silently be ignored.

## Checkpoint Evaluation After Training

After training with `save_every_n_steps=100` (or 300), evaluate checkpoints:

1. **Copy all checkpoints** to ComfyUI loras directory:
   ```bash
   cp assets/lora_output/*.safetensors ~/comfy/ComfyUI/models/loras/
   ```

2. **Generate the SAME test prompt** with each checkpoint (same seed, same settings):
   - Use 2-3 prompt types: portrait, full-body, action/armor
   - Keep LoRA strength at 0.8 for evaluation
   - Use a fixed seed for reproducibility

3. **Evaluate on 4 criteria** (score 1-10):
   - **Face anatomy** — Are eyes/ears/nose proportional? No extra eyes or misplaced features?
   - **Character consistency** — Does the trigger word produce the intended character?
   - **Image quality** — Sharpness, color depth, no artifacts or noise patterns
   - **Artifact check** — No watermarks, text, double exposures, compositional errors

4. **Select the best checkpoint** — Usually NOT the final step:
   - Steps 600-1400 are the sweet spot for character LoRA with 16-30 images
   - Later steps (1600-1800+) may overfit: character is consistent but flexibility drops
   - Earlier steps (300-500) may underfit: character is weakly captured
   - If two checkpoints tie, prefer the later one (more training = less overfitting risk)

5. **Rename and deploy** the winner:
   ```bash
   cp ~/comfy/ComfyUI/models/loras/eir_niflheimr_v2_lora-step001400.safetensors \
      ~/comfy/ComfyUI/models/loras/eir_niflheimr_v2_best.safetensors
   ```

## Why These Parameters

| Parameter | Value | Why |
|-----------|-------|-----|
| `dim=32` | 32 | Sweet spot for character consistency. dim=16 too low (loses detail), dim=64 overfits on small datasets |
| `alpha=16` | dim/2 | Balanced effective LR. alpha=dim → full LR (risk of instability). alpha=1 → very low effective LR |
| `dropout=0.1` | 0.1 | Prevents overfitting on 16-30 image datasets. Forces network to generalize |
| `min_snr_gamma=5` | 5 | SDXL tends to over-emphasize noisy timesteps. This weights loss toward clean-signal steps |
| `keep_tokens=1` | 1 | Ensures trigger word is never shuffled away from position 1 in caption |
| `tag_dropout=0.05` | 5% | Random drops non-trigger tags, forcing the model to rely on trigger word |
| `cosine` | — | Smoother LR decay than constant. Warmup prevents early instability |
| `steps=1800` | ~11 epochs (16 imgs × 20 repeats = 320 steps/epoch) | Enough to learn character without overfitting. Best checkpoint usually at step 800-1400 |
| `caption_tag_dropout_rate` | 0.05 | Correct Kohya flag name. NOT "tag_dropout" (that flag doesn't exist) |
| `AdamW` not `AdamW8bit` | — | bitsandbytes crashes on CUDA 13.x WSL with `libnvJitLink.so.13` error. Use plain AdamW |

## Caption Best Practices

### Format (CRITICAL)
```
trigger_word, 1girl, solo, [physical_description], [outfit], [setting], [lighting], [composition], [quality_tags]
```

### Rules:
1. **Trigger word ALWAYS first** — `eir_niflheimr, 1girl, ...` (enforced by `keep_tokens=1`)
2. **Consistent physical description** — repeat the same 3-4 core tags in EVERY caption
3. **Vary outfit/setting/lighting** — this is where diversity comes from
4. **Quality tags last** — `masterpiece, best quality, ...` always at the end
5. **No contradictory tags** — don't say "black hair" and "silver hair" in same caption

## Master Negative Prompt

For character LoRA generations. Use in EVERY generation:

```
cartoon, anime, 3d render, deformed, bad anatomy, bad hands, missing fingers,
extra digits, extra limbs, blurry, low quality, worst quality, watermark, text,
logo, signature, amputated, duplicate, morbid, mutilated, poorly drawn face,
mutation, disfigured, out of frame, excess skin, poorly drawn eyes, bad
proportions, distorted face, ugly, tiling, frame, grainy, noisy, oversaturated,
undersaturated, cropped, jpeg artifacts, simple background, flat lighting,
overexposed, underexposed, harsh shadows, harsh highlights, floating limbs,
severed limbs, malformed hands, long neck, cross-eyed, disproportionate
```

## Checkpoint Evaluation

After training with `save_every_n_steps=100`, you'll have ~18 checkpoints:

1. Copy each to `~/comfy/ComfyUI/models/loras/`
2. Generate SAME test prompt with EACH checkpoint (same seed, same settings)
3. Compare: face consistency, detail preservation, artifacts, creative flexibility
4. Best checkpoint is usually NOT the last — it's where character is recognizable AND model can still vary clothing/setting (steps 800-1400 typically)

## LoRA Strength Guidance

| Strength | Effect |
|----------|--------|
| 0.5-0.6 | Subtle influence, character barely recognizable |
| 0.7-0.8 | Sweet spot — recognizable but flexible |
| 0.9-1.0 | Strong adherence — may reduce creative flexibility |

Start at 0.8 for evaluation, then adjust based on results.