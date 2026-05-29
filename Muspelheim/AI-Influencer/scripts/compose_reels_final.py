#!/usr/bin/env python3
"""Compose 3 Reels from 9 vertical clips with crossfade + watermark."""
import sys
sys.path.insert(0, str(__import__('pathlib').Path.home() / "comfy/ComfyUI/.venv/lib/python3.13/site-packages"))

from PIL import Image, ImageDraw, ImageFont, ImageEnhance
from pathlib import Path
import imageio
import numpy as np

PROJECT_DIR = Path("/mnt/d/Proyectos/Yggdrasil/Muspelheim/AI-Influencer")
CLIPS_DIR = PROJECT_DIR / "outputs/reel_clips"
OUTPUT_DIR = PROJECT_DIR / "outputs/reels"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

def webp_to_frames(webp_path: Path) -> list:
    img = Image.open(webp_path)
    frames = []
    try:
        while True:
            frames.append(img.convert("RGB").copy())
            img.seek(img.tell() + 1)
    except EOFError:
        pass
    return frames

def add_watermark(img: Image.Image, text: str = "@eir.creates") -> Image.Image:
    font_paths = [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
        "/mnt/c/Windows/Fonts/arialbd.ttf",
    ]
    font = None
    for fp in font_paths:
        if Path(fp).exists():
            try:
                font = ImageFont.truetype(fp, 28)
                break
            except Exception:
                continue
    if font is None:
        font = ImageFont.load_default()
    
    overlay = Image.new("RGBA", img.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)
    bbox = draw.textbbox((0, 0), text, font=font)
    tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
    pos = (img.width - tw - 20, img.height - th - 20)
    draw.text((pos[0] + 1, pos[1] + 1), text, font=font, fill=(0, 0, 0, 80))
    draw.text(pos, text, font=font, fill=(255, 255, 255, 130))
    return Image.alpha_composite(img.convert("RGBA"), overlay).convert("RGB")

def apply_warm(img: Image.Image) -> Image.Image:
    r, g, b = img.split()
    r = r.point(lambda x: min(255, x + 15))
    g = g.point(lambda x: min(255, x + 5))
    b = b.point(lambda x: max(0, x - 10))
    return Image.merge("RGB", (r, g, b))

def apply_cool(img: Image.Image) -> Image.Image:
    r, g, b = img.split()
    r = r.point(lambda x: max(0, x - 10))
    g = g.point(lambda x: min(255, x + 2))
    b = b.point(lambda x: min(255, x + 15))
    return Image.merge("RGB", (r, g, b))

def apply_moody(img: Image.Image) -> Image.Image:
    img = ImageEnhance.Color(img).enhance(0.7)
    img = ImageEnhance.Contrast(img).enhance(1.3)
    img = ImageEnhance.Brightness(img).enhance(0.85)
    return img

GRADE_FUNCS = {"warm": apply_warm, "cool": apply_cool, "moody": apply_moody}

# Define 3 reels from clips
reels = [
    {
        "name": "reel_northern_mystique",
        "clips": ["reel1_aurora.webp", "reel1_temple.webp", "reel1_snow.webp"],
        "grade": "warm",
    },
    {
        "name": "reel_dark_elegance",
        "clips": ["reel2_candle.webp", "reel2_armor.webp", "reel2_mirror.webp"],
        "grade": "moody",
    },
    {
        "name": "reel_wild_spirit",
        "clips": ["reel3_huntress.webp", "reel3_cozy.webp", "reel3_lake.webp"],
        "grade": "cool",
    },
]

TRANSITION_FRAMES = 8
FPS = 12
TARGET_SIZE = (1080, 1920)

for reel in reels:
    print(f"\n=== Composing: {reel['name']} ===")
    
    # Load clips
    clip_frames = []
    for clip_name in reel["clips"]:
        clip_path = CLIPS_DIR / clip_name
        if not clip_path.exists():
            print(f"  SKIP: {clip_name} not found")
            continue
        frames = webp_to_frames(clip_path)
        clip_frames.append(frames)
        print(f"  Loaded {clip_name}: {len(frames)} frames")
    
    if len(clip_frames) < 2:
        print(f"  ERROR: Need at least 2 clips, got {len(clip_frames)}")
        continue
    
    # Compose with crossfade transitions
    grade_fn = GRADE_FUNCS.get(reel["grade"])
    final_frames = []
    
    for i, frames in enumerate(clip_frames):
        # Add transition from previous clip
        if i > 0:
            prev_frames = clip_frames[i - 1]
            for t in range(TRANSITION_FRAMES):
                alpha = t / TRANSITION_FRAMES
                prev_frame = prev_frames[-1].resize(TARGET_SIZE, Image.LANCZOS)
                curr_frame = frames[0].resize(TARGET_SIZE, Image.LANCZOS)
                blended = Image.blend(prev_frame, curr_frame, alpha)
                final_frames.append(blended)
        
        # Add clip frames (resize to target)
        for f in frames:
            resized = f.resize(TARGET_SIZE, Image.LANCZOS)
            final_frames.append(resized)
    
    # Apply color grading
    if grade_fn:
        print(f"  Applying {reel['grade']} grade to {len(final_frames)} frames...")
        final_frames = [grade_fn(f) for f in final_frames]
    
    # Add watermark to last 30% of frames
    wm_start = int(len(final_frames) * 0.7)
    for i in range(wm_start, len(final_frames)):
        final_frames[i] = add_watermark(final_frames[i])
    
    # Write MP4
    out_path = OUTPUT_DIR / f"{reel['name']}.mp4"
    writer = imageio.get_writer(
        str(out_path),
        fps=FPS,
        codec="libx264",
        output_params=["-pix_fmt", "yuv420p"],
    )
    for frame in final_frames:
        writer.append_data(np.array(frame))
    writer.close()
    
    duration = len(final_frames) / FPS
    size_mb = out_path.stat().st_size / (1024 * 1024)
    print(f"  DONE: {out_path.name} ({duration:.1f}s, {len(final_frames)} frames, {size_mb:.1f} MB)")

print("\n=== All Reels composed! ===")
for f in sorted(OUTPUT_DIR.glob("*.mp4")):
    size_mb = f.stat().st_size / (1024 * 1024)
    print(f"  {f.name}: {size_mb:.1f} MB")