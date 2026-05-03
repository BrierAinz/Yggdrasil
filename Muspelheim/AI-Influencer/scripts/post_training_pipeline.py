#!/usr/bin/env python3
"""
Eir LoRA v2 — Post-Training Pipeline
1. Find all checkpoints
2. Copy to ComfyUI
3. Generate comparison images for each
4. Output summary for manual review

Usage:
  python post_training_pipeline.py [--skip-gen] [--skip-copy]
"""
import json
import os
import re
import shutil
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

# --- Config ---
COMFY_URL = "http://localhost:8188"
PROJECT_DIR = Path("/mnt/d/Proyectos/Yggdrasil/Muspelheim/AI-Influencer")
LORA_OUTPUT_DIR = PROJECT_DIR / "assets" / "lora_output"
COMFY_LORA_DIR = Path(os.path.expanduser("~/comfy/ComfyUI/models/loras"))
WORKFLOW_TEMPLATE = PROJECT_DIR / "workflows" / "eir_lora_portrait_api.json"
EVAL_OUTPUT_DIR = PROJECT_DIR / "outputs" / "lora_evaluation"

# Evaluation prompts (consistent across checkpoints)
EVAL_PROMPTS = [
    {
        "name": "portrait_front",
        "prompt": "eir_niflheimr, 1girl, solo, pale skin, silver-white hair with violet highlights, icy blue eyes, high cheekbones, portrait close-up face looking at viewer, dark flowing robes with silver embroidery, northern lights aurora borealis, moonlight, masterpiece, best quality, photorealistic, 4k, detailed skin, cinematic lighting",
        "negative": "cartoon, anime, 3d render, deformed, bad anatomy, blurry, low quality, watermark, text, multiple people",
        "width": 832,
        "height": 1216,
    },
    {
        "name": "full_body_armor",
        "prompt": "eir_niflheimr, 1girl, solo, pale skin, silver-white hair with violet highlights, icy blue eyes, ornate dark plate armor with silver runic etchings, shoulder pauldrons, full body standing, confident pose, rune-carved stone temple interior, ethereal blue glow from runes, masterpiece, best quality, photorealistic, dramatic lighting, volumetric",
        "negative": "cartoon, anime, 3d, close-up, portrait only, casual, modern, blurry, low quality",
        "width": 832,
        "height": 1216,
    },
    {
        "name": "landscape_aurora",
        "prompt": "eir_niflheimr, 1girl, solo, pale skin, silver-white hair with violet highlights, icy blue eyes, standing on cliff edge, vast frozen nordic landscape, aurora borealis in sky, dark flowing cloak, wind blowing hair, epic scale, masterpiece, best quality, photorealistic, cinematic, volumetric lighting",
        "negative": "cartoon, anime, close-up, indoor, blurry, low quality, watermark",
        "width": 1216,
        "height": 832,
    },
]


def find_checkpoints():
    """Find all v2 checkpoint files sorted by step number."""
    checkpoints = []
    for f in sorted(LORA_OUTPUT_DIR.glob("eir_niflheimr_v2_lora-step*.safetensors")):
        match = re.search(r"step(\d+)", f.name)
        if match:
            step = int(match.group(1))
            checkpoints.append(
                {
                    "path": f,
                    "name": f.name,
                    "step": step,
                    "size_mb": f.stat().st_size / 1024**2,
                }
            )
    # Also check for final
    final = LORA_OUTPUT_DIR / "eir_niflheimr_v2_lora.safetensors"
    if final.exists():
        checkpoints.append(
            {
                "path": final,
                "name": final.name,
                "step": 9999,
                "size_mb": final.stat().st_size / 1024**2,
            }
        )
    checkpoints.sort(key=lambda x: x["step"])
    return checkpoints


def copy_to_comfy(checkpoint_name):
    """Copy checkpoint to ComfyUI models/loras/."""
    src = LORA_OUTPUT_DIR / checkpoint_name
    dst = COMFY_LORA_DIR / checkpoint_name
    if dst.exists():
        print(f"  Already in ComfyUI: {checkpoint_name}")
        return True
    if src.exists():
        shutil.copy2(src, dst)
        print(f"  Copied: {checkpoint_name}")
        return True
    print(f"  ERROR: Not found: {src}")
    return False


def check_comfyui():
    """Verify ComfyUI is running."""
    try:
        response = urllib.request.urlopen(f"{COMFY_URL}/system_stats", timeout=5)
        stats = json.loads(response.read())
        vram_free = stats["devices"][0].get("vram_free", 0) / 1024**3
        print(f"  ComfyUI running ✓ (VRAM free: {vram_free:.1f} GB)")
        return True
    except:
        print("  ComfyUI NOT running!")
        return False


def build_workflow(prompt_data, lora_name, seed=42, lora_strength=0.8):
    """Build ComfyUI workflow from template."""
    with open(WORKFLOW_TEMPLATE) as f:
        wf = json.load(f)

    wf["10"]["inputs"]["lora_name"] = lora_name
    wf["10"]["inputs"]["strength_model"] = lora_strength
    wf["10"]["inputs"]["strength_clip"] = lora_strength
    wf["5"]["inputs"]["width"] = prompt_data["width"]
    wf["5"]["inputs"]["height"] = prompt_data["height"]
    wf["6"]["inputs"]["text"] = prompt_data["prompt"]
    wf["7"]["inputs"]["text"] = prompt_data["negative"]
    wf["3"]["inputs"]["seed"] = seed
    wf["3"]["inputs"]["steps"] = 30
    wf["3"]["inputs"]["cfg"] = 7.0
    wf["9"]["inputs"][
        "filename_prefix"
    ] = f"eval_{lora_name.replace('.safetensors','')}_{prompt_data['name']}"
    return wf


def generate_image(workflow, timeout=180):
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
        print(f"    HTTP Error {e.code}: {e.read().decode()[:200]}")
        return None
    except Exception as e:
        print(f"    Error: {e}")
        return None

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

    print("    Timeout!")
    return None


def evaluate_all(skip_copy=False, skip_gen=False):
    """Main evaluation pipeline."""
    print("=" * 60)
    print("Eir LoRA v2 — Post-Training Evaluation Pipeline")
    print("=" * 60)

    # 1. Find checkpoints
    checkpoints = find_checkpoints()
    print(f"\nFound {len(checkpoints)} checkpoints:")
    for cp in checkpoints:
        print(f"  Step {cp['step']:5d} — {cp['name']} ({cp['size_mb']:.1f} MB)")

    if not checkpoints:
        print("No checkpoints found! Training may not have completed.")
        return

    # 2. Copy to ComfyUI
    if not skip_copy:
        print("\n--- Copying checkpoints to ComfyUI ---")
        for cp in checkpoints:
            copy_to_comfy(cp["name"])

    # 3. Check ComfyUI
    if not skip_gen:
        print("\n--- Checking ComfyUI ---")
        if not check_comfyui():
            print(
                "Start ComfyUI first: cd ~/comfy/ComfyUI && python3 main.py --listen --port 8188"
            )
            return

    # 4. Generate evaluation images
    results = []
    if not skip_gen:
        print(f"\n--- Generating evaluation images ---")
        print(
            f"  {len(checkpoints)} checkpoints x {len(EVAL_PROMPTS)} prompts = {len(checkpoints) * len(EVAL_PROMPTS)} images"
        )

        total = len(checkpoints) * len(EVAL_PROMPTS)
        current = 0

        for cp in checkpoints:
            print(f"\n  Checkpoint: {cp['name']} (step {cp['step']})")

            # Test at multiple strengths
            for strength in [0.7, 0.8, 0.9]:
                for prompt_data in EVAL_PROMPTS:
                    current += 1
                    label = f"[{current}/{total}]"
                    print(f"    {label} {prompt_data['name']} @ strength={strength}...")

                    wf = build_workflow(
                        prompt_data, cp["name"], seed=42, lora_strength=strength
                    )
                    wf["9"]["inputs"][
                        "filename_prefix"
                    ] = f"eval_step{cp['step']}_{prompt_data['name']}_s{strength}"

                    fname = generate_image(wf)

                    result = {
                        "checkpoint": cp["name"],
                        "step": cp["step"],
                        "prompt": prompt_data["name"],
                        "strength": strength,
                        "file": fname,
                        "seed": 42,
                    }
                    results.append(result)

                    if fname:
                        print(f"      -> {fname}")
                    else:
                        print(f"      -> FAILED")

                    time.sleep(1)  # Small delay between generations

    # 5. Save results
    EVAL_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    results_file = EVAL_OUTPUT_DIR / "evaluation_results.json"
    with open(results_file, "w") as f:
        json.dump(results, f, indent=2)

    print(f"\n{'=' * 60}")
    print(f"EVALUATION COMPLETE: {len(results)} images generated")
    print(f"Results: {results_file}")
    print(f"{'=' * 60}")

    # 6. Recommendation
    print("\n--- Best Checkpoint Selection Guide ---")
    print("Review the generated images in ComfyUI output folder.")
    print("Look for:")
    print("  1. Character consistency (face, hair, eyes)")
    print("  2. Prompt adherence (does it follow the prompt?)")
    print("  3. Artifact reduction (no extra limbs, weird textures)")
    print("  4. Best strength (0.7 vs 0.8 vs 0.9)")
    print("")
    print("Typical sweet spot: step 600-1200, strength 0.7-0.8")
    print("Early steps (100-300): undertrained, may lack detail")
    print("Late steps (1500-1800): may overfit, less flexible")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Eir LoRA v2 Post-Training Pipeline")
    parser.add_argument("--skip-gen", action="store_true", help="Skip image generation")
    parser.add_argument(
        "--skip-copy", action="store_true", help="Skip copying to ComfyUI"
    )
    args = parser.parse_args()

    evaluate_all(skip_copy=args.skip_copy, skip_gen=args.skip_gen)
