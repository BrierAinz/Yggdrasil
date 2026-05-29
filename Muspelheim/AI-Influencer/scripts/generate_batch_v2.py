#!/usr/bin/env python3
"""
Eir Batch Image Generator v2
Uses ComfyUI API with CheckpointLoaderSimple + LoraLoader workflow.
Generates Instagram feed posts, stories, and profile assets.

Usage:
  python generate_batch_v2.py --lora eir_niflheimr_lora_r32_epoch10.safetensors --posts
  python generate_batch_v2.py --lora eir_niflheimr_v2_lora_r32-000100.safetensors --all
  python generate_batch_v2.py --profile  # Generate avatar, banner, highlights
"""
import json
import os
import random
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

# --- Config ---
COMFY_URL = "http://localhost:8188"
PROJECT_DIR = Path("/mnt/d/Proyectos/Yggdrasil/Muspelheim/AI-Influencer")
OUTPUT_BASE = PROJECT_DIR / "outputs"
LORA_DIR = PROJECT_DIR / "assets" / "lora_output"
COMFY_LORA_DIR = Path(os.path.expanduser("~/comfy/ComfyUI/models/loras"))
PROMPTS_FILE = PROJECT_DIR / "config" / "prompts" / "eir_content_plan.json"
WORKFLOW_TEMPLATE = PROJECT_DIR / "workflows" / "eir_lora_portrait_api.json"

DEFAULT_LORA = "eir_niflheimr_lora_r32_epoch10.safetensors"
DEFAULT_CKPT = "Juggernaut-XL_v9_RunDiffusionPhoto_v2.safetensors"
SEED_OFFSET = 42


def load_prompts():
    with open(PROMPTS_FILE) as f:
        return json.load(f)


def find_lora(name=None):
    """Find LoRA file, copy to ComfyUI if needed."""
    if name is None:
        name = DEFAULT_LORA

    # Check ComfyUI models dir first
    comfy_path = COMFY_LORA_DIR / name
    if comfy_path.exists():
        return name

    # Check lora_output dir for exact match
    exact = LORA_DIR / name
    if exact.exists():
        import shutil

        shutil.copy2(exact, comfy_path)
        print(f"  Copied {name} to ComfyUI loras/")
        return name

    # Try glob for partial matches
    for f in LORA_DIR.glob("*.safetensors"):
        if name in f.name or f.name.startswith(name.split(".")[0]):
            import shutil

            shutil.copy2(f, COMFY_LORA_DIR / f.name)
            print(f"  Copied {f.name} to ComfyUI loras/")
            return f.name

    # Last resort: list available
    available = list(COMFY_LORA_DIR.glob("*.safetensors"))
    print(f"LoRA not found: {name}")
    print(f"Available: {[f.name for f in available]}")
    sys.exit(1)


def build_workflow(
    prompt,
    negative,
    width,
    height,
    lora_name,
    seed=42,
    lora_strength=0.8,
    steps=30,
    cfg=7.0,
    filename_prefix="eir_gen",
):
    """Build ComfyUI workflow from template with overrides."""
    with open(WORKFLOW_TEMPLATE) as f:
        wf = json.load(f)

    # Update values
    wf["10"]["inputs"]["lora_name"] = lora_name
    wf["10"]["inputs"]["strength_model"] = lora_strength
    wf["10"]["inputs"]["strength_clip"] = lora_strength
    wf["5"]["inputs"]["width"] = width
    wf["5"]["inputs"]["height"] = height
    wf["6"]["inputs"]["text"] = prompt
    wf["7"]["inputs"]["text"] = negative
    wf["3"]["inputs"]["seed"] = seed
    wf["3"]["inputs"]["steps"] = steps
    wf["3"]["inputs"]["cfg"] = cfg
    wf["9"]["inputs"]["filename_prefix"] = filename_prefix

    return wf


def queue_and_wait(workflow, timeout=180):
    """Submit workflow and wait for completion."""
    data = json.dumps({"prompt": workflow}).encode("utf-8")
    req = urllib.request.Request(
        f"{COMFY_URL}/prompt", data=data, headers={"Content-Type": "application/json"}
    )

    try:
        response = urllib.request.urlopen(req, timeout=30)
        result = json.loads(response.read())
        prompt_id = result.get("prompt_id")
    except urllib.error.HTTPError as e:
        print(f"  HTTP Error: {e.code}")
        try:
            error_body = e.read().decode()
            print(f"  Details: error_body[:500]")
        except:
            pass
        return None
    except Exception as e:
        print(f"  Error: {e}")
        return None

    if not prompt_id:
        print("  No prompt_id returned!")
        return None

    # Wait for completion
    start = time.time()
    while time.time() - start < timeout:
        try:
            req = urllib.request.Request(f"{COMFY_URL}/history/{prompt_id}")
            response = urllib.request.urlopen(req, timeout=10)
            history = json.loads(response.read())
            if prompt_id in history:
                outputs = history[prompt_id].get("outputs", {})
                for node_id, node_output in outputs.items():
                    if "images" in node_output:
                        for img in node_output["images"]:
                            return img["filename"]
                return "completed_no_image"
        except:
            pass
        time.sleep(2)

    print(f"  Timeout waiting for generation!")
    return None


def generate_image(
    prompt,
    negative,
    width,
    height,
    lora_name,
    seed=None,
    lora_strength=0.8,
    filename_prefix="eir_gen",
):
    """Generate a single image and return filename."""
    if seed is None:
        seed = random.randint(0, 2**32 - 1)

    print(f"  Generating {width}x{height} (seed={seed}, lora_str={lora_strength})...")

    wf = build_workflow(
        prompt,
        negative,
        width,
        height,
        lora_name,
        seed,
        lora_strength,
        filename_prefix=filename_prefix,
    )
    result = queue_and_wait(wf)

    if result:
        print(f"  -> {result}")
    return result


def generate_feed_posts(data, lora_name, lora_strength=0.8):
    """Generate all 9 Instagram feed posts."""
    print("\n" + "=" * 60)
    print("=== GENERATING FEED POSTS ===")
    print("=" * 60)

    (OUTPUT_BASE / "feed_posts").mkdir(parents=True, exist_ok=True)

    posts = data["instagram_feed"]
    neg_master = data["negative_prompts"]["master"]

    generated = []
    for post_key, post in sorted(posts.items(), key=lambda x: x[1].get("order", 0)):
        print(f"\n--- {post_key} (order {post.get('order', '?')}) ---")

        if post["type"] == "single":
            neg = post.get("negative", neg_master)
            res = post["resolution"]
            seed = SEED_OFFSET + post.get("order", 1) * 100
            fname = generate_image(
                prompt=post["prompt"],
                negative=neg,
                width=res[0],
                height=res[1],
                lora_name=lora_name,
                seed=seed,
                lora_strength=lora_strength,
                filename_prefix=f"eir_{post_key}",
            )
            if fname:
                generated.append({"post": post_key, "file": fname, "seed": seed})

        elif post["type"] == "carousel":
            neg = post.get("negative", neg_master)
            slides = post.get("slides", 2)
            for i in range(slides):
                slide_key = f"prompt_slide{i+1}"
                if slide_key in post:
                    res = (
                        post["resolutions"][i]
                        if "resolutions" in post
                        else post["resolution"]
                    )
                    seed = SEED_OFFSET + post.get("order", 1) * 100 + i + 1
                    fname = generate_image(
                        prompt=post[slide_key],
                        negative=neg,
                        width=res[0],
                        height=res[1],
                        lora_name=lora_name,
                        seed=seed,
                        lora_strength=lora_strength,
                        filename_prefix=f"eir_{post_key}_slide{i+1}",
                    )
                    if fname:
                        generated.append(
                            {
                                "post": post_key,
                                "slide": i + 1,
                                "file": fname,
                                "seed": seed,
                            }
                        )

    print(f"\n=== Generated {len(generated)} feed post images ===")
    return generated


def generate_stories(data, lora_name, lora_strength=0.75):
    """Generate story images."""
    print("\n" + "=" * 60)
    print("=== GENERATING STORIES ===")
    print("=" * 60)

    (OUTPUT_BASE / "stories").mkdir(parents=True, exist_ok=True)

    neg_master = data["negative_prompts"]["master"]
    generated = []

    for story_key, story in data.get("stories", {}).items():
        print(f"\n--- {story_key} ---")
        seed = SEED_OFFSET + 90000 + hash(story_key) % 1000
        fname = generate_image(
            prompt=story["prompt"],
            negative=neg_master,
            width=story["resolution"][0],
            height=story["resolution"][1],
            lora_name=lora_name,
            seed=seed,
            lora_strength=lora_strength,
            filename_prefix=f"eir_story_{story_key}",
        )
        if fname:
            generated.append({"story": story_key, "file": fname, "seed": seed})

    print(f"\n=== Generated {len(generated)} story images ===")
    return generated


def generate_profile_assets(data, lora_name):
    """Generate profile picture, banner, highlight covers."""
    print("\n" + "=" * 60)
    print("=== GENERATING PROFILE ASSETS ===")
    print("=" * 60)

    (OUTPUT_BASE / "profile_assets").mkdir(parents=True, exist_ok=True)

    neg_master = data["negative_prompts"]["master"]
    assets = data.get("profile_assets", {})
    generated = []

    # Avatar (1024x1024, high LoRA strength for face)
    if "avatar" in assets:
        av = assets["avatar"]
        print(f"\n--- Avatar (1024x1024) ---")
        fname = generate_image(
            prompt=av["prompt"],
            negative=av.get("negative", neg_master),
            width=1024,
            height=1024,
            lora_name=lora_name,
            lora_strength=0.85,
            seed=42,
            filename_prefix="eir_avatar",
        )
        if fname:
            generated.append({"asset": "avatar", "file": fname})

    # X/Twitter Banner (1500x500)
    if "banner_x" in assets:
        bn = assets["banner_x"]
        print(f"\n--- X/Twitter Banner (1500x500) ---")
        fname = generate_image(
            prompt=bn["prompt"],
            negative=bn.get("negative", neg_master),
            width=1500,
            height=500,
            lora_name=lora_name,
            lora_strength=0.7,
            seed=43,
            filename_prefix="eir_banner_x",
        )
        if fname:
            generated.append({"asset": "banner_x", "file": fname})

    # Highlight covers (512x512, low LoRA - mostly background/object)
    if "highlight_covers" in assets:
        for cover_key, cover in assets["highlight_covers"].items():
            print(f"\n--- Highlight: {cover_key} ---")
            seed = SEED_OFFSET + 95000 + hash(cover_key) % 500
            fname = generate_image(
                prompt=cover["prompt"],
                negative=neg_master,
                width=cover["resolution"][0],
                height=cover["resolution"][1],
                lora_name=lora_name,
                lora_strength=0.5,
                seed=seed,
                filename_prefix=f"eir_hl_{cover_key}",
            )
            if fname:
                generated.append({"asset": f"highlight_{cover_key}", "file": fname})

    print(f"\n=== Generated {len(generated)} profile asset images ===")
    return generated


def main():
    import argparse

    parser = argparse.ArgumentParser(description="Eir Batch Image Generator v2")
    parser.add_argument(
        "--lora", default=DEFAULT_LORA, help="LoRA filename in ComfyUI models/loras/"
    )
    parser.add_argument("--posts", action="store_true", help="Generate feed posts")
    parser.add_argument("--stories", action="store_true", help="Generate stories")
    parser.add_argument(
        "--profile", action="store_true", help="Generate profile assets"
    )
    parser.add_argument("--all", action="store_true", help="Generate everything")
    parser.add_argument(
        "--strength", type=float, default=0.8, help="Default LoRA strength (0-1)"
    )
    args = parser.parse_args()

    # Check ComfyUI
    try:
        urllib.request.urlopen(f"{COMFY_URL}/system_stats", timeout=5)
        print("ComfyUI is running ✓")
    except:
        print("ERROR: ComfyUI is not running!")
        print("  Start: cd ~/comfy/ComfyUI && python3 main.py --listen --port 8188")
        sys.exit(1)

    # Check GPU availability
    stats = json.loads(
        urllib.request.urlopen(f"{COMFY_URL}/system_stats", timeout=5).read()
    )
    vram_free = stats["devices"][0]["vram_free"] if stats.get("devices") else 0
    print(f"  VRAM free: {vram_free / 1024**3:.1f} GB")
    if vram_free < 2 * 1024**3:
        print("  WARNING: Low VRAM! May need to wait for training to finish first.")

    # Find LoRA
    lora_name = find_lora(args.lora)
    print(f"Using LoRA: {lora_name} (strength={args.strength})")

    # Load content plan
    data = load_prompts()
    print(
        f"Loaded content plan: {len(data.get('instagram_feed', {}))} posts, {len(data.get('stories', {}))} stories"
    )

    all_generated = []

    if args.all:
        all_generated.extend(generate_feed_posts(data, lora_name, args.strength))
        all_generated.extend(generate_stories(data, lora_name))
        all_generated.extend(generate_profile_assets(data, lora_name))
    else:
        if args.posts:
            all_generated.extend(generate_feed_posts(data, lora_name, args.strength))
        if args.stories:
            all_generated.extend(generate_stories(data, lora_name))
        if args.profile:
            all_generated.extend(generate_profile_assets(data, lora_name))

    if not all_generated:
        print(
            "\nNo generation mode specified. Use --posts, --stories, --profile, or --all"
        )
        parser.print_help()
        return

    # Summary
    print("\n" + "=" * 60)
    print(f"GENERATION COMPLETE: {len(all_generated)} images generated")
    print("=" * 60)
    for item in all_generated:
        key = list(item.keys())[0]
        print(f"  {item.get(key, '?'):20s} -> {item.get('file', '?')}")


if __name__ == "__main__":
    main()
