#!/usr/bin/env python3
"""
Batch upscale all remaining images via ComfyUI + RealESRGAN_x4plus.
Processes: content_bank_v2, stories_highlights_v2, profile_assets, profile_variations, outfits_ghi
"""
import json, time, shutil, urllib.request
from pathlib import Path
from PIL import Image

COMFY_URL = "http://localhost:8188"
PROJECT_DIR = Path("/mnt/d/Proyectos/Yggdrasil/Muspelheim/AI-Influencer")
OUTPUT_DIR = PROJECT_DIR / "outputs/upscaled"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
COMFY_INPUT = Path.home() / "comfy/ComfyUI/input"
COMFY_OUTPUT = Path.home() / "comfy/ComfyUI/output"

# Upscale workflow template
def make_upscale_workflow(image_name: str, target_w: int = 1080, target_h: int = 1350) -> dict:
    return {
        "1": {
            "class_type": "UpscaleModelLoader",
            "inputs": {"model_name": "RealESRGAN_x4plus.pth"}
        },
        "2": {
            "class_type": "LoadImage",
            "inputs": {"image": image_name}
        },
        "3": {
            "class_type": "UpscaleImage",
            "inputs": {
                "image": ["2", 0],
                "upscale_model": ["1", 0]
            }
        },
        "4": {
            "class_type": "ImageScale",
            "inputs": {
                "image": ["3", 0],
                "upscale_method": "lanczos",
                "width": target_w,
                "height": target_h,
                "crop": "center"
            }
        },
        "5": {
            "class_type": "SaveImage",
            "inputs": {
                "filename_prefix": "eir_upscl",
                "images": ["4", 0]
            }
        }
    }


def queue_prompt(workflow):
    data = json.dumps({"prompt": workflow}).encode("utf-8")
    req = urllib.request.Request(f"{COMFY_URL}/prompt", data=data, headers={"Content-Type": "application/json"})
    resp = urllib.request.urlopen(req)
    return json.loads(resp.read())["prompt_id"]


def wait_for_prompt(prompt_id, timeout=300):
    start = time.time()
    while time.time() - start < timeout:
        try:
            resp = urllib.request.urlopen(f"{COMFY_URL}/history/{prompt_id}")
            history = json.loads(resp.read())
            if prompt_id in history:
                return history[prompt_id]
        except Exception:
            pass
        time.sleep(2)
    raise TimeoutError(f"Prompt {prompt_id} timed out")


# Source directories and their target sizes
sources = {
    "content_bank_v2": (1080, 1350),   # IG portrait 4:5
    "stories_highlights_v2": (1080, 1920),  # Story 9:16
    "profile_assets": (1080, 1080),     # Square for profile
    "profile_variations": (1080, 1080),  # Square for profile
    "outfits_ghi": (1080, 1350),         # IG portrait 4:5
}

# Flatten: [(src_dir, filename, target_w, target_h, prefix), ...]
jobs = []
for folder, (tw, th) in sources.items():
    src_dir = PROJECT_DIR / "outputs" / folder
    for png in sorted(src_dir.glob("*.png")):
        # Skip if already upscaled (check by stem)
        existing = OUTPUT_DIR / f"{folder}_{png.stem}_upscaled.jpg"
        if existing.exists():
            print(f"  SKIP (exists): {existing.name}")
            continue
        jobs.append((folder, png, tw, th))

print(f"Batch upscale: {len(jobs)} images to process")
print(f"Target sizes: content_bank=1080x1350, stories=1080x1920, profiles=1080x1080, outfits=1080x1350")

total = len(jobs)
done = 0
failed = 0

for i, (folder, png_path, tw, th) in enumerate(jobs):
    print(f"\n[{i+1}/{total}] Upscaling: {png_path.name} -> {tw}x{th}")

    # Copy to ComfyUI input
    comfy_name = f"eir_batch_{png_path.name}"
    dest = COMFY_INPUT / comfy_name
    shutil.copy2(png_path, dest)

    # Create and queue workflow
    wf = make_upscale_workflow(comfy_name, tw, th)
    try:
        pid = queue_prompt(wf)
        history = wait_for_prompt(pid, timeout=300)

        # Find output
        found = False
        for nid, nout in history.get("outputs", {}).items():
            if "images" in nout:
                for img in nout["images"]:
                    src = COMFY_OUTPUT / img["filename"]
                    if src.exists():
                        # Convert to JPG and save
                        img_obj = Image.open(src)
                        final_name = f"{folder}_{png_path.stem}_upscaled.jpg"
                        final_path = OUTPUT_DIR / final_name
                        img_obj.save(final_path, "JPEG", quality=92)
                        print(f"  OK: {final_name} ({final_path.stat().st_size / 1024:.0f} KB)")
                        done += 1
                        # Clean up ComfyUI output
                        src.unlink()
                        found = True
                        break
            if found:
                break
        if not found:
            print(f"  FAILED: no output found")
            failed += 1
    except Exception as e:
        print(f"  ERROR: {e}")
        failed += 1

    # Clean up input
    if dest.exists():
        dest.unlink()

print(f"\n{'='*60}")
print(f"Batch upscale complete: {done} succeeded, {failed} failed out of {total}")
print(f"Output directory: {OUTPUT_DIR}")
