# Ehyra Z-Image LoRA Training Config

## Full Config (RTX 3060 12GB)

```yaml
---
job: extension
config:
  name: "ehyra_zimage_lora_v1"
  process:
    - type: 'sd_trainer'
      training_folder: "output"
      device: cuda:0
      trigger_word: "ehyra"
      network:
        type: "lora"
        linear: 16
        linear_alpha: 16
      save:
        dtype: float16
        save_every: 500
        max_step_saves_to_keep: 4
      datasets:
        - folder_path: "/home/brierainz/comfy/ai-toolkit/dataset/images/ehyra_dataset"
          caption_ext: "txt"
          caption_dropout_rate: 0.05
          shuffle_tokens: false
          cache_latents_to_disk: true
          resolution: [ 512, 768, 1024 ]
      train:
        batch_size: 1
        cache_text_embeddings: true
        steps: 3000
        gradient_accumulation: 1
        train_unet: true
        train_text_encoder: false
        gradient_checkpointing: true
        noise_scheduler: "flowmatch"
        optimizer: "adamw8bit"
        lr: 1e-4
        lr_scheduler: "constant"
        dtype: bf16
        ema_config:
          use_ema: true
          ema_decay: 0.99
      model:
        # CRITICAL: Use LOCAL path, NOT HuggingFace ID.
        # Using "Tongyi-MAI/Z-Image" causes ai-toolkit to re-download ~33GB.
        name_or_path: "/home/brierainz/comfy/ai-toolkit/models/Z-Image"
        arch: "zimage"
        quantize: true
        # No ARA for Z-Image exists. Use uint4 without pipe suffix.
        qtype: "uint4"
        quantize_te: true
        qtype_te: "qfloat8"
        low_vram: true
      sample:
        sampler: "flowmatch"
        sample_every: 500
        width: 1024
        height: 1024
        prompts:
          - "ehyra, anime girl with long silver hair and piercing blue eyes, wearing a dark blue cloak, standing in a mystical forest, dramatic lighting"
          - "ehyra, young woman with pale skin and pointed ears, silver armor, fantasy warrior pose, moonlit battlefield"
          - "ehyra, character portrait, fierce expression, dark hair blowing in wind, glowing runes on skin, magical aura"
        neg: ""
        seed: 42
        walk_seed: true
        guidance_scale: 3
        sample_steps: 25
meta:
  name: "[name]"
  version: '1.0'
```

## ARA (Accuracy Recovery Adapter) Status

NO ARA exists for Z-Image in `ostris/accuracy_recovery_adapters`. Available ARAs:
- flux1_dev_kontext_torchao_uint3
- hidream_i1_full_torchao_uint3
- qwen_image_2512_torchao_uint3/uint4
- qwen_image_edit_2509/2511_torchao_uint3
- qwen_image_torchao_uint3
- wan22_14b_i2v/t2i_torchao_uint3/uint4

**Do NOT use qwen_image ARA with Z-Image** — different transformer architecture.

If uint4 OOM on RTX 3060 12GB, try:
- Reduce resolution to [512]
- Remove EMA config
- Try uint3 without ARA (lower quality)

## Z-Image Architecture Details

From `model_index.json` and `transformer/config.json`:

| Component | Class | Details |
|-----------|-------|---------|
| Pipeline | ZImagePipeline | diffusers, v0.37.0.dev0 |
| Transformer | ZImageTransformer2DModel | dim=3840, 30 layers, 30 heads, n_kv_heads=30, in_channels=16, rope_theta=256.0 |
| Text Encoder | Qwen3ForCausalLM | Qwen3-2.6B variant, 36 layers, hidden_size=2560, 8 KV heads |
| Tokenizer | Qwen2Tokenizer | vocab_size=151936 |
| VAE | AutoencoderKL | Standard |
| Scheduler | FlowMatchEulerDiscreteScheduler | Flow matching |

Key differences from Qwen-Image:
- Z-Image has `cap_feat_dim: 2560` and `siglip_feat_dim: None`
- Uses `axes_dims: [32, 48, 48]` and `all_patch_size: [2]`
- `t_scale: 1000.0` for timestep scaling

## Training Startup Sequence (observed on RTX 3060 12GB)

1. Load ZImage model → load transformer (2 shards, ~20GB)
2. Quantize transformer: 30 blocks in ~40s (uint4)
3. Move quantized transformer to CPU (frees GPU VRAM)
4. Load text encoder (Qwen3, 398 shards)
5. Quantize text encoder (qfloat8)
6. Found N images, create buckets (8 buckets for 61 images)
7. Cache latents to disk (~15s for 61 images)
8. Cache text embeddings
9. EMA initialization
10. **Training loop begins** (step 1/3000)

Expected VRAM during training: ~7.5 GB with uint4 quant + qfloat8 TE + gradient checkpointing + cached embeddings.

## Observed Training Stats (RTX 3060 12GB, 61 images, 8 buckets)

| Metric | Value |
|--------|-------|
| VRAM usage (training) | 8,900-9,200 MiB / 12,288 MiB (~75%) |
| VRAM usage (cache phase) | 7,500 MiB (~61%) |
| GPU util | 77-100% (lower during sample generation) |
| GPU temp | 83-87°C, fan 85-94% |
| Power draw | 140-162W |
| Speed | 6-12s/step (varies by bucket resolution) |
| Total time (3000 steps) | ~8-9 hours |
| Loss range | 0.25-0.68 (oscillates with batch_size=1, normal) |
| Loss trend | No clear downward trend after ~500 steps (constant LR 1e-4) |
| Checkpoint size | 82 MB per safetensors file |
| Startup sequence total | ~3.5 min |
| Quantize transformer | ~40s (30 blocks, uint4) |
| Quantize text encoder | ~30s (398 shards, qfloat8) |
| Cache latents (61 imgs) | ~17s |
| Cache text embeddings | Instant (<1s) |
| Sample generation (3 prompts) | ~30-60s per checkpoint |
| Model download size | ~20GB (not 33GB — HuggingFace shows compressed sizes) |

### Bucket Distribution (61 images)

| Resolution | Count |
|------------|-------|
| 896x1088 | 20 |
| 768x1344 | 14 |
| 832x1152 | 12 |
| 704x1408 | 2 |
| 576x672 | 4 |
| 768x992 | 2 |
| 1472x704 | 4 |
| 704x1472 | 3 |

### Monitoring Commands

```bash
# Check process alive
ps aux | grep "python.*run.py" | grep -v grep

# GPU status
nvidia-smi

# Check for saved checkpoints
ls -la ~/comfy/ai-toolkit/output/ehyra_zimage_lora_v1/*.safetensors

# Check sample images
ls -la ~/comfy/ai-toolkit/output/ehyra_zimage_lora_v1/samples/

# Kill stale training processes
pkill -f "python.*run.py"
```