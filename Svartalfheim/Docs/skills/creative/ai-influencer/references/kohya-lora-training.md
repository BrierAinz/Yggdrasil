# Kohya sd-scripts: SDXL LoRA Training Reference

Proven configuration for training a character LoRA with Kohya's
`sdxl_train_network.py` on an RTX 3060 12GB (WSL2).

## Environment Setup

```bash
cd /path/to/AI-Influencer/tools
git clone https://github.com/kohya-ss/sd-scripts.git kohya_ss
cd kohya_ss

# Use uv for venv management (pip/venv breaks with python3.12-venv on WSL)
uv venv venv --python 3.12
uv pip install --python venv/bin/python torch torchvision \
  --index-url https://download.pytorch.org/whl/cu124
# ⚠ cu124 ONLY — cu126 fails on WSL (nvidia-nvshmem-cu12 download timeout)
# ⚠ If torch gets a newer CUDA version (e.g., cu130), torchvision MUST match:
#   torch 2.11.0+cu130 → torchvision 0.26.0+cu130 (NOT 0.21.0+cu124)
#   Mismatched CUDA versions cause RuntimeError on import.
#   Fix: uv pip install --python venv/bin/python torch torchvision \
#        --index-url https://download.pytorch.org/whl/cu130

uv pip install --python venv/bin/python -r requirements.txt
uv pip install --python venv/bin/python xformers  # optional, for --xformers flag

# Verify
venv/bin/python -c "import torch; print(torch.cuda.is_available(), torch.cuda.get_device_name(0))"
venv/bin/python -c "import xformers; print('xformers OK')"  # if installed
```

**If `pip` goes missing from the Kohya venv** (happens with some uv installs):
```bash
curl -sS https://bootstrap.pypa.io/get-pip.py -o /tmp/get-pip.py
./venv/bin/python3 /tmp/get-pip.py
```

## Dataset Structure (CRITICAL)

Kohya supports two dataset methods: **config-based** (dataset_config.toml) and
**DreamBooth CLI** (`--train_data_dir`). They have DIFFERENT directory naming
requirements.

### Method 1: Config-based (recommended for control)

Uses `--dataset_config` flag. Images go in a subdirectory whose name is the
concept/class name:

```
assets/lora_dataset/
├── dataset_config.toml          ← points train_data_dir here
└── eir_niflheimr/              ← concept subfolder (any name)
    ├── image_001.png
    ├── image_001.txt            ← caption file (same basename)
    ├── image_002.png
    ├── image_002.txt
    └── metadata.json            ← optional but recommended
```

In `dataset_config.toml`, set `num_repeats` in the subset config:

```toml
[[datasets.subsets]]
image_dir = "/path/to/lora_dataset/eir_niflheimr"
class_tokens = "eir_niflheimr"
num_repeats = 10
caption_extension = ".txt"
```

### Method 2: DreamBooth CLI (`--train_data_dir`)

Uses `--train_data_dir` flag. The subdirectory name MUST follow the
`NN_concept` naming format where NN is the repeat count:

```
assets/lora_dataset/
└── eir_db/                           ← --train_data_dir points here
    └── 20_eir_niflheimr/             ← NN_concept naming (REQUIRED)
        ├── image_001.png
        ├── image_001.txt
        └── ...
```

**⚠️ CRITICAL:** If you use `--train_data_dir`, Kohya's `extract_dreambooth_params`
parses the directory name as `number_concept`. A directory named `eir_niflheimr`
(without a leading number) produces the error:
"ignore directory without repeats / 繰り返し回数のないディレクトリを無視します"
and ALL images are silently skipped, resulting in zero training data.

**Correct naming:** `20_eir_niflheimr` (repeatCount_conceptName)
**Wrong naming:** `eir_niflheimr`, `eir_niflheimr_20`, `eir_niflheimr_XX`

### Caption format (.txt files)

Each .txt file should contain the prompt/caption for its corresponding image.
Start with the trigger word:

```
eir_niflheimr, pale skin, long silver-white hair with violet tips, icy blue eyes, dark fantasy, ...
```

### metadata.json format

```json
[
  {
    "file_name": "image_001.png",
    "caption": "eir_niflheimr, pale skin, long silver-white hair, icy blue eyes, ..."
  }
]
```

### Image preparation

- Resize all images to **1024x1024** for SDXL training (SDXL native resolution)
- Use PNG format for lossless quality
- 16-30 images per character (16 minimum, 25+ recommended for quality)
- Curate for diversity: headshots, full-body, different outfits, settings, angles

## dataset_config.toml

```toml
[general]
enable_bucket = true
mixed_priority = "max"

[[datasets]]
resolution = 1024
batch_size = 1
num_repeats = 10

  [[datasets.subsets]]
  image_dir = "/mnt/d/Proyectos/Yggdrasil/Muspelheim/AI-Influencer/assets/lora_dataset/eir_niflheimr"
  class_tokens = "eir_niflheimr"
  num_repeats = 10
  caption_extension = ".txt"
```

**Key fields:**
- `resolution = 1024` — SDXL native resolution (not 768 or 512)
- `batch_size = 1` — required for 12GB VRAM; use `gradient_checkpointing` instead
- `num_repeats = 10` — each image is seen 10 times per epoch (160 steps/epoch with 16 images)
- `class_tokens` — your trigger word, used alongside caption files

## Training Command (Config-based — Epochs)

```bash
cd /path/to/AI-Influencer/tools/kohya_ss

venv/bin/python sdxl_train_network.py \
  --pretrained_model_name_or_path "/home/brierainz/comfy/ComfyUI/models/checkpoints/sd_xl_base_1.0.safetensors" \
  --dataset_config "/mnt/d/Proyectos/Yggdrasil/Muspelheim/AI-Influencer/assets/lora_dataset/dataset_config.toml" \
  --output_dir "/mnt/d/Proyectos/Yggdrasil/Muspelheim/AI-Influencer/assets/lora_output" \
  --output_name eir_niflheimr_lora_r32 \
  --save_model_as safetensors \
  --prior_loss_weight 1.0 \
  --network_module networks.lora \
  --network_dim 32 \
  --network_alpha 16 \
  --network_train_unet_only \
  --learning_rate 1e-4 \
  --lr_scheduler cosine \
  --lr_warmup_steps 100 \
  --max_train_epochs 15 \
  --save_every_n_epochs 5 \
  --mixed_precision bf16 \
  --save_precision bf16 \
  --seed 42 \
  --gradient_checkpointing \
  --cache_latents \
  --cache_text_encoder_outputs \
  --sdpa \
  --enable_bucket \
  --min_bucket_reso 768 \
  --max_bucket_reso 1280 \
  --bucket_reso_steps 64
```

## Training Command (DreamBooth CLI — Steps-based, Optimized v2)

For finer control over step count and checkpoint frequency. Uses improved
hyperparameters from the Eir v2 training run (min_snr_gamma, network_dropout,
caption_tag_dropout_rate, keep_tokens, shuffle_caption).

```bash
cd /path/to/AI-Influencer/tools/kohya_ss

venv/bin/python sdxl_train_network.py \
  --pretrained_model_name_or_path "/home/brierainz/comfy/ComfyUI/models/checkpoints/sd_xl_base_1.0.safetensors" \
  --train_data_dir "/mnt/d/Proyectos/Yggdrasil/Muspelheim/AI-Influencer/assets/lora_dataset/eir_db" \
  --output_dir "/mnt/d/Proyectos/Yggdrasil/Muspelheim/AI-Influencer/assets/lora_output" \
  --output_name eir_niflheimr_v2_lora \
  --save_model_as safetensors \
  --prior_loss_weight 1.0 \
  --network_module networks.lora \
  --network_dim 32 \
  --network_alpha 16 \
  --network_train_unet_only \
  --optimizer_type AdamW \
  --optimizer_args weight_decay=0.01 \
  --learning_rate 2e-4 \
  --text_encoder_lr 1e-4 \
  --unet_lr 2e-4 \
  --lr_scheduler cosine \
  --lr_warmup_steps 100 \
  --max_train_steps 1800 \
  --save_every_n_steps 300 \
  --save_precision bf16 \
  --mixed_precision bf16 \
  --seed 42 \
  --gradient_checkpointing \
  --cache_latents \
  --sdpa \
  --min_snr_gamma 5 \
  --network_dropout 0.1 \
  --keep_tokens 1 \
  --shuffle_caption \
  --caption_tag_dropout_rate 0.05 \
  --enable_bucket \
  --min_bucket_reso 768 \
  --max_bucket_reso 1280 \
  --bucket_reso_steps 64 \
  --xformers
```

**Why this config differs from epoch-based:**
- `--max_train_steps 1800` with `--save_every_n_steps 300` gives 6 checkpoints
  (steps 300, 600, 900, 1200, 1500, 1800) for evaluation comparison
- `--train_data_dir` + `NN_concept/` directory naming enables DreamBooth method
  without a config file; repeat count is embedded in directory name
- Removed `--cache_text_encoder_outputs` because it conflicts with
  `--shuffle_caption` and `--caption_tag_dropout_rate` (these need fresh TEC
  outputs per step for effective dropout/shuffle)
- `--optimizer_args weight_decay=0.01` (NOT `--weight_decay 0.01`)
- `--xformers` is included but can be replaced with `--sdpa` if xformers is not installed

### Parameter Notes (Config-based / Epoch Method)

| Parameter | Value | Rationale |
|-----------|-------|-----------|
| `network_dim` | 32 | Good balance for character LoRA; 16 too little detail, 64+ OOMs on 12GB |
| `network_alpha` | 16 | Half of dim; standard practice for stable training |
| `network_train_unet_only` | (flag) | Required when using `--cache_text_encoder_outputs`; trains LoRA only on UNet |
| `learning_rate` | 1e-4 | Standard for LoRA dim 32; too high causes instability |
| `lr_scheduler` | cosine | Smooth decay; prevents late-training instability |
| `lr_warmup_steps` | 100 | ~6% of total steps; prevents early instability |
| `max_train_epochs` | 15 | With 16 imgs × 10 repeats = 160 steps/epoch × 15 = 2400 total steps |
| `mixed_precision` | bf16 | Use bf16 for SDXL (fp16 can cause NaN losses) |
| `cache_latents` | (flag) | Pre-compute latents to save VRAM during training |
| `cache_text_encoder_outputs` | (flag) | Pre-compute TEC outputs; incompatible with training text encoder |
| `sdpa` | (flag) | PyTorch 2.0+ native scaled dot-product attention (alternative to xformers) |
| `enable_bucket` | (flag) | Allow varied aspect ratios in training |
| `gradient_checkpointing` | (flag) | Trade compute for VRAM — essential on 12GB cards |

### Parameter Notes (Steps-based / DreamBooth / Optimized v2)

| Parameter | Value | Rationale |
|-----------|-------|-----------|
| `max_train_steps` | 1800 | ~11 epochs with 16 imgs × 20 repeats = 320 steps/epoch; good for character LoRA |
| `save_every_n_steps` | 300 | 6 checkpoints for evaluation: 300/600/900/1200/1500/1800 |
| `train_data_dir` | (path) | Parent dir containing `20_concept/` subdirectories |
| `optimizer_type` | AdamW | NOT AdamW8bit (bitsandbytes fails on CUDA 13.x WSL) |
| `optimizer_args` | weight_decay=0.01 | Passed as `--optimizer_args weight_decay=0.01` (NOT `--weight_decay`) |
| `min_snr_gamma` | 5 | Reduces loss for high-noise timesteps; improves detail quality |
| `network_dropout` | 0.1 | Regularization; prevents overfitting on small datasets |
| `keep_tokens` | 1 | Always keeps trigger word as first token during shuffle |
| `shuffle_caption` | (flag) | Shuffles caption tokens each step for augmentation |
| `caption_tag_dropout_rate` | 0.05 | Drops 5% of caption tags per step; improves generalization |
| `learning_rate` | 2e-4 | Higher LR for steps-based with warmup + cosine decay |
| `text_encoder_lr` | 1e-4 | Separate (lower) LR for text encoder when not cached |
| `unet_lr` | 2e-4 | Higher LR for UNet, the main target |

**⚠️ Key flag conflict:** `--cache_text_encoder_outputs` is incompatible with
ALL of `--shuffle_caption`, `--caption_tag_dropout_rate`, and `--keep_tokens`.
These augmentation flags modify the caption on every step, which requires
re-encoding the text encoder each time. If you cache TEC outputs, captions
are fixed and these augmentations are silently ignored. For optimized v2
training with caption augmentation, remove `--cache_text_encoder_outputs`
and accept ~20% slower training for better quality.

## Training Timeline (RTX 3060 12GB)

- **Steps per epoch:** 160 (16 images × 10 repeats)
- **Total steps:** 2,400 (160 × 15 epochs)
- **Speed:** ~4.5 seconds/step (after cache warmup)
- **Total time:** ~3 hours
- **VRAM usage:** ~8.7 GB during training
- **Saves:** Every 5 epochs (at epoch 5, 10, 15)

## Pre-Training Checklist

1. [ ] Kill ComfyUI if running: `kill $(pgrep -f "ComfyUI/main.py")`
2. [ ] Verify VRAM free: `nvidia-smi` should show <2GB used
3. [ ] Verify dataset structure: images in `class_name/` subdirectory
4. [ ] Verify caption files: each .png has matching .txt
5. [ ] Verify dataset_config.toml: paths are absolute, resolution=1024
6. [ ] Verify PyTorch CUDA: `venv/bin/python -c "import torch; print(torch.cuda.is_available())"`

## Post-Training

```bash
# Copy LoRA to ComfyUI models directory
cp /path/to/lora_output/eir_niflheimr_lora_r32.safetensors \
   ~/comfy/ComfyUI/models/loras/

# Restart ComfyUI
cd ~/comfy/ComfyUI && .venv/bin/python main.py --listen 0.0.0.0 --port 8188 &

# Test generation with LoRA
# Use ComfyUI workflow with LoRA Loader node → weight 0.7
```

## Debugging Failures (Chronological Record)

### Failure 1: "no valid subset found in dataset"
**Cause:** Images placed directly in `train_data_dir` without class subdirectory.
**Fix:** Move images to `train_data_dir/eir_niflheimr/` subdirectory.

### Failure 2: Same dataset structure error
**Cause:** Subset directory name didn't match `class_tokens` field, and metadata was malformed.
**Fix:** Ensure subdirectory name matches concept, captions use `.txt` extension matching `caption_extension`.

### Failure 3: "cannot train text encoder while caching text encoder outputs"
**Cause:** `--cache_text_encoder_outputs` flag is incompatible with training the text encoder.
**Fix:** Use `--network_train_unet_only` (trains LoRA only on UNet, caches TEC outputs). Do NOT use `--train_text_encoder=false` (not a valid Kohya flag).

### Failure 4: xformers import error
**Cause:** `--xformers` flag passed but xformers package not installed in venv.
**Fix:** Either install xformers (`uv pip install --python venv/bin/python xformers`) or use `--sdpa` instead (PyTorch 2.0+ native attention).