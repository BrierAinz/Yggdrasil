---
name: lora-training-pipeline
description: Full LoRA training pipeline for character/person generation — dataset prep, auto-captioning with Qwen3-VL, training config (ai-toolkit/Kohya), execution, evaluation, and iteration.
version: 1.0.0
tags: [lora, sdxl, training, qwen3-vl, comfyui, kohya, ai-toolkit, character-generation, trigger-words, pixai, style-lora]
related_skills:
  - comfyui-batch-generate
  - comfyui
  - auto-captioning
---

# LoRA Training Pipeline for Character/Person Generation

End-to-end workflow: collect references → augment via ComfyUI → auto-caption with Qwen3-VL → train LoRA → evaluate → iterate.

## Trigger Word Strategy (DiT.1 vs DiT.2, Character vs Style)

See `references/trigger-words-and-pixai-dit.md` for full details. Key points:

- **DiT.1 (Tsubaki)**: Short tags like `character_name, source, attribute` (e.g. `hatsune_miku, vocaloid, twin_tails`). Style LoRAs can be one tag: `ink_wash_style`.
- **DiT.2 (Tsubaki.2)**: Descriptive phrase of **30+ characters** (e.g. `A young woman with long silver hair, golden eyes, and a futuristic black visor`). Short triggers leave quality on the table.
- **Character LoRAs**: Only include permanent features (eyes, hair color, markings, signature accessories). NEVER include outfits, poses, or backgrounds in trigger words.
- **Style LoRAs**: Only include shared visual characteristics across ALL images (line style, coloring technique, palette, recurring motifs, mood). NEVER include character names, specific outfits, artist names, or variable elements.
- **PixAI 256-char limit** on trigger words. Aim 80–200 chars.
- **Prompt order at generation**: style trigger → character tags → outfit → pose → scene → `<lora:name:weight>`

| LoRA Type | Include in Trigger | Exclude |
|-----------|-------------------|---------|
| Character | Eye/hair color, markings, signature accessories, anatomy | Clothing, poses, backgrounds, temporary elements |
| Style | Line style, shading, palette, background motifs, effects, aesthetic mood | Character names, specific outfits, artist tags, variable poses |

## 1. Dataset Preparation

### Collect Reference Images
Gather 15–30 high-quality reference images of the target character/person:
- **Face shots**: front, 3/4, profile — varied expressions
- **Body shots**: full-body, half-body — varied poses and outfits
- **Avoid**: blurry, heavily filtered, watermarked images

### Generate Variations via ComfyUI
Use the `comfyui-batch-generate` skill to augment the dataset:
- Generate stylistic variations (lighting, background, pose)
- Use IPAdapter FaceID for face consistency across generations
- Target 30–50 total images after augmentation
- **Pre-filter reference images**: InsightFace must detect a face in every ref. Exclude photos where the face is too small (< 20% of frame), obscured, or at extreme angles. These will silently fail with "No face detected".
- **Expect some failures**: Even with valid refs, a small % of generations may fail. Build resume/skip logic into batch scripts.

### Organize Training Directory
```
training_data/<trigger_word>/
├── image_001.jpg
├── image_001.txt    # paired caption file
├── image_002.jpg
├── image_002.txt
└── ...
```

**Trigger word format**: `3hyr4_p3r50n` (alphanumeric underscores, unique per character)

## 2. Auto-Captioning with Qwen3-VL

Use Qwen3-VL-4B-Instruct to generate captions for all training images.

### Critical Constraints (12GB VRAM)
- **Cannot run Qwen3-VL and ComfyUI simultaneously** — unload ComfyUI models before captioning
- Use `quantize: true` and `low_vram: true` in the model config
- Estimated VRAM usage with quantization: ~8-9GB

### Captioning Script
```python
from transformers import Qwen3VLForConditionalGeneration, AutoProcessor
from qwen_vl_utils import process_vision_info

model = Qwen3VLForConditionalGeneration.from_pretrained(
    "Qwen/Qwen3-VL-4B-Instruct",
    torch_dtype=torch.bfloat16,
    device_map="auto",
    # For low VRAM:
    # quantization_config=BitsAndBytesConfig(load_in_4bit=True)
)

processor = AutoProcessor.from_pretrained("Qwen/Qwen3-VL-4B-Instruct")

prompt = """Describe this person's appearance in detail for AI training.
Focus on: face features, hair, body type, clothing, pose.
Start with a trigger word and use comma-separated tags.
Format: <trigger_word>, <tags>, <description>"""

messages = [{"role": "user", "content": [
    {"type": "image", "image": image_path},  # PLAIN path, NOT file:// URI
    {"type": "text", "text": prompt}
]}]

# Process inputs
text = processor.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)
image_inputs, video_inputs = process_vision_info(messages)
inputs = processor(
    text=[text],
    images=image_inputs,
    videos=video_inputs,
    padding=True,
    return_tensors="pt"
).to(model.device)

# MUST use batch_decode, NOT batch_text_decoder
output = model.generate(**inputs, max_new_tokens=256)
caption = processor.batch_decode(output, skip_special_tokens=True)[0]
```

### Pitfalls
| Issue | Fix |
|-------|-----|
| `batch_text_decoder` not found | Use `processor.batch_decode()` — no such method as `batch_text_decoder` |
| Image path with `file://` prefix | Pass plain path string: `/path/to/image.jpg` not `file:///path/to/image.jpg` |
| Wrong Qwen3-VL class name | Use `Qwen3VLForConditionalGeneration`, NOT `Qwen2VL` — wrong class raises RuntimeError |
| OOM with Qwen3-VL | Enable 4-bit quantization + `low_vram`, close ComfyUI first |
| Caption quality too generic | Refine prompt; add character-specific attributes to seed descriptions |

## 3. Training Configuration

### Recommended: ai-toolkit

Config path: `/home/brierainz/comfy/ai-toolkit/`

### SD1.5 Training (ChilloutMix)

When training on SD1.5 / ChilloutMix (the gold standard for Asian face consistency):

```yaml
# ai-toolkit config for SD1.5 / ChilloutMix
device: cuda:0
model:
  name_or_path: /home/brierainz/comfy/ComfyUI/models/checkpoints/chilloutmix_NiPrunedFp16Fix.safetensors
  is_sdxl: false          # SD1.5, NOT SDXL
  vae_path: /home/brierainz/comfy/ComfyUI/models/vae/vae-ft-mse-840000.safetensors

trigger_word: "fr3y4"

datasets:
  - folder_path: /home/brierainz/comfy/training_data/freya
    caption_ext: txt
    shuffle_tokens: false
    dropout_tokens: false

train:
  dtype: fp16             # SD1.5 uses fp16 (bf16 is SDXL-only)
  xformers: true
  optimizer: adamw8bit
  learning_rate: 1e-4
  lr_scheduler: cosine
  gradient_accumulation_steps: 1
  
  # LoRA params
  lora_rank: 32
  lora_alpha: 16
  lora_dropout: 0.0
  
  resolution: [512, 768]   # SD1.5 native resolution
  batch_size: 1
  
  steps: 3000              # character: 3000-4000 steps
  
  save_every: 500
  log_every: 50
```

**Key differences from SDXL training:**
- `is_sdxl: false` — MUST set this for SD1.5 checkpoints
- `resolution: [512, 768]` — SD1.5 native is 512×768, NOT 768×1024
- `dtype: fp16` — SD1.5 uses fp16 mixed precision (bf16 can cause issues)
- `vae_path` — ChilloutMix uses vae-ft-mse-840000, NOT sdxl_vae
- Use `name_or_path` with local `.safetensors` path, not HuggingFace ID

### SDXL Training (default)

trigger_word: "3hyr4_p3r50n"

datasets:
  - folder_path: /path/to/training_data/3hyr4_p3r50n
    caption_ext: txt
    shuffle_tokens: false
    dropout_tokens: false

train:
  dtype: bf16
  xformers: true
  optimizer: adamw8bit
  learning_rate: 8e-5
  lr_scheduler: cosine
  gradient_accumulation_steps: 1
  
  # LoRA params
  lora_rank: 32
  lora_alpha: 16
  lora_dropout: 0.0
  
  resolution: [768, 1024]
  batch_size: 1
  
  steps: 3000   # character: 3000-4000 steps
  
  save_every: 500
  log_every: 50
```

### Alternative: Kohya_SS

```toml
# Kohya config for SDXL character LoRA
pretrained_model_name_or_path = "stabilityai/stable-diffusion-xl-base-1.0"

[datasets]
batch_size = 1
resolution = [768, 1024]

[network]
network_dim = 32
network_alpha = 16
network_dropout = 0.0
network_args = []

[optimizer]
optimizer_type = "AdamW8bit"
learning_rate = 8e-5
lr_scheduler = "cosine"
warmup_ratio = 0.1

[misc]
gradient_accumulation_steps = 1
mixed_precision = "bf16"
xformers = true
save_model_as = "safetensors"
```

### Recommended Hyperparameters Summary

| Parameter | Value | Notes |
|-----------|-------|-------|
| rank (dim) | 32 | Good balance for character likeness |
| alpha | 16 | alpha = rank/2 is a common starting point |
| learning_rate | 8e-5 | Start here; reduce if overfitting |
| scheduler | cosine | Smooth LR decay |
| optimizer | adamw8bit | Saves VRAM vs full adamw |
| precision | bf16 | RTX 30xx/40xx support bf16 natively |
| attention | xformers | Required for VRAM efficiency |
| resolution | [768, 1024] | Mixed resolution improves generalization |
| steps | 3000–4000 | Character LoRA range; start at 3000 |
| batch_size | 1 | 12GB VRAM constraint |

## 4. Training Execution

### Launch with ai-toolkit
```bash
cd /home/brierainz/comfy/ai-toolkit/
python run.py config/<your_config>.yml
```

### Launch with Kohya
```bash
# Kohya venv may need PyTorch reinstall
pip install torch torchvision --force-reinstall
accelerate launch --num_cpu_threads_per_process 2 train_network.py \
  --config_file config/<your_config>.toml
```

### Monitor Training
- Watch loss curves: should steadily decrease then plateau
- Loss around **0.08–0.15** is typical for a well-trained character LoRA
- If loss drops too fast → lr too high / overfitting risk
- If loss plateaus early → dataset too small or lr too low

### Pitfalls
| Issue | Fix |
|-------|-----|
| Kohya venv PyTorch mismatch | `pip install torch torchvision --force-reinstall` before training |
| ComfyUI BrokenPipeError | Patch ComfyUI server code for pipe handling; see comfyui skill |
| OOM during training | Reduce resolution to [768], reduce batch_size, enable gradient checkpointing |
| Loss spiking | Reduce lr by 50%, increase warmup_ratio to 0.15 |

### Choose Best Checkpoint
- Don't default to the last checkpoint
- Generate test images at steps 2000, 2500, 3000, 3500, 4000
- Pick the step with best likeness vs. flexibility tradeoff
- Overfitting signs: exact background reproduction, frozen expressions

## 5. Evaluation

### Generate Comparison Images
For each checkpoint, generate test images:
1. **With LoRA** at weights 0.7, 0.85, 1.0
2. **Without LoRA** (same prompt minus trigger word)

```bash
# ai-toolkit inference
python run.py inference --lora_path <checkpoint> --prompt "3hyr4_p3r50n, portrait, ..."

# Or via ComfyUI with LoRA Loader node
```

### Systematic Testing via ComfyUI API (Recommended)

For thorough evaluation, submit batch test jobs via ComfyUI's REST API. This lets you test multiple checkpoints × strengths × prompts systematically.

**Key workflow node chain for LoRA testing:**
```
CheckpointLoaderSimple → LoraLoader → CLIPTextEncode (positive) → CLIPTextEncode (negative) → EmptyLatentImage → KSampler → VAEDecode → SaveImage
```

**Test matrix pattern:**
```python
import json, urllib.request

tests = [
    {"lora": "lora_step1000.safetensors", "strength": 0.8,
     "prompt": "score_9, score_8_up, <trigger>, <outfit_1>, ..."},
    {"lora": "lora_step2000.safetensors", "strength": 0.8,
     "prompt": "score_9, score_8_up, <trigger>, <outfit_2>, ..."},
    {"lora": "lora_final.safetensors", "strength": 0.9,
     "prompt": "score_9, score_8_up, <trigger>, <outfit_3>, ..."},
    {"lora": "lora_final.safetensors", "strength": 1.0,
     "prompt": "score_9, score_8_up, <trigger>, <outfit_4>, ..."},
]
# Submit each as JSON to http://localhost:8188/prompt
# Poll /queue until all done, then check /output/ for results
```

See `references/comfyui-lora-testing-api.md` for the full Python workflow template.

**Important: Pony V6 body LoRA strengths** body LoRAs on Pony V6 XL require strength 0.9–1.0. At 0.7–0.8, Pony's base anime style dominates and results look cartoonish. Training images were real/photorealistic (Flux-generated), so the LoRA fights Pony's base style at lower weights. Always test at multiple strengths (0.8, 0.9, 0.95, 1.0) and diverse outfits to find the sweet spot.

### Evaluation Criteria
- **Face consistency**: Does the face match reference across generations?
- **Pose flexibility**: Can the character take new poses while retaining likeness?
- **Outfit variety**: Does changing outfit prompts work, or is clothing baked in?
- **Background diversity**: Are backgrounds varied or memorized?
- **Artifact check**: No extra limbs, eyes, or texture glitches

### Overfitting Indicators
| Sign | Meaning |
|------|---------|
| Identical backgrounds across images | Background memorized — add background diversity to dataset |
| Same pose every time | Pose memorized — add pose variety or pose-conditioned captions |
| Face distorts at weight < 0.8 | LoRA too strong — reduce steps or lower rank |
| Trigger word has no effect | Undertrained — increase steps, check caption quality |

## 6. Body / Full-Body Dataset Generation

Face-only datasets produce LoRAs that only work for portraits. For full-body consistency, you need a separate body dataset with diverse poses, outfits, and body types.

### Critical: IPAdapter FaceID Does NOT Work for Full-Body Generation

**IPAdapter FaceID dominates composition regardless of settings.** Extensive testing shows:
- Weight 0.80: face-focused portrait crop
- Weight 0.65: three-quarter crop, still face-dominated
- Weight 0.35: mid-thighs crop, slim body type
- Weight 0.30 + `end_at=0.40` + `weight_type="composition"`: still three-quarter, slim
- Even at 1024x1536 resolution: still crops at mid-thighs

**The root cause**: IPAdapter FaceID injects face identity into generation, biasing the model toward face-centric compositions. Lowering weight only reduces face fidelity — it does NOT shift composition toward full-body. The model compensates for a weaker face signal by generating a generic slim body.

**Additionally, Juggernaut XL v9 has an inherent slim portrait bias** — even without IPAdapter, it generates mid-thigh-cropped slim portraits regardless of prompt content. It works well for portraits but is fundamentally unsuitable for body generation.

### Two-Phase Body Generation Approach (v6 — Flux GGUF)

Instead of IPAdapter FaceID for body images, use a **two-phase approach**:

**Phase 1 — Generate full-body images WITHOUT IPAdapter (prompt-driven)**:

**RECOMMENDED: Flux.1-dev GGUF Q8 at 1536×640** — produces 10/10 full body, 10/10 body type accuracy, 10/10 photorealism. Best option for body dataset generation on RTX 3060 12GB. ~3-4 min per image. See comfyui skill pitfall #50 for the complete workflow node chain.

**Checkpoint comparison for body generation:**
| Checkpoint | Full Body | Body Type Accuracy | Photorealism | Notes |
|------------|-----------|-------------------|--------------|-------|
| **Flux.1-dev GGUF Q8** (1536×640) | 10/10 | 10/10 curvy slim | 10/10 | Best option. Understands "curvy slim" correctly |
| Pony V6 XL (1344×768) | 8/10 | 1/10 (produces BBW) | 4/10 | Only full body with wide ratio; always anime-ish |
| RealVisXL V4.0 | 2/10 | 2/10 | moderate | Crops mid-thigh; slim portrait bias |
| Juggernaut XL v9 | 2/10 | 2/10 | moderate | Inherent slim portrait bias |

- **DO NOT use Juggernaut XL v9** for body generation (inherent slim portrait bias)
- **DO NOT use RealVisXL V4** for body generation (crops mid-thigh)
- **Pony V6 XL** works for full body BUT interprets "curvy" as BBW/fat and produces semi-illustrated style
- Use 1536×640 (ultra-wide) for Flux GGUF — this is the ONLY tested resolution that consistently produces head-to-toe full body
- For SDXL checkpoints (Pony, Juggernaut), use 1344×768 (wide/landscape) — tall ratios crop mid-thigh

**Phase 2 — Face swap with ReActor to transfer the target face**:
- Use `ReActorFastFaceSwap` or `ReActorFaceSwap` nodes in ComfyUI
- Inputs: `input_image` (generated body from Phase 1), `source_image` (reference face photo)
- Swap model: `inswapper_128.onnx` (place in `models/reactor/`)
- This preserves the full-body composition from Phase 1 while adding facial likeness

This two-phase approach produces far better full-body results than any IPAdapter FaceID configuration.

### Directory Structure

```
dataset/
├── images/
│   ├── ehyra_reference/          # Face-only reference photos (face crops)
│   │   ├── ehyra_ref_01.jpeg
│   │   └── ...
│   └── ehyra_reference_body/     # Full-body reference photos (originals)
│       ├── 20250427_071835.jpg   # Full-body originals, 1500x2000+ resolution
│       └── ...
├── ehyra_v3_train/              # Merged training dir (face gen + body gen + refs + captions)
│   ├── ehyra_ref_01.jpeg        # Original face references
│   ├── ehyra_v2_ehyra_ref_01_closeup_*.png  # Generated face variations
│   ├── ehyra_v2_body_*_casual_body_*.png     # Generated body variations
│   ├── *.txt                    # Paired caption files
│   └── 20250427_071835.jpg      # Original body references
├── metadata/
│   ├── ehyra_body_generated_captions.json
│   └── ...
└── scripts/
    ├── regenerate_ehyra_v3.py     # Face generation script (IPAdapter FaceID)
    ├── regenerate_ehyra_body.py   # Body generation script (separate workflow)
    └── caption_ehyra_body_gen.py  # Auto-captioning for body images
```

### Body Generation Script Pattern (v6 — Flux GGUF Two-Phase)

The v3 body generation used IPAdapter FaceID with only 4 categories (fullbody, fashion_body, casual_body, environmental_body) and repetitive descriptors. v4.1 used RealVisXL/Pony. v5 tried Pony V6 with BBW tags. All produced wrong body types or low realism.

**v6 two-phase approach** (as implemented in `regenerate_ehyra_body_v6.py`):

**Phase 1 — Body generation with Flux GGUF at 1536×640**:
```python
# Complete workflow node chain:
# UnetLoaderGGUF → DualCLIPLoader(type="flux") → VAELoader → ModelSamplingFlux
# → CLIPTextEncode(positive) → FluxGuidance(3.5) → CLIPTextEncode("")
# → EmptyLatentImage(1536,640) → KSampler(cfg=1, euler, simple, steps=20)
# → VAEDecode → SaveImage
#
# Key differences from SDXL:
# - UnetLoaderGGUF (NOT CheckpointLoaderSimple or UnetLoader)
# - DualCLIPLoader with type="flux" (loads T5-XXL + CLIP-L together)
# - FluxGuidance node sets guidance (3.5 for dev, 1.0 for schnell)
# - ModelSamplingFlux REQUIRED with matching width/height
# - VAELoader for separate ae.safetensors
# - KSampler cfg=1.0 (NOT cfg>1 for Flux)
# - Negative prompt: empty string in separate CLIPTextEncode node

BODY_TYPES = {
    "hourglass": "curvy slim hourglass figure with wide hips, full bust, and narrow defined waist, fit and toned body",
    "pear": "slim pear figure with wide hips and narrow waist, toned legs, smaller bust",
    "athletic_curvy": "athletic toned body with feminine curves, fit with wide hips and full bust, narrow waist",
}

OUTFITS = {  # 10+ varied outfits
    "studio_black": "form-fitting black cocktail dress with low neckline, strappy black heels",
    "casual_denim": "fitted white crop top and tight blue jeans showcasing her hourglass figure, white sneakers",
    "bikini_beach": "string bikini revealing her curvy slim body, barefoot on sand",
    # ... more outfits
}

SCENES = {  # 10+ varied scenes
    "studio_grey": "professional photography studio with neutral grey backdrop, soft studio lighting",
    "park_sunny": "sunny park with green trees and walking path, natural golden hour lighting",
    # ... more scenes
}

POSES = {  # 8+ varied poses
    "standing_confident": "standing with confident posture, weight on one leg, hands at sides",
    "walking_toward": "walking toward the camera with natural stride, both feet visible on ground",
    "three_quarter": "standing at three-quarter angle, looking over shoulder at camera",
    # ... more poses
}
```

- Deterministic seeds for resume/reproducibility: `seed = 100000 + i * 10 + j`
- Queue drain between submissions (avoid timeout from backlog)
- Skip existing images with `--skip-existing` flag for resume
- Copy from ComfyUI output dir to organized dataset dir after each generation
- **Curvy slim = wide hips + full bust + narrow waist + fit/toned. NOT BBW/fat/plus-size.**
- Flux understands "curvy slim hourglass" correctly — no need for BBW tags
- **Phase 2 (ReActor face swap) success rate is ~82% (28/34 in testing)** — ReActor fails on non-frontal poses at 640px image height because faces are too small for detection
- **ReActor face swap QUALITY is inconsistent even when detection succeeds** — ~40% of successful face swaps produce generic/plastic faces that don't match the reference ("uncanny valley" effect: smooth skin, melting mouth/chin, asymmetrical eyes). Only ~60% of face-swapped images are truly usable for LoRA training. Manual curation is MANDATORY — do not add generated images to the training dataset without visual review
- **Deformed hands in Flux full-body generation** — ~20-30% of Flux GGUF images at 1536×640 have visibly deformed hands (extra fingers, fused fingers, twisted wrists). Exclude these from training datasets
- **Flux prompt misinterpretation** — Flux occasionally reinterprets scene/background descriptions at 1536×640 (e.g., "sunny park" → woman on sofa with dog). Always visually verify each image matches the intended prompt before including in training data
- **Net yield for LoRA training: ~50-60% of generated images are usable** — out of 34 generated combinations, expect ~23 successful face swaps, of which ~14-17 are truly training-quality after curation (correct face, no hand deformations, correct scene, correct body type)
- **Face-friendly poses for ReActor:** `standing_confident`, `hand_on_hip` (frontal angles)
- **Face-unfriendly poses (ReActor will fail):** `turning_back`, `three_quarter`, `arms_crossed`, `sitting_elegant`, `leaning_wall`, `walking_toward`
- **YOLOv5l face detection does NOT help** — switching from `retinaface_resnet50` to `YOLOv5l` in ReActor still fails on the same non-frontal poses. The limitation is fundamental: at 640px image height, faces in full-body compositions are too few pixels for any detection model.
- **Recommendation:** Generate body images with face-friendly frontal poses for the face swap pass. If you need non-frontal poses in the final dataset, either skip face swap for them (accept varied faces) or generate close-up face crops separately. Expect ~82% success rate (28/34) with mixed poses; use only frontal poses for near-100% success.

### Body Captioning Pattern

Body captions must describe the **full person** — not just the face. The Qwen3-VL caption prompt for body images:

```
Describe this image in detail for a LoRA training dataset caption. Focus on:
- The person's physical appearance (skin tone, hair color/style, body type/physique, facial features)
- Clothing and outfit details
- Pose and body positioning
- Setting/background
- Lighting and mood
- Overall composition

Start with "RAW photo" and be specific about physical traits. Keep it under 150 words.
```

### Cleanup: Regenerating Body Images

When regenerating body images (e.g., deleting v3 to make v4):

1. **Delete body PNGs and their TXTs from the training dir:**
   ```bash
   cd /path/to/ehyra_v3_train/
   rm -f ehyra_v2_body_*.png ehyra_v2_body_*.txt
   ```

2. **Delete the generated body output dir:**
   ```bash
   rm -rf /path/to/ehyra_generated_v2_body/
   ```

3. **Delete old body caption metadata:**
   ```bash
   rm -f /path/to/metadata/ehyra_body_generated_captions.json
   ```

4. **Keep original body references** (`ehyra_reference_body/`) — they're source photos, not generated.

5. **Create v4 generation script** with improved prompts (see above), then run with ComfyUI.

6. **Re-caption** all generated body images with Qwen3-VL before merging into training dir.

### Body-Only LoRA Training (Without Face Swap)

When Phase 2 (ReActor face swap) produces poor results, train a **body-only LoRA** using just the Phase 1 Flux-generated bodies. This LoRA captures body type, proportions, and outfit diversity without requiring consistent faces.

**Workflow:**
1. Select best ~25 images from Phase 1 (exclude deformed hands — ~20-30% have them)
2. Prioritize diverse poses/hand visibility: LOW risk (arms_crossed, turning_back) > MEDIUM (standing, walking) > HIGH (hand_on_hip, reaching)
3. For SDXL training: center-crop ultra-wide (1536x640) images to 1024x1024
4. For Flux training: keep original 1536x640 with AR bucketing via `resolution: [640, 768, 1024]`
5. Write captions manually from known generation prompts (more accurate than Qwen3-VL captioning)
6. Caption format: `<trigger>, <body description>, wearing <outfit>, <pose>, <scene>, <lighting>, photorealistic full body shot`
7. **Do NOT describe face features** in body-only captions (the LoRA should not learn face identity)

**Caption template for body LoRA:**
```
ehyra_body, a woman with a curvy slim hourglass figure, wide hips, full bust, narrow defined waist, fit and toned body, wearing <outfit>, <pose>, <scene>, <lighting>, photorealistic full body shot
```

**ai-toolkit YAML config for body LoRA (SDXL base):**
See `templates/ai-toolkit-body-lora-sdxl.yaml` for a complete working config tested on RTX 3060 12GB. Key differences from face LoRA: `xformers: false` (broken on PyTorch 2.11+), `noise_scheduler: "ddpm"` (not flowmatch), Pony quality tags in sample prompts.

**ai-toolkit YAML config for body LoRA (FLUX base):**
Same as SDXL but with: `is_flux: true`, `quantize: true`, `low_vram: true`, `noise_scheduler: "flowmatch"`, `cfg: 1.0`, and `resolution: [640, 768, 1024]`.

### Pitfalls

| Issue | Fix |
|-------|-----|
| Same body descriptors in every prompt | Vary descriptors per category; don't repeat "voluptuous" in every prompt |
| Only 4 categories | Use 8+ categories for diversity |
| Oven TXTs after deleting PNGs | Always clean up matching `.txt` files when removing `.png` images |
| Body images not using FaceID | ALWAYS use face swap (ReActor) for body generation — but generate bodies WITHOUT IPAdapter first, then swap faces in Phase 2 |
| IPAdapter FaceID dominates composition | Cannot produce full-body images at any weight (0.30–0.90 tested). Use two-phase: generate bodies with Flux GGUF, then ReActor face swap |
| Juggernaut XL v9 slim portrait bias | Inherent bias toward slim portrait crops even at 1024x1536. Use Flux GGUF for body generation |
| Pony V6 produces BBW not curvy slim | "Curvy" in Pony V6 always means BBW/fat. Use Flux GGUF instead, which understands "curvy slim hourglass" correctly |
| SDXL tall ratios crop mid-thigh | ALL SDXL checkpoints (Juggernaut, Pony, RealVisXL) crop mid-thigh with tall/narrow ratios. Use 1344x768 wide for SDXL, or 1536x640 ultra-wide for Flux GGUF |
| ReActor face swap quality for LoRA training | Even successful face swaps look generic/plastic (~40% mismatch the reference). MUST manually curate — only ~50-60% of generated images are LoRA-training quality after accounting for face mismatches, deformed hands, and prompt misinterpretation |
| Deformed hands in Flux full-body | ~20-30% of Flux 1536×640 images have visibly deformed hands. Exclude from training data or photoshop before use |
| No manual curation before training | ALWAYS visually review every generated image before adding to training dataset. Exclude: mismatched faces, deformed hands, wrong scene/body type, poor composition |
| embeds_scaling format | Must be "V only" (with space), NOT "V_ONLY" — underscore format causes 400 error |
| IPAdapter Plus Face model mismatch | ip-adapter-plus-face_sdxl_vit-h incompatible with UnifiedLoader (size mismatch). Use plain ip-adapter-faceid_sdxl.bin |
| ComfyUI not running when starting generation | Verify with `curl -s http://127.0.0.1:8188/system_stats` before running scripts |
| Qwen3-VL and ComfyUI can't run simultaneously on 12GB VRAM | Stop ComfyUI before captioning, restart after |
| Flux GGUF generation timing | ~3-4 min per 1536x640 image on RTX 3060 12GB. 34 images takes 1.5-2 hours. Launch in background and monitor output dir for progress |
| ai-toolkit missing dependencies | Install ALL requirements: `pip install -r requirements.txt --break-system-packages`. Common missing: oyaml, lpips, torchao. Each missing dep crashes on startup with no prior warning. |
| xformers PyTorch version mismatch | xformers built for different PyTorch/CUDA causes `ModuleNotFoundError` or `C++/CUDA extensions can't load`. Workaround: set `xformers: false` in YAML config. VRAM usage increases but training works. Rebuilding xformers from source is another option but slow. |
| FLUX.1-dev gated model | FLUX.1-dev requires HF login (`huggingface-cli login`) AND license acceptance on huggingface.co. Without auth, `from_pretrained("black-forest-labs/FLUX.1-dev")` raises OSError. The local GGUF (ComfyUI) cannot be used for ai-toolkit training — it needs full diffusers format. Alternative: use a local SDXL checkpoint or FLUX.1-schnell (open). |
| Body-only LoRA on different base model | If training images come from Flux but you can only use SDXL base (e.g., Pony V6) for training, center-crop 1536x640 → 1024x1024 and accept reduced fidelity. The LoRA will still capture body type/outfit diversity. Re-train with Flux base when HF auth is available. |
| Training images 1536x640 for SDXL | Ultra-wide images get center-cropped to square (640x640 → 1024x1024), losing ~58% of horizontal content. Prefer generating at 1024x1024 or 768x1024 if training on SDXL. For Flux training with AR bucketing, original 1536x640 works fine via `resolution: [640, 768, 1024]`. |
| ai-toolkit restarts from step 0 | By default, `python run.py config/train.yaml` restarts training from step 0 even if a checkpoint exists. To resume from a checkpoint, you must use the `--resume` flag or specify `resume_from` in the config YAML. Without it, all previous training progress is lost and the model retrains from scratch. Always verify step count in logs after restarting. |
| Z-Image `name_or_path` must be local path | When training on Z-Image (or any large model already downloaded locally), use the local filesystem path in `name_or_path` (e.g., `/home/user/comfy/ai-toolkit/models/Z-Image`), NOT the HuggingFace model ID (`Tongyi-MAI/Z-Image`). The HF ID causes ai-toolkit to attempt re-downloading the entire model even when it exists locally. |
| Z-Image has NO ARA | The `ostris/accuracy_recovery_adapters` repo has no Z-Image ARA. Available ARAs: flux1, hidream, qwen_image, wan22. Use `qtype: "uint4"` without ARA pipe syntax. Do NOT use qwen_image ARA — different architecture. |
| Z-Image requires `arch: "zimage"` | Z-Image is a separate architecture from Qwen-Image. Use `arch: "zimage"` in ai-toolkit config, NOT `arch: "qwen_image"`. The `ZImageModel` extension registers dynamically. You may also need to patch `ModelArch` Literal in `toolkit/config_modules.py` to add `"zimage"` for type validation. |
| Z-Image LoRA loss oscillation | Loss for Z-Image LoRAs with batch_size=1 oscillates 0.25-0.68 per step — much wider than SDXL body LoRAs. This is normal. Do NOT expect smooth downward loss curves. Check sample images at each checkpoint (every 500 steps) instead of relying on loss values. Total training time: ~8-9 hours for 3000 steps on RTX 3060 12GB. |
| ai-toolkit `run.py` positional arg syntax | Do NOT use `config=filename.yaml`. Use `python run.py filename.yaml` (if in `config/` dir) or `python run.py /full/path/to/config.yaml`. The `config=` prefix causes a "Could not find config file" error. |
| ai-toolkit PYTHONUNBUFFERED for background | ai-toolkit's Python output is fully buffered by default. When running in background, this causes complete silence for minutes (model loading). Always use `PYTHONUNBUFFERED=1 python -u run.py ...` for background training. |
| ai-toolkit config directory is `config/` (singular) | NOT `configs/` (plural). Config files go in `~/comfy/ai-toolkit/config/`. |
| Pony V6 quality tags in sample prompts | Pony V6 XL expects quality tags in prompts: prefix with `score_9, score_8_up,` and add `score_6, score_5, score_4` to negative prompts. Without these tags, Pony V6 produces lower quality output. |
| Body LoRA loss oscillation | Loss for body-only LoRAs on SDXL oscillates widely (0.002–0.28 per step). This is normal — the 0.08–0.15 "well-trained" range applies to face LoRAs with consistent features. Body LoRAs with diverse poses/outfits have inherently higher variance. Check sample images instead of loss values for quality assessment. |
| Pony V6 body LoRA low strength = cartoonish | Body LoRAs on Pony V6 XL require strength 0.9–1.0. At 0.7–0.8, Pony's anime-style base dominates and results look cartoonish despite realistic training images. Test at 0.8, 0.9, 0.95, 1.0 — the sweet spot is usually 0.9 for body LoRAs. Face LoRAs tolerate lower strengths (0.7–0.85) because face identity is more distinctive than body proportions. |
| SDXL noise_scheduler for ai-toolkit | For SDXL models in ai-toolkit, use `noise_scheduler: "ddpm"` and `sample.sampler: "ddpm"` with `guidance_scale: 7`. For Flux, use `noise_scheduler: "flowmatch"` and `sample.sampler: "flowmatch"` with `guidance_scale: 3.5`. Mixing these up causes poor training results. |
| ai-toolkit `quantize` and `low_vram` | These flags are Flux-specific. For SDXL models, set `quantize: false` and remove `low_vram`. SDXL models fit in 12GB without quantization. |
| ComfyUI must be stopped during LoRA training | ComfyUI uses ~1.2GB VRAM even idle. Stop it (`kill <pid>`) before ai-toolkit training. Restart after training with `python3 main.py --listen 0.0.0.0 --port 8188`. |
| Phase 2 (ReActor face swap) FAILURE for body LoRA | ReActor produces generic/plastic faces that don't match reference. For body-only LoRA, skip face swap entirely — train on Flux-generated bodies without face reference. The LoRA learns body type, not face. |
| Cross-architecture LoRA produces poor results | SDXL-trained LoRAs used on SD1.5 checkpoints (like ChilloutMix) produce noticeably worse body consistency and introduce artifacts even at reduced weights (face 0.6, body 0.5). User verdict: "hay más inconsistencias." **Always train a dedicated LoRA on the target base model architecture** — cross-architecture use is a stopgap, not production quality. The architecture mismatch (SDXL UNet dimensions → SD1.5 UNet) causes feature bleeding and loss of detail. |
| Z-Image generation via ai-toolkit produces black images | The `job: generate` pipeline for Z-Image in ai-toolkit produces 100% black PNGs (all-zero latents). Bug is in the sampler/denoising loop, not in the LoRA or model. Tested with and without LoRA across multiple resolutions. **Workaround**: Upload Z-Image LoRA to PixAI for generation, or use ComfyUI with a different checkpoint (SDXL/Flux) — but the LoRA face won't transfer across architectures. See `ehyra-zimage-lora` skill for full details. |
| ai-toolkit `inference_lora_path` crashes generate | In `job: generate` configs, use `assistant_lora_path` (NOT `inference_lora_path`). The wrong key causes `AttributeError: 'NoneType' object has no attribute 'is_active'` because `self.assistant_lora` is None. See `ehyra-zimage-lora` skill for config example. |
| ai-toolkit generate config needs `device: cuda` | The `GenerateProcess` defaults to CPU if `device` is not specified. Always set `device: cuda` under `config:` section for any GPU generation. |
| Manual captions from known prompts | When you generated images from structured prompts (outfit/scene/pose combos), write captions manually from the original prompt data instead of running Qwen3-VL. This guarantees accuracy and saves VRAM/time. Format: `<trigger>, body description, outfit, pose, scene, lighting, photorealistic full body shot` |

## 7. Iteration

### If Undertrained
- Increase steps (add 500–1000)
- Increase rank to 64 for more expressivity
- Add more diverse images to dataset
- Check caption quality — are trigger words present in every caption?

### If Overfitting
- Reduce steps (try -500)
- Reduce rank to 16
- Reduce learning rate to 5e-5
- Augment dataset with more variety
- Add dropout (0.1) to LoRA layers
- Use earlier checkpoint

### If Mixed Results
- Review captions for consistency
- Ensure all images paired with .txt files
- Verify trigger word appears in every caption
- Split dataset: remove low-quality images
- Try different seeds for evaluation (5+ per checkpoint)

## Quick Reference: Full Pipeline Commands

```bash
# 1. Generate variations (ComfyUI must be running)
# → Use comfyui-batch-generate skill

# 2. Caption all images (ComfyUI must be stopped for VRAM)
python caption_images.py --input_dir /path/to/training_data/3hyr4_p3r50n \
  --trigger_word 3hyr4_p3r50n \
  --model Qwen/Qwen3-VL-4B-Instruct \
  --quantize --low_vrm

# 3. Train LoRA
cd /home/brierainz/comfy/ai-toolkit/
python run.py config/character_lora.yml

# 4. Evaluate checkpoints
python run.py inference --lora_path output/3hyr4_p3r50n/step3000.safetensors \
  --prompt "3hyr4_p3r50n, portrait, detailed face" \
  --num_images 4

# 5. Iterate based on results
```