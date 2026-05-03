#!/usr/bin/env python3
"""
Eir Batch Image Generator
Generates images via ComfyUI API using LoRA v1/v2 checkpoints.
Usage: python generate_batch.py [--lora NAME] [--posts] [--all] [--profile]
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
OUTPUT_BASE = Path("/mnt/d/Proyectos/Yggdrasil/Muspelheim/AI-Influencer/outputs")
LORA_DIR = Path(
    "/mnt/d/Proyectos/Yggdrasil/Muspelheim/AI-Influencer/assets/lora_output"
)
COMFY_LORA_DIR = Path(os.path.expanduser("~/comfy/ComfyUI/models/loras"))
COMFY_CKPT_DIR = Path(os.path.expanduser("~/comfy/ComfyUI/models/checkpoints"))
PROMPTS_FILE = Path(
    "/mnt/d/Proyectos/Yggdrasil/Muspelheim/AI-Influencer/config/prompts/eir_content_plan.json"
)

DEFAULT_LORA = "eir_niflheimr_lora_r32_epoch10.safetensors"
DEFAULT_CKPT = "Juggernaut-XL_v9_RunDiffusionPhoto_v2.safetensors"
DEFAULT_VAE = ""

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

    # Check lora_output dir
    for f in LORA_DIR.glob(f"*{name}*"):
        import shutil

        shutil.copy2(f, comfy_path)
        print(f"  Copied {f.name} to ComfyUI loras/")
        return f.name

    # Try as partial match
    for f in LORA_DIR.glob(f"*{name}*.safetensors"):
        import shutil

        shutil.copy2(f, comfy_path)
        print(f"  Copied {f.name} to ComfyUI loras/")
        return f.name

    print(f"LoRA not found: {name}")
    sys.exit(1)


def build_workflow(
    prompt, negative, width, height, lora_name, seed=None, lora_strength=0.8
):
    """Build ComfyUI workflow JSON for SDXL + LoRA generation."""
    if seed is None:
        seed = random.randint(0, 2**32 - 1)

    workflow = {
        "3": {
            "class_type": "KSampler",
            "inputs": {
                "seed": seed,
                "steps": 30,
                "cfg": 7.0,
                "sampler_name": "dpmpp_2m",
                "scheduler": "karras",
                "denoise": 1.0,
                "model": ["10", 0],
                "positive": ["6", 0],
                "negative": ["7", 0],
                "latent_image": ["5", 0],
            },
        },
        "4": {
            "class_type": "UNETLoader",
            "inputs": {"unet_name": DEFAULT_CKPT, "weight_dtype": "default"},
        },
        "5": {
            "class_type": "EmptyLatentImage",
            "inputs": {"width": width, "height": height, "batch_size": 1},
        },
        "6": {
            "class_type": "CLIPTextEncode",
            "inputs": {"text": prompt, "clip": ["11", 0]},
        },
        "7": {
            "class_type": "CLIPTextEncode",
            "inputs": {"text": negative, "clip": ["11", 0]},
        },
        "8": {
            "class_type": "VAEDecode",
            "inputs": {"samples": ["3", 0], "vae": ["9", 0]},
        },
        "9": {
            "class_type": "VAELoader",
            "inputs": {"vae_name": "sdxl_vae.safetensors"},
        },
        "10": {
            "class_type": "LoraLoader",
            "inputs": {
                "lora_name": lora_name,
                "strength_model": lora_strength,
                "strength_clip": lora_strength,
                "model": ["4", 0],
                "clip": ["11", 0],
            },
        },
        "11": {
            "class_type": "CLIPLoader",
            "inputs": {"clip_name": "clip_g.safetensors", "type": "clip_g"},
        },
        "12": {
            "class_type": "CLIPLoader",
            "inputs": {"clip_name": "clip_l.safetensors", "type": "clip_l"},
        },
        "13": {
            "class_type": "CLIPMergeSimple",
            "inputs": {"clip1": ["11", 0], "clip2": ["12", 0], "ratio": 1.0},
        },
        "14": {
            "class_type": "SaveImage",
            "inputs": {"filename_prefix": "eir_gen", "images": ["8", 0]},
        },
    }

    # Update CLIP connections to use merged clip
    for node_id in ["6", "7", "10"]:
        if node_id in workflow:
            if "clip" in workflow[node_id]["inputs"]:
                if workflow[node_id]["inputs"]["clip"] == ["11", 0]:
                    workflow[node_id]["inputs"]["clip"] = ["13", 0]

    # LoraLoader clip output should also use merged
    workflow["10"]["inputs"]["clip"] = ["13", 0]

    return workflow


def queue_prompt(workflow):
    """Submit workflow to ComfyUI API."""
    data = json.dumps({"prompt": workflow}).encode("utf-8")
    req = urllib.request.Request(
        f"{COMFY_URL}/prompt", data=data, headers={"Content-Type": "application/json"}
    )

    try:
        response = urllib.request.urlopen(req, timeout=30)
        result = json.loads(response.read())
        return result.get("prompt_id")
    except urllib.error.HTTPError as e:
        print(f"  Error: {e.code} - {e.read().decode()}")
        return None
    except Exception as e:
        print(f"  Error: {e}")
        return None


def wait_for_completion(prompt_id, timeout=300):
    """Wait for generation to complete."""
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
    return "timeout"


def generate_image(
    prompt,
    negative,
    width,
    height,
    lora_name,
    seed=None,
    lora_strength=0.8,
    output_dir=None,
):
    """Generate a single image."""
    if seed is None:
        seed = random.randint(SEED_OFFSET, SEED_OFFSET + 10000)

    print(f"  Generating {width}x{height} (seed={seed}, lora={lora_name})...")

    workflow = build_workflow(
        prompt, negative, width, height, lora_name, seed, lora_strength
    )
    prompt_id = queue_prompt(workflow)

    if not prompt_id:
        print("  Failed to queue prompt!")
        return None

    result = wait_for_completion(prompt_id)
    print(f"  Result: {result}")
    return result


def generate_feed_posts(data, lora_name):
    """Generate all 9 Instagram feed posts."""
    print("\n=== Generating Feed Posts ===")
    out_dir = OUTPUT_BASE / "feed_posts"
    out_dir.mkdir(parents=True, exist_ok=True)

    posts = data["instagram_feed"]
    neg_master = data["negative_prompts"]["master"]

    for post_key, post in sorted(posts.items(), key=lambda x: x[1].get("order", 0)):
        print(f"\n--- {post_key} ---")

        if post["type"] == "single":
            filename = generate_image(
                prompt=post["prompt"],
                negative=post.get("negative", neg_master),
                width=post["resolution"][0],
                height=post["resolution"][1],
                lora_name=lora_name,
                seed=SEED_OFFSET + post.get("order", 1) * 100,
            )
            print(f"  Generated: {filename}")

        elif post["type"] == "carousel":
            slides = post.get("slides", 2)
            for i in range(slides):
                slide_key = f"prompt_slide{i+1}"
                if slide_key in post:
                    res = (
                        post["resolutions"][i]
                        if "resolutions" in post
                        else post["resolution"]
                    )
                    filename = generate_image(
                        prompt=post[slide_key],
                        negative=post.get("negative", neg_master),
                        width=res[0],
                        height=res[1],
                        lora_name=lora_name,
                        seed=SEED_OFFSET + post.get("order", 1) * 100 + i + 1,
                    )
                    print(f"  Slide {i+1}: {filename}")


def generate_stories(data, lora_name):
    """Generate story images."""
    print("\n=== Generating Stories ===")
    out_dir = OUTPUT_BASE / "stories"
    out_dir.mkdir(parents=True, exist_ok=True)

    neg_master = data["negative_prompts"]["master"]

    for story_key, story in data.get("stories", {}).items():
        print(f"\n--- {story_key} ---")
        filename = generate_image(
            prompt=story["prompt"],
            negative=neg_master,
            width=story["resolution"][0],
            height=story["resolution"][1],
            lora_name=lora_name,
            seed=SEED_OFFSET + 90000 + hash(story_key) % 1000,
        )
        print(f"  Generated: {filename}")


def generate_profile_assets(data, lora_name):
    """Generate profile picture, banner, highlight covers."""
    print("\n=== Generating Profile Assets ===")

    neg_master = data["negative_prompts"]["master"]
    assets = data.get("profile_assets", {})

    # Avatar
    if "avatar" in assets:
        avatar = assets["avatar"]
        print(f"\n--- Avatar ---")
        filename = generate_image(
            prompt=avatar["prompt"],
            negative=avatar.get("negative", neg_master),
            width=avatar["resolution"][0],
            height=avatar["resolution"][1],
            lora_name=lora_name,
            lora_strength=0.85,
            seed=42,
        )
        print(f"  Generated: {filename}")

    # Banner
    if "banner_x" in assets:
        banner = assets["banner_x"]
        print(f"\n--- X/Twitter Banner ---")
        filename = generate_image(
            prompt=banner["prompt"],
            negative=banner.get("negative", neg_master),
            width=banner["resolution"][0],
            height=banner["resolution"][1],
            lora_name=lora_name,
            lora_strength=0.7,  # Lower strength for landscape composition
            seed=43,
        )
        print(f"  Generated: {filename}")

    # Highlight covers
    if "highlight_covers" in assets:
        for cover_key, cover in assets["highlight_covers"].items():
            print(f"\n--- Highlight: {cover_key} ---")
            filename = generate_image(
                prompt=cover["prompt"],
                negative=neg_master,
                width=cover["resolution"][0],
                height=cover["resolution"][1],
                lora_name=lora_name,
                lora_strength=0.5,  # Low strength for background/objects
                seed=SEED_OFFSET + 95000 + hash(cover_key) % 500,
            )
            print(f"  Generated: {filename}")


def main():
    import argparse

    parser = argparse.ArgumentParser(description="Eir Batch Image Generator")
    parser.add_argument("--lora", default=DEFAULT_LORA, help="LoRA filename")
    parser.add_argument("--posts", action="store_true", help="Generate feed posts")
    parser.add_argument("--stories", action="store_true", help="Generate stories")
    parser.add_argument(
        "--profile", action="store_true", help="Generate profile assets"
    )
    parser.add_argument("--all", action="store_true", help="Generate everything")
    parser.add_argument("--strength", type=float, default=0.8, help="LoRA strength")
    args = parser.parse_args()

    # Check ComfyUI is running
    try:
        response = urllib.request.urlopen(f"{COMFY_URL}/system_stats", timeout=5)
        print("ComfyUI is running ✓")
    except:
        print("ERROR: ComfyUI is not running! Start it first:")
        print("  cd ~/comfy/ComfyUI && python3 main.py --listen --port 8188")
        sys.exit(1)

    # Find and copy LoRA
    lora_name = find_lora(args.lora)
    print(f"Using LoRA: {lora_name} (strength={args.strength})")

    # Load prompts
    data = load_prompts()

    if args.all:
        generate_feed_posts(data, lora_name)
        generate_stories(data, lora_name)
        generate_profile_assets(data, lora_name)
    else:
        if args.posts:
            generate_feed_posts(data, lora_name)
        if args.stories:
            generate_stories(data, lora_name)
        if args.profile:
            generate_profile_assets(data, lora_name)

    if not (args.posts or args.stories or args.profile or args.all):
        print(
            "\nNo generation mode specified. Use --posts, --stories, --profile, or --all"
        )
        parser.print_help()


if __name__ == "__main__":
    main()
