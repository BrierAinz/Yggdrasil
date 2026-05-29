---
name: ehyra-zimage-lora
description: Full LoRA training pipeline for Ehyra character using Z-Image Base (Tongyi-MAI/Z-Image) on ai-toolkit
trigger: User says "continuar con Z-Image" or asks to resume Ehyra LoRA training
---

# Ehyra Full LoRA — Z-Image Base

## Overview
Train a full LoRA for the Ehyra character using Z-Image Base model via ai-toolkit.

## Z-Image Architecture Details

Z-Image (Tongyi-MAI/Z-Image) uses these components:
- **Pipeline**: `ZImagePipeline` (diffusers)
- **Transformer**: `ZImageTransformer2DModel` (3840 dim, 30 layers, 30 heads, 16 in_channels)
- **Text Encoder**: `Qwen3ForCausalLM` (Qwen3-2.6B variant, 36 layers, hidden_size 2560)
- **Tokenizer**: `Qwen2Tokenizer`
- **VAE**: `AutoencoderKL`
- **Scheduler**: `FlowMatchEulerDiscreteScheduler` (flow matching, same as Flux)
- **arch property**: `"zimage"` (NOT "qwen_image" — they are separate architectures)

## Pipeline Steps (in order)

### 1. Download Z-Image Base
- Model: `Tongyi-MAI/Z-Image` on HuggingFace (~33GB)
- **PITFALL**: `huggingface-cli` is DEPRECATED. Use `hf download` instead:
  ```bash
  cd ~/comfy/ai-toolkit && source .venv/bin/activate
  hf download Tongyi-MAI/Z-Image --local-dir ~/comfy/ai-toolkit/models/Z-Image
  ```
- Run in background: add `&` or use background process
- Verify download: `du -sh ~/comfy/ai-toolkit/models/Z-Image/` should show ~33GB
- Sufficient disk space required (~33GB model + ~8GB for Qwen3-VL captioning model)

### 2. Patch ModelArch Literal (REQUIRED)
- ai-toolkit's `ModelArch` Literal in `toolkit/config_modules.py` does NOT include `"zimage"` out of the box
- **PITFALL**: Without this patch, the YAML config `arch: "zimage"` will not validate
- The extension `extensions_built_in/diffusion_models/z_image/z_image.py` EXISTS and registers `arch = "zimage"` dynamically via `AI_TOOLKIT_MODELS`
- Patch: add `"zimage"` to the ModelArch Literal:
  ```python
  # In ~/comfy/ai-toolkit/toolkit/config_modules.py line ~582
  # CHANGE FROM:
  ModelArch = Literal['sd1', 'sd2', 'sd3', 'sdxl', 'pixart', 'pixart_sigma', 'auraflow', 'flux', 'flex1', 'flex2', 'lumina2', 'vega', 'ssd', 'wan21']
  # CHANGE TO:
  ModelArch = Literal['sd1', 'sd2', 'sd3', 'sdxl', 'pixart', 'pixart_sigma', 'auraflow', 'flux', 'flex1', 'flex2', 'lumina2', 'vega', 'ssd', 'wan21', 'zimage']
  ```
- The `validate_configs()` function does NOT validate against this Literal at runtime, so training works without the patch — but it should be patched for correctness.

### 3. Prepare dataset
- Source refs:
  - Faces: `dataset/images/ehyra_reference/` (44 images)
  - Body: `dataset/images/ehyra_reference_body/` (17 images)
- Consolidate into single folder: `dataset/images/ehyra_dataset/`
- Each image needs a corresponding `.txt` caption file with same filename
- Body refs should be renamed with consistent prefix (e.g., `ehyra_body_001.jpg`)

### 4. Auto-caption with Qwen3-VL
- Script: `~/comfy/ai-toolkit/caption_ehyra.py` (already created)
- Uses `Qwen3-VL-4B-Instruct` with 4-bit quantization (~8GB VRAM)
- Trigger word: `ehyra`
- **PITFALL**: Requires `qwen-vl-utils` package: `pip install qwen-vl-utils`
- **PITFALL**: On RTX 3060 12GB, cannot run Qwen3-VL alongside ComfyUI or training. Kill other GPU processes first.
- **PITFALL**: Use `processor.batch_decode()` NOT `batch_text_decoder` (removed in newer transformers)
- **PITFALL**: Use plain filesystem paths for images, NOT `file://` URIs
- **CRITICAL PITFALL**: Qwen3-VL injects refusal prefixes (~15% of captions) like `"Actually, this is not an anime or manga character illustration — it's a real-life photograph of..."` and meta-commentary (~10%) like `"Here's a detailed description... crafted for a training dataset:\n\n"`. These MUST be cleaned before training or they poison the LoRA. See `auto-captioning` skill for cleanup script pattern. Verification: `grep -rl "Actually" *.txt` and `grep -rl "Here's" *.txt` should return zero matches after cleanup.
- Captions auto-skip images that already have `.txt` files (resume-safe)
- After captioning, script frees GPU memory (`del model; torch.cuda.empty_cache()`)

### 5. Create config YAML
- Location: `~/comfy/ai-toolkit/config/train_lora_ehyra_zimage.yaml` (NOT `configs/` — it's `config/`)
- **PITFALL**: `name_or_path` MUST use local filesystem path, NOT HuggingFace model ID. Using `"Tongyi-MAI/Z-Image"` causes ai-toolkit to attempt re-downloading ~33GB instead of using the local copy. Use `/home/brierainz/comfy/ai-toolkit/models/Z-Image`.
- Config file created at this path. Key params:
  - `arch: "zimage"` (separate from qwen_image — Z-Image has its own arch)
  - `name_or_path: "/home/brierainz/comfy/ai-toolkit/models/Z-Image"` (LOCAL PATH, not HF ID)
  - `trigger_word: "ehyra"`
  - `network: type lora, linear 16, linear_alpha 16`
  - `steps: 3000`, `lr: 1e-4`, `optimizer: adamw8bit`
  - `quantize: true`, `qtype: "uint4"` (see ARA pitfall below)
  - `quantize_te: true`, `qtype_te: "qfloat8"`, `low_vram: true`
  - `cache_text_embeddings: true` (critical for 12GB VRAM)
  - `gradient_checkpointing: true`
  - `noise_scheduler: "flowmatch"`, `dtype: bf16`
  - `resolution: [512, 768, 1024]`
- See `references/config-details.md` for full config template and ARA details.

### 6. Train LoRA
```bash
cd ~/comfy/ai-toolkit && source .venv/bin/activate
# IMPORTANT: Use positional arg (filename or full path), NOT "config=filename.yaml"
PYTHONUNBUFFERED=1 python -u run.py /home/brierainz/comfy/ai-toolkit/config/train_lora_ehyra_zimage.yaml
```
- **PITFALL**: `run.py` takes config path as POSITIONAL argument. Do NOT use `config=filename.yaml` syntax — it will fail with "Could not find config file config=filename.yaml". Use just the filename (if in `config/` dir) or full path.
- **PITFALL**: Run with `PYTHONUNBUFFERED=1 python -u` when running in background. Without this, output buffering causes silence for minutes while the model loads, making it appear crashed. The `-u` flag and env var force unbuffered stdout.
- RTX 3060 12GB — uint4 quantization required. **Observed VRAM: ~7.5 GB** (not 2-3 GB — that was an underestimate)
- Expected startup sequence: load transformer (~20s) → quantize 30 blocks (~40s) → move transformer to CPU → load+quantize text encoder (~30s with qfloat8) → cache latents (~17s for 61 images) → cache text embeddings (<1s) → EMA init → **training loop begins**
- Training time: ~8-9 hours for 3000 steps on RTX 3060 (6-12s/step depending on bucket resolution). Monitor with `nvidia-smi` or `ps aux | grep run.py`
- Checkpoints saved every 500 steps to `output/ehyra_zimage_lora_v1/`
- Sample images generated every 500 steps alongside checkpoints
- Run in background so user can multitask on other projects
- See `references/config-details.md` for full observed training stats, bucket distribution, and monitoring commands
- See `references/zimage-generation-black-images.md` for the Z-Image black image bug — reproduction, diagnosis, and workarounds
- See `references/comfyui-sdxl-inference.md` for local ComfyUI generation with Ehyra XL LoRA (SDXL), including validated parameters, workflow JSON, and the 15-image influencer prompt set

### 7. Evaluate checkpoints
- Checkpoints saved every 500 steps: `ehyra_zimage_lora_v1_000000500.safetensors`, etc.
- Sample images generated every 500 steps in `samples/` directory
- Checkpoint file size: ~82 MB each
- Compare sample quality across steps (500, 1000, 1500, 2000)
- Loss oscillation (0.25-0.68) is normal with batch_size=1 — don't expect smooth loss curves
- Use Z-Image pipeline or ComfyUI with the LoRA to generate test images at each checkpoint weight
- Select best checkpoint for final LoRA — don't default to the last step

## Resume Training from Step 2000

Training was paused at step 2000/3000. To resume to 3000:

1. Edit `~/comfy/ai-toolkit/config/train_lora_ehyra_zimage.yaml`
2. Add `resume` key pointing to step 2000 checkpoint:
   ```yaml
   process:
     - type: sd_trainer
       resume: output/ehyra_zimage_lora_v1/ehyra_zimage_lora_v1_000002000.safetensors
       training_folder: "output"
   ```
   **PITFALL**: The `resume` key must be added INSIDE the `process` item, alongside `type` and `training_folder`. Don't nest it or put it elsewhere — ai-toolkit reads it as a sibling key to `type`.
3. Launch:
   ```bash
   cd ~/comfy/ai-toolkit && source .venv/bin/activate
   PYTHONUNBUFFERED=1 python -u run.py /home/brierainz/comfy/ai-toolkit/config/train_lora_ehyra_zimage.yaml 2>&1
   ```

**Current status (May 2026)**: **TRAINING COMPLETE** — 3000/3000 steps finished. Loss final: ~0.30-0.64 (oscillating, normal for batch_size=1). Total training time: ~8-9h for full 3000 steps (2h12m for steps 2000→3000 resume). Final model saved at `ehyra_zimage_lora_v1.safetensors` (82MB). Sample images generated at steps 0, 500, 1000, 1500, 2000, 2500, 3000.

13. **Z-Image generation via ai-toolkit `job: generate` produces 100% black images** — Both with and without LoRA, the `GenerateProcess` produces all-zero latents that decode to black PNGs. Tested with multiple configs and resolutions. This is a bug in ai-toolkit's Z-Image pipeline, NOT in the LoRA or model. **Workaround**: Upload LoRA to PixAI for Z-Image generation, or use a different checkpoint (SDXL/Flux) via ComfyUI (but Ehyra face won't transfer across architectures).

14. **`inference_lora_path` crashes ai-toolkit GenerateProcess** — In `job: generate` configs, use `assistant_lora_path` (NOT `inference_lora_path`). The `inference_lora_path` key causes `AttributeError: 'NoneType' object has no attribute 'is_active'` at `base_model.py:385` because `self.assistant_lora` is only initialized by `assistant_lora_path`. For training configs, the existing `assistant_lora_path` key also works.

15. **`device: cuda` required in generate config** — ai-toolkit's `GenerateProcess` defaults to CPU if `device` is not specified. Always add `device: cuda` under the `config:` section. Running on CPU is extremely slow and may also contribute to black image output.

**Next steps**: Upload LoRA to PixAI (Z-Image native, consistent Ehyra face) or CivitAI. Use PixAI/DiT.2 for face-consistent generation, or ComfyUI with SDXL/Flux for general quality (but not Ehyra face).

### Key Files
- Config: `~/comfy/ai-toolkit/config/train_lora_ehyra_zimage.yaml`
- Model: `~/comfy/ai-toolkit/models/Z-Image/`
- Dataset: `~/comfy/ai-toolkit/dataset/images/ehyra_dataset/` (61 imgs + captions)
- Output: `~/comfy/ai-toolkit/output/ehyra_zimage_lora_v1/`
- **Final model**: `ehyra_zimage_lora_v1.safetensors` (82MB, 3000 steps)
- Checkpoints: steps 500, 1000, 1500, 2000, 3000 (82MB each)
- Samples: 3 final sample images in `samples/` directory

## Pitfalls

1. **`huggingface-cli` DEPRECATED**: Use `hf download` instead. The old command exits with error code 1 and does nothing.

2. **ModelArch Literal missing "zimage"**: Must patch `toolkit/config_modules.py` to add `"zimage"` to the `ModelArch` Literal. The extension registers it dynamically, but the type hint doesn't include it. See Step 2.

3. **NO ARA for Z-Image**: The `ostris/accuracy_recovery_adapters` repo does NOT contain a Z-Image ARA. Available ARAs: flux1, hidream, qwen_image, wan22. **Workaround**: Use `qtype: "uint4"` without ARA pipe syntax. If VRAM is tight, try `qtype: "uint3"` without ARA (lower quality but fits). Do NOT use the `qwen_image` ARA with Z-Image — different architecture.

4. **Z-Image ≠ Qwen-Image**: These are separate architectures. Z-Image uses `ZImageTransformer2DModel` + `Qwen3ForCausalLM` text encoder. The `arch: "zimage"` setting is required, NOT `"qwen_image"`.

5. **`text_embedding_space_version`**: Set automatically from `model_config.arch` — becomes `"zimage"` when config has `arch: "zimage"`. Handles list-format text embeddings correctly. No manual config needed.

6. **Cannot run captioning + training simultaneously**: Qwen3-VL-4B uses ~8GB VRAM. On RTX 3060 12GB, must complete captioning first, then free GPU memory before starting training.

7. **Config path**: ai-toolkit uses `config/` (singular), NOT `configs/` (plural). Config files go in `~/comfy/ai-toolkit/config/`.

8. **Batch size 1**: Required for 12GB VRAM. gradient_accumulation can be increased if needed.

9. **`run.py` positional arg syntax**: Do NOT use `config=filename.yaml`. Use `python run.py filename.yaml` (if in `config/` dir) or `python run.py /full/path/to/config.yaml`. The `config=` prefix causes a "Could not find config file" error.

10. **`PYTHONUNBUFFERED=1` for background runs**: ai-toolkit's Python output is fully buffered by default. When running in background, this causes complete silence for minutes (while loading models), making it look like a crash. Always use `PYTHONUNBUFFERED=1 python -u run.py ...` for background training.

11. **Qwen3-VL caption contamination**: ~25% of captions will contain refusal prefixes ("Actually, this is not an anime...") or meta-commentary ("Here's a detailed description... crafted for a training dataset"). These MUST be cleaned before training. See Step 4 and the `auto-captioning` skill for cleanup patterns. Verification: `grep -rl "Actually" *.txt` and `grep -rl "Here's" *.txt` should return zero matches.

12. **`name_or_path` must be local path**: When the model is already downloaded, use the local filesystem path (`/home/brierainz/comfy/ai-toolkit/models/Z-Image`), NOT the HuggingFace model ID (`Tongyi-MAI/Z-Image`). Using the HF ID causes ai-toolkit to attempt re-downloading the full model even though it exists locally, wasting time and bandwidth.

## LoRA Evaluation / Generation (BLOCKED locally)

**Z-Image generation via ai-toolkit `job: generate` is BROKEN** — produces 100% black images. This was tested exhaustively:
- With LoRA (`assistant_lora_path`): 5 images, all black (min=0, max=0, mean=0)
- Without LoRA (base model only): 1 image, all black
- Multiple resolution configs tested (768x1344, 768x512)
- Model loads, quantizes, and runs the sampler without errors — output is just all zeros

**Root cause (suspected):** ai-toolkit's Z-Image `GenerateProcess` has a bug in the sampler initialization or denoising loop. The model loads correctly, text encoder works, but the generated latents are all zeros → VAE decodes to black. This appears to be an ai-toolkit issue, not a model or LoRA issue.

**Workarounds for generating Ehyra images with the trained LoRA:**
- **Option A: Upload LoRA to PixAI** — Z-Image (DiT.2) is natively supported. This is the best path for face-consistent Ehyra images.
- **Option B: Use CivitAI with a different checkpoint** — e.g., SDXL or Flux model via ComfyUI. Ehyra face will NOT be consistent (LoRA trained on Z-Image architecture only). Use ComfyUI for generation, but accept different face quality.
- **Option C: Debug ai-toolkit's Z-Image GenerateProcess** — time-consuming, requires diving into `toolkit/generation/generate_process.py` and the Z-Image pipeline code.

**Generate config key pitfall: `inference_lora_path` crashes ai-toolkit.** When using the `inference_lora_path` key in a `job: generate` config, ai-toolkit crashes with `AttributeError: 'NoneType' object has no attribute 'is_active'` at `base_model.py:385` because `self.assistant_lora` is None. The correct key is `assistant_lora_path`:
```yaml
# WRONG — crashes:
process:
  - type: to_folder
    inference_lora_path: /path/to/lora.safetensors  # ← CRASHES

# CORRECT:
process:
  - type: to_folder
    assistant_lora_path: /path/to/lora.safetensors  # ← loads LoRA
```

**Generate config requires `device: cuda` explicitly.** Without it, ai-toolkit defaults to CPU which is extremely slow (and may contribute to the black image issue):
```yaml
config:
  name: generate_test
  device: cuda  # REQUIRED — defaults to CPU otherwise
```

**Sample generate config (produces black images — for reference only):**
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
      - prompt: "ehyra, a woman with long black hair with straight bangs, dramatic winged eyeliner, round wire-rimmed glasses, geometric clavicle tattoo, porcelain skin, lip piercing, fashion editorial portrait"
        width: 768
        height: 1024
        seed: 42
        steps: 25
        cfg: 3.0
        sampler: flowmatch
```

## Critical Notes
- RTX 3060 12GB — uint4 quantization + gradient checkpointing + cache_text_embeddings required. **Observed VRAM: 7.5 GB during cache, 8.9-9.2 GB during training** (75% of 12GB). Loss oscillates 0.25-0.68 with batch_size=1 — this is normal. Total time: ~8-9 hours for 3000 steps.
- Z-Image download is ~20GB (not 33GB — HF shows compressed sizes). Total disk: ~20GB model + 8GB Qwen3-VL for captioning.
- CivitAI API key: 557dee19fba740dc81b2b4925e1af3b8
- PixAI API key: sk-ln7AYoAOtsdnR5I2Ds2YoqEJQc9Wl2adEWsHyHjf0YEqtFLd
- User prefers autonomous 40-60 min blocks — run training in background
- PIVOTED from Pony V6 to Z-Image Base
- Caption cleanup: ~16 of 61 captions had refusal prefixes or meta-commentary from Qwen3-VL. Always verify with `grep -rl "Actually" *.txt` and `grep -rl "Here's" *.txt` after captioning.
- **LoRA v1 COMPLETE** (3000/3000 steps, 82MB safetensors). Not yet uploaded to CivitAI/PixAI.
- **Local Z-Image generation is BROKEN** — all-black output. Use PixAI or alternative checkpoint for generation.
- **Ehyra XL LoRA (PixAI SDXL) WORKS LOCALLY** via ComfyUI. See `references/comfyui-sdxl-inference.md` for full workflow with checkpoint comparison.
- **LoRA filename changed**: `checkpoint-e36_s684.safetensors` → `ehyra_xl_lora.safetensors` — always use the new name in workflow JSONs and scripts.
- **Best checkpoint for influencer faces**: RealVisXL V4.0 produces more consistent facial features than Juggernaut XL v9 for batch AI influencer image generation. Juggernaut is too artistic/variable for character consistency.
- **CivitAI model upload**: REST API only supports GET/read operations. Creating models requires the web UI at https://civitai.com/model/create — no programmatic upload available.