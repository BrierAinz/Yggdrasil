#!/usr/bin/env python3
"""
Eir LoRA Training Pipeline — Kohya_ss
========================================
Prepara el dataset y lanza el entrenamiento del LoRA de Eir.

Requisitos:
- Kohya_ss instalado: https://github.com/kohya-ss/sd-scripts
- 20-30 imágenes de referencia de Eir (en assets/reference_sheets/)
- GPU con >=12GB VRAM (RTX 3060 12GB funciona)

Uso:
    python scripts/train_lora.py --prepare     # Preparar dataset
    python scripts/train_lora.py --train       # Lanzar entrenamiento
    python scripts/train_lora.py --test         # Generar imágenes de test
"""

import argparse
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent
REFERENCE_DIR = PROJECT_ROOT / "assets" / "reference_sheets"
OUTPUT_DIR = PROJECT_ROOT / "assets" / "lora"
DATASET_DIR = PROJECT_ROOT / "assets" / "dataset"

# ── LoRA Training Config ─────────────────────────────────────────

LORA_CONFIG = {
    # Model base
    "pretrained_model_name_or_path": "sd_xl_base_1.0.safetensors",
    "vae": "sdxl_vae.safetensors",
    # LoRA params
    "network_module": "networks.lora",
    "network_dim": 32,  # LoRA rank (16-64, más alto = más detalle)
    "network_alpha": 16,  # Alpha (normalmente dim/2)
    "network_args": "",
    # Training
    "learning_rate": 1e-4,
    "text_encoder_lr": 5e-5,
    "unet_lr": 1e-4,
    "lr_scheduler": "cosine",
    "lr_warmup_steps": 100,
    "train_batch_size": 1,  # RTX 3060 12GB: batch 1
    "max_train_steps": 2000,  # 20-30 imágenes × ~70 epochs = ~2000 steps
    "save_every_n_epochs": 5,
    "mixed_precision": "bf16",  # RTX 3060 soporta bf16
    "save_precision": "bf16",
    "optimizer_type": "AdamW8bit",  # Memoria eficiente
    "gradient_accumulation_steps": 2,
    "cache_latents": True,
    "cache_latents_to_disk": True,
    # Output
    "output_name": "eir_niflheimr",
    "output_dir": str(OUTPUT_DIR),
    "save_model_as": "safetensors",
    # Resolution
    "resolution": "832,1216",  # Portrait aspect ratio
    "enable_bucket": True,  # Permite variar aspect ratios
    # Captions
    "caption_extension": ".txt",
    "keep_tokens": 1,  # Mantener trigger word como primer token
}

TRIGGER_WORD = "eir_niflheimr"

# ── Caption templates per image type ──────────────────────────────

CAPTION_TEMPLATES = {
    "front_face": (
        f"{TRIGGER_WORD}, 1girl, front face, looking at viewer, "
        "pale skin, violet eyes, long black hair with purple tips, "
        "oval face, subtle freckles, upper body portrait, "
        "simple background, studio lighting"
    ),
    "side_profile": (
        f"{TRIGGER_WORD}, 1girl, side profile, looking away, "
        "pale skin, violet eye, long black hair flowing, "
        "sharp jawline, silver earrings, "
        "dark background, dramatic side lighting"
    ),
    "three_quarter": (
        f"{TRIGGER_WORD}, 1girl, three quarter view, "
        "pale skin, violet eyes, long black hair with purple tips, "
        "silver runic necklace, "
        "neutral expression, soft lighting"
    ),
    "full_body": (
        f"{TRIGGER_WORD}, 1girl, full body, standing, "
        "pale skin, violet eyes, long black hair, "
        "wearing dark outfit with silver accents, "
        "boots, full length pose, fashion photography"
    ),
    "close_up": (
        f"{TRIGGER_WORD}, 1girl, close up face, "
        "pale skin, intense violet eyes detailed, "
        "long black hair framing face, silver runic necklace, "
        "subtle freckles on nose and cheeks, "
        "macro photography, detailed skin texture"
    ),
    "casual": (
        f"{TRIGGER_WORD}, 1girl, casual pose, "
        "pale skin, violet eyes, long black hair loose, "
        "wearing oversized black sweater, relaxed, "
        "indoor natural lighting, coffee shop aesthetic"
    ),
    "moody": (
        f"{TRIGGER_WORD}, 1girl, moody expression, "
        "pale skin, dark violet eyes, long black hair, "
        "wearing dark velvet dress, serious, "
        "dramatic lighting, fog, stone corridor background"
    ),
    "artistic": (
        f"{TRIGGER_WORD}, 1girl, dark fantasy style, "
        "pale skin, glowing violet eyes, flowing black hair in wind, "
        "ornate dark armor with silver runic engravings, "
        "magical atmosphere, digital painting"
    ),
}


def prepare_dataset():
    """Prepara el dataset para entrenamiento de LoRA."""
    print("◆ Eir LoRA Training — Dataset Preparation")
    print("=" * 50)

    # Check reference images
    if not REFERENCE_DIR.exists():
        print(f"  ✗ Reference dir not found: {REFERENCE_DIR}")
        print(f"  → Create it and add 20-30 reference images")
        REFERENCE_DIR.mkdir(parents=True, exist_ok=True)
        return False

    images = (
        list(REFERENCE_DIR.glob("*.png"))
        + list(REFERENCE_DIR.glob("*.jpg"))
        + list(REFERENCE_DIR.glob("*.webp"))
    )
    print(f"  ◆ Found {len(images)} reference images")

    if len(images) < 15:
        print(f"  ⚠ Need at least 15-30 images for good LoRA training")
        print(f"  → Currently have {len(images)}")
        print(f"  → Add more images to {REFERENCE_DIR}")

    # Create dataset directory
    DATASET_DIR.mkdir(parents=True, exist_ok=True)

    # Create training metadata
    image_subdir = DATASET_DIR / "10_eir"
    image_subdir.mkdir(parents=True, exist_ok=True)

    print(f"\n  ◆ Preparing dataset in {DATASET_DIR}...")

    caption_count = 0
    for i, img_path in enumerate(images):
        # Copy image
        dest = image_subdir / f"eir_{i:03d}{img_path.suffix}"
        shutil.copy2(img_path, dest)

        # Create caption file
        caption_type = list(CAPTION_TEMPLATES.keys())[i % len(CAPTION_TEMPLATES)]
        caption = CAPTION_TEMPLATES[caption_type]
        caption_file = image_subdir / f"eir_{i:03d}.txt"
        with open(caption_file, "w", encoding="utf-8") as f:
            f.write(caption)
        caption_count += 1

        print(f"  ✓ {dest.name} → {caption_type}")

    # Create metadata.json for Kohya
    metadata = {
        "models": [
            {
                "name": "eir_niflheimr",
                "trigger_word": TRIGGER_WORD,
                "images": len(images),
                "captions": caption_count,
                "training_steps": LORA_CONFIG["max_train_steps"],
            }
        ]
    }
    metadata_path = DATASET_DIR / "metadata.json"
    with open(metadata_path, "w", encoding="utf-8") as f:
        json.dump(metadata, f, indent=2)

    print(f"\n  ◆ Dataset ready:")
    print(f"    Images: {len(images)}")
    print(f"    Captions: {caption_count}")
    print(f"    Trigger word: {TRIGGER_WORD}")
    print(f"    Max steps: {LORA_CONFIG['max_train_steps']}")
    return True


def generate_training_script():
    """Genera el script de entrenamiento para Kohya_ss."""
    script_dir = OUTPUT_DIR / "training_scripts"
    script_dir.mkdir(parents=True, exist_ok=True)

    # Generate accelerate config
    accelerate_config = """
compute_environment: LOCAL_MACHINE
debug: false
distributed_type: 'NO'
downcast_bf16: 'no'
gpu_ids: all
machine_rank: 0
main_training_function: main
mixed_precision: bf16
num_machines: 1
num_processes: 1
rdzv_backend: static
same_network: true
tpu_env: []
tpu_use_cluster: false
tpu_use_sudo: false
use_cpu: false
"""
    config_path = script_dir / "accelerate_config.yaml"
    with open(config_path, "w") as f:
        f.write(accelerate_config.strip())

    # Generate training command
    comfy_path = Path.home() / "comfy" / "ComfyUI"
    model_path = (
        comfy_path
        / "models"
        / "checkpoints"
        / LORA_CONFIG["pretrained_model_name_or_path"]
    )
    dataset_path = DATASET_DIR / "10_eir"
    output_path = OUTPUT_DIR

    # Build command
    cmd_parts = [
        "accelerate launch",
        f"--config_file={config_path}",
        f"{Path.home()}/kohya_ss/sd-scripts/sdxl_train_network.py",
        f"--pretrained_model_name_or_path={model_path}",
        f"--train_data_dir={dataset_path}",
        f"--output_dir={output_path}",
        f"--output_name={LORA_CONFIG['output_name']}",
        f"--resolution={LORA_CONFIG['resolution']}",
        f"--train_batch_size={LORA_CONFIG['train_batch_size']}",
        f"--max_train_steps={LORA_CONFIG['max_train_steps']}",
        f"--learning_rate={LORA_CONFIG['learning_rate']}",
        f"--lr_scheduler={LORA_CONFIG['lr_scheduler']}",
        f"--lr_warmup_steps={LORA_CONFIG['lr_warmup_steps']}",
        f"--network_module={LORA_CONFIG['network_module']}",
        f"--network_dim={LORA_CONFIG['network_dim']}",
        f"--network_alpha={LORA_CONFIG['network_alpha']}",
        f"--mixed_precision={LORA_CONFIG['mixed_precision']}",
        f"--save_precision={LORA_CONFIG['save_precision']}",
        f"--save_every_n_epochs={LORA_CONFIG['save_every_n_epochs']}",
        f"--save_model_as={LORA_CONFIG['save_model_as']}",
        f"--caption_extension={LORA_CONFIG['caption_extension']}",
        f"--keep_tokens={LORA_CONFIG['keep_tokens']}",
        f"--enable_bucket" if LORA_CONFIG["enable_bucket"] else "",
        f"--cache_latents" if LORA_CONFIG["cache_latents"] else "",
        f"--gradient_accumulation_steps={LORA_CONFIG['gradient_accumulation_steps']}",
        f"--optimizer_type={LORA_CONFIG['optimizer_type']}",
        f"--text_encoder_lr={LORA_CONFIG['text_encoder_lr']}",
        f"--unet_lr={LORA_CONFIG['unet_lr']}",
        f"--xformers",
        f"--sdpa",
    ]

    script_content = f"""#!/bin/bash
# Eir LoRA Training Script
# Generated by train_lora.py
# ==========================================

set -e

echo "◆ Eir LoRA Training"
echo "  Trigger word: {TRIGGER_WORD}"
echo "  Model: {LORA_CONFIG['pretrained_model_name_or_path']}"
echo "  Steps: {LORA_CONFIG['max_train_steps']}"
echo "  Batch: {LORA_CONFIG['train_batch_size']}"
echo ""

# Check Kohya_ss
if [ ! -d "$HOME/kohya_ss/sd-scripts" ]; then
    echo "✗ Kohya_ss not found at $HOME/kohya_ss/sd-scripts"
    echo "  Install: git clone https://github.com/kohya-ss/sd-scripts.git $HOME/kohya_ss/sd-scripts"
    echo "  Then: cd $HOME/kohya_ss/sd-scripts && pip install -r requirements.txt"
    exit 1
fi

# Check model
if [ ! -f "{model_path}" ]; then
    echo "✗ Base model not found: {model_path}"
    echo "  Download first with: comfy model download ..."
    exit 1
fi

# Check dataset
if [ ! -d "{dataset_path}" ]; then
    echo "✗ Dataset not found: {dataset_path}"
    echo "  Run: python scripts/train_lora.py --prepare"
    exit 1
fi

echo "◆ Starting training..."
echo ""

{' '.join(cmd_parts)}

echo ""
echo "◆ Training complete!"
echo "  LoRA saved to: {output_path}"
echo "  Copy to ComfyUI: cp {output_path}/*.safetensors {comfy_path}/models/loras/"
"""
    script_path = script_dir / "train_eir.sh"
    with open(script_path, "w") as f:
        f.write(script_content)
    os.chmod(script_path, 0o755)

    print(f"  ✓ Training script generated: {script_path}")
    print(f"  ✓ Accelerate config: {config_path}")
    return script_path


def main():
    parser = argparse.ArgumentParser(description="Eir LoRA Training Pipeline")
    parser.add_argument(
        "--prepare", action="store_true", help="Prepare dataset from reference images"
    )
    parser.add_argument(
        "--train",
        action="store_true",
        help="Generate training script (requires Kohya_ss)",
    )
    parser.add_argument(
        "--test", action="store_true", help="Generate test images with trained LoRA"
    )
    args = parser.parse_args()

    if args.prepare:
        prepare_dataset()
    elif args.train:
        script_path = generate_training_script()
        print(f"\n  ◆ Run: bash {script_path}")
    elif args.test:
        print("  ◆ LoRA test requires ComfyUI server running")
        print("  → Use scripts/generate.py with LoRA config")
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
