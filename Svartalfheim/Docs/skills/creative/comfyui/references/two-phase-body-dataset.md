# Two-Phase Body Dataset Generation (Flux GGUF + ReActor)

Validated approach for generating full-body LoRA training datasets on RTX 3060 12GB.

## Phase 1: Body Generation (Flux.1-dev GGUF Q8)

**Resolution:** 1536×640 (ultra-wide) — the ONLY tested resolution producing consistent head-to-toe full body.

**Workflow node chain:**
```
UnetLoaderGGUF(unet_name="flux1-dev-Q8_0.gguf")
→ DualCLIPLoader(clip_name1="t5xxl_fp8_e4m3fn.safetensors", clip_name2="clip_l.safetensors", type="flux")
→ VAELoader(vae_name="ae.safetensors")
→ ModelSamplingFlux(model=[10,0], max_shift=1.15, base_shift=0.5, width=1536, height=640)
→ CLIPTextEncode(text=prompt, clip=[11,0])           # positive
→ FluxGuidance(guidance=3.5, conditioning=[6,0])     # dev only; schnell uses 1.0
→ CLIPTextEncode(text="", clip=[11,0])                # empty negative
→ EmptyLatentImage(width=1536, height=640, batch_size=1)
→ KSampler(steps=20, cfg=1.0, sampler="euler", scheduler="simple", denoise=1.0,
            model=[13,0], positive=[14,0], negative=[16,0], latent_image=[5,0])
→ VAEDecode(samples=[7,0], vae=[12,0])
→ SaveImage(filename_prefix="ehyra_flux", images=[8,0])
```

**Key constraints:**
- KSampler negative MUST be linked CLIPTextEncode node `[16, 0]`, NOT empty array `[]`
- cfg=1.0 for Flux (NOT >1)
- steps=20 for dev, 4 for schnell
- guidance=3.5 for dev, 1.0 for schnell
- ~3-4 min per image on RTX 3060 12GB

**Prompting for curvy slim hourglass:**
Use explicit descriptors: "curvy slim hourglass figure with wide hips, full bust, and narrow defined waist, fit and toned body". Flux understands "curvy slim" correctly (unlike Pony V6 which interprets it as BBW).

**Known issues:**
- ~20-30% of images have deformed hands
- Occasional prompt misinterpretation at ultra-wide aspect ratio
- Not all poses produce usable compositions

## Phase 2: Face Swap (ReActor)

**ReActorFaceSwap API fields (verified via /object_info):**
```python
"enabled": True,                           # BOOLEAN
"swap_model": "inswapper_128.onnx",       # STRING
"source_image": ["11", 0],                 # IMAGE - linked LoadImage node
"input_image": ["10", 0],                  # IMAGE - linked LoadImage node
"facedetection": "retinaface_resnet50",     # STRING
"face_restore_model": "codeformer-v0.1.0.pth",  # STRING
"face_restore_visibility": 1.0,            # FLOAT 0.1-1.0
"codeformer_weight": 0.7,                   # FLOAT 0.0-1.0
"detect_gender_input": "no",               # STRING "no"/"female"/"male"
"detect_gender_source": "no",              # STRING
"source_faces_index": "0",                 # STRING, NOT list
"input_faces_index": "0",                  # STRING, NOT list
"console_log_level": 1                      # INT 0-2
```

**Detection failure rates by pose (at 1536×640):**
| Pose | ReActor Success | Notes |
|------|-----------------|-------|
| standing_confident | ✅ Yes | Face clearly visible |
| hand_on_hip | ⚠️ Sometimes | Depends on angle |
| walking_toward | ❌ Often fails | Face too small/angled |
| three_quarter | ❌ Fails | Profile view |
| arms_crossed | ❌ Fails | Face partially obscured |
| sitting_elegant | ❌ Fails | Face too small |
| leaning_wall | ❌ Fails | Face too small |
| turning_back | ❌ Fails | Back of head |

**Quality of successful swaps:**
- ~60% closely match the reference face
- ~40% look generic/plastic ("uncanny valley" — smooth poreless skin, melting mouth/chin)
- Net yield from 34 combinations: ~23 successful face swaps, ~14-17 training-quality images

## Required Dependencies
```bash
pip3 install --break-system-packages onnxruntime albumentations onnx ultralytics segment-anything
```
Restart ComfyUI after installing — custom nodes only register on startup.

**Required models:**
- `models/unet/flux1-dev-Q8_0.gguf`
- `models/text_encoders/t5xxl_fp8_e4m3fn.safetensors`
- `models/text_encoders/clip_l.safetensors`
- `models/vae/ae.safetensors`
- `models/insightface/inswapper_128.onnx`
- `models/insightface/models/buffalo_l/` (auto-downloaded)
- `models/facerestore_models/codeformer-v0.1.0.pth`

## Output Filtering

ReActor produces BOTH a full-resolution image AND a 512×512 2KB thumbnail. Always filter by file size:
```python
best = max(images, key=lambda p: os.path.getsize(p) if os.path.exists(p) else 0)
```
Or validate with PIL:
```python
from PIL import Image
img = Image.open(path)
if img.size != (1536, 640):  # thumbnail, not real image
    os.remove(path)
```

## Manual Curation Checklist

Before adding any generated image to a LoRA training dataset, verify:
- [ ] Face matches reference person (not generic/plastic)
- [ ] No deformed hands (extra/fused fingers, twisted wrists)
- [ ] Body type matches target (e.g., curvy slim, NOT BBW or petite)
- [ ] Scene matches prompt intent (no misinterpretation)
- [ ] No major composition artifacts
- [ ] Resolution is full-size (1536×640), not 512×512 thumbnail

Expect ~50-60% of generated images to pass curation from a typical batch.