# LoRA v2 Training Log

## Configuración

| Parámetro | Valor |
|-----------|-------|
| Base model | Juggernaut-XL v9 (SDXL) |
| Network module | networks.lora |
| Network dim | 32 |
| Network alpha | 16 |
| Network dropout | 0.1 |
| Resolution | 1024x1024 |
| Bucket reso steps | 64 |
| Train batch size | 1 |
| Max train steps | 1800 |
| Save every n steps | 100 |
| Optimizer | AdamW |
| Optimizer args | weight_decay=0.01 |
| Learning rate | 2e-4 |
| Text encoder LR | 1e-4 |
| UNet LR | 2e-4 |
| LR scheduler | cosine |
| LR warmup steps | 100 |
| Min SNR gamma | 5 |
| Gradient checkpointing | True |
| Mixed precision | bf16 |
| xformers | True |
| SDPA | True |
| Cache latents | True |
| Keep tokens | 1 |
| Shuffle caption | True |
| Caption tag dropout rate | 0.05 |
| Seed | 42 |
| Dataset | 16 images x 20 repeats = 320 samples |

## Problemas Resueltos

1. **torchview compatibility** — torch 2.11.0+cu130 vs torchvision 0.21.0+cu124
   - Solución: `pip install torchvision==0.26.0+cu130 --index-url https://download.pytorch.org/whl/cu130`
2. **pip faltante en kohya venv** — Restaurado con get-pip.py
3. **Dataset structure** — Kohya necesita formato `padrefolder/NN_nombre/`
4. **CLI args** — Eliminados flags no reconocidos: --tag_dropout, --weight_decay, --min_lr_ratio, --persistent_workers
5. **bitsandbytes** — No compatible con CUDA 13.2, usando AdamW (no 8bit)

## Loss Progress

| Step | Loss |
|------|------|
| 100 | ~0.12 |
| 200 | ~0.11 |
| 300 | ~0.10 |
| 500 | ~0.097 |
| 700 | ~0.095 |
| 900 | ~0.091 |
| 1100 | ~0.091 |
| 1300 | ~0.089 |
| 1500 | ~0.086 |
| 1700 | ~0.086 |
| 1800 (final) | ~0.086 |

## Evaluación de Checkpoints

| Checkpoint | Portrait Score | Armor Score | Promedio | Notas |
|------------|----------------|-------------|----------|-------|
| step 600 | 9/10 | 7/10 | 8.0 | Excelente consistencia, un poco underfit |
| step 800 | 7/10 | - | 7.0 | Más anime-style, algunos artefactos |
| step 1000 | 8/10 | - | 8.0 | Bien balanceado |
| step 1200 | 8/10 | 8.5/10 | 8.3 | Buena consistencia |
| **step 1400** | **9/10** | - | **9.0** | **Ganador - mejor balance calidad/consistencia** |
| step 1600 | - | - | - | No evaluado individualmente |
| step 1800 | - | 8/10 | 8.0 | Similar a 1400 pero marginalmente más overfit |
| final | 8/10 | - | 8.1 | Buena consistencia, ligero overfit |

**Selección: step 1400** → `eir_niflheimr_v2_best.safetensors`

## Archivos Resultantes

- 19 checkpoints en `assets/lora_output/eir_niflheimr_v2_lora-step00000XXX.safetensors`
- Mejor checkpoint: `~/comfy/ComfyUI/models/loras/eir_niflheimr_v2_best.safetensors` (step 1400)
- 24 imágenes de feed + 6 assets de perfil en `outputs/`
- 17 imágenes de evaluación en `outputs/eval_checkpoints/`

## Comando de Retorno (si se necesita reentrenar)

```bash
bash /mnt/d/Proyectos/Yggdrasil/Muspelheim/AI-Influencer/scripts/train_eir_v2.sh
```
