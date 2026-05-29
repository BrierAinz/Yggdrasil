#!/usr/bin/env python3
"""
Eir LoRA Training Script
=========================
Trains a SDXL LoRA for the character Eir Niflheimr using Kohya sd-scripts.

Usage:
    python train_lora.py [--epochs 15] [--rank 32] [--lr 1e-4]

The trained LoRA will be saved to assets/lora/eir_niflheimr_sdxl.safetensors
"""

import argparse
import os
import subprocess
import sys
from pathlib import Path

# Paths
PROJECT_ROOT = Path("/mnt/d/Proyectos/Yggdrasil/Muspelheim/AI-Influencer")
KOHYA_DIR = PROJECT_ROOT / "tools" / "kohya_ss"
DATASET_DIR = PROJECT_ROOT / "assets" / "lora_dataset"
OUTPUT_DIR = PROJECT_ROOT / "assets" / "lora"
CHECKPOINT_PATH = Path("/home/brierainz/comfy/ComfyUI/models/checkpoints")


def find_sdxl_checkpoint():
    """Find SDXL checkpoint for training."""
    # Prefer Juggernaut XL, fall back to SDXL base
    for name in [
        "Juggernaut-XL_v9_RunDiffusionPhoto_v2.safetensors",
        "sd_xl_base_1.0.safetensors",
    ]:
        path = CHECKPOINT_PATH / name
        if path.exists():
            return str(path)
    # Also check for diffusers format
    diffusers = CHECKPOINT_PATH / "unet"
    if diffusers.exists():
        # Use diffusers path (parent of unet/)
        return str(CHECKPOINT_PATH)
    raise FileNotFoundError(f"No SDXL checkpoint found in {CHECKPOINT_PATH}")


def train_lora(epochs=15, rank=32, lr=1e-4, alpha=None):
    """Launch Kohya LoRA training."""
    if alpha is None:
        alpha = rank // 2

    output_dir = OUTPUT_DIR
    output_dir.mkdir(parents=True, exist_ok=True)

    checkpoint = find_sdxl_checkpoint()
    print(f"Using checkpoint: {checkpoint}")
    print(f"Dataset: {DATASET_DIR}")
    print(f"Output: {output_dir}")
    print(f"Rank: {rank}, Alpha: {alpha}, LR: {lr}, Epochs: {epochs}")
    print()

    # Build training command
    # Using accelerate for mixed precision training
    cmd = [
        sys.executable,
        str(KOHYA_DIR / "sdxl_train.py"),  # SDXL training script
        # OR use the LoRA-specific script
        # str(KOHYA_DIR / "sd-scripts" / "sdxl_train_network.py"),
        # Model
        "--pretrained_model_name_or_path",
        checkpoint,
        # Dataset
        "--train_data_dir",
        str(DATASET_DIR),
        "--caption_extension",
        ".txt",
        "--shuffle_caption",
        "--keep_tokens",
        "1",
        # Resolution
        "--resolution",
        "1024,1024",
        "--enable_bucket",
        "--min_bucket_reso",
        "512",
        "--max_bucket_reso",
        "1536",
        "--bucket_reso_steps",
        "64",
        # LoRA
        "--network_module",
        "networks.lora",
        "--network_dim",
        str(rank),
        "--network_alpha",
        str(alpha),
        "--network_dropout",
        "0.1",
        # Optimizer
        "--optimizer_type",
        "AdamW8bit",
        "--learning_rate",
        str(lr),
        "--text_encoder_lr",
        str(lr * 0.5),
        "--unet_lr",
        str(lr),
        "--lr_scheduler",
        "cosine",
        "--lr_warmup_steps",
        "100",
        # Training
        "--max_train_epochs",
        str(epochs),
        "--train_batch_size",
        "1",
        "--gradient_accumulation_steps",
        "4",
        "--mixed_precision",
        "bf16",
        "--save_every_n_epochs",
        "5",
        "--xformers",
        "--gradient_checkpointing",
        "--cache_latents",
        "--cache_text_encoder_outputs",
        # Output
        "--output_dir",
        str(output_dir),
        "--output_name",
        "eir_niflheimr_sdxl",
        "--save_model_as",
        "safetensors",
        "--save_precision",
        "fp16",
        # Sample generation during training
        "--sample_every_n_epochs",
        "5",
        "--sample_prompts",
        "eir_niflheimr, 1girl, solo, pale skin, silver-white hair with violet highlights, icy blue eyes, dark fantasy portrait",
    ]

    print("Command:")
    print(" \\\n  ".join(cmd))
    print()

    # Run training
    venv_python = str(KOHYA_DIR / "venv" / "bin" / "python")
    if os.path.exists(venv_python):
        cmd[0] = venv_python

    env = os.environ.copy()
    env["PYTHONPATH"] = str(KOHYA_DIR)

    try:
        result = subprocess.run(cmd, env=env, check=True)
        print("\nTraining complete!")
        print(f"LoRA saved to: {output_dir / 'eir_niflheimr_sdxl.safetensors'}")
    except subprocess.CalledProcessError as e:
        print(f"\nTraining failed with exit code {e.returncode}")
        return e.returncode
    except FileNotFoundError:
        print("\nTraining script not found. Check Kohya installation.")
        print("You may need to run training manually:")
        print(f"  cd {KOHYA_DIR}")
        print(f"  python sdxl_train_network.py <args>")
        return 1

    return 0


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Train Eir LoRA")
    parser.add_argument("--epochs", type=int, default=15)
    parser.add_argument("--rank", type=int, default=32)
    parser.add_argument("--lr", type=float, default=1e-4)
    parser.add_argument("--alpha", type=int, default=None)
    args = parser.parse_args()

    sys.exit(
        train_lora(
            epochs=args.epochs,
            rank=args.rank,
            lr=args.lr,
            alpha=args.alpha,
        )
    )
