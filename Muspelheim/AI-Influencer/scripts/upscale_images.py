#!/usr/bin/env python3
"""
Eir Image Upscaler — Batch upscale images via ComfyUI API + RealESRGAN_x4plus.

Pipeline:
  1. Load original image (832x1216 typically)
  2. Upscale 4x via RealESRGAN → 3328x4864
  3. Resize to 1080x1350 (IG portrait format) via Pillow
  4. Save final output

Usage:
  python upscale_images.py [--input DIR] [--output DIR] [--limit N]
"""
import argparse
import io
import json
import os
import shutil
import sys
import time
import urllib.request
from pathlib import Path

COMFY_URL = "http://localhost:8188"
PROJECT_DIR = Path(__file__).resolve().parent.parent
DEFAULT_INPUT = PROJECT_DIR / "outputs"
DEFAULT_OUTPUT = PROJECT_DIR / "outputs" / "upscaled"

# IG-optimized target sizes
TARGET_SIZES = {
    "portrait": (1080, 1350),   # 4:5 portrait (IG feed)
    "square": (1080, 1080),     # 1:1 square
    "story": (1080, 1920),     # 9:16 story/reel
}


def queue_prompt(workflow: dict) -> str:
    """Queue a workflow and return the prompt_id."""
    data = json.dumps({"prompt": workflow}).encode("utf-8")
    req = urllib.request.Request(f"{COMFY_URL}/prompt", data=data, headers={"Content-Type": "application/json"})
    resp = urllib.request.urlopen(req)
    return json.loads(resp.read())["prompt_id"]


def wait_for_prompt(prompt_id: str, timeout: int = 120) -> dict:
    """Wait for a prompt to complete and return output images info."""
    start = time.time()
    while time.time() - start < timeout:
        try:
            resp = urllib.request.urlopen(f"{COMFY_URL}/history/{prompt_id}")
            history = json.loads(resp.read())
            if prompt_id in history:
                return history[prompt_id]
        except Exception:
            pass
        time.sleep(1)
    raise TimeoutError(f"Prompt {prompt_id} timed out after {timeout}s")


def upscale_image(input_path: str, output_dir: Path, target_size: str = "portrait") -> str:
    """Upscale a single image via ComfyUI + RealESRGAN, then resize to IG format."""
    # Copy input image to ComfyUI input dir
    comfy_input = Path.home() / "comfy/ComfyUI/input"
    comfy_input.mkdir(parents=True, exist_ok=True)
    img_name = os.path.basename(input_path)
    shutil.copy2(input_path, comfy_input / img_name)

    # Build workflow
    workflow = {
        "1": {
            "class_type": "UpscaleModelLoader",
            "inputs": {"model_name": "RealESRGAN_x4plus.pth"}
        },
        "2": {
            "class_type": "LoadImage",
            "inputs": {"image": img_name}
        },
        "3": {
            "class_type": "ImageUpscaleWithModel",
            "inputs": {
                "upscale_model": ["1", 0],
                "image": ["2", 0]
            }
        },
        "4": {
            "class_type": "SaveImage",
            "inputs": {
                "filename_prefix": "eir_upscl",
                "images": ["3", 0]
            }
        }
    }

    # Queue and wait
    prompt_id = queue_prompt(workflow)
    print(f"  Queued: {img_name} (prompt {prompt_id[:8]})")

    history = wait_for_prompt(prompt_id, timeout=180)

    # Find output image
    outputs = history.get("outputs", {})
    for node_id, node_out in outputs.items():
        if "images" in node_out:
            for img_info in node_out["images"]:
                src_path = Path.home() / "comfy/ComfyUI/output" / img_info["filename"]
                if src_path.exists():
                    # Post-process: resize to IG format
                    from PIL import Image
                    img = Image.open(src_path)

                    # Calculate target keeping aspect ratio
                    tw, th = TARGET_SIZES[target_size]
                    # Smart crop: center-crop to target aspect ratio then resize
                    orig_ratio = img.width / img.height
                    target_ratio = tw / th

                    if orig_ratio > target_ratio:
                        # Image is wider — crop width
                        new_w = int(img.height * target_ratio)
                        left = (img.width - new_w) // 2
                        img = img.crop((left, 0, left + new_w, img.height))
                    else:
                        # Image is taller — crop height
                        new_h = int(img.width / target_ratio)
                        top = (img.height - new_h) // 2
                        img = img.crop((0, top, img.width, top + new_h))

                    img = img.resize((tw, th), Image.LANCZOS)

                    # Save with high quality
                    out_name = f"{Path(img_name).stem}_{target_size}.png"
                    final_path = output_dir / out_name
                    img.save(final_path, "PNG", optimize=True)
                    print(f"  Saved: {final_path.name} ({tw}x{th})")
                    return str(final_path)

    raise FileNotFoundError(f"No output found for {img_name}")


def main():
    parser = argparse.ArgumentParser(description="Eir Image Upscaler")
    parser.add_argument("--input", default=str(DEFAULT_INPUT), help="Input directory")
    parser.add_argument("--output", default=str(DEFAULT_OUTPUT), help="Output directory")
    parser.add_argument("--limit", type=int, default=0, help="Max images to process (0=all)")
    parser.add_argument("--size", default="portrait", choices=list(TARGET_SIZES.keys()), help="Target size")
    parser.add_argument("--source", default="feed", help="Source subfolder (feed, content_bank, stories, profile)")
    args = parser.parse_args()

    input_dir = Path(args.input) / f"{args.source}_batch_v2" if args.source else Path(args.input)
    output_dir = Path(args.output)
    output_dir.mkdir(parents=True, exist_ok=True)

    # Collect images
    extensions = {".png", ".jpg", ".jpeg", ".webp"}
    images = sorted([
        f for f in input_dir.iterdir()
        if f.suffix.lower() in extensions
    ])

    if not images:
        print(f"No images found in {input_dir}")
        sys.exit(1)

    if args.limit:
        images = images[:args.limit]

    print(f"Eir Upscaler — {len(images)} images from {input_dir}")
    print(f"Target: {TARGET_SIZES[args.size]} ({args.size})")
    print(f"Output: {output_dir}")
    print()

    results = []
    for i, img_path in enumerate(images):
        print(f"[{i+1}/{len(images)}] {img_path.name}")
        try:
            result = upscale_image(str(img_path), output_dir, args.size)
            results.append(result)
        except Exception as e:
            print(f"  ERROR: {e}")
        # Small delay to let GPU cool
        time.sleep(2)

    print(f"\nDone! {len(results)}/{len(images)} images upscaled to {output_dir}")


if __name__ == "__main__":
    main()
