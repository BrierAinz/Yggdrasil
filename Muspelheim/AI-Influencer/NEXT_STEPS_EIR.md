# Eir — Instrucciones para la Siguiente Instancia

> **Estado actual**: FASE 0 COMPLETADA. FASE 1 en progreso. LoRA v2 listo para entrenar.
> **Última actualización**: Mayo 2026 (sesión autónoma de 5h)

---

## PROGRESO REALIZADO (sesión autónoma)

- [x] PLAN_COMPLETO.md creado — Plan detallado de 3 fases (~16KB)
- [x] LoRA v2 config optimizada — `config/lora/eir_v2_optimized.toml`
- [x] Script de entrenamiento listo — `scripts/train_eir_v2.sh` (pre-flight checks + dry-run)
- [x] Script de evaluación de checkpoints — `scripts/evaluate_lora_checkpoints.py`
- [x] Prompts v2 creados — `config/prompts/eir_prompts_v2.json` (9 posts IG + templates)
- [x] Captions del dataset mejorados — los 16 archivos .txt + metadata.json actualizados
- [x] 6 imágenes de test generadas — `outputs/test_batch_lora/` (LoRA epoch 10)
- [x] Investigación de técnicas 2025-2026 completada
- [x] ComfyUI verificado funcional en localhost:8188
- [x] LoRA epoch 10 copiado a ComfyUI models/loras/

## FASE 0 — COMPLETADA

- [x] ComfyUI v0.20.1 instalado en ~/comfy/ComfyUI
- [x] Juggernaut XL v9 + SDXL + VAE configurados
- [x] 28 imágenes de referencia (16 para LoRA dataset, 12 adicionales)
- [x] 9 posts de Instagram con captions generadas
- [x] Trigger word: `eir_niflheimr`
- [x] Kohya_ss instalado (PyTorch 2.11.0+cu130 FUNCIONAL)
- [x] Cuenta conceptual @eir.creates definida
- [x] LoRA entrenado hasta epoch 5 (y checkpoint epoch 10 + final disponibles)

## DATOS CRÍTICOS

- **Hardware**: RTX 3060 12GB VRAM + 48GB RAM + AMD Ryzen 5 5500
- **ComfyUI**: `~/comfy/ComfyUI` (python3 directo, NO venv), puerto 8188
  - Start: `cd ~/comfy/ComfyUI && python3 main.py --listen --port 8188`
- **Kohya_ss**: `/mnt/d/Proyectos/Yggdrasil/Muspelheim/AI-Influencer/tools/kohya_ss/`
  - PyTorch 2.11.0+cu130 FUNCIONAL en venv
  - **NO usar AdamW8bit** — bitsandbytes tiene error con libnvJitLink.so.13 (CUDA 13)
  - **USAR AdamW normal** — funciona perfecto con 12GB VRAM
  - Python: `tools/kohya_ss/venv/bin/python3`
- **LoRA actual**: epoch 5, 10, y final en `/assets/lora_output/`
- **LoRA en ComfyUI**: `~/comfy/ComfyUI/models/loras/eir_niflheimr_lora_r32_epoch10.safetensors`
- **Dataset**: 16 imágenes 1024x1024 + 16 captions mejorados en `assets/lora_dataset/eir_niflheimr/`
- **Negative prompts optimizados**: en `config/prompts/eir_prompts_v2.json`
- **Test images**: `outputs/test_batch_lora/` (6 imágenes generadas con epoch 10)

## PRÓXIMOS PASOS — LISTO PARA EJECUTAR

### PASO 1: Entrenar LoRA v2

```bash
# Dry run (verificar todo sin entrenar):
bash /mnt/d/Proyectos/Yggdrasil/Muspelheim/AI-Influencer/scripts/train_eir_v2.sh --dry-run

# Entrenar para real (~45-60 min en RTX 3060 12GB):
bash /mnt/d/Proyectos/Yggdrasil/Muspelheim/AI-Influencer/scripts/train_eir_v2.sh
```

**Parámetros v2 optimizados:**
- dim=32, alpha=16, dropout=0.1
- AdamW (LR 2e-4 UNet, 1e-4 TE)
- cosine schedule, warmup 100 steps
- min_snr_gamma=5, keep_tokens=1
- 1800 steps, save cada 100 steps
- bf16, xformers, gradient checkpointing

### PASO 2: Evaluar Checkpoints

```bash
# Después de entrenar, con ComfyUI corriendo:
python3 /mnt/d/Proyectos/Yggdrasil/Muspelheim/AI-Influencer/scripts/evaluate_lora_checkpoints.py
```

Genera 1 imagen de test por checkpoint (18 total). Elegir el mejor visualmente (generalmente step 800-1400).

### PASO 3: Generar Batch Completo

Usar `config/prompts/eir_prompts_v2.json` con ComfyUI API para generar las 9 posts de IG + extras.

### PASO 4: Crear Cuentas (TU PARTE)

Ver PLAN_COMPLETO.md sección 1.2 para bios, handles, y estrategia.

---

## ARCHIVOS CLAVE

| Archivo | Contenido |
|---------|-----------|
| `PLAN_COMPLETO.md` | **Plan detallado de 3 fases** (NUEVO) |
| `NEXT_STEPS_EIR.md` | Este archivo — instrucciones para siguiente sesión |
| `config/lora/eir_v2_optimized.toml` | **Config LoRA v2 optimizada** (NUEVO) |
| `scripts/train_eir_v2.sh` | **Script de entrenamiento v2** (NUEVO) |
| `scripts/evaluate_lora_checkpoints.py` | **Evaluador de checkpoints** (NUEVO) |
| `config/prompts/eir_prompts_v2.json` | **Prompts v2 + negative prompts + captions** (NUEVO) |
| `README.md` | Visión general del proyecto |
| `PIPELINE.md` | Pipeline de generación completo |
| `LORA_TRAINING.md` | Guía de entrenamiento LoRA paso a paso |
| `PLATFORMS.md` | Estrategia por plataforma |
| `MONETIZATION.md` | Plan de monetización |
| `ACCOUNTS_GUIDE.md` | Guía de configuración de cuentas |
| `outputs/test_batch_lora/` | 6 imágenes de test con LoRA epoch 10 |
| `assets/lora_dataset/eir_niflheimr/` | 16 imágenes + 16 captions mejorados |

---

## NOTAS DE OPTIMIZACIÓN

### LoRA Training (investigación 2025-2026)
1. **dim=32, alpha=16** — sweet spot para character consistency
2. **AdamW** con LR 2e-4, TE LR 1e-4 — más estable que Prodigy para primer training
3. **min_snr_gamma=5** — reduce noise bias en SDXL
4. **tag_dropout=0.05** — mejora trigger word dependency
5. **keep_tokens=1** — trigger word SIEMPRE primero en caption
6. **cosine con warmup 100 steps** — mejor que constant LR
7. **1800 steps** — óptimo para 16 imágenes
8. **NO usar AdamW8bit/bitsandbytes** — error con CUDA 13 (libnvJitLink.so.13)

### Social Media (investigación 2025-2026)
1. **Carousel posts (5-10 slides)** = 3x reach en IG
2. **Process/BTS content** = 3-5x más engagement
3. **Character-driven accounts** crecen más rápido que generic AI art
4. **Lore/worldbuilding** impulsa parasocial engagement
5. **5-15 hashtags** en IG (no 30)
6. **IG Reels** = #1 discovery tool 2025-2026
7. **TikTok**: process videos >> static images

---

*Actualizado sesión autónoma Mayo 2026. Todo listo para entrenar LoRA v2. Ejecutar `train_eir_v2.sh` cuando se decida. 🎨冰⚡*
