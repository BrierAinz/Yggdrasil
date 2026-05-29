# LoRA Training Guide — Eir Niflheimr
## Paso a paso para entrenar el LoRA de carácter de Eir

---

## Requisitos de Hardware

| Componente | Mínimo | Recomendado | Nuestro Setup |
|-----------|--------|-------------|---------------|
| VRAM | 8GB | 12GB+ | 12GB RTX 3060 ✅ |
| RAM | 16GB | 32GB+ | 48GB ✅ |
| Storage | 20GB | 50GB+ | 567GB libre ✅ |
| Tiempo estimado | 1-2h | 30-60min | ~60min |

---

## FASE 1: Generar Reference Sheet (20-30 imágenes)

### Reglas para imágenes de entrenamiento
1. **Consistencia facial**: mismo personaje en todos los shots
2. **Variedad de ángulos**: 40% front, 25% 3/4, 20% side, 15% full body
3. **Variedad de expresiones**: neutral, seria, sonriendo, contemplativa
4. **Variedad de outfits**: 3-4 outfits mínimos
5. **Backgrounds variados**: fondo neutro (50%), fondos temáticos (50%)
6. **Sin texto/avertes**: sin marcas de agua, logos, texto
7. **Alta resolución**: mínimo 512x768 (portrait), ideal 832x1216

### Método: Generar con SDXL base, luego iterar

#### Opción A: Sin LoRA (generación inicial)
Usar Juggernaut XL o DreamShaper XL con prompts detallados:

```
Prompt: masterpiece, best quality, photorealistic, 1girl,
pale skin, violet eyes with silver highlights, long black hair
with purple tips, oval face, subtle freckles on cheeks,
silver runic necklace, [OUTFIT], [BACKGROUND],
shot on Sony A7IV, 85mm f/1.4

Negative: cartoon, anime, 3d, deformed, extra fingers,
blurry, watermark, text
```

Generar 40-50 imágenes, seleccionar las 25-30 mejores que mantienen
consistencia en rasgos faciales.

#### Opción B: Usar ControlNet para consistencia
1. Generar una imagen base excelente de Eir
2. Usar ControlNet Depth + IP-Adapter para mantener pose
3. Variar outfits y backgrounds manteniendo rostro consistente

#### Opción C: Usar IMG2IMG para variaciones
1. Generar 1 imagen base perfecta
2. Usar img2img con denoise 0.4-0.6 para crear variaciones
3. Cambiar prompts de outfit/background

### Prompts por tipo de imagen

| Cantidad | Tipo | Prompt Base |
|----------|------|------------|
| 8-10 | Front face | `1girl, front face, looking at viewer, ...` |
| 6-8 | 3/4 view | `1girl, three quarter view, ...` |
| 4-5 | Side profile | `1girl, side profile, looking away, ...` |
| 4-5 | Full body | `1girl, full body, standing, ...` |
| 3-4 | Close-up | `1girl, close up face, macro detail, ...` |
| 3-4 | Artistic | `1girl, dark fantasy style, ...` |

---

## FASE 2: Preparar Captions

### Trigger Word: `eir_niflheimr`

Cada imagen necesita un archivo `.txt` con el mismo nombre:

```
eir_001.png → eir_001.txt
eir_002.png → eir_002.txt
```

### Formato de caption

```
eir_niflheimr, 1girl, [ANGLE], [OUTFIT], [EXPRESSION], [BACKGROUND], [LIGHTING]
```

**IMPORTANTE**:
- `eir_niflheimr` SIEMPRE primero (es el trigger word)
- Describir lo que SE VE, no lo que quieres evitar
- NO重复 descripciones entre imágenes
- Variedad en captions = LoRA más flexible

### Ejecutar preparación automática:
```bash
cd /mnt/d/Proyectos/Yggdrasil/Muspelheim/AI-Influencer
python scripts/train_lora.py --prepare
```

---

## FASE 3: Entrenar LoRA con Kohya_ss

### Instalar Kohya_ss

```bash
cd ~
git clone https://github.com/kohya-ss/sd-scripts.git kohya_ss/sd-scripts
cd kohya_ss/sd-scripts
pip install -r requirements.txt
```

### Configuración de entrenamiento

| Parámetro | Valor | Razón |
|-----------|-------|-------|
| network_dim | 32 | Buen balance detalle/generalización |
| network_alpha | 16 | dim/2, estándar |
| learning_rate | 1e-4 | Standard para LoRA |
| lr_scheduler | cosine | Buen converge |
| max_train_steps | 2000 | ~70 epochs con 25 imágenes |
| batch_size | 1 | RTX 3060 12GB |
| mixed_precision | bf16 | RTX 3060 soporta bf16 |
| optimizer | AdamW8bit | Memoria eficiente |
| gradient_accum | 2 | Efectivo batch size 2 |
| resolution | 832,1216 | Portrait SDXL |

### Generar script de entrenamiento:
```bash
cd /mnt/d/Proyectos/Yggdrasil/Muspelheim/AI-Influencer
python scripts/train_lora.py --train
```

### Lanzar entrenamiento:
```bash
bash ~/comfy/ComfyUI/models/lora/training_scripts/train_eir.sh
```

### Tiempo estimado
- RTX 3060 12GB: ~60-90 minutos para 2000 steps
- Monitor con `nvidia-smi` en otra terminal

---

## FASE 4: Testing y Selección

### Después del entrenamiento

1. Se generan checkpoints cada 5 épocas: `eir_niflheimr-000005.safetensors`, etc.
2. Probar CADA checkpoint con el mismo prompt de test:

```
Prompt: eir_niflheimr, 1girl, front face, pale skin, violet eyes,
long black hair with purple tips, silver runic necklace, simple background,
studio lighting, photorealistic
```

3. Evaluar:
   - ¿Se parece a Eir? (consistencia facial)
   - ¿El estilo se mantiene? (no overfitting)
   - ¿Es flexible? (puede cambiar outfits, backgrounds)

### Criterios de calidad
- ✅ Rostro consistente entre seeds
- ✅ Mantiene features clave (violet eyes, black hair)
- ✅ Responde a modificaciones de prompt (outfits, backgrounds)
- ✅ No introduce artefactos o deformaciones
- ❌ Overfitting: siempre mismo outfit/pose sin importar prompt
- ❌ Underfitting: no se parece a Eir

### Seleccionar el mejor checkpoint
Generalmente el checkpoint en el ~80% del entrenamiento funciona mejor
(epoch 12-15 de 20, step 1600-1800 de 2000).

---

## FASE 5: Instalar LoRA en ComfyUI

```bash
# Copiar el LoRA seleccionado a ComfyUI
cp /mnt/d/Proyectos/Yggdrasil/Muspelheim/AI-Influencer/assets/lora/eir_niflheimr.safetensors \
   ~/comfy/ComfyUI/models/loras/
```

### Usar en ComfyUI workflow
En el prompt, agregar: `<lora:eir_niflheimr:0.8>`
(el peso 0.7-0.9 es el rango recomendado)

---

## Troubleshooting

| Problema | Solución |
|----------|----------|
| OOM (Out of Memory) | Reducir batch_size, usar gradient checkpointing, reducir resolución |
| LoRA no aprende | Aumentar learning_rate, más steps, verificar captions |
| Overfitting | Reducir steps, aumentar regularization, reducir network_dim |
| Rostro inconsistente | Más imágenes de entrenamiento, mejores captions, verificar trigger word |
| Artefactos | Reducir network_dim (16 en vez de 32), reducir learning rate |
| Colores lavados | Agregar más caption detail, verificar VAE |
