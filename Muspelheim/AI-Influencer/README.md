# AI Influencer Project — "Eir" ✦

## Visión

**Eir** es una influencer AI de arte digital y estética dark fantasy. No es solo "otra chica generada por IA" — es un personaje con lore nórdico que genera y exhibe arte, estética, y contenido visual de alta calidad.

### ¿Por qué Eir?
- **Eir** = diosa nórdica de la sanación y la medicina, asociada con la luz en la oscuridad
- Encaja con la estética Yggdrasil (dark fantasy, mitología nórdica)
- Nicho undersaturated: AI art + dark fantasy aesthetic (no compite con las miles de chicas genéricas)
- Tu hardware puede correr Stable Diffusion con CPU offload o Flux

---

## Nicho: Arte Digital / Dark Fantasy Aesthetic

**Target**: Personas interesadas en dark fantasy, estética gótica, arte conceptual, ilustración digital, y diseño visual.

**Diferenciador**: Eir no es solo un rostro bonito — es una curadora de lo oculto y lo bello. Sus posts muestran:
- Arte conceptual generado por SD/Flux con su "toque"
- Estética de mundo: paisajes nórdicos, runas, criaturas mitológicas
- Tutoriales cortos de técnicas de generación (ControlNet, LoRA, composición)
- "Detrás del lienzo" — mostrando cómo se crea cada pieza

---

## Stack Tecnológico

### Generación de Imágenes
| Herramienta | Uso | Prioridad |
|-------------|-----|-----------|
| **Stable Diffusion XL / Flux** | Generación principal de personaje | Alta |
| **LoRA entrenado** | Consistencia facial de Eir | Crítica |
| **ControlNet** | Poses específicas, composición | Alta |
| **IP-Adapter** | Transferencia de estilo | Media |
| **Upscaler (ESRGAN)** | Calidad final para posts | Alta |

### Hardware (tu setup)
- **GPU**: RTX 3060 4GB → SD XL con --medvram o Flux con CPU offload
- **RAM**: 48GB → suficiente para CPU offload de modelos grandes
- **Alternativa cloud**: RunPod ($0.20/hr A100) para LoRA training

### Automatización
- **Lilith batch mode** para generación programática
- **Python scripts** para pipeline de contenido
- **Cron jobs** para posting automático

### Plataformas (orden de prioridad)
1. **Instagram** — visual principal (cuenta profesional, "Digital Creation")
2. **TikTok** — motor de crecimiento (Reels cortos con efecto)
3. **Twitter/X** — comunidad AI art, engagement, threads educativos
4. **Patreon** — monetización (exclusive content, tutorials, LoRA files)
5. **CivitAI** — publicación de LoRAs, visibilidad en comunidad SD

---

## Fases del Proyecto

### FASE 0: Fundamentos (1-2 semanas)
- [ ] Definir diseño de personaje de Eir (rasgos, estilo, paleta)
- [ ] Crear sheet de referencia (reference sheet)
- [ ] Setup de entorno SD/Flux en WSL
- [ ] Crear cuenta IG profesional + TikTok + Twitter/X
- [ ] Escribir bio y lore de Eir

### FASE 1: Consistencia del Personaje (2-3 semanas)
- [ ] Recopilar 20-30 imágenes base de alta calidad
- [ ] Entrenar LoRA de Eir (via Kohya_ss, RunPod recomendado)
- [ ] Validar consistencia facial en múltiples poses/estilos
- [ ] Crear set de 30-50 imágenes para stock inicial

### FASE 2: Contenido Inicial (2-3 semanas)
- [ ] Producir primer batch de 15-20 posts de alta calidad
- [ ] Escribir captions con personalidad de Eir
- [ ] Hashtags research (dark art, fantasy art, AI art, gothic aesthetic)
- [ ] Crear 5-10 Reels/TikToks (edición con CapCut o DaVinci)

### FASE 3: Growth (meses 2-4)
- [ ] Publicación consistente: 1 post/día IG, 2-3 TikToks/semana
- [ ] Engagement manual: comentar en cuentas de nicho
- [ ] Colaboraciones con artistas de la comunidad
- [ ] Analizar métricas y ajustar estrategia

### FASE 4: Monetización (meses 4-6)
- [ ] Lanzar Patreon ( tiers: $3, $10, $25)
- [ ] Publicar LoRA de Eir en CivitAI (con watermark)
- [ ] Commissions personalizadas
- [ ] Brand deals con marcas de estética alternativa

---

## Reglas de Oro (lecciones del Reddit post)

1. **Cuenta Profesional SIEMPRE** — Marcar como "Digital Creation" evita bans
2. **Transparencia** — Siempre indicar que es IA generada
3. **Personalidad, no solo fotos** — Eir tiene lore, opiniones, "gustos"
4. **Consistencia > Cantidad** — Mejor 5 fotos geniales que 20 mediocres
5. **TikTok es el motor** — Reels/TikToks dan 10x más alcance que posts estáticos
6. **No pagar por promoción** — Usar ads oficiales o crecimiento orgánico
7. **Comunidad > Seguidores** — Interacción real en nicho specific

---

## Estructura del Proyecto

```
AI-Influencer/
├── README.md              # Este archivo
├── CHARACTER.md           # Diseño de personaje, lore, personalidad
├── PIPELINE.md            # Workflow de generación de contenido
├── PLATFORMS.md           # Guía por plataforma (IG, TikTok, X, Patreon)
├── MONETIZATION.md         # Estrategias de monetización
├── config/
│   ├── generation.yaml    # Configs de SD/Flux (prompts, steps, samplers)
│   └── posting.yaml       # Horarios de publicación, captions templates
├── scripts/
│   ├── generate.py        # Pipeline de generación batch
│   ├── post_scheduler.py  # Scheduler de publicación
│   ├── train_lora.py      # Script para entrenar LoRA
│   └── watermark.py       # Agregar watermark sutil
├── assets/
│   ├── reference_sheets/   # Reference sheets de Eir
│   ├── lora/              # LoRA entrenado
│   └── templates/         # Templates de posts, stories
├── content/
│   ├── posts/             # Posts generados listos para publicar
│   ├── reels/             # Videos cortos
│   └── archive/           # Contenido ya publicado
└── analytics/
    └── metrics.json       # Tracking de métricas
```

---

## Siguiente Paso

Empezar con **FASE 0**: diseñar el personaje de Eir y setupear el entorno de generación.