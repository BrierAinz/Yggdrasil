# PuLID-Flux Troubleshooting & Pitfalls

## Critical: Missing `w600k_r50.onnx` in antelopev2

**Symptom:** `ApplyPulidFlux` node crashes with:
```
TypeError: expected np.ndarray (got NoneType)
```
This means `face_info.embedding` is `None` — InsightFace detected a face but
couldn't extract an embedding because the recognition model file is missing.

**Root cause:** The `antelopev2` model pack requires `w600k_r50.onnx` (174 MB)
for face embedding extraction. It is NOT included by default in many
antelopev2 downloads and is gated on HuggingFace.

**Fix:** Copy from the `buffalo_l` pack (already installed alongside insightface):
```bash
cp models/insightface/models/buffalo_l/w600k_r50.onnx \
   models/insightface/models/antelopev2/w600k_r50.onnx
```

**Verify:**
```python
from insightface.app import FaceAnalysis
app = FaceAnalysis(name='antelopev2', root='models/insightface',
                   providers=['CPUExecutionProvider'])
app.prepare(ctx_id=0, det_size=(640, 640))
faces = app.get(cv2.imread('face_reference.png'))
print(faces[0].embedding.shape)  # Should be (512,) — NOT None
```

## `PulidFluxInsightFaceLoader`: Use `provider="CPU"` on Python 3.13+

`onnxruntime-gpu` does NOT provide `CUDAExecutionProvider` on Python 3.13+
(wheels not available). You must set `provider: "CPU"` in the API workflow
JSON. Using `"CUDA"` will crash or fail silently.

Check available providers:
```python
import onnxruntime
print(onnxruntime.get_available_providers())
# ['AzureExecutionProvider', 'CPUExecutionProvider']  ← no CUDA
```

This is slower but functional (~8 min per 1024x1024 image on RTX 3060).

## `PulidFluxEvaClipLoader`: Takes No Inputs

The `PulidFluxEvaClipLoader` node has **no required or optional inputs** in
the current version. The EVA-CLIP model path is auto-detected from
`models/clip/EVA02_CLIP_L_336_psz14_s6B.pt`. Setting `eva_file` as an input
will cause HTTP 400.

```json
"6": {
  "class_type": "PulidFluxEvaClipLoader",
  "inputs": {}
}
```

## KSampler Requires Explicit `denoise`

The `KSampler` node requires `denoise` in the API JSON. Omitting it causes
HTTP 400 with no helpful error message. Always include:

```json
"KSampler": { "inputs": { "denoise": 1.0, ... } }
```

## GGUFLoaderKJ Requires All Parameters

Do NOT rely on defaults in API mode. Provide every parameter explicitly:

```json
"GGUFLoaderKJ": {
  "inputs": {
    "model_name": "flux1-dev-Q8_0.gguf",
    "extra_model_name": "none",
    "dequant_dtype": "default",
    "patch_dtype": "default",
    "patch_on_device": false,
    "enable_fp16_accumulation": false,
    "attention_override": "none"
  }
}
```

## VRAM Requirements (RTX 3060 12 GB)

- Flux.1 Dev Q8_0 GGUF: ~11.5 GB VRAM
- + PuLID models (IDFormer + EVA-CLIP + InsightFace): adds ~2 GB during processing
- Total peak: ~13 GB → system will offload/unload as needed, but generation
  is slower (~8 min/image with CPU InsightFace)
- Works but is tight. Close other GPU consumers before generating.

## Required Models Checklist

| Model | Path | Source |
|-------|------|--------|
| Flux.1 Dev Q8_0 GGUF | `models/unet/flux1-dev-Q8_0.gguf` | HuggingFace |
| T5-XXL CLIP | `models/clip/t5xxl_fp8_e4m3fn.safetensors` | HuggingFace |
| CLIP-L | `models/clip/clip_l.safetensors` | HuggingFace |
| FLUX VAE | `models/vae/ae.safetensors` | HuggingFace |
| PuLID Flux model | `models/pulid/pulid_flux_v0.9.1.safetensors` | HuggingFace |
| EVA-CLIP | `models/clip/EVA02_CLIP_L_336_psz14_s6B.pt` | HuggingFace |
| antelopev2 (4 files) | `models/insightface/models/antelopev2/` | InsightFace repo |
| **w600k_r50.onnx** | `models/insightface/models/antelopev2/` | Copy from `buffalo_l/` |
| inswapper (optional) | `models/insightface/inswapper_128.onnx` | InsightFace repo |

## ComfyUI v0.20.1 Breaks PuLID's `forward_orig` Patch

**Symptom:** `ApplyPulidFlux` crashes with:
```
TypeError: forward_orig() got an unexpected keyword argument 'timestep_zero_index'
```
This happens because ComfyUI v0.20.1 added new parameters (`timestep_zero_index`,
`transformer_options`) to the Flux model's `forward_orig` method, but the PuLID
node patches `forward_orig` with a version that doesn't accept these params.

**Root cause:** In `~/comfy/ComfyUI/custom_nodes/ComfyUI-PuLID-Flux/pulidflux.py`,
the patched `forward_orig` function signature (around line 65) doesn't include
the new parameters that v0.20.1's Flux model now passes to it.

**Fix:** Patch `pulidflux.py` to accept the new parameters:
```bash
# Find and edit the forward_orig function signature in pulidflux.py
# Change:  def forward_orig(self, ...):
# To:      def forward_orig(self, ..., timestep_zero_index=None, transformer_options=None, **kwargs):
```
More precisely, add `timestep_zero_index=None`, `transformer_options=None`, and
`**kwargs` to the `forward_orig` method signature so it gracefully accepts any
new positional or keyword args that future ComfyUI versions may pass.

**After patching, restart ComfyUI** — the change takes effect on import.

This fix is needed on **ComfyUI v0.20.1+** with **balazik/ComfyUI-PuLID-Flux**
(as of May 2026). Once the PuLID repo merges a fix, this patch can be removed.

## ComfyUI Restarts Kill Background Queues

When debugging iterative bugs (e.g., PuLID), you typically need to restart
ComfyUI. Any queued/running prompts are **lost** — they'll report `error`
status on next history check. Always wait for in-flight jobs to finish
or explicitly cancel them before restarting.

## Sending Large Images via Telegram

Telegram has strict media size limits. 1024×1024 PNGs (~500KB-2MB) often
timeout on send. Compress to 512×512 JPEG (~15-50KB) before sending:

```python
from PIL import Image
thumb = Image.open('output.png').resize((512, 512), Image.LANCZOS)
thumb.save('thumb.jpg', 'JPEG', quality=85)
# Send thumb.jpg via MEDIA:
```

## Node: balazik/ComfyUI-PuLID-Flux

This is the correct ComfyUI custom node repo for PuLID with Flux:
```
https://github.com/balazik/ComfyUI-PuLID-Flux
```

Other PuLID repos (e.g., cubiq) may have different node class names or params.
The nodes registered by `balazik` are:
- `ApplyPulidFlux`
- `PulidFluxModelLoader`
- `PulidFluxInsightFaceLoader`
- `PulidFluxEvaClipLoader`
- `easy pulIDApply`
- `pulIDApplyADV`