# SeedVR2 & Anima 3.0 Workflow Nodes

Custom nodes and models for the SeedVR2 video upscaler and Anima 3.0 video
generation workflows in ComfyUI.

## Custom Nodes Required

| Node Name | Package | Install |
|-----------|---------|---------|
| SeedVR2VideoUpscaler | ComfyUI-SeedVR2 | `git clone https://github.com/AcademiaSD/ComfyUI-SeedVR2.git` into `custom_nodes/` |
| SeedVR2LoadVAEModel | ComfyUI-SeedVR2 | (included above) |
| SeedVR2LoadDiTModel | ComfyUI-SeedVR2 | (included above) |
| WanVideoModelLoader | ComfyUI-WanVideoWrapper | `git clone https://github.com/kijai/ComfyUI-WanVideoWrapper.git` into `custom_nodes/` |
| WanVideoTextEncodeCached | ComfyUI-WanVideoWrapper | (included above) — **MAY NOT EXIST in all versions; verify via `/object_info` before using** |
| WanVideoSampler | ComfyUI-WanVideoWrapper | (included above) |
| WanVideoDecode | ComfyUI-WanVideoWrapper | (included above) |
| WanVideoVAELoader | ComfyUI-WanVideoWrapper | (included above) |
| WanVideoEmptyEmbeds | ComfyUI-WanVideoWrapper | (included above) |
| VHS_VideoCombine | ComfyUI-VideoHelperSuite | `git clone https://github.com/Kosinkadink/ComfyUI-VideoHelperSuite.git` into `custom_nodes/` |
| easy clearCacheAll | ComfyUI-Easy-Use | `git clone https://github.com/yolain/ComfyUI-Easy-Use.git` into `custom_nodes/` |
| Image Comparer (rgthree) | rgthree-comfy | `git clone https://github.com/rgthree/rgthree-comfy.git` into `custom_nodes/` |

## Models Required for Anima 3.0 (WanVideo-based)

| Model File | Target Directory | Size |
|------------|-----------------|------|
| `anima-preview3-base.safetensors` | `models/diffusion_models/` | ~3.9 GB |
| `umt5-xxl-encoder-bf16.pth` | `models/text_encoders/` | ~9.6 GB |
| `qwen_image_vae.safetensors` | `models/vae/` | ~243 MB |
| `clip_vision_vit_h.safetensors` | `models/clip_vision/` | ~2.5 GB |

**CRITICAL:** Anima 3.0 requires the UMT5-XXL text encoder (`umt5-xxl-encoder-bf16.pth`),
NOT `qwen_3_06b_base.safetensors`. The `LoadWanVideoT5TextEncoder` node strictly
validates model name = "umt5-xxl" and raises `ValueError` for any other model.
The `qwen_3_06b_base` encoder only works with Wan2.1 models, not Anima.

**Download UMT5-XXL** (direct URL returns 401 — requires HuggingFace):
```python
from huggingface_hub import hf_hub_download
hf_hub_download(
    repo_id='Wan-AI/Wan2.1-T2V-1.3B',
    filename='models_t5_umt5-xxl-enc-bf16.pth',
    local_dir='/home/brierainz/comfy/ComfyUI/models/text_encoders/'
)
# File downloads as models_t5_umt5-xxl-enc-bf16.pth, but WanVideoWrapper
# expects "umt5-xxl-encoder-bf16.pth" or "umt5-xxl-encoder-bf16.safetensors"
# May need to rename or symlink depending on version.
```

## Anima 3.0 Minimal WanVideo Node Chain

Anima 3.0 is a WanVideo diffusion model — use `WanVideoModelLoader`, NOT
AnimateDiff motion modules.

```
# PREFERRED (if WanVideoTextEncodeCached is available):
WanVideoModelLoader (model: anima-preview3-base.safetensors, quantization: fp8_e4m3fn_fast)
→ WanVideoTextEncodeCached (model_name: umt5-xxl-encoder-bf16.pth, use_disk_cache: True)
→ WanVideoVAELoader (model: qwen_image_vae.safetensors)
→ WanVideoEmptyEmbeds (width, height, num_frames)
→ WanVideoSampler (model, image_embeds, text_embeds, steps, cfg, shift: 5.0, scheduler: unipc, force_offload: True)
→ WanVideoDecode (vae, samples, enable_vae_tiling: True)
→ VHS_VideoCombine (format: h264-mp4, frame_rate, filename_prefix)

# FALLBACK (if WanVideoTextEncodeCached is NOT available — verify first!):
WanVideoModelLoader (model: anima-preview3-base.safetensors, quantization: fp8_e4m3fn_fast)
→ LoadWanVideoT5TextEncoder (model_name: "umt5-xxl")
→ WanVideoTextEncode (text_encs from T5 loader, clip, positive_prompt, negative_prompt)
→ WanVideoVAELoader (model: qwen_image_vae.safetensors)
→ WanVideoEmptyEmbeds (width, height, num_frames)
→ WanVideoSampler (model, image_embeds, text_embeds, steps, cfg, shift: 5.0, scheduler: unipc, force_offload: True)
→ WanVideoDecode (vae, samples, enable_vae_tiling: True)
→ VHS_VideoCombine (format: h264-mp4, frame_rate, filename_prefix)
```

**Fallback if WanVideoTextEncodeCached is unavailable:** Query
`GET /object_info` and look for `WanVideoTextEncodeCached`. If absent, use the
two-node chain instead:
```
LoadWanVideoT5TextEncoder (model_name: "umt5-xxl")
→ WanVideoTextEncode (text_encs, clip, prompt, ...)
```
This keeps T5 (~9.6GB) in VRAM throughout sampling, so on 12GB cards you
MUST use `quantization: "fp8_e4m3fn_fast"` on WanVideoModelLoader and
`force_offload: True` on WanVideoSampler. If VRAM is still tight, reduce
resolution or frame count.

**Verify node availability before building the workflow:**
```bash
curl -s http://localhost:8188/object_info | python3 -c "
import sys,json; d=json.load(sys.stdin)
print('WanVideoTextEncodeCached' in d)
if 'WanVideoTextEncodeCached' not in d:
    print('AVAILABLE WanVideo nodes:')
    for k in d:
        if 'Wan' in k: print(f'  {k}')
"
```

**Why prefer WanVideoTextEncodeCached when available?** It loads the T5,
encodes both prompts, then offloads T5 (~9.6GB freed), caching to disk for
reuse. This is essential for 12GB VRAM cards. The separate
LoadWanVideoT5TextEncoder + WanVideoTextEncode keeps T5 in VRAM throughout,
risking OOM.

**Frame count constraint:** (frames - 1) % 4 == 0. Minimum 5 frames.
**Resolution constraint:** width and height multiples of 16.
**RTX 3060 12GB:** Use fp8_e4m3fn_fast quantization + force_offload=True + VAE tiling.

### WanVideoWrapper API Node Names (class_type)

| Display Name | class_type | Key Inputs |
|--------------|-----------|------------|
| WanVideoModelLoader | `WanVideoModelLoader` | model, base_precision, quantization, load_device, attention_mode |
| LoadWanVideoT5TextEncoder | `LoadWanVideoT5TextEncoder` | model_name (must be "umt5-xxl"), precision |
| WanVideoTextEncodeCached | `WanVideoTextEncodeCached` | model_name, positive_prompt, negative_prompt, quantization, use_disk_cache, device |
| WanVideoClipTextEncode | `WanVideoClipTextEncode` | clip_name, positive_prompt, negative_prompt |
| WanVideoVAELoader | `WanVideoVAELoader` | model, precision |
| WanVideoEmptyEmbeds | `WanVideoEmptyEmbeds` | width, height, num_frames |
| WanVideoSampler | `WanVideoSampler` | model, image_embeds, text_embeds, steps, cfg, shift, seed, force_offload, scheduler, riflex_freq_index |
| WanVideoDecode | `WanVideoDecode` | vae, samples, enable_vae_tiling, tile_x, tile_y, tile_stride_x, tile_stride_y |
| VHS_VideoCombine | `VHS_VideoCombine` | images, frame_rate, loop_count, format, save_output, filename_prefix |

## Install Steps

```bash
cd /home/brierainz/comfy/ComfyUI

# Install custom nodes
cd custom_nodes
git clone https://github.com/yolain/ComfyUI-Easy-Use.git
git clone https://github.com/rgthree/rgthree-comfy.git
git clone https://github.com/kijai/ComfyUI-WanVideoWrapper.git
git clone https://github.com/Kosinkadink/ComfyUI-VideoHelperSuite.git
# SeedVR2 should already exist if using AcademiaSD

# Install requirements
cd /home/brierainz/comfy/ComfyUI
source .venv/bin/activate
pip install -r custom_nodes/ComfyUI-Easy-Use/requirements.txt
pip install -r custom_nodes/ComfyUI-SeedVR2/requirements.txt
pip install -r custom_nodes/ComfyUI-WanVideoWrapper/requirements.txt
pip install -r custom_nodes/ComfyUI-VideoHelperSuite/requirements.txt

# Place models (verify files exist in target directories)
ls -lh models/diffusion_models/anima-preview3-base.safetensors
ls -lh models/text_encoders/umt5-xxl-encoder-bf16.pth
ls -lh models/vae/qwen_image_vae.safetensors
ls -lh models/clip_vision/clip_vision_vit_h.safetensors
```

## Known Issue: transformers 5.7.0 KeyError 'flash_attn'

If ComfyUI logs show `KeyError: 'flash_attn'` on startup, or SeedVR2/ReActor
nodes appear as "missing" despite being cloned in `custom_nodes/`, the bug is
in `transformers/utils/import_utils.py`. The functions
`is_flash_attn_2_available()` and `is_flash_attn_4_available()` access
`PACKAGE_DISTRIBUTION_MAPPING["flash_attn"]` without checking the key exists.

**Quick patch:**
```bash
F=$(find /home/brierainz/comfy/ComfyUI/.venv -path "transformers/utils/import_utils.py")
sed -i 's/PACKAGE_DISTRIBUTION_MAPPING\["flash_attn"\]/PACKAGE_DISTRIBUTION_MAPPING.get("flash_attn", [])/g' "$F"
sed -i 's/PACKAGE_DISTRIBUTION_MAPPING\["flash_attn_interface"\]/PACKAGE_DISTRIBUTION_MAPPING.get("flash_attn_interface", [])/g' "$F"
```

Restart ComfyUI after patching. Check `pip show transformers` — once
transformers >=5.8 (or whichever version includes the upstream fix) is
installed, the patch is no longer needed.

## Live Debugging Tips

- Check ComfyUI startup log for `IMPORT FAILED` lines — they tell you which
  custom nodes failed and why.
- `ps aux | grep 'python.*main.py'` to find running ComfyUI processes.
- The startup log goes to the background process output, NOT a file — use
  `process log` or redirect: `nohup python3 main.py > /tmp/comfy.log 2>&1 &`.
- After installing custom nodes or pip packages, you MUST restart ComfyUI.
  Browser refresh alone is not enough.

## Known Issue: qwen_3_06b_base is NOT compatible with Anima 3.0

Previous Anima v02 workflows used `qwen_3_06b_base.safetensors` as the text
encoder. Anima 3.0 (WanVideo-based) requires `umt5-xxl-encoder-bf16.pth` instead.
The WanVideoWrapper's `LoadWanVideoT5TextEncoder` node validates the model name
with `if model_name != "umt5-xxl": raise ValueError(...)`. The qwen encoder
only works with Wan2.1 official models, not Anima.