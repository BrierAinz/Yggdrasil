#!/usr/bin/env python3
"""
Eir Instagram First Batch — 9 Grid Posts
==========================================
Generates 9 cohesive Instagram posts for the @eir.creates launch.

Post Types (3x3 grid = 9 posts):
  1. Heróico close-up — Presentación
  2. Half-body outfit — Estilo personal
  3. Dark fantasy landscape — Mundo de Eir
  4. Detail shot (hands/accessories) — Artesanía
  5. Moody portrait — Misterio
  6. Action/magic — Poder
  7. Serene moment — Vulnerabilidad
  8. Fashion editorial — Estética
  9. Storytelling scene — Lore

Uses SDXL via ComfyUI API. No LoRA yet — pure prompt engineering.
"""

import json
import os
import random
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

COMFY_URL = "http://127.0.0.1:8188"
OUTPUT_DIR = Path(
    "/mnt/d/Proyectos/Yggdrasil/Muspelheim/AI-Influencer/outputs/first_batch"
)
CHECKPOINT = "Juggernaut-XL_v9_RunDiffusionPhoto_v2.safetensors"
VAE = "sdxl_vae.safetensors"

OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# 9 Instagram posts — each with prompt, caption, and hashtags
POSTS = [
    {
        "id": 1,
        "type": "hero_closeup",
        "title": "Presentación",
        "prompt": "masterpiece, best quality, photorealistic, 1girl, eir_niflheimr, pale skin, sharp features, icy blue eyes, silver-white hair with violet highlights, slight smile, dark fantasy aesthetic, close-up portrait, rim lighting, dark background with violet mist, runic jewelry, detailed skin texture, cinematic lighting, 8k",
        "negative": "low quality, blurry, deformed, extra fingers, bad hands, watermark, text, logo, cartoon, anime, 3d render, plastic skin, flat lighting",
        "width": 768,
        "height": 1152,
        "caption": "I craft visions from the silence between worlds.\n\nSome call it art. I call it memory.\n\n✦ Dark Fantasy Digital Art ✦\n#darkfantasy #digitalart #aiart #fantasyart #portrait",
    },
    {
        "id": 2,
        "type": "half_body_outfit",
        "title": "Estilo Personal",
        "prompt": "masterpiece, best quality, photorealistic, 1girl, eir_niflheimr, pale skin, icy blue eyes, silver-white hair flowing, wearing dark velvet cloak with silver runic embroidery, fur-lined shoulders, ornate silver brooch with violet gem, dramatic lighting, medieval fantasy, half body, museum quality, detailed fabric texture, 8k",
        "negative": "low quality, blurry, deformed, extra fingers, bad hands, watermark, text, logo, cartoon, anime, 3d render, modern clothing, casual",
        "width": 768,
        "height": 1152,
        "caption": "Velvet and silver. Runes and silence.\n\nEvery thread tells a story from Svartalfheim.\n\n✦ Dark Fantasy Digital Art ✦\n#darkfantasy #medieval #cloak #silver #fantasyfashion",
    },
    {
        "id": 3,
        "type": "landscape",
        "title": "Mundo de Eir",
        "prompt": "masterpiece, best quality, photorealistic, 1girl, eir_niflheimr, standing on ancient stone bridge, dark enchanted forest, bioluminescent mushrooms, twisted trees, silver moonlight, flowing silver-white hair, dark robes, mystical atmosphere, epic landscape, cinematic wide shot, mist, fog, depth of field, 8k",
        "negative": "low quality, blurry, deformed, extra fingers, bad hands, watermark, text, urban, modern, bright colors, oversaturated",
        "width": 1024,
        "height": 1024,
        "caption": "The forest remembers what the world forgot.\n\nBetween the trees, the old magic still breathes.\n\n✦ World of Eir ✦\n#darkforest #fantasyworld #enchanted #bioluminescent #mystic",
    },
    {
        "id": 4,
        "type": "detail_shot",
        "title": "Artesanía",
        "prompt": "masterpiece, best quality, photorealistic, close-up detail of ornate silver gauntlet with runic engravings, violet gemstone embedded in silver ring, pale delicate hands, dark fabric background, depth of field, macro photography style, intricate metalwork details, reflected violet light, dark fantasy aesthetic, 8k",
        "negative": "low quality, blurry, deformed, extra fingers, bad hands, six fingers, watermark, text, modern, plastic, cheap",
        "width": 1024,
        "height": 1024,
        "caption": "Every rune was carved by hand. Every gem holds a frozen whisper.\n\n✦ The Craft ✦\n#runes #silver #jewelry #darkfantasy #craftsmanship",
    },
    {
        "id": 5,
        "type": "moody_portrait",
        "title": "Misterio",
        "prompt": "masterpiece, best quality, photorealistic, 1girl, eir_niflheimr, half face in shadow, one icy blue eye glowing in darkness, silver-white hair falling across face, mysterious expression, partial face illumination, dramatic chiaroscuro lighting, dark fantasy, film noir aesthetic, moody, atmospheric, 8k",
        "negative": "low quality, blurry, deformed, extra fingers, bad hands, watermark, text, bright, cheerful, flat lighting, oversaturated",
        "width": 768,
        "height": 1152,
        "caption": "What lurks in shadow, I illuminate.\nWhat hides in silence, I reveal.\n\n✦ Mystery ✦\n#darkportrait #chiaroscuro #shadow #mystery #darkaesthetic",
    },
    {
        "id": 6,
        "type": "action_magic",
        "title": "Poder",
        "prompt": "masterpiece, best quality, photorealistic, 1girl, eir_niflheimr, casting ice magic, crystal frost forming from outstretched hand, magical energy swirls in violet and silver, silver-white hair blowing dramatically, icy blue eyes glowing with power, dark throne room background, dynamic pose, frozen ground, magical particles, epic, cinematic, 8k",
        "negative": "low quality, blurry, deformed, extra fingers, bad hands, watermark, text, cartoon, anime, fire, warm colors, cheerful",
        "width": 768,
        "height": 1152,
        "caption": "Ice remembers. Ice endures.\n\nWhen the old words are spoken, the frost obeys.\n\n✦ Power ✦\n#icemagic #fantasyart #sorceress #powerful #magic",
    },
    {
        "id": 7,
        "type": "serene",
        "title": "Vulnerabilidad",
        "prompt": "masterpiece, best quality, photorealistic, 1girl, eir_niflheimr, serene gentle expression, reading an ancient tome, candlelit ancient Nordic library, silver-white hair cascading over shoulder, soft warm light from candles, peaceful, contemplative, wearing simple dark linen dress, vulnerability, intimate portrait, painterly, 8k",
        "negative": "low quality, blurry, deformed, extra fingers, bad hands, watermark, text, harsh lighting, action, dramatic, scary, horror",
        "width": 768,
        "height": 1152,
        "caption": "In the quiet hours, I read what the ancients wrote.\n\nSome spells are just poems that forgot they were magic.\n\n✦ Stillness ✦\n#reading #library #candlelight #peaceful #darkacademia",
    },
    {
        "id": 8,
        "type": "fashion_editorial",
        "title": "Estética",
        "prompt": "masterpiece, best quality, fashion editorial, photorealistic, 1girl, eir_niflheimr, high fashion pose, wearing avant-garde dark fantasy gown, silver and violet structured bodice, flowing translucent fabric, cinematic studio lighting, pale skin, silver-white hair styled elegantly, icy blue eyes, Vogue quality, editorial fashion photography, clean background, 8k",
        "negative": "low quality, blurry, deformed, extra fingers, bad hands, watermark, text, amateur, casual, modern street, sloppy",
        "width": 768,
        "height": 1152,
        "caption": "Dark fantasy meets high fashion.\n\nWhere Svartalfheim craftsmanship meets Midgard style.\n\n✦ Editorial ✦\n#darkfashion #avantgarde #editorial #style #gown",
    },
    {
        "id": 9,
        "type": "storytelling",
        "title": "Lore",
        "prompt": "masterpiece, best quality, photorealistic, 1girl, eir_niflheimr, standing at ancient rune-inscribed altar in misty Nordic forest, ritual candles, ancient stones with carved runes, offering bowl with violet flame, silver-white hair flowing in wind, dark robes, mystical ceremony, storytelling scene, fog rolling between trees, cinematic composition, epic, 8k",
        "negative": "low quality, blurry, deformed, extra fingers, bad hands, watermark, text, modern, urban, cartoon, anime, bright, cheerful",
        "width": 1024,
        "height": 1024,
        "caption": "At the altar of forgotten gods, I speak the names they dare not whisper.\n\nFrom Svartalfheim I came. Through Midgard I walk. Into legend I forge.\n\nThis is my story.\n\n✦ The Beginning ✦\n#norse #mythology #runes #ritual #darkfantasy #lore",
    },
]


def queue_prompt(prompt_data):
    """Queue a prompt to ComfyUI API and return the prompt_id."""
    data = json.dumps({"prompt": prompt_data}).encode("utf-8")
    req = urllib.request.Request(
        f"{COMFY_URL}/prompt", data=data, headers={"Content-Type": "application/json"}
    )
    try:
        response = urllib.request.urlopen(req, timeout=30)
        result = json.loads(response.read())
        return result.get("prompt_id")
    except urllib.error.HTTPError as e:
        print(f"  ERROR: HTTP {e.code} - {e.read().decode()[:200]}")
        return None
    except Exception as e:
        print(f"  ERROR: {e}")
        return None


def wait_for_completion(prompt_id, timeout=300):
    """Wait for a queued prompt to complete and return output images."""
    start = time.time()
    while time.time() - start < timeout:
        try:
            req = urllib.request.Request(f"{COMFY_URL}/history/{prompt_id}")
            response = urllib.request.urlopen(req, timeout=10)
            history = json.loads(response.read())
            if prompt_id in history:
                outputs = history[prompt_id].get("outputs", {})
                images = []
                for node_id, node_output in outputs.items():
                    if "images" in node_output:
                        for img in node_output["images"]:
                            images.append(
                                {
                                    "filename": img["filename"],
                                    "subfolder": img.get("subfolder", ""),
                                    "type": img.get("type", "output"),
                                }
                            )
                return images
        except Exception:
            pass
        time.sleep(2)
    return None


def download_image(filename, subfolder, img_type, dest_path):
    """Download an image from ComfyUI output."""
    url = f"{COMFY_URL}/view?filename={urllib.parse.quote(filename)}&subfolder={urllib.parse.quote(subfolder)}&type={img_type}"
    try:
        req = urllib.request.Request(url)
        response = urllib.request.urlopen(req, timeout=30)
        with open(dest_path, "wb") as f:
            f.write(response.read())
        return True
    except Exception as e:
        print(f"  ERROR downloading {filename}: {e}")
        return False


def build_workflow(post):
    """Build a ComfyUI API workflow for generating an image."""
    seed = random.randint(0, 2**32 - 1)

    return {
        "4": {  # Model loader
            "class_type": "CheckpointLoaderSimple",
            "inputs": {
                "ckpt_name": CHECKPOINT,
            },
        },
        "5": {  # Empty CLIP
            "class_type": "CLIPTextEncode",
            "inputs": {
                "text": post["prompt"],
                "clip": ["4", 1],
            },
        },
        "6": {  # Negative CLIP
            "class_type": "CLIPTextEncode",
            "inputs": {
                "text": post["negative"],
                "clip": ["4", 1],
            },
        },
        "7": {  # KSampler
            "class_type": "KSampler",
            "inputs": {
                "seed": seed,
                "steps": 30,
                "cfg": 7,
                "sampler_name": "dpmpp_2m",
                "scheduler": "karras",
                "denoise": 1,
                "model": ["4", 0],
                "positive": ["5", 0],
                "negative": ["6", 0],
                "latent_image": ["5", 0] if False else ["8", 0],
            },
        },
        "8": {  # Empty latent
            "class_type": "EmptyLatentImage",
            "inputs": {
                "width": post["width"],
                "height": post["height"],
                "batch_size": 1,
            },
        },
        "9": {  # VAE Decode
            "class_type": "VAEDecode",
            "inputs": {
                "samples": ["7", 0],
                "vae": ["4", 2],
            },
        },
        "10": {  # Save image
            "class_type": "SaveImage",
            "inputs": {
                "filename_prefix": f"eir_batch_{post['id']:02d}",
                "images": ["9", 0],
            },
        },
    }


def main():
    import urllib.parse

    print("=" * 60)
    print("Eir Instagram First Batch — 9 Posts")
    print("=" * 60)

    # Check ComfyUI is running
    try:
        urllib.request.urlopen(f"{COMFY_URL}/system_stats", timeout=5)
        print("✓ ComfyUI is running")
    except:
        print("✗ ComfyUI is NOT running! Start it first.")
        sys.exit(1)

    results = []

    for post in POSTS:
        print(f"\n[{post['id']}/9] Generating: {post['title']} ({post['type']})")
        print(f"  Size: {post['width']}x{post['height']}")

        # Build and queue workflow
        workflow = build_workflow(post)
        prompt_id = queue_prompt(workflow)

        if not prompt_id:
            print(f"  ✗ Failed to queue prompt")
            results.append(
                {"id": post["id"], "status": "error", "error": "queue_failed"}
            )
            continue

        print(f"  Prompt ID: {prompt_id}")

        # Wait for completion
        print(f"  Waiting for generation...")
        images = wait_for_completion(prompt_id, timeout=300)

        if not images:
            print(f"  ✗ Generation timed out")
            results.append({"id": post["id"], "status": "error", "error": "timeout"})
            continue

        # Download images
        for img in images:
            dest = OUTPUT_DIR / f"post_{post['id']:02d}_{post['type']}.png"
            if download_image(img["filename"], img["subfolder"], img["type"], dest):
                size_kb = dest.stat().st_size / 1024
                print(f"  ✓ Saved: {dest.name} ({size_kb:.0f}KB)")
                results.append(
                    {
                        "id": post["id"],
                        "type": post["type"],
                        "title": post["title"],
                        "status": "ok",
                        "file": str(dest),
                        "size_kb": size_kb,
                        "caption": post["caption"],
                        "seed": workflow["7"]["inputs"]["seed"],
                    }
                )
            else:
                print(f"  ✗ Failed to download")
                results.append(
                    {"id": post["id"], "status": "error", "error": "download_failed"}
                )

    # Save manifest
    manifest_path = OUTPUT_DIR / "manifest.json"
    with open(manifest_path, "w") as f:
        json.dump(results, f, indent=2, ensure_ascii=False)

    ok_count = sum(1 for r in results if r.get("status") == "ok")
    print(f"\n{'=' * 60}")
    print(f"Batch complete: {ok_count}/{len(POSTS)} posts generated")
    print(f"Manifest saved to: {manifest_path}")
    print(f"Output dir: {OUTPUT_DIR}")

    # Save captions file
    captions_path = OUTPUT_DIR / "captions.txt"
    with open(captions_path, "w") as f:
        for r in results:
            if r.get("status") == "ok":
                f.write(f"=== Post {r['id']}: {r['title']} ===\n")
                f.write(f"{r['caption']}\n\n")
    print(f"Captions saved to: {captions_path}")


if __name__ == "__main__":
    main()
