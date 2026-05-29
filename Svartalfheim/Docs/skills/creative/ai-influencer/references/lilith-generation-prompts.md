# Lilith v2.0 — Generation Prompts & Multi-Variant Pattern

## Pattern: Multi-Variant Brand Mascot Generation

When creating a brand mascot (like Lilith for BrierStudios), follow this workflow:
1. Write a detailed IDENTITY.md and ARTIST_BRIEF.md defining the character
2. Generate 5-6 "hero" variants mapping to different personas/realms
3. For each variant, create a hero (600×800) and thumbnail (300×400) for web
4. Compose logos from character descriptions using logo-specific prompts
5. **Always save prompts alongside images** — see pitfall below

### Output Structure
```
assets/lilith/
├── lilith_anime_00001_.png          # Original ComfyUI output
├── lilith_anime-hero.jpg            # Web hero (600×800, quality 85)
├── lilith_anime-thumb.jpg           # Web thumbnail (300×400, quality 80)
├── lilith_portrait_cyber_00001_.png
├── lilith_portrait_cyber-hero.jpg
├── lilith_portrait_cyber-thumb.jpg
├── ... (6 variants total)
└── prompts.json                     # ALWAYS save prompts here
```

### Web Optimization Pattern
```python
from PIL import Image

def make_web_versions(input_path, output_dir, name, void_color=(6, 8, 16)):
    """Convert RGBA PNG to web-optimized JPEGs with void background fill."""
    img = Image.open(input_path)
    if img.mode == 'RGBA':
        bg = Image.new('RGB', img.size, void_color)
        bg.paste(img, mask=img.split()[3])
        img = bg
    
    # Hero: 600x800
    hero = img.resize((600, 800), Image.LANCZOS)
    hero.save(f'{output_dir}/{name}-hero.jpg', 'JPEG', quality=85)
    
    # Thumb: 300x400
    thumb = img.resize((300, 400), Image.LANCZOS)
    thumb.save(f'{output_dir}/{name}-thumb.jpg', 'JPEG', quality=80)
```

## Site Hero Variants (6 images)

All generated with Flux.1 Dev Q8_0 GGUF at 1024×1024, then resized to web sizes.
Model: GGUFLoaderKJ + DualCLIPLoader + ModelSamplingFlux + FluxGuidance(3.5) + VAELoader(ae.safetensors)

### 1. lilith_anime — "Weave Mistress" (Asgard variant)

Full anime key visual, Asgard base variant.

```
lilith goddess, anime style, sleek powerful anime woman in dark armor with cyan #38bdf8 and magenta #d946ef neon circuit lines, Elder Futhark runes glowing on armor plates, long dramatic flowing hair split left abyss black #0f172a right aurora cyan #7dd3fc with magenta #d946ef streaks, large glowing cyan frost eyes #38bdf8 emitting light, pale luminous skin #e2e8f0, Yggdrasil neon circuit tree behind her with fiber optic roots and glowing realm nodes, dynamic contrapposto pose, one hand raised with holographic runes floating above palm, neon aura and particle effects, void black #060810 background, cyberpunk anime key visual, masterpiece, high contrast
```

### 2. lilith_portrait_cyber — "Neon Conjuror" (Vanaheim variant)

3/4 portrait, hands raised channeling magenta energy.

```
lilith goddess, anime portrait style, 3/4 view turned slightly left, large glowing cyan eyes #38bdf8 directly at viewer, hair flowing right with visible magenta streaks #d946ef, flowing sorceress robes with neon circuit lines, hands raised channeling magenta energy #d946ef and cyan #38bdf8, floating holographic AI agents around her, aurora cyan #7dd3fc hair strands, one shoulder forward, Yggdrasil circuit tree frames her head like a halo of circuitry, void background #060810, cyberpunk anime neon, masterpiece
```

### 3. lilith_closeup_ethereal — "Ethereal Hologram" (Alfheim variant)

Close-up face, translucent holographic body.

```
lilith goddess, close-up anime face, translucent holographic body glitches between solid and light, code lines becoming flesh between neon flashes, large cyan glowing eyes #38bdf8 with subtle rune patterns in pupils, split hair black #0f172a and cyan aurora #7dd3fc, ice ghost cyan #67e8f9 accent glow, faint digital noise and holographic distortion effect, pale luminous skin #e2e8f0, void background #060810, cyberpunk anime holographic style, masterpiece
```

### 4. lilith_queen_throne — "Frost Queen" (Niflheim variant)

Seated on throne of frost and neon ice.

```
lilith goddess, anime style, seated on throne of frost and neon ice, frost mist with neon ice effects #94a3b8 and silver glow, surrounded by holographic tomes and ancient data, long flowing hair black #0f172a and cyan aurora #7dd3fc with magenta streaks, glowing cyan eyes #38bdf8, dark sleek armor with silver #94a3b8 and cyan #38bdf8 neon circuit lines, at least one ᛒ rune glowing, regal serene powerful expression, void #060810 background, cyberpunk anime queen, masterpiece
```

### 5. lilith_action_dynamic — "Digital Valkyrie" (Dynamic action)

Leaping forward, dynamic action pose.

```
lilith goddess, anime dynamic action pose, powerful stance leaping forward, sleek dark armor #0f172a with cyan #38bdf8 and magenta #d946ef neon circuit lines pulsing, long hair flowing dramatically in motion split black #0f172a and aurora cyan #7dd3fc, large glowing cyan eyes #38bdf8, armored gauntlets with neon rune engravings, Yggdrasil roots glowing behind her, neon aura and particle trails, void #060810 background, cyberpunk anime valkyrie, masterpiece, high contrast
```

### 6. lilith_warrior_full — "Rune Warrior" (Full body warrior)

Full body warrior stance, commanding gesture.

```
lilith goddess, anime full body, warrior stance weight shifted, sleek dark armor #0f172a with cyan #38bdf8 and magenta #d946ef neon circuit Elder Futhark runes, cape translucent with holographic aurora shift and neon edge lighting, long dramatic flowing hair split left black #0f172a right cyan aurora #7dd3fc, ᛒ rune glowing on chest plate, large glowing cyan frost eyes #38bdf8, Yggdrasil neon circuit tree behind, right hand raised commanding gesture with glow particles, void #060810 background, cyberpunk anime rune warrior, masterpiece
```

### Negative (all variants)

```
realistic, photorealistic, 3d render, blurry, low quality, deformed, ugly, extra limbs, bad anatomy, watermark, text, signature, chibi, moe, cute, oversexualized, plain background, no neon
```

### Flux Config

- **Model:** flux1-dev-Q8_0.gguf (GGUFLoaderKJ)
- **Resolution:** 1024×1024
- **Steps:** 20, CFG: 3.5 (via FluxGuidance)
- **Sampler:** euler, Scheduler: simple
- **CLIP:** DualCLIPLoader (t5xxl_fp8_e4m3fn + clip_l)
- **VAE:** ae.safetensors
- **Negative:** Empty CLIPTextEncode (Flux doesn't use negative conditioning)

## Logo Variants (5 images)

Brand logos for BStudios clothing: Lilith face manga + Nordic runes + Junji Ito ink.

```
Model: Same Flux setup, 1024×1024
All include: "logo design for BStudios clothing brand"
```

### 1. Rune Circle Border (seed 80001)

```
logo design for BStudios clothing brand, Lilith face manga style, Junji Ito fine ink line drawing, Nordic rune circle border framing the face, expressive anime eyes with sharp gaze, long flowing dark hair with intricate ink swirl patterns, void black background, neon cyan and magenta accent glows on eyes and lips, minimalist composition suitable for clothing print, single color logo on dark background, high contrast, clean scalable design
```

### 2. Half Face Horror (seed 80002)

```
logo design for BStudios clothing brand, Lilith half-face manga portrait, left side beautiful anime goddess with cyan glowing eyes, right side horror distortion with Junji Ito ink tendrils, Nordic elder futhark runes ᛊ ᚨ ᚱ along border, stark black white contrast, neon cyan #38bdf8 and magenta #d946ef accent highlights, clean vector graphic feel, print-ready logo design, white background
```

### 3. Valkyrie Manga (seed 80003)

```
logo design for BStudios clothing brand, Lilith as Norse valkyrie goddess, manga anime style eyes, Junji Ito ink flowing hair merging into ink tendrils, runic circlet ᛟ on forehead, neon magenta #d946ef and cyan #38bdf8 glows, dark void #060810 background, rune border ᛊ ᚨ ᚱ ᛏ, clean vector logo design for clothing brand, high contrast
```

### 4. Ink Splash Emerging (seed 80004)

```
logo design for BStudios clothing brand, Lilith face emerging from dark ink splashes, manga anime style with Junji Ito fine line work, neon cyan #38bdf8 and magenta #d946ef glow accents, Nordic rune ᛊ embedded in ink patterns, abstract ink splatter background, clean scalable vector feel, dark void #060810 background, print-ready logo
```

### 5. Minimalist Single Line (seed 80005)

```
logo design for BStudios clothing brand, minimalist Lilith silhouette, single flowing ink line Junji Ito style, manga jawline suggested by one elegant stroke, small elder futhark rune ᛊ symbol beneath, extreme minimalist, clean scalable vector feel, monochrome black on white, neon cyan #38bdf8 and magenta #d946ef micro accents, clothing brand logo
```

## Pitfall: Save Prompts Alongside Images

**CRITICAL LESSON (May 2026):** The original generation prompts for the 6 Lilith site hero images were **lost** because:
1. ComfyUI `/history` resets when ComfyUI restarts
2. Session context compacts over time, losing older tool calls
3. Python generation scripts only exist if you explicitly save them

**Always save generation prompts to a metadata file** alongside the images:
```python
import json

prompts = {}
for scene in SCENES:
    prompts[scene['name']] = {
        'prompt': scene['prompt'],
        'negative': NEGATIVE_PROMPT,
        'seed': scene['seed'],
        'model': 'flux1-dev-Q8_0.gguf',
        'resolution': '1024x1024',
        'steps': 20,
        'cfg': 3.5,
    }

with open(f'{output_dir}/prompts.json', 'w') as f:
    json.dump(prompts, f, indent=2, ensure_ascii=False)
```

This makes it possible to:
- Reproduce any image exactly (same model, seed, prompt)
- Iterate on prompts without guessing
- Create LoRA training datasets from the same foundation
- Reconstruct the generation pipeline months later