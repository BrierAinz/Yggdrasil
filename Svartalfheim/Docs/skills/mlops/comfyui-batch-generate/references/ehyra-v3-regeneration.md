# Ehyra LoRA v3 — Session-Specific Regeneration Details

This file preserves the session-learned specifics from the Ehyra v3 photorealistic dataset regeneration. The *generalized* pipeline is in the parent SKILL.md; this file contains only the Ehyra-specific configuration, file paths, and bugs discovered during sessions.

## Status

V5 BODY GENERATION — Two-phase approach validated. RealVisXL V4 FAILED (same portrait bias as Juggernaut). Pony V6 + BBW tags + wide ratio (1344x768) = only working solution for voluptuous full-body. Script v5 created, test mode bug fixed (BBW tags missing in test prompt). Ready for full Phase 1 execution.

## Critical Findings

### IPAdapter FaceID Cannot Produce Full-Body Images

Extensive testing confirmed IPAdapter FaceID dominates composition regardless of settings:

| Config | Weight | Result |
|--------|--------|--------|
| Default | 0.80 | Face-focused portrait crop |
| Reduced | 0.65 | Three-quarter crop, face-dominated |
| Low | 0.35 | Mid-thighs crop, slim body |
| Very low + composition | 0.30 (end_at=0.40, weight_type="composition") | Still three-quarter, slim |
| Juggernaut XL no IPAdapter | N/A | Mid-thigh crop, slim — portrait bias in checkpoint |
| Pony V6 no IPAdapter | N/A | Full body (10/10) but anime style, slim |

**Solution**: Two-phase approach — generate bodies with Pony V6 + BBW tags (Phase 1), then ReActor face swap (Phase 2).

### Aspect Ratio is Critical

| Ratio | Full Body Score | Notes |
|-------|----------------|-------|
| 1344×768 (WIDE) | 8-10/10 | **ONLY working ratio** |
| 768×1344 (TALL) | 0-1/10 | Crops at mid-thigh, ALWAYS |
| 1024×1024 (SQUARE) | 1/10 | Crops at mid-thigh |
| 1024×1536 (EXTRA-TALL) | 0/10 | Still crops mid-thigh |

This is a fundamental SDXL composition bias. No amount of prompt engineering overcomes it at non-wide ratios.

### Checkpoint Testing Results

| Checkpoint | Full-body? | Voluptuous? | Style | Notes |
|------------|-----------|-------------|-------|-------|
| Juggernaut XL v9 | No (mid-thigh) | No (slim) | Photorealistic | Inherent portrait bias, even at 1024x1536 |
| Pony V6 XL + BBW tags | Yes (8-10/10) | Yes (8-9/10) | Semi-anime | **ONLY working config for voluptuous full-body** |
| Pony V6 XL (no BBW tags) | Yes (8-10/10) | No (slim 1/10) | Anime | Tags are mandatory |
| RealVisXL V4.0 | No (2/10) | No (2/10) | Photorealistic | Same portrait bias as Juggernaut — FAILED |

### BBW Tags are Mandatory

Pony V6 has an inherent slim bias. Without explicit body-type tags, output is slim regardless of prompt language ("curves", "hourglass", "generous figure"). Minimum effective tag set:

**Positive**: `bbw, thick, very wide hips, thick thighs` (must appear early in prompt, before clothing/setting)
**Negative**: `slim, thin, skinny, narrow hips, small breasts, flat chest`
**Quality tags**: `score_9, score_8_up, score_7_up, score_6_up, source_photo, source_5_more`

## File Paths

| Item | Path |
|------|------|
| Body gen script (v5, current) | `/home/brierainz/comfy/ai-toolkit/scripts/regenerate_ehyra_body_v5.py` |
| Face gen script | `/home/brierainz/comfy/ai-toolkit/scripts/regenerate_ehyra_v3.py` |
| Face caption script | `/home/brierainz/comfy/ai-toolkit/scripts/caption_ehyra.py` |
| Body gen caption script | `/home/brierainz/comfy/ai-toolkit/scripts/caption_ehyra_body_gen.py` |
| Workflow JSON | `/home/brierainz/comfy/ai-toolkit/scripts/ehyra_faceid_workflow.json` |
| Training dataset | `/home/brierainz/comfy/ai-toolkit/dataset/ehyra_v3_train/` |
| Training config | `/home/brierainz/comfy/ai-toolkit/config/train_lora_ehyra_v3.yaml` |
| Face generated (source) | `/home/brierainz/comfy/ai-toolkit/dataset/images/ehyra_generated_v2/` (61 imgs) |
| Body v5 Phase 1 output | `/home/brierainz/comfy/ai-toolkit/dataset/images/ehyra_v5_phase1_pony/` |
| Body v5 Phase 2 output | `/home/brierainz/comfy/ai-toolkit/dataset/images/ehyra_v5_phase2_faceswap/` |
| Body v5 final output | `/home/brierainz/comfy/ai-toolkit/dataset/images/ehyra_generated_v5_body/` |
| Body references | `/home/brierainz/comfy/ai-toolkit/dataset/images/ehyra_reference_body/` (17 imgs) |
| Face references | `/home/brierainz/comfy/ai-toolkit/dataset/images/ehyra_reference/` (22 photos) |
| Face reference for ReActor | `/home/brierainz/comfy/ComfyUI/input/ehyra_face_ref.jpg` |
| Metadata | `/home/brierainz/comfy/ai-toolkit/dataset/metadata/` |
| Pony V6 checkpoint | `/home/brierainz/comfy/ComfyUI/models/checkpoints/` (Pony V6 XL) |
| RealVisXL V4.0 checkpoint | `/home/brierainz/comfy/ComfyUI/models/checkpoints/RealVisXL_V4.0.safetensors` (6.5GB, FAILED) |
| inswapper_128.onnx | `/home/brierainz/comfy/ComfyUI/models/insightface/inswapper_128.onnx` (529MB) |
| InsightFace models | `/home/brierainz/comfy/ComfyUI/models/insightface/models/buffalo_l/` |
| Face restore models | `/home/brierainz/comfy/ComfyUI/models/facerestore_models/` |
| ComfyUI output dir | `/home/brierainz/comfy/ComfyUI/output/` |

## Dataset Current State

| Category | Images | Captions | Source |
|----------|--------|----------|--------|
| Face generated | 61 | 61 | IPAdapter FaceID + 22 ref photos |
| Body generated (v2, DELETED) | 0 | 0 | Was 56, deleted for regeneration |
| Body generated (v5, pending) | ~34 | ~34 | Pony V6 + BBW tags → ReActor face swap |
| Body references | 17 | 17 | Proyecto A originals (filtered) |
| **Total (after v5)** | **~112** | **~112** | Target: 129+ after full pipeline |

## ComfyUI Workflow Config (v5 — Two-Phase Body Generation)

### Phase 1 (Pony V6 Body Generation — NO IPAdapter)
- **Checkpoint**: Pony V6 XL
- **Aspect ratio**: 1344×768 (WIDE — critical for full body)
- **IPAdapter**: NONE — pure prompt-driven generation
- **Steps**: 30, sampler: dpmpp_2m, scheduler: karras, CFG: 7.0
- **Positive prompt template**: `score_9, score_8_up, score_7_up, score_6_up, source_photo, source_5_more, bbw, thick, very wide hips, thick thighs, 3hyr4_p3r50n, {clothing}, {setting}, full body visible, standing, head to toe`
- **Negative prompt**: `score_6, score_5, score_4, source_pony, source_furry, source_cartoon, 3d, realistic, photorealistic, slim, thin, skinny, narrow hips, small breasts, flat chest, close-up, portrait, cropped`
- **Categories**: 8 (fullbody_outfit, fashion_editorial, casual_day, athletic_wear, boudoir_intimate, outdoor_nature, formal_evening, swimwear_beach) × 2 refs each × 1 seed = 16 body variations × ~2 refs = ~34 images
- **CATEGORIES_PER_REF**: 2, **SEEDS_PER_CATEGORY**: 1

### Phase 2 (ReActor Face Swap)
- **Node**: ReActorFastFaceSwap or ReActorFaceSwap
- **Swap model**: `inswapper_128.onnx`
- **Face detection**: `retinaface_resnet50`
- **Face restore**: `codeformer-v0.1.0.pth`
- **Source image**: `ehyra_face_ref.jpg` (cropped face from best reference)
- **Input image**: Output from Phase 1

## Training Config (Ehyra-specific)

- **Base model**: Juggernaut-XL_v9_RunDiffusionPhoto_v2.safetensors
- **Trigger word**: `3hyr4_p3r50n`
- **Steps**: 4000, LR: 8e-5 (cosine), LoRA rank: 32, alpha: 16
- **Batch size**: 1, gradient checkpointing: true, xformers: true
- **EMA**: decay 0.99
- **Resolution**: [768, 1024]
- **Estimated time**: ~2–3 hours on RTX 3060 12GB

## Bugs Discovered During Ehyra Sessions

1. **ComfyUI v0.20+ status check**: Returns `{"status_str": "success", "completed": true}`, NOT `status["status"]`. Check `completed=True` or `status_str=="success"`.

2. **Python `hash()` non-determinism**: `hash()` is randomized via PYTHONHASHSEED. Use `hashlib.md5()` for cross-run determinism.

3. **FaceID PLUS V2 crashes**: Requires ViT-bigG-14 clip vision model (1664 dims). Without it, you get a dims mismatch error (1280 vs 1664). Use plain FaceID only.

4. **CLIP vision filename**: IPAdapter regex-matches on filename pattern. The ViT-H-14 model must be named `ViT-H-14.s32B.b79K.safetensors` — renaming breaks the match.

5. **FaceID LoRA symlink**: Required at `models/ipadapter/faceid.sdxl.lora.safetensors` → `ip-adapter-faceid_sdxl_lora.safetensors`.

6. **InsightFace no-face failures**: References showing the subject looking down or with face partially hidden (refs 10, 12) fail InsightFace detection — no fix, exclude those refs.

7. **`.jpeg` vs `.jpg` extension mismatch**: Reference images had mixed extensions. ComfyUI handles both, but Python glob/pattern matching may not. Normalize early.

8. **Filename underscore parsing**: Body ref filenames like `20250427_071835.jpg` contain underscores. When extracting categories from output filenames, parse from the END (longest match first) rather than splitting on underscores from the front.

9. **Queue flooding batch**: v1/v2 scripts submitted all prompts at once causing 7–8 min per image. v3 drains the queue between submissions — reduces to ~34s per image.

10. **Qwen3-VL + ComfyUI VRAM conflict**: Both need ~8–9GB on RTX 3060 12GB. Must stop ComfyUI before running captioning.

11. **Qwen3VL processor bug**: `processor.batch_text_decoder()` does NOT exist on Qwen3VLProcessor. Use `processor.batch_decode()`.

12. **Qwen3VL image path format**: Use plain `image_path` string in message content, NOT `f"file://{image_path}"`.

13. **Double prefix in filenames**: Script generated `ehyra_ehyra_ref_01_closeup_882791` — removed redundant ref_base from prefix.

14. **InsightFace "No face detected" on large portraits**: Refs 10 and 12 (2304×4096) failed because the face is too small relative to the image. Center-cropping doesn't help if face isn't centered.

15. **Python stdout buffering in background processes**: Use `python -u script.py` or `PYTHONUNBUFFERED=1` + `sys.stdout.reconfigure(line_buffering=True)`.

16. **PyTorch/IPAdapter tensor dumps flood stdout**: ComfyUI/IPAdapter model loading dumps massive tensor info to stdout, drowning custom progress output.

17. **InsightFace standalone cannot use CUDA**: Outside ComfyUI's process, InsightFace falls back to CPUExecutionProvider. Face detection works but slower; loading ipadapter models will fail entirely.

18. **IPAdapter FaceID composition dominance**: IPAdapter FaceID forces portrait/face-focused composition at every tested weight (0.30-0.90). Cannot produce full-body images. Use two-phase: Pony V6 body → ReActor face swap.

19. **Juggernaut XL v9 inherent slim portrait bias**: Even without IPAdapter, Juggernaut XL generates mid-thigh slim portraits. NOT suitable for body generation.

20. **Pony V6 XL with BBW tags = voluptuous full body solution**: 1344×768 wide ratio + "bbw, thick, very wide hips, thick thighs" = 8-9/10 voluptuous, 8-10/10 full body. WITHOUT tags → slim. ONLY working config found.

21. **RealVisXL V4.0 FAILED for body generation**: Same portrait/slim bias as Juggernaut XL (full_body 2/10, voluptuous 2/10). Do NOT use for body datasets.

22. **`embeds_scaling` format bug**: Parameter must be `"V only"` (with space), NOT `"V_ONLY"`. ComfyUI returns 400 for underscore format.

23. **IPAdapter Plus Face model incompatibility**: `ip-adapter-plus-face_sdxl_vit-h.safetensors` causes tensor size mismatch with `IPAdapterUnifiedLoader`. Use plain `ip-adapter-faceid_sdxl.bin`.

24. **ReActor inswapper_128.onnx must be in models/insightface/**: NOT `models/reactor/`. Download from `https://huggingface.co/ezioruan/inswapper_128.onnx/resolve/main/inswapper_128.onnx`. Verify with: `python3 -c "import insightface; print(insightface.model_zoo.get_model('inswapper_128.onnx'))"` from ComfyUI venv.

25. **Script v5 test mode bug**: Test prompt at line 593 lacked BBW tags and "full body visible" in setting. Must include `bbw, thick` in positive prompt test template or results appear slim (voluptuous 1-3/10).

## Commands

```bash
# Start ComfyUI (for generation)
cd /home/brierainz/comfy/ComfyUI && source .venv/bin/activate && python main.py --listen 127.0.0.1 --port 8188

# Body generation v5 (two-phase: Pony V6 body + ReActor face swap)
cd /home/brierainz/comfy/ai-toolkit
PYTHONUNBUFFERED=1 .venv/bin/python3 -u scripts/regenerate_ehyra_body_v5.py --phase 1  # ~34 images, ~30-45 min
PYTHONUNBUFFERED=1 .venv/bin/python3 -u scripts/regenerate_ehyra_body_v5.py --phase 2  # face swap
PYTHONUNBUFFERED=1 .venv/bin/python3 -u scripts/regenerate_ehyra_body_v5.py --phase 3  # caption + copy to training dir

# Face generation (~40 min for 66 images)
cd /home/brierainz/comfy/ai-toolkit
PYTHONUNBUFFERED=1 python3 -u scripts/regenerate_ehyra_v3.py 2>&1

# Captioning (MUST stop ComfyUI first)
cd /home/brierainz/comfy/ComfyUI && source .venv/bin/activate
PYTHONUNBUFFERED=1 python3 -u /home/brierainz/comfy/ai-toolkit/scripts/caption_ehyra.py
PYTHONUNBUFFERED=1 python3 -u /home/brierainz/comfy/ai-toolkit/scripts/caption_ehyra_body_gen.py

# Train LoRA v3
cd /home/brierainz/comfy/ai-toolkit && python run.py config/train_lora_ehyra_v3.yaml
```