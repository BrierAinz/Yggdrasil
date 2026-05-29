# AcademiaSD Custom Nodes for ComfyUI

**Repo:** https://github.com/AcademiaSD/comfyui_AcademiaSD
**Stars:** 41 | **Forks:** 7
**YouTube:** @Academia SD — ComfyUI & ForgeWebUI tutorials

## Why Useful

AcademiaSD is a quality-of-life node pack that reduces canvas clutter and
automates tedious tasks (downloading, captioning, LoRA management, resolution
math). Particularly useful for LoRA training workflows (Eir dataset pipeline)
and video generation workflows (LTX-Video, Wan 2.x).

## Key Custom Nodes

### Automatic Downloader v0.99
Paste Civitai or HuggingFace links → downloads directly to canvas. Detects
GGUF versions from HF repos. Manages Civitai/HF tokens for NSFW/private
models. Shows real-time MB/GB progress. Checks `extra_model_paths.yaml` to
avoid duplicate downloads.

### Multi-LoRA v0.8
Load multiple LoRAs in one compact node. Per-LoRA toggles (enable/disable
without disconnecting). Hover tooltips show base model, training resolution,
top-15 trigger words. "Model Only" injection to bypass text-encoder errors in
video models. Compatible with SD1.5, SDXL, Flux, and video architectures.

### Resolution Selector v0.9
Forces all inputs/outputs to multiples of 8 (prevents Flux/LTX-Video tensor
errors). Quick buttons: Half, Double, Swap. 📐 button reads image dimensions
from a connected Load Image node.

### Image Save & Send v0.3
Saves images normally + "Send to Edit" button that copies to
`input/Academia_Edits/` and refreshes the source Load Image node. Perfect for
cyclic inpainting / I2I workflows.

### VL Model Loader + Captioner (Qwen3-VL)
Full dataset captioning pipeline:
- **VLModel (Down)Loader** — loads VLMs from HF (Qwen3-VL-2B-Instruct etc.)
  with low_vram toggle
- **Captioner** — interrogates images with natural-language prompts
- **Batch Image Loader** — iterates numbered images from a folder
- **Counter / Reset Counter** — tracks batch progress via `loops.json`
- **Save Dataset Caption (.txt)** — sidecar .txt files with trigger-word
  prefix/suffix positioning

### Time Calculator
Real-time video duration display (green LED style). Outputs FRAMES (INT) and
FPS (FLOAT). Supports decimal FPS (23.976, 29.97). 180px wide — ultra compact.

### LTXV Multi-Frames
Drag-and-drop multi-image injector for LTX-Video I2V. Auto-assigns frame
indexes (0 for first, -1 for last). Per-frame strength control. Direct latent
injection without external wiring spaghetti.

### Numeric Input
Single input → INT + FLOAT simultaneously. Eliminates converter nodes.

### Bypass Nodes by Value
Control up to 5 nodes (ON/BYPASS). Manual toggle or automatic via
`active_count` integer. Switches auto-rename to match connected node titles.

### Gemini Vision 1.1.2
Dataset captioning via Google Gemini. See example workflow:
`Gemini_dataset_captions_AcademiaSD.json`

## Installation

```bash
cd /path/to/ComfyUI/custom_nodes
git clone https://github.com/AcademiaSD/comfyui_AcademiaSD.git
# Restart ComfyUI
```

Missing dependency? Install into ComfyUI's venv:
```bash
/path/to/ComfyUI/.venv/bin/pip install matplotlib  # for dwpose nodes
```

## Example Workflows (66 JSON files)

Key categories available in `example_workflows/`:

| Category | Notable Workflows |
|----------|-------------------|
| LTX-Video 2.x/2.3 | V12–V24, GGUF variants, TILED VAE, FFLF (first/last frame) |
| LTX-Video specialized | Loop Keyframes, V2V Detailer, Video Outpaint, Clone Voice |
| Wan 2.1/2.2 | IMG2VID, T2V, 14B variants, FusionX I2V, Holocine, 5B Ovi |
| Hunyuan | Hunyuan Video, Hunyuan 1.5 I2V |
| Flux 2 | GGUF, Klein GGUF, Krea I2I/T2I multilora |
| Qwen/Ernie | Image generation, image edit, dataset captioning |
| FireRed | Edit 1.1 plus ultra |
| Self-Forcing | T2V, VACE I2V |

Load any `.json` file via ComfyUI → Load workflow, or drag into the canvas.