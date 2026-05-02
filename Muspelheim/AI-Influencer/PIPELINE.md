# Content Generation Pipeline

## Arquitectura del Pipeline

```
┌─────────────┐    ┌──────────────┐    ┌───────────────┐    ┌─────────────┐
│  Prompt      │───▶│  SD/Flux      │───▶│  Post-process  │───▶│  Schedule    │
│  Template    │    │  Generation   │    │  ( Upscale,   │    │  & Post      │
│  + LoRA Eir  │    │  (batch mode) │    │   Watermark,  │    │  (IG/TikTok) │
│              │    │              │    │   Validate )  │    │              │
└─────────────┘    └──────────────┘    └───────────────┘    └─────────────┘
```

## 1. Setup de Entorno

### Opción A: Local (tu RTX 3060)
```bash
# Instalar Stable Diffusion WebUI (AUTOMATIC1111)
cd /mnt/d/Proyectos/
git clone https://github.com/AUTOMATIC1111/stable-diffusion-webui.git
cd stable-diffusion-webui
./webui.sh --medvram --xformers

# Flux con CPU offload (48GB RAM suficiente)
# Descargar flux1-dev.safetensors → models/Stable-diffusion/
```

### Opción B: Cloud (RunPod) — RECOMENDADO para LoRA training
```bash
# RunPod con A100 ($0.20/hr)
# Template: RunPod PyTorch 2.1
# Instalar Kohya_ss para LoRA training
```

### Modelos Base Recomendados

| Modelo | Uso | VRAM Necesario |
|--------|-----|----------------|
| **Juggernaut XL v9** | Retrato fotorrealista | 6-8GB (medvram OK) |
| **RealVisXL v4** | Variante más suave | 6-8GB |
| **Flux.1 Dev** | Máxima calidad, todos los estilos | 12GB+ (CPU offload) |
| **DreamShaper XL** | Artístico, menos realista | 6-8GB |

### LoRA de Eir
- **Dataset**: 20-30 imágenes generadas con Flux/SDXL del personaje
- **Clipping**: Entrenar solo las capas de identidad facial
- **Dim**: 32 (good balance calidad/tamaño)
- **Steps**: 1500-2000
- **Platform**: Kohya_ss en RunPod A100 (~30 min training)

## 2. Generación Batch

### Script: generate.py
```python
"""Batch generation pipeline for Eir content."""
import subprocess
import json
from pathlib import Path
from datetime import datetime

# Prompt templates por tipo de contenido
TEMPLATES = {
    "portrait_casual": {
        "positive": "masterpiece, best quality, photorealistic, 1girl, eir_niflheimr, "
                    "pale skin, violet eyes, long black hair with purple highlights, "
                    "oval face, subtle freckles, wearing dark minimalist outfit, "
                    "silver runic necklace, casual pose, relaxed expression, "
                    "natural lighting, urban background, shot on Sony A7IV",
        "negative": "cartoon, anime, 3d, deformed, extra fingers, blurry, watermark",
        "steps": 30,
        "cfg": 7,
        "sampler": "DPM++ 2M Karras",
        "size": "832x1216",  # Portrait 2:3
    },
    "portrait_artistic": {
        "positive": "masterpiece, best quality, 1girl, eir_niflheimr, "
                    "painting style, dark fantasy, moody atmosphere, "
                    "volumetric lighting, dramatic shadows, "
                    "runic symbols floating, ethereal glow",
        "negative": "photorealistic, photo, simple, plain",
        "steps": 35,
        "cfg": 8,
        "sampler": "Euler a",
        "size": "1024x1024",
    },
    "landscape_dark_fantasy": {
        "positive": "masterpiece, best quality, dark fantasy landscape, "
                    "norwegian fjord, fog, ancient ruins, runestones, "
                    "moonlight, aurora borealis, cinematic wide shot",
        "negative": "person, character, text, watermark, cartoon",
        "steps": 30,
        "cfg": 7,
        "sampler": "DPM++ 2M Karras",
        "size": "1344x768",  # Landscape 16:9
    },
    "detail_jewelry": {
        "positive": "masterpiece, macro photography, silver runic jewelry, "
                    "intricate celtic knotwork, moonstone gem, "
                    "dark velvet background, ring light, shallow DOF",
        "negative": "person, face, hands, blurry, low detail",
        "steps": 30,
        "cfg": 7,
        "sampler": "DPM++ 2M Karras",
        "size": "1024x1024",
    },
}

def generate_batch(template_name: str, count: int = 5, outdir: str = "content/posts"):
    """Generate a batch of images from a template."""
    template = TEMPLATES[template_name]
    timestamp = datetime.now().strftime("%Y%m%d_%H%M")
    output_dir = Path(outdir) / f"{template_name}_{timestamp}"
    output_dir.mkdir(parents=True, exist_ok=True)

    # Call Lilith in batch mode for caption generation
    caption_prompt = (
        f"Write an Instagram caption for Eir (dark fantasy AI artist) "
        f"for a {template_name.replace('_', ' ')} image. "
        f"Style: elegant, mysterious, with emojis 🗡️ 🌙 ✦. Max 150 chars. "
        f"In Spanish."
    )

    # Using SD WebUI API for generation
    for i in range(count):
        seed = random_seed()
        payload = {
            "prompt": template["positive"],
            "negative_prompt": template["negative"],
            "steps": template["steps"],
            "cfg_scale": template["cfg"],
            "sampler_name": template["sampler"],
            "width": int(template["size"].split("x")[0]),
            "height": int(template["size"].split("x")[1]),
            "seed": seed,
            "override_settings": {"sd_model_checkpoint": "juggernautXL_v9Rdphoto2Light.safetensors"},
        }
        # POST to SD WebUI API
        # response = requests.post("http://127.0.0.1:7860/sdapi/v1/txt2img", json=payload)
        print(f"  [{i+1}/{count}] Generated {template_name} seed={seed}")

    print(f"Batch complete: {output_dir}")


def random_seed():
    import random
    return random.randint(0, 2**32 - 1)
```

## 3. Post-Processing

### Watermark Sutil
```python
"""Add invisible and visible watermark to images."""
from PIL import Image, ImageDraw, ImageFont

def add_watermark(input_path, output_path, text="@eir.creates"):
    img = Image.open(input_path)
    draw = ImageDraw.Draw(img)
    # Small text in bottom-right, 60% opacity
    font = ImageFont.truetype("assets/fonts/serif.ttf", 16)
    bbox = img.getbbox()
    x = bbox[2] - 120
    y = bbox[3] - 25
    draw.text((x, y), text, fill=(255, 255, 255, 153), font=font)
    img.save(output_path, quality=95)
```

### Upscale Pipeline
```
1. Generate at 832x1216 or 1024x1024
2. ESRGAN upscale 2x → 1664x2432 or 2048x2048
3. Crop to IG optimal: 1080x1350 (portrait) or 1080x1080 (square)
4. Add watermark
5. Save as PNG (archive) + JPEG 95% (posting)
```

## 4. Caption Generation

Usar Lilith batch mode para generar captions:
```bash
python -m Lilith.batch \
    --batch-json \
    --batch-sys "Eres Eir, una artista digital de estética dark fantasy. Escribe captions de Instagram en español. Usa emojis 🗡️ 🌙 ✦ 🖤. Máximo 150 caracteres." \
    "Caption para un retrato oscuro en la niebla con joyería rúnica"
```

## 5. Posting Schedule

| Día | Plataforma | Tipo | Hora (CET) |
|-----|-----------|------|-------------|
| Lunes | IG Feed | Retrato/estética | 19:00 |
| Martes | TikTok | Reel/transición | 21:00 |
| Miércoles | IG Feed | Arte digital | 19:00 |
| Jueves | Twitter/X | Thread educativo | 12:00 |
| Viernes | IG Stories | Behind the lienzo | 20:00 |
| Sábado | TikTok | Tutorial corto | 18:00 |
| Domingo | IG Feed |paisaje dark fantasy | 17:00 |

### Hashtags por tipo
```
# Retratos: #darkfantasyart #aesthetica #darkaesthetic #runic #nordicstyle
# Arte: #conceptart #darkart #fantasyillustration #digitalart #aiartist
# Estética: #darkfashion #minimaliststyle #silverjewelry #gothstyle
# Tutoriales: #stableiffusion #aigenerated #aiartcommunity #controlnet
```

## 6. Cantidad de Contenido por Sesión

Una sesión de generación de 2-3 horas debería producir:
- **8-12 retratos** (variaciones de 2-3 escenarios)
- **4-6 paisajes/artístico**
- **3-4 close-ups/detalles**
- **2-3 composiciones para Reels**

Total: ~20-25 piezas por sesión, 2-3 sesiones/semana = 40-75 piezas/semana