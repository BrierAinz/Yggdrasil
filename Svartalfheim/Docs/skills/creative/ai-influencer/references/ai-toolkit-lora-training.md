# AI Toolkit (ostris/ai-toolkit): LoRA Training Reference

Alternative to Kohya sd-scripts for LoRA/LoKr training. 10.4k stars, actively
maintained. Offers CLI + web UI (Next.js on port 8675) + auto-captioning.

GitHub: https://github.com/ostris/ai-toolkit

## When to Use AI Toolkit vs Kohya

| Feature | AI Toolkit | Kohya sd-scripts |
|---------|-----------|-------------------|
| Auto-captioning | Built-in (Qwen3VL) | External (BLIP/WD14) |
| Web UI | Yes (Next.js + Prisma) | No (Kohya_ss GUI separate) |
| SDXL LoRA | Yes (sd_trainer extension) | Yes (sdxl_train_network.py) |
| FLUX LoRA | Yes (native support) | Partial (xf-makers) |
| Video LoRA | Yes (Wan 2.2, LTX) | No |
| LoKr support | Yes | Limited |
| Quantized training | Yes (4-bit via optimum-quanto) | No |
| Setup complexity | Moderate (own venv required) | High (many pitfalls) |
| Dataset prep | Automatic captioning | Manual |

**Choose AI Toolkit when:** You want auto-captioning, web UI, or need to train
FLUX/video LoRAs. Best for new projects where dataset prep is a bottleneck.

**Choose Kohya when:** You need maximum control over every hyperparameter, are
iterating on a known-good config, or need DreamBooth-style fine control.

## Environment Setup

AI Toolkit requires its own virtual environment due to dependency conflicts
with ComfyUI (diffusers from git, transformers 5.5.3 vs ComfyUI's 5.7.0).

```bash
cd /home/brierainz/comfy
git clone https://github.com/ostris/ai-toolkit.git
cd ai-toolkit

# Create isolated venv — use uv (python3.12-venv unavailable on WSL without sudo)
uv venv .venv --python 3.12

# Install PyTorch first (CUDA 12.8 for RTX 3060)
uv pip install --python .venv/bin/python torch==2.9.1 torchvision==0.24.1 torchaudio==2.9.1 \
  --index-url https://download.pytorch.org/whl/cu128

# Install base requirements (diffusers from git, transformers 5.5.3)
# Use requirements_base.txt — requirements.txt pins scipy==1.12.0 which
# may fail to build from source; requirements_base.txt allows compatible versions
uv pip install --python .venv/bin/python -r requirements_base.txt
uv pip install --python .venv/bin/python "scipy>=1.12"

# Verify
.venv/bin/python -c "
import torch; print(f'PyTorch {torch.__version__}, CUDA: {torch.cuda.is_available()}, GPU: {torch.cuda.get_device_name(0)}')
import transformers; print(f'Transformers: {transformers.__version__}')
import diffusers; print(f'Diffusers: {diffusers.__version__}')
"
```

**⚠️ Dependency conflicts with ComfyUI:**
- `transformers`: ai-toolkit requires `==5.5.3`, ComfyUI uses `>=5.7.0`
- `diffusers`: ai-toolkit requires git version (with custom patches), ComfyUI needs stable PyPI
- Solution: separate venvs. Never install ai-toolkit in ComfyUI's `.venv`

**⚠️ WSL venv creation:**
- `python3.12 -m venv` fails without `python3.12-venv` package (requires sudo on WSL)
- Use `uv venv --python 3.12 .venv` instead — uv handles venv creation correctly
- Never use `python3.13 -m venv` then install into it — pip scripts will point to
  python3.13 while the venv default is python3.12, causing silent dependency conflicts

## Training Configuration (SDXL / Pony V6 XL)

The sd_trainer extension handles SDXL-family models. Config is YAML-based.

### Example: `train_pony_lora.yaml`

```yaml
job: extension
config:
  name: "pony_character_v1"
  process:
    - type: sd_trainer
      training_folder: "output"
      device: cuda:0
      dtype: bf16
      
      # Model
      is_xl: true
      pretrained_model: "/home/brierainz/comfy/ComfyUI/models/checkpoints/ponyDiffusionV6XL_v6StartWithThisOne.safetensors"
      
      # Network
      network:
        type: lora
        linear: 32
        linear_alpha: 16
        dropout: 0.1
      
      # Dataset (auto-captioned)
      datasets:
        - folder_path: "/path/to/character_images"
          caption_extension: .txt
          is_reg: false
          num_repeats: 10
      
      # Auto-captioning (optional — generates .txt caption files)
      captioner:
        type: qwen3_vl  # Built-in Qwen3VL vision model
        batch_size: 4
        max_length: 150
        add_trigger_word: "character_name"
      
      # Optimizer
      optimizer: AdamW
      optimizer_args:
        weight_decay: 0.01
      learning_rate: 2e-4
      lr_scheduler: cosine
      lr_warmup_steps: 100
      
      # Training
      max_train_steps: 1800
      save_every_n_steps: 300
      train_batch_size: 1
      gradient_checkpointing: true
      
      # Quantization (for 12GB VRAM)
      quantize: false  # Set true for FLUX training on 12GB
      
      # Mixed precision
      mixed_precision: bf16
      save_precision: bf16
      
      # Noise / augmentation
      min_snr_gamma: 5
      keep_tokens: 1
      shuffle_caption: true
      caption_tag_dropout_rate: 0.05
      
      seed: 42
      cache_latents: true
      # NOTE: Do NOT set cache_text_encoder_output when using
      # shuffle_caption or caption_tag_dropout_rate
```

### Running Training

```bash
cd /home/brierainz/comfy/ai-toolkit
source .venv/bin/activate

# CLI training
python run.py train_pony_lora.yaml

# Or use the web UI
python run.py --ui
# Opens http://localhost:8675
```

**Before training:** Kill ComfyUI to free VRAM:
```bash
kill $(pgrep -f "ComfyUI/main.py")
```

## Quantized Training (FLUX on 12GB VRAM)

For FLUX.1-dev LoRA training on a 12GB card, enable quantization:

```yaml
quantize: true
low_vram: true
mixed_precision: bf16
gradient_checkpointing: true
train_batch_size: 1
```

This uses `optimum-quanto` to 4-bit quantize the base model, reducing VRAM
from ~24GB to ~10GB. Training will be ~30% slower but fits on RTX 3060 12GB.

## Auto-Captioning with Qwen3VL

The Qwen3VL captioner generates .txt files alongside each training image
automatically. No manual captioning needed.

```yaml
captioner:
  type: qwen3_vl
  batch_size: 4
  max_length: 150
  add_trigger_word: "your_character_trigger"
```

The model downloads Qwen3VL weights on first run (~4GB). Captions are
written to `image_name.txt` next to each `image_name.png`, compatible
with both ai-toolkit and Kohya dataset formats.

## Output

Trained LoRA files are saved as `.safetensors` in the `output/` directory.
Copy to ComfyUI:

```bash
cp output/pony_character_v1/*.safetensors /home/brierainz/comfy/ComfyUI/models/loras/
```

## RTX 3060 12GB Training Parameters

| Parameter | SDXL/Pony | FLUX (quantized) |
|-----------|-----------|------------------|
| network_dim | 32 | 32 |
| network_alpha | 16 | 16 |
| batch_size | 1 | 1 |
| gradient_checkpointing | true | true |
| mixed_precision | bf16 | bf16 |
| quantize | false | true |
| low_vram | false | true |
| max_train_steps | 1800 | 1200 |
| VRAM usage | ~8-9 GB | ~9-10 GB |
| Training speed | ~4.5 s/step | ~8 s/step |
| Estimated time | ~2.5 hrs | ~2.7 hrs |

## Pitfalls

1. **Separate venv required** — ai-toolkit's diffusers and transformers versions
   conflict with ComfyUI. Never install in ComfyUI's `.venv`.
2. **Diffusers from git** — `pip install diffusers` won't work. The
   `requirements_base.txt` pulls from git. If it fails, try:
   `pip install git+https://github.com/huggingface/diffusers.git`
3. **Use requirements_base.txt, not requirements.txt** — `requirements.txt`
   pins `scipy==1.12.0` which fails to build from source on many systems (needs
   gfortran). Use `requirements_base.txt` and then `pip install "scipy>=1.12"`.
4. **Kill ComfyUI before training** — Same as Kohya. ComfyUI uses ~7.8GB VRAM.
   Free it first: `kill $(pgrep -f "ComfyUI/main.py")`
5. **Qwen3VL first-run download** — The captioner downloads ~4GB on first run.
   Plan for this if working offline.
6. **is_xl: true for Pony** — Pony V6 XL is SDXL-based. Set `is_xl: true` or
   training will use SD 1.5 settings and produce garbage.
7. **CUDA 13.x on WSL** — Same `bitsandbytes` issue as Kohya. Use `AdamW`
   instead of `AdamW8bit` or `Prodigy` with 8-bit.
8. **WSL venv creation** — `python3.12 -m venv` fails without sudo. Use `uv venv
   --python 3.12 .venv`. Never mix python3.13 venv creation with python3.12
   default — pip scripts will point to the wrong interpreter.
9. **Model download: InsightFace** — The `buffalo_l` face detection model is NOT
   on HuggingFace (gated/404). Install via Python: `pip install insightface
   onnxruntime`, then `FaceAnalysis(name='buffalo_l', root='models/insightface')`
   which auto-downloads from GitHub releases. Place in ComfyUI's
   `models/insightface/models/buffalo_l/`.
10. **Model download: IPAdapter FaceID** — There are TWO SDXL FaceID models with different CLIP Vision requirements:
    - `ip-adapter-faceid_sdxl.bin` (normal) — works with CLIP Vision ViT-H (`clip_vision_vit_h.safetensors`). This is the recommended default.
    - `ip-adapter-faceid-plusv2_sdxl.bin` (PlusV2) — requires ViT-L, NOT ViT-H. Using PlusV2 with ViT-H causes a `shape mismatch` error on `proj_in.weight` (expects 1280-dim ViT-L, gets 1664-dim ViT-H). There is no runtime check — it crashes.
    - There is also `ip-adapter-faceid-plusv2_sdxl_lora.safetensors` — a LoRA adapter that goes with the PlusV2 model.
    
    Both download from `h94/IP-Adapter` HuggingFace repo. When building ComfyUI API workflows, use the manual node chain (IPAdapterModelLoader + CLIPVisionLoader + IPAdapterInsightFaceLoader + IPAdapterFaceID), NOT the unified loaders which have model-path resolution issues in API mode.
11. **Model download: CLIP Vision** — IPAdapter's image encoder
    (`sdxl_models/image_encoder/model.safetensors`, 3.5GB) downloads inside the
    `models/ipadapter/sdxl_models/` tree, but ComfyUI's CLIPVisionLoader scans
    `models/clip_vision/`. Create a symlink:
    `ln -sf /path/to/ComfyUI/models/ipadapter/sdxl_models/image_encoder/model.safetensors
    /path/to/ComfyUI/models/clip_vision/clip_vision_vit_h.safetensors`
12. **Model download: 4x-UltraSharp** — This upscaler model has gated/private
    repos on HuggingFace. Use `RealESRGAN_x4plus.pth` (comes with ComfyUI) as
    fallback, or search for alternative mirrors.