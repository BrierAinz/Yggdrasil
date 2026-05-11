---
name: ai-influencer
description: Create and manage AI influencer projects — character design, content generation pipeline, platform strategy, caption automation, and monetization. Covers the full lifecycle from concept to posting.
version: 1.0.0
author: Assistant
tags: [ai-influencer, content-creation, stable-diffusion, flux, lora, instagram, social-media]
---

# AI Influencer Project Setup

End-to-end guide for creating and managing an AI influencer — a fictional digital persona that generates and posts content on social media platforms.

## When to Use This Skill

- Creating a new AI influencer from scratch
- Setting up the content generation pipeline (SD/Flux + LoRA + batch generation)
- Designing character sheets and reference materials
- Planning platform strategy and posting cadence
- Automating caption generation with LLM batch mode
- Structuring an AI influencer project directory

## Project Structure

```
AI-Influencer/
├── README.md                  # Project vision, phases, stack
├── CHARACTER.md               # Full character design sheet
├── PIPELINE.md                # Content generation pipeline architecture
├── PLATFORMS.md               # Platform strategy per channel
├── MONETIZATION.md             # Revenue tiers and projections
├── .env                       # API keys (gitignored)
├── .gitignore                 # Never commit .env, generated images cache
├── config/
│   ├── generation.toml        # SD/Flux model config, samplers, LoRA, upscaling
│   └── posting.toml           # Schedule, hashtags, caption style
├── scripts/
│   ├── generate.py             # Batch content generation (prompts → images)
│   ├── caption_generator.py    # LLM-powered caption + hashtag generation
│   ├── watermark.py           # Subtle branding overlay
│   └── analytics_tracker.py   # JSON metrics tracker per platform
├── assets/
│   ├── reference_sheets/       # Character reference images (20-30 base poses)
│   ├── lora/                   # Trained LoRA weights
│   └── templates/              # Post templates (story, carousel, reel)
├── content/
│   ├── posts/                  # Generated content ready to post
│   ├── reels/                  # Short video content
│   └── archive/                # Posted content (for consistency tracking)
└── analytics/
    └── metrics.json            # Growth tracking data
```

## Phase 0: Character Design (CRITICAL — Do This First)

The character defines everything. A generic "hot girl" won't stand out. Choose a **niche aesthetic** with lore depth.

### Character Sheet Must-Haves

1. **Name** — Short, memorable, available across platforms. Norse mythology names work well.
2. **Origin story** — Not "AI model", but a mythical realm (e.g., Svartalfheim = dark elves)
3. **Visual identity** — Hair, eyes, skin, build, signature outfit, color palette, accessories
4. **Personality** — 3-5 traits with textual descriptions for prompt consistency
5. **Voice style** — How they write (tone, vocabulary, emoji usage, humor style)
6. **Aesthetic pillars** — 3-4 visual themes that recur (e.g., violet + silver + runes + mist)
7. **Taboo list** — What they NEVER do (consistency is key)
8. **Negative prompts** — What to exclude from generation (modern tech, skinny body type, etc.)

### Building Character Sheets from Reference Images

When the user provides reference photos/images for a character:

1. **Copy images** to `dataset/images/<character>_reference/` with clean filenames (`ref_01.jpg`, etc.)
2. **Analyze each image** with vision — describe face, eyes, hair, skin, body, clothing, vibe in extreme detail
3. **Extract INVARIANT features** — traits that appear in every image (face shape, eye color, skin tone, freckles, body build). These go into the LoRA trigger word description.
4. **Identify VARIABLE features** — traits that change across images (hair color/style, clothing, setting, lighting). These define style categories the LoRA should NOT learn as invariants.
5. **Create a trigger word** — a non-English, alphanumeric token (e.g., `3hyr4_p3r50n`) that won't collide with common English words. Used in every caption.
6. **Define style categories** — group variable looks into themes (dark fantasy, cyberpunk, candid/IG, boudoir, streetwear) with keyword sets for each.
7. **Build Pony V6 XL prompt templates** — quality tags (`score_9, score_8_up, score_7_up, source_photo`) + trigger word + invariant physical description + style keywords.
8. **Write CHARACTER.md** — full character sheet with identity table, invariant traits section, variable traits section, style categories, prompt templates, negative prompts, and dataset spec.

**Key LoRA training insight:** The LoRA must learn INVARIANT features (face, eyes, freckles, body build) while allowing VARIABLE features (hair color, clothing, setting) to remain flexible. If the dataset is all one hair color with one outfit, the LoRA will fuse those into the trigger word and struggle to generalize. Include variety in the training set.

### Prompt Engineering for Character

Build a reusable prompt template:

```
[character_desc], [hair_style], [eye_color], [outfit], [setting], [lighting], [aesthetic_keywords], [quality_tags]
```

Example for "Eir" (dark fantasy):
```
masterpiece, best quality, 1girl, eir_niflheimr, pale skin, long silver-white hair with violet tips, violet eyes with runic glow, black corset with silver runic embroidery, flowing dark violet cape, forest glade at twilight, volumetric lighting, ethereal mist swirling, dark fantasy, mysterious atmosphere
```

**Negative prompt** (always include):
```
modern, phone, screenshot, watermark, text, blurry, low quality, deformed, nsfw, nude
```

**Pony V6 XL prompt template** (for NSFW/influencer characters):
```
score_9, score_8_up, score_7_up, rating_explicit, [TRIGGER_WORD], 1girl, [INVARIANT_TRAITS], [STYLE_KEYWORDS], [SCENE_DESCRIPTION], [LIGHTING], [QUALITY_TAGS]
```
Example: `score_9, score_8_up, score_7_up, rating_explicit, 3hyr4_p3r50n, 1girl, freckles, ice blue eyes with amber ring, dark brown wavy hair, off-shoulder white blouse, boudoir, soft natural lighting, detailed skin`

**Trigger words must be non-English alphanumeric tokens** (e.g., `3hyr4_p3r50n`, `3hyr4_nsfx`) to avoid collision with common prompt words. Always include the trigger word as the FIRST token in every training caption and generation prompt.

## Phase 1: Reference Sheet Generation

Before LoRA training, generate 20-30 base reference images:

1. **5 headshot variations** — different expressions, angles, lighting
2. **5 full-body poses** — standing, sitting, dynamic action
3. **5 outfit variations** — signature outfit + seasonal alternates
4. **5 setting moods** — indoor, outdoor, fantasy landscapes, abstract backgrounds
5. **5 close-up details** — eyes, hands, accessories, hair detail, fabric texture
6. **5 action shots** — holding items, magic effects, dynamic poses

### Create-From-Scratch Reference Generation (No Existing LoRA)

When starting a **brand new character** with no existing LoRA, generate reference images using just the base model + detailed prompts. This is the "blank slate" approach:

1. **Choose base model**: ChilloutMix (SD1.5) for Asian characters, Juggernaut XL for Western/photorealistic
2. **Define character invariants** in prompts: hair, eyes, skin, markings, body type — these go in EVERY prompt
3. ** Generate 5 face candidates** (same prompt, different seeds = 5 different face variations) **BEFORE generating the full dataset**. The user picks THE ONE face they like. This avoids wasting time generating 30 images of a face nobody wants.
4. **Once face is selected**, use that seed's face as the reference and generate 25-30 variation images (varying expression, pose, outfit, setting, lighting) — these create dataset diversity
5. **Curate**: Select 25-30 best images with consistent face/features
6. **Train LoRA**: Use curated set to train a dedicated LoRA on the same base model

**Why face-first selection matters**: Without an existing LoRA, each seed produces a different face even with identical prompts. If you generate 30 images upfront, you get ~30 different faces — useless for LoRA training (which needs the SAME face across varied poses). The face-first approach ensures all dataset images depict the chosen face.

**Flux.1 Dev GGUF Q8 (recommended for photorealism)**:
- Resolution: 1024×1024 (native), 1536×640 (ultra-wide full-body)
- Steps: 20, CFG: 1.0, Sampler: euler, Scheduler: simple
- Uses `GGUFLoaderKJ` (NOT `UnetLoaderGGUF`) + `DualCLIPLoader(type="flux")` + `ModelSamplingFlux` + `FluxGuidance(guidance=3.5)` + `VAELoader(vae_name="ae.safetensors")`
- Negative prompt: empty CLIPTextEncode node (Flux doesn't use negative conditioning)
- ~3-4 min per image on RTX 3060 12GB
- See comfyui skill pitfall #50 for complete node chain and validated settings

**SD1.5 + ChilloutMix (alternative for Asian face consistency)**:
- Resolution: 512×768 portrait, 768×512 landscape (NOT 768×1344 — SD1.5 native is 512)
- Steps: 35-40 (SD1.5 needs more steps than SDXL)
- CFG: 7
- Sampler: euler_ancestral or dpmpp_2m karras
- VAE: vae-ft-mse-840000.safetensors (NOT SDXL VAE)
- Prompt format (Danbooru-style tags work best):
  ```
  1girl, [CHARACTER_INVARIANTS], [EXPRESSION], [OUTFIT], [SETTING], [LIGHTING], photorealistic, 8k, masterpiece, best quality
  ```
- Negative prompt:
  ```
  anime, cartoon, illustration, 3d render, painting, blurry, deformed, ugly, duplicate, watermark, text, bad anatomy, extra fingers, missing fingers, mutated hands, low quality, worst quality
  ```

**Critical**: Do NOT cross architectures. SDXL LoRAs on SD1.5 produce poor body consistency even at reduced weights. Train the LoRA on the same architecture as your base model. Flux LoRAs require Flux base, SD1.5 LoRAs require SD1.5 base.

### Face-Consistent Reference Generation with IPAdapter FaceID

For characters with existing reference photos (not text descriptions), use ComfyUI + IPAdapter FaceID to generate consistent face images across varied poses/outfits/settings. This produces a higher-quality LoRA training dataset than text-only generation.

**Why NOT Pony V6 XL for training datasets:** Pony V6 XL produces cartoonish/anime-looking generations even with `source_photo` and `photorealistic` tags. For LoRA training, you want photorealistic outputs that preserve the reference face's realism. Use Juggernaut XL v9 + IPAdapter FaceID instead — it produces 8/10 photorealism vs Pony's 4/10.

### Face-Consistent Reference Generation with PuLID (Flux ONLY)

For **Flux.1 Dev** models, IPAdapter FaceID does NOT work (IPAdapter Plus only supports SD1.5/SDXL). Use **PuLID** (Pose-agnostic and Lightweight Identity) instead — a zero-shot face consistency method that takes one reference face photo and maintains identity across varied generations.

**Why PuLID for Flux datasets:**
- Zero-shot: no LoRA training needed, just provide one reference face photo
- Less composition dominance than IPAdapter — body/outfit prompts work better
- Works natively with Flux.1 Dev GGUF Q8 on RTX 3060 12GB
- Ideal for AI influencer dataset generation: generate 25-30 face-consistent variations, then train a dedicated Flux LoRA for permanent consistency

**Setup:** See comfyui skill pitfall #49 for full installation instructions (ComfyUI-PuLID-Flux custom node, 3 model downloads: PuLID Flux v0.9.1, EVA-CLIP, InsightFace AntelopeV2).

**⚠️ PuLID API parameter names differ from UI display — ALWAYS verify via `/object_info`:**
The #1 cause of PuLID workflow failures (HTTP 400) is mismatched parameter names. Known API-vs-UI mismatches (May 2026):
- `PulidFluxModelLoader`: use `pulid_file` (NOT `pulid_name`)
- `PulidFluxEvaClipLoader`: use `eva_file` (NOT `eva_name`)
- `PulidFluxInsightFaceLoader`: set `provider: "CUDA"` explicitly
- `ApplyPulidFlux`: `weight`, `start_at`, `end_at`, `fusion` are correct as documented
- `KSampler`: MUST include `denoise: 1.0` explicitly (omitting causes validation error in some versions)

Always verify parameter names before building workflows:
```bash
curl -s http://127.0.0.1:8188/object_info/PulidFluxModelLoader | python3 -m json.tool
```

**PuLID + Flux workflow pattern for dataset generation:**
1. Choose the best face candidate (generate 5 candidates first, pick THE ONE)
2. Use that face as PuLID reference image
3. Generate 25-30 variations with varied prompts (poses, outfits, settings, lighting)
4. PuLID keeps face identity consistent across all variations
5. Curate best images, auto-caption with trigger word, train Flux LoRA

**PuLID weight guidance:**
- `weight=1.0`: Strong face adherence — face matches reference very closely
- `weight=0.8`: Balanced — good face match with more style flexibility
- `weight=0.6-0.7`: Subtle — face influence present but allows more prompt control
- Start at 1.0 and reduce if the face looks "stuck" or over-fitted

**SD1.5 + ChilloutMix for Asian face consistency:** The Reddit/StableDiffusion community consensus (2024-2025) is that SD1.5 + ChilloutMix (NiPrunedFp16Fix, CivitAI ID 6424) produces far more consistent Asian faces than ANY SDXL model. This is the recommended pipeline for AI influencers with Asian character designs. Key technical notes:
- Native resolution: 512×768 (portrait), NOT 768×1344 SDXL
- Required VAE: `vae-ft-mse-840000.safetensors` (NOT SDXL VAE)
- LoRA weights reduced: SDXL LoRA on SD1.5 base → use 0.6 face / 0.5 body (instead of 0.8/0.6)
- For best results, train a dedicated SD1.5 LoRA on ChilloutMix base (cross-architecture LoRA use works but is suboptimal)

**Model comparison for AI influencer consistency (validated testing):**
| Model | Face Consistency | Body Consistency | Overall | Notes |
|-------|-----------------|------------------|---------|-------|
| PixAI PhotoPedia XL (cloud) | 9/10 | 8/10 | Best | Cloud-only, can't run locally |
| ChilloutMix (SD1.5) | 8/10 | 7/10 | Excellent | Community gold standard for Asian faces |
| RealVisXL V4 (SDXL) | 8/10 | 2/10 | Poor | Good face, terrible body (crops mid-thigh) |
| Multi-LoRA RealVisXL + Face+Body | 7/10 | 5/10 | Mixed | Stacking helps body but introduces artifacts |
| Juggernaut XL v9 (SDXL) | 6/10 | 3/10 | Poor | Inconsistent faces, painterly style |

**Required models:**
- Juggernaut XL v9 checkpoint → `models/checkpoints/`
- `ip-adapter-faceid_sdxl.bin` (NOT PlusV2 — see pitfall) → `models/ipadapter/`
- `ViT-H-14.s32B.b79K.safetensors` (CLIP Vision) → `models/clip_vision/` (MUST use this exact filename — ComfyUI regex requires it)
- InsightFace `buffalo_l` → `models/insightface/models/buffalo_l/`
- FaceID LoRA symlink: `ln -s models/ipadapter/ip-adapter-faceid_sdxl_lora.safetensors models/loras/faceid.sdxl.lora.safetensors`

**API workflow (use `IPAdapterUnifiedLoaderFaceID`, NOT manual node chain):**
```
CheckpointLoaderSimple (Juggernaut-XL_v9)
→ IPAdapterUnifiedLoaderFaceID (preset: "FACEID", lora_strength: 0.6, provider: "CUDA")
→ LoadImage (reference face photo)
→ IPAdapterFaceID (image, weight: 0.8-0.9, weight_type: "linear", embeds_scaling: "K+V")
→ CLIPTextEncode (positive prompt)
→ CLIPTextEncode (negative prompt)
→ EmptyLatentImage (768x1024)
→ KSampler (steps: 30, cfg: 7.0, sampler: dpmpp_2m, scheduler: karras)
→ VAEDecode → SaveImage
```

The unified loader returns `(MODEL, ipadapter)` — pass both outputs to `IPAdapterFaceID`. Do NOT pass clip_vision or insightface separately.

**Critical pitfalls:**
- **PlusV2 requires ViT-bigG-14 (1664-dim, ~3.5GB), NOT ViT-H or ViT-L.** Using PlusV2 with ViT-H gives `size mismatch for perceiver_resampler.proj_in_weight: torch.Size([2048, 1280]) vs torch.Size([2048, 1664])`. Use the normal FaceID model with ViT-H, or download ViT-bigG-14 for PlusV2.
- **CLIP Vision filename must match regex** — `clip_vision_vit_h.safetensors` does NOT work. Rename/symlink to `ViT-H-14.s32B.b79K.safetensors`.
- **Manual node chain (ModelLoader+CLIPVisionLoader+InsightFaceLoader) has path resolution issues in API mode.** Use `IPAdapterUnifiedLoaderFaceID` which handles all model loading automatically.

**Batch generation script pattern:**
- Upload reference face images to ComfyUI input dir
- For each image × each prompt variation, submit via `/api/prompt`
- Include the face image node in the workflow JSON
- Use 300s timeout per image (FaceID is slower than standard txt2img)
- On RTX 3060: ~40s per generation
- Weight variations (0.80-0.90) and LoRA strength (0.5-0.7) across prompts give dataset diversity

### SD/Flux Generation Config

Use `config/generation.toml`:

```toml
[model]
name = "juggernautXL_v9Rundiffusion"  # Photorealistic
# name = "FLUX.1-dev"                  # Artistic/creative
sampler = "DPM++ 2M Karras"
steps = 30
cfg_scale = 7

[dimensions]
portrait = [768, 1024]    # Instagram portrait
landscape = [1024, 768]   # Landscape/carousel
square = [1024, 1024]     # Square posts
story = [1080, 1920]      # Stories/reels

[lora]
enabled = false  # Enable after training
name = "eir_niflheimr"
weight = 0.7

[upscaling]
enabled = true
model = "4x-UltraSharp"
scale = 2

[watermark]
enabled = true
text = "@eir.creates"
position = "bottom-right"
opacity = 0.15
```

## Phase 2: LoRA Training

### Option A: Local Training (RTX 3060 12GB+) — Kohya sd-scripts

You can train SDXL LoRA locally with ≥12GB VRAM. Uses Kohya's
`sdxl_train_network.py` (not the GUI).

See `references/kohya-lora-training.md` for the full step-by-step guide
including the proven command, dataset structure, config template, and all
pitfalls discovered through iterative debugging.

See `references/lora-training-optimization.md` for the optimized SDXL LoRA
parameters (min_snr_gamma, network_dropout, tag_dropout, AdamW vs Prodigy),
caption best practices, negative prompt catalog, checkpoint evaluation
workflow, and LoRA strength tuning — based on 2025-2026 community best
practices and iterative Eir Niflheimr training.

**Quick start (proven on RTX 3060 12GB):**

```bash
# 1. Clone Kohya sd-scripts
cd /path/to/AI-Influencer/tools
git clone https://github.com/kohya-ss/sd-scripts.git kohya_ss
cd kohya_ss

# 2. Create venv — use uv (pip/venv breaks on WSL with python3.12-venv)
uv venv venv --python 3.12
uv pip install --python venv/bin/python torch==2.6.0 torchvision==0.21.0 \
  --index-url https://download.pytorch.org/whl/cu124
# ⚠ cu124 ONLY — cu126's nvidia-nvshmem-cu12 dependency times out on WSL2
uv pip install --python venv/bin/python -r requirements.txt
uv pip install --python venv/bin/python xformers  # optional but recommended

# 3. Curate dataset (16-30 imgs, 1024x1024)
#    Dataset structure (CRITICAL — Kohya requires subdirectories):
#    assets/lora_dataset/
#    ├── dataset_config.toml
#    └── eir_niflheimr/          ← class_name subfolder REQUIRED
#        ├── image_001.png
#        ├── image_001.txt       ← matching .txt caption (same basename)
#        ├── image_002.png
#        ├── image_002.txt
#        └── metadata.json      ← optional but recommended

# 4. Run training (see references/kohya-lora-training.md for full command)
venv/bin/python sdxl_train_network.py \
  --pretrained_model_name_or_path /path/to/sd_xl_base_1.0.safetensors \
  --dataset_config /path/to/dataset_config.toml \
  --output_dir /path/to/lora_output \
  --output_name eir_niflheimr_lora_r32 \
  --network_module networks.lora \
  --network_dim 32 --network_alpha 16 \
  --network_train_unet_only \
  --learning_rate 1e-4 --lr_scheduler cosine --lr_warmup_steps 100 \
  --max_train_epochs 15 --save_every_n_epochs 5 \
  --mixed_precision bf16 --save_precision bf16 \
  --cache_latents --cache_text_encoder_outputs \
  --gradient_checkpointing --sdpa --seed 42
```

**Critical pitfalls (learned the hard way — 5+ failed attempts):**

1. **Dataset must be in subdirectories** — Kohya rejects flat directories.
   Structure: `train_data_dir/class_name/images.png + images.txt`. The
   `class_name` subfolder is mandatory or you get "no valid subset found."
2. **`--cache_text_encoder_outputs` conflicts with training text encoder** — use
   `--network_train_unet_only` (NOT `--train_text_encoder=false` which isn't
   a valid flag). Caching TEC outputs and training TEC simultaneously errors.
3. **`--xformers` requires the xformers package** — if missing, use `--sdpa`
   instead (built into PyTorch 2.0+). Don't pass `--xformers` flag without
   the package installed or training crashes on import.
4. **Kill ComfyUI before training** — ComfyUI uses ~7.8GB VRAM. On a 12GB
   card you need that headroom. `kill $(pgrep -f "ComfyUI/main.py")` or
   similar.
5. **Use `bf16` not `fp16` for SDXL** — SDXL works better with bf16 mixed
   precision. fp16 can cause NaN losses on some checkpoints.
6. **Always use `uv pip install --python venv/bin/python`** — don't activate
   the venv with `source` on WSL; use the full python path for reliability.
7. **`bitsandbytes` fails with CUDA 13.x on WSL** — `AdamW8bit` optimizer
   requires `bitsandbytes`, which crashes with `libnvJitLink.so.13: cannot
   open shared object file: No such file or directory` on CUDA 13.x runtimes
   in WSL. **Fix: use `AdamW` instead of `AdamW8bit`** — it works fine on
   12GB VRAM for dim=32 LoRA. Alternatively, install `nvidia-cuda-runtime-cu13`
   into the Kohya venv, but this doesn't always resolve the issue.

Output: `.safetensors` LoRA file → copy to ComfyUI `models/loras/`

### Option B: AI Toolkit (Local — Recommended for New Projects)

[ostris/ai-toolkit](https://github.com/ostris/ai-toolkit) — 10.4k-star toolkit
with CLI + web UI (Next.js port 8675) + built-in auto-captioning (Qwen3VL).

**Advantages over Kohya:**
- Built-in Qwen3VL auto-captioning (no manual BLIP/WD14 tagging)
- Modern web UI for config + monitoring
- Supports FLUX, Wan video, LTX video LoRAs (Kohya does not)
- Quantized training (4-bit) for FLUX on 12GB VRAM
- LoRA + LoKr support in one tool

**Requires its own venv** (diffusers from git, transformers 5.5.3 conflict
with ComfyUI's 5.7.0).

**Critical: Use `uv venv` NOT `python3.13 -m venv`** — On WSL, `python3.13 -m venv`
creates a broken hybrid venv where `pip` shebangs resolve to python3.13 but the
`python` symlink points to python3.12, causing packages to install into the wrong
Python. Always create venvs with:
```bash
uv venv --python 3.12 /path/to/ai-toolkit/.venv
uv pip install --python .venv/bin/python torch==2.9.1 torchvision torchaudio \
  --index-url https://download.pytorch.org/whl/cu128
uv pip install --python .venv/bin/python -r requirements_base.txt
```
**`uv pip install` is 5-10x faster than pip** for large packages. Use
`--python .venv/bin/python` explicitly instead of activating venv + pip.

**PyTorch CUDA:** cu128 and cu130 both work on WSL2. Only cu126 fails
(nvidia-nvshmem-cu12 timeout). Use cu128 for ai-toolkit.

See `references/ai-toolkit-lora-training.md` for full setup, YAML configs,
quantized FLUX training, auto-captioning, and RTX 3060 benchmarks.

### Option C: Kohya_ss on RunPod (A100)

Use RunPod with A100 ($1.14/hr) for fast LoRA training:

```bash
# 1. Launch RunPod with kohya_ss image
# 2. Upload 20-30 reference images (512x512 or 768x768 minimum)
# 3. Caption each image (use BLIP or manual captions)
# 4. Training settings:
#    - Network dim/alpha: 32/16
#    - Learning rate: 1e-4 (text encoder), 5e-5 (unet)
#    - Epochs: 10-15
#    - Batch size: 2
#    - Gradient accumulation: 4
#    - Mixed precision: fp16
# 5. Monitor loss — should decrease steadily, stop if diverging
```

Output: `.safetensors` LoRA file → place in `assets/lora/`

## Phase 3: Content Generation Pipeline

### Batch Generation Script

`scripts/generate.py` handles the full pipeline:

```
1. Load prompt templates from config
2. Generate images with SD/Flux + LoRA
3. Upscale with 4x-UltraSharp
4. Apply watermark
5. Generate metadata JSON (prompt, seed, date, tags)
6. Optionally generate caption via Lilith batch mode
```

### Caption Generation via Lilith Batch

Use Lilith's `--batch` mode for automated caption writing:

```bash
# Generate a caption for a generated image
python3 -m Lilith.batch "Write an Instagram caption for a dark fantasy portrait of Eir, a silver-haired artisan from Svartalfheim. Tone: mysterious, poetic. Include 15 relevant hashtags. Max 2200 chars." --batch-json --batch-no-tools

# Generate multiple captions in a loop
for img in content/posts/*.png; do
    python3 -m Lilith.batch "Write a short poetic caption (under 300 chars) for: $(basename $img). Style: dark fantasy, cryptic, evocative. Add 5 niche hashtags." --batch-json --batch-no-tools
done
```

### Posting Schedule

Use `config/posting.toml` for cadence:

| Day | Platform | Time | Content Type |
|-----|----------|------|-------------|
| Mon-Wed-Fri | Instagram | 7pm | Portrait/gallery |
| Tue-Thu | TikTok | 3pm | Reel/transition |
| Daily | Twitter/X | 12pm | WIP/teaser |
| Sat | Patreon | — | Exclusive/tutorial |
| Sun | Reddit | 10am | Community post |

## Phase 3.5: Video Content (AnimateDiff)

AnimateDiff Evolved in ComfyUI generates short animated clips from still LoRA
characters. This is essential for Reels/TikTok/Twitter video content.

### Setup

1. Install AnimateDiff Evolved: `cd ~/comfy/ComfyUI/custom_nodes && git clone https://github.com/Kosinkadink/ComfyUI-AnimateDiff-Evolved.git`
2. Download motion module: `mm_sdxl_v10_beta.ckpt` (907MB) from HuggingFace `guoyww/animatediff` → place in `custom_nodes/ComfyUI-AnimateDiff-Evolved/models/`
3. **Restart ComfyUI completely** — custom nodes only load on startup, not hot-reload
4. Verify: `curl -s http://localhost:8188/object_info | python3 -c "import sys,json; d=json.load(sys.stdin); ad=[k for k in d if 'ADE_' in k or 'AnimateDiff' in k]; print(f'AnimateDiff nodes: {len(ad)}')"` — should show 100+ nodes

### Video Generation Parameters

| Parameter | Recommended | Notes |
|-----------|------------|-------|
| Resolution | 512x512 | SDXL+AnimateDiff+LoRA uses ~8-9GB VRAM at 512x512 |
| batch_size (frames) | 16 | More frames = more VRAM; 16 frames is stable on 12GB |
| steps | 20 | 20-25 for quality; more = slower |
| cfg | 7.5 | Standard for character prompts |
| fps | 8 | 16 frames / 8fps = 2 second clips |
| sampler | euler_ancestral | Good motion diversity |
| LoRA strength | 0.8 | Same as still images |

### WEBP → MP4 Conversion

ComfyUI outputs animated WEBP. Most social platforms require MP4:

```python
from PIL import Image
import subprocess
img = Image.open("input.webp")
for i in range(img.n_frames):
    img.seek(i)
    img.convert('RGB').save(f"frames/frame_{i:04d}.png")
subprocess.run(["ffmpeg", "-y", "-framerate", "8", "-i", "frames/frame_%04d.png",
    "-c:v", "libx264", "-pix_fmt", "yuv420p", "-crf", "23",
    "-vf", "scale=512:512:flags=lanczos", "-an", "output.mp4"])
```

If `ffmpeg` is not installed system-wide, use `imageio-ffmpeg`:
`pip install imageio imageio-ffmpeg`, then `imageio_ffmpeg.get_ffmpeg_exe()` for
the binary path.

### Motion Prompt Tips

Add motion keywords to the positive prompt:
- Hair/body movement: "hair flowing in wind", "gentle head turn"
- Particles: "snow falling", "frost particles floating", "magical sparks drifting"
- Atmosphere: "breathing animation", "candlelight flickering", "aurora shifting"

Negative prompt should include `static, still, frozen` to encourage motion.

## Phase 3.6: Content Inventory & Publishing

### Content Directory Structure

```
outputs/
├── feed_batch_v2/          # 18+ feed post images (832x1216, 1216x832)
├── content_bank_v2/        # 17+ carousel + scene images
├── stories_highlights_v2/  # 12+ story (768x1344) + highlight (512x512) images
├── profile_assets/         # 6 images: avatar, banner, story covers, highlight icons
├── profile_variations/     # 5 alternatives: 3 avatars + 2 banners
├── videos_v2/              # 7+ AnimateDiff clips (WEBP + MP4)
└── eval_checkpoints/       # LoRA evaluation set (not for publication)
```

### Publishing Automation (CLI)

A `publish.py` script manages content inventory and posting:

```bash
python scripts/publish.py status              # Show content inventory
python scripts/publish.py calendar            # Show posting schedule
python scripts/publish.py generate-captions   # Extract all captions from content plan
python scripts/publish.py post-x --image <path> --text <caption>  # Post to X/Twitter
python scripts/publish.py post-x-batch --dry-run  # Preview batch post to X
python scripts/publish.py schedule            # Show optimal posting times
```

X/Twitter posting uses `xurl` CLI (requires one-time OAuth setup).
Instagram posting is manual (recommended for better algorithm reach).

### xurl Setup (One-Time)

```bash
curl -fsSL https://raw.githubusercontent.com/xdevplatform/xurl/main/install.sh | bash
xurl auth apps add eir-creates --client-id <ID> --client-secret <SECRET>
xurl auth oauth2 --app eir-creates  # Opens browser for OAuth
xurl auth default eir-creates
xurl whoami  # Verify
```

## Phase 4: Platform Strategy

### Anti-Ban Guidelines (CRITICAL)

- **Never post more than 3x/day** on any platform initially
- **Vary posting times** ±2 hours from schedule
- **Don't use banned hashtags** — check platform's current list
- **Engage authentically** — reply to comments, like similar accounts
- **Use human-like cadence** — gaps between posts, not burst-then-silence
- **Rotate content types** — don't post the same angle/pose repeatedly
- **Instagram**: Use carousel format (5-10 slides) for algorithm boost
- **TikTok**: Use trending sounds, keep under 60s, strong first 3 seconds
- **Twitter/X**: Quote-tweet your own Instagram posts, engage in art community threads
- **Reddit**: Post in relevant subreddits FIRST, then share to your own profile

### Platform-Specific Notes

**Instagram** (primary)
- Feed: 768x1024 portrait, high quality
- Stories: 1080x1920, polls/questions for engagement
- Reels: 9:16, 15-30s, trending audio
- Bio: link-in-bio to Patreon

**TikTok** (growth engine)
- 9:16 vertical only
- Trending sounds + transitions
- "How I made this" behind-the-scenes format works well

**Patreon** (monetization)
- Tier 1 ($3): Early access, WIPs
- Tier 2 ($7): Full res, PSD files, tutorials
- Tier 3 ($15): Custom commissions, 1-on-1 chat

**CivitAI** (model sharing)
- Share LoRA checkpoints (builds authority in the community)
- Link back to Instagram in model descriptions

## Phase 5: Monetization

### Revenue Streams (Chronological Priority)

1. **Patreon subscriptions** (Month 1-2) — start at $3/$7/$15 tiers
2. **Commission slots** (Month 2-3) — limited custom work via Ko-fi
3. **CivitAI LoRA sales** (Month 3-4) — if LoRA is unique enough
4. **Print-on-demand merchandise** (Month 4-6) — Redbubble, TeePublic
5. **Brand collaborations** (Month 6+) — after 5K+ followers
6. **OnlyFans/Fansly** (Month 8+, if comfortable) — exclusive artistic content

### Cost Estimates

| Item | Monthly Cost |
|------|-------------|
| RunPod A100 (LoRA training, batch gen) | ~$20-40 |
| Instagram scheduling tool | $0-15 |
| Domain + hosting | $10 |
| Midjourney/SD backup | $0 (local) |
| **Total** | **$30-65/month** |

### Growth Targets

| Milestone | Timeline | Revenue |
|-----------|----------|---------|
| 100 followers | Month 1 | $0 |
| 1,000 followers | Month 3 | $30-50/mo (Patreon) |
| 5,000 followers | Month 6 | $150-300/mo |
| 10,000 followers | Month 9 | $500-1000/mo |

## Social Media Research Findings (2025-2026)

Key findings from Instagram/TikTok algorithm analysis:

1. **Carousel posts (5-10 slides)** = 3x reach vs single image on Instagram
2. **Process/BTS content** = 3-5x more engagement than polished final images
3. **Character-driven accounts** grow faster than generic AI art accounts (parasocial engagement)
4. **Lore/worldbuilding** drives long-term followers — give the character a story, not just pretty images
5. **5-15 hashtags** optimal on Instagram (not the old 30-tag max)
6. **IG Reels** = #1 discovery tool on Instagram in 2025-2026
7. **TikTok**: process videos vastly outperform static image posts
8. **Posting consistency** matters more than volume — 1 post/day > 5 posts once a week
9. **First 30 minutes** after posting determine algorithm distribution — post when your audience is online
10. **Comment replies** within first hour boost post visibility significantly

### Content Type Priority (Instagram)

| Priority | Type | Frequency | Why |
|----------|------|-----------|-----|
| 1 | Carousel (5-10 slides) | 3x/week | Highest reach, algorithm favorite |
| 2 | Reels (9:16, 15-60s) | 2-3x/week | Discovery engine, new audience reach |
| 3 | Single image (portrait) | 1-2x/week | Feed presence, lower reach |
| 4 | Stories | Daily | Engagement with existing followers |

## Research Techniques

### Reddit Market Research

Use the JSON API to extract post data for strategy research:

```bash
# Extract top posts from niche subreddits
curl -s "https://old.reddit.com/r/StableDiffusion/comments/.json?limit=25" | \
  python3 -c "
import json, sys
data = json.load(sys.stdin)
for post in data['data']['children']:
    d = post['data']
    print(f'{d[\"score\"]:>5} | {d[\"title\"][:80]}')
"

# Search specific topics
curl -s "https://old.reddit.com/r/StableDiffusion/search/.json?q=AI+influencer&limit=10&sort=top&t=year" | \
  python3 -c "
import json, sys
data = json.load(sys.stdin)
for post in data['data']['children']:
    d = post['data']
    print(f'{d[\"score\"]:>5} | {d[\"url\"]} | {d[\"title\"][:60]}')
"
```

Key subreddits for AI influencer research: `r/StableDiffusion`, `r/aiArt`, `r/localllama`, `r/Instagram`

### Consistency Checking

Every 2 weeks, audit your content for:
- Face consistency across posts (same character?)
- Style drift (same color palette, lighting mood?)
- Voice consistency (same writing style?)
- Engagement rate trends (declining = change something)

- `nsfw-pipeline-models.md` — NSFW model downloads, custom node map, Pony V6 prompt tags, install pitfalls
- `face-consistency-research.md` — Model comparison for AI influencer face consistency (SD1.5 + ChilloutMix benchmarked against SDXL models, cross-architecture LoRA incompatibility validated, create-from-scratch workflow, download pitfalls, Reddit consensus)
- `references/face-consistency-research.md` also now includes: cross-architecture LoRA results (SDXL LoRA on SD1.5 = poor body consistency even at 0.5 weight), create-from-scratch character workflow (generating refs with just base model), download pitfalls (HuggingFace VAE redirect, CivitAI API format, ComfyUI venv path), and Reddit community consensus
- `nous-research-competitive-analysis.md` — Full investigation of Nous Research's 8 branches (main site, Hermes Agent docs, Portal, Psyche, Releases, Careers, Shop, Blog) with BrierStudios adaptation plan, storefront strategy, and feature comparison
- `nous-docs-site-analysis.md` — Detailed analysis of Nous Research's docs site (Docusaurus v3.9.2, gold accent theme, sidebar structure, font stacks, CSS variables) with BrierStudios adaptation plan for docs.brierstudios.com
- `flux-gguf-migration.md` — Flux.1 Dev GGUF Q8_0 migration from ChilloutMix: GGUFLoaderKJ node details, complete API workflow, model files, RTX 3060 benchmarks, Freya prompt notes, face-first selection process
- `lilith-generation-prompts.md` — Lilith v2.0 brand mascot generation prompts: 6 site hero variants (anime/cyberpunk neon), 5 logo prompts (manga + Nordic + Junji Ito ink), Flux config, web optimization pattern, and the critical lesson about saving prompts alongside images

## Competitive Benchmarking

When evaluating competitive positioning for BrierStudios/Lilith, refer to `references/nous-research-competitive-analysis.md` for the full analysis of Nous Research's ecosystem. Key takeaways:

- **NOUS GIRL → Lilith**: Their mascot is a simple stylized human; ours has deep lore (18K identity doc). Play to this strength.
- **Merch flagship**: NOUS GIRL NEON sign sells at $420.69. Our equivalent: Lilith Neon LED sign (Printful/Printify, lower startup cost).
- **Docs site**: Hermes Agent has dedicated docs site with /llms.txt. Our equivalent: docs.brierstudios.com.
- **Terminal demo**: Their animated CLI showcase converts visitors. Our equivalent: animated Yggdrasil CLI demo.
- **Design direction**: Keep frost/cyan/magenta palette (NOT warm/amber). User preference is "mas frio y con mas movimiento".
- **3-phase roadmap**: Quick wins (terminal demo, copy buttons, /releases) → Medium term (docs subsite, /lilith gallery, light mode) → Store (Printful merch, Lilith Neon LED sign).

## Pitfalls

- **Character drift:** Without LoRA, the character's face will change between generations. Always train a LoRA early.
- **Shadowban:** Posting too fast, using banned hashtags, or looking "too AI" triggers shadowban. Start slow (1 post/day), ramp up over weeks.
- **Watermark skipping:** Always watermark. AI art theft is common. Use subtle placement (15% opacity, bottom corner).
- **Negative prompts:** Maintain a canonical negative prompt list and use it in EVERY generation. Inconsistent negatives = inconsistent character.
- **Caption repetition:** LLM-generated captions can feel same-y. Use Lilith batch mode with varied system prompts (poetic, mysterious, cryptic, playful) to introduce variety.
- **API key leakage:** Never put `.env` in git. Always verify `.gitignore` includes `.env`, `*.safetensors`, generated images cache.
- **Over-automation:** Start manual. Learn what works by posting yourself. Automate AFTER you find the formula.
- **WSL venv creation pitfall:** `python3.13 -m venv` creates a broken hybrid venv where pip shebangs point to python3.13 but python symlink resolves to python3.12. Packages silently install to the wrong Python. Always use `uv venv --python 3.12` and `uv pip install --python .venv/bin/python` instead.
- **uv > pip for large installs:** `uv pip install` is 5-10x faster than pip for PyTorch, transformers, etc. Always prefer uv when available.
- **Community matters:** 80% of growth comes from engaging with OTHER people's content. Don't just broadcast.
- **Web image optimization for artist sites:** When deploying AI-generated character images to a static site, convert RGBA PNGs (5-7MB each) to JPEG with a dark background fill matching the site's `--void` color (e.g., `rgb(6,8,16)` for `#060810`). Use two sizes: hero (600x800, quality 85) and thumb (300x400, quality 80). This reduces total payload from ~35MB to ~800KB while preserving visual quality on dark backgrounds. Pillow `Image.new('RGB', size, (6,8,16))` + `paste(img, mask=img.split()[3])` for RGBA→RGB compositing.
- **Interactive gallery pattern (click-to-swap hero):** For character showcase pages, use a main hero image + grid of variant thumbnails. On click: fade hero to opacity 0 + scale(0.95), swap `src` to the hero-sized variant, fade back in. CSS: `transition: opacity 0.3s, transform 0.3s`. JS: `heroImg.style.opacity = '0'`, setTimeout swap src, `onload → opacity = '1'`. Preload the default hero image with `<link rel="preload" as="image">`.
- **Cloudflare Pages cache-busting:** After deploying, always bump `?v=X.Y` version query params in HTML for CSS and JS references. Wrangler hashes files and skips unchanged ones — version params force CDN + browser cache invalidation. Also append a version comment to CSS/JS files to force wrangler re-upload of modified files.
- **PyTorch cu126 on WSL:** Installing torch with `--index-url .../cu126` fails on WSL2 due to `nvidia-nvshmem-cu12` download timeout. Always use cu124: `uv pip install torch torchvision --index-url https://download.pytorch.org/whl/cu124`.
- **Kohya venv torch breakage:** After uv venv creation, `torch.__init__.py` can go missing, causing `AttributeError: module 'torch' has no attribute '__version__'`. Fix by reinstalling: `uv pip install --reinstall torch torchvision --index-url https://download.pytorch.org/whl/cu124`.
- **Juggernaut XL format:** The HuggingFace repo stores checkpoints as diffusers (separate unet/, text_encoder/ dirs), not as a single `.safetensors` file. ComfyUI can load diffusers-format models from `models/checkpoints/` as a directory reference.
- **Pony V6 XL produces cartoonish training datasets:** Even with `source_photo, photorealistic` tags and score-based prompting, Pony V6 XL generations look cartoonish (analyzed at ~4/10 photorealism). For LoRA training datasets where you need photorealistic reference images, use Juggernaut XL v9 + IPAdapter FaceID instead (8/10 photorealism). Pony is fine for anime/illustration LoRAs but not for photorealistic character training.
- **IPAdapter FaceID PlusV2 needs ViT-bigG-14 (1664-dim):** The PlusV2 model's perceiver resampler expects 1664-dim CLIP Vision input. This is NOT ViT-L (which is also 1280-dim like ViT-H). You must download `CLIP-ViT-bigG-14-laion2B-39B-b160k.safetensors` (~3.5GB) from `h94/IP-Adapter` on HuggingFace. If unavailable locally, use the basic `ip-adapter-faceid_sdxl.bin` with ViT-H-14 instead.
- **CLIP Vision model filename must match ComfyUI regex:** Files named `clip_vision_vit_h.safetensors` are NOT found by the IPAdapter regex. Rename or symlink to `ViT-H-14.s32B.b79K.safetensors`. Similarly, the FaceID LoRA needs a symlink: `ln -s models/ipadapter/ip-adapter-faceid_sdxl_lora.safetensors models/loras/faceid.sdxl.lora.safetensors`.
- **FaceID unified loader for API mode:** The `IPAdapterUnifiedLoaderFaceID` node works correctly in API-format workflows. The manual chain (IPAdapterModelLoader→CLIPVisionLoader→InsightFaceLoader) has model-path resolution issues in API mode and should be avoided.
- **Save generation prompts alongside images (CRITICAL):** ComfyUI `/history` resets on restart, and session context compacts over time. If you only keep prompts in your conversation or ComfyUI history, they WILL be lost. Always write a `prompts.json` file in the output directory mapping each image to its prompt, seed, model, and settings. Without this, reproducing or iterating on generated content requires reconstructing prompts from filenames and character briefs — error-prone and time-consuming. See `references/lilith-generation-prompts.md` for the saved prompts pattern and a real example of prompt loss + reconstruction.
- **Filenames with spaces:** ComfyUI output filenames can contain spaces from prompt text. Always quote filenames or use `find -print0 | xargs -0` in scripts. Better: set `filename_prefix` in SaveImage node to a slug.
- **Large tools in git:** Kohya sd-scripts is ~500MB+ and belongs in `.gitignore` (under `tools/kohya_ss/`). Same for output directories and model files.
- **Kohya dataset subdirectory requirement:** `sdxl_train_network.py` requires images inside a class-name subdirectory under `train_data_dir`, e.g. `train_data_dir/eir_niflheimr/`. Flat directories cause "no valid subset found in dataset" error even if metadata.json and captions are present.
- **`--cache_text_encoder_outputs` vs `--train_text_encoder`:** These flags are mutually exclusive. When caching text encoder outputs (recommended for VRAM savings), you MUST use `--network_train_unet_only` instead. Using both causes an explicit error. `--train_text_encoder=false` is NOT a valid Kohya flag.
- **xformers vs sdpa:** `--xformers` requires the `xformers` package installed in the venv. If missing, use `--sdpa` (PyTorch 2.0+ native SDPA) instead. Don't pass `--xformers` without the package — it crashes on import.
- **ComfyUI VRAM conflict during training:** ComfyUI consumes ~7.8GB VRAM on launch. On RTX 3060 12GB, kill ComfyUI before training: `kill $(pgrep -f "ComfyUI/main.py")`. Restart after training completes.
- **bf16 over fp16 for SDXL:** Use `--mixed_precision bf16` and `--save_precision bf16` for SDXL LoRA training. fp16 can cause NaN losses on some SDXL checkpoints.

## NSFW Influencer Pipeline

For NSFW (18+) AI influencers, the pipeline differs from SFW in key ways: model selection, LoRA training dataset composition, workflow architecture, and platform strategy.

### NSFW Base Models (RTX 3060 12GB)

| Model | Use Case | VRAM | HuggingFace |
|-------|----------|------|-------------|
| **Pony Diffusion V6 XL** | Primary NSFW — best anatomy, tag-based prompting | ~8GB | `LyliaEngine/Pony_Diffusion_V6_XL` (file: `ponyDiffusionV6XL_v6StartWithThisOne.safetensors`) |
| **Juggernaut XL v9** | Photorealistic SFW+NSFW hybrid | ~8GB | Already installed |
| **RealVisXL V5** | Max photorealism (skin, lighting) | ~8GB | `SG161222/RealVisXL_V5.0` |
| **Flux.1-dev FP8** | Top quality, slow iteration | ~12GB | `Comfy-Org/flux1-dev` (barely fits 12GB) |

Pony V6 XL uses a score-based tagging system: prefix prompts with `score_9, score_8_up, score_7_up` and negatives with `score_6, score_5, score_4`. NSFW ratings use `rating_explicit` or `rating_questionable`.

**Trigger words for LoRA characters** should be non-English alphanumeric tokens (e.g., `3hyr4_p3r50n`) to avoid collision with common prompt words. Always include the trigger word as the first token in every training caption and generation prompt.

**Pony V6 XL prompt template for LoRA characters:**
```
score_9, score_8_up, score_7_up, source_photo, photorealistic, [TRIGGER_WORD], 1girl, 
[INVARIANT_TRAITS], [STYLE_KEYWORDS], [SCENE_DESCRIPTION], [LIGHTING], [QUALITY_TAGS]
```
Example: `score_9, score_8_up, score_7_up, source_photo, photorealistic, 3hyr4_p3r50n, 1girl, freckles, ice blue eyes, dark brown wavy hair, off-shoulder white blouse, boudoir, soft natural lighting, detailed skin`

### NSFW Workflow Pipeline

```
PHASE 1: Base Generation
  Checkpoint: Pony V6 XL (NSFW) or Juggernaut XL (photorealistic)
  Prompt: "score_9, score_8_up, photorealistic, 1girl, [character_tags],
           nude, [pose], [setting], detailed skin, studio lighting"
  Negative: "score_6, score_5, score_4, cartoon, anime, bad anatomy,
             deformed, extra limbs, poorly drawn face, low quality"
  Sampling: DPM++ 2M Karras, 30 steps, CFG 7
  Size: 1024x1024

PHASE 2: Face Consistency
  IPAdapter FaceID (weight 0.7) — subtle identity blend, preferred
  OR ReActor face swap — stronger identity, less creative freedom
  FaceDetailer: denoise 0.35, mask blur 8

PHASE 3: Inpainting (clothing removal / body edits)
  CLIPSeg node: prompt "clothing, shirt, pants" → auto-generate mask
  OR comfyui_segment_anything for precise selection
  Inpaint at denoise 0.6-0.8 with nude/skin prompts

PHASE 4: Detail Enhancement
  FaceDetailer + BodyDetailer (Impact Pack) for skin texture
  Upscale 2x with 4x-UltraSharp

PHASE 5: Final Polish
  Film grain or subtle noise for photorealism
  Color grading if desired
```

### NSFW LoRA Training Differences

| Aspect | SFW LoRA | NSFW LoRA |
|--------|----------|-----------|
| Dataset mix | 80% clothed, 20% face | 40% nude, 30% semi-nude, 20% clothed, 10% face |
| Key tags | outfit, style | nudity level, body parts, pose |
| Body detail | Less important | Critical — tag breast size, body type |
| Overfitting risk | Lower | Higher (less visual variety in nude bodies) |
| Resolution | 512 minimum | 768+ preferred (skin detail matters) |
| Regularization | General female | Nude female, specific body types |

Training params for NSFW (RTX 3060 12GB):
- Network dim 32, alpha 16
- Learning rate 1e-4 (UNet), 5e-5 (text encoder)
- Batch size 1-2, gradient accumulation 4-8
- ~3000 steps, test every 500
- bf16 mixed precision
- Include 100-200 regularization images of similar body types

### NSFW Custom Nodes Required

Beyond the SFW setup, NSFW workflows need:
- **ComfyUI-CLIPSeg** — semantic clothing masking for inpainting
- **comfyui_segment_anything** — precise body/clothing selection
- **ComfyUI-SAM2** — zero-shot segmentation (requires `addict` + `yapf` packages)
- **IPAdapter FaceID** — model `ip-adapter-plus-faceid_sdxl.bin` from `h94/IP-Adapter`
- **InsightFace buffalo_l** — face detection model from `h94/IP-Adapter/models/`

### Platform Strategy: SFW Funnel to NSFW

```
Tier 1 — Instagram (SFW, free, mass audience)
  └─ Teaser photos (implied, beach shots, lifestyle)
  └─ Links to linktree in bio

Tier 2 — Twitter/X + Free OnlyFans (SFW → soft NSFW)
  └─ Topless with crop, selective blur, short clips
  └─ Free OF page for conversion

Tier 3 — Paid OnlyFans / Fansly (Full NSFW content)
  └─ Full photosets, extended videos, customs
  └─ Primary revenue
```

Platform splits: OnlyFans 80/20, Fansly 80/20, Fanvue 85/15.

### Important: Separate Characters for SFW and NSFW

Never mix SFW and NSFW on the same social account. The SFW funnel (Instagram) drives traffic to NSFW platforms. The SFW character and NSFW character can be the same fictional persona, but content categories stay platform-specific.

Disclose AI nature where required (many platforms now mandate this). Consistency via LoRA is critical — your LoRA is your model's identity.

## PixAI LoRA Training (Cloud)

PixAI (https://pixai.art) is a cloud LoRA training platform — use it when local
GPU is limited or when Z-Image has NaN issues on RTX 3060. The available training
model is Tsubaki.2 (anime-styled). See `references/pixai-lora-training.md` for
full details including prompt format, style variants, pitfalls, and LoRA inventory.

**Key difference from local training:** Tsubaki.2 is anime-styled. All LoRAs trained
on it produce anime-style output even with "realistic" checkpoint models. Positive
prompts must include `anime style`; negatives must include `photorealistic, photo,
realistic`. Trigger words can be short tokens (e.g. `ehyra`).

**Current project: Freya** — Korean/Japanese AI influencer with dark goth aesthetic.

- **Character:** Freya — black long hair, honey/amber eyes, goth eyeliner, high cheekbones, natural lips, voluptuous slim figure (large bust, nice butt, not exaggerated), no tattoos
- **Style:** Dark, goth, minimalist, grunge, oversized
- **Trigger word:** `fr3y4`
- **Base model:** Flux.1 Dev Q8_0 GGUF — superior photorealism and body consistency vs SD1.5/SDXL
- **Resolution:** 1024×1024 (face/closeup), 1536×640 (ultra-wide full-body)
- **Face consistency:** PuLID (zero-shot) — chosen because IPAdapter doesn't support Flux. Uses `ComfyUI-PuLID-Flux` (balazik repo) with AntelopeV2 + EVA-CLIP + v0.9.1 model
- **⚠️ Critical:** PuLID API parameter names differ from UI — always verify via `/object_info` before building workflows. Known mismatches: `pulid_file` (not `pulid_name`), `eva_file` (not `eva_name`), `model_name` (not `unet_name` for GGUFLoaderKJ). See comfyui skill pitfall #49.
- **⚠️ Critical:** `onnxruntime-gpu` on Python 3.13+ has no `CUDAExecutionProvider` — must use `provider="CPU"` for PulidFluxInsightFaceLoader. InsightFace works on CPU, just slower.
- **GGUFLoaderKJ** requires ALL params explicitly: `model_name`, `extra_model_name`, `dequant_dtype`, `patch_dtype`, `patch_on_device`, `enable_fp16_accumulation`, `attention_override`. See comfyui skill pitfall #50.
- **Flux face candidate:** E (seed 50389) — A-D rejected due to blur. Reference at `~/comfy/output/freya_flux_candidates/freya_flux_candidate_E.png`
- **Face-first approach:** Generate 5 face candidates first → user picks THE one → PuLID for consistent variations → curate → train Flux LoRA with trigger word `fr3y4`
- **LoRA training tool:** ai-toolkit (ostris) — supports quantized FLUX training on 12GB VRAM
- **Previous project (Ehyra):** Abandoned due to SDXL body inconsistency. SDXL LoRA does not transfer to SD1.5.
- **Migration note:** Pivoted from ChilloutMix (SD1.5) to Flux.1 Dev Q8_0 GGUF for superior photorealism. Flux GGUF Q8 workflow uses different nodes than SDXL — see comfyui skill pitfall #50.

**Previous project: Eir Niflheimr** — Norse goddess of healing, dark fantasy digital artist from Svartalfheim. Violet + silver aesthetic. Project lives at `/mnt/d/Proyectos/Yggdrasil/Muspelheim/AI-Influencer/`.

## Brand Mascot: Lilith (v2.0 Anime/Neon)

Lilith is the BrierStudios brand mascot — NOT an AI influencer in the traditional sense, but shares pipeline needs (character consistency, LoRA training, multi-variant generation). The v2.0 direction is anime/cyberpunk neon (pivoted from dark-fantasy realistic in v1.0).

**Key specs for generation:**
- **Style:** Anime/cyberpunk neon — sleek proportions, large expressive eyes, dramatic flowing hair, neon circuit lines
- **Palette:** Cyan `#38bdf8` (primary), Magenta `#d946ef` (accent), Aurora `#7dd3fc`, Abyss `#0f172a`
- **9 realm variants** with different neon accent colors per realm
- **Trigger word for LoRA:** `l1l1th`
- **Identity docs:** `/mnt/d/Proyectos/Yggdrasil/Svartalfheim/LILITH_IDENTITY.md` (v2.0), `/mnt/d/Proyectos/Yggdrasil/Svartalfheim/LILITH_ARTIST_BRIEF.md` (v2.0)
- **Site:** Live at brierstudios.com, section `#lilith`, deployed v2.5
- **v2.5 additions**: Animated CLI terminal demo section (`#cli-demo` with 3 scenes), copy buttons on code blocks (clipboard API + SVG swap), `/releases` page with vertical timeline (7 versions v1.0→v2.5), additional whitespace (section padding 8rem, headers 5rem)
- **Images:** Real anime hero images (JPEG 600x800 hero + 300x400 thumbs) in `assets/lilith/`
- **Gallery:** Interactive 3x2 grid — click swaps hero with fade transition. 6 variants mapped to 6 realms.
- **SVG:** Replaced by real anime images in v2.4 (dark-fantasy placeholder removed)
- **Logo variants:** 5 concepts generated with Flux.1 Dev — rune circle border, half face horror, valkyrie manga, ink splash emerging, minimalist single line. All in Junji Ito ink style + Nordic runes. Trigger word `l1l1th` proposed for LoRA.
- **Generation prompts:** See `references/lilith-generation-prompts.md` for all 6 site hero prompts + 5 logo prompts + Flux config + the critical lesson about saving prompts alongside images