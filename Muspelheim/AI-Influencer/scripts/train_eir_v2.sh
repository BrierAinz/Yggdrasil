#!/bin/bash
# ============================================================
# Eir LoRA v2 — Training Launcher
# ============================================================
# Usage:
#   bash train_eir_v2.sh              # Train with optimized settings
#   bash train_eir_v2.sh --dry-run    # Print the command without running
# ============================================================

set -e

PROJECT="/mnt/d/Proyectos/Yggdrasil/Muspelheim/AI-Influencer"
KOHYA="$PROJECT/tools/kohya_ss"
PYTHON="$KOHYA/venv/bin/python3"
CONFIG="$PROJECT/config/lora/eir_v2_optimized.toml"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m'

echo -e "${CYAN}============================================================${NC}"
echo -e "${CYAN}  Eir Niflheimr LoRA v2 — Training Launcher${NC}"
echo -e "${CYAN}============================================================${NC}"

# Pre-flight checks
echo -e "\n${YELLOW}[1/5] Checking Kohya venv...${NC}"
if [ ! -f "$PYTHON" ]; then
    echo -e "${RED}ERROR: Kohya venv not found at $PYTHON${NC}"
    exit 1
fi
echo -e "${GREEN}  OK: venv found${NC}"

echo -e "\n${YELLOW}[2/5] Checking PyTorch + CUDA...${NC}"
TORCH_VER=$($PYTHON -c "import torch; print(torch.__version__)" 2>/dev/null)
CUDA_OK=$($PYTHON -c "import torch; print(torch.cuda.is_available())" 2>/dev/null)
if [ "$CUDA_OK" != "True" ]; then
    echo -e "${RED}ERROR: CUDA not available!${NC}"
    exit 1
fi
echo -e "${GREEN}  OK: PyTorch $TORCH_VER + CUDA${NC}"

echo -e "\n${YELLOW}[3/5] Checking dataset...${NC}"
DS_DIR="$PROJECT/assets/lora_dataset/eir_niflheimr"
IMG_COUNT=$(ls "$DS_DIR"/*.png 2>/dev/null | wc -l)
CAP_COUNT=$(ls "$DS_DIR"/*.txt 2>/dev/null | wc -l)
if [ "$IMG_COUNT" -lt 5 ]; then
    echo -e "${RED}ERROR: Only $IMG_COUNT images found (need at least 5)${NC}"
    exit 1
fi
echo -e "${GREEN}  OK: $IMG_COUNT images, $CAP_COUNT captions${NC}"

echo -e "\n${YELLOW}[4/5] Checking checkpoint...${NC}"
CKPT="$HOME/comfy/ComfyUI/models/checkpoints/Juggernaut-XL_v9_RunDiffusionPhoto_v2.safetensors"
if [ ! -f "$CKPT" ]; then
    echo -e "${RED}ERROR: Checkpoint not found at $CKPT${NC}"
    exit 1
fi
CKPT_SIZE=$(( $(stat -c%s "$CKPT" 2>/dev/null || stat -f%z "$CKPT" 2>/dev/null) / 1024 / 1024 ))
echo -e "${GREEN}  OK: Juggernaut XL v9 ($CKPT_SIZE MB)${NC}"

echo -e "\n${YELLOW}[5/5] Checking output dir...${NC}"
OUT_DIR="$PROJECT/assets/lora_output"
mkdir -p "$OUT_DIR"
echo -e "${GREEN}  OK: $OUT_DIR${NC}"

# Check for existing v2 outputs
EXISTING=$(ls "$OUT_DIR"/eir_niflheimr_v2_lora*.safetensors 2>/dev/null | wc -l)
if [ "$EXISTING" -gt 0 ]; then
    echo -e "\n${YELLOW}WARNING: Found $EXISTING existing v2 LoRA files in output dir${NC}"
    echo -e "${YELLOW}  They will NOT be overwritten (new checkpoints will be saved alongside)${NC}"
fi

# Build the command
CMD="cd $KOHYA && $PYTHON sdxl_train_network.py \
  --pretrained_model_name_or_path $CKPT \
  --train_data_dir $DS_DIR \
  --output_dir $OUT_DIR \
  --output_name eir_niflheimr_v2_lora \
  --save_model_as safetensors \
  --save_precision bf16 \
  --network_module networks.lora \
  --network_dim 32 \
  --network_alpha 16 \
  --network_dropout 0.1 \
  --resolution 1024,1024 \
  --enable_bucket \
  --bucket_reso_steps 64 \
  --min_bucket_reso 512 \
  --max_bucket_reso 2048 \
  --train_batch_size 1 \
  --max_train_steps 1800 \
  --save_every_n_steps 100 \
  --optimizer_type AdamW \
  --learning_rate 2e-4 \
  --text_encoder_lr 1e-4 \
  --unet_lr 2e-4 \
  --weight_decay 0.01 \
  --lr_scheduler cosine \
  --lr_warmup_steps 100 \
  --min_lr_ratio 0.1 \
  --min_snr_gamma 5 \
  --gradient_checkpointing \
  --mixed_precision bf16 \
  --full_bf16 \
  --xformers \
  --sdpa \
  --cache_latents \
  --cache_text_encoder_outputs \
  --keep_tokens 1 \
  --shuffle_caption \
  --tag_dropout 0.05 \
  --seed 42 \
  --persistent_workers \
  --max_data_loader_n_workers 2 \
  --log_prefix eir_v2"

# Dry run or execute
if [ "$1" == "--dry-run" ]; then
    echo -e "\n${CYAN}DRY RUN — Command that would be executed:${NC}"
    echo ""
    echo "$CMD" | tr -s ' ' | fold -s -w 100
    echo ""
    echo -e "${CYAN}Training params summary:${NC}"
    echo "  Steps:        1800 (~112 per image × 16 images)"
    echo "  Checkpoints:  Every 100 steps (18 checkpoints)"
    echo "  Optimizer:    AdamW (LR 2e-4, TE 1e-4)"
    echo "  Network:      LoRA dim=32, alpha=16, dropout=0.1"
    echo "  Estimated VRAM usage: ~8-9GB"
    echo "  Estimated time:       ~45-60 min on RTX 3060 12GB"
else
    echo -e "\n${GREEN}Starting training...${NC}"
    echo -e "${YELLOW}This will take approximately 45-60 minutes.${NC}"
    echo -e "${YELLOW}Checkpoints saved every 100 steps to:$OUT_DIR${NC}"
    echo ""
    eval $CMD
fi
