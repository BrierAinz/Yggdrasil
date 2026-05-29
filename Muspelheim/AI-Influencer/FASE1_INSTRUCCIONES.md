# Eir — FASE 1: Instrucciones para Continuar

## Estado Actual (Automated by another instance)

### LoRA Training — COMPLETADO EXITOSAMENTE
- **Checkpoint final guardado**: `/mnt/d/Proyectos/Yggdrasil/Muspelheim/AI-Influencer/assets/lora_output/eir_niflheimr_lora_r32.safetensors`
- **Config**: Network dim 32, alpha 16, cosine scheduler, bf16, seed 42
- **Training**: 15 epochs completos, 2400 steps, loss final ~0.102
- **Trigger word**: `eir_niflheimr`
- **Base model**: SDXL 1.0 (`sd_xl_base_1.0.safetensors`)

### FASE 0 — COMPLETADA
- ComfyUI v0.20.1 instalado en `~/comfy/ComfyUI` (venv propio, port 8188)
- Juggernaut XL v9 + SDXL base + VAE configurados
- 28 imágenes de referencia (16 en dataset LoRA)
- 9 IG posts con captions generados
- Kohya_ss instalado (el training completó sin errores)
- LoRA entrenado y listo para inferencia

---

## FASE 1.1: Crear Cuentas Sociales

### Instagram (@eir.creates)
1. Crear cuenta de Instagram Business/Creator
2. Username: `eir.creates` (o alternativa: `eir_niflheimr`, `eir.artistry`)
3. Bio template: `Norse goddess of healing, reborn as digital art. AI-generated dark fantasy. ⚔️🧊`
4. Profile pic: generar con ComfyUI usando el LoRA entrenado
5. Link en bio → Yggdrasil website

### Twitter/X (@eir_creates)
1. Crear cuenta
2. Mismo aesthetic que IG
3. Bio: `Digital dark fantasy art. Norse mythology meets AI. ⚔️🧊 Part of @Yggdrasil_ ecosystem`

### Reddit (u/eir_creates)
1. Para posting en r/StableDiffusion, r/aiArt, r/DarkArt, r/FantasyArt
2. Karma building strategy

## FASE 1.2: Generar Primer Batch de Posts (9 posts)

### Requisitos Previos
1. **Iniciar ComfyUI**:
```bash
cd ~/comfy/ComfyUI && source .venv/bin/activate && python main.py --port 8188 --listen
```

2. **Copiar LoRA al directorio de ComfyUI**:
```bash
cp /mnt/d/Proyectos/Yggdrasil/Muspelheim/AI-Influencer/assets/lora_output/eir_niflheimr_lora_r32.safetensors ~/comfy/ComfyUI/models/loras/
```

3. **Workflow de generación**: Usar API de ComfyUI con el LoRA cargado
   - Prompt base: `eir_niflheimr, [theme], dark fantasy art, [style details]`
   - Negative: `blurry, low quality, watermark, text, deformed, extra fingers`
   - Config: 1024x1024, steps 30, cfg 7, sampler euler_ancestral

### Los 9 Posts (temáticas)
1. **Awakening** — Eir emerges from ice, Norse runes glowing
2. **The Healer's Touch** — Healing hands, ice crystals, curing
3. **Niflheim Frost** — Misty realm, frozen landscape, figure
4. **Runic Divination** — Scattered runes, mystical glow
5. **The Forge** — Dark workshop, sparks, metalwork
6. **Frost Queen** — Crown of ice, regal pose, dark palette
7. **Beast Companion** — Wolf or raven, dark bond
8. **The Well of Wisdom** — Mimir's well, reflection, visions
9. **Twilight Prophecy** — World tree silhouette, apocalyptic sky

### Captions
Ya existen en: `/mnt/d/Proyectos/Yggdrasil/Muspelheim/AI-Influencer/assets/ig_posts/`
Archivo: `captions_batch_1.txt`

### Hashtags por tema
- Generales: `#AIArt #DarkFantasy #NorseMythology #DigitalArt #StableDiffusion #AIgenerated`
- Específicos por post: `#EirNiflheimr #Niflheim #Runes #Frost #FantasyArt`

## FASE 1.3: Publicación y Monetización
1. Publicar 1 post/día en IG (primera semana)
2. Cross-post a Twitter/X
3. Engage con comunidad AI art
4. Considerar Patreon/Ko-fi para prints de alta resolución
