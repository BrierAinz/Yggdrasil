# Content Improvement Pipeline

Post-generation processing pipeline for AI influencer content — upscaling,
color grading, watermarking, story templates, and Reel composition.

Developed for the Eir (@eir.creates) project on SDXL + LoRA + AnimateDiff.

## 1. Upscale Pipeline

Generated images are typically 832x1216 or 512x768 — too small for social
media. Two upscale approaches:

### A. RealESRGAN via ComfyUI (Best Quality — Single Image)

Uses the `RealESRGAN_x4plus.pth` model (64MB). Place in
`models/upscale_models/`. Workflow chain:

```
LoadImage → UpscaleModelLoader → ImageUpscaleWithModel → ImageScale → SaveImage
```

- RealESRGAN 4x upscale: 832x1216 → 3328x4864 (then crop to target)
- Works great for single images via ComfyUI API
- **Pitfall:** Batch submission via REST API can fail with 400 Bad Request
  (input validation race condition on file path references). Use PIL fallback
  for batch operations.

### B. PIL Lanczos (Bulk — Reliable for Batch)

```python
from PIL import Image

def upscale_lanczos(input_path, target_w, target_h, crop_mode='center'):
    """Upscale 4x with Lanczos, center-crop to aspect ratio, resize to target."""
    img = Image.open(input_path)
    # 4x upscale
    img = img.resize((img.width * 4, img.height * 4), Image.LANCZOS)
    # Center crop to target aspect ratio
    target_ratio = target_w / target_h
    current_ratio = img.width / img.height
    if current_ratio > target_ratio:
        new_w = int(img.height * target_ratio)
        left = (img.width - new_w) // 2
        img = img.crop((left, 0, left + new_w, img.height))
    else:
        new_h = int(img.width / target_ratio)
        top = (img.height - new_h) // 2
        img = img.crop((0, top, img.width, top + new_h))
    # Final resize
    img = img.resize((target_w, target_h), Image.LANCZOS)
    return img
```

**Target dimensions:**
- Instagram feed (4:5): 1080x1350
- Instagram stories/Reels (9:16): 1080x1920
- Square (1:1): 1080x1080
- Profile avatar: 1080x1080

Quality: PIL Lanczos at 4x → crop → resize is visually acceptable for
Instagram. Not as sharp as RealESRGAN but sufficient for social media and
works reliably in bulk without API dependency.

## 2. Post-Processing Pipeline

Python script (`scripts/postprocess.py`) that applies:

### Color Grades (4 presets)

| Grade | Character | RGB Shift | Contrast | Saturation |
|-------|-----------|-----------|----------|------------|
| warm | Golden warmth | +8R, +3G, -5B | +10% | +5% |
| cool | Nordic frost | -5R, -2G, +8B | +5% | -5% |
| moody | Deep shadows | -8R, -5G, -3B | +20% | -10% |
| vivid | High energy | +12R, +2G, +5B | +15% | +15% |

Applied via PIL `ImageEnhancer` + `ImageOps.point()` for tone mapping.

### Watermark

- Text: `@eir.creates`
- Position: bottom-right, 5px margin
- Font: 20px, white with 180px alpha (70% opacity)
- PIL `ImageDraw.text` with `ImageFont.truetype`

### Story Overlays (3 styles)

| Style | Description | Technique |
|-------|------------|-----------|
| minimal | Cool grade, thin line, small handle | Cool grade + `ImageDraw.line` + handle text |
| bold | Warm grade, large handle, thick border | Warm grade + wide border + bold text |
| frosted | Cool grade, frosted glass bottom | Cool grade + Gaussian blur bottom 40% + semi-transparent overlay |

Story dimensions: 1080x1920 (9:16).

### Border Effect

Optional thin white or colored border (1-3px) for carousel posts.

## 3. Story Template Generation

Story templates combine an upscaled image with an overlay:

```python
def create_story(image_path, style='minimal', handle='@eir.creates'):
    """Create a 1080x1920 story from a feed image."""
    img = Image.open(image_path).convert('RGB')
    # Apply color grade based on style
    if style == 'minimal':
        img = apply_grade(img, 'cool')
    elif style == 'bold':
        img = apply_grade(img, 'warm')
    elif style == 'frosted':
        img = apply_grade(img, 'cool')
    # Expand to 9:16 (crop from center or paste on background)
    img = crop_to_story(img, 1080, 1920)
    # Apply overlay
    if style == 'frosted':
        img = apply_frost_overlay(img, 0.4)  # bottom 40% blurred
    # Add handle watermark
    img = add_watermark(img, handle)
    return img
```

Each image produces 3 story variations (minimal/bold/frosted).
With 6 feed images, that's 18 story-adjacent templates.

## 4. Vertical Video for Reels/TikTok

### AnimateDiff Portrait Clip Generation

Generate individual short clips at portrait resolution, then compose into
Reels with crossfade transitions.

**Parameters (proven on RTX 3060 12GB):**
- Resolution: 512x768 (portrait, ~10-11GB VRAM with LoRA+AnimateDiff+SDXL)
- Frames: 24 (2 seconds at 12fps)
- Steps: 20
- CFG: 7.5
- LoRA strength: 0.8
- Trigger word in prompt + motion keywords

**Prompt template for clips:**
```
eir_niflheimr, [outfit/scene description], [motion keywords], 
masterpiece, best quality, dark fantasy
```

**Motion keywords:** hair flowing in wind, gentle head turn, snow falling,
candlelight flickering, aurora shifting, frost particles floating,
breathing animation, magical sparks drifting

**Negative prompt additions:** static, still, frozen, motionless

### Composing Reels from Clips

```python
# scripts/compose_reel.py — Reel composition pipeline
# Input: 3 WEBP clips (512x768, 24 frames, 12fps)
# Output: 1 MP4 Reel (1080x1920, ~9 seconds, crossfade transitions)

import subprocess
from PIL import Image

def compose_reel(clips, output_path, crossfade_frames=8):
    """
    1. Extract frames from each WEBP clip via Pillow
    2. Upscale frames to 1080x1920 (Lanczos)
    3. Apply crossfade transitions (8 frames = 0.67s overlap)
    4. Add @eir.creates watermark to each frame
    5. Encode to MP4 via ffmpeg:
       ffmpeg -y -framerate 12 -i frame_%05d.png -c:v libx264
       -pix_fmt yuv420p -preset medium -crf 23 -an output.mp4
    """
```

**ffmpeg binary on this system:** Uses `imageio-ffmpeg` bundled binary at
`~/comfy/ComfyUI/.venv/lib/python3.13/site-packages/imageio_ffmpeg/binaries/ffmpeg-linux-x86_64-v7.0.2`

**Structural breakdown (3-Reel strategy):**
- Reel 1 (aurora theme): clip_aurora + clip_temple + clip_snow
- Reel 2 (dark theme): clip_candle + clip_armor + clip_swords
- Reel 3 (nature theme): clip_forest + clip_lake + clip_mist
- Each clip: 2s, crossfade 0.67s, total ~9s per Reel

**Note:** Face consistency in AnimateDiff is 6-7/10 due to SDXL latent
drift. Acceptable for social media but not perfect. Future improvement:
FaceID or IPAdapter nodes for consistency.

## 5. Outfit Generation

Generate outfit variations by modifying the prompt while keeping the
trigger word and core physical description constant:

```
# Template:
eir_niflheimr, [same face/hair/body], wearing [OUTFIT_DESCRIPTION], 
[in SETTING], [LIGHTING], masterpiece, best quality, dark fantasy
```

**Outfit naming conventions:**
- Use memorable thematic names (Huntress, Alchemist, Shapeshifter)
- Number quality on generation: anatomy 1-10, outfit detail 1-10, face 1-10
- Discard anything below 7/10 on any axis

## 6. Face Consistency Verification

After generating a batch of images or video clips:

```python
def verify_face_consistency(image_dir, sample_count=5):
    """Extract and visually compare face regions across generations."""
    # 1. Extract face region from center of each image
    # 2. Compare: same eye color? same skin tone? same proportions?
    # 3. Rate 1-10: 7+ is acceptable for social media
    # 4. For video: extract every 5th frame, compare faces
```

**Qualitative checks:**
- Same eye color across all images? (violet for Eir)
- Same hair color and style? (silver-white with violet tips)
- Same skin tone? (pale)
- Same facial proportions? (nose, chin, cheeks)

**Expected consistency:** 7-9/10 for still images (LoRA), 6-7/10 for
AnimateDiff video clips (SDXL latent drift). For higher video consistency,
consider FaceID or IPAdapter (future work).

## 7. Content Inventory Structure

After post-processing, organize content into:

```
outputs/
├── upscaled/                    # Raw upscaled images (pre-post-processing)
│   ├── feed_*.jpg               # 1080x1350 (4:5 portrait)
│   └── story_*.png              # 1080x1920 (9:16 story)
├── final/                       # Post-processed, ready to post
│   ├── feed_warm/               # Warm color grade
│   ├── feed_moody/              # Moody color grade
│   ├── feed_cool/               # Cool color grade
│   ├── content_bank_warm/       # Carousel images, warm grade
│   ├── outfits_warm/            # Outfit variations, warm grade
│   ├── stories_minimal/         # Story templates, minimal style
│   ├── stories_bold/            # Story templates, bold style
│   ├── stories_frosted/         # Story templates, frosted style
│   └── profiles/                # Avatar, banner, story covers
├── outfits_ghi/                 # Raw outfit G/H/I generations
└── reel_clips/                  # AnimateDiff WEBP clips (512x768, 24 frames)
```

**File naming:** Use descriptive slugs with outfit/scene names.
Example: `eir_forest_glade_warm.jpg`, `eir_huntress_armor_moody.jpg`

**Quality targets:**
- Feed images: 8-9/10 anatomy, 1080x1350 JPG (340-512KB)
- Stories: 8-9/10 composition, 1080x1920 PNG
- Reels: 6-7/10 face consistency, 1080x1920 MP4 (9-15 seconds)
- Profiles: 9/10 face clarity, 1080x1080 PNG