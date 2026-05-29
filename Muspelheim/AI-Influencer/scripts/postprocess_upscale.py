#!/usr/bin/env python3
"""Post-process upscaled images: center-crop to 4:5 and resize to 1080x1350."""
from PIL import Image
from pathlib import Path

src_dir = Path.home() / "comfy/ComfyUI/output"
out_dir = Path("/mnt/d/Proyectos/Yggdrasil/Muspelheim/AI-Influencer/outputs/upscaled")
out_dir.mkdir(parents=True, exist_ok=True)

TARGET_W, TARGET_H = 1080, 1350  # 4:5 portrait IG format

files = sorted(src_dir.glob("eir_upscl_*.png"))
print(f"Processing {len(files)} files")

for f in files:
    img = Image.open(f)
    orig_w, orig_h = img.size

    # Smart center-crop to 4:5 aspect ratio
    target_ratio = TARGET_W / TARGET_H  # 0.8
    orig_ratio = orig_w / orig_h

    if orig_ratio > target_ratio:
        new_w = int(orig_h * target_ratio)
        left = (orig_w - new_w) // 2
        img = img.crop((left, 0, left + new_w, orig_h))
    else:
        new_h = int(orig_w / target_ratio)
        top = (orig_h - new_h) // 2
        img = img.crop((0, top, orig_w, top + new_h))

    img = img.resize((TARGET_W, TARGET_H), Image.LANCZOS)

    idx = int(f.stem.split("_")[2]) - 1
    out_name = f"eir_upscl_{idx+1:02d}_portrait_1080x1350.png"
    final = out_dir / out_name
    img.save(final, "PNG", optimize=True)
    print(f"  {f.name}: {orig_w}x{orig_h} -> {TARGET_W}x{TARGET_H} -> {final.name}")

    # Also save as JPEG for web (smaller)
    out_jpg = final.with_suffix(".jpg")
    img.save(out_jpg, "JPEG", quality=95, optimize=True)
    print(f"    JPG: {out_jpg.name}")

print("All done!")
