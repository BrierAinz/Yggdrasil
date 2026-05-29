#!/usr/bin/env python3
"""
Eir LoRA Dataset Curator
=========================
Selects the best images from the reference sheet for LoRA training.
Filters for: face visible, no obvious AI artifacts, consistent character.

LoRA Training Dataset Requirements:
- 15-30 high quality images
- Mix of close-ups and medium shots
- Consistent character appearance
- Square cropping (1024x1024 for SDXL)
- Clean backgrounds preferred
- No hands visible (or good hands)

This script:
1. Copies best images to lora_dataset directory
2. Creates .txt caption files for each image
3. Generates a training config for Kohya
"""

import json
import os
import shutil

SRC_DIR = "/mnt/d/Proyectos/Yggdrasil/Muspelheim/AI-Influencer/outputs/reference_sheet"
DST_DIR = "/mnt/d/Proyectos/Yggdrasil/Muspelheim/AI-Influencer/assets/lora_dataset"

# Best images for LoRA training (face visible, consistent, no hands)
# Prioritize: close-ups, portraits, clean backgrounds
SELECTED_IMAGES = {
    # Portraits - face focused (highest priority for character consistency)
    "eir_portrait_001.png": "eir_niflheimr, 1girl, solo, pale skin, silver-white hair with violet highlights, icy blue eyes, dark fantasy aesthetic, sharp features, high cheekbones, portrait, close-up face, detailed skin, moody lighting",
    "eir_01_portrait_closeup.png": "eir_niflheimr, 1girl, solo, pale skin, silver-white hair with violet highlights, icy blue eyes, close-up portrait, detailed face, runic tattoo, atmospheric lighting",
    "eir_01_portrait_medium.png": "eir_niflheimr, 1girl, solo, pale skin, silver-white hair with violet highlights, icy blue eyes, medium shot, dark flowing robes, silver embroidery, runic amulet",
    "eir_01_portrait_side_profile.png": "eir_niflheimr, 1girl, solo, pale skin, silver-white hair with violet highlights, side profile, silver hair flowing, rim lighting, dramatic atmosphere",
    # Mood - character personality
    "eir_02_mood_ethereal.png": "eir_niflheimr, 1girl, solo, pale skin, silver-white hair with violet highlights, icy blue eyes, ethereal mood, soft diffused lighting, violet aura, dreamlike, floating runes",
    "eir_02_mood_serene.png": "eir_niflheimr, 1girl, solo, pale skin, silver-white hair with violet highlights, icy blue eyes, serene expression, soft morning light, white fur-lined cloak, gentle smile",
    # Outfit variations - consistency with different clothing
    "eir_03_outfit_dark_robes.png": "eir_niflheimr, 1girl, solo, pale skin, silver-white hair with violet highlights, icy blue eyes, dark velvet robes, silver runic embroidery, hood down, scholar outfit, candlelit",
    "eir_03_outfit_armor.png": "eir_niflheimr, 1girl, solo, pale skin, silver-white hair with violet highlights, icy blue eyes, ornate dark plate armor, silver runic etchings, shoulder pauldrons, warrior",
    # Lighting - character under different conditions
    "eir_04_lighting_rim_light.png": "eir_niflheimr, 1girl, solo, pale skin, silver-white hair with violet highlights, icy blue eyes, rim lighting, silhouette outline, silver light, face in shadow",
    "eir_04_lighting_moonlit.png": "eir_niflheimr, 1girl, solo, pale skin, silver-white hair with violet highlights, icy blue eyes, moonlit night, cool blue and silver lighting, full moon behind, castle battlement",
    # Expressions - emotional range
    "eir_05_expression_contemplative.png": "eir_niflheimr, 1girl, solo, pale skin, silver-white hair with violet highlights, icy blue eyes, contemplative expression, hand on chin, dim candlelit study, soft focus",
    "eir_05_expression_mysterious.png": "eir_niflheimr, 1girl, solo, pale skin, silver-white hair with violet highlights, mysterious half-smile, partially hidden by shadow, one eye visible, theatrical lighting",
    # Background - character in context
    "eir_06_background_enchanted_forest.png": "eir_niflheimr, 1girl, solo, pale skin, silver-white hair with violet highlights, icy blue eyes, standing in enchanted dark forest, bioluminescent mushrooms, twisted trees, fog",
    "eir_06_background_ancient_library.png": "eir_niflheimr, 1girl, solo, pale skin, silver-white hair with violet highlights, icy blue eyes, ancient Nordic library, floor-to-ceiling bookshelves, floating tomes, warm candlelight",
    # Hair variations
    "eir_07_hair_braided.png": "eir_niflheimr, 1girl, solo, pale skin, silver-white hair in intricate Norse braids, violet highlights, icy blue eyes, silver hair accessories, runic beads, Viking hairstyle",
    # Special effects - magic
    "eir_09_special_magic_effect.png": "eir_niflheimr, 1girl, solo, pale skin, silver-white hair with violet highlights, icy blue eyes, casting ice magic, frost crystals from hands, frozen ground, magical glow",
}

os.makedirs(DST_DIR, exist_ok=True)

# Copy and caption images
copied = 0
for img_name, caption in SELECTED_IMAGES.items():
    src = os.path.join(SRC_DIR, img_name)
    # Number the images for training
    dst_name = f"eir_{copied+1:02d}.png"
    dst = os.path.join(DST_DIR, dst_name)
    cap_file = os.path.join(DST_DIR, f"eir_{copied+1:02d}.txt")

    if os.path.exists(src):
        shutil.copy2(src, dst)
        with open(cap_file, "w") as f:
            f.write(caption)
        # Get image size
        size_kb = os.path.getsize(dst) / 1024
        print(f"  [{copied+1:2d}] {img_name} -> {dst_name} ({size_kb:.0f}KB)")
        copied += 1
    else:
        print(f"  [SKIP] {img_name} not found")

print(f"\nCurated {copied} images for LoRA training")
print(f"Dataset: {DST_DIR}")

# Save dataset metadata
metadata = {
    "trigger_word": "eir_niflheimr",
    "model_target": "sdxl",
    "images": copied,
    "captions": "separate .txt files per image",
    "training_resolution": 1024,
    "source_images": list(SELECTED_IMAGES.keys()),
}

with open(os.path.join(DST_DIR, "metadata.json"), "w") as f:
    json.dump(metadata, f, indent=2)

print(f"\nMetadata saved to {DST_DIR}/metadata.json")
print(f"Trigger word: eir_niflheimr")
