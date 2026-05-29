#!/usr/bin/env bash
# ============================================================
# Eir Niflheimr LoRA v2 — Training Script (CORRECTED)
# ============================================================
# FIXES:
#   - train_data_dir must be PARENT of subfolder named NN_name
#   - Cannot use cache_text_encoder_outputs with shuffle_caption
#   - caption_tag_dropout_rate instead of tag_dropout
#   - lr_scheduler_min_lr_ratio (not min_lr_ratio)
# ============================================================
set -euo pipefail

KOHYA_DIR="/mnt/d/Proyectos/Yggdrasil/Muspelheim/AI-Influencer/tools/kohya_ss"
PYTHON="${KOHYA_DIR}/venv/bin/python3"
CKPT="$HOME/comfy/ComfyUI/models/checkpoints/Juggernaut-XL_v9_RunDiffusionPhoto_v2.safetensors"
DATA="/mnt/d/Proyectos/Yggdrasil/Muspelheim/AI-Influencer/assets/lora_dataset/eir_db"
OUT="/mnt/d/Proyectos/Yggdrasil/Muspelheim/AI-Influencer/assets/lora_output"

# Pre-flight checks
echo "=== Eir LoRA v2 Training ==="
echo ""

check() {
    local label="$1" target="$2"
    if [ -e "$target" ]; then
        echo "  ✓ $label"
    else
        echo "  ✗ $label NOT FOUND: $target"
        exit 1
    fi
}

check "Kohya script" "${KOHYA_DIR}/sdxl_train_network.py"
check "Python venv" "${KOHYA_DIR}/venv/bin/python3"
check "Checkpoint" "$CKPT"
check "Dataset dir" "$DATA"

# Count images
IMGS=$(find "$DATA" -name '*.png' -o -name '*.jpg' -o -name '*.jpeg' -o -name '*.webp' | wc -l)
echo "  Dataset: $IMGS images"

if [ "$IMGS" -lt 5 ]; then
    echo "  ✗ Not enough images (need at least 5)"
    exit 1
fi

mkdir -p "$OUT"

echo ""
echo "Starting training (1800 steps, saving every 100)..."
echo ""

cd "$KOHYA_DIR"

"$PYTHON" sdxl_train_network.py \
    --pretrained_model_name_or_path "$CKPT" \
    --train_data_dir "$DATA" \
    --output_dir "$OUT" \
    --output_name eir_niflheimr_v2_lora \
    --save_model_as safetensors \
    --save_precision bf16 \
    --network_module networks.lora \
    --network_dim 32 \
    --network_alpha 16 \
    --network_dropout 0.1 \
    --resolution "1024,1024" \
    --enable_bucket \
    --bucket_reso_steps 64 \
    --min_bucket_reso 512 \
    --max_bucket_reso 2048 \
    --train_batch_size 1 \
    --max_train_steps 1800 \
    --save_every_n_steps 100 \
    --optimizer_type AdamW \
    --optimizer_args weight_decay=0.01 \
    --learning_rate 2e-4 \
    --text_encoder_lr 1e-4 \
    --unet_lr 2e-4 \
    --lr_scheduler cosine \
    --lr_warmup_steps 100 \
    --lr_scheduler_min_lr_ratio 0.1 \
    --min_snr_gamma 5 \
    --gradient_checkpointing \
    --mixed_precision bf16 \
    --full_bf16 \
    --xformers \
    --sdpa \
    --cache_latents \
    --keep_tokens 1 \
    --shuffle_caption \
    --caption_tag_dropout_rate 0.05 \
    --seed 42 \
    --max_data_loader_n_workers 2 \
    --log_prefix eir_v2

echo ""
echo "=== Training Complete ==="
echo "Output files:"
ls -la "$OUT"/eir_niflheimr_v2_lora*.safetensors 2>/dev/null || echo "  No output files found!"
