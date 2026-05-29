# Workflow de Stable Diffusion para Ainz

## Objetivo
Generar assets visuales consistentes (Pixel Art Horror, Dark Fantasy) para Yggdrasil/Noteh.

## Herramientas
- **Automatic1111 (WebUI):** Para experimentaciÃ³n rÃ¡pida y entrenamiento de LoRA.
- **ComfyUI:** Para pipelines complejos y automatizaciÃ³n (Node-based).

## Flujo de Trabajo de Entrenamiento (LoRA)
1.  **Dataset:**
    - ImÃ¡genes 512x512 o 768x768.
    - Captions detallados en archivos `.txt` (tags de booru o lenguaje natural).
    - Estructura: `dataset/concept/XX_triggerword/*.png`.
2.  **ConfiguraciÃ³n Kohya_ss:**
    - Base Model: SD 1.5 (para pixel art) o SDXL (para realismo/detalles).
    - Network Rank (Dim): 32 o 64 (suficiente para estilo).
    - Alpha: Mitad del Dim (16 o 32) para estabilidad.
    - Learning Rate: Text Encoder 5e-5, Unet 1e-4.
3.  **Entrenamiento:**
    - Epochs: 10-15.
    - Guardar cada 2 epochs para comparar.

## Flujo de Trabajo de GeneraciÃ³n (Inferencia)
1.  **Prompting:**
    - Positivo: `(score_9, score_8_up), pixel art, dark fantasy, horror, triggerword, <lora:my_lora:0.8>`
    - Negativo: `(score_1, score_2, score_3), blurry, low quality, 3d render, vector`
2.  **Upscaling:**
    - Usar `R-ESRGAN 4x+ Anime6B` para pixel art limpio.
    - Denoising strength bajo (0.3-0.4) en Hires. Fix para mantener la estructura.

## Estructura de Salida
- Las imÃ¡genes finales deben moverse a `Midgard/assets/sprites/` o `Svartalfheim/assets/ui/` segÃºn corresponda.
