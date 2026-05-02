#!/usr/bin/env python3
"""
Eir Reference Sheet Generator — Batch ComfyUI API
===================================================
Generates 27 reference images of Eir across 9 categories (3 each).

Categories:
1. Portrait variations (close-up, medium, side profile)
2. Mood/atmosphere (ethereal, dark, serene)
3. Outfit variations (robes, armor, casual)
4. Lighting styles (rim light, golden hour, moonlit)
5. Expression variations (contemplative, fierce, mysterious)
6. Background/context (forest, throne, library)
7. Hair variations (flowing, braided, windswept)
8. Full body (standing, seated, dynamic pose)
9. Special (action, magic effect, silhouette)
"""

import json
import os
import sys
import time
import urllib.request

COMFY_URL = "http://127.0.0.1:8188"
OUTPUT_DIR = (
    "/mnt/d/Proyectos/Yggdrasil/Muspelheim/AI-Influencer/outputs/reference_sheet"
)
os.makedirs(OUTPUT_DIR, exist_ok=True)

# Base character description for Eir
EIR_BASE = (
    "masterpiece, best quality, photorealistic, 1girl, "
    "eir_niflheimr, pale skin, long silver-white hair with violet highlights, "
    "icy blue eyes, sharp features, high cheekbones, "
)

EIR_NEGATIVE = (
    "cartoon, anime, 3d render, low quality, blurry, deformed, extra fingers, "
    "missing fingers, bad anatomy, watermark, text, logo, signature, "
    "mutation, disfigured, poorly drawn face, poorly drawn hands, "
    "extra limbs, missing arms, extra arms, fused fingers, "
    "bad proportions, distorted face, duplicate, morbid"
)

CATEGORIES = {
    "01_portrait": [
        (
            "close-up portrait",
            f"{EIR_BASE} close-up face portrait, detailed skin texture, "
            "sharp focus on eyes, shallow depth of field, dark fantasy aesthetic, "
            "subtle runic tattoo on cheek, moody atmospheric lighting, 8k",
        ),
        (
            "medium portrait",
            f"{EIR_BASE} medium shot portrait from waist up, "
            "wearing dark flowing robes with silver embroidery, "
            "runic amulet necklace, dark background with purple ambient glow, "
            "cinematic lighting, film grain, 8k",
        ),
        (
            "side profile",
            f"{EIR_BASE} side profile portrait, looking away contemplatively, "
            "silver hair flowing in wind, dramatic rim lighting from behind, "
            "dark moody atmosphere with floating particles, bokeh background, 8k",
        ),
    ],
    "02_mood": [
        (
            "ethereal",
            f"{EIR_BASE} ethereal mood, soft diffused lighting, "
            "glowing violet aura around hair strands, mist particles, "
            "floating magical runes in background, dreamlike atmosphere, "
            "fantasy illustration style, 8k",
        ),
        (
            "dark_brooding",
            f"{EIR_BASE} dark brooding atmosphere, deep shadows, "
            "dramatic chiaroscuro lighting, red and violet accent lights, "
            "gothic architecture in background, thunderstorm sky, 8k",
        ),
        (
            "serene",
            f"{EIR_BASE} serene peaceful expression, soft morning light, "
            "light snow falling, winter forest background, "
            "white fur-lined cloak, gentle smile, kodak portra 400, 8k",
        ),
    ],
    "03_outfit": [
        (
            "dark_robes",
            f"{EIR_BASE} wearing dark flowing velvet robes, "
            "silver runic embroidery, hood down, ornate belt with potion vials, "
            "fantasy scholar outfit, dark library background, candlelit, 8k",
        ),
        (
            "armor",
            f"{EIR_BASE} wearing ornate dark plate armor, "
            "silver etchings with runic patterns, shoulder pauldrons, "
            "hooded cloak, warrior stance, stormy mountain background, 8k",
        ),
        (
            "casual_modern",
            f"{EIR_BASE} wearing oversize black hoodie and silver jewelry, "
            "modern gothic fashion, choker with rune pendant, "
            "urban night background with neon violet lights, cyberpunk undertone, 8k",
        ),
    ],
    "04_lighting": [
        (
            "rim_light",
            f"{EIR_BASE} dramatic rim lighting from behind, "
            "silhouette outline in silver light, face partially in shadow, "
            "hair glowing at edges, black background, studio lighting, 8k",
        ),
        (
            "golden_hour",
            f"{EIR_BASE} golden hour sunset lighting, "
            "warm orange and cool violet color contrast, "
            "autumn forest setting, lens flare, cinematic wide shot, 8k",
        ),
        (
            "moonlit",
            f"{EIR_BASE} moonlit night scene, cool blue and silver lighting, "
            "full moon behind, stars visible, standing on castle battlement, "
            "silver hair reflecting moonlight, long exposure look, 8k",
        ),
    ],
    "05_expression": [
        (
            "contemplative",
            f"{EIR_BASE} contemplative thoughtful expression, "
            "looking at distance, hand on chin, dim candlelit study, "
            "old books and scrolls around, soft focus background, 8k",
        ),
        (
            "fierce",
            f"{EIR_BASE} fierce determined expression, "
            "intense icy blue eyes, battle stance, glowing runes on hands, "
            "cracked ground, storm clouds, dynamic action shot, 8k",
        ),
        (
            "mysterious",
            f"{EIR_BASE} mysterious enigmatic half-smile, "
            "partially hidden by shadow, one eye visible glowing violet, "
            "smoke and mirrors effect, theatrical lighting, 8k",
        ),
    ],
    "06_background": [
        (
            "enchanted_forest",
            f"{EIR_BASE} standing in enchanted dark forest, "
            "bioluminescent mushrooms and plants, twisted ancient trees, "
            "fog rolling through, violet and teal color palette, 8k",
        ),
        (
            "throne_room",
            f"{EIR_BASE}坐在暗色哥特式王座上, "
            "ornate dark throne room, towering pillars, "
            "candelabras with purple flames, grand hall, 8k",
        ),
        (
            "ancient_library",
            f"{EIR_BASE} in ancient Nordic library, "
            "floor-to-ceiling bookshelves, floating magical tomes, "
            "warm candlelight, scrolls with runic writing, 8k",
        ),
    ],
    "07_hair": [
        (
            "flowing",
            f"{EIR_BASE} long silver-white hair flowing freely in magical wind, "
            "hair strands illuminated by violet light, dynamic hair movement, "
            "dark background, studio shot, 8k",
        ),
        (
            "braided",
            f"{EIR_BASE} hair in intricate Norse braids, "
            "silver hair accessories, small runic beads woven in, "
            "Viking-inspired hairstyle, side profile, detailed braid work, 8k",
        ),
        (
            "windswept",
            f"{EIR_BASE} windswept hair wildly flowing, "
            "snowstorm setting, icicles in hair, eyes glowing blue, "
            "fierce weather, dramatic wide shot, 8k",
        ),
    ],
    "08_fullbody": [
        (
            "standing",
            f"{EIR_BASE} full body standing pose, "
            "dark fantasy robes flowing, silver staff with glowing crystal, "
            "dramatic mountain cliff edge, wind blowing clothes, epic fantasy landscape, 8k",
        ),
        (
            "seated",
            f"{EIR_BASE} seated casually on stone steps, "
            "relaxed pose, dark leather outfit with silver accents, "
            "ancient Nordic ruins behind, moss and ivy, afternoon light, 8k",
        ),
        (
            "dynamic",
            f"{EIR_BASE} dynamic action pose, "
            "mid-cast spell, runic circles glowing around hands, "
            "hair and robes swirling dramatically, magic energy particles, 8k",
        ),
    ],
    "09_special": [
        (
            "magic_effect",
            f"{EIR_BASE} casting ice magic, "
            "frost crystals emanating from hands, frozen ground, "
            "ice particles floating, magical glow, "
            "dynamic composition, tilted angle, 8k",
        ),
        (
            "silhouette",
            f"{EIR_BASE} dark silhouette against massive full moon, "
            "cape flowing dramatically, sword drawn, "
            "iconic heroic composition, minimal colors, poster art, 8k",
        ),
        (
            "mirror_reflection",
            f"{EIR_BASE} looking at reflection in dark mirror, "
            "reflection shows a different version with glowing violet eyes, "
            "cracked mirror frame with runic symbols, psychological depth, 8k",
        ),
    ],
}


def make_workflow(prompt_positive, prompt_negative, width=768, height=1152, seed=None):
    """Create a ComfyUI API workflow for SDXL text2img."""
    if seed is None:
        import random

        seed = random.randint(0, 2**32 - 1)

    return {
        "3": {
            "class_type": "KSampler",
            "inputs": {
                "seed": seed,
                "steps": 30,
                "cfg": 7.0,
                "sampler_name": "dpmpp_2m",
                "scheduler": "karras",
                "denoise": 1.0,
                "model": ["4", 0],
                "positive": ["6", 0],
                "negative": ["7", 0],
                "latent_image": ["5", 0],
            },
        },
        "4": {
            "class_type": "CheckpointLoaderSimple",
            "inputs": {"ckpt_name": "sd_xl_base_1.0.safetensors"},
        },
        "5": {
            "class_type": "EmptyLatentImage",
            "inputs": {"width": width, "height": height, "batch_size": 1},
        },
        "6": {
            "class_type": "CLIPTextEncode",
            "inputs": {"text": prompt_positive, "clip": ["4", 1]},
        },
        "7": {
            "class_type": "CLIPTextEncode",
            "inputs": {"text": prompt_negative, "clip": ["4", 1]},
        },
        "8": {
            "class_type": "VAEDecode",
            "inputs": {"samples": ["3", 0], "vae": ["4", 2]},
        },
        "9": {
            "class_type": "SaveImage",
            "inputs": {
                "filename_prefix": "eir_{category}_{variant}",
                "images": ["8", 0],
            },
        },
    }


def submit_workflow(workflow):
    """Submit a workflow to ComfyUI and return prompt_id."""
    data = json.dumps({"prompt": workflow}).encode("utf-8")
    req = urllib.request.Request(
        f"{COMFY_URL}/prompt", data=data, headers={"Content-Type": "application/json"}
    )
    resp = urllib.request.urlopen(req, timeout=30)
    result = json.loads(resp.read())
    return result.get("prompt_id")


def poll_completion(prompt_id, timeout=300):
    """Poll ComfyUI until the workflow completes."""
    start = time.time()
    while time.time() - start < timeout:
        time.sleep(2)
        try:
            req = urllib.request.Request(f"{COMFY_URL}/history/{prompt_id}")
            resp = urllib.request.urlopen(req, timeout=10)
            hist = json.loads(resp.read())
            entry = hist.get(prompt_id)
            if entry:
                status = entry.get("status", {})
                if status.get("completed", False):
                    return entry.get("outputs", {})
                if status.get("status_str") == "error":
                    return {"error": status}
        except Exception:
            continue
    return {"error": "timeout"}


def download_image(filename, subfolder="", output_path=""):
    """Download a generated image from ComfyUI."""
    params = f"filename={filename}&subfolder={subfolder}&type=output"
    url = f"{COMFY_URL}/view?{params}"
    req = urllib.request.Request(url)
    resp = urllib.request.urlopen(req, timeout=30)
    data = resp.read()

    if not output_path:
        output_path = os.path.join(OUTPUT_DIR, filename)

    with open(output_path, "wb") as f:
        f.write(data)
    return output_path


# ============================================================
# Main generation loop
# ============================================================


def main():
    total = sum(len(cats) for cats in CATEGORIES.values())
    count = 0
    results = []

    print(f"\n{'='*60}")
    print(f"  Eir Reference Sheet Generator")
    print(f"  Generating {total} images across {len(CATEGORIES)} categories")
    print(f"{'='*60}\n")

    for category, variants in CATEGORIES.items():
        for i, (variant_name, prompt) in enumerate(variants, 1):
            count += 1
            filename_prefix = f"eir_{category}_{variant_name}"
            print(
                f"[{count}/{total}] {category}/{variant_name}...", end=" ", flush=True
            )

            # Create workflow
            workflow = make_workflow(
                prompt_positive=prompt,
                prompt_negative=EIR_NEGATIVE,
                width=768,
                height=1152,
                seed=random.randint(0, 2**32 - 1),
            )
            # Fix filename prefix
            workflow["9"]["inputs"]["filename_prefix"] = filename_prefix

            try:
                # Submit
                prompt_id = submit_workflow(workflow)

                # Wait for completion
                outputs = poll_completion(prompt_id, timeout=300)

                if "error" in outputs:
                    print(f"ERROR: {outputs['error']}")
                    results.append(
                        {
                            "category": category,
                            "variant": variant_name,
                            "status": "error",
                            "error": str(outputs["error"]),
                        }
                    )
                    continue

                # Download images
                for node_id, node_output in outputs.items():
                    for img in node_output.get("images", []):
                        src_name = img["filename"]
                        dst_name = f"{filename_prefix}{os.path.splitext(src_name)[1]}"
                        dst_path = os.path.join(OUTPUT_DIR, dst_name)
                        download_image(src_name, img.get("subfolder", ""), dst_path)
                        size_kb = os.path.getsize(dst_path) / 1024
                        print(f"OK ({size_kb:.0f}KB)")
                        results.append(
                            {
                                "category": category,
                                "variant": variant_name,
                                "status": "ok",
                                "file": dst_path,
                                "size_kb": size_kb,
                            }
                        )

            except Exception as e:
                print(f"ERROR: {e}")
                results.append(
                    {
                        "category": category,
                        "variant": variant_name,
                        "status": "error",
                        "error": str(e),
                    }
                )

    # Summary
    ok = sum(1 for r in results if r["status"] == "ok")
    err = sum(1 for r in results if r["status"] == "error")
    print(f"\n{'='*60}")
    print(f"  Done! {ok} images generated, {err} errors")
    print(f"  Output: {OUTPUT_DIR}")
    print(f"{'='*60}\n")

    # Save manifest
    manifest_path = os.path.join(OUTPUT_DIR, "manifest.json")
    with open(manifest_path, "w") as f:
        json.dump(results, f, indent=2, ensure_ascii=False)
    print(f"  Manifest saved: {manifest_path}")


import random

if __name__ == "__main__":
    main()
