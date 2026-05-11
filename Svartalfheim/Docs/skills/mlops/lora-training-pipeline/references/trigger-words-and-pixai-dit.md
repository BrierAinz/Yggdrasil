# LoRA Trigger Words & PixAI DiT Training Reference

## DiT.1 vs DiT.2 Trigger Word Requirements

Based on PixAI blog (https://blog.pixai.art/en/lora-trigger-words-guide/):

### DiT.1 (Tsubaki) — Short Tags
- Format: `character_name, source_work, other_attributes`
- Example (character): `hatsune_miku, vocaloid, twin_tails`
- Example (style): `ink_wash_style`
- Keep trigger words **short and specific**
- Multi-word tags use underscores: `aqua_hair`, `twin_tails`

### DiT.2 (Tsubaki.2) — Descriptive Phrases (30+ chars)
- Format: A compact **feature inventory sentence** (not just a name)
- Example (character): `A young woman with long silver hair, golden eyes, and a futuristic black visor`
- Example (style): `KNQ style, mesmerizer hypnosis art, spiral eyes, psychedelic vortex backgrounds, neon magenta cyan purple palette, hard cel shading, bold lineart, concentric rings, mind control trance aesthetic`
- **MUST be at least 30 characters** — shorter triggers leave training quality on the table for DiT.2
- Describe distinguishing visual attributes, not just a name token

### 256 Character Limit
- PixAI enforces a 256-character max on trigger words
- Keep descriptions rich but concise — aim for 80–200 characters

## What to INCLUDE in Trigger Words

### Character LoRAs — Permanent Features Only
| Include (permanent) | Avoid (variable) |
|---|---|
| Eye color/characteristics: `purple_eyes`, `heterochromia` | Clothing/outfit: `dress`, `bodysuit` |
| Unique markings: `facial_tattoo`, `beauty_mark` | Pose-specific: `sitting`, `arms_up` |
| Signature accessories: `hair_ornament`, `tiara` | Background: `outdoors`, `night` |
| Distinctive anatomy: `pointy_ears`, `fangs` | Temporary elements |

### Style LoRAs — Shared Visual Characteristics Only
Style LoRAs should describe the **visual grammar** shared across all training images:

| Include | Avoid |
|---|---|
| Line art style: `bold lineart`, `clean lineart` | Character names: `hatsune_miku` |
| Coloring technique: `cel shading`, `flat colors` | Specific outfits: `necktie`, `uniform` |
| Color palette: `neon magenta cyan purple` | Specific poses: `hands raised` |
| Background motifs: `concentric rings`, `vortex` | Artist names: `artist:nixeu` |
| Recurring effects: `spiral eyes`, `psychedelic` | Variable elements per image |
| Mood/aesthetic: `mind control trance aesthetic` | |

## How to Analyze Your Dataset for Style Trigger Words

Before training a style LoRA, examine 5–10 representative images and identify the **intersection** of visual traits:

1. **Line style**: thick/thin, sketchy/clean, black/colored outlines
2. **Coloring**: cel shading, flat fills, gradients, airbrush
3. **Shadow style**: hard-edged, soft, color-shifted (cool-toned shadows)
4. **Palette**: dominant color families (warm/cool, saturated/muted)
5. **Background patterns**: abstract patterns, motifs, recurring visual elements
6. **Effects**: glowing, spirals, halftone dots, speed lines, checkerboard
7. **Mood/aesthetic**: trance, dreamy, energetic, dark, etc.

The trigger phrase should capture items 1–7 that appear in **ALL or nearly all** training images. Anything that varies between images belongs in the generation prompt, not the training trigger.

## Prompt Structure at Generation Time

```
<style_trigger>, <character_tags>, <outfit>, <pose>, <scene> <lora:name:weight>
```

Example:
```
KNQ style, mesmerizer hypnosis art, spiral eyes, psychedelic vortex backgrounds, neon magenta cyan purple palette, hard cel shading, bold lineart, hatsune miku, aqua hair, twin tails, detached sleeves, necktie <lora:KNQ_V1:0.8>
```

The style trigger comes first, then variable elements, then the LoRA tag.

## PixAI Training Platform Notes

- Categories: Character, Style, Concept, Pose, etc.
- Model themes (base models): Illustrious-v1.0, NoobAI XL, Hinata v2, Illustrious-v0.1
- DiT.2 is the newer training backend — requires longer trigger phrases for best results
- SDXL and "Other..." options also available