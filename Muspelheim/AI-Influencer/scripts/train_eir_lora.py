#!/usr/bin/env python3
"""
Eir LoRA Training Launcher
===========================
Trains a SDXL LoRA for the character Eir Niflheimr using Kohya sd-scripts.

This script:
1. Validates the dataset
2. Generates the Kohya training command
3. Runs sdxl_train_network.py with correct params
4. Outputs the LoRA to assets/lora_output/

Usage:
    python3 train_lora.py [--epochs 15] [--lr 1e-4] [--rank 32]

Requirements:
    - Kohya sd-scripts in tools/kohya_ss/
    - PyTorch with CUDA in Kohya venv
    - SDXL base model in ~/comfy/ComfyUI/models/checkpoints/
    - Dataset in assets/lora_dataset/ (1024x1024 images + captions)
"""
import argparse
import json
import os
import subprocess
import sys
from pathlib import Path

# === Paths ===
PROJECT = Path("/mnt/d/Proyectos/Yggdrasil/Muspelheim/AI-Influencer")
KOHYA = PROJECT / "tools" / "kohya_ss"
DATASET = PROJECT / "assets" / "lora_dataset"
OUTPUT = PROJECT / "assets" / "lora_output"
SDXL_MODEL = (
    Path.home()
    / "comfy"
    / "ComfyUI"
    / "models"
    / "checkpoints"
    / "sd_xl_base_1.0.safetensors"
)
JUGGERNAUT = (
    Path.home()
    / "comfy"
    / "ComfyUI"
    / "models"
    / "checkpoints"
    / "Juggernaut-XL_v9_RunDiffusionPhoto_v2.safetensors"
)

# Kohya venv
KOHYA_PYTHON = KOHYA / "venv" / "bin" / "python3"
KOHYA_TRAIN = KOHYA / "sdxl_train_network.py"

TRIGGER_WORD = "eir_niflheimr"


def validate_dataset(dataset_dir: Path) -> tuple[int, int]:
    """Validate dataset has images and captions."""
    images = list(dataset_dir.glob("*.png")) + list(dataset_dir.glob("*.jpg"))
    captions = list(dataset_dir.glob("*.txt"))

    if not images:
        print(f"ERROR: No images found in {dataset_dir}")
        sys.exit(1)

    missing = 0
    for img in images:
        cap = img.with_suffix(".txt")
        if not cap.exists():
            print(f"  WARNING: Missing caption for {img.name}")
            missing += 1

    if missing > 0:
        print(f"  {missing} images missing captions (will use default)")

    # Check metadata.json
    meta = dataset_dir / "metadata.json"
    if meta.exists():
        data = json.loads(meta.read_text())
        print(f"  metadata.json: {len(data)} entries")
    else:
        print(f"  WARNING: No metadata.json found")

    return len(images), len(captions)


def find_checkpoint() -> Path:
    """Find best available SDXL checkpoint."""
    if JUGGERNAUT.exists():
        return JUGGERNAUT
    if SDXL_MODEL.exists():
        return SDXL_MODEL
    print("ERROR: No SDXL checkpoint found!")
    print(f"  Tried: {JUGGERNAUT}")
    print(f"  Tried: {SDXL_MODEL}")
    sys.exit(1)


def run_training(
    epochs: int = 15,
    lr: float = 1e-4,
    rank: int = 32,
    batch_size: int = 1,
    save_every: int = 5,
):
    """Run Kohya sdxl_train_network.py for LoRA training."""

    # Validate
    print("=" * 60)
    print("Eir LoRA Training")
    print("=" * 60)

    print("\n[1/4] Validating dataset...")
    n_images, n_captions = validate_dataset(DATASET)
    print(f"  Found {n_images} images, {n_captions} captions")

    print("\n[2/4] Checking environment...")
    if not KOHYA_PYTHON.exists():
        print(f"ERROR: Kohya venv not found at {KOHYA_PYTHON}")
        sys.exit(1)

    # Check PyTorch
    result = subprocess.run(
        [str(KOHYA_PYTHON), "-c", "import torch; print(torch.__version__)"],
        capture_output=True,
        text=True,
        timeout=10,
    )
    if result.returncode != 0:
        print(f"ERROR: PyTorch not working in Kohya venv")
        print(f"  {result.stderr}")
        sys.exit(1)
    torch_version = result.stdout.strip()
    print(f"  PyTorch: {torch_version}")

    # Check CUDA
    result = subprocess.run(
        [str(KOHYA_PYTHON), "-c", "import torch; print(torch.cuda.is_available())"],
        capture_output=True,
        text=True,
        timeout=10,
    )
    cuda_ok = result.stdout.strip() == "True"
    print(f"  CUDA: {'OK' if cuda_ok else 'NOT AVAILABLE'}")
    if not cuda_ok:
        print("  WARNING: CUDA not available, training will be very slow on CPU")

    # Check training script
    if not KOHYA_TRAIN.exists():
        print(f"ERROR: Kohya training script not found at {KOHYA_TRAIN}")
        sys.exit(1)
    print(f"  Training script: OK")

    # Find checkpoint
    print("\n[3/4] Finding SDXL checkpoint...")
    checkpoint = find_checkpoint()
    print(f"  Using: {checkpoint.name}")

    # Create output directory
    OUTPUT.mkdir(parents=True, exist_ok=True)

    # Build training command
    print(f"\n[4/4] Starting LoRA training...")
    print(f"  Epochs: {epochs}")
    print(f"  Learning rate: {lr}")
    print(f"  LoRA rank: {rank}")
    print(f"  Batch size: {batch_size}")
    print(f"  Save every: {save_every} epochs")
    print(f"  Output: {OUTPUT}")
    print()

    # Calculate steps
    steps_per_epoch = n_images // batch_size
    total_steps = steps_per_epoch * epochs

    cmd = [
        str(KOHYA_PYTHON),
        str(KOHYA_TRAIN),
        "--pretrained_model_name_or_path",
        str(checkpoint),
        "--train_data_dir",
        str(DATASET),
        "--output_dir",
        str(OUTPUT),
        "--output_name",
        f"eir_niflheimr_lora_r{rank}",
        "--save_model_as",
        "safetensors",
        "--prior_loss_weight",
        "1.0",
        "--network_module",
        "networks.lora",
        "--network_dim",
        str(rank),
        "--network_alpha",
        str(rank // 2),
        "--resolution",
        "1024,1024",
        "--train_batch_size",
        str(batch_size),
        "--learning_rate",
        str(lr),
        "--lr_scheduler",
        "cosine",
        "--lr_warmup_steps",
        "100",
        "--max_train_epochs",
        str(epochs),
        "--save_every_n_epochs",
        str(save_every),
        "--mixed_precision",
        "bf16",
        "--save_precision",
        "bf16",
        "--seed",
        "42",
        "--gradient_checkpointing",
        "--cache_latents",
        "--cache_text_encoder_outputs",
        "--xformers",
        "--sdpa",
        "--enable_bucket",
        "--min_bucket_reso",
        "768",
        "--max_bucket_reso",
        "1280",
        "--bucket_reso_steps",
        "64",
    ]

    # Also write the command to a script for reproducibility
    script_path = OUTPUT / "train_command.sh"
    script_path.write_text(
        "#!/bin/bash\n"
        + " \\\n  ".join(f'"{c}"' if " " in c else c for c in cmd)
        + "\n"
    )
    os.chmod(script_path, 0o755)
    print(f"  Training command saved to: {script_path}")
    print()

    # Run training
    print("Starting training...")
    print("-" * 60)
    try:
        process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            bufsize=1,
            universal_newlines=True,
        )
        for line in process.stdout:
            print(line, end="")
        process.wait()

        if process.returncode == 0:
            print("\n" + "=" * 60)
            print("TRAINING COMPLETE!")
            print(f"Output: {OUTPUT}")
            print(f"LoRA file: {OUTPUT}/eir_niflheimr_lora_r{rank}.safetensors")
            print("=" * 60)
        else:
            print(f"\nERROR: Training failed with exit code {process.returncode}")
            sys.exit(1)

    except KeyboardInterrupt:
        print("\nTraining interrupted by user")
        process.terminate()
        sys.exit(130)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Train Eir LoRA with Kohya sd-scripts")
    parser.add_argument(
        "--epochs", type=int, default=15, help="Number of training epochs"
    )
    parser.add_argument("--lr", type=float, default=1e-4, help="Learning rate")
    parser.add_argument("--rank", type=int, default=32, help="LoRA rank/dim")
    parser.add_argument("--batch-size", type=int, default=1, help="Batch size")
    parser.add_argument("--save-every", type=int, default=5, help="Save every N epochs")

    args = parser.parse_args()
    run_training(
        epochs=args.epochs,
        lr=args.lr,
        rank=args.rank,
        batch_size=args.batch_size,
        save_every=args.save_every,
    )
