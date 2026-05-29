# NSFW Pipeline: Model & Node Reference

## Base Models

| Model | File | Size | HuggingFace Repo | Download Command |
|-------|------|------|-------------------|------------------|
| Pony Diffusion V6 XL | `ponyDiffusionV6XL_v6StartWithThisOne.safetensors` | ~6.5GB | `LyliaEngine/Pony_Diffusion_V6_XL` | `hf download LyliaEngine/Pony_Diffusion_V6_XL ponyDiffusionV6XL_v6StartWithThisOne.safetensors --local-dir ~/comfy/ComfyUI/models/checkpoints` |
| RealVisXL V5 | `RealVisXL_V5.0.safetensors` | ~6.5GB | `SG161222/RealVisXL_V5.0` | `hf download SG161222/RealVisXL_V5.0 RealVisXL_V5.0.safetensors --local-dir ~/comfy/ComfyUI/models/checkpoints` |
| Flux.1-dev FP8 | `flux1-dev-fp8.safetensors` | ~12GB | `Comfy-Org/flux1-dev` | Barely fits RTX 3060 12GB — use only for high-quality single images |

## IPAdapter & Face Models

| Model | File | HuggingFace Repo | Target Dir |
|-------|------|-------------------|------------|
| IPAdapter FaceID SDXL | `ip-adapter-plus-faceid_sdxl.bin` | `h94/IP-Adapter` → `sdxl_models/` | `models/ipadapter/` |
| IPAdapter SDXL vit-h | `ip-adapter_sdxl_vit-h.safetensors` | `h94/IP-Adapter` → `sdxl_models/` | `models/ipadapter/` |
| InsightFace buffalo_l | `model.onnx` | `h94/IP-Adapter` → `models/buffalo_l/` | `models/insightface/` |

Download via `huggingface_hub` Python API:
```python
from huggingface_hub import hf_hub_download
# IPAdapter FaceID
hf_hub_download(repo_id='h94/IP-Adapter', filename='sdxl_models/ip-adapter-plus-faceid_sdxl.bin', local_dir='models/ipadapter')
# InsightFace
hf_hub_download(repo_id='h94/IP-Adapter', filename='models/buffalo_l/model.onnx', local_dir='models/insightface')
```

## Upscalers

| Model | File | Use | Target Dir |
|-------|------|-----|------------|
| 4x-UltraSharp | `4x-UltraSharp.pth` | Photorealistic skin detail | `models/upscale_models/` |
| RealESRGAN x4plus | `RealESRGAN_x4plus.pth` | General upscale (already installed) | `models/upscale_models/` |

## NSFW Custom Nodes

Additional nodes beyond the SFW setup that NSFW workflows require:

| Node | Repo | Purpose |
|------|------|---------|
| ComfyUI-CLIPSeg | `shadowcz007/comfyui-CLIPSeg` | Semantic masking (clothing removal inpainting) |
| comfyui_segment_anything | `storyicon/comfyui_segment_anything` | Precise body/clothing segmentation |
| ComfyUI-SAM2 | `0xswordsman/ComfyUI-SAM2` | Zero-shot segmentation (needs `addict` + `yapf` packages) |
| comfyui_AcademiaSD | `AcademiaSD/comfyui_AcademiaSD` | Multi-LoRA, VL Captioner, video workflows |
| ComfyUI-FL-Nodes | `gitmylo/FlowNodes` | Math/conversion nodes (NOT `6174/comfyui-flowy-nodes`) |

## Pony V6 XL Prompting

Pony uses a score-based quality tag system:

**Positive prefix:** `score_9, score_8_up, score_7_up, source_realistic, realistic, photorealistic,`
**Negative prefix:** `score_6, score_5, score_4, source_cartoon, anime, 3d, bad anatomy, deformed,`

Character tags: `1girl, [name_trigger], [hair], [eyes], [body_type], [skin_tone]`
NSFW tags: `nude, completely naked, [body_description], [pose]`

## ComfyUI Custom Node Install Pitfalls

- **ComfyUI-Simple-Math** — registry entry points to an empty repo. `SimpleMath+` is in `ComfyUI_Comfyroll_CustomNodes` (already installed). Remove the empty clone.
- **ComfyUI-FL-Nodes** — common search finds `6174/comfyui-flowy-nodes` (wrong, empty). Correct: `gitmylo/FlowNodes`.
- **ComfyUI-SAM2** — requires `addict` and `yapf` Python packages. Install: `pip install addict yapf` in the ComfyUI `.venv`.
- **ComfyUI-ReActor** — requires `insightface` and `onnxruntime-gpu`. The `transformers>=5.5` flash_attn KeyError bug can block ReActor import (see main skill pitfall #22).
- Always verify a cloned repo has `__init__.py` before restarting ComfyUI.