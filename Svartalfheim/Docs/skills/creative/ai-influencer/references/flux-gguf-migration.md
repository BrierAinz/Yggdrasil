# Flux.1 Dev GGUF Q8_0 Migration Notes

Migration from ChilloutMix (SD1.5) to Flux.1 Dev Q8_0 GGUF for Freya AI influencer project, May 2026.

## Why Flux Over ChilloutMix

ChilloutMix (SD1.5) produces decent Asian face consistency but suffers from:
- Low resolution (512×768 native)
- Limited photorealism (anime-influenced aesthetic even with "photorealistic" tags)
- Body inconsistency across seeds
- SD1.5 architecture limitations (older model, less semantic understanding)

Flux.1 Dev Q8_0 GGUF advantages:
- **10/10 photorealism** vs ChilloutMix's 6-7/10
- **10/10 body type accuracy** (curvy slim hourglass rendered correctly without BBW tags)
- **10/10 full-body composition** at 1536×640 ultra-wide (ChilloutMix struggles with full-body)
- **Better semantic understanding** of complex prompts
- **1024×1024 native resolution** (vs 512×768)

## GGUFLoaderKJ — Critical Node Name

The ComfyUI-GGUF package renamed its model loading node. The correct node for loading GGUF quantized Flux models is:

- ✅ `GGUFLoaderKJ` — current correct node name
- ❌ `UnetLoaderGGUF` — does NOT exist, causes HTTP 400 error
- ❌ `UNETLoaderGGUF` — does NOT exist

Verify available GGUF nodes at runtime:
```bash
curl -s http://127.0.0.1:8188/object_info | python3 -c "import sys,json; d=json.load(sys.stdin); [print(k) for k in d if 'GGUF' in k.upper()]"
```

## GGUFLoaderKJ Input Parameters

```python
{
    "class_type": "GGUFLoaderKJ",
    "inputs": {
        "model_name": "flux1-dev-Q8_0.gguf",    # filename in models/unet/
        "extra_model_name": "none",               # optional additional model
        "dequant_dtype": "default",               # dequantization dtype
        "patch_dtype": "default",                  # patch dtype
        "patch_on_device": false,                  # keep patches on GPU
        "enable_fp16_accumulation": false,         # fp16 math accumulation
        "attention_override": "none"               # "none", "sdpa", "flash", etc.
    }
}
```

## Complete Flux GGUF Workflow (API Format)

Minimal working workflow validated on RTX 3060 12GB:

```json
{
    "1": {
        "class_type": "GGUFLoaderKJ",
        "inputs": {
            "model_name": "flux1-dev-Q8_0.gguf",
            "extra_model_name": "none",
            "dequant_dtype": "default",
            "patch_dtype": "default",
            "patch_on_device": false,
            "enable_fp16_accumulation": false,
            "attention_override": "none"
        }
    },
    "2": {
        "class_type": "DualCLIPLoader",
        "inputs": {
            "clip_name1": "t5xxl_fp8_e4m3fn.safetensors",
            "clip_name2": "clip_l.safetensors",
            "type": "flux"
        }
    },
    "3": {
        "class_type": "VAELoader",
        "inputs": {"vae_name": "ae.safetensors"}
    },
    "4": {
        "class_type": "ModelSamplingFlux",
        "inputs": {
            "model": ["1", 0],
            "max_shift": 1.15,
            "base_shift": 0.5,
            "width": 1024,
            "height": 1024
        }
    },
    "5": {
        "class_type": "CLIPTextEncode",
        "inputs": {
            "text": "1girl, fr3y4, black long hair, honey eyes, goth eyeliner, photorealistic",
            "clip": ["2", 0]
        }
    },
    "6": {
        "class_type": "CLIPTextEncode",
        "inputs": {"text": "", "clip": ["2", 0]}
    },
    "7": {
        "class_type": "FluxGuidance",
        "inputs": {"guidance": 3.5, "conditioning": ["5", 0]}
    },
    "8": {
        "class_type": "EmptyLatentImage",
        "inputs": {"width": 1024, "height": 1024, "batch_size": 1}
    },
    "9": {
        "class_type": "KSampler",
        "inputs": {
            "seed": -1, "steps": 20, "cfg": 1.0,
            "sampler_name": "euler", "scheduler": "simple",
            "denoise": 1.0,
            "model": ["4", 0], "positive": ["7", 0],
            "negative": ["6", 0], "latent_image": ["8", 0]
        }
    },
    "10": {
        "class_type": "VAEDecode",
        "inputs": {"samples": ["9", 0], "vae": ["3", 0]}
    },
    "11": {
        "class_type": "SaveImage",
        "inputs": {"filename_prefix": "flux_freya", "images": ["10", 0]}
    }
}
```

## Required Model Files

| File | Size | Path | Source |
|------|------|------|--------|
| `flux1-dev-Q8_0.gguf` | ~12GB | `models/unet/` | `city96/FLUX.1-dev-GGUF` on HuggingFace |
| `t5xxl_fp8_e4m3fn.safetensors` | ~4.6GB | `models/clip/` (or `models/text_encoders/`) | `comfyanonymous/flux_text_encoders` on HuggingFace |
| `clip_l.safetensors` | ~235MB | `models/clip/` (or `models/text_encoders/`) | `comfyanonymous/flux_text_encoders` on HuggingFace |
| `ae.safetensors` | ~320MB | `models/vae/` | `black-forest-labs/FLUX.1-dev` on HuggingFace |

**Note:** ComfyUI may look for text encoders in either `models/clip/` or `models/text_encoders/` — symlink or copy if the node can't find them. Verify paths with `curl -s http://127.0.0.1:8188/object_info/DualCLIPLoader`.

## RTX 3060 12GB Performance

| Setting | Time | VRAM |
|---------|------|-------|
| 1024×1024, 20 steps | ~7 min (first run, model load) | ~11.5 GB |
| 1024×1024, 20 steps (subsequent) | ~3-4 min | ~11.5 GB |
| 1536×640, 20 steps | ~3-4 min | ~11.5 GB |

VRAM is very tight at 11.5/12 GB. Kill ComfyUI during LoRA training. No room for additional models (IPAdapter, etc.) running simultaneously.

## Key Differences from SDXL/SD1.5 Workflows

1. **No negative prompt meaning** — Flux ignores negative conditioning. Still need an empty CLIPTextEncode node as `negative` input for KSampler, but `text: ""` and `cfg: 1.0`.
2. **FluxGuidance node** — wraps CLIP conditioning with guidance scale. Flux dev = 3.5, schnell = 1.0. No separate CFG guidance via KSampler.
3. **ModelSamplingFlux** — mandatory node. Width/height must match EmptyLatentImage.
4. **Separate VAE** — Flux uses `ae.safetensors`, NOT checkpoint-baked VAE.
5. **KSampler cfg=1.0** — Flux dev uses cfg 1.0 with euler sampler and simple scheduler.
6. **GGUFLoaderKJ not UnetLoaderGGUF** — the node was renamed. Use `GGUFLoaderKJ` with full parameter set.

## Freya Character Prompt Notes

- **Trigger word:** `fr3y4`
- **Base prompt:** `1girl, fr3y4, black long hair, honey eyes, goth eyeliner, Korean Japanese face, high cheekbones, natural lips, voluptuous slim, large breasts, big butt, no tattoos, dark goth minimalist grunge oversized clothing`
- **Body generation at 1536×640** produces consistent full-body without BBW tags — Flux understands "curvy slim hourglass" correctly
- **Face candidates should be 1024×1024** for face detail, body shots at 1536×640

## Face-First Selection Process

When creating a new character without an existing LoRA:

1. Generate 5 face-only candidates (1024×1024, different seeds, same prompt)
2. Present to user for selection
3. Use selected seed as base for full dataset generation
4. Each seed produces a different face even with identical prompts — this is why face-first saves time
5. After face selection, generate 25-30 variations (poses, outfits, expressions, lighting)
6. Auto-caption with trigger word `fr3y4`
7. Train Flux LoRA on curated dataset

### Face Candidate Generation Parameters (Validated)

For face candidates, use **28 steps** (higher than the standard 20) for better facial detail:

```python
# Face candidate generation — key differences from standard workflow
"seed": 50001,       # Different seed per candidate (50001, 50042, 50133, 50207, 50389)
"steps": 28,         # Higher than standard 20 — better face detail
"cfg": 1.0,          # Standard for Flux (guidance comes from FluxGuidance node)
# FluxGuidance: 3.5   # Standard for Flux dev
# Resolution: 1024×1024  # Square for face detail (use 1536×640 for full-body)
```

The prompt used for Freya face candidates:
```
1girl, fr3y4, black long hair, honey colored eyes with goth eyeliner, Korean-Japanese features, high cheekbones, natural lips, no tattoos, wearing dark oversized hoodie, choker, minimalist goth style, cinematic lighting, 8k, photorealistic, detailed skin texture
```

## PuLID for Flux Face Consistency

### Why PuLID, Not IPAdapter

IPAdapter Plus (`ComfyUI_IPAdapter_plus`) only supports SD1.5 and SDXL — it has no Flux-compatible adapter. For face consistency with Flux.1 Dev, **PuLID** (Pose-agnostic and Lightweight Identity) is the correct tool. It's zero-shot: provide one reference face photo and it maintains identity across varied generations.

### PuLID Setup (Validated on RTX 3060 12GB)

**Custom node:** `ComfyUI-PuLID-Flux` from `balazik/ComfyUI-PuLID-Flux`

```bash
cd ~/comfy/ComfyUI/custom_nodes
git clone https://github.com/balazik/ComfyUI-PuLID-Flux.git
source ~/comfy/ComfyUI/.venv/bin/activate
pip install insightface onnxruntime onnxruntime-gpu facexlib timm ftfy
# Restart ComfyUI after install
```

**Required models:**

| File | Size | Path | Download URL |
|------|------|------|-------------|
| `pulid_flux_v0.9.1.safetensors` | ~1.1GB | `models/pulid/` | `https://huggingface.co/h94/PuLID/resolve/main/pulid_flux_v0.9.1.safetensors` |
| `EVA02_CLIP_L_336_psz14_s6B.pt` | ~816MB | `models/clip/` | `https://huggingface.co/h94/PuLID/resolve/main/EVA02_CLIP_L_336_psz14_s6B.pt` |
| `1k3d68.onnx` | — | `models/insightface/models/antelopev2/` | `https://huggingface.co/datasets/GourieND/insightface_antelopev2/resolve/main/` |
| `2d106det.onnx` | — | `models/insightface/models/antelopev2/` | same |
| `genderage.onnx` | — | `models/insightface/models/antelopev2/` | same |
| `scrfd_10g_bnkps.onnx` | — | `models/insightface/models/antelopev2/` | same |

**⚠️ AntelopeV2 ≠ buffalo_l:** PuLID uses AntelopeV2 models (different directory). ReActor and IPAdapter use buffalo_l. Both coexist in their respective subdirectories under `models/insightface/models/`.

**Available PuLID nodes (verify after restart):**
- `PulidFluxModelLoader` — loads the PuLID model
- `PulidFluxEvaClipLoader` — loads EVA-CLIP
- `PulidFluxInsightFaceLoader` — loads AntelopeV2 face analysis (provider: "CUDA")
- `ApplyPulidFlux` — applies face identity to model + conditioning
- `easy pulIDApply` / `easy pulIDApplyADV` — simplified wrappers

**⚠️ PuLID API parameter names differ from UI display — ALWAYS verify via `/object_info`:**
Three rounds of debugging (HTTP 400 errors) revealed that PuLID nodes use different parameter names in API format vs the ComfyUI web UI. Always verify before building workflows:
```bash
curl -s http://127.0.0.1:8188/object_info/PulidFluxModelLoader | python3 -m json.tool
curl -s http://127.0.0.1:8188/object_info/PulidFluxEvaClipLoader | python3 -m json.tool
curl -s http://127.0.0.1:8188/object_info/ApplyPulidFlux | python3 -m json.tool
```

Known API parameter mismatches (validated May 2026):
- `PulidFluxModelLoader`: use `pulid_file` (NOT `pulid_name`) — the template was wrong
- `PulidFluxEvaClipLoader`: use `eva_file` (NOT `eva_name`)
- `PulidFluxInsightFaceLoader`: `provider` must be explicitly set — use `"CUDA"` if onnxruntime-gpu supports it, `"CPU"` on Python 3.13+ (which lacks CUDAExecutionProvider). Check with `python -c "import onnxruntime; print(onnxruntime.get_available_providers())"`
- `KSampler`: MUST include `denoise: 1.0` — omitting it causes validation error in some ComfyUI versions
- `ApplyPulidFlux`: `weight`, `start_at`, `end_at`, `fusion` are correct as documented

**VRAM impact:** PuLID adds ~2GB on top of Flux Q8's ~11.5GB baseline, peaking at ~11.8GB on RTX 3060 12GB. Very tight but works. Reduce resolution or steps if OOM occurs.

### Face Candidate Selection (Freya)

Five Flux face candidates generated at 1024×1024, seeds 50001-50389:
- **A (seed 50001):** Blonde hair — inconsistent with character spec
- **B (seed 50042):** Slightly blurry
- **C (seed 50133):** Slightly blurry
- **D (seed 50207):** Slightly blurry
- **E (seed 50389):** BEST — sharp, correct features, chosen as reference

Selected candidate E for PuLID-based dataset generation.
Reference image: `~/comfy/output/freya_flux_candidates/freya_flux_candidate_E.png`

### PuLID Dataset Generation Workflow (VALIDATED ✅)

PuLID is now fully working on RTX 3060 12GB. Validated end-to-end: reference face image → PuLID face embedding → consistent generation. First successful generation: `freya_pulid_TEST_00001_.png` (1024×1024, ~512s on RTX 3060 with CPU InsightFace).

**Critical fixes required for ComfyUI v0.20.1+ (see comfyui skill `references/pulid-flux-pitfalls.md`):**
1. `w600k_r50.onnx` must be copied from `buffalo_l/` to `antelopev2/` (face embedding model missing by default)
2. `forward_orig()` in `pulidflux.py` must accept `timestep_zero_index`, `transformer_options`, `**kwargs` (ComfyUI v0.20.1 adds these params)

**Steps:**
1. Load face E as PuLID reference image ✅
2. Vary prompts for diversity (poses, outfits, expressions, lighting, settings) — pending
3. PuLID keeps face identity consistent across all variations ✅ (validated)
4. Curate best 20-25 images — pending
5. Auto-caption with trigger word `fr3y4` — pending
6. Train dedicated Flux LoRA on curated dataset for permanent consistency — pending

**Performance:** ~8.5 min per image with CPU InsightFace on RTX 3060. Full 25-image dataset ≈ 3.5-4 hours.