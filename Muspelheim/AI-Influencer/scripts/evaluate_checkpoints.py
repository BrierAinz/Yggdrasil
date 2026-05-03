#!/usr/bin/env python3
"""
Eir LoRA Checkpoint Evaluator
Generates comparison images using each checkpoint saved during training.
After training completes, run this to determine the best checkpoint.

Usage:
  python evaluate_checkpoints.py
  python evaluate_checkpoints.py --lora-prefix eir_niflheimr_v2_lora
  python evaluate_checkpoints.py --prompt "custom prompt here"
"""
import json
import os
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

COMFY_URL = "http://localhost:8188"
PROJECT_DIR = Path("/mnt/d/Proyectos/Yggdrasil/Muspelheim/AI-Influencer")
LORA_OUTPUT_DIR = PROJECT_DIR / "assets" / "lora_output"
COMFY_LORA_DIR = Path(os.path.expanduser("~/comfy/ComfyUI/models/loras"))
WORKFLOW_TEMPLATE = PROJECT_DIR / "workflows" / "eir_lora_portrait_api.json"

DEFAULT_CKPT = "Juggernaut-XL_v9_RunDiffusionPhoto_v2.safetensors"

# Test prompts to evaluate character consistency
EVAL_PROMPTS = [
    {
        "name": "portrait_front",
        "prompt": "eir_niflheimr, 1girl, solo, pale skin, silver-white hair with violet highlights, icy blue eyes, high cheekbones, portrait close-up face looking at viewer, dark flowing robes with silver embroidery, northern lights aurora borealis, moonlight, masterpiece, best quality, photorealistic, 4k, detailed skin, cinematic lighting",
        "negative": "cartoon, anime, 3d render, deformed, bad anatomy, blurry, low quality, watermark, text, multiple people",
    },
    {
        "name": "full_body_armor",
        "prompt": "eir_niflheimr, 1girl, solo, pale skin, silver-white hair with violet highlights, icy blue eyes, ornate dark plate armor with silver runic etchings, shoulder pauldrons, full body standing, confident pose, rune-carved stone temple interior, ethereal blue glow from runes, masterpiece, best quality, photorealistic, dramatic lighting, volumetric",
        "negative": "cartoon, anime, 3d, close-up, portrait only, casual, modern, blurry, low quality",
    },
    {
        "name": "dramatic_34",
        "prompt": "eir_niflheimr, 1girl, solo, pale skin, silver-white hair with violet highlights, icy blue eyes, dramatic portrait 3/4 view, intense expression, dark flowing robes, moonlight side lighting, volumetric fog, masterpiece, best quality, photorealistic, 4k, cinematic lighting, moody",
        "negative": "cartoon, anime, 3d, full body, wide shot, casual, blurry, low quality",
    },
]


def find_lora_checkpoints(prefix="eir_niflheimr"):
    """Find all LoRA checkpoint files matching the prefix."""
    checkpoints = []
    for f in sorted(LORA_OUTPUT_DIR.glob(f"{prefix}*.safetensors")):
        checkpoints.append(f.name)
    # Also check ComfyUI dir
    for f in sorted(COMFY_LORA_DIR.glob(f"{prefix}*.safetensors")):
        if f.name not in checkpoints:
            checkpoints.append(f.name)
    return checkpoints


def copy_lora_to_comfy(checkpoint_name):
    """Copy LoRA to ComfyUI models dir if not already there."""
    comfy_path = COMFY_LORA_DIR / checkpoint_name
    if comfy_path.exists():
        return True

    src = LORA_OUTPUT_DIR / checkpoint_name
    if src.exists():
        import shutil

        shutil.copy2(src, comfy_path)
        print(f"  Copied {checkpoint_name} to ComfyUI")
        return True

    print(f"  ERROR: Cannot find {checkpoint_name}")
    return False


def build_eval_workflow(prompt, negative, lora_name, seed=42, lora_strength=0.8):
    """Build a workflow for evaluation."""
    with open(WORKFLOW_TEMPLATE) as f:
        wf = json.load(f)

    wf["10"]["inputs"]["lora_name"] = lora_name
    wf["10"]["inputs"]["strength_model"] = lora_strength
    wf["10"]["inputs"]["strength_clip"] = lora_strength
    wf["5"]["inputs"]["width"] = 832
    wf["5"]["inputs"]["height"] = 1216
    wf["6"]["inputs"]["text"] = prompt
    wf["7"]["inputs"]["text"] = negative
    wf["3"]["inputs"]["seed"] = seed
    wf["3"]["inputs"]["steps"] = 30
    wf["3"]["inputs"]["cfg"] = 7.0

    return wf


def generate_eval_image(prompt_data, lora_name, lora_strength=0.8, seed=42):
    """Generate a single evaluation image."""
    wf = build_eval_workflow(
        prompt_data["prompt"],
        prompt_data["negative"],
        lora_name=lora_name,
        seed=seed,
        lora_strength=lora_strength,
    )
    wf["9"]["inputs"][
        "filename_prefix"
    ] = f"eval_{lora_name.replace('.safetensors','')}_{prompt_data['name']}"

    data = json.dumps({"prompt": wf}).encode("utf-8")
    req = urllib.request.Request(
        f"{COMFY_URL}/prompt", data=data, headers={"Content-Type": "application/json"}
    )

    try:
        response = urllib.request.urlopen(req, timeout=30)
        result = json.loads(response.read())
        prompt_id = result.get("prompt_id")
    except Exception as e:
        print(f"  ERROR submitting: {e}")
        return None

    start = time.time()
    while time.time() - start < 180:
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
                return "completed"
        except:
            pass
        time.sleep(2)

    return None


def evaluate_checkpoints(prefix, lora_strength=0.8):
    """Evaluate all checkpoints of a LoRA."""
    checkpoints = find_lora_checkpoints(prefix)

    if not checkpoints:
        print(f"No checkpoints found for prefix: {prefix}")
        return

    print(f"\nFound {len(checkpoints)} checkpoints:")
    for cp in checkpoints:
        print(f"  - {cp}")

    # Check ComfyUI
    try:
        urllib.request.urlopen(f"{COMFY_URL}/system_stats", timeout=5)
        print("\nComfyUI is running ✓")
    except:
        print("\nERROR: ComfyUI is not running!")
        return

    # Generate images for each checkpoint + prompt combination
    eval_dir = OUTPUT_BASE = PROJECT_DIR / "outputs" / "lora_evaluation"
    eval_dir.mkdir(parents=True, exist_ok=True)

    results = []
    total = len(checkpoints) * len(EVAL_PROMPTS)
    current = 0

    print(f"\nGenerating {total} evaluation images...")
    print("=" * 60)

    for cp in checkpoints:
        print(f"\n--- Checkpoint: {cp} ---")
        if not copy_lora_to_comfy(cp):
            continue

        for prompt_data in EVAL_PROMPTS:
            current += 1
            print(f"  [{current}/{total}] {prompt_data['name']}...")

            fname = generate_eval_image(
                prompt_data,
                cp,
                lora_strength=lora_strength,
                seed=42,  # Consistent seed for comparison
            )

            if fname:
                results.append(
                    {
                        "checkpoint": cp,
                        "prompt": prompt_data["name"],
                        "file": fname,
                        "seed": 42,
                        "lora_strength": lora_strength,
                    }
                )
                print(f"  -> {fname}")
            else:
                print(f"  FAILED")

            # Small delay between generations
            time.sleep(2)

    # Save results
    results_file = eval_dir / "evaluation_results.json"
    with open(results_file, "w") as f:
        json.dump(results, f, indent=2)

    print(f"\n{'='*60}")
    print(f"EVALUATION COMPLETE: {len(results)}/{total} images generated")
    print(f"Results saved to: {results_file}")
    print(f"{'='*60}")

    # Print summary
    print("\nSummary by checkpoint:")
    for cp in checkpoints:
        cp_results = [r for r in results if r["checkpoint"] == cp]
        print(f"\n  {cp}:")
        for r in cp_results:
            print(f"    {r['prompt']:20s} -> {r['file']}")


def main():
    import argparse

    parser = argparse.ArgumentParser(description="Eir LoRA Checkpoint Evaluator")
    parser.add_argument(
        "--prefix", default="eir_niflheimr", help="LoRA filename prefix"
    )
    parser.add_argument("--strength", type=float, default=0.8, help="LoRA strength")
    args = parser.parse_args()

    evaluate_checkpoints(args.prefix, args.strength)


if __name__ == "__main__":
    main()
