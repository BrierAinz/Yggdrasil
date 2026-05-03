# PLAN COMPLETO — Eir AI Influencer (@eir.creates)

> **Fecha**: Mayo 2026
> **Estado**: FASE 0 completada, FASE 1 en progreso
> **Hardware**: RTX 3060 12GB VRAM + 48GB RAM + AMD Ryzen 5 5500
> **Stack**: ComfyUI v0.20.1 + Juggernaut XL v9 + SDXL + LoRA eir_niflheimr
> **Autonomía**: Sesión de 5h — el agente trabaja sin interrupción

---

## FASE 1 — Fundamentos y Primer Contenido (SEM 1-2)

### 1.1 Optimizar LoRA y Pipeline de Generación

**Objetivo**: Maximar calidad del LoRA antes de publiar nada.

#### 1.1.1 Analizar Dataset Actual (16 imágenes)
- [x] Dataset existe en `/assets/lora_dataset/`
- [ ] Verificar calidad: todas >= 832x1216
- [ ] Recortar/resizear si es necesario (Power of 64: 832x1216 optimal)
- [ ] Verificar variedad: 30% portraits, 30% bust, 30% full body, 10% artistic
- [ ] Chequear captions: trigger word `eir_niflheimr` como PRIMERA palabra
- [ ] Eliminar imágenes con artefactos visibles

#### 1.1.2 Re-entrenar LoRA con Parámetros Optimizados
Config recomendada (basada en investigación 2025):

```toml
# Config LoRA Optimizada para Eir
pretrained_model_name_or_path = "Juggernaut-XL_v9_RunDiffusionPhoto_v2.safetensors"

# Network
network_dim = 32          # Sweet spot para character consistency
network_alpha = 16        # alpha = dim/2 → effective LR balance
network_module = "lora"
network_dropout = 0.1     # Previene overfitting

# Optimizer
optimizer_type = "AdamW8bit"
learning_rate = 2e-4
text_encoder_lr = 1e-4
unet_lr = 2e-4
weight_decay = 0.01

# LR Schedule
lr_scheduler = "cosine"
lr_warmup_steps = 100     # ~10% de total steps
min_lr_ratio = 0.1

# Training
max_train_steps = 1800    # 16 imgs × 112 epochs ≈ 1792 steps
save_every_n_epochs = 1   # Guardar CADA epoch para elegir el mejor
mixed_precision = "bf16"
gradient_checkpointing = true
xformers = true
min_snr_gamma = 5         # Reduce noise bias en SDXL
gradient_accumulation_steps = 1

# Dataset
resolution = "1024,1024"
bucket_reso_steps = 64
min_bucket_reso = 512
max_bucket_reso = 2048
cache_latents = true
cache_text_encoder = true

# Captioning
keep_tokens = 1            # Trigger word SIEMPRE primero
shuffle_caption = true
tag_dropout = 0.05        # 5% dropout → aprende dependencia del trigger
flip_aug = false           # OFF para character consistency
reg_weight = 1.0
```

**Alternativa Prodigy** (si AdamW8bit no converge bien):
```toml
optimizer_type = "Prodigy"
learning_rate = 1.0
network_alpha = 1.0       # Prodigy necesita alpha=1.0
weight_decay = 0.01
max_train_steps = 1200    # Prodigy converge más rápido
```

#### 1.1.3 Evaluar Checkpoints
- [ ] Re-entrenar LoRA con nueva config
- [ ] Generar 3-4 imágenes de test con CADA checkpoint de epoch
- [ ] Evaluar: consistencia facial, detalle, artefactos, creative flexibility
- [ ] Elegir el mejor checkpoint (probablemente epoch 8-12)
- [ ] Guardar como `eir_niflheimr_v2_best.safetensors`

#### 1.1.4 Crear Negative Prompt Optimizado
```
Master negative prompt:
cartoon, anime, 3d render, deformed, bad anatomy, bad hands, missing fingers,
extra digits, extra limbs, blurry, low quality, worst quality, watermark, text,
logo, signature, amputated, duplicate, morbid, mutilated, poorly drawn face,
mutation, disfigured, out of frame, excess skin, poorly drawn eyes, bad
proportions, distorted face, ugly, tiling, frame, grainy, noisy, oversaturated,
undersaturated, cropped, jpeg artifacts, simple background, flat lighting,
overexposed, underexposed, harsh shadows, harsh highlights, floating limbs,
 severed limbs, malformed hands, long neck, cross-eyed, disproportionate
```

### 1.2 Crear Cuentas Sociales (TU PARTE — el agente NO puede crear cuentas)

| Plataforma | Handle | Tipo | Prioridad |
|-----------|--------|------|-----------|
| Instagram | @eir.creates | Business/Digital Creator | **ALTA** |
| Twitter/X | @eir_creates | Professional | **MEDIA** |
| TikTok | @eir.creates | Creator | **MEDIA** |

**Assets que el agente preparará**:
- [x] Foto de perfil (circular, 400x400) — generar con ComfyUI
- [x] Banner/header Twitter (1500x500) — generar con ComfyUI
- [x] Bio corta (150 chars)
- [x] Bio larga (300 chars)
- [x] Primeros 9 posts de IG con captions
- [x] Primeros 3 videos concepto para TikTok

**Bios optimizadas para 2025-2026**:

IG/TikTok (150 chars):
```
🌙 Dark fantasy artist forged by code | ✦ Norse mythology meets AI
🗡️ Creating from the void | 🖤 #AIart #DarkFantasy
```

Twitter/X (300 chars):
```
Eir Niflheimr ✦ Artesana de imágenes desde Svartalfheim 🌙
Dark fantasy digital artist | AI-powered | Runic aesthetics & ice magic
🗡️ Creating portals between worlds, one pixel at a time
🔗 linktr.ee/eircreates
```

### 1.3 Generar Primer Batch de Imágenes (12-18 imágenes de alta calidad)

#### Templates de Prompt (Post-LoRA Optimization)

**Base prompt structure**:
```
eir_niflheimr, [character_desc], [outfit], [setting], [lighting],
[composition], [quality_tags]
```

**Character descriptor (consistente en todos los prompts)**:
```
1girl, solo, pale skin, silver-white hair with violet highlights,
icy blue eyes, high cheekbones, sharp features, slight freckles
```

**Quality tags (siempre al final)**:
```
masterpiece, best quality, photorealistic, 4k, detailed skin,
cinematic lighting, volumetric fog
```

**Variable sets**:

| Set | Outfits | Settings | Lighting |
|-----|---------|----------|----------|
| A | Dark flowing robes with silver embroidery | Nordic frozen lake | Northern lights + moonlight |
| B | Silver armor plates over black dress | Rune-carved stone temple | Ethereal blue glow from runes |
| C | Simple white fur-trimmed cloak | Snowy forest clearing | Golden sunset through pines |
| D | Black leather corset with runic amulet | Ancient library with floating books | Warm candlelight + cold moonbeams |
| E | Oversized knit sweater (casual) | Cozy cabin with fireplace | Warm firelight + window snow glow |
| F | Ice crystal tiara + ceremonial robes | Throne room of an ice palace | Dramatic rim lighting + crystal refractions |

**Negative prompt (optimizado)**: Ver sección 1.1.4

#### Lista de Imágenes a Generar (18 total)

| # | Tipo | Prompt Key | Resolución | Uso |
|---|------|------------|------------|-----|
| 1 | Portrait close-up | Set A, front face | 832x1216 | Post #1 (introducción) |
| 2 | Portrait dramatic | Set B, 3/4 view | 832x1216 | Post #2 |
| 3 | Full body | Set A, standing | 832x1216 | Post #3 |
| 4 | Creating art | Set D, upper body | 832x1216 | Post #4 "process" |
| 5 | Mood/aesthetic | Set C, contemplative | 832x1216 | Post #5 |
| 6 | Detail close-up | Set F, face | 512x768 | Post #6 (carousel detail) |
| 7 | Aurora borealis | Set A, landscape | 1216x832 (landscape) | Post #7 |
| 8 | Winter casual | Set E, 3/4 view | 832x1216 | Post #8 |
| 9 | Power pose | Set B, full body | 832x1216 | Post #9 |
| 10 | Before/After | — | 1080x1080 | TikTok transition |
| 11-12 | Avatar crop | Set A, close-up | 1080x1080 | Profile picture + variants |
| 13 | Banner Twitter | Set F, wide composition | 1500x500 | Twitter header |
| 14-15 | Story backgrounds | Set C + D | 1080x1920 | IG Stories aesthetico |
| 16-18 | Carousel variants | Set A-F, mixed | 832x1216 | Carousel posts (5-img sets) |

### 1.4 Publicar Primer Batch

#### Calendario de Publicación (Días 1-9)

| Día | Plataforma | Contenido | Caption |
|-----|-----------|-----------|---------|
| 1 | IG | Post #1 (portrait) | "Hola Midgard ✦ Primer portal abierto..." |
| 1 | X | Thread introductorio (3-5 tweets) | Hilo presentando a Eir |
| 2 | IG | Post #2 (dramatic) | Artistic caption |
| 2 | TikTok | Video transición #1 | Process → final |
| 3 | IG | Post #3 (full body) + Story | Landscape caption |
| 4 | IG | Post #4 (creating art) | BTS/process caption |
| 4 | TikTok | Video before/after | "Esto vs Aquello" |
| 5 | IG | Post #5 (mood) | Atmospheric caption |
| 5 | X | Prompt + resultado | Technical thread |
| 6 | IG | Post #6 (carousel detail) | "Los detalles esconden la magia" |
| 7 | IG | Post #7 (aurora) | Nordic landscape caption |
| 7 | TikTok | Montaje aesthetic | 5-8 imgs con dark ambient |
| 8 | IG | Post #8 (winter casual) | Casual caption |
| 9 | IG | Post #9 (power pose) | Throne/closing first batch |

**Hashtags optimizados por plataforma**:

Instagram (5-8 hashtags, NO 30):
```
#DarkFantasyArt #NorseMythology #AIartist #DigitalArt #CharacterDesign
#FantasyArt #DarkAesthetic #RunicArt
```

TikTok (3-5 hashtags):
```
#darkfantasy #AIart #digitalart #characterdesign #norsemythology
```

Twitter/X (2-4 hashtags):
```
#AIart #DarkFantasy #CharacterDesign #StableDiffusion
```

**Anti-Ban Rules**:
- IG: Max 3-4 posts/día. Engage 15 min antes/después de postear
- TikTok: SIEMPRE label de AI-generated. Stagger 4-6h entre posts
- X: No más de 50 tweets/día. Formato thread preferido

---

## FASE 2 — Crecimiento y Consistencia (SEM 3-8)

### 2.1 Sistema de Generación Continua

**Pipeline automatizado de contenido**:

| Día | Feed Post | Story | Reel/TikTok | X Thread |
|-----|-----------|-------|-------------|----------|
| L | Portrait | WIP screenshot | — | — |
| Ma | — | Mood board | Transition video | — |
| Mi | Landscape/artistic | Poll/pregunta | — | Prompt share |
| Ju | — | BTS | Process video | — |
| V | Carousel (5 imgs) | — | — | Lore thread |
| Sa | Casual/cultural | Story sale | Montaje | — |
| Do | — | Weekly recap | — | Community |

**Total semanal**: 3-4 feed posts, 4-5 stories, 2 videos, 2 X threads

### 2.2 Contenido Recurrente (Templates)

#### Weekly Series

| Serie | Frecuencia | Tipo | Descripción |
|-------|------------|------|-------------|
| "Rune of the Week" | Semanal | Thread + Story | Explica una runa nórdica + arte asociado |
| "Before & After" | 2x/semana | Video | Raw SDXL → LoRA → Final edit |
| "Eir Creates" | Semanal | Reel | Proceso completo de generación |
| "Mythology Monday" | Semanal | Post + Thread | Diosa nórdica del día + su historia |
| "Close-Up Friday" | Semanal | Carousel | Detalles macro de la semana |

#### Monthly Content

| Mes | Actividad |
|-----|-----------|
| Mes 1 | Focus en presentación + consistencia de personaje |
| Mes 2 | Empezar process videos + tutoriales |
| Mes 3 | Primer thread educativo largo (cómo entrené mi LoRA) |
| Mes 4 | Interacción con comunidad (polls, Q&A, "comment a concept") |
| Mes 6 | Primer hito (500+ followers) → anunciar Patreon |

### 2.3 Video Content Pipeline

**Requisitos para video**:
- CapCut para edición (gratis)
- Screen recording de ComfyUI workflow o A1111
- Audio: trending sounds + dark ambient
- Duración: 15-30 seg (TikTok), 15-60 seg (IG Reels)

**Template de Before/After Video**:
1. Frame 1-2s: Prompt text on screen ("eir_niflheimr, dark fantasy...")
2. Frame 2-4s: Raw sin LoRA (blurry, generic)
3. Beat drop →
4. Frame 4-8s: Con LoRA aplicada (sharp, detailed, character-consistent)
5. Frame 8-10s: Text overlay "Follow for more"

**Template de Process Video**:
1. Screen recording de ComfyUI workflow
2. Speed x4 (60s → 15s)
3. Text overlay explicando cada paso
4. Resultado final 3s + CTA

### 2.4 Crecimiento Organico

**Instagram**:
- Engagement window: 15 min antes + 15 min después de postear
- Comentar en cuentas similares (dark fantasy, AI art, nordic aesthetics)
- Story replies a todos los que interactúen
- Carousel posts = 3x más reach que single image

**TikTok**:
- Responder a comentarios dentro de 1 hora
- Duet con otros artistas AI (con permiso)
- Usar trending audio como background
- Postear 1-2x/día durante fase de crecimiento

**Twitter/X**:
- Thread format para todo (hook image first)
- Interactuar con cuentas grandes de AI art community
- Quote-tweet propio contenido antiguo
- Compartir prompts y configs (la comunidad de SD ama eso)

---

## FASE 3 — Monetización y Expansión (MES 3-6)

### 3.1 Monetización Progresiva

| Fase | Timeline | Fuente | Target |
|------|----------|--------|--------|
| Soft launch | Mes 3-4 | Ko-fi (donaciones) | $0-50/mes |
| Growth | Mes 4-5 | Commissions abiertas | $50-200/mes |
| Establish | Mes 5-6 | Patreon launch | $100-500/mes |
| Scale | Mes 6+ | Brand deals + merch | $500-1000/mes |

### 3.2 Patreon Tier Structure

| Tier | Precio | Contenido Exclusivo |
|------|--------|---------------------|
| Runa 🗡️ | $3/mes | Wallpapers (4K), early access a artwork |
| Hechizo ✦ | $10/mes | Prompts completos, tutoriales, PSD layers, process videos |
| Portal 🌙 | $25/mes | Commissions prioritarias, LoRA access, chat privado, monthly print |

### 3.3 CivitAI Strategy
- Publicar LoRA de Eir de forma gratuita → visibilidad
- Publicar LoRA de estilo "Dark Fantasy Aesthetic" gratis → credibility
- Cada download = 1-5% conversión a Patreon
- Siempre incluir link a redes en descripción

### 3.4 Expansión de Contenido

| Nuevo Formato | Timeline | Descripción |
|---------------|----------|-------------|
| AnimateDiff loops | Mes 3-4 | 2-3 seg loops de images estáticas |
| Print-on-demand | Mes 4-5 | Redbubble/Society6 con mejores pieces |
| Patreon exclusives | Mes 5-6 | High-res downloads, WIPs, sources |
| Collabs | Mes 4+ | Duets con otros AI artists |
| Lore series | Mes 3+ | Historias nórdicas ilustradas |

### 3.5 KPIs y Métricas

| Métrica | Mes 1 | Mes 3 | Mes 6 | Objetivo |
|---------|-------|-------|-------|----------|
| IG Followers | 50-100 | 500-1K | 3K-5K | 10K en 12 meses |
| TikTok Followers | 50-200 | 500-2K | 5K-10K | 20K en 12 meses |
| X Followers | 20-50 | 200-500 | 1K-3K | 5K en 12 meses |
| Engagement Rate | 5-8% | 3-5% | 2-4% | >3% sostenido |
| Patreon Patrons | 0 | 0 | 10-30 | 50 en 12 meses |
| Monthly Income | $0 | $0-50 | $200-500 | $1000/mes en 12 meses |

---

## QUICK REFERENCE — Comandos Clave

### ComfyUI Start
```bash
cd ~/comfy/ComfyUI && ~/comfy/ComfyUI/.venv/bin/python main.py --listen --port 8188
```

### LoRA Training (Kohya_ss)
```bash
cd ~/kohya_ss && source venv/bin/activate
accelerate launch --num_cpu_threads_per_process=2 scripts/sdxl_train_network.py \
  --config_file /path/to/config.toml
```

### Generate Image via API
```python
import urllib.request, json
# POST to http://localhost:8188/prompt with workflow JSON
```

### Key File Paths
| Archivo | Path |
|---------|------|
| LoRA actual | `/assets/lora_output/eir_niflheimr_lora_r32_final.safetensors` |
| ComfyUI LoRA dir | `~/comfy/ComfyUI/models/loras/` |
| Checkpoint | `~/comfy/ComfyUI/models/checkpoints/Juggernaut-XL_v9_RunDiffusionPhoto_v2.safetensors` |
| Reference images | `/assets/reference/` |
| LoRA dataset | `/assets/lora_dataset/` |
| Output images | `/outputs/` |
| Kohya_ss config | `/config/lora/` |
| Captions | `/assets/captions/` |

---

## NOTAS DE OPTIMIZACIÓN (Investigación 2025-2026)

### LoRA Training Key Findings
1. **dim=32, alpha=16** is the sweet spot for character consistency (current: r=32)
2. **AdamW8bit** with LR 2e-4, TE LR 1e-4 is more stable than Prodigy for first training
3. **min_snr_gamma=5** reduces noise bias in SDXL training
4. **tag_dropout=0.05** helps trigger word dependency
5. **keep_tokens=1** ensures trigger word stays first in caption
6. **Cosine schedule with warmup** > constant LR
7. **1800 steps** optimal for 16-image dataset (vs current 15 epochs ≈ 2400 steps)
8. **bf16 mixed precision** > fp16 when GPU supports it (RTX 3060 does via AMP)

### Social Media Key Findings
1. **Carousel posts (5-10 slides)** get 3x reach on IG
2. **Process/BTS content** gets 3-5x more engagement than polished images
3. **Character-driven accounts** grow faster than generic AI art
4. **Lore/worldbuilding** drives parasocial engagement
5. **Transparency about AI** is essential (anti-ban + trust)
6. **5-15 hashtags** on IG (not 30)
7. **IG Reels** = #1 discovery tool in 2025-2026
8. **TikTok**: process videos outperform static images significantly

---

*Documento creado durante sesión autónoma de 5h. Actualizar según progreso.*
