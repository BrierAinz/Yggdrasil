# Eir — Instrucciones para la Siguiente Instancia

> **Estado actual**: FASE 1 COMPLETADA + Sesión autónoma de mejora completada.
> **Última actualización**: Mayo 3, 2026

---

## LoRA v2 — Entrenado y Evaluado

### Resultados del Entrenamiento
- **Modelo base**: Juggernaut-XL v9 (SDXL)
- **Config**: dim=32, alpha=16, AdamW, min_snr_gamma=5, network_dropout=0.1, cosine schedule
- **Steps**: 1800 (save cada 100)
- **Loss final**: ~0.086 (descenso estable de 0.12 → 0.086)
- **19 checkpoints** guardados (step 100-1800 + final)

### Checkpoint Ganador: **step 1400**
- Face Anatomy: 9/10 | Character Consistency: 10/10 | Quality: 9/10 | Artifacts: 8/10
- **Promedio: 9.0** (empatado con step 600, pero 1400 tiene mejor generalización)
- Archivo: `~/comfy/ComfyUI/models/loras/eir_niflheimr_v2_best.safetensors`
- **strength_model**: 0.8 | **strength_clip**: 0.8

### Problemas Resueltos en Sesión Autónoma (Mayo 3)
1. **torchview incompatibilidad** — torch 2.11.0+cu130 vs torchvision 0.21.0+cu124 → Instalado torchvision 0.26.0+cu130
2. **pip faltante en venv** → Restaurado con get-pip.py
3. **Estructura de dataset incorrecta** → Corregido a formato Kohya: `eir_db/20_eir_niflheimr/`
4. **Argumentos CLI inválidos** → Eliminados --tag_dropout, --weight_decay CLI, --min_lr_ratio, --persistent_workers; corregido weight_decay a `--optimizer_args weight_decay=0.01`
5. **Batch upscale via ComfyUI API falla (400 Bad Request)** → Las imágenes no están en input dir de ComfyUI. Workaround: PIL Lanczos para batch, RealESRGAN para 6 quality upscales.

---

## Contenido Generado — Inventario Completo

### Feed Posts Originales (18 imágenes) — `outputs/feed_batch_v2/`

| # | Nombre | Dimensión | Descripción |
|---|--------|-----------|-------------|
| 01 | introducing_eir | 832x1216 | Close-up con aurora boreal |
| 02 | ice_warrior | 832x1216 | Armadura con runas brillantes |
| 03 | forest_path | 1216x832 | Caminando en bosque nevado |
| 04 | rune_mage | 832x1216 | Biblioteca mágica con runas |
| 05 | winter_throne | 832x1216 | Trono de hielo |
| 06 | casual_dark | 832x1216 | Outfit casual interior |
| 07 | aurora_night | 1216x832 | Precipicio con aurora |
| 08 | frost_flower | 832x1216 | Manos con flor de escarcha |
| 09 | training_grounds | 1216x832 | Luchando con espada |
| 10 | crystal_cave | 832x1216 | Cueva de cristales brillantes |
| 11 | blacksmith | 1216x832 | Forjando espada rúnica |
| 12 | reflection | 1216x832 | Reflejo en lago congelado |
| 13 | ice_dragon | 1216x832 | Frente a cráneo de dragón |
| 14 | moonlit_walk | 1216x832 | Pueblo nevado nocturno |
| 15 | candle_study | 832x1216 | Estudio a la luz de vela |
| 16 | storm_summoner | 1216x832 | Invocando tormenta de hielo |
| 17 | traveler_rest | 1216x832 | Fogata en nieve |
| 18 | sunset_ridge | 1216x832 | Atardecer en montaña |

### Profile Assets (6 imágenes) — `outputs/profile_assets/`

| Nombre | Dimensión | Uso |
|--------|-----------|-----|
| avatar_1x1 | 1024x1024 | Foto de perfil IG/TikTok |
| banner_wide | 1344x576 | Banner de X/Twitter |
| story_cover_1 | 1080x1920 | Historia dramática (cicatriz, lluvia) |
| story_cover_2 | 1080x1920 | Historia etérea (ojos cerrados, escarcha) |
| highlight_icon_1 | 512x512 | Ícono highlight: ojo de hielo |
| highlight_icon_2 | 512x512 | Ícono highlight: mechón violeta |

### Outfits G/H/I (3 imágenes) — `outputs/outfits_ghi/`

| Nombre | Dimensión | Descripción | Calidad |
|--------|-----------|-------------|---------|
| huntress | 832x1216 | Cazadora nórdica con arco | 9/10 |
| alchemist | 832x1216 | Alquimista con frascos lumínicos | 8/10 |
| shapeshifter | 832x1216 | Cambiaforma con aura etérea | 8/10 |

### Animaciones Originales (7 videos) — `outputs/videos_v2/`

| # | Video | Duración | Descripción |
|---|-------|----------|-------------|
| 01 | eir_aurora_borealis | 2s | Aurora boreal de fondo |
| 02 | eir_ice_crystal | 2s | Cristales de hielo |
| 03 | eir_frozen_waterfall | 2s | Cascada congelada |
| 04 | eir_rune_glow | 2s | Runas brillando |
| 05 | eir_snow_fall | 2s | Nieve cayendo |
| 06 | eir_candle_flame | 2s | Llama de vela |
| 07 | eir_mystical_forest | 2s | Bosque místico |

### Reel Clips Vertical (9 clips) — `outputs/reel_clips/`

| Clip | Seed | Tamaño | Descripción |
|------|------|--------|-------------|
| reel1_aurora.webp | 61926 | 512x768 | Aurora boreal (vertical) |
| reel1_temple.webp | 84500 | 512x768 | Templo nórdico (vertical) |
| reel1_snow.webp | 89306 | 512x768 | Nieve cayendo (vertical) |
| reel2_candle.webp | 79563 | 512x768 | Vela dramática (vertical) |
| reel2_armor.webp | 89665 | 512x768 | Armadura con brillo (vertical) |
| reel2_mirror.webp | 86974 | 512x768 | Espejo místico (vertical) |
| reel3_huntress.webp | 93963 | 512x768 | Cazadora nórdica (vertical) |
| reel3_cozy.webp | 82100 | 512x768 | Atardecer cálido (vertical) |
| reel3_lake.webp | 11336 | 512x768 | Lago helado (vertical) |

Todos: 24 frames @ 12fps, formato WEBP animado.

---

## Contenido Post-Procesado Final — Listo para Publicar

### Imágenes Upscaled (49) — `outputs/upscaled/`
- 6 originales con RealESRGAN x4 + center-crop a 1080x1350
- 43 adicionales con PIL Lanczos a resoluciones correctas
- Dimensiones: feed=1080x1350 (4:5), stories=1080x1920 (9:16), profiles=1080x1080 (1:1)

### Colecciones Finales — `outputs/final/`

| Carpeta | Cantidad | Dimensión | Descripción |
|---------|----------|-----------|-------------|
| feed_warm | 6 | 1080x1350 | Feed con color grading cálido |
| feed_moody | 6 | 1080x1350 | Feed con color grading oscuro |
| feed_cool | 6 | 1120x1390 | Feed con color grading frío (borde incluido) |
| content_bank_warm | 17 | 1080x1350 | Banco de contenido variado (warm grade) |
| outfits_warm | 3 | 1080x1350 | Outfits G/H/I con warm grade |
| profiles | 11 | 1080x1080 | Avatares y profile assets |
| stories_minimal | 3 | 1080x1920 | Stories estilo minimalista |
| stories_bold | 3 | 1080x1920 | Stories estilo bold |
| stories_frosted | 3 | 1080x1920 | Stories estilo frosted/escarcha |
| stories | 6 | 1080x1920 | Stories adicionales |

**Total: 64 imágenes listas para publicar.**

### Reels Compuestos (3) — `outputs/reels/`

| Nombre | Duración | Frames | Tamaño | Grade |
|--------|----------|--------|--------|-------|
| reel_northern_mystique.mp4 | 7.3s | 88 | 3.3 MB | warm |
| reel_dark_elegance.mp4 | 7.3s | 88 | 2.7 MB | moody |
| reel_wild_spirit.mp4 | 7.3s | 88 | 3.2 MB | cool |

Cada Reel: 3 clips con crossfade de 8 frames, watermark @eir.creates en último 30%, 1088x1920 (ajustado por ffmpeg macro_block_size=16).

---

## ComfyUI — Configuración Actual

- **URL**: http://localhost:8188
- **Directorio**: ~/comfy/ComfyUI/
- **venv**: ~/comfy/ComfyUI/.venv/
- **Python**: `/home/brierainz/comfy/ComfyUI/.venv/bin/python` (3.13)
- **Modelo base**: Juggernaut-XL_v9_RunDiffusionPhoto_v2.safetensors
- **LoRA principal**: `eir_niflheimr_v2_best.safetensors` (step 1400, strength 0.8)
- **LoRA v1** (fallback): `eir_niflheimr_lora_r32_epoch10.safetensors`
- **AnimateDiff**: `mm_sdxl_v10_beta.ckpt` (907 MB)
- **Upscale**: RealESRGAN_x4plus.pth (64 MB)
- **Workflows API**:
  - `workflows/eir_lora_portrait_api.json` — Retratos/paisajes con LoRA
  - `workflows/eir_upscale_api.json` — Upscale con RealESRGAN
  - `workflows/eir_reel_vertical_api.json` — Clips verticales AnimateDiff (512x768, 24f, 12fps)

**NOTA**: En WSL, `~` es `/home/aizen`, NO `/home/brierainz`. Usar paths absolutos siempre para ComfyUI.

---

## Scripts Disponibles

| Script | Descripción | Tamaño |
|--------|-------------|--------|
| `scripts/generate_batch_v2.py` | Generador batch de imágenes via ComfyUI API | — |
| `scripts/evaluate_checkpoints.py` | Evaluador de checkpoints LoRA | — |
| `scripts/post_training_pipeline.py` | Pipeline post-entrenamiento | — |
| `scripts/upscale_images.py` | Batch upscale via ComfyUI API + RealESRGAN | 6.7 KB |
| `scripts/batch_upscale_simple.py` | Batch upscale con PIL Lanczos (fallback) | 3 KB |
| `scripts/postprocess_upscale.py` | Center-crop 4:5 y resize a 1080x1350 | — |
| `scripts/postprocess.py` | Post-procesamiento completo: 4 color grades, watermark, borders, story overlays (3 estilos) | 11.2 KB |
| `scripts/generate_reel_clips.py` | Genera 9 clips verticales via ComfyUI AnimateDiff | 5 KB |
| `scripts/compose_reels_final.py` | Compone 3 Reels desde clips con crossfade, grade y watermark | 5.6 KB |
| `scripts/compose_reel.py` | Reel composer alternativo (10.3 KB, versión anterior) | 10.3 KB |
| `scripts/extract_frames.py` | Extrae frames de videos para verificación | — |

---

## Siguientes Pasos (FASE 2)

### Inmediato (requiere acción manual)
1. **Abrir cuenta de Instagram** como @eir.creates
   - Avatar: `outputs/profile_assets/v2_profile_avatar_1x1_00001_.png` (recortar a 320x320)
   - Bio: Ver `docs/VOICE_AND_PERSONALITY.md`
2. **Abrir cuenta de X/Twitter** como @eir_creates
   - Banner: `outputs/profile_assets/v2_profile_banner_wide_00001_.png`
3. **Abrir cuenta de TikTok** como @eir.creates

### Contenido — Semana 1 (Lanzamiento)
- **Reel 1**: `reel_northern_mystique.mp4` — "Northern Mystique" (aurora + templo + nieve)
- **Reel 2**: `reel_dark_elegance.mp4` — "Dark Elegance" (vela + armadura + espejo)
- **Reel 3**: `reel_wild_spirit.mp4` — "Wild Spirit" (cazadora + atardecer + lago)
- Post 1 (Lunes): Carousel 3 slides con feed_warm imágenes
- Post 2 (Miércoles): Close-up artístico de `frost_flower`
- Post 3 (Viernes): Landscape de `forest_path`
- Stories diarias con los 9 templates (minimal/bold/frosted)
- Ver calendario completo en `docs/CONTENT_CALENDAR.md`

### Contenido — Semana 2-3
- Post 4-9 usando images de content_bank_warm
- Alternar feed_moody y feed_cool para variedad
- Ver `docs/CONTENT_CALENDAR.md` para orden y captions
- Ver `docs/HASHTAG_STRATEGY.md` para hashtags optimizados

### Mejoras Futuras
- **FaceID v3**: Para mejorar consistencia facial de 6-7/10 a 9/10 en videos
- **Reels más largos**: 9-15s con más clipspor reel (actualmente 7.3s)
- **xurl CLI**: Instalar para publicación automatizada en X/Twitter
- **instagrapi**: Requiere setup interactivo para publicación en Instagram
- **Batch upscale via ComfyUI**: Arreglar path issue (imágenes deben estar en ComfyUI input dir)

---

## Estructura del Proyecto

```
AI-Influencer/
├── assets/
│   ├── lora_dataset/
│   │   ├── eir_niflheimr/          # Dataset original (16 imágenes + captions)
│   │   └── eir_db/                 # Dataset Kohya (20_eir_niflheimr/)
│   ├── lora_output/                # 19 checkpoints v2 + v1
│   └── reference_images/           # 28 imágenes de referencia
├── config/
│   ├── lora/
│   │   └── eir_v2_optimized.toml   # Config de entrenamiento v2
│   └── prompts/
│       ├── eir_prompts_v2.json      # 9 posts con prompts y captions
│       ├── eir_content_plan.json    # Plan expandido (9 posts + stories + profile)
│       └── generation_config.json   # Negative prompts y configuración
├── docs/
│   ├── CONTENT_CALENDAR.md         # Calendario 3 semanas
│   ├── HASHTAG_STRATEGY.md         # Estrategia de hashtags
│   ├── VOICE_AND_PERSONALITY.md    # Guía de voz y personalidad
│   ├── FASE2_GROWTH.md             # Plan de crecimiento
│   └── TRAINING_LOG_V2.md          # Log de entrenamiento
├── outputs/
│   ├── test_batch_lora/            # 6 imágenes test v1
│   ├── eval_checkpoints/           # 17 imágenes de evaluación
│   ├── feed_batch_v2/              # 18 imágenes feed v2 originales
│   ├── profile_assets/             # 6 imágenes de perfil
│   ├── outfits_ghi/               # 3 PNG outfits (huntress, alchemist, shapeshifter)
│   ├── videos_v2/                  # 7 videos originales (2s c/u)
│   ├── video_frames_check/         # Frames extraídos para verificación
│   ├── reel_clips/                 # 9 clips verticales WEBP (512x768, 24f, 12fps)
│   ├── reels/                      # 3 Reels MP4 compuestos (1088x1920)
│   ├── upscaled/                   # 49 imágenes upscaled (JPG)
│   └── final/                      # 64 imágenes post-procesadas listas
│       ├── feed_warm/              # 6 imágenes (warm grade + watermark)
│       ├── feed_moody/             # 6 imágenes (moody grade + watermark)
│       ├── feed_cool/              # 6 imágenes (cool grade + watermark + border)
│       ├── content_bank_warm/      # 17 imágenes variadas (warm)
│       ├── outfits_warm/           # 3 outfits G/H/I (warm)
│       ├── profiles/               # 11 avatares y profile assets
│       ├── stories_minimal/        # 3 stories estilo minimalista
│       ├── stories_bold/           # 3 stories estilo bold
│       ├── stories_frosted/        # 3 stories estilo escarcha
│       └── stories/                # 6 stories adicionales
├── scripts/
│   ├── train_eir_v2.sh             # Script de entrenamiento (CORREGIDO)
│   ├── generate_batch_v2.py        # Generador batch via ComfyUI API
│   ├── evaluate_checkpoints.py     # Evaluador de checkpoints
│   ├── post_training_pipeline.py   # Pipeline post-entrenamiento
│   ├── upscale_images.py            # Upscale ComfyUI + RealESRGAN
│   ├── batch_upscale_simple.py     # Upscale PIL Lanczos (fallback)
│   ├── postprocess_upscale.py      # Center-crop 4:5
│   ├── postprocess.py              # Post-procesamiento completo
│   ├── generate_reel_clips.py      # Generador de 9 clips verticales
│   ├── compose_reels_final.py      # Compositor de 3 Reels (crossfade+grade+wm)
│   ├── compose_reel.py            # Compositor alternativo (versión anterior)
│   └── extract_frames.py          # Extractor de frames para verificación
├── workflows/
│   ├── eir_lora_portrait_api.json  # Workflow retratos/paisajes
│   ├── eir_upscale_api.json        # Workflow upscale RealESRGAN
│   └── eir_reel_vertical_api.json  # Workflow AnimateDiff vertical
├── NEXT_STEPS_EIR.md              # Este archivo
└── PLAN_COMPLETO.md               # Plan general FASE 0-2
```

---

## Métricas de Calidad

| Aspecto | Score | Nota |
|---------|-------|------|
| Face anatomy (LoRA) | 9/10 | Mejor en step 1400 |
| Character consistency | 10/10 | Trigger word: `eir_niflheimr` |
| Image quality | 9/10 | Juggernaut XL v9 + SDXL |
| Video face consistency | 6-7/10 | Típico AnimateDiff SDXL, aceptable |
| Post-processing | 8/10 | 4 grades, watermark, story overlays |
| Reel quality | 7/10 | Crossfade suave, resolutions correctas |

**Total de assets listos para publicar**: 64 imágenes + 3 Reels + 7 videos cortos = **74 assets**