# Nous Research Competitive Analysis

Full investigation of https://nousresearch.com ecosystem, conducted May 2026.
This analysis informs BrierStudios/Yggdrasil product roadmap, brand strategy, and monetization.

## 8 Branches Investigated

### 1. nousresearch.com (Main Site)
- **Purpose**: Corporate landing, team, mission, product showcase
- **Design**: Minimalist, warm tones (amber #ffe6cb on #041c1c), serif typography (Mondwest)
- **Key features**: Animated terminal demo, copy-to-clipboard code blocks, prominent CTAs
- **Takeaway**: Clean product-page approach. Our BrierStudios site is more dark-fantasy visual with runes/particles — don't dilute this, but DO adopt their whitespace, copy buttons, and terminal demo concept.

### 2. hermes-agent.nousresearch.com (Agent Docs)
- **Purpose**: Full documentation site for Hermes Agent (v0.13.0, 68+ tools)
- **Design**: Same warm minimalist aesthetic, excellent docs structure
- **Key features**: /docs, /llms.txt for agent discoverability, versioned releases, CLI install commands
- **Takeaway**: We should create docs.brierstudios.com with similar structure. /llms.txt is a smart SEO move for AI agents discovering our tools. Terminal demo of Yggdrasil CLI would be our version of their setup command showcase.

### 3. portal.nousresearch.com (API Portal)
- **Purpose**: Model hosting and API access (334+ models)
- **Key features**: Psyche Network integration, model catalog, API keys
- **Takeaway**: Yggdrasil Portal could host our models (Eir LoRA, future models) plus ComfyUI API access. Monetization potential.

### 4. psyche.network/runs (Distributed Training)
- **Purpose**: Distributed AI training network, $500K incentive pool
- **Design**: Clean dashboard with runs visualization
- **Takeaway**: Community-driven compute. Our 9-realm structure could organize distributed training (e.g., Muspelheim for active training, Niflheim for cold storage of models).

### 5. nousresearch.com/releases (42 Releases)
- **Purpose**: Product release blog/changelog
- **Key features**: Timeline format, version numbers, dates, descriptions
- **Takeaway**: We need a /releases page for Yggdrasil ecosystem updates. Could show realm-specific releases (Asgard core updates, Vanaheim agent releases, etc.).

### 6. nousresearch.com/careers (7 Positions)
- **Purpose**: Hiring page for research engineers, product designers
- **Takeaway**: Future consideration — Yggdrasil could have a "Join the Nine Realms" careers page with Norse theming.

### 7. shop.nousresearch.com (16 Products, Shopify)
- **Purpose**: Merch store — NOUS GIRL NEON sign ($420.69!), apparel, accessories
- **Key features**: Shopify backend, character-driven merch (NOUS GIRL is their brand mascot equivalent)
- **Takeaway**: **CRITICAL INSIGHT** — Our Lilith serves the same role as NOUS GIRL. We should create a Lilith Neon LED sign as our flagship product. Print-on-demand (Printful/Printify) is the model. Shopify integrates well.

### 8. nousresearch.com/blog (15 Posts)
- **Purpose**: Technical blog posts, research updates
- **Takeaway**: Blog drives SEO and community engagement. Our Svartalfheim realm (knowledge/docs) should produce regular blog content.

## BrierStudios Adaptation Plan

### What Nous Does Well (Copy/Wrangle)
| Feature | Nous Implementation | BrierStudios Adaptation |
|---------|-------------------|------------------------|
| Brand mascot | NOUS GIRL (stylized human) | Lilith v2.0 (anime/cyberpunk neon) |
| Merch | Shopify store, flagship neon sign | Printful/Printify, Lilith Neon LED sign |
| Terminal demo | Animated CLI showcase | Yggdrasil CLI demo (GIF/CSS animation) |
| Code blocks | Copy-to-clipboard buttons | Copy buttons on repo install commands |
| Docs | Hermes Agent docs site | docs.brierstudios.com + /llms.txt |
| Releases | Timeline changelog | /releases with 9-realm theming |
| API Portal | 334 models, Psyche Network | Yggdrasil Portal (models + ComfyUI API) |

### What Yggdrasil Does Better (Keep/Strengthen)
| Feature | Our Edge |
|---------|----------|
| Identity | Runes + neon + Norse lore > generic AI branding |
| Mascot depth | 18K Lilith brief vs simple NOUS GIRL illustration |
| Visual effects | Particles, mouse tracking, parallax, glow effects |
| Lore structure | 9 realms give narrative depth to every product |
| Site v2.4 | Live with real anime images + interactive gallery |

### 3-Phase Roadmap

**Fase 1 — Quick Wins (IN PROGRESS):**
- [x] Real anime Lilith images replacing SVG silhouette (v2.4 deployed)
- [x] Interactive gallery with click-to-swap hero (v2.4 deployed)
- [ ] Terminal demo animation of Yggdrasil CLI (CSS or GIF)
- [ ] Copy buttons on code blocks in site
- [ ] /releases page with 9-realm timeline
- [ ] More whitespace/padding between sections

**Fase 2 — Medium Term (1 week):**
- docs.brierstudios.com (Hermes Agent docs inspired)
- /lilith dedicated page with expanded gallery (9 variants for 9 realms)
- Dark/Light mode toggle (frost-dark / frost-light)
- /llms.txt for AI agent discoverability

**Fase 3 — Store (2-4 weeks):**
- Printful or Printify integration
- Flagship: Lilith Neon LED sign
- Merch: realm-themed apparel (9 designs)
- Shopify or alternative storefront

## Design Decisions

- **Palette**: Keep frost/cyan/magenta (NOT warm amber like Nous). User preference: "mas frio y con mas movimiento"
- **Style**: Anime/cyberpunk neon (pivoted from dark fantasy in v2.0)
- **Mascot**: Lilith v2.0 (anime goddess, big expressive eyes, neon circuit armor)
- **Differentiator**: Nous is minimalist/warm; BrierStudios is maximalist/cool with Norse depth

## Assets Generated
- 6 Lilith anime images: `/mnt/d/Proyectos/lilith_anime_output/`
- Optimized web images: `/mnt/d/Proyectos/brierstudios-site/assets/lilith/`
  - 6 hero JPEGs (600x800, ~100KB each)
  - 6 thumb JPEGs (300x400, ~30KB each)
- Model used: PD_v1.safetensors (SDXL) + eir_niflheimr LoRA v2_best
- ComfyUI workflow: `/mnt/d/Proyectos/lilith_anime_gen.json`
- Identity docs: LILITH_IDENTITY.md v2.0, LILITH_ARTIST_BRIEF.md v2.0

## Implementation Notes (v2.4)

### Image Optimization Pipeline
Pillow (PIL) conversion: RGBA PNG → RGB JPEG with dark bg composite:
```python
from PIL import Image
img = Image.open(src)  # RGBA PNG
bg = Image.new('RGB', img.size, (6, 8, 16))  # Match site --void: #060810
bg.paste(img, mask=img.split()[3])  # Composite
img_rgb = bg
img_hero = img_rgb.resize((600, 800), Image.LANCZOS)
img_hero.save(hero_path, "JPEG", quality=85, optimize=True)
img_thumb = img_rgb.resize((300, 400), Image.LANCZOS)
img_thumb.save(thumb_path, "JPEG", quality=80, optimize=True)
```
Result: 6 PNGs at ~35MB total → 12 JPEGs at ~811KB total.

### Gallery Click-to-Swap Hero
HTML: 6 `.lilith-variant` cards in a 3x2 grid, each with `data-variant` attribute.
JS: On click, fade hero image out (opacity 0, scale 0.95), swap `src`, fade back in.
CSS: `.lilith-hero-img` has `transition: opacity 0.3s, transform 0.3s`.
Active variant gets `.lilith-variant.active` with cyan glow border.