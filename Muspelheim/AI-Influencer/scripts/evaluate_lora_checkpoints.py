#!/usr/bin/env python3
"""
Eir LoRA v2 — Checkpoint Evaluator
===================================
After training completes, run this script to:
1. Copy each checkpoint to ComfyUI models/loras/
2. Generate a test image with each checkpoint
3. Save comparison images to outputs/lora_evaluation/

Usage:
    python3 evaluate_lora_checkpoints.py
"""
import json
import os
import shutil
import time
import urllib.error
import urllib.request

PROJECT = "/mnt/d/Proyectos/Yggdrasil/Muspelheim/AI-Influencer"
LORA_OUTPUT = f"{PROJECT}/assets/lora_output"
COMFY_LORA = os.path.expanduser("~/comfy/ComfyUI/models/loras")
EVAL_OUTPUT = f"{PROJECT}/outputs/lora_evaluation"
COMFY_URL = "http://localhost:8188"

# Test prompt — same for all checkpoints for fair comparison
TEST_PROMPT = (
    "eir_niflheimr, 1girl, solo, pale skin, silver-white hair with violet highlights, "
    "icy blue eyes, portrait, close-up, looking at viewer, dark fantasy aesthetic, "
    "dramatic side lighting, detailed skin, masterpiece, best quality"
)
NEGATIVE_PROMPT = (
    "cartoon, anime, 3d render, deformed, bad anatomy, bad hands, missing fingers, "
    "extra digits, extra limbs, blurry, low quality, worst quality, watermark, text, "
    "logo, signature, deformed face, distorted features, ugly, tiling, grainy, noisy, "
    "oversaturated, poorly drawn eyes, bad proportions, floating limbs"
)


def find_checkpoints():
    """Find all v2 LoRA checkpoints."""
    checkpoints = []
    for f in sorted(os.listdir(LORA_OUTPUT)):
        if f.startswith("eir_niflheimr_v2_lora") and f.endswith(".safetensors"):
            path = os.path.join(LORA_OUTPUT, f)
            size_mb = os.path.getsize(path) / 1024 / 1024
            # Extract step number
            step = "final"
            if "-0000" in f:
                step = f.split("-")[-1].replace(".safetensors", "")
            checkpoints.append(
                {
                    "filename": f,
                    "path": path,
                    "size_mb": round(size_mb, 1),
                    "step": step,
                }
            )
    return checkpoints


def copy_to_comfy(checkpoint):
    """Copy a LoRA checkpoint to ComfyUI models directory."""
    src = checkpoint["path"]
    dst = os.path.join(COMFY_LORA, checkpoint["filename"])
    if os.path.exists(dst):
        print(f"  Already exists: {checkpoint['filename']}")
    else:
        shutil.copy2(src, dst)
        print(f"  Copied: {checkpoint['filename']} -> {dst}")
    return dst


def generate_test_image(lora_filename, step_label, seed=42):
    """Generate a test image with ComfyUI API using the specified LoRA."""
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
            "class_type": "CheckpointLoaderSimple",
            "inputs": {
                "ckpt_name": "Juggernaut-XL_v9_RunDiffusionPhoto_v2.safetensors"
            },
        },
        "5": {
            "class_type": "EmptyLatentImage",
            "inputs": {"width": 832, "height": 1216, "batch_size": 1},
        },
        "6": {
            "class_type": "CLIPTextEncode",
            "inputs": {"text": f"{TEST_PROMPT}, lora_weight=0.8", "clip": ["11", 1]},
        },
        "7": {
            "class_type": "CLIPTextEncode",
            "inputs": {"text": NEGATIVE_PROMPT, "clip": ["11", 1]},
        },
        "8": {
            "class_type": "VAEDecode",
            "inputs": {"samples": ["3", 0], "vae": ["4", 2]},
        },
        "9": {
            "class_type": "SaveImage",
            "inputs": {
                "filename_prefix": f"eir_eval_step{step_label}",
                "images": ["8", 0],
            },
        },
        "10": {
            "class_type": "LoraLoader",
            "inputs": {
                "lora_name": lora_filename,
                "strength_model": 0.8,
                "strength_clip": 0.8,
                "model": ["4", 0],
                "clip": ["4", 1],
            },
        },
        "11": {
            "class_type": "LoraLoader",
            "inputs": {
                "lora_name": lora_filename,
                "strength_model": 0.8,
                "strength_clip": 0.8,
                "model": ["10", 0],
                "clip": ["10", 2],
            },
        },
    }

    prompt = {"prompt": workflow}
    data = json.dumps(prompt).encode("utf-8")
    req = urllib.request.Request(
        f"{COMFY_URL}/prompt", data=data, headers={"Content-Type": "application/json"}
    )

    try:
        resp = urllib.request.urlopen(req)
        result = json.loads(resp.read())
        return result.get("prompt_id")
    except urllib.error.URLError as e:
        print(f"  ERROR: ComfyUI not reachable - {e}")
        return None


def wait_for_completion(prompt_id, timeout=120):
    """Wait for ComfyUI to finish generating an image."""
    start = time.time()
    while time.time() - start < timeout:
        try:
            resp = urllib.request.urlopen(f"{COMFY_URL}/history/{prompt_id}")
            history = json.loads(resp.read())
            if prompt_id in history:
                status = history[prompt_id].get("status", {})
                if (
                    status.get("completed", False)
                    or status.get("status_str") == "success"
                ):
                    outputs = history[prompt_id].get("outputs", {})
                    for node_id, node_output in outputs.items():
                        if "images" in node_output:
                            for img in node_output["images"]:
                                return img["filename"]
                elif status.get("status_str") == "error":
                    print(f"  ERROR: Generation failed")
                    return None
        except:
            pass
        time.sleep(3)
    print(f"  TIMEOUT after {timeout}s")
    return None


def main():
    print("=" * 60)
    print("  Eir LoRA v2 — Checkpoint Evaluator")
    print("=" * 60)

    # Find checkpoints
    checkpoints = find_checkpoints()
    if not checkpoints:
        print("\nNo v2 checkpoints found in", LORA_OUTPUT)
        print("Run training first: bash scripts/train_eir_v2.sh")
        return

    print(f"\nFound {len(checkpoints)} checkpoints:")
    for ckpt in checkpoints:
        print(f"  {ckpt['filename']} ({ckpt['size_mb']}MB, step={ckpt['step']})")

    # Create output dir
    os.makedirs(EVAL_OUTPUT, exist_ok=True)

    # Copy all checkpoints to ComfyUI
    print("\n[1/3] Copying checkpoints to ComfyUI...")
    for ckpt in checkpoints:
        copy_to_comfy(ckpt)

    # Check if ComfyUI is running
    print("\n[2/3] Checking ComfyUI...")
    try:
        resp = urllib.request.urlopen(f"{COMFY_URL}/system_stats", timeout=5)
        print("  ComfyUI is running")
    except:
        print("  WARNING: ComfyUI not running! Start it first:")
        print("  cd ~/comfy/ComfyUI && python3 main.py --listen --port 8188")
        return

    # Generate test images
    print("\n[3/3] Generating test images...")
    for ckpt in checkpoints:
        step = ckpt["step"]
        print(f"\n  Generating with step {step}...")
        prompt_id = generate_test_image(ckpt["filename"], step)
        if prompt_id:
            print(f"    Submitted: {prompt_id}")
            filename = wait_for_completion(prompt_id, timeout=120)
            if filename:
                print(f"    Generated: {filename}")
            else:
                print(f"    Failed to generate")

    print("\n" + "=" * 60)
    print("  Evaluation complete!")
    print(f"  Check images in ComfyUI output directory")
    print(f"  or at {EVAL_OUTPUT}")
    print("=" * 60)
    print("\nNext steps:")
    print("  1. Compare images visually")
    print("  2. Choose the best checkpoint (usually step 800-1400)")
    print("  3. Copy best checkpoint as: eir_niflheimr_v2_best.safetensors")


if __name__ == "__main__":
    main()
