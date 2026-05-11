---
name: comfyui-batch-generate
description: Batch image generation via ComfyUI API with IPAdapter FaceID — covers reference prep, workflow JSON, prompt submission, deterministic seeds, resume logic, and quality verification.
version: 1.0.0
category: mlops
tags: [comfyui, image-generation, ipadapter, faceid, batch, stable-diffusion, automation]
---

# ComfyUI Batch Image Generation

Generalized batch photorealistic image generation pipeline using ComfyUI's API with IPAdapter FaceID for face consistency.

## Prerequisites

- ComfyUI installed and running (default path: `/home/brierainz/comfy/ComfyUI`)
- Default checkpoint: `Juggernaut-XL_v9_RunDiffusionPhoto_v2.safetensors`
- IPAdapter FaceID models installed in `models/ipadapter/`
- GPU with sufficient VRAM (RTX 3060 12GB → batch_size=1)
- Python 3 with `requests`, `hashlib`, `PIL`

## 1. Preparing Reference Images

### Naming Convention

```
ref_<person_id>_<variant>.jpg
```

- Use lowercase, no spaces. Example: `ref_alice_front.jpg`, `ref_bob_side.jpg`
- One reference per subject variant — the pipeline matches on `<person_id>` prefix

### Format Requirements

| Property    | Value                          |
|-------------|--------------------------------|
| Format      | `.jpg` or `.jpeg` (not `.png`) |
| Resolution  | 512×512 minimum, square crops preferred |
| Color space | sRGB, 8-bit                    |
| Face size   | Face must occupy ≥20% of frame |

**Pitfall — `.jpeg` vs `.jpg`:** ComfyUI node inputs and Python `os.path` may report `.jpeg` while your code expects `.jpg`. Normalize extensions early:

```python
import os
def normalize_ext(path):
    base, ext = os.path.splitext(path)
    if ext.lower() in ('.jpeg',):
        ext = '.jpg'
    return base + ext
```

### Storage

Place reference images in: `<comfyui_root>/input/` or a dedicated subdirectory like `<comfyui_root>/input/ref_images/`.

## 2. ComfyUI Workflow JSON with IPAdapter FaceID

### Workflow Structure

A typical batch workflow for face-consistent generation contains these nodes:

1. **CheckpointLoaderSimple** — loads the base SDXL checkpoint
2. **IPAdapter FaceID** — applies face embedding from the reference image
3. **CLIPTextEncode** (positive + negative prompts)
4. **KSampler** — generates latent with seed, steps, cfg
5. **VAEDecode** — decodes latent to pixel space
6. **SaveImage** — writes output to ComfyUI's `output/` directory

### Critical: Two-Phase Body Generation (Validated)

IPAdapter FaceID CANNOT produce full-body images (see Pitfall #21). The validated approach for voluptuous/curvy body LoRA datasets:

**Phase 1 — Body Generation (no IPAdapter):**
- Checkpoint: Pony V6 XL (NOT Juggernaut, NOT RealVisXL)
- Aspect ratio: 1344×768 (WIDE) — tall ratios always crop mid-thigh
- Mandatory tags in positive prompt: `bbw, thick, very wide hips, thick thighs` (without these, output is slim)
- Pony V6 quality tags: `score_9, score_8_up, score_7_up, score_6_up, source_photo, source_5_more`
- Negative prompt must include: `slim, thin, skinny, narrow hips, small breasts, flat chest`
- Seed: deterministic via `hashlib.md5`
- **STYLE WARNING:** Pony V6 produces semi-illustrated/semi-realistic output (realism ~5-6/10), NOT photorealistic. For photorealistic body generation, use Flux.1-dev GGUF Q8 instead (see Phase 1B below)

**Phase 1B — Photorealistic Body Generation (Flux.1-dev GGUF Q8):**
- Use when photorealistic output is required (Pony V6 produces semi-illustrated style)
- Checkpoint: Flux.1-dev in GGUF Q8 format (runs on RTX 3060 12GB, ~3-5 min/image)
- Full node chain (DIFFERENT from SDXL in every node):
  ```
  UnetLoaderGGUF(unet_name="flux1-dev-Q8_0.gguf")
  → DualCLIPLoader(clip_name1="t5xxl_fp8_e4m3fn.safetensors", clip_name2="clip_l.safetensors", type="flux")
  → VAELoader(vae_name="ae.safetensors")
  → ModelSamplingFlux(model=UnetLoaderGGUF.0, max_shift=1.15, base_shift=0.5, width=W, height=H)
  → CLIPTextEncode(text=prompt, clip=DualCLIPLoader.0)   ← positive
  → CLIPTextEncode(text="", clip=DualCLIPLoader.0)       ← EMPTY negative (Flux ignores it)
  → FluxGuidance(guidance=3.5, conditioning=positive.0)  ← dev only; schnell uses 1.0
  → EmptyLatentImage(width=W, height=H, batch_size=1)
  → KSampler(steps=20, cfg=1.0, sampler="euler", scheduler="simple", denoise=1.0)
  → VAEDecode(samples=KSampler.0, vae=VAELoader.0)
  → SaveImage
  ```
- **Critical differences from SDXL:**
  - `UnetLoaderGGUF` (NOT `UnetLoader`, NOT `CheckpointLoaderSimple`) — loads GGUF quantized models
  - `DualCLIPLoader` MUST have `type="flux"` parameter — without it, text encoding is wrong
  - `FluxGuidance` (NOT `FluxGuidcoder` — that was a typo) — wraps conditioning with guidance scale
  - `ModelSamplingFlux` — REQUIRED for Flux models; set width/height to match latent
  - KSampler: `cfg=1.0` (NOT 7.0), `sampler=euler`, `scheduler=simple` for Flux dev
  - Negative prompt MUST be a separate empty CLIPTextEncode node — do NOT reuse positive
  - `VAELoader` with `ae.safetensors` — separate node, NOT baked into checkpoint
- Models required: `unet/flux1-dev-Q8_0.gguf`, `text_encoders/t5xxl_fp8_e4m3fn.safetensors`, `text_encoders/clip_l.safetensors`, `vae/ae.safetensors`
- Requires ComfyUI-GGUF custom node: `git clone https://github.com/city96/ComfyUI-GGUF` into `custom_nodes/`
- Flux.1-schnell requires HuggingFace auth (401 Unauthorized) — use GGUF dev instead
- BBW tags: use natural language body descriptions ("voluptuous woman with wide hips", "full-figured body") — Flux responds better to natural language than Danbooru-style tags
- Aspect ratio: landscape 1344×768 still recommended for full-body; test prompt quality first at 1024×1024

**Phase 2 — Face Swap (ReActor):**
- Node: `ReActorFastFaceSwap` or `ReActorFaceSwap`
- Required model: `inswapper_128.onnx` (~529MB) in `models/insightface/`
- Face detection: `retinaface_resnet50`, face restore: `codeformer-v0.1.0.pth`
- Input: Phase 1 body image (from either Pony V6 or Flux), source: reference face photo
- This transfers identity without distorting body composition

This replaces the old IPAdapter-only approach for body generation. The `build_workflow()` function below is still valid for portrait/face generation via IPAdapter.

### Critical: IPAdapter FaceID vs FaceID plusv2

> **Pitfall:** `IPAdapter FaceID plusv2` requires the `ViT-bigG-14` vision encoder which may not be installed. Use plain `IPAdapter FaceID` unless you've explicitly confirmed the encoder is present.

- **FaceID (plain):** Uses only the InsightFace face embedding. Works out-of-the-box with the standard `ip-adapter-faceid_sd15.bin` or `ip-adapter-faceid_sdxl.bin` models.
- **FaceID plusv2:** Requires `clip-vit-large-patch14` AND `ViT-bigG-14` in `models/clip_vision/`. Fails silently or throws a model-not-found error if missing.

Check for the encoder:

```bash
ls /home/brierainz/comfy/ComfyUI/models/clip_vision/ | grep -i "bigG\|big-g"
# If empty → use plain FaceID only
```

### Workflow JSON Template

```python
import json

def build_workflow(
    prompt: str,
    negative_prompt: str,
    reference_image: str,
    seed: int,
    checkpoint: str = "Juggernaut-XL_v9_RunDiffusionPhoto_v2.safetensors",
    steps: int = 30,
    cfg: float = 7.0,
    width: int = 1024,
    height: int = 1024,
    batch_size: int = 1,
    ipadapter_model: str = "ip-adapter-faceid_sdxl.bin",
):
    """Build a ComfyUI workflow JSON for IPAdapter FaceID generation."""
    return {
        "1": {  # CheckpointLoader
            "class_type": "CheckpointLoaderSimple",
            "inputs": {
                "ckpt_name": checkpoint,
            }
        },
        "2": {  # IPAdapter FaceID
            "class_type": "IPAdapterFaceID",
            "inputs": {
                "model": ["1", 0],
                "image": reference_image,  # filename relative to input dir
                "ipadapter_file": ipadapter_model,
            }
        },
        "3": {  # Positive prompt
            "class_type": "CLIPTextEncode",
            "inputs": {
                "text": prompt,
                "clip": ["1", 1],
            }
        },
        "4": {  # Negative prompt
            "class_type": "CLIPTextEncode",
            "inputs": {
                "text": negative_prompt,
                "clip": ["1", 1],
            }
        },
        "5": {  # KSampler
            "class_type": "KSampler",
            "inputs": {
                "seed": seed,
                "steps": steps,
                "cfg": cfg,
                "sampler_name": "dpmpp_2m",
                "scheduler": "karras",
                "denoise": 1.0,
                "model": ["2", 0],  # model from IPAdapter, NOT checkpoint directly
                "positive": ["3", 0],
                "negative": ["4", 0],
                "latent_image": ["6", 0],  # from EmptyLatentImage
            }
        },
        "6": {  # EmptyLatentImage
            "class_type": "EmptyLatentImage",
            "inputs": {
                "width": width,
                "height": height,
                "batch_size": batch_size,
            }
        },
        "7": {  # VAEDecode
            "class_type": "VAEDecode",
            "inputs": {
                "samples": ["5", 0],
                "vae": ["1", 2],
            }
        },
        "8": {  # SaveImage
            "class_type": "SaveImage",
            "inputs": {
                "filename_prefix": "batch_out",
                "images": ["7", 0],
            }
        },
    }
```

> **Pitfall:** The model input to KSampler must come from the IPAdapter node (`["2", 0]`), NOT the checkpoint loader, because IPAdapter modifies the model in-place.

## 3. Batch Generation Script Pattern

### Submit Prompt → Poll → Download

```python
import time
import json
import requests
from pathlib import Path

COMFYUI_URL = "http://127.0.0.1:8188"
OUTPUT_DIR = Path("/home/brierainz/comfy/ComfyUI/output")
DOWNLOAD_DIR = Path("./generated_images")

def queue_prompt(workflow: dict) -> str:
    """Submit a workflow to ComfyUI and return the prompt_id."""
    resp = requests.post(f"{COMFYUI_URL}/prompt", json={"prompt": workflow})
    resp.raise_for_status()
    return resp.json()["prompt_id"]


def wait_for_completion(prompt_id: str, poll_interval: float = 2.0, timeout: float = 600) -> dict:
    """
    Poll ComfyUI's history endpoint until the prompt completes.
    
    CRITICAL: ComfyUI v0.20+ uses status_str:'success' in the status dict,
    NOT status:'completed'. Older versions used status.status == 'completed'.
    
    Check BOTH patterns for robustness.
    """
    start = time.time()
    while time.time() - start < timeout:
        resp = requests.get(f"{COMFYUI_URL}/history/{prompt_id}")
        if resp.status_code != 200:
            time.sleep(poll_interval)
            continue

        history = resp.json()
        if prompt_id not in history:
            time.sleep(poll_interval)
            continue

        prompt_data = history[prompt_id]
        status_info = prompt_data.get("status", {})

        # ComfyUI v0.20+: check status_str
        if status_info.get("status_str") == "success":
            return prompt_data

        # ComfyUI older: check status.completed
        if status_info.get("status", {}).get("completed", False):
            return prompt_data

        # Check for errors
        if status_info.get("status_str") == "error":
            raise RuntimeError(f"ComfyUI error for prompt {prompt_id}: {status_info}")

        time.sleep(poll_interval)

    raise TimeoutError(f"Prompt {prompt_id} did not complete within {timeout}s")


def download_outputs(prompt_data: dict, dest_dir: Path) -> list[Path]:
    """Download generated images from ComfyUI output to dest_dir."""
    dest_dir.mkdir(parents=True, exist_ok=True)
    downloaded = []

    outputs = prompt_data.get("outputs", {})
    for node_id, node_output in outputs.items():
        if "images" not in node_output:
            continue
        for img_info in node_output["images"]:
            filename = img_info["filename"]
            subfolder = img_info.get("subfolder", "")
            url = f"{COMFYUI_URL}/view?filename={filename}&subfolder={subfolder}&type=output"
            
            resp = requests.get(url)
            resp.raise_for_status()
            
            out_path = dest_dir / filename
            out_path.write_bytes(resp.content)
            downloaded.append(out_path)

    return downloaded


def generate_one(workflow: dict) -> list[Path]:
    """Full pipeline: submit, wait, download."""
    prompt_id = queue_prompt(workflow)
    prompt_data = wait_for_completion(prompt_id)
    return download_outputs(prompt_data, DOWNLOAD_DIR)
```

> **Pitfall — ComfyUI v0.20+ status check:** The completion check must use `status_str == 'success'` OR check `status.completed`. Using only `status == 'completed'` will hang forever on newer ComfyUI versions because that field no longer exists in the same position.

## 4. Deterministic Seed Generation

> **Pitfall:** Python's built-in `hash()` is randomized via `PYTHONHASHSEED` and produces different values across runs. NEVER use `hash()` for seed generation.

Always use `hashlib.md5` (or sha256) for deterministic seeds:

```python
import hashlib

def deterministic_seed(person_id: str, variant: str, index: int = 0) -> int:
    """
    Generate a deterministic seed from person/variant/index.
    Uses MD5 for determinism — hash() is randomized in Python 3.
    """
    raw = f"{person_id}__{variant}__{index}".encode("utf-8")
    digest = hashlib.md5(raw).hexdigest()
    return int(digest, 16) % (2**32)  # 32-bit unsigned int for ComfyUI


# Example usage across batch:
for i in range(num_images):
    seed = deterministic_seed("alice", "professional_headshot", i)
    # seed is the same on every run for same inputs
```

### Why MD5 and not `hash()`?

| Function      | Deterministic? | Python version | Notes                              |
|---------------|----------------|----------------|------------------------------------|
| `hash(s)`     | NO             | 3.3+           | Randomized by PYTHONHASHSEED       |
| `hashlib.md5` | YES            | All            | Stable, fast, sufficient for seeds |

## 5. Resume Logic (Skip Existing Files)

```python
def get_pending_tasks(
    person_id: str,
    variants: list[str],
    images_per_variant: int,
    output_dir: Path,
) -> list[tuple[str, int]]:
    """
    Return (variant, index) pairs that haven't been generated yet.
    Enables resume from where the last run left off.
    """
    pending = []
    for variant in variants:
        for idx in range(images_per_variant):
            expected_name = f"{person_id}_{variant}_{idx:04d}.jpg"
            expected_path = output_dir / expected_name
            if not expected_path.exists():
                pending.append((variant, idx))
    return pending


# Usage in batch loop:
pending = get_pending_tasks("alice", ["professional", "casual", "artistic"], 10, DOWNLOAD_DIR)
for variant, idx in pending:
    seed = deterministic_seed("alice", variant, idx)
    workflow = build_workflow(
        prompt=f"professional headshot of a person, {variant} style",
        negative_prompt="blurry, low quality, distorted",
        reference_image=f"ref_alice_{variant}.jpg",
        seed=seed,
    )
    generate_one(workflow)
```

## 6. Output File Naming Conventions

```
{person_id}_{variant}_{index:04d}.jpg
```

Examples:
- `alice_professional_0000.jpg`
- `alice_professional_0001.jpg`
- `bob_casual_0000.jpg`

When downloading from ComfyUI, the `SaveImage` node generates names like `batch_out_001.jpg_` which are not useful. Rename after download:

```python
import shutil

def rename_output(raw_paths: list[Path], person_id: str, variant: str, index: int, dest_dir: Path) -> Path:
    """Rename a ComfyUI output file to our naming convention."""
    final_name = f"{person_id}_{variant}_{index:04d}.jpg"
    final_path = dest_dir / final_name
    shutil.move(str(raw_paths[0]), str(final_path))
    return final_path
```

## 7. Quality Verification

After batch generation, verify output quality:

```python
from PIL import Image
import os

def verify_outputs(output_dir: Path, expected_count: int) -> dict:
    """Check batch output for completeness and basic quality."""
    results = {
        "total_files": 0,
        "missing": 0,
        "corrupt": 0,
        "too_small": 0,
        "ok": 0,
    }
    
    for img_path in sorted(output_dir.glob("*.jpg")):
        results["total_files"] += 1
        try:
            with Image.open(img_path) as img:
                w, h = img.size
                if w < 512 or h < 512:
                    results["too_small"] += 1
                    print(f"  TOO SMALL: {img_path.name} ({w}x{h})")
                else:
                    results["ok"] += 1
        except Exception as e:
            results["corrupt"] += 1
            print(f"  CORRUPT: {img_path.name} — {e}")
    
    results["missing"] = max(0, expected_count - results["total_files"])
    return results


# Post-batch check:
results = verify_outputs(DOWNLOAD_DIR, expected_count=len(pending))
print(f"Verified: {results['ok']} OK, {results['corrupt']} corrupt, {results['too_small']} too small, {results['missing']} missing")
```

## 8. ComfyUI Output Directory Cleanup

ComfyUI accumulates files in its output directory. Clean between batch runs to avoid confusion:

```bash
# Before starting a batch
rm -f /home/brierainz/comfy/ComfyUI/output/batch_out_*.png
rm -f /home/brierainz/comfy/ComfyUI/output/batch_out_*.jpg
```

Or in Python:

```python
import glob

def clean_comfyui_output():
    """Remove batch_out files from ComfyUI output dir before a new run."""
    pattern = str(OUTPUT_DIR / "batch_out_*")
    for f in glob.glob(pattern):
        os.remove(f)
```

> **Pitfall:** If you don't clean up, `download_outputs` may pick up stale files from previous runs, and `SaveImage` node numbering will not start at 0.

## 9. Full Batch Script Outline

```python
#!/usr/bin/env python3
"""ComfyUI Batch FaceID Generation Pipeline"""
import hashlib
import json
import os
import time
import glob
from pathlib import Path
import requests
from PIL import Image

COMFYUI_URL = "http://127.0.0.1:8188"
COMFYUI_ROOT = Path("/home/brierainz/comfy/ComfyUI")
OUTPUT_DIR = COMFYUI_ROOT / "output"
DOWNLOAD_DIR = Path("./generated_images")
CHECKPOINT = "Juggernaut-XL_v9_RunDiffusionPhoto_v2.safetensors"

# --- Configuration ---
PERSON_ID = "alice"
VARIANTS = ["professional", "casual", "artistic"]
IMAGES_PER_VARIANT = 10
REFERENCE_IMAGE = "ref_alice.jpg"
PROMPT_TEMPLATE = "photo of a person, {variant} style, high quality, detailed"
NEGATIVE_PROMPT = "blurry, low quality, distorted, deformed, ugly"

def main():
    DOWNLOAD_DIR.mkdir(parents=True, exist_ok=True)
    clean_comfyui_output()
    
    pending = get_pending_tasks(PERSON_ID, VARIANTS, IMAGES_PER_VARIANT, DOWNLOAD_DIR)
    print(f"Pending tasks: {len(pending)}")
    
    for variant, idx in pending:
        seed = deterministic_seed(PERSON_ID, variant, idx)
        prompt = PROMPT_TEMPLATE.format(variant=variant)
        
        workflow = build_workflow(
            prompt=prompt,
            negative_prompt=NEGATIVE_PROMPT,
            reference_image=REFERENCE_IMAGE,
            seed=seed,
            checkpoint=CHECKPOINT,
        )
        
        raw_paths = generate_one(workflow)
        final_path = rename_output(raw_paths, PERSON_ID, variant, idx, DOWNLOAD_DIR)
        print(f"  Generated: {final_path}")
    
    results = verify_outputs(DOWNLOAD_DIR, IMAGES_PER_VARIANT * len(VARIANTS))
    print(f"Done: {results}")

if __name__ == "__main__":
    main()
```

## Pitfalls Summary

| # | Pitfall | Fix |
|---|---------|-----|
| 1 | ComfyUI v0.20+ completion status | Use `status_str == 'success'` OR `status.completed`, NOT `status == 'completed'` |
| 2 | `hash()` non-deterministic | Use `hashlib.md5(text.encode()).hexdigest()` |
| 3 | IPAdapter FaceID plusv2 missing ViT-bigG | Use plain FaceID unless encoder is confirmed installed |
| 4 | `.jpeg` vs `.jpg` extension mismatch | Normalize extensions with `normalize_ext()` early |
| 5 | Stale files in ComfyUI output dir | Clean `output/batch_out_*` before each run |
| 6 | KSampler model from wrong node | Model input must come from IPAdapter node, not CheckpointLoader |
| 7 | RTX 3060 12GB VRAM | Set `batch_size=1`; don't attempt batch > 1 |
| 8 | SaveImage node naming | Rename output files to `{person_id}_{variant}_{index:04d}.jpg` after download |
| 9 | FaceID Plus V2 requires ViT-bigG-14 (1664 dims) | Use plain FaceID only; dims mismatch (1280 vs 1664) crashes generation |
| 10 | CLIP vision filename must match IPAdapter regex | Model file must be named `ViT-H-14.s32B.b79K.safetensors` — renaming breaks pattern match |
| 11 | InsightFace no-face failures on bad refs | Pre-filter refs for clear facial visibility; exclude photos with hidden/obscured faces |
| 12 | Queue flooding SLOWS batch | Drain queue between submissions (sequential mode) — reduces per-image time from 7–8 min to ~34s |
| 13 | ComfyUI + Qwen3-VL VRAM conflict (12GB) | Both need ~8–9GB; stop ComfyUI before captioning |
| 14 | Qwen3-VLprocessor: `batch_text_decoder` doesn't exist | Use `processor.batch_decode()` only |
| 15 | Qwen3-VL image path: `file://` prefix breaks loading | Use plain path string: `"/path/to/image.jpg"` not `"file:///path/to/image.jpg"` |
| 16 | Double prefix in output filenames | Remove redundant base/ref prefix from naming to avoid `ehyra_ehyra_ref_01_closeup` |
| 17 | InsightFace "No face detected" on large portrait photos | Face occupies too small a % of the frame (e.g. 2304×4096 full-body → face is ~5%). Crop to face region first, or exclude the ref. Center-cropping may not help if face isn't centered. |
| 18 | Python `print()` silently lost in background processes | Use `python -u script.py` or `PYTHONUNBUFFERED=1` + `sys.stdout.reconfigure(line_buffering=True)`. Without this, 0 lines appear in process logs. |
| 19 | PyTorch/IPAdapter tensor dumps flood stdout | ComfyUI loads models with verbose tensor output (dimensions, providers, dtype). In background scripts these explode the log, drowning custom print output. Filter or redirect. |
| 20 | InsightFace standalone script: no CUDA | Outside ComfyUI's venv/process, InsightFace falls back to CPUExecutionProvider. Face detection works but slower; GPU-only ops (like ipadapter_model loading) will fail entirely. |
| 21 | IPAdapter FaceID dominates composition | Cannot produce full-body images — even weight 0.30 forces portrait crop. Use two-phase approach: generate body WITHOUT IPAdapter (Pony V6 + BBW tags at 1344x768), then ReActor face swap. Validated: body 8-9/10 voluptuous, face swap preserves identity |
| 22 | Juggernaut XL + RealVisXL V4 both have portrait/slim bias | Juggernaut crops mid-thigh; RealVisXL V4 ALSO tested and FAILED (full_body 2/10, voluptuous 2/10). Only Pony V6 with BBW tags + wide ratio produces full-body voluptuous |
| 23 | Pony V6 XL + BBW tags = full-body BUT semi-illustrated style | Pony V6 at 1344x768 with BBW tags produces body composition 8-9/10 but realism ~5-6/10 (semi-illustrated). For photorealistic output, use Flux.1-dev GGUF Q8 instead. Two-phase: Pony or Flux body → ReActor face swap |
| 26 | ReActor for face swap (Phase 2) | Use `ReActorFastFaceSwap` node. Required: `inswapper_128.onnx` in `models/insightface/` (~529MB). API fields: `swap_model: "inswapper_128.onnx"`, `facedetection: "retinaface_resnet50"`, `face_restore_model: "codeformer-v0.1.0.pth"`. Validated working with `codeformer-v0.1.0.pth` face restoration |
| 27 | Aspect ratio critical for full body | 1344x768 (WIDE) is the ONLY tested ratio producing full-body. 768x1344 and 1024x1024 both crop mid-thigh. Always use landscape ratio for body LoRA datasets |
| 28 | BBW tags mandatory for curvy body | Without "bbw, thick, very wide hips, thick thighs" in prompt, ALL SDXL checkpoints produce slim/average builds regardless of prompt language like "curves, voluptuous, generous figure" |
| 26 | ReActor for face swap (Phase 2) | Use `ReActorFastFaceSwap` node after generating bodies without IPAdapter. Models go in `models/reactor/` (inswapper_128.onnx) |
| 27 | Wrong checkpoint for body generation | Juggernaut XL = portrait/slim. RealVisXL V4 = portrait/slim. Pony V6 = full-body but semi-illustrated style. Flux.1-dev = photorealistic (recommended for body datasets). Always test checkpoint before batch generation |
| 28 | Flux.1-dev GGUF Q8 setup differs from SDXL | Uses UnetLoaderGGUF (not CheckpointLoaderSimple, not UnetLoader), DualCLIPLoader(type="flux"), FluxGuidance (not FluxGuidcoder — that was a typo), ModelSamplingFlux, VAELoader. Requires 4 models: flux1-dev-Q8_0.gguf, clip_l.safetensors, t5xxl_fp8_e4m3fn.safetensors, ae.safetensors. KSampler must use cfg=1.0, sampler=euler, scheduler=simple |
| 29 | Flux negative prompt must be separate empty node | Do NOT reuse the positive CLIPTextEncode node as negative. Create a SECOND CLIPTextEncode with text="" — Flux ignores negative conditioning but ComfyUI requires a valid conditioning connection |
| 30 | Flux.1-schnell download requires HuggingFace auth | Direct URL download returns 401 Unauthorized. Must use `huggingface-cli login` then `huggingface-cli download`. Flux.1-dev GGUF Q8 from city96 does NOT require auth |
| 31 | wget/curl silently create 0-byte files for large downloads | Files >4GB may download as 0 bytes with exit code 0. ALWAYS verify file size after download. Use `huggingface-cli download` or `hf download` for reliability |
| 32 | ComfyUI venv prefix is `.venv/` not `venv/` | The ComfyUI venv (when created by the user) uses `.venv/bin/python`, NOT `venv/bin/activate`. Always run `.venv/bin/python main.py` directly — there is no `venv/bin/activate` to source. |
| 33 | LoRA-only workflow (no IPAdapter) for trained character LoRAs | When using a trained character LoRA (e.g., Ehyra XL from PixAI DiT.2), use `LoraLoader` node between `CheckpointLoaderSimple` and `KSampler`. No IPAdapter needed — the LoRA carries the character identity. Params: Juggernaut XL base, LoRA weight 0.8, 50 steps, CFG 6, Euler a sampler, 768x1344 portrait |
| 34 | SD1.5 + ChilloutMix for Asian face consistency | Community gold standard for consistent Asian faces. CivitAI model ID 6424, download version 11732 (NiPrunedFp16Fix, ~2GB). Native resolution: 512×768 (NOT 768×1344). Requires dedicated VAE: `vae-ft-mse-840000.safetensors` (NOT SDXL VAE). SDXL LoRAs work on SD1.5 but reduce weights to 0.5-0.6 (from 0.7-0.8). For best results, train a dedicated SD1.5 LoRA on ChilloutMix base |
| 35 | Cross-architecture LoRA weight reduction | SDXL-trained LoRAs used on SD1.5 checkpoints must have reduced weights to avoid artifacts. Tested: Face LoRA 0.6 + Body LoRA 0.5 on ChilloutMix (SD1.5) vs 0.8 + 0.6 on SDXL. Always test weights 0.3-0.7 range when crossing architectures; higher weights cause distortion and color artifacts |

## Reference Paths

- ComfyUI root: `/home/brierainz/comfy/ComfyUI`
- Default checkpoint: `Juggernaut-XL_v9_RunDiffusionPhoto_v2.safetensors`
- IPAdapter models: `<comfyui_root>/models/ipadapter/`
- Input images: `<comfyui_root>/input/`
- Output images: `<comfyui_root>/output/`
- API endpoint: `http://127.0.0.1:8188`

## Templates

- `templates/flux_dev_gguf_txt2img_api.json` — Ready-to-run Flux.1-dev GGUF Q8 txt2img workflow (API format). 1344×768 landscape, 20 steps, euler/simple scheduler, cfg=1.0, guidance=3.5. Inject your prompt in node 5 and seed in node 9.

## References

- `references/ehyra-v3-regeneration.md` — Ehyra LoRA v3 session-specific details: config values, file paths, bugs discovered, and dataset breakdown