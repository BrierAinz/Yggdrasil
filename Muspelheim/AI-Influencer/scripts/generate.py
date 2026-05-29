#!/usr/bin/env python3
"""
Eir Content Generator — Batch pipeline for AI influencer content
===============================================================
Generates images, captions, and metadata for Eir's social media.

Usage:
    python scripts/generate.py --type portrait --count 5
    python scripts/generate.py --type landscape --count 3 --upscale
    python scripts/generate.py --caption portrait_casual --lang es
    python scripts/generate.py --batch  # Generate full day's content
"""

import argparse
import json
import random
import sys
from datetime import datetime
from pathlib import Path

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

try:
    import tomllib
except ImportError:
    import tomli as tomllib  # Python < 3.11

# ── Prompt Templates ──────────────────────────────────────────────

PROMPTS = {
    "portrait_casual": {
        "positive": (
            "masterpiece, best quality, photorealistic, 1girl, eir_niflheimr, "
            "pale skin, violet eyes with silver highlights, long black hair with purple tips, "
            "oval face, subtle freckles on cheeks, "
            "wearing oversized black sweater, silver runic necklace, "
            "casual relaxed pose, slight smile, "
            "natural window lighting, coffee shop interior, "
            "shot on Sony A7IV, 85mm f/1.4, shallow depth of field, film grain"
        ),
        "negative": "cartoon, anime, 3d, deformed, extra fingers, blurry, watermark, text",
        "size": "832x1216",
        "steps": 30,
        "cfg": 7,
    },
    "portrait_moody": {
        "positive": (
            "masterpiece, best quality, photorealistic, 1girl, eir_niflheimr, "
            "pale skin, intense violet eyes, long flowing black hair with purple highlights, "
            "wearing dark velvet dress, silver runic arm bands, "
            "serious contemplative expression, "
            "dramatic side lighting, fog, ancient stone corridor, "
            "velle draped shadows, cinematic, shot on Canon EOS R5, 50mm"
        ),
        "negative": "cartoon, anime, 3d, deformed, extra fingers, blurry, watermark, text, smile",
        "size": "832x1216",
        "steps": 35,
        "cfg": 8,
    },
    "portrait_artistic": {
        "positive": (
            "masterpiece, best quality, 1girl, eir_niflheimr, "
            "dark fantasy style, ethereal glow, runic symbols floating around, "
            "pale skin, violet eyes glowing, black hair flowing in wind, "
            "wearing ornate dark armor with silver runic engravings, "
            "volumetric lighting, particle effects, magical atmosphere, "
            "digital painting, trending on artstation"
        ),
        "negative": "photorealistic, photo, simple, plain, modern, casual",
        "size": "1024x1024",
        "steps": 35,
        "cfg": 8,
    },
    "landscape_dark_fantasy": {
        "positive": (
            "masterpiece, best quality, dark fantasy landscape, "
            "norwegian fjord at twilight, ancient runestones on cliff edge, "
            "northern lights, fog rising from dark water, "
            "old stone bridge over chasm, purple and green aurora borealis, "
            "volumetric fog, cinematic wide shot, epic scale, "
            "digital matte painting, trending on artstation"
        ),
        "negative": "person, character, text, watermark, cartoon, modern, city",
        "size": "1344x768",
        "steps": 30,
        "cfg": 7,
    },
    "detail_jewelry": {
        "positive": (
            "masterpiece, best quality, macro photography, "
            "silver runic jewelry, intricate celtic knotwork, "
            "moonstone gemstone centerpiece, "
            "dark velvet background, subtle rim lighting, "
            "shallow depth of field, focus stacking, "
            "product photography, luxury, minimalist"
        ),
        "negative": "person, face, hands, blurry, low detail, plastic, cheap",
        "size": "1024x1024",
        "steps": 30,
        "cfg": 7,
    },
    "aesthetic_room": {
        "positive": (
            "masterpiece, best quality, interior photography, "
            "dark aesthetic bedroom, velvet curtains, candles, "
            "silver ornaments, runic symbols on wall, "
            "bookshelf with old books, vinyl record player, "
            "warm amber lighting, moody atmosphere, "
            "cozy dark academia, hygge, architectural digest quality"
        ),
        "negative": "person, bright, colorful, modern, minimalist white, messy",
        "size": "1344x768",
        "steps": 30,
        "cfg": 7,
    },
}

CAPTION_TEMPLATES = {
    "portrait_casual": [
        "Un café, un libro, un momento de calma entre sombras 🗡️☕",
        "Los domingos son para descansar... incluso las hechiceras ✦",
        "Luz de ventana, taza de algo cálido, y el sonido de la lluvia 🌙",
        "Descanso temporal del portal. Midgard tiene sus encantos 🖤",
    ],
    "portrait_moody": [
        "Hay beauty en la oscuridad, si sabes dónde buscar 🌙",
        "Cada runa cuenta una historia. Esta es mía ✦",
        "Niebla y misterio. Así me encontró Midgard 🗡️",
        "Lo que se forja en la oscuridad, brilla diferente 🖤",
    ],
    "portrait_artistic": [
        "Cuando el código se convierte en arte mágico ✦",
        "Svartalfheim Sewing Circle: donde las runas se hacen imágenes 🗡️",
        "No es solo una imagen. Es un portal 🌙",
        "Cada pixel cargado de intención arcana 🖤",
    ],
    "landscape_dark_fantasy": [
        "Los fjords alumbrados por aurora. Mi hogar antes del portal 🌙",
        "Donde la tierra se encuentra con el cielo nórdico ✦",
        "Paisajes que solo existían en la memoria... hasta ahora 🗡️",
        "Svartalfheim tiene sus propios amaneceres. Este es uno 🖤",
    ],
    "detail_jewelry": [
        "Los detalles esconden la magia ✦ Detalle rúnico del día",
        "Cada joyería tiene un hechizo dentro. Esta es la mía 🗡️",
        "Plata, moonstone y siglos de historia nórdica 🌙",
        "Lo que llevas debería contar una historia 🖤",
    ],
    "aesthetic_room": [
        "Mi rincón en Midgard. Velas runicas incluidas 🕯️✦",
        "Hygge pero make it dark fantasy 🗡️",
        "Si pudierais ver mi estudio... bueno, aquí está 🌙",
        "Elminimalismo oscuro es mi lenguaje 🖤",
    ],
}

HASHTAG_SETS = {
    "portrait": ["#darkfantasyart", "#aesthetica", "#darkaesthetic", "#runic", "#nordicstyle"],
    "art": ["#conceptart", "#darkart", "#fantasyillustration", "#digitalart", "#aiartist"],
    "aesthetic": ["#darkfashion", "#minimaliststyle", "#silverjewelry", "#gothstyle", "#moody"],
}


def load_config(config_name: str) -> dict:
    """Load TOML config from config/ directory."""
    config_path = PROJECT_ROOT / "config" / f"{config_name}.toml"
    if not config_path.exists():
        print(f"⚠ Config not found: {config_path}")
        return {}
    with open(config_path, "rb") as f:
        return tomllib.load(f)


def generate_image(template_name: str, seed: int = None, output_dir: str = None) -> dict:
    """Generate a single image using SD WebUI API."""
    if template_name not in PROMPTS:
        print(f"✗ Unknown template: {template_name}")
        print(f"  Available: {', '.join(PROMPTS.keys())}")
        return {}

    template = PROMPTS[template_name]
    config = load_config("generation")

    if seed is None:
        seed = random.randint(0, 2**32 - 1)
    if output_dir is None:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_dir = PROJECT_ROOT / "content" / "posts" / f"{template_name}_{timestamp}"

    out_path = Path(output_dir)
    out_path.mkdir(parents=True, exist_ok=True)

    w, h = map(int, template["size"].split("x"))

    payload = {
        "prompt": template["positive"],
        "negative_prompt": template["negative"] + ", " + config.get("negative_prompt", {}).get("base", ""),
        "steps": template.get("steps", 30),
        "cfg_scale": template.get("cfg", 7),
        "sampler_name": config.get("defaults", {}).get("sampler", "DPM++ 2M Karras"),
        "width": w,
        "height": h,
        "seed": seed,
    }

    # Add LoRA if available
    lora_config = config.get("lora", {})
    if lora_config:
        lora_name = lora_config.get("name", "eir_niflheimr")
        lora_weight = lora_config.get("weight", 0.8)
        payload["prompt"] += f", <lora:{lora_name}:{lora_weight}>"

    print(f"  ◆ Template: {template_name}")
    print(f"  ◆ Seed: {seed}")
    print(f"  ◆ Size: {w}x{h}")
    print(f"  ◆ Output: {out_path}")

    # Save prompt metadata
    metadata = {
        "template": template_name,
        "seed": seed,
        "size": f"{w}x{h}",
        "steps": payload["steps"],
        "cfg": payload["cfg_scale"],
        "prompt": template["positive"],
        "negative": template["negative"],
        "timestamp": datetime.now().isoformat(),
    }
    meta_path = out_path / "metadata.json"
    with open(meta_path, "w", encoding="utf-8") as f:
        json.dump(metadata, f, indent=2, ensure_ascii=False)

    # Try to call SD WebUI API
    try:
        import requests
        api_url = "http://127.0.0.1:7860/sdapi/v1/txt2img"
        response = requests.post(api_url, json=payload, timeout=300)
        if response.status_code == 200:
            result = response.json()
            import base64
            img_data = base64.b64decode(result["images"][0])
            img_path = out_path / f"{template_name}_{seed}.png"
            with open(img_path, "wb") as f:
                f.write(img_data)
            print(f"  ✓ Image saved: {img_path}")
            metadata["output_file"] = str(img_path)
            with open(meta_path, "w", encoding="utf-8") as f:
                json.dump(metadata, f, indent=2, ensure_ascii=False)
        else:
            print(f"  ✗ SD API error: {response.status_code}")
            print(f"  → Prompt saved. Run manually in SD WebUI.")
    except (ImportError, ConnectionError, Exception) as e:
        print(f"  ⚠ SD WebUI not available: {e}")
        print(f"  → Prompt saved. Run manually in SD WebUI or Flux.")

    return metadata


def generate_caption(template_name: str, variation: int = None) -> str:
    """Generate a random caption from templates."""
    if template_name not in CAPTION_TEMPLATES:
        return ""
    captions = CAPTION_TEMPLATES[template_name]
    hashtags = HASHTAG_SETS.get(
        "portrait" if "portrait" in template_name else
        "art" if "art" in template_name else "aesthetic",
        HASHTAG_SETS["portrait"],
    )
    if variation is not None and variation < len(captions):
        caption = captions[variation]
    else:
        caption = random.choice(captions)
    hashtag_str = " ".join(hashtags)
    disclaimer = "\n\n✦ Generated with AI | Creado con IA"
    return f"{caption}\n\n{hashtag_str}{disclaimer}"


def generate_full_day():
    """Generate a full day's content: multiple images + captions."""
    print("◆ Eir Content Generator — Full Day Batch")
    print("=" * 50)

    day_plan = [
        ("portrait_casual", 2),
        ("portrait_moody", 1),
        ("portrait_artistic", 1),
        ("landscape_dark_fantasy", 1),
        ("detail_jewelry", 1),
        ("aesthetic_room", 1),
    ]

    results = []
    for template_name, count in day_plan:
        print(f"\n◆ Generating {count}x {template_name}...")
        for i in range(count):
            metadata = generate_image(template_name)
            caption = generate_caption(template_name)
            metadata["caption"] = caption
            results.append(metadata)
            print(f"  → Caption: {caption[:60]}...")

    print(f"\n◆ Batch complete: {len(results)} images")
    return results


def main():
    parser = argparse.ArgumentParser(description="Eir Content Generator")
    parser.add_argument("--type", choices=list(PROMPTS.keys()), help="Content type to generate")
    parser.add_argument("--count", type=int, default=1, help="Number of images")
    parser.add_argument("--caption", choices=list(CAPTION_TEMPLATES.keys()), help="Generate caption only")
    parser.add_argument("--batch", action="store_true", help="Generate full day's content")
    parser.add_argument("--seed", type=int, help="Specific seed for reproducibility")
    parser.add_argument("--output", type=str, help="Output directory")

    args = parser.parse_args()

    if args.batch:
        generate_full_day()
    elif args.caption:
        caption = generate_caption(args.caption)
        print(caption)
    elif args.type:
        for i in range(args.count):
            generate_image(args.type, seed=args.seed, output_dir=args.output)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()