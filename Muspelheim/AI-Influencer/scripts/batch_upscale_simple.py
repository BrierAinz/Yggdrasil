#!/usr/bin/env python3
"""
Simple batch upscale using PIL (Lanczos resampling) — no ComfyUI needed.
For production-quality 4x upscale, use ComfyUI with RealESRGAN manually.

This script handles the remaining inventory that the ComfyUI batch missed.
Uses high-quality Lanczos resampling which is sufficient for social media.
"""
from PIL import Image, ImageEnhance, ImageFilter
from pathlib import Path
import sys

PROJECT_DIR = Path("/mnt/d/Proyectos/Yggdrasil/Muspelheim/AI-Influencer")
OUTPUT_DIR = PROJECT_DIR / "outputs/upscaled"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# Target sizes by category
TARGETS = {
    "content_bank_v2": (1080, 1350, "4:5 portrait"),
    "stories_highlights_v2": (1080, 1920, "9:16 story"),
    "profile_assets": (1080, 1080, "1:1 square"),
    "profile_variations": (1080, 1080, "1:1 square"),
    "outfits_ghi": (1080, 1350, "4:5 portrait"),
}

# Source dirs
sources = [PROJECT_DIR / "outputs" / d for d in TARGETS.keys()]

def smart_resize(img: Image.Image, target_w: int, target_h: int) -> Image.Image:
    """Center-crop to target aspect ratio then resize with Lanczos."""
    orig_w, orig_h = img.size
    target_ratio = target_w / target_h
    orig_ratio = orig_w / orig_h

    # Center-crop to match target aspect ratio
    if orig_ratio > target_ratio:
        # Original is wider — crop sides
        new_w = int(orig_h * target_ratio)
        left = (orig_w - new_w) // 2
        img = img.crop((left, 0, left + new_w, orig_h))
    elif orig_ratio < target_ratio:
        # Original is taller — crop top/bottom
        new_h = int(orig_w / target_ratio)
        top = (orig_h - new_h) // 2
        img = img.crop((0, top, orig_w, top + new_h))

    # Resize with Lanczos
    if img.size != (target_w, target_h):
        img = img.resize((target_w, target_h), Image.LANCZOS)

    return img

total = 0
done = 0
skipped = 0

for folder_name, (tw, th, desc) in TARGETS.items():
    src_dir = PROJECT_DIR / "outputs" / folder_name
    if not src_dir.exists():
        print(f"SKIP: {folder_name} directory not found")
        continue

    print(f"\n=== {folder_name} -> {tw}x{th} ({desc}) ===")

    for png in sorted(src_dir.glob("*.png")):
        total += 1
        out_name = f"{folder_name}_{png.stem}_upscaled.jpg"
        out_path = OUTPUT_DIR / out_name

        if out_path.exists():
            skipped += 1
            print(f"  SKIP (exists): {out_name}")
            continue

        try:
            img = Image.open(png).convert("RGB")
            resized = smart_resize(img, tw, th)
            resized.save(out_path, "JPEG", quality=92)
            kb = out_path.stat().st_size / 1024
            print(f"  OK: {out_name} ({kb:.0f} KB)")
            done += 1
        except Exception as e:
            print(f"  ERROR: {png.name}: {e}")

print(f"\n{'='*60}")
print(f"Batch upscale complete: {done} done, {skipped} skipped, {total - done - skipped} failed")
print(f"Output: {OUTPUT_DIR}")
