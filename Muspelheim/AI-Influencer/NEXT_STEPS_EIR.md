# Eir — Instrucciones para la Siguiente Instancia

> **Estado actual**: FASE 1 COMPLETADA. LoRA v2 entrenado, evaluado, y 24 imágenes + 6 assets de perfil generados.
> **Última actualización**: Mayo 3, 2026 — Sesión autónoma completada

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
- Nombre ComfyUI: `eir_niflheimr_v2_best.safetensors`
- **strength_model**: 0.8 | **strength_clip**: 0.8

### Problemas Resueltos en Esta Sesión
1. **torchview incompatibilidad** — torch 2.11.0+cu130 vs torchvision 0.21.0+cu124 → Instalado torchvision 0.26.0+cu130
2. **pip faltante en venv** → Restaurado con get-pip.py
3. **Estructura de dataset incorrecta** → Corregido a formato Kohya: `eir_db/20_eir_niflheimr/`
4. **Argumentos CLI inválidos** → Eliminados --tag_dropout, --weight_decay CLI, --min_lr_ratio, --persistent_workers; corregido weight_decay a `--optimizer_args weight_decay=0.01`

---

## Imágenes Generadas

### Feed Posts (18 imágenes) — `outputs/feed_batch_v2/`
| # | Nombre | Tipo | Dimensión | Descripción |
|---|--------|------|-----------|-------------|
| 01 | introducing_eir | Portrait | 832x1216 | Close-up con aurora boreal |
| 02 | ice_warrior | Full body | 832x1216 | Armadura con runas brillantes |
| 03 | forest_path | Landscape | 1216x832 | Caminando en bosque nevado |
| 04 | rune_mage | Portrait | 832x1216 | Biblioteca mágica con runas |
| 05 | winter_throne | Portrait | 832x1216 | Trono de hielo |
| 06 | casual_dark | Portrait | 832x1216 | outfit casual interior |
| 07 | aurora_night | Landscape | 1216x832 | Precipio con aurora |
| 08 | frost_flower | Close-up | 832x1216 | Manos con flor de escarcha |
| 09 | training_grounds | Landscape | 1216x832 | Patiendo con espada |
| 10 | crystal_cave | Portrait | 832x1216 | Cueva de cristales brillantes |
| 11 | blacksmith | Landscape | 1216x832 | Forjando espada rúnica |
| 12 | reflection | Landscape | 1216x832 | Reflejo en lago congelado |
| 13 | ice_dragon | Landscape | 1216x832 | Frente a cráneo de dragón |
| 14 | moonlit_walk | Landscape | 1216x832 | Pueblo nevado nocturno |
| 15 | candle_study | Portrait | 832x1216 | Estudio a la luz de vela |
| 16 | storm_summoner | Landscape | 1216x832 | Invocando tormenta de hielo |
| 17 | traveler_rest | Landscape | 1216x832 | Fogata en nieve |
| 18 | sunset_ridge | Landscape | 1216x832 | Atardecer en montaña |

### Profile Assets (6 imágenes) — `outputs/profile_assets/`
| Nombre | Dimensión | Uso |
|--------|-----------|-----|
| avatar_1x1 | 1024x1024 | Foto de perfil IG/TikTok |
| banner_wide | 1344x576 | Banner de X/Twitter |
| story_cover_1 | 1080x1920 | Historia dramática (cicatriz, lluvia) |
| story_cover_2 | 1080x1920 | Historia etérea (ojos cerrados, escarcha) |
| highlight_icon_1 | 512x512 | Ícono highlight: ojo de hielo |
| highlight_icon_2 | 512x512 | Ícono highlight: mechón violeta |

---

## ComfyUI — Configuración Actual

- **URL**: http://localhost:8188
- **Directorio**: `~/comfy/ComfyUI/`
- **venv**: `~/comfy/ComfyUI/.venv/`
- **Modelo base**: Juggernaut-XL_v9_RunDiffusionPhoto_v2.safetensors
- **LoRA principal**: `eir_niflheimr_v2_best.safetensors` (step 1400)
- **v1 LoRA** (fallback): `eir_niflheimr_lora_r32_epoch10.safetensors`
- **Workflow API**: `workflows/eir_lora_portrait_api.json`

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
- Post 1 (Lunes): Carousel 3 slides con `01_introducing_eir`, `05_winter_throne`, `07_aurora_night`
- Post 2 (Miércoles): `08_frost_flower` como close-up artístico
- Post 3 (Viernes): `03_forest_path` como landscape
- Stories diarias con `story_cover_1` y `story_cover_2`
- Ver calendario completo en `docs/CONTENT_CALENDAR.md`

### Contenido — Semana 2-3
- Post 4-9 usando imágenes 04-09
- Ver `docs/CONTENT_CALENDAR.md` para orden y captions
- Ver `docs/HASHTAG_STRATEGY.md` para hashtags optimizados

---

## Estructura del Proyecto

```
AI-Influencer/
├── assets/
│   ├── lora_dataset/
│   │   ├── eir_niflheimr/          # Dataset original (16 imágenes + captions)
│   │   └── eir_db/                 # Dataset en formato Kohya (20_eir_niflheimr/)
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
│   ├── eval_checkpoints/           # 17 imágenes de evaluación de checkpoints
│   ├── feed_batch_v2/              # 18 imágenes feed v2 (BEST)
│   └── profile_assets/             # 6 imágenes de perfil
├── scripts/
│   ├── train_eir_v2.sh             # Script de entrenamiento (CORREGIDO)
│   ├── generate_batch_v2.py        # Generador batch via ComfyUI API
│   ├── evaluate_checkpoints.py     # Evaluador de checkpoints
│   └── post_training_pipeline.py   # Pipeline post-entrenamiento
├── workflows/
│   └── eir_lora_portrait_api.json  # Workflow ComfyUI API
├── NEXT_STEPS_EIR.md               # Este archivo
└── PLAN_COMPLETO.md                 # Plan general FASE 0-2
