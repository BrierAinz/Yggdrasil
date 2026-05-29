---
name: comfyui
description: "Generate images, video, and audio with ComfyUI — install, launch, manage nodes/models, run workflows with parameter injection. Uses the official comfy-cli for lifecycle and direct REST/WebSocket API for execution."
version: 5.0.0
author: [kshitijk4poor, alt-glitch]
license: MIT
platforms: [macos, linux, windows]
compatibility: "Requires ComfyUI (local, Comfy Desktop, or Comfy Cloud) and comfy-cli (auto-installed via pipx/uvx by the setup script)."
prerequisites:
  commands: ["python3"]
setup:
  help: "Run scripts/hardware_check.py FIRST to decide local vs Comfy Cloud; then scripts/comfyui_setup.sh auto-installs locally (or use Cloud API key for platform.comfy.org)."
metadata:
  hermes:
    tags:
      - comfyui
      - image-generation
      - stable-diffusion
      - flux
      - sd3
      - wan-video
      - hunyuan-video
      - creative
      - generative-ai
      - video-generation
    related_skills: [stable-diffusion-image-generation, image_gen]
    category: creative
---

# ComfyUI

Generate images, video, audio, and 3D content through ComfyUI using the
official `comfy-cli` for setup/lifecycle and direct REST/WebSocket API
for workflow execution.

## What's in this skill

**Reference docs (`references/`):**

- `official-cli.md` — every `comfy ...` command, with flags
- `rest-api.md` — REST + WebSocket endpoints (local + cloud), payload schemas
- `workflow-format.md` — API-format JSON, common node types, param mapping
- `academia-sd-nodes.md` — AcademiaSD custom nodes (Multi-LoRA, Auto Downloader, VL Captioner, Resolution Selector, Time Calculator, etc.) — QoL nodes for dataset prep and video workflows
- `model-directory-map.md` — where to place each model type (checkpoints, diffusion_models, text_encoders, vae, loras, etc.) and key path rules
- `seedvr2-anima-nodes.md` — SeedVR2 upscaler & Anima workflow: custom nodes, models, and install steps
- `lokarni-asset-manager.md` — LokArni standalone asset catalog: API reference, CivitAI import, category mapping, bulk import patterns, Prompt Studio feature, adding custom views, pitfalls
- `two-phase-body-dataset.md` — Two-phase body dataset generation (Flux GGUF + ReActor): validated node chains, pose success rates, curation checklist, output filtering

**Scripts (`scripts/`):**

| Script | Purpose |
|--------|---------|
| `_common.py` | Shared HTTP, cloud routing, node catalogs (don't run directly) |
| `hardware_check.py` | Probe GPU/VRAM/disk → recommend local vs Comfy Cloud |
| `comfyui_setup.sh` | Hardware check + comfy-cli + ComfyUI install + launch + verify |
| `extract_schema.py` | Read a workflow → list controllable params + model deps |
| `check_deps.py` | Check workflow against running server → list missing nodes/models |
| `auto_fix_deps.py` | Run check_deps then `comfy node install` / `comfy model download` |
| `run_workflow.py` | Inject params, submit, monitor, download outputs (HTTP or WS) |
| `run_batch.py` | Submit a workflow N times with sweeps, parallel up to your tier |
| `ws_monitor.py` | Real-time WebSocket viewer for executing jobs (live progress) |
| `health_check.py` | Verification checklist runner — comfy-cli + server + models + smoke test |
| `fetch_logs.py` | Pull traceback / status messages for a given prompt_id |

**Example workflows (`workflows/`):** SD 1.5, SDXL, Flux Dev, SDXL img2img,
SDXL inpaint, ESRGAN upscale, AnimateDiff video, Wan T2V, **IPAdapter FaceID
(SDXL portrait generation preserving facial identity)**. See
`workflows/README.md`. AnimateDiff SDXL+LoRA video template also available
at `templates/animatediff_sdxl_video_api.json`. **Flux.1-dev GGUF Q8 txt2img**\ntemplate at `templates/flux_dev_gguf_txt2img_api.json` — complete workflow\nwith GGUFLoaderKJ, DualCLIPLoader, FluxGuidance, ModelSamplingFlux, and\ncorrect KSampler settings (cfg=1.0, euler, simple). **ReActor FaceSwap** template at `templates/reactor_faceswap_api.json` — verified field names for
ReActorFaceSwap node with inswapper_128, codeformer face restoration, and
retinaface_resnet50 detection. **PuLID + Flux face consistency** template at
`templates/pulid_flux_face_api.json` — complete workflow with GGUFLoaderKJ,
PuLID model/EVA-CLIP/InsightFace loaders, ApplyPulidFlux, FluxGuidance, and
KSampler (cfg=1.0, euler, simple).

## When to Use

- User asks to generate images with Stable Diffusion, SDXL, Flux, SD3, etc.
- User wants to run a specific ComfyUI workflow file
- User wants to chain generative steps (txt2img → upscale → face restore)
- User needs ControlNet, inpainting, img2img, or other advanced pipelines
- User asks to manage ComfyUI queue, check models, or install custom nodes
- User wants video/audio/3D generation via AnimateDiff, Hunyuan, Wan, AudioCraft, etc.

## Architecture: Two Layers

```
┌─────────────────────────────────────────────────────┐
│ Layer 1: comfy-cli (official lifecycle tool)        │
│   Setup, server lifecycle, custom nodes, models     │
│   → comfy install / launch / stop / node / model    │
└─────────────────────────┬───────────────────────────┘
                          │
┌─────────────────────────▼───────────────────────────┐
│ Layer 2: REST/WebSocket API + skill scripts         │
│   Workflow execution, param injection, monitoring   │
│   POST /api/prompt, GET /api/view, WS /ws           │
│   → run_workflow.py, run_batch.py, ws_monitor.py    │
└─────────────────────────────────────────────────────┘
```

**Why two layers?** The official CLI is excellent for installation and server
management but has minimal workflow execution support. The REST/WS API fills
that gap — the scripts handle param injection, execution monitoring, and
output download that the CLI doesn't do.

## Quick Start

### Detect environment

```bash
# What's available?
command -v comfy >/dev/null 2>&1 && echo "comfy-cli: installed"
curl -s http://127.0.0.1:8188/system_stats 2>/dev/null && echo "server: running"

# Can this machine run ComfyUI locally? (GPU/VRAM/disk check)
python3 scripts/hardware_check.py
```

If nothing is installed, see **Setup & Onboarding** below — but always run the
hardware check first.

### One-line health check

```bash
python3 scripts/health_check.py
# → JSON: comfy_cli on PATH? server reachable? at least one checkpoint? smoke-test passes?
```

## Core Workflow

### Step 1: Get a workflow JSON in API format

Workflows must be in API format (each node has `class_type`). They come from:

- ComfyUI web UI → **Workflow → Export (API)** (newer UI) or
  the legacy "Save (API Format)" button (older UI)
- This skill's `workflows/` directory (ready-to-run examples)
- Community downloads (civitai, Reddit, Discord) — usually editor format,
  must be loaded into ComfyUI then re-exported

Editor format (top-level `nodes` and `links` arrays) is **not directly
executable**. The scripts detect this and tell you to re-export.

### Step 2: See what's controllable

```bash
python3 scripts/extract_schema.py workflow_api.json --summary-only
# → {"parameter_count": 12, "has_negative_prompt": true, "has_seed": true, ...}

python3 scripts/extract_schema.py workflow_api.json
# → full schema with parameters, model deps, embedding refs
```

### Step 3: Run with parameters

```bash
# Local (defaults to http://127.0.0.1:8188)
python3 scripts/run_workflow.py \
  --workflow workflow_api.json \
  --args '{"prompt": "a beautiful sunset over mountains", "seed": -1, "steps": 30}' \
  --output-dir ./outputs

# Cloud (export API key once; uses correct /api routing automatically)
export COMFY_CLOUD_API_KEY="comfyui-..."
python3 scripts/run_workflow.py \
  --workflow workflow_api.json \
  --args '{"prompt": "..."}' \
  --host https://cloud.comfy.org \
  --output-dir ./outputs

# Real-time progress via WebSocket (requires `pip install websocket-client`)
python3 scripts/run_workflow.py \
  --workflow flux_dev.json \
  --args '{"prompt": "..."}' \
  --ws

# img2img / inpaint: pass --input-image to upload + reference automatically
python3 scripts/run_workflow.py \
  --workflow sdxl_img2img.json \
  --input-image image=./photo.png \
  --args '{"prompt": "make it watercolor", "denoise": 0.6}'

# Batch / sweep: 8 random seeds, parallel up to cloud tier limit
python3 scripts/run_batch.py \
  --workflow sdxl.json \
  --args '{"prompt": "abstract"}' \
  --count 8 --randomize-seed --parallel 3 \
  --output-dir ./outputs/batch
```

`-1` for `seed` (or omitting it with `--randomize-seed`) generates a fresh
random seed per run.

### Step 4: Present results

The scripts emit JSON to stdout describing every output file:

```json
{
  "status": "success",
  "prompt_id": "abc-123",
  "outputs": [
    {"file": "./outputs/sdxl_00001_.png", "node_id": "9",
     "type": "image", "filename": "sdxl_00001_.png"}
  ]
}
```

## Decision Tree

| User says | Tool | Command |
|-----------|------|---------|
| **Lifecycle (use comfy-cli)** | | |
| "install ComfyUI" | comfy-cli | `bash scripts/comfyui_setup.sh` |
| "start ComfyUI" | comfy-cli | `comfy launch --background` |
| "stop ComfyUI" | comfy-cli | `comfy stop` |
| "install X node" | comfy-cli | `comfy node install <name>` |
| "download X model" | comfy-cli | `comfy model download --url <url> --relative-path models/checkpoints` |
| "list installed models" | comfy-cli | `comfy model list` |
| "list installed nodes" | comfy-cli | `comfy node show installed` |
| **Execution (use scripts)** | | |
| "is everything ready?" | script | `health_check.py` (optionally with `--workflow X --smoke-test`) |
| "what can I change in this workflow?" | script | `extract_schema.py W.json` |
| "check if W's deps are met" | script | `check_deps.py W.json` |
| "fix missing deps" | script | `auto_fix_deps.py W.json` |
| "generate an image" | script | `run_workflow.py --workflow W --args '{...}'` |
| "use this image" (img2img) | script | `run_workflow.py --input-image image=./x.png ...` |
| "8 variations with random seeds" | script | `run_batch.py --count 8 --randomize-seed ...` |
| "show me live progress" | script | `ws_monitor.py --prompt-id <id>` |
| "fetch the error from job X" | script | `fetch_logs.py <prompt_id>` |
| **Direct REST** | | |
| "what's in the queue?" | REST | `curl http://HOST:8188/queue` (local) or `--host https://cloud.comfy.org` |
| "cancel that" | REST | `curl -X POST http://HOST:8188/interrupt` |
| "free GPU memory" | REST | `curl -X POST http://HOST:8188/free` |

## Setup & Onboarding

When a user asks to set up ComfyUI, **the FIRST thing to do is ask whether
they want Comfy Cloud (hosted, zero install, API key) or Local (install
ComfyUI on their machine)**. Don't start running install commands or hardware
checks until they've answered.

**Official docs:** https://docs.comfy.org/installation
**CLI docs:** https://docs.comfy.org/comfy-cli/getting-started
**Cloud docs:** https://docs.comfy.org/get_started/cloud
**Cloud API:** https://docs.comfy.org/development/cloud/overview

### Step 0: Ask Local vs Cloud (ALWAYS FIRST)

Suggested script:

> "Do you want to run ComfyUI locally on your machine, or use Comfy Cloud?
>
> - **Comfy Cloud** — hosted on RTX 6000 Pro GPUs, all common models pre-installed,
>   zero setup. Requires an API key (paid subscription required to actually run
>   workflows; free tier is read-only). Best if you don't have a capable GPU.
> - **Local** — free, but your machine MUST meet the hardware requirements:
>   - NVIDIA GPU with **≥6 GB VRAM** (≥8 GB for SDXL, ≥12 GB for Flux/video), OR
>   - AMD GPU with ROCm support (Linux), OR
>   - Apple Silicon Mac (M1+) with **≥16 GB unified memory** (≥32 GB recommended).
>   - Intel Macs and machines with no GPU will NOT work — use Cloud instead.
>
> Which would you like?"

Routing:

- **Cloud** → skip to **Path A**.
- **Local** → run hardware check first, then pick a path from Paths B–E based on the verdict.
- **Unsure** → run the hardware check and let the verdict decide.

### Step 1: Verify Hardware (ONLY if user chose local)

```bash
python3 scripts/hardware_check.py --json
# Optional: also probe `torch` for actual CUDA/MPS:
python3 scripts/hardware_check.py --json --check-pytorch
```

| Verdict    | Meaning                                                       | Action |
|------------|---------------------------------------------------------------|--------|
| `ok`       | ≥8 GB VRAM (discrete) OR ≥32 GB unified (Apple Silicon)       | Local install — use `comfy_cli_flag` from report |
| `marginal` | SD1.5 works; SDXL tight; Flux/video unlikely                  | Local OK for light workflows, else **Path A (Cloud)** |
| `cloud`    | No usable GPU, <6 GB VRAM, <16 GB Apple unified, Intel Mac, Rosetta Python | **Switch to Cloud** unless user explicitly forces local |

The script also surfaces `wsl: true` (WSL2 with NVIDIA passthrough) and
`rosetta: true` (x86_64 Python on Apple Silicon — must reinstall as ARM64).

If verdict is `cloud` but the user wants local, do not proceed silently.
Show the `notes` array verbatim and ask whether they want to (a) switch to
Cloud or (b) force a local install (will OOM or be unusably slow on modern models).

### Choosing an Installation Path

Use the hardware check first. The table below is the fallback for when the
user has already told you their hardware:

| Situation | Recommended Path |
|-----------|------------------|
| `verdict: cloud` from hardware check | **Path A: Comfy Cloud** |
| No GPU / want to try without commitment | **Path A: Comfy Cloud** |
| Windows + NVIDIA + non-technical | **Path B: ComfyUI Desktop** |
| Windows + NVIDIA + technical | **Path C: Portable** or **Path D: comfy-cli** |
| Linux + any GPU | **Path D: comfy-cli** (easiest) |
| macOS + Apple Silicon | **Path B: Desktop** or **Path D: comfy-cli** |
| Headless / server / CI / agents | **Path D: comfy-cli** |

For the fully automated path (hardware check → install → launch → verify):

```bash
bash scripts/comfyui_setup.sh
# Or with overrides:
bash scripts/comfyui_setup.sh --m-series --port=8190 --workspace=/data/comfy
```

It runs `hardware_check.py` internally, refuses to install locally when the
verdict is `cloud` (unless `--force-cloud-override`), picks the right
`comfy-cli` flag, and prefers `pipx`/`uvx` over global `pip` to avoid polluting
system Python.

---

### Path A: Comfy Cloud (No Local Install)

For users without a capable GPU or who want zero setup. Hosted on RTX 6000 Pro.

**Docs:** https://docs.comfy.org/get_started/cloud

1. Sign up at https://comfy.org/cloud
2. Generate an API key at https://platform.comfy.org/login
3. Set the key:
   ```bash
   export COMFY_CLOUD_API_KEY="comfyui-xxxxxxxxxxxx"
   ```
4. Run workflows:
   ```bash
   python3 scripts/run_workflow.py \
     --workflow workflows/flux_dev_txt2img.json \
     --args '{"prompt": "..."}' \
     --host https://cloud.comfy.org \
     --output-dir ./outputs
   ```

**Pricing:** https://www.comfy.org/cloud/pricing
**Concurrent jobs:** Free/Standard 1, Creator 3, Pro 5. Free tier
**cannot run workflows via API** — only browse models. Paid subscription
required for `/api/prompt`, `/api/upload/*`, `/api/view`, etc.

---

### Path B: ComfyUI Desktop (Windows / macOS)

One-click installer for non-technical users. Currently Beta.

**Docs:** https://docs.comfy.org/installation/desktop
- **Windows (NVIDIA):** https://download.comfy.org/windows/nsis/x64
- **macOS (Apple Silicon):** https://comfy.org

Linux is **not supported** for Desktop — use Path D.

---

### Path C: ComfyUI Portable (Windows Only)

**Docs:** https://docs.comfy.org/installation/comfyui_portable_windows

Download from https://github.com/comfyanonymous/ComfyUI/releases, extract,
run `run_nvidia_gpu.bat`. Update via `update/update_comfyui_stable.bat`.

---

### Path D: comfy-cli (All Platforms — Recommended for Agents)

The official CLI is the best path for headless/automated setups.

**Docs:** https://docs.comfy.org/comfy-cli/getting-started

#### Install comfy-cli

```bash
# Recommended:
pipx install comfy-cli
# Or use uvx without installing:
uvx --from comfy-cli comfy --help
# Or (if pipx/uvx unavailable):
pip install --user comfy-cli
```

Disable analytics non-interactively:
```bash
comfy --skip-prompt tracking disable
```

#### Install ComfyUI

```bash
comfy --skip-prompt install --nvidia              # NVIDIA (CUDA)
comfy --skip-prompt install --amd                 # AMD (ROCm, Linux)
comfy --skip-prompt install --m-series            # Apple Silicon (MPS)
comfy --skip-prompt install --cpu                 # CPU only (slow)
comfy --skip-prompt install --nvidia --fast-deps  # uv-based dep resolution
```

Default location: `~/comfy/ComfyUI` (Linux), `~/Documents/comfy/ComfyUI`
(macOS/Win). Override with `comfy --workspace /custom/path install`.

#### Launch / verify

```bash
comfy launch --background                       # background daemon on :8188
comfy launch -- --listen 0.0.0.0 --port 8190    # LAN-accessible custom port
curl -s http://127.0.0.1:8188/system_stats      # health check
```

---

### Path E: Manual Install (Advanced / Unsupported Hardware)

For Ascend NPU, Cambricon MLU, Intel Arc, or other unsupported hardware.

**Docs:** https://docs.comfy.org/installation/manual_install

```bash
git clone https://github.com/comfyanonymous/ComfyUI.git
cd ComfyUI
pip install torch torchvision torchaudio --extra-index-url https://download.pytorch.org/whl/cu130
pip install -r requirements.txt
python main.py
```

---

### Post-Install: Download Models

```bash
# SDXL (general purpose, ~6.5 GB)
comfy model download \
  --url "https://huggingface.co/stabilityai/stable-diffusion-xl-base-1.0/resolve/main/sd_xl_base_1.0.safetensors" \
  --relative-path models/checkpoints

# SD 1.5 (lighter, ~4 GB, good for 6 GB cards)
comfy model download \
  --url "https://huggingface.co/stable-diffusion-v1-5/stable-diffusion-v1-5/resolve/main/v1-5-pruned-emaonly.safetensors" \
  --relative-path models/checkpoints

# Flux Dev fp8 (smaller variant, ~12 GB)
comfy model download \
  --url "https://huggingface.co/Comfy-Org/flux1-dev/resolve/main/flux1-dev-fp8.safetensors" \
  --relative-path models/checkpoints

# CivitAI (set token first):
comfy model download \
  --url "https://civitai.com/api/download/models/128713" \
  --relative-path models/checkpoints \
  --set-civitai-api-token "YOUR_TOKEN"
```

List installed: `comfy model list`.

### Post-Install: Install Custom Nodes

```bash
comfy node install comfyui-impact-pack             # popular utility pack
comfy node install comfyui-animatediff-evolved     # video generation
comfy node install comfyui-controlnet-aux          # ControlNet preprocessors
comfy node install comfyui-essentials              # common helpers
comfy node update all
comfy node install-deps --workflow=workflow.json   # install everything a workflow needs
```

### Post-Install: Verify

```bash
python3 scripts/health_check.py
# → comfy_cli on PATH? server reachable? checkpoints? smoke test?

python3 scripts/check_deps.py my_workflow.json
# → are this workflow's nodes/models/embeddings installed?

python3 scripts/run_workflow.py \
  --workflow workflows/sd15_txt2img.json \
  --args '{"prompt": "test", "steps": 4}' \
  --output-dir ./test-outputs
```

## Image Upload (img2img / Inpainting)

The simplest way is to use `--input-image` with `run_workflow.py`:

```bash
python3 scripts/run_workflow.py \
  --workflow workflows/sdxl_img2img.json \
  --input-image image=./photo.png \
  --args '{"prompt": "make it cyberpunk", "denoise": 0.6}'
```

The flag uploads `photo.png`, then injects its server-side filename into
whatever schema parameter is named `image`. For inpainting, pass both:

```bash
python3 scripts/run_workflow.py \
  --workflow workflows/sdxl_inpaint.json \
  --input-image image=./photo.png \
  --input-image mask_image=./mask.png \
  --args '{"prompt": "fill with flowers"}'
```

Manual upload via REST:
```bash
curl -X POST "http://127.0.0.1:8188/upload/image" \
  -F "image=@photo.png" -F "type=input" -F "overwrite=true"
# Returns: {"name": "photo.png", "subfolder": "", "type": "input"}

# Cloud equivalent:
curl -X POST "https://cloud.comfy.org/api/upload/image" \
  -H "X-API-Key: $COMFY_CLOUD_API_KEY" \
  -F "image=@photo.png" -F "type=input" -F "overwrite=true"
```

## Cloud Specifics

- **Base URL:** `https://cloud.comfy.org`
- **Auth:** `X-API-Key` header (or `?token=KEY` for WebSocket)
- **API key:** set `$COMFY_CLOUD_API_KEY` once and the scripts pick it up automatically
- **Output download:** `/api/view` returns a 302 to a signed URL; the scripts
  follow it and strip `X-API-Key` before fetching from the storage backend
  (don't leak the API key to S3/CloudFront).
- **Endpoint differences from local ComfyUI:**
  - `/api/object_info`, `/api/queue`, `/api/userdata` — **403 on free tier**;
    paid only.
  - `/history` is renamed to `/history_v2` on cloud (the scripts route
    automatically).
  - `/models/<folder>` is renamed to `/experiment/models/<folder>` on cloud
    (the scripts route automatically).
  - `clientId` in WebSocket is currently ignored — all connections for a
    user receive the same broadcast. Filter by `prompt_id` client-side.
  - `subfolder` is accepted on uploads but ignored — cloud has a flat namespace.
- **Concurrent jobs:** Free/Standard: 1, Creator: 3, Pro: 5. Extras queue
  automatically. Use `run_batch.py --parallel N` to saturate your tier.

## Queue & System Management

```bash
# Local
curl -s http://127.0.0.1:8188/queue | python3 -m json.tool
curl -X POST http://127.0.0.1:8188/queue -d '{"clear": true}'    # cancel pending
curl -X POST http://127.0.0.1:8188/interrupt                      # cancel running
curl -X POST http://127.0.0.1:8188/free \
  -H "Content-Type: application/json" \
  -d '{"unload_models": true, "free_memory": true}'

# Cloud — same paths under /api/, plus:
python3 scripts/fetch_logs.py --tail-queue --host https://cloud.comfy.org
```

## Pitfalls

- **PuLID-Flux**: see [references/pulid-flux-pitfalls.md](references/pulid-flux-pitfalls.md) for critical setup issues (missing w600k_r50.onnx, forward_orig signature fix for ComfyUI v0.20.1, CPU-only onnxruntime, node parameter quirks)

1. **API format required** — every script and the `/api/prompt` endpoint expect
   API-format workflow JSON. The scripts detect editor format (top-level
   `nodes` and `links` arrays) and tell you to re-export via
   "Workflow → Export (API)" (newer UI) or "Save (API Format)" (older UI).

2. **Server must be running** — all execution requires a live server.
   `comfy launch --background` starts one. Verify with
   `curl http://127.0.0.1:8188/system_stats`.

3. **Model names are exact** — case-sensitive, includes file extension.
   `check_deps.py` does fuzzy matching (with/without extension and folder
   prefix), but the workflow itself must use the canonical name. Use
   `comfy model list` to discover what's installed.

4. **Missing custom nodes** — When the ComfyUI web UI shows "This workflow
   uses custom nodes you haven't installed", three approaches exist:
   - **comfy-cli:** `comfy node install <package_name>` (best for registered nodes)
   - **git clone:** `cd custom_nodes && git clone <repo_url>` then install
     its `requirements.txt` — necessary for unregistered or niche nodes
   - **Auto-fix script:** `auto_fix_deps.py` (best for API-format workflows)
   
   Common custom node repos needed by popular workflows:
   | Package | Repo | Nodes it provides |
   |---------|------|-------------------|
   | ComfyUI-Easy-Use | `yolain/ComfyUI-Easy-Use` | `easy clearCacheAll`, `easy cleanGpuUsed`, plus many QoL workflow nodes |
   | ComfyUI-SeedVR2 | already listed in academia-sd-nodes | SeedVR2 upscaler nodes |
   | rgthree-comfy | `rgthree/rgthree-comfy` | `Image Comparer`, Seed control, display nodes |
   
   After `git clone`, always install requirements:
   ```bash
   cd ~/comfy/ComfyUI && source .venv/bin/activate
   pip install -r custom_nodes/<PackageName>/requirements.txt
   ```
   Then **restart ComfyUI** — custom nodes only register on startup.

5. **Working directory** — `comfy-cli` auto-detects the ComfyUI workspace.
   If commands fail with "no workspace found", use
   `comfy --workspace /path/to/ComfyUI <command>` or
   `comfy set-default /path/to/ComfyUI`.

6. **Cloud free-tier API limits** — `/api/prompt`, `/api/view`, `/api/upload/*`,
   `/api/object_info` all return 403 on free accounts. `health_check.py` and
   `check_deps.py` handle this gracefully and surface a clear message.

7. **Timeout for video/audio workflows** — auto-detected when an output node
   is `VHS_VideoCombine`, `SaveVideo`, etc.; the default jumps from 300 s to
   900 s. Override explicitly with `--timeout 1800`.

8. **Path traversal in output filenames** — server-supplied filenames are
   passed through `safe_path_join` to refuse anything escaping `--output-dir`.
   Keep this protection on — workflows with custom save nodes can produce
   arbitrary paths.

9. **Workflow JSON is arbitrary code** — custom nodes run Python, so
   submitting an unknown workflow has the same trust profile as `eval`.
   Inspect workflows from untrusted sources before running.

10. **Auto-randomized seed** — pass `seed: -1` in `--args` (or use
    `--randomize-seed` and omit the seed) to get a fresh seed per run.
    The actual seed is logged to stderr.

11. **`tracking` prompt** — first run of `comfy` may prompt for analytics.
    Use `comfy --skip-prompt tracking disable` to skip non-interactively.
    `comfyui_setup.sh` does this for you.

12. **WSL venv location** — `comfy install --nvidia` creates the virtual
    environment at `~/comfy/ComfyUI/.venv/` (dot-venv, NOT `venv/`). If you
    need to manually install missing packages, use:
    ```bash
    ~/comfy/ComfyUI/.venv/bin/pip install <package>
    ~/comfy/ComfyUI/.venv/bin/python -c "import torch; print(torch.cuda.is_available())"
    ```
    Do NOT assume `python3` in PATH picks up the venv — always use the
    `.venv/bin/python` path explicitly.

    **Multi-user WSL caveat:** `~` expands to the SHELL user's home, which
    may differ from the ComfyUI owner. For example, if ComfyUI is at
    `/home/brierainz/comfy/ComfyUI` but the agent shell user is `aizen`,
    `~/comfy/ComfyUI` would resolve to `/home/aizen/comfy/ComfyUI` — wrong.
    Always verify the real path (e.g. `find / -maxdepth 4 -name main.py
    -path '*ComfyUI*'`) or use the absolute path stored in memory.

13. **Missing dependencies after install** — The comfy-cli install may not
    pull in all runtime dependencies (especially `transformers`, `accelerate`,
    `safetensors`). If `main.py` crashes with `ModuleNotFoundError`, install
    them into the venv:
    ```bash
    ~/comfy/ComfyUI/.venv/bin/pip install transformers accelerate safetensors
    ```
    Then re-check with: `~/comfy/ComfyUI/.venv/bin/python -c "import transformers; print('OK')"`

14. **Large model downloads** — `comfy model download` can silently stall on
    very large files (>4 GB). For reliability, prefer `huggingface-cli download`
    (or `hf download`) pointing directly at the `models/checkpoints/` directory:
    ```bash
    cd ~/comfy/ComfyUI/models/checkpoints
    hf download stabilityai/stable-diffusion-xl-base-1.0 sd_xl_base_1.0.safetensors --local-dir .
    ```
    The Juggernaut XL model repo on HuggingFace is `RunDiffusion/Juggernaut-XL-v9`.
    For CivitAI models, use `curl` with the download URL and an API token.
    Always verify with `ls -lh ~/comfy/ComfyUI/models/checkpoints/` after download.

15. **Moving model files into ComfyUI from Windows** — When copying model
    files from Windows (`/mnt/c/Users/...`) to ComfyUI directories, always
    use `cp` (not `mv`) because cross-filesystem moves are slow/fragile, and
    always verify with `ls -lh` afterward. Map file types to the correct
    `models/` subdirectory using `references/model-directory-map.md`. Common
    misplacements: putting a diffusion model in `checkpoints/` instead of
    `diffusion_models/`, or a text encoder in `checkpoints/` instead of
    `text_encoders/`. ComfyUI nodes like `CheckpointLoaderSimple` only scan
    `checkpoints/`; nodes like `UNETLoader` scan `diffusion_models/` — a
    model in the wrong directory is invisible.

16. **Juggernaut XL downloads as diffusers, not safetensors** — The
    `RunDiffusion/Juggernaut-XL-v9` repo on HuggingFace stores the model as
    separate diffusers files (unet/, text_encoder/, scheduler/, etc.), NOT as a
    single `.safetensors` checkpoint. ComfyUI can load diffusers-format models
    from `models/checkpoints/` as a directory, but for a single-file
    checkpoint you need to find a safetensors conversion on CivitAI or convert
    it yourself. If downloading via `hf download`, pull the whole repo:
    ```bash
    cd ~/comfy/ComfyUI/models/checkpoints
    hf download RunDiffusion/Juggernaut-XL-v9 --local-dir Juggernaut-XL_v9
    ```
    Then reference the directory name in workflows as the checkpoint name.

16. **PyTorch cu126 breaks on WSL** — Installing `torch` with CUDA 12.6 via
    `pip install torch --index-url https://download.pytorch.org/whl/cu126` fails
    on WSL because the `nvidia-nvshmem-cu12` dependency times out during
    download. **Use cu124 instead** which is stable on WSL:
    ```bash
    uv pip install torch==2.6.0 torchvision==0.21.0 --index-url https://download.pytorch.org/whl/cu124
    ```
    This applies to any venv (ComfyUI's `.venv`, Kohya's venv, etc.).

17. **Output filenames with spaces** — ComfyUI's output filenames can contain
    spaces (e.g., from prompt text). This breaks downstream scripts that use
    `for f in *.png` without quoting. Always quote filenames or use
    `find -print0 | xargs -0` for robustness. Alternatively, set
    `filename_prefix` in the SaveImage node to a slug with no spaces.

15. **Launching on WSL** — When running on WSL2 with NVIDIA passthrough, launch
    with:
    ```bash
    cd ~/comfy/ComfyUI && ~/comfy/ComfyUI/.venv/bin/python main.py --listen 0.0.0.0 --port 8188
    ```
    The Windows host can access `http://localhost:8188` automatically.
    Verify with: `curl -s http://127.0.0.1:8188/system_stats | python3 -m json.tool`

18. **WSL system-Python startup missing packages** — If ComfyUI was installed
    without `comfy-cli` (e.g., cloned directly) and has no `.venv`, starting with
    `python3 main.py` will crash on missing dependencies. The following packages
    are NOT pulled in by `requirements.txt` but are required at runtime:
    `sqlalchemy`, `gitpython`, `toml`, `opencv-python-headless`. Install them:
    ```bash
    pip3 install --break-system-packages sqlalchemy gitpython toml opencv-python-headless
    ```
    If you see `ModuleNotFoundError` for any of these on startup, install them
    into whichever Python is running ComfyUI.

19. **SDXL + LoRA workflow via API** — To generate images with a LoRA, the API
    workflow JSON must include a `LoraLoader` node between the
    `CheckpointLoaderSimple` and the `KSampler`. A minimal working API-format
    workflow has this node chain:
    ```
    CheckpointLoaderSimple → LoraLoader → KSampler → VAEDecode → SaveImage
    ```
    The `LoraLoader` takes `model` and `clip` from the checkpoint, plus
    `lora_name` (exact filename from `models/loras/`) and `strength_model` /
    `strength_clip` (typically 0.6–0.8). See the `ai-influencer` skill's
    `templates/sdxl_lora_portrait_api.json` for a complete working example.

20. **KSampler input is `latent_image`, not `latents`** — The KSampler node's
    latent input is named `latent_image` (not `latents`). Using `latents` in
    your API workflow JSON causes a 400 error with no helpful message. Always
    verify input names via `GET /object_info/KSampler` before building
    workflows by hand.

21. **AnimateDiff Evolved custom nodes require restart** — After `git clone`
    of ComfyUI-AnimateDiff-Evolved into `custom_nodes/`, the new nodes will
    NOT appear until ComfyUI is fully restarted (just refreshing the browser
    is not enough). Kill the process and relaunch. Verify with:
    ```bash
    curl -s http://localhost:8188/object_info | python3 -c "
    import sys, json
    d = json.load(sys.stdin)
    ad = [k for k in d if 'ADE_' in k or 'AnimateDiff' in k]
    print(f'AnimateDiff nodes: {len(ad)}')
    "
    ```
    You should see 100+ nodes (144 as of 2026). If you only see 4 generic
    nodes (SaveAnimatedWEBP, SaveAnimatedPNG, etc.), restart is needed.

22. **transformers KeyError: 'flash_attn' breaks custom nodes** — If you
    see `KeyError: 'flash_attn'` (or `flash_attn_interface`) in ComfyUI startup
    logs, it means `transformers>=5.5` has a bug in
    `PACKAGE_DISTRIBUTION_MAPPING` where it does `dict[key]` instead of
    `dict.get(key, [])`. This silently crashes `import` of any custom node that
    depends on `transformers` (ComfyUI-SeedVR2, ComfyUI-ReActor, etc.), and the
    affected nodes show as "missing" in the UI even though they're installed.

    **Fix** — Patch the file in the venv:
    ```bash
    # Locate the file
    F=$(find /home/brierainz/comfy/ComfyUI/.venv -path \
      "transformers/utils/import_utils.py")

    # Replace all 3 occurrences of PACKAGE_DISTRIBUTION_MAPPING["flash_attn"]
    # and PACKAGE_DISTRIBUTION_MAPPING["flash_attn_interface"] with .get():
    sed -i 's/PACKAGE_DISTRIBUTION_MAPPING\["flash_attn"\]/PACKAGE_DISTRIBUTION_MAPPING.get("flash_attn", [])/g' "$F"
    sed -i 's/PACKAGE_DISTRIBUTION_MAPPING\["flash_attn_interface"\]/PACKAGE_DISTRIBUTION_MAPPING.get("flash_attn_interface", [])/g' "$F"
    ```

    Then restart ComfyUI. The upstream fix should land in a future `transformers`
    release; check `pip show transformers` — if ≥5.8 (or whichever release
    includes the fix), the patch is no longer needed and can be removed.

23. **AnimateDiff SDXL video generation** — AnimateDiff Evolved supports SDXL
    via the `ADE_AnimateDiffLoaderWithContext` node with
    `mm_sdxl_v10_beta.ckpt` motion module. The minimal workflow chain:
    ```
    CheckpointLoaderSimple → LoraLoader → ADE_AnimateDiffLoaderWithContext
    → KSampler → VAEDecode → SaveAnimatedWEBP
    ```
    Key parameters:
    - `EmptyLatentImage` with `batch_size=16` (16 frames at 512x512)
    - `fps=8` in SaveAnimatedWEBP (2-second clip at 8fps)
    - `beta_schedule: "autoselect"` in ADE_AnimateDiffLoaderWithContext
    - Motion module: `mm_sdxl_v10_beta.ckpt` (907MB) from HuggingFace
      `guoyww/animatediff`

    VRAM: 512x512 with LoRA+AnimateDiff+SDXL uses ~8-9GB VRAM per generation.
    On RTX 3060 12GB, this leaves ~3GB headroom. For larger resolutions or more
    frames, expect OOM. Lower `batch_size` (frames) or resolution to fit.

    **Portrait/vertical video for Reels/TikTok:** Use 512x768 (2:3) or
    448x768 for 9:16 content. With LoRA+AnimateDiff+SDXL at 512x768, VRAM
    peaks at ~10-11GB (safe on 12GB cards). Set `batch_size=24` and `fps=12`
    for 2-second clips at smoother frame rate, or reduce to `batch_size=16`
    for longer Generation time. Face consistency in AnimateDiff clips is
    typically 6-7/10 (inherent SDXL latent drift) — acceptable for social
    media but expect minor facial variation between frames. For higher
    consistency, consider FaceID or IPAdapter nodes (not yet tested).

23. **IPAdapter FaceID model compatibility** — There are TWO SDXL FaceID models with different CLIP Vision requirements:
    - `ip-adapter-faceid_sdxl.bin` (normal) — works with CLIP Vision ViT-H-14 (`ViT-H-14.s32B.b79K.safetensors`, 1280-dim). This is the safe default for most setups.
    - `ip-adapter-faceid-plusv2_sdxl.bin` (PlusV2) — requires CLIP Vision ViT-bigG-14 (`CLIP-ViT-bigG-14-laion2B-39B-b160k.safetensors`, 1664-dim), NOT ViT-H or ViT-L. If you use PlusV2 with ViT-H, you get: `size mismatch for perceiver_resampler.proj_in.weight: copying a param with shape torch.Size([2048, 1280]) from checkpoint, the shape in current model is torch.Size([2048, 1664])`. The PlusV2 perceiver resampler expects 1664-dim input. ViT-bigG is ~3.5GB and must be downloaded separately from `h94/IP-Adapter` on HuggingFace.
    
    **CLIP Vision model naming pitfall:** ComfyUI's IPAdapter uses regex patterns to find clip_vision models by name. `clip_vision_vit_h.safetensors` does NOT match the pattern `(ViT.H.14.*s32B.b79K|...)`. You must rename or symlink the file to match: `ln -s clip_vision_vit_h.safetensors ViT-H-14.s32B.b79K.safetensors`. Similarly, the FaceID LoRA file needs a symlink in `models/loras/`: `ln -s /path/to/models/ipadapter/ip-adapter-faceid_sdxl_lora.safetensors models/loras/faceid.sdxl.lora.safetensors`.
    
    **API workflow for FaceID — use `IPAdapterUnifiedLoaderFaceID`, NOT manual node chain:** The `IPAdapterModelLoader` + `CLIPVisionLoader` + `IPAdapterInsightFaceLoader` manual chain works in the ComfyUI web UI but has model-path resolution issues in API format. The `IPAdapterUnifiedLoaderFaceID` node handles all model loading automatically and works reliably in API mode. Correct API workflow:
    ```
    CheckpointLoaderSimple (ckpt_name: Juggernaut-XL_v9...)
    → IPAdapterUnifiedLoaderFaceID (preset: "FACEID", lora_strength: 0.6, provider: "CUDA")
    → LoadImage (reference face photo)
    → IPAdapterFaceID (image, weight: 0.8-0.9, weight_type: "linear", embeds_scaling: "K+V")
    → CLIPTextEncode (positive prompt)
    → CLIPTextEncode (negative prompt)
    → EmptyLatentImage (768x1024)
    → KSampler (steps: 30, cfg: 7.0, sampler: dpmpp_2m, scheduler: karras)
    → VAEDecode → SaveImage
    ```
    The unified loader returns `(MODEL, ipadapter)` where ipadapter is a pipeline dict containing model, clip_vision, and insightface. Pass both outputs directly to `IPAdapterFaceID` — do NOT pass clip_vision or insightface separately.
    
    InsightFace files go in `models/insightface/models/buffalo_l/`. CLIP Vision goes in `models/clip_vision/`. IPAdapter models go in `models/ipadapter/`.

24. **Custom node INSTALL FAILED — always check for empty clones** — Some GitHub repos listed on ComfyUI registry or search may be stale, renamed, or empty (README-only). After `git clone`, verify the directory contains `__init__.py` or actual Python source. If not, remove it and search GitHub directly for the correct repo. Common cases:
    - `ComfyUI-Simple-Math` → repo is empty (README-only). The `SimpleMath+` node comes from `ComfyUI_Comfyroll_CustomNodes` (already installed by default).
    - `ComfyUI-FL-Nodes` (`FL_IntToFloat`, `FL_Math`) → correct repo is `gitmylo/FlowNodes`, not the similarly-named `6174/comflowy-nodes` (which provides `Int Expression` and `Float Expression`, NOT `FL_Math`).
    After cloning custom nodes, always `ls <dir>/__init__.py` to confirm, then install dependencies and restart ComfyUI.

34. **Verifying workflow node dependencies systematically** — When loading a workflow that shows "missing nodes" in ComfyUI, use this procedure to find and resolve ALL missing nodes at once:
    1. **Collect all node types from workflow JSONs**: Parse every `.json` in `user/default/workflows/` and `workflows/`, extracting `node.type` (editor format) or `class_type` (API format).
    2. **Get registered nodes**: `curl -s http://127.0.0.1:8188/object_info | python3 -c "import sys,json; d=json.load(sys.stdin); print(len(d))"` — if the count is suspiciously low (e.g., <300), many custom nodes failed to import. Check the startup log for `IMPORT FAILED` messages.
    3. **Compute missing nodes**: Subtract registered nodes from workflow nodes. Exclude virtual/editor-only nodes (`PrimitiveNode`, `Reroute`, `SetNode`, `Fast Groups Bypasser (rgthree)`, `Label (rgthree)`, `MarkdownNote`) which only exist in the UI.
    4. **Find the source package** for each missing node by:
       - `grep -r "class NodeName" custom_nodes/*/nodes.py custom_nodes/*/__init__.py` — checks if a local package defines the class
       - Search the ComfyUI Manager registry: `curl -sL https://raw.githubusercontent.com/ltdrdata/ComfyUI-Manager/main/custom-node-list.json` — find title/repo mappings
       - GitHub code search for `"class NodeName"` in ComfyUI repos
       - Cross-reference with `curl -s https://api.comfy.org/nodes?search=NodeName`
    5. **Install the package** (`git clone` into `custom_nodes/` + `pip install -r requirements.txt` + restart) or **create a compatibility node** if no package exists.
    6. **Re-verify** after restart — total registered nodes should jump (e.g., from 269 → 2414+ when solving mass import failures).

35. **Node name collisions between SAM2 packages** — Multiple ComfyUI-SAM2 repos exist with DIFFERENT node class names. The two most common:
    - `neverbiasu/ComfyUI-SAM2` provides: `SAM2ModelLoader (segment anything2)`, `GroundingDinoModelLoader`, `GroundingDinoSAM2Segment` — uses `Sam2ModelLoader` Python class
    - `kijai/ComfyUI-segment-anything-2` provides: `DownloadAndLoadSAM2Model`, `Sam2Segmentation`, `Sam2AutoSegmentation`, `Sam2VideoSegmentation` — uses different API/format
    Both can coexist (different `NODE_CLASS_MAPPINGS` keys) but if a workflow references `DownloadAndLoadSAM2Model`, you MUST install `kijai/ComfyUI-segment-anything-2`. The `neverbiasu` package does NOT provide that node. Similarly, if a workflow uses FL_Math (not Int Expression / Float Expression), you need a compatibility node — the `gitmylo/FlowNodes` package does NOT provide `FL_Math`.

36. **Creating compatibility nodes for missing node types** — When no GitHub package provides a workflow node (e.g., `FL_Math`), create a minimal compatibility node in `custom_nodes/`:
    ```python
    # custom_nodes/ComfyUI-Compat-Nodes/fl_math.py
    class FL_Math:
        OPERATION_MODES = ["A+B", "A-B", "A*B", "A/B", "A^B", "A%B"]
        @classmethod
        def INPUT_TYPES(cls):
            return {"required": {
                "A": ("INT", {"default": 0, "min": -0xFFFFFFFF, "max": 0xFFFFFFFF}),
                "B": ("INT", {"default": 0, "min": -0xFFFFFFFF, "max": 0xFFFFFFFF}),
                "mode": (cls.OPERATION_MODES, {"default": "A*B"}),
            }}
        RETURN_TYPES = ("INT", "FLOAT")
        RETURN_NAMES = ("INT", "FLOAT")
        FUNCTION = "execute"
        CATEGORY = "math"
        def execute(self, A, B, mode="A*B"):
            ops = {"A+B": A+B, "A-B": A-B, "A*B": A*B, "A/B": A/B if B else 0, "A^B": A**B, "A%B": A%B if B else 0}
            result = ops.get(mode, A*B)
            return (int(result), float(result))
    ```
    Then register in `__init__.py`:
    ```python
    from .fl_math import FL_Math
    NODE_CLASS_MAPPINGS = {"FL_Math": FL_Math}
    NODE_DISPLAY_NAME_MAPPINGS = {"FL_Math": "FL Math (Compat)"}
    ```
    Match the workflow's `widgets_values` format (e.g., `[0, 0, 0, "A*B"]` means the `mode` widget uses string expressions, not an index).

24. **Custom node missing Python packages — check startup logs** — When ComfyUI shows `IMPORT FAILED` for a custom node, check the startup log for the specific `ModuleNotFoundError`. Common missing packages:
    - `ComfyUI-SAM2` needs `addict` and `yapf` → `pip install addict yapf`
    - `transformers>=5.5` KeyError for `flash_attn` → see pitfall #22
    - **ComfyUI-WanVideoWrapper** needs a long dependency chain: `accelerate>=1.2.1`, `ftfy`, `gguf>=0.17.1`, `einops`, `diffusers>=0.33.0`, `peft>=0.17.0`, `sentencepiece>=0.2.0`, `protobuf`, `pyloudnorm`, `scipy`, `opencv-python`. Without ALL of these, the entire custom node fails to load (117 WanVideo nodes silently disappear). Check `user/comfyui_8188.log` for the chain — each restart reveals the NEXT missing package. Install all at once:
      ```bash
      pip3 install --break-system-packages ftfy accelerate einops diffusers peft sentencepiece protobuf pyloudnorm opencv-python scipy gguf
      ```
      The ComfyUI log shows sequential failures: first `accelerate`, then `ftfy`, then `gguf`, etc. — each `ModuleNotFoundError` blocks the entire custom node from loading.
    After installing missing packages, restart ComfyUI (nodes only register on startup).

25. **LoRA Management — ComfyUI-Lora-Manager + LokArni** — Two complementary tools for organizing LoRAs locally:
    - **ComfyUI-Lora-Manager** (`custom_nodes/ComfyUI-Lora-Manager`): In-ComfyUI catalog with previews, trigger words, CivitAI download, drag-and-drop to canvas. Install: `git clone https://github.com/willmiao/ComfyUI-Lora-Manager.git` into `custom_nodes/`, then `pip install -r requirements.txt`. Access at `http://localhost:8188/loras` when ComfyUI is running. Auto-detects `models/loras/` folder.
    - **LokArni** (`/home/brierainz/comfy/lokarni`): Standalone webapp (React+FastAPI+SQLite) for asset cataloging with categories, CivitAI import, favorites, masonry views, and **Prompt Studio** (preset-based prompt builder with fragment buttons, model selectors with asset catalog integration, copy-to-clipboard). Runs on port 8000. See `references/lokarni-asset-manager.md` for full API, pitfalls, and customization guide.
    
    **When user wants "CelebMakerAI but local"** — LokArni + ComfyUI together approximate the experience. Use LokArni's Prompt Studio to build configs, then paste into ComfyUI.

25. **AcademiaSD custom nodes** — The `comfyui_AcademiaSD` plugin provides 16+ nodes for video workflows. It requires several companion custom nodes (WanVideoWrapper, HunyuanVideoWrapper, LTXVideo, SeedVR2, GGUF, ReActor, Impact-Pack, IPAdapter+, ControlNet aux, AnimateDiff, VideoHelperSuite, Crystools, Comfyroll, rgthree, Easy-Use, KJNodes). The `AcademiaSD_Downloader` node can auto-download missing models. Full install:
    ```bash
    cd ~/comfy/ComfyUI/custom_nodes
    git clone https://github.com/AcademiaSD/comfyui_AcademiaSD.git
    # Install all companion nodes (see references/academia-sd-nodes.md for full list)
    pip install google-generativeai matplotlib  # AcademiaSD-specific deps
    ```

27. **Sequential API generation — always wait for queue-empty** — When submitting prompts one-at-a-time via the REST API (e.g., for a FaceID generation loop), you MUST check that the queue is empty before submitting the next prompt. If you submit while a previous job is still running, the new job queues behind it but the script's timeout clock keeps ticking, causing every job after the first to time out. The correct pattern:
    ```python
    def wait_for_queue_empty(base_url, timeout=120):
        start = time.time()
        while time.time() - start < timeout:
            resp = requests.get(f"{base_url}/queue")
            data = resp.json()
            running = len(data.get("queue_running", []))
            pending = len(data.get("queue_pending", []))
            if running == 0 and pending == 0:
                return True
            time.sleep(5)
        return False
    ```
    Also note: SDXL + IPAdapter FaceID on RTX 3060 takes ~63 seconds per image with queue drain (NOT 7-8 minutes — earlier measurements were inflated by queue backlog from submitting multiple prompts without waiting). Set a generous timeout (480s+) as safety margin, or better yet, poll indefinitely with no hard timeout — just print progress every 15-30s. The pattern in `regenerate_ehyra_v3.py` (ai-toolkit) implements infinite polling with `wait_for_queue_empty()` between submissions.

    **LoRA training dataset generation pattern:** When generating a dataset for face LoRA training, use Juggernaut XL v9 (photorealistic) + IPAdapter FaceID, NOT Pony V6 XL (which produces cartoonish/anime-style results that contaminate the dataset). Each reference photo should generate 3-5 variations with different prompts (closeup, casual, studio, environmental, fashion), weight 0.80-0.90, LoRA strength 0.50-0.70. For captioning the generated dataset, use Qwen3-VL via ai-toolkit's `caption_dataset.yaml`.

28. **BrokenPipeError from pip logging causes HTTP 500 on /prompt** — If ComfyUI's `POST /prompt` returns a bare `500 Internal Server Error` with no JSON details, check the ComfyUI log at `~/comfy/ComfyUI/user/comfyui_8188.log`. The most common cause is `pip._internal.utils.logging.BrokenStdoutLoggingError` — pip's rich console handler crashes when stdout is a pipe (which it is when ComfyUI runs via `nohup`, systemd, or `&`). This breaks ALL prompt submissions even though `GET /system_stats`, `GET /queue`, and `GET /object_info` work fine.

    **Diagnosis** — Look for this traceback in the log:
    ```
    pip._internal.utils.logging.BrokenStdoutLoggingError
      → self.on_broken_pipe() → self._check_buffer() → raise
    ```
    It happens inside `aiohttp/web_protocol.py` during `post_prompt` at the `logging.info("got prompt")` line — so the prompt never actually enters the queue.

    **Fix options** (pick one):
    1. **Redirect stdout+stderr to /dev/null**: Restart ComfyUI with `python main.py ... >/dev/null 2>&1` — prevents pip from detecting a broken pipe.
    2. **Restart in a proper terminal**: Run ComfyUI in a real terminal (not backgrounded) where stdout is a TTY.
    3. **Patch pip logging** (nuclear): Rename or disable the pip logging handler:
       ```bash
       F=$(python3 -c "import pip._internal.utils.logging; print(pip._internal.utils.logging.__file__)")
       # Comment out the BrokenStdoutLoggingError raise
       sed -i 's/raise BrokenStdoutLoggingError/# raise BrokenStdoutLoggingError/' "$F"
       ```
    4. **Patch ComfyUI's LogInterceptor** (surgical, recommended for proxy API setups): Patch `app/logger.py` in the ComfyUI directory to catch `BrokenPipeError` in the `write()` and `flush()` methods, and patch `server.py` to wrap `logging.info("got prompt")` in `try/except`. This keeps stdout logging functional while preventing pipe errors from killing requests:
       ```python
       # In app/logger.py, LogInterceptor.write() — add BrokenPipeError handling:
       def write(self, data):
           entry = {"t": datetime.now().isoformat(), "m": data}
           with self._lock:
               self._logs_since_flush.append(entry)
           try:
               for stream in self._original_streams:
                   stream.write(data)
           except (BrokenPipeError, OSError):
               pass  # pip's rich logging crashes on pipe writes

       # In app/logger.py, flush callbacks — catch errors:
       for cb in self._flush_callbacks:
           try:
               cb(self._logs_since_flush)
           except (BrokenPipeError, OSError):
               pass
           self._logs_since_flush = []

       # In server.py, wrap the trigger line:
       @routes.post("/prompt")
       async def post_prompt(request):
           try:
               logging.info("got prompt")
           except Exception:
               pass  # Suppress BrokenPipeError from pip's rich logging
       ```
    5. **Use the run_workflow.py script** which uses httpx directly and handles errors gracefully — but it won't help if the server itself crashes during logging.

    The root cause is that pip's `RichHandler` tries to write to stdout, detects a broken pipe, and raises an exception that propagates into aiohttp's request handler. This is NOT a workflow JSON error — any valid workflow will 500 until the logging is fixed.

29. **WebSocket progress requires same client_id as prompt submission** — ComfyUI's WebSocket (`/ws?clientId=X`) only sends progress events to the `clientId` that submitted the prompt. If you open a WebSocket with a random UUID but submitted the prompt via REST with a different `client_id`, ComfyUI silently drops all progress events — the generation completes but you never receive `execution_start`, `progress`, or `executing` messages. This is the #1 cause of "generation appears stuck at queued" bugs. **Rule**: the `clientId` query parameter on the WebSocket connection MUST match the `client_id` field in the POST `/prompt` payload. If using a singleton ComfyUI client class, store its `client_id` and reuse it for both submission and WebSocket listening.

30. **WanVideo models in diffusers format need `net.` prefix stripping** — Models from HF as `diffusion_pytorch_model.safetensors` have `net.` prefix. WanVideoModelLoader only strips `model.diffusion_model.` and `model.`. **Fix:** patched `nodes_model_loading.py` to add `elif first_key.startswith("net."): sd = {key.replace("net.", "", 1): value for key, value in sd.items()}`. Base model `diffusion_pytorch_model.safetensors` (Wan2.1-T2V-1.3B native) works without this patch. `anima-preview3-base.safetensors` CANNOT be standalone — it uses `net.x_embedder` instead of `patch_embedding` and needs conversion or LoRA loading.
48. **Juggernaut XL v9 produces facial inconsistency for AI influencer characters** — Juggernaut XL v9 generates artistic, painterly images that lack face consistency — the same LoRA + same character prompt produces noticeably different facial features across images. For AI influencer use cases where consistent identity is paramount, prefer SD1.5 + ChilloutMix (community gold standard for Asian face consistency), RealVisXL V4.0 (better face retention), or the original training platform's base model (e.g., PixAI's PhotoPedia XL for Ehyra). Juggernaut XL is suitable for one-off artistic pieces but NOT for batch generation where the character must look like the same person across all images.

52. **SD1.5 + ChilloutMix for consistent Asian faces** — The Reddit/StableDiffusion community consensus is that SD1.5 + ChilloutMix (or BRA, removed from CivitAI) produces far more consistent Asian faces than any SDXL model. ChilloutMix NiPrunedFp16Fix (CivitAI model ID 6424, version download `/api/download/models/11732`) is the recommended download — ~2GB, 1.1M+ downloads. Key technical differences from SDXL workflows:
    - **Native resolution**: 512×768 (portrait) — NOT 768×1344 or 1024×1536
    - **Required VAE**: `vae-ft-mse-840000.safetensors` (SD1.5 VAE, NOT sdxl_vae). Download from HuggingFace `stabilityai/sd-vae-ft-mse-original` — note the `ema-pruned` variant URL, regular URL may redirect to HTML. Place in `models/vae/`
    - **KSampler**: Use `dpmpp_2m` scheduler `karras` with 25-30 steps, CFG 7-8 (standard SD1.5 settings)
    - **LoRA compatibility**: SDXL-trained LoRAs can be used on SD1.5 checkpoints but MUST have reduced weights (typically 0.5-0.6 instead of 0.7-0.8) to avoid artifacts. For optimal results, train a dedicated SD1.5 LoRA on ChilloutMix base
    - **Multi-LoRA stacking**: Face LoRA (weight 0.6) + Body LoRA (weight 0.5) on ChilloutMix base produces better face consistency than any single-SDXL-model approach tested

53. **SD1.5 VAE is NOT interchangeable with SDXL VAE** — Using `sdxl_vae.safetensors` (SDXL's VAE) with an SD1.5 model like ChilloutMix produces washed-out colors, incorrect contrast, and sometimes broken images. Always use `vae-ft-mse-840000.safetensors` (or equivalent SD1.5 VAE) with SD1.5 checkpoints. In ComfyUI workflows, add a dedicated `VAELoader` node pointing to the correct VAE file — do NOT rely on the checkpoint's baked-in VAE.

49. **LoRA filenames must match ComfyUI model list exactly** — When a LoRA file is renamed externally (e.g., `checkpoint-e36_s684.safetensors` → `ehyra_xl_lora.safetensors`), all workflow JSON files and generation scripts must reference the NEW filename. ComfyUI's LoraLoader node uses the exact filename from `models/loras/`. To discover current LoRA names: `curl -s http://127.0.0.1:8188/object_info/LoraLoader | python3 -c "import sys,json; d=json.load(sys.stdin); print([x[1] for x in d['LoraLoader']['input']['required']['lora_name'][0]])"`. Always verify after renaming or downloading a new LoRA.

50. **CivitAI REST API is read-only for models** — The CivitAI REST API (`https://civitai.com/api/v1/models`) only supports GET requests for browsing and downloading. Creating models, uploading LoRA files, and publishing requires the web UI at `https://civitai.com/model/create`. There is no programmatic upload endpoint. The API token is used for downloading gated models and authenticating requests, NOT for creating model pages.

51. **Aspect ratio is critical for full-body generation** — SDXL models (Juggernaut, RealVisXL, Pony V6) ALL crop at mid-thigh or waist when using tall/narrow aspect ratios (768x1344, 1024x1536, etc.), regardless of prompt content. This is a fundamental SDXL composition bias. The ONLY tested aspect ratio that produces consistent full-body (head-to-toe) compositions is WIDE/landscape (1344x768). Square (1024x1024) also crops to mid-thigh. For body/full-body LoRA dataset generation:
    - **CORRECT**: 1344×768 (wide/landscape) — 8-10/10 full body
    - **WRONG**: 768×1344 (tall/portrait) — crops mid-thigh
    - **WRONG**: 1024×1024 (square) — crops mid-thigh
    - **WRONG**: 1024×1536 (extra-tall) — still crops mid-thigh
    
    This applies even with aggressive "full body" prompts including "standing, full body visible, head to toe, whole figure". The SDXL latent space has a strong portrait-bias prior that only wide ratios can override.

49. **BBW/voluptuous tags mandatory for curvy body in Pony V6** — Pony V6 XL (and most SDXL checkpoints) have an inherent slim/fit body bias. Without explicit body-type tags, even prompts like "curves, generous figure, hourglass" produce slim or average builds. The minimum effective tag set for voluptuous/BBW body generation is: `bbw, thick, very wide hips, thick thighs`. These must appear early in the positive prompt (before clothing and setting descriptions). WITHOUT these tags, Pony V6 at 1344x768 generates full-body but slim images (voluptuous: 1/10). WITH these tags, voluptuous scores 8-9/10. This was validated across multiple seeds and prompt variations.

38. **Qwen3-VL processor has no `batch_text_decoder` method** — When captioning images with Qwen3-VL-4B-Instruct, the correct decoding method is `processor.batch_decode(generated_ids, skip_special_tokens=True, clean_up_tokenization_spaces=False)`. The method `processor.batch_text_decoder()` does NOT exist on `Qwen3VLProcessor` — it will raise `AttributeError`. This differs from the Qwen2.5-VL processor which may have had `batch_text_decoder`. Always use `batch_decode`. Additionally, the image content dict should use `{"type": "image", "image": image_path}` (plain path string), NOT `{"type": "image", "image": f"file://{image_path}"}` — the processor handles path resolution internally.

39. **ComfyUI + Qwen3-VL-4B VRAM conflict on 12GB GPU** — Both need ~8-9GB VRAM. Running them simultaneously causes CUDA OOM. When using Qwen3-VL for dataset captioning, stop ComfyUI first (`pkill -f 'python.*main.py.*8188'`), then run captioning, then restart ComfyUI for generation. This applies to any two VRAM-heavy processes on a 12GB card.

40. **Output filenames with underscored ref names confuse category parsing** — When generating images with IPAdapter FaceID where reference filenames contain underscores (e.g., `20250427_071835.jpg`), output filenames like `ehyra_v2_body_20250427_071835_casual_body_621781.png` have ambiguous underscore boundaries. To extract the category, parse from the END using longest-match-first: check for `environmental_body`, then `fashion_body`, then `casual_body`, then `fullbody`. Splitting from the front by underscores will produce wrong results when the ref name itself contains underscores.

41. **IPAdapter FaceID dominates composition — cannot produce full-body images** — IPAdapter FaceID (both plain and PlusV2) forces portrait/face-focused composition regardless of weight, CFG, prompt strength, or resolution. Tested extensively:
    - Weight 0.80: face-focused portrait crop
    - Weight 0.65: three-quarter crop, still face-dominated
    - Weight 0.35: mid-thighs crop, slim body type
    - Weight 0.30 with `end_at=0.40` and `weight_type="composition"`: still three-quarter, slim
    - Resolution 1024x1536 (tall): still crops at mid-thighs
    
    **Root cause**: IPAdapter FaceID injects face identity into the generation process, which biases the model toward face-centric compositions. Lowering weight only reduces face fidelity — it does NOT shift composition toward full-body. The model compensates for weaker face signal by generating a generic slim body.
    
    **Solution — two-phase approach for full-body generation**:
    - **Phase 1**: Generate full-body images WITHOUT IPAdapter (pure prompt-driven, using a checkpoint known for body diversity like RealVisXL V4 or CyberRealistic V4). Juggernaut XL v9 has an inherent slim portrait bias even without IPAdapter — avoid it for body generation.
    - **Phase 2**: Face swap with ReActor (`ReActorFastFaceSwap` or `ReActorFaceSwap` node) to transfer the target face onto the generated body images.
    
    This produces much better full-body results than any IPAdapter FaceID configuration tested.

42. **Juggernaut XL v9 has inherent slim portrait bias** — Even without IPAdapter, Juggernaut XL v9 generates mid-thigh-cropped slim portraits regardless of prompt content. Tested with aggressive full-body prompts + voluptuous descriptors at 1024x1536 resolution — still produces face-focused slim women. Do NOT use Juggernaut XL for body/full-body dataset generation where body diversity matters. It works well for portrait/face generation.

43. **Pony V6 XL generates full body with BBW tags, BUT semi-illustrated style** — Pony V6 XL produces 10/10 full-body compositions, but ONLY at WIDE aspect ratio (1344x768). At tall/narrow ratios (768x1344, 1024x1536), it still crops at mid-thighs like other SDXL models. Without BBW tags, Pony generates slim anime bodies. WITH "bbw, thick, very wide hips, thick thighs" in the prompt + wide ratio, it generates voluptuous/curvy bodies at 8-9/10 body composition quality. HOWEVER, the output style is **semi-illustrated/semi-realistic** (realism ~5-6/10), NOT photorealistic — even with quality tags `score_9, score_8_up, source_photo, source_5_more`. Pony V6's aesthetic inherently lean toward anime/digital-painting. For **photorealistic** body generation, use **Flux.1-dev GGUF Q8** instead (see pitfall #50). IPAdapter FaceID on Pony produces wrong faces (anime characters rather than the reference face). Use the two-phase approach: Pony V6 + BBW tags for body (Phase 1), then ReActor face swap (Phase 2).

44. **RealVisXL V4.0 tested — FAILED for full-body voluptuous generation** — RealVisXL V4.0 produces the same portrait/slim bias as Juggernaut XL despite being marketed for photorealism. Tested results: full_body 2/10, voluptuous 2/10. Crops at mid-thigh even with aggressive full-body prompts at 768x1344. NOT recommended for body/full-body generation — only Pony V6 with BBW tags produces consistent full-body voluptuous results.

50. **Flux.1-dev GGUF Q8 for photorealistic body generation on RTX 3060 12GB** — Flux.1-dev produces truly photorealistic images (unlike Pony V6). It can run on RTX 3060 12GB using the GGUF Q8 quantization format via the ComfyUI-GGUF custom node. Setup requires 4 model files:
    - **UNet (GGUF Q8):** `models/unet/flux1-dev-Q8_0.gguf` (~12GB) — from `https://huggingface.co/city96/FLUX.1-dev-GGUF/resolve/main/flux1-dev-Q8_0.gguf`
    - **CLIP-L text encoder:** `models/text_encoders/clip_l.safetensors` (~235MB) — from `https://huggingface.co/comfyanonymous/flux_text_encoders/resolve/main/clip_l.safetensors`
    - **T5-XXL text encoder (FP8):** `models/text_encoders/t5xxl_fp8_e4m3fn.safetensors` (~4.8GB) — from `https://huggingface.co/comfyanonymous/flux_text_encoders/resolve/main/t5xxl_fp8_e4m3fn.safetensors`
    - **VAE:** `models/vae/ae.safetensors` (~320MB) — from `https://huggingface.co/black-forest-labs/FLUX.1-dev/resolve/main/ae.safetensors`

    **Flux GGUF workflow node chain (DIFFERENT from SDXL, DIFFERENT from Flux schnell checkpoint):**
    ```
    GGUFLoaderKJ(model_name="flux1-dev-Q8_0.gguf", extra_model_name="none", dequant_dtype="default",
                 patch_dtype="default", patch_on_device=false, enable_fp16_accumulation=false,
                 attention_override="none")
    → DualCLIPLoader(clip_name1="t5xxl_fp8_e4m3fn.safetensors", clip_name2="clip_l.safetensors", type="flux")
    → VAELoader(vae_name="ae.safetensors")          ← separate VAE node, NOT from checkpoint
    → ModelSamplingFlux(model=GGUFLoaderKJ.0, max_shift=1.15, base_shift=0.5, width=W, height=H)
    → CLIPTextEncode(text=prompt, clip=DualCLIPLoader.0)  ← positive prompt
    → CLIPTextEncode(text="", clip=DualCLIPLoader.0)      ← EMPTY negative (Flux ignores it)
    → FluxGuidance(guidance=3.5, conditioning=positive.0)  ← dev only; schnell uses guidance=1.0
    → EmptyLatentImage(width=W, height=H, batch_size=1)
    → KSampler(steps=20, cfg=1.0, sampler="euler", scheduler="simple", denoise=1.0,
                model=ModelSamplingFlux.0, positive=FluxGuidance.0, negative=empty_text.0,
                latent_image=EmptyLatentImage.0)
    → VAEDecode(samples=KSampler.0, vae=VAELoader.0)
    → SaveImage
    ```

    **CRITICAL: Node name is `GGUFLoaderKJ`, NOT `UnetLoaderGGUF` or `UNETLoaderGGUF`.**
    The node was renamed in ComfyUI-GGUF package — `UnetLoaderGGUF` does NOT exist and
    returns HTTP 400. Verify available nodes with:
    ```bash
    curl -s http://127.0.0.1:8188/object_info | python3 -c "import sys,json; d=json.load(sys.stdin); [print(k) for k in d if 'GGUF' in k.upper()]"
    ```

    Key differences from SDXL workflows:
- `GGUFLoaderKJ` (NOT `CheckpointLoaderSimple`, NOT `UnetLoader`, NOT `UnetLoaderGGUF`) — loads GGUF quantized models from `models/unet/`
    - `DualCLIPLoader` — loads BOTH CLIP-L AND T5-XXL in one node, MUST set `type="flux"` parameter
    - `FluxGuidance` (NOT `CLIPTextEncode` for guidance) — wraps CLIP encoded conditioning with a guidance scale. Flux dev uses guidance=3.5, schnell uses guidance=1.0
    - `ModelSamplingFlux` — required node that Flux models need for proper sampling. Width/height must match latent image
    - `VAELoader` — Flux uses a separate VAE (`ae.safetensors`), NOT the one baked into checkpoints
    - **Negative prompt MUST be a separate empty CLIPTextEncode node** — do NOT reuse the positive conditioning node. Flux doesn't use negative conditioning, but ComfyUI requires a valid conditioning connection. CRITICAL: in API-format workflow JSON, the `KSampler` `negative` field must be a **linked node reference** like `["16", 0]`, NOT an empty array `[]`. Passing `negative: []` causes a validation error or silent failure. Always create a dedicated CLIPTextEncode node (e.g., node "16") with `text: ""` and link KSampler's `negative` to it
    - **KSampler settings:** steps=20 (dev) or 4 (schnell), cfg=1.0, sampler=euler, scheduler=simple. DO NOT use cfg>1.0 for Flux

    **Flux.1-schnell requires HuggingFace auth (401 Unauthorized)** — The official `FLUX.1-schnell` checkpoint at `black-forest-labs/FLUX.1-schnell` requires accepting a license on HuggingFace before downloading. Direct `wget`/`curl` downloads return 401. Use `huggingface-cli download` after `huggingface-cli login` with a token from https://huggingface.co/settings/tokens. The GGUF Q8 version of Flux.1-dev from `city96/FLUX.1-dev-GGUF` does NOT require auth and runs on 12GB VRAM.

    **Performance on RTX 3060 12GB:** ~3-4 min per 1536×640 image with 20 steps. ~11610 MiB VRAM at generation time. The GGUF Q8 format significantly reduces VRAM usage vs full FP16 (~24GB). Must use ComfyUI-GGUF custom node (`git clone https://github.com/city96/ComfyUI-GGUF` into `custom_nodes/`).

    **Validated resolution for full-body generation — 1536×640 (ultra-wide):** This is the ONLY tested resolution that produces consistent head-to-toe full body with Flux GGUF. Comparison data (same prompts, same character):

    | Metric | Pony V6 XL (1344×768) | Flux.1-dev GGUF Q8 (1536×640) |
    |--------|----------------------|-------------------------------|
    | Full body | 8/10 | **10/10** |
    | Body type accuracy | BBW/fat (not curvy slim) | **10/10 curvy slim hourglass** |
    | Photorealism | 4/10 (semi-illustrated) | **10/10** |

    Key findings:
    - 1536×640 consistently produces full-body images from head to feet, even without aggressive "full body" prompting
    - Flux understands "curvy slim hourglass" correctly (wide hips + full bust + narrow waist + fit), unlike Pony which interprets "curvy" as BBW regardless of prompt
    - Pony V6 body type tags (bbw, thick, very wide hips) are MANDATORY for any curves but produce plus-size bodies, not curvy slim
    - For photorealistic body dataset generation, Flux GGUF Q8 at 1536×640 is the best option on RTX 3060 12GB

    **Pitfall:** Downloading these large files (>4GB) with `wget`/`curl` may silently create 0-byte files (wget returns 0 exit code). Use `huggingface-cli download` or `hf download` for reliability, and ALWAYS verify file size after download matches expected size.

44. **RealVisXL V4.0 tested — FAILED for full-body voluptuous generation** — RealVisXL V4.0 produces the same portrait/slim bias as Juggernaut XL despite being marketed for photorealism. Tested results: full_body 2/10, voluptuous 2/10. Crops at mid-thigh even with aggressive full-body prompts at 768x1344. NOT recommended for body/full-body generation. Do NOT use RealVisXL for body dataset generation — only Pony V6 with BBW tags produces consistent full-body voluptuous results.

45. **IPAdapter `embeds_scaling` parameter format** — The `embeds_scaling` parameter in IPAdapter nodes uses space-separated values, NOT underscore format. The correct values are:
    - `"V only"` (NOT `"V_ONLY"`) — V-only scaling
    - `"K+V"` — combined K and V scaling
    - `"K only"` — K-only scaling
    
    Using `"V_ONLY"` causes a **400 Bad Request** error from ComfyUI with no helpful message. This is NOT documented in the IPAdapter node description — check `/object_info/IPAdapterFaceID` for valid values.

46. **IPAdapter Plus Face model size mismatch** — The `ip-adapter-plus-face_sdxl_vit-h.safetensors` model is **incompatible** with `IPAdapterUnifiedLoader` nodes. When loaded via `IPAdapterUnifiedLoaderFaceID` or `IPAdapterUnifiedLoader`, it produces a tensor shape mismatch error: `proj_in.weight shape [1280, 1280] vs [1280, 1664]`. The Plus Face model's perceiver resampler expects 1664-dim input (ViT-bigG-14), not 1280-dim (ViT-H-14). Use plain `ip-adapter-faceid_sdxl.bin` with `IPAdapterUnifiedLoaderFaceID` instead.

47. **ReActor face swap in ComfyUI (Phase 2 of body generation)** — Use `ReActorFaceSwap` (preferred, more control) or `ReActorFastFaceSwap` for post-generation face swapping. This is Phase 2 of the validated two-phase approach: generate full-body images with Flux GGUF Q8 or Pony V6 (Phase 1), then swap the target face with ReActor (Phase 2).

    **Required models and setup:**
    - `inswapper_128.onnx` (~529MB) → `models/insightface/inswapper_128.onnx`
      Download: `wget -O models/insightface/inswapper_128.onnx "https://huggingface.co/ezioruan/inswapper_128.onnx/resolve/main/inswapper_128.onnx"`
    - InsightFace detection models: `models/insightface/models/buffalo_l/` (auto-downloaded by ReActor node)
    - Face restoration models: `models/facerestore_models/` — `codeformer-v0.1.0.pth` recommended, `GFPGANv1.4.pth` also available
    - **`onnxruntime` and additional packages are REQUIRED** but NOT listed in ReActor's `requirements.txt`. Install them before starting ComfyUI:
      ```bash
      pip3 install --break-system-packages onnxruntime albumentations onnx ultralytics segment-anything  # or into venv if using one
      ```
      Without `onnxruntime`, ReActor imports but the node is invisible in `/object_info` and face swap returns 512×512 2KB blank thumbnails instead of real images. Without `albumentations`, `onnx`, `ultralytics`, and `segment-anything`, the `reactor_core` import fails and the entire ReActor node disappears from `/object_info`.
    - After installing `onnxruntime` or any ReActor dependency, **restart ComfyUI** — custom nodes only register on startup.
    - Verify ReActor is loaded: `curl -s http://127.0.0.1:8188/object_info/ReActorFaceSwap | python3 -c "import sys,json; d=json.load(sys.stdin); print('OK' if 'ReActorFaceSwap' in d else 'NOT FOUND')"`
    - Reference face image: upload to `input/` directory, reference as filename in workflow

    **ReActorFaceSwap API field names (verified via /object_info):**
    ```python
    "ReActorFaceSwap": {
        "enabled": True,                        # BOOLEAN
        "swap_model": "inswapper_128.onnx",     # STRING — only valid value
        "source_image": ["11", 0],              # IMAGE — linked LoadImage node
        "input_image": ["10", 0],               # IMAGE — linked LoadImage node
        "facedetection": "retinaface_resnet50", # STRING — options: retinaface_resnet50, retinaface_mobile0.25, YOLOv5l, YOLOv5n. NOTE: YOLOv5l is NOT better at detecting small faces in full-body images. At 640px height, all detectors fail on non-frontal poses equally.
        "face_restore_model": "codeformer-v0.1.0.pth",  # STRING, NOT "facerestorer_model"
        "face_restore_visibility": 1.0,         # FLOAT 0.1–1.0, NOT "facerestorer_visibility"
        "codeformer_weight": 0.7,               # FLOAT 0.0–1.0
        "detect_gender_input": "no",            # STRING "no"/"female"/"male", NOT boolean
        "detect_gender_source": "no",            # STRING "no"/"female"/"male", NOT boolean
        "source_faces_index": "0",              # STRING, NOT list [0]
        "input_faces_index": "0",               # STRING, NOT list [0]
        "console_log_level": 1                  # INT 0–2
    }
    ```
    **Common field name mistakes** (these cause silent failures or 400 errors):
    - `facerestorer_model` → should be `face_restore_model`
    - `facerestorer_visibility` → should be `face_restore_visibility`
    - `detect_face_source` / `detect_face_input` → should be `detect_gender_source` / `detect_gender_input`
    - `face_index` → should be `input_faces_index` (STRING "0", not list [0])
    - `source_faces_index` → STRING "0", not list [0]
    - `face_model` → type FACE_MODEL (optional, linked node), NOT a string filename
    - `gender_source` / `gender_target` → should be `detect_gender_source` / `detect_gender_input`

    **Face detection failure on non-frontal poses (CRITICAL):**
    At 1536×640 resolution (ultra-wide for full-body), ReActor's face detection (`retinaface_resnet50`) CANNOT find faces in the following pose types, producing a 512×512 2KB blank thumbnail instead of a real face-swapped image:
    - `turning_back`, `three_quarter`, `arms_crossed`  ← face too small/angled
    - `sitting_elegant`, `leaning_wall`, `walking_toward` ← face too small
    - `hand_on_hip` sometimes fails depending on the image
    Only frontal-facing poses like `standing_confident` reliably produce face swaps at 640px image height.
    
    **`YOLOv5l` does NOT fix this issue** — switching facedetection from `retinaface_resnet50` to `YOLOv5l` still fails on the same non-frontal poses. The issue is fundamental: at 640px image height, a full-body composition produces a face that is too few pixels for any detection model to reliably identify.
    
    **ReActor face swap QUALITY is inconsistent even on successful swaps:** ~40% of successful face swaps produce generic, plastic-looking faces ("uncanny valley" — smooth poreless skin, slightly asymmetrical eyes, melting mouth/chin) that don't closely match the reference. This is a fundamental inswapper limitation, not a configuration issue. Only ~60% of face-swapped images look like the reference person. This makes ReActor marginal for LoRA training datasets where facial consistency is critical — manual curation of every image is MANDATORY.

    **Deformed hands in Flux full-body generation:** Flux.1-dev GGUF Q8 at 1536×640 frequently generates deformed hands (extra/fused fingers, twisted wrists). Expect ~20-30% of images with noticeable hand deformations. Exclude from LoRA datasets or photoshop before use.

    **Flux prompt misinterpretation at 1536×640:** Flux occasionally misinterprets scene/background prompts at ultra-wide aspect ratio (e.g., "park_sunny" → woman on sofa with dog). Always visually verify each generated image against the intended prompt.

    **Workaround:** Generate body images with face-friendly frontal poses for the face swap pass. For non-frontal poses, either skip face swap or generate close-up face crops separately. Manually curate ALL face-swapped images — exclude generic/plastic faces, deformed hands, and scene misinterpretations. Expect ~50-60% usable images from a batch of 34.

    **Output filtering — ComfyUI may produce both a real image AND a 512×512 thumbnail:**
    When ReActor succeeds, it outputs the full-resolution swapped image. When it FAILS (no face detected), it outputs a 512×512 2KB blank thumbnail. When copying outputs from `ComfyUI/output/`, always filter by file size — pick the largest file per generation (real images are 300KB–1.2MB; thumbnails are ~2KB):
    ```python
    best = max(images, key=lambda p: os.path.getsize(p) if os.path.exists(p) else 0)
    ```
    Or validate dimensions with PIL:
    ```python
    from PIL import Image
    img = Image.open(path)
    if img.size != expected_size:
        # This is a failed thumbnail, not a real image
    ```

    **Minimal ReActor workflow (API format):**
    ```json
    {
      "10": {"class_type": "LoadImage", "inputs": {"image": "body_image.png"}},
      "11": {"class_type": "LoadImage", "inputs": {"image": "face_reference.jpg"}},
      "20": {"class_type": "ReActorFaceSwap", "inputs": {
        "enabled": true, "swap_model": "inswapper_128.onnx",
        "source_image": ["11", 0], "input_image": ["10", 0],
        "facedetection": "retinaface_resnet50",
        "face_restore_model": "codeformer-v0.1.0.pth",
        "face_restore_visibility": 1.0, "codeformer_weight": 0.7,
        "detect_gender_input": "no", "detect_gender_source": "no",
        "source_faces_index": "0", "input_faces_index": "0",
        "console_log_level": 1}},
      "30": {"class_type": "SaveImage", "inputs": {"filename_prefix": "faceswap", "images": ["20", 0]}}
    }
    ```

    This avoids IPAdapter's composition dominance — faces come from the reference photo, body composition from the prompt.

48. **ReActor `codeformer` model filename must match exactly** — The face restoration model is `codeformer-v0.1.0.pth` (with hyphens and "v0.1.0"), NOT `codeformer_v1.0.pth` (with underscores and "v1"). If you use the wrong filename, the ReActor workflow fails with a model-not-found error. Verify the exact filename in `models/facerestore_models/` — common names are `codeformer-v0.1.0.pth` and `GFPGANv1.4.pth`. Do NOT guess the version number; check the actual files on disk first.

49. **PuLID for Flux face consistency (IPAdapter does NOT support Flux)** — IPAdapter Plus (`ComfyUI_IPAdapter_plus`) only supports SD1.5 and SDXL, NOT Flux. For face consistency with Flux.1 Dev, use **PuLID** (Pose-agnostic and Lightweight Identity) via ComfyUI-PuLID-Flux. PuLID is zero-shot: give it one reference face photo and it maintains face identity across varied generations, no LoRA training required. This is ideal for creating consistent AI influencer datasets.

    **⚠️ PuLID has critical pitfalls on ComfyUI v0.20.1+** — see `references/pulid-flux-pitfalls.md` for mandatory fixes (missing w600k_r50.onnx, forward_orig signature, provider=CPU on Py3.13).

    **Ready-to-use workflow template:** `templates/pulid-flux-api.json` — a validated minimal PuLID + Flux GGUF API workflow. Replace `REPLACE_WITH_PROMPT` and `REPLACE_WITH_REFERENCE_IMAGE` before submitting.

    **Install ComfyUI-PuLID-Flux:**
    ```bash
    cd ~/comfy/ComfyUI/custom_nodes
    git clone https://github.com/balazik/ComfyUI-PuLID-Flux.git
    source ~/comfy/ComfyUI/.venv/bin/activate
    pip install insightface onnxruntime onnxruntime-gpu facexlib timm ftfy
    # Then restart ComfyUI — custom nodes only register on startup
    ```

    **Required models (3 downloads, ~2GB total):**
    - **PuLID Flux model** (~1.1GB): `models/pulid/pulid_flux_v0.9.1.safetensors`
      — Download: `https://huggingface.co/h94/PuLID/resolve/main/pulid_flux_v0.9.1.safetensors`
    - **EVA-CLIP** (~816MB): `models/clip/EVA02_CLIP_L_336_psz14_s6B.pt`
      — Download: `https://huggingface.co/h94/PuLID/resolve/main/EVA02_CLIP_L_336_psz14_s6B.pt`
    - **InsightFace AntelopeV2** (~160MB total): `models/insightface/models/antelopev2/`
      — 4 files: `1k3d68.onnx`, `2d106det.onnx`, `genderage.onnx`, `scrfd_10g_bnkps.onnx`
      — Download each from `https://huggingface.co/datasets/GourieND/insightface_antelopev2/resolve/main/`

    **⚠️ AntelopeV2 vs buffalo_l:** PuLID uses `antelopev2` models (in `models/insightface/models/antelopev2/`), NOT `buffalo_l` (which is for ReActor/IPAdapter). They go in different subdirectories. Both can coexist.

    **PuLID nodes available (verify with `/object_info`):**
    - `PulidFluxModelLoader` — loads `pulid_flux_v0.9.1.safetensors`
    - `PulidFluxEvaClipLoader` — loads `EVA02_CLIP_L_336_psz14_s6B.pt`
    - `PulidFluxInsightFaceLoader` — loads AntelopeV2 models; `provider` param must be `"CPU"` on Python 3.13+ (onnxruntime-gpu has no CUDAExecutionProvider)
    - `ApplyPulidFlux` — applies PuLID face identity to the model cond
    - `easy pulIDApply` / `easy pulIDApplyADV` — simplified wrappers

    **PuLID + Flux workflow node chain:**
    ```
    GGUFLoaderKJ(model_name="flux1-dev-Q8_0.gguf", extra_model_name="none", dequant_dtype="default",
                  patch_dtype="default", patch_on_device=false, enable_fp16_accumulation=false,
                  attention_override="none")
    → ModelSamplingFlux(model=GGUFLoaderKJ.0, max_shift=1.15, base_shift=0.5, width=1024, height=1024)
    → DualCLIPLoader(clip_name1="t5xxl_fp8_e4m3fn.safetensors", clip_name2="clip_l.safetensors", type="flux")
    → VAELoader(vae_name="ae.safetensors")
    → PulidFluxModelLoader(pulid_file="pulid_flux_v0.9.1.safetensors")
    → PulidFluxEvaClipLoader(eva_file="EVA02_CLIP_L_336_psz14_s6B.pt")
    → PulidFluxInsightFaceLoader(provider="CUDA")
    → LoadImage(image="face_reference.png")  ← the chosen face photo
    → ApplyPulidFlux(
        model=ModelSamplingFlux.0,
        pulid_flux=PulidFluxModelLoader.0,
        eva_clip=PulidFluxEvaClipLoader.0,
        face_analysis=PulidFluxInsightFaceLoader.0,
        image=LoadImage.0,
        weight=0.8-1.0,         ← start at 1.0, reduce if over-fitted
        start_at=0.0,           ← face identity applies from step 0
        end_at=1.0,             ← face identity applies through all steps
        fusion="median"         ← fusion method: "mean", "median", "threshold"
      )
    → CLIPTextEncode(text=prompt, clip=DualCLIPLoader.0)
    → CLIPTextEncode(text="", clip=DualCLIPLoader.0)  ← empty negative
    → FluxGuidance(guidance=3.5, conditioning=positive_clip.0)
    → EmptyLatentImage(width=1024, height=1024, batch_size=1)
    → KSampler(steps=20, cfg=1.0, sampler="euler", scheduler="simple", denoise=1.0,
                model=ApplyPulidFlux.0, positive=FluxGuidance.0, negative=empty_clip.0,
                latent_image=EmptyLatentImage.0)
    → VAEDecode(samples=KSampler.0, vae=VAELoader.0)
    → SaveImage
    ```

    **Key PuLID parameters:**
    - `weight`: 0.8-1.0 (start at 1.0 for strong face adherence, reduce to 0.6-0.8 for more style flexibility)
    - `start_at` / `end_at`: Control when face identity kicks in during denoising (0.0-1.0). Default 0.0/1.0 = full range
    - `fusion`: `"mean"` averages embeddings, `"median"` is more robust to outliers, `"threshold"` clips extreme values
    - **KSampler cfg MUST be 1.0** for Flux (not 3.5 — guidance is set via FluxGuidance node, not KSampler CFG)

    **⚠️ PuLID API parameter names differ from node display names — ALWAYS verify via `/object_info`:**
    Multiple PuLID nodes have parameter names in the API format that differ from what the ComfyUI web UI displays. Building workflows by guessing parameter names causes HTTP 400 errors with unhelpful messages. Before creating a PuLID workflow:
    ```bash
    # Check actual parameter names for each node
    curl -s http://127.0.0.1:8188/object_info/PulidFluxModelLoader | python3 -m json.tool
    curl -s http://127.0.0.1:8188/object_info/PulidFluxEvaClipLoader | python3 -m json.tool
    curl -s http://127.0.0.1:8188/object_info/PulidFluxInsightFaceLoader | python3 -m json.tool
    curl -s http://127.0.0.1:8188/object_info/ApplyPulidFlux | python3 -m json.tool
    ```
    Known mismatches (validated May 2026):
    - `PulidFluxModelLoader`: API uses `pulid_file` (NOT `pulid_name`). The template and documentation were wrong.
    - `PulidFluxEvaClipLoader`: API uses `eva_file` (NOT `eva_name`).
    - `PulidFluxInsightFaceLoader`: API uses `provider` (string "CUDA" or "CPU"). Must be explicitly set — omitting it may cause silent defaults to CPU.
    - `KSampler` in Flux workflows: MUST include `denoise: 1.0` explicitly. Omitting it causes validation errors in some ComfyUI versions even though the default should be 1.0.
    - `ApplyPulidFlux`: `weight`, `start_at`, `end_at`, `fusion` are confirmed correct as documented above.

    If PuLID generation returns HTTP 400, the #1 cause is mismatched parameter names. Always query `/object_info` for the exact node before building the workflow JSON.

    **⚠️ onnxruntime-gpu has NO CUDAExecutionProvider on Python 3.13+** — The `onnxruntime-gpu` package on Python 3.13+ only provides `CPUExecutionProvider` and `AzureExecutionProvider` (no CUDA support). This means `PulidFluxInsightFaceLoader(provider="CUDA")` will FAIL on Python 3.13. **Fix:** Check available providers first:
    ```bash
    ~/comfy/ComfyUI/.venv/bin/python -c "import onnxruntime; print(onnxruntime.get_available_providers())"
    ```
    If `CUDAExecutionProvider` is missing, set `provider="CPU"` in the PuLID workflow. InsightFace still works on CPU — it's slower (~2-3x) but functional. On Python 3.13+, `provider="CPU"` is the only option regardless of GPU availability.

    **⚠️ PulidFluxEvaClipLoader may appear empty in /object_info** — When querying `GET /object_info/PulidFluxEvaClipLoader`, the response may show `required: {}` and `optional: {}` (no inputs). This is because the node auto-discovers the EVA-CLIP model from `models/clip/`. Despite appearing empty, you still need to include the node in your workflow JSON with the `eva_file` parameter — it's required for the node to load the model even if the schema doesn't list it as a required input. The model file must exist at `models/clip/EVA02_CLIP_L_336_psz14_s6B.pt`.

    **Use case: AI influencer dataset generation** — Generate 25-30 variations of a chosen face with PuLID for identity consistency. Vary prompts (poses, outfits, settings, lighting) while PuLID keeps the same face. Then curate the best images and train a dedicated Flux LoRA for permanent character consistency. PuLID is better than IPAdapter FaceID for Flux because: (1) IPAdapter Plus doesn't support Flux at all, (2) PuLID is zero-shot (one photo, no training), (3) PuLID produces less composition dominance than IPAdapter (body/outfit prompts work better).

    **VRAM impact:** Adding PuLID to Flux Q8 adds ~2GB VRAM overhead on top of the ~11.5GB Flux baseline. On RTX 3060 12GB, total VRAM usage peaks at ~11.8GB — very tight. If OOM occurs, try: (1) reduce resolution to 512x512 then upscale, (2) reduce KSampler steps to 15, (3) use `fusion="mean"` (lighter than median).

37. **httpx `http2=True` requires the `h2` package** — If you set `http2=True` in `httpx.AsyncClient()` without installing `h2` (`pip install httpx[http2]`), all requests return `502 Bad Gateway` with the message "Using http2=True, but the 'h2' package is not installed." This is a silent failure that looks like a ComfyUI connectivity issue but is actually a client-side HTTP library config error. **Fix**: either `pip install h2` (or `httpx[http2]`) or set `http2=False` (HTTP/1.1 is fine for local ComfyUI proxying). For local ComfyUI clients, `http2=False` is the correct default — HTTP/2 only matters for remote/high-latency connections.

36. **Always verify ComfyUI node parameter names via `/object_info` before building API workflows** — Multiple custom nodes have parameter names in API format that differ from the ComfyUI web UI display. Building workflow JSON by guessing parameter names causes HTTP 400 errors with unhelpful error messages. This is the #1 cause of "workflow works in UI but fails via API" issues. The pattern that causes failures:
    1. You see a parameter labeled "pulid_name" or "model" in the ComfyUI UI
    2. You use that name in the API JSON
    3. ComfyUI rejects it with a generic 400 Bad Request
    4. No error message tells you the correct name — you must query `/object_info`
    
    **Always run this before building any workflow with unfamiliar nodes:**
    ```bash
    curl -s http://127.0.0.1:8188/object_info | python3 -c "
    import sys, json
    d = json.load(sys.stdin)
    for node in ['NodeName1', 'NodeName2']:
        if node in d:
            inputs = d[node]['input']['required']
            print(f'{node} required inputs: {list(inputs.keys())}')
            for k, v in inputs.items():
                if isinstance(v, list) and len(v) > 1:
                    print(f'  {k}: type={v[0]}, default={v[1]}')
                else:
                    print(f'  {k}: {v}')
    "
    ```
    Known mismatches (validated May 2026): `PulidFluxModelLoader` → `pulid_file` (not `pulid_name`), `PulidFluxEvaClipLoader` → `eva_file` (not `eva_name`), `GGUFLoaderKJ` → `model_name` (not `unet_name`), `KSampler` → requires explicit `denoise` input.
32. **VHS_VideoCombine requires ffmpeg** — Install via `pip install imageio-ffmpeg` + copy binary to ComfyUI dir. Without ffmpeg, video gen silently fails at encoding.
33. **Video gen ~3 min on RTX 3060** — Wan2.1-T2V-1.3B fp8_e4m3fn, 33 frames 832x480 takes ~178s.

31. **Anima 3.0 (WanVideo) requires UMT5-XXL, not qwen text encoder** — The
    `LoadWanVideoT5TextEncoder` node in ComfyUI-WanVideoWrapper strictly validates
    `model_name == "umt5-xxl"` and raises `ValueError` for any other model. The
    `qwen_3_06b_base.safetensors` text encoder only works with Wan2.1 official models,
    NOT Anima. Download UMT5-XXL from `Wan-AI/Wan2.1-T2V-1.3B` via `huggingface_hub`
    (direct URL returns 401 — must use `hf_hub_download`):
    ```python
    hf_hub_download(repo_id='Wan-AI/Wan2.1-T2V-1.3B',
      filename='models_t5_umt5-xxl-enc-bf16.pth',
      local_dir='/path/to/ComfyUI/models/text_encoders/')
    ```
    **CRITICAL: HuggingFace downloads the file as `models_t5_umt5-xxl-enc-bf16.pth`,
    but ComfyUI WanVideoWrapper nodes expect it listed as `umt5-xxl-encoder-bf16.pth`
    in `folder_paths.get_filename_list("text_encoders")`.** Create a symlink:
    ```bash
    cd ~/comfy/ComfyUI/models/text_encoders/
    ln -sf models_t5_umt5-xxl-enc-bf16.pth umt5-xxl-encoder-bf16.pth
    ```
    **WanVideoTextEncodeCached availability:** This node DOES exist in
    ComfyUI-WanVideoWrapper once all Python dependencies are installed (see pitfall
    #24). Before using it, verify:
    ```bash
    curl -s http://localhost:8188/object_info | python3 -c "
    import sys,json; d=json.load(sys.stdin)
    print('WanVideoTextEncodeCached' in d)
    "
    ```
    If it returns `False`, you have missing dependencies (the entire WanVideoWrapper
    failed to load). Install ALL deps at once (see pitfall #24), then restart ComfyUI.
    To list available WanVideo nodes: `curl -s http://localhost:8188/object_info | python3 -c "import sys,json; d=json.load(sys.stdin); [print(k) for k in d if 'WanVideo' in k or 'Wan' in k]"`.

    **ALWAYS validate node parameters against `/object_info` before building workflows
    by hand.** The WanVideo nodes had multiple wrong/missing parameters in initial workflow building:
    - `WanVideoModelLoader` has NO `attention_mode` param — remove it entirely
    - `WanVideoModelLoader` REQUIRES `load_device` param (value: `"offload_device"`) — omitting it causes a validation error
    - `WanVideoVAELoader` uses `model_name` (NOT `model`) for the VAE checkpoint
    - `VHS_VideoCombine` format must be `video/h264-mp4` (NOT `h264-mp4`)
    - `VHS_VideoCombine` REQUIRES `pingpong: false` — omitting it defaults to true, which reverses every other frame
    Verify with: `curl -s http://localhost:8188/object_info/WanVideoModelLoader | python3 -m json.tool`

    For 12GB cards (RTX 3060), use `quantization: "fp8_e4m3fn_fast"` on the model
    loader, `force_offload: True` on the sampler, and `enable_vae_tiling: True` on
    decode. Frame count must satisfy `(frames-1) % 4 == 0` (minimum 5). Resolution
    must be multiples of 16. See `references/seedvr2-anima-nodes.md` for full node chain.

32. **VHS_VideoCombine outputs use `gifs` key, not `images`** — When building
    API clients that poll ComfyUI history for generation results, video outputs from
    `VHS_VideoCombine` appear under `output[node_id]["gifs"]` (not `"images"`). Each
    entry has `filename`, `subfolder`, and `type` keys, just like image entries, but
    the key name is `"gifs"`. If you only check `"images"`, MP4/WebM outputs will be
    silently dropped. Update your result parser to check both keys:
    ```python
    for node_id, node_output in history.get("outputs", {}).items():
        for img in node_output.get("images", []):
            outputs.append(img.get("filename", ""))
        for vid in node_output.get("gifs", []):
            filename = vid.get("filename", "")
            if filename:
                outputs.append(filename)
    ```
    The proxy endpoint that serves these files (`/view?filename=X&type=output`) works
    for both images and videos — it passes through ComfyUI's `content-type` header, so
    MP4 files get `video/mp4` and PNG files get `image/png`.

31. **Batch upscale via ComfyUI REST API can fail** — Submitting multiple
    upscale requests to `/api/prompt` in rapid succession can cause 400
    Bad Request errors (input validation fails on image path references
    when the queue processes out of order). For batch upscaling, use PIL
    Lanczos as a reliable fallback: resize 4x with `Image.LANCZOS`, then
    center-crop to target aspect ratio and resize to final dimensions.
    This avoids API queue dependencies and produces acceptable quality for
    social media. Single-image ComfyUI upscale (RealESRGAN) works fine
    via the API — the issue is only with rapid-fire batch submissions.

24. **Social media image dimensions** — ComfyUI generates at model-native
    resolutions (512x512, 768x1024, etc.) which don't match social media
    specs. Post-processing is always required:
    - Instagram feed (portrait): 1080x1350 (4:5)
    - Instagram stories/Reels/TikTok: 1080x1920 (9:16)
    - Instagram square: 1080x1080 (1:1)
    - Profile avatar: 1080x1080
    Use PIL Lanczos resize (4x upscale then crop to target) or RealESRGAN
    4x upscale followed by center-crop. Never upscale below 1080px on the
    long edge or social platforms will over-compress.

23. **WEBP animated → MP4 conversion** — ComfyUI's `SaveAnimatedWEBP` produces
    animated WEBP files that social media platforms reject. Convert to MP4:
    ```python
    from PIL import Image
    import subprocess
    # Extract frames
    img = Image.open("input.webp")
    for i in range(img.n_frames):
        img.seek(i)
        img.convert("RGB").save(f"frames/frame_{i:04d}.png")
    # Encode to MP4
    subprocess.run([
        "ffmpeg", "-y", "-framerate", "8",
        "-i", "frames/frame_%04d.png",
        "-c:v", "libx264", "-pix_fmt", "yuv420p",
        "-preset", "medium", "-crf", "23",
        "-vf", "scale=512:512:flags=lanczos",
        "-an", "output.mp4"
    ])
    ```
    If system `ffmpeg` is unavailable, use `imageio-ffmpeg` (bundled with
    imageio): `pip install imageio imageio-ffmpeg`, then
    `imageio_ffmpeg.get_ffmpeg_exe()` returns the binary path. WEBP files
    cannot be read directly by most ffmpeg builds — always extract frames
    first via Pillow, then encode.

## Verification Checklist

Use `python3 scripts/health_check.py` to run the whole list at once. Manual:

- [ ] `hardware_check.py` verdict is `ok` OR the user explicitly chose Comfy Cloud
- [ ] `comfy --version` works (or `uvx --from comfy-cli comfy --help`)
- [ ] `curl http://HOST:PORT/system_stats` returns JSON
- [ ] `comfy model list` shows at least one checkpoint (local) OR
      `/api/experiment/models/checkpoints` returns models (cloud)
- [ ] Workflow JSON is in API format
- [ ] `check_deps.py` reports `is_ready: true` (or only `node_check_skipped`
      on cloud free tier)
- [ ] Test run with a small workflow completes; outputs land in `--output-dir`
