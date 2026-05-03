# Eir — Instrucciones para la Siguiente Instancia

> **Estado actual**: FASE 0 COMPLETADA. LoRA entrenado solo hasta epoch 5 (de 15). FASE 1 pendiente.

---

## FASE 0 — COMPLETADA

- [x] ComfyUI v0.20.1 instalado en ~/comfy/ComfyUI
- [x] Juggernaut XL v9 + SDXL + VAE configurados
- [x] 28 imágenes de referencia (16 para LoRA dataset, 12 adicionales)
- [x] 9 posts de Instagram con captions generadas
- [x] Trigger word: `eir_niflheimr`
- [x] Kohya_ss instalado (PyTorch venv necesita fix para re-entrenar)
- [x] Cuenta conceptual @eir.creates definida
- [x] LoRA entrenado hasta epoch 5 (checkpoint en `/mnt/d/Proyectos/Yggdrasil/Muspelheim/AI-Influencer/outputs/lora/`)

## DATOS CRÍTICOS

- **Hardware**: RTX 3060 12GB VRAM + 48GB RAM
- **ComfyUI**: `~/comfy/ComfyUI` con venv propio, puerto 8188
- **Kohya_ss**: Instalado pero PyTorch venv.ro necesita fix (`pip install torch torchvision --force-reinstall` dentro del venv)
- **LoRA actual**: Solo epoch 5 de 15 — PRODUCE IMÁGENES PERO CALIDAD ES BÁSICA
- **Imágenes de referencia**: `/mnt/d/Proyectos/Yggdrasil/Muspelheim/AI-Influencer/assets/reference/`
- **Config LoRA**: `/mnt/d/Proyectos/Yggdrasil/Muspelheim/AI-Influencer/config/lora/`
- **Captions**: `/mnt/d/Proyectos/Yggdrasil/Muspelheim/AI-Influencer/assets/captions/`

---

## FASE 1 — Crear Cuentas Sociales y Publicar

### 1.1 Crear cuentas sociales (@eir.creates)

**Plataformas prioridad (en orden):**
1. **Instagram** — @eir.creates (principal, arte digital dark fantasy)
2. **Twitter/X** — @eir_creates (secondary, vox populi del proyecto)
3. **TikTok** — @eir.creates (video content, time-lapses de generación)

**Configuración:**
- Foto de perfil: Generar con ComfyUI usando el LoRA epoch 5 (retrato estilo dark fantasy)
- Bio: "Norse goddess of creation. Digital art from the void. 🎨⚔️ 🔮"
- Link en bio: https://brierainz.github.io/Yggdrasil/ (sitio del ecosistema)
- Tema: Dark fantasy, mitología nórdica, arte digital con IA, proceso creativo

**NOTA**: NO publicar hasta tener al menos 6 imágenes de calidad aceptable.

### 1.2 Re-entrenar LoRA (OPCIONAL pero recomendado)

El LoRA actual solo tiene 5 epochs. Para mejorar calidad:
```bash
# 1. Iniciar ComfyUI
cd ~/comfy/ComfyUI && source venv/bin/activate && python main.py --listen --port 8188 &

# 2. Fix Kohya venv (si no funciona)
cd ~/kohya_ss && source venv/bin/activate
pip install torch torchvision --force-reinstall

# 3. Re-entrenar LoRA completo (15 epochs)
# Usar la config existente en config/lora/
```

### 1.3 Generar primer batch de imágenes

Usar ComfyUI con el LoRA (epoch 5 o re-entrenado) para generar al menos 6-9 imágenes de alta calidad con prompts como:

Prompt base: `eir_niflheimr, dark fantasy portrait, norse goddess, ice magic, glowing runes, ultrarealistic, 4k`

Variantes:
- Retrato dramático con fondo de aurora boreal
- Creando arte en un taller nórdico
- De pie ante el pozo de Mimir
- Con pincel mágico pintando el Yggdrasil
- Cuerpo completo en paisaje invernal nórdico
- Close-up con ojos brillantes (efecto ice-blue)

### 1.4 Publicar primer batch

Los 9 posts ya tienen captions generadas. Publicar en Instagram con:
- Imágenes generadas con ComfyUI + LoRA
- Captions del archivo `assets/captions/`
- Hashtags: #DarkFantasyArt #NorseMythology #AIart #DigitalArt #EirNiflheimr #Yggdrasil
- Horario: 1-2 posts por día, no spam

---

## FASE 2 — Crecimiento

### 2.1 Contenido recurrente
- **Process videos**: Time-lapses de generación de imágenes en ComfyUI
- **Before/After**: Raw SDXL vs LoRA-fine-tuned
- **Mythology threads**: Hilos sobre Eir y otras diosas nórdicas
- **Behind the scenes**: Mostrar los prompts, los parámetros, el workflow

### 2.2 Monetización (futuro)
- Ver `MONETIZATION.md` para la estrategia completa
- Print-on-demand (Redbubble, Society6)
- Commissions
- Patreon/Ko-fi para supporters

---

## ARCHIVOS CLAVE

| Archivo | Contenido |
|---------|-----------|
| `README.md` | Visión general del proyecto |
| `PIPELINE.md` | Pipeline de generación completo |
| `LORA_TRAINING.md` | Guía de entrenamiento LoRA paso a paso |
| `PLATFORMS.md` | Estrategia por plataforma |
| `MONETIZATION.md` | Plan de monetización |
| `ACCOUNTS_GUIDE.md` | Guía de configuración de cuentas |
| `config/lora/` | Configs de entrenamiento LoRA |
| `outputs/lora/` | Checkpoints LoRA generados |
| `assets/reference/` | 28 imágenes de referencia |
| `assets/captions/` | 9 captions de Instagram |

---

*Generado por la instancia anterior. Buena suerte, siguiente instancia. 🎨冰⚡*
