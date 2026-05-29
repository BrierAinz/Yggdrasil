# ComfyUI Model Directory Map

Where to place different model file types in a ComfyUI installation.
Root: `~/comfy/ComfyUI/models/` (or the configured `--models-dir`).

## Standard Directories

| Directory | File Types | Examples |
|-----------|-----------|---------|
| `checkpoints/` | Full model checkpoints (.safetensors, .ckpt, .pth) | `sd_xl_base_1.0.safetensors`, Juggernaut XL |
| `diffusion_models/` | Diffusion model weights (DiT, UNet) — separate from full checkpoint | `anima-preview3-base.safetensors`, FLUX DiT |
| `text_encoders/` | Text encoder models (CLIP, T5, Qwen) | `qwen_3_06b_base.safetensors`, `clip_g.safetensors` |
| `vae/` | VAE models | `qwen_image_vae.safetensors`, `sdxl_vae.safetensors` |
| `vae_approx/` | Approximate VAEs for preview | `taesd_decoder.pth` |
| `loras/` | LoRA adapters | `detail_enhancer.safetensors` |
| `embeddings/` | Textual inversion embeddings | `easy_negative.safetensors` |
| `controlnet/` | ControlNet models | `control_v11p_sd15_canny.pth` |
| `clip/` | CLIP vision models | `clip_vision_vit_h.safetensors` |
| `clip_vision/` | CLIP vision models (alt location) | same as `clip/` |
| `unet/` | UNet models (some workflows reference this) | GGUF-quantized UNets |
| `upscale_models/` | Upscaling models (ESRGAN, RealESRGAN) | `RealESRGAN_x4plus.pth` |
| `latent_upscale_models/` | Latent upscale models | `4x-UltraSharp.pth` |
| `animatediff_models/` | AnimateDiff motion modules | `mm_sdxl_v10_beta.ckpt` |
| `animatediff_motion_lora/` | AnimateDiff motion LoRAs | `v3_sd15_mm.ckpt` |
| `style_models/` | Style models | IP-Adapter style models |
| `gligen/` | GLIGEN models | `gligen_sd_text_box_pruned.safetensors` |
| `hypernetworks/` | Hypernetwork models | Various |
| `insightface/` | InsightFace models (face detection + swap) | `inswapper_128.onnx` (529MB face swap) |
| `insightface/models/buffalo_l/` | InsightFace detection model | `2d106det.onnx`, `det_10g.onnx`, etc. |
| `facerestore_models/` | Face restoration models | `codeformer-v0.1.0.pth`, `GFPGANv1.4.pth` |
| `photomaker/` | PhotoMaker models | `photomaker_v1.bin` |
| `audio_encoders/` | Audio encoder models | CLAP, T5 audio |
| `configs/` | Config files for models | Model-specific YAML configs |

## Other Important Paths

| Path | Contents |
|------|----------|
| `user/default/workflows/` | Saved workflow JSON files (appear in browser UI) |
| `custom_nodes/` | Git-cloned custom node packages |
| `output/` | Generated images/videos (default output dir) |
| `input/` | Uploaded input images |

## Key Rules

1. **File names must be exact** — Workflows reference models by exact filename including extension. `sdxl_vae.safetensors` ≠ `SDXL_VAE.safetensors`.
2. **Diffusion models vs checkpoints** — Newer model architectures (FLUX, DiT-based) often separate the diffusion model into `diffusion_models/` and the text encoder into `text_encoders/`, unlike legacy SD/SDXL which bundled everything into one checkpoint in `checkpoints/`.
3. **Multiple locations for same type** — Some nodes look in `clip/`, others in `clip_vision/`. Keep both in sync or symlink.
4. **WSL paths** — When copying from Windows (`/mnt/c/Users/...`) always use absolute paths. `~` resolves to the shell user's home, which may differ from the ComfyUI owner.
5. **inswapper_128.onnx placement** — The ReActor face swap model must go in `models/insightface/inswapper_128.onnx` (NOT `models/reactor/`). Download: `wget -O models/insightface/inswapper_128.onnx "https://huggingface.co/ezioruan/inswapper_128.onnx/resolve/main/inswapper_128.onnx"`. ReActor node references it as `swap_model: "inswapper_128.onnx"`.