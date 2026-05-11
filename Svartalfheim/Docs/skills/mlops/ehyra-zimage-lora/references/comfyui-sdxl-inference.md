# ComfyUI SDXL Local Inference for Ehyra XL LoRA

## Status: WORKING (May 2026)

Z-Image local generation produces 100% black images (see `zimage-generation-black-images.md`). 
The Ehyra XL LoRA trained on PixAI (DiT.2) is SDXL-compatible and works with ComfyUI + SDXL checkpoints locally.

## Setup

### 1. ComfyUI Installation
```bash
cd ~/comfy
git clone https://github.com/comfyanonymous/ComfyUI.git
cd ComfyUI
python -m venv .venv
.venv/bin/pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu121
.venv/bin/pip install -r requirements.txt
```

### 2. Start ComfyUI
```bash
cd ~/comfy/ComfyUI
.venv/bin/python main.py --listen 0.0.0.0 --port 8188
```

**PITFALL**: Use `.venv/bin/python` directly. There is NO `venv/bin/activate` — the venv uses `.venv/` prefix, not `venv/`.

### 3. Required Models
- **SDXL Checkpoint**: Any SDXL 1.0 checkpoint in `models/checkpoints/`
  - `Juggernaut XL v9` — artistic/painterly, inconsistent faces for character work
  - `RealVisXL V4.0` — **recommended** for AI influencer use (better face consistency)
  - `PonyDiffusion V6 XL` — anime style, not photorealistic
- **Ehyra XL LoRA**: `ehyra_xl_lora.safetensors` (244MB) → `models/loras/`
  - **NOTE**: Originally named `checkpoint-e36_s684.safetensors`, renamed to `ehyra_xl_lora.safetensors` for clarity
- **Other LoRAs available**:
  - `ehyra_body_lora_v1` (4 checkpoint files) — body-focused training
  - `eir_niflheimr_v2` — different character
  - `faceid` — InsightFace for face consistency

### 4. LoRA Details
- **Source**: PixAI DiT.2 training, exported as SDXL-compatible safetensors
- **Original location**: `/mnt/c/Users/Game_/Downloads/Ehyra_XL/`
- **ComfyUI path**: `~/comfy/ComfyUI/models/loras/ehyra_xl_lora.safetensors`
- **Trigger word**: `ehyra`
- **Recommended weight**: 0.8
- **Training**: checkpoint e36, step 684

## SDXL Checkpoint Comparison for AI Influencer Use

| Checkpoint | Face Consistency | Photorealism | Full-Body | Notes |
|---|---|---|---|---|
| **RealVisXL V4.0** | 7/10 | 8/10 | 4/10 | Best for face-consistent influencer portraits. Crops mid-thigh for tall ratios. |
| **Juggernaut XL v9** | 4/10 | 6/10 | 3/10 | Artistic/painterly style. Faces vary significantly between images. NOT recommended for character consistency. |
| **PhotoPedia XL** (PixAI) | 9/10 | 8/10 | 6/10 | Best consistency, but only available on PixAI platform — not downloadable for local use. Reference standard. |
| **Pony V6 XL** | 6/10 | 4/10 | 8/10 | Semi-illustrated/anime style. Good full-body at wide ratios (1344x768) with BBW tags. Not photorealistic. |

**Recommendation**: For AI influencer image sets where the same character must look consistent, use **RealVisXL V4.0** for portraits/half-body shots. For full-body generation, use **Pony V6 XL** at 1344x768 (wide) with ReActor face swap (Phase 2).

## Generation Parameters (Validated)

| Parameter | Value |
|---|---|
| Width | 768 |
| Height | 1344 (portrait) |
| Steps | 50 |
| CFG | 6 |
| Sampler | euler_ancestral (Euler a) |
| Scheduler | normal |
| LoRA weight | 0.8 |
| Seed | per-image (deterministic) |

## Workflow JSON Format

Path: `~/comfy/ComfyUI/workflows/ehyra_sdxl_api.json`

Workflow nodes:
1. **CheckpointLoaderSimple** — loads SDXL checkpoint (RealVisXL or Juggernaut)
2. **LoraLoader** — loads Ehyra XL LoRA at weight 0.8
3. **CLIPTextEncode** (positive) — prompt with trigger word `ehyra`
4. **CLIPTextEncode** (negative) — negative prompt
5. **EmptyLatentImage** — 768x1344
6. **KSampler** — steps=50, cfg=6, euler_ancestral, normal scheduler
7. **VAEDecode** — latent to image
8. **SaveImage** — output to `ehyra_influencer_sdxl/` or `ehyra_realvis_test/`

**CRITICAL**: The LoraLoader node must be wired between CheckpointLoaderSimple and KSampler:
```
CheckpointLoaderSimple → LoraLoader (model + clip passthrough) → KSampler
```
The LoRA takes `model` and `clip` from the checkpoint, applies weights, and outputs modified `model` and `clip` to the KSampler.

## Influencer Prompt Set (15 images)

| # | Name | Seed | Prompt Summary |
|---|---|---|---|
| 1 | mirror_selfie | 1001 | Bathroom mirror selfie, phone in hand |
| 2 | coffee_shop | 2200 | Café window light, latte art |
| 3 | neon_street | 3300 | Cyberpunk neon rain, reflections |
| 4 | studio_portrait | 4100 | Professional portrait, soft box |
| 5 | golden_hour_rooftop | 5578 | Sunset rooftop, wind in hair |
| 6 | gym_mirror | 6643 | Gym mirror selfie, athletic wear |
| 7 | aesthetic_flat_lay | 7890 | Flat lay, coffee + phone + journal |
| 8 | car_window | 8834 | Passenger seat, city lights through rain |
| 9 | outfit_transition_1 | 9120 | Before/after outfit grid |
| 10 | outfit_transition_2 | 9456 | Second outfit transition |
| 11 | tech_minimal | 10234 | Minimal desk, MacBook, earbuds |
| 12 | fashion_brand | 11567 | Streetwear brand shoot, bold graphics |
| 13 | rain_window | 12890 | Looking out rain-covered window |
| 14 | night_out | 13456 | Night out, neon bar entrance |
| 15 | bookshop_cafe | 14012 | Reading in bookshop café |

Generation script: `~/comfy/generate_ehyra_sdxl.py` (Juggernaut XL)
Test scripts: `~/comfy/test_realvis_debug.py`, `~/comfy/test_realvis_batch.py` (RealVisXL V4.0)

## Ehyra Invariant Traits (for prompts)
- Black hair with bangs
- Winged/dramatic eyeliner
- Round wire-rimmed glasses
- Geometric clavicle tattoo/mark
- Porcelain skin
- Lip piercing (optional)

## Output Directories

| Directory | Checkpoint | Count | Status |
|---|---|---|---|
| `~/comfy/output/ehyra_influencer_sdxl/` | Juggernaut XL v9 | 15 | Inconsistent faces — not ideal for influencer use |
| `~/comfy/output/ehyra_realvis_test/` | RealVisXL V4.0 | 3 | Test batch — better face consistency |
| `~/comfy/ComfyUI/output/` | Various | varies | Default ComfyUI output dir |

Reference images (PixAI/PhotoPedia XL — gold standard for consistency):
`/mnt/c/Users/Game_/Downloads/Ehyra_Generated/` (4 images)

## ComfyUI API

Endpoint: `http://127.0.0.1:8188/prompt`
Method: POST
Body: JSON workflow (see `ehyra_sdxl_api.json`)
Response: `{"prompt_id": "uuid"}`

Poll status: `GET http://127.0.0.1:8188/history/{prompt_id}`
Output images in response under `outputs` → `images` → `filename`, `subfolder`

## CivitAI Upload

**CivitAI REST API does NOT support model creation** — only GET/read operations. To upload the Ehyra XL LoRA:
1. Go to https://civitai.com/model/create (web UI, requires login)
2. Fill in model details, upload `ehyra_xl_lora.safetensors` (244MB)
3. Set trigger word: `ehyra`, base model: SDXL 1.0

LoRA file location: `~/comfy/ComfyUI/models/loras/ehyra_xl_lora.safetensors`

## GPU Notes
- RTX 3060 12GB VRAM
- RealVisXL V4.0: ~6.5GB VRAM loaded
- Juggernaut XL v9: ~6.5GB VRAM loaded
- Generation time: ~30-45 seconds per image
- Can run ComfyUI + generation while other CPU tasks run concurrently