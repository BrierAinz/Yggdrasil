#!/usr/bin/env python3
"""
Prepare LoRA dataset for Kohya sd-scripts SDXL training.
=========================================================
1. Resizes images to 1024x1024 (center crop + pad)
2. Creates metadata.json in Kohya format
3. Generates caption files if missing

Usage:
    python3 prepare_lora_dataset.py
"""
import json
import os
import sys
from pathlib import Path

try:
    from PIL import Image
except ImportError:
    print("Pillow required: pip install Pillow")
    sys.exit(1)

DATASET_DIR = Path(
    "/mnt/d/Proyectos/Yggdrasil/Muspelheim/AI-Influencer/assets/lora_dataset"
)
TARGET_SIZE = 1024
TRIGGER = "eir_niflheimr"


def resize_image(img: Image.Image, size: int = TARGET_SIZE) -> Image.Image:
    """Resize image to size x size, center-cropping to maintain aspect ratio."""
    # Center crop to square
    w, h = img.size
    min_dim = min(w, h)
    left = (w - min_dim) // 2
    top = (h - min_dim) // 2
    img = img.crop((left, top, left + min_dim, top + min_dim))
    # Resize to target
    img = img.resize((size, size), Image.LANCZOS)
    return img


def main():
    print(f"Preparing LoRA dataset in {DATASET_DIR}")
    print(f"Target size: {TARGET_SIZE}x{TARGET_SIZE}")
    print(f"Trigger word: {TRIGGER}")
    print()

    metadata = {}
    processed = 0

    for img_path in sorted(DATASET_DIR.glob("*.png")):
        name = img_path.name

        # Read caption
        caption_path = img_path.with_suffix(".txt")
        if caption_path.exists():
            caption = caption_path.read_text().strip()
        else:
            caption = f"{TRIGGER}, dark fantasy portrait, detailed face"

        # Ensure trigger word is in caption
        if TRIGGER not in caption:
            caption = f"{TRIGGER}, {caption}"

        # Resize image
        img = Image.open(img_path)
        if img.size != (TARGET_SIZE, TARGET_SIZE):
            img = resize_image(img, TARGET_SIZE)
            img.save(img_path, "PNG")
            print(f"  Resized: {name} ({img.size[0]}x{img.size[1]})")
        else:
            print(f"  OK: {name} ({img.size[0]}x{img.size[1]})")

        # Save updated caption
        caption_path.write_text(caption)

        # Kohya metadata format
        metadata[name] = {
            "train_resolution": [TARGET_SIZE, TARGET_SIZE],
            "caption": caption,
            "tags": caption.split(", "),
        }

        processed += 1

    # Write Kohya metadata.json
    meta_path = DATASET_DIR / "metadata.json"
    meta_path.write_text(json.dumps(metadata, indent=2))

    print(f"\nDone! {processed} images prepared")
    print(f"Metadata: {meta_path}")
    print(f"\nTrigger word: {TRIGGER}")
    print(f"Resolution: {TARGET_SIZE}x{TARGET_SIZE}")
    print(f"Images: {processed}")
    print(f"\nReady for Kohya LoRA training!")


if __name__ == "__main__":
    main()
