# Elder Futhark Rune Icon System

## Overview

The BrierStudios docs site uses **Elder Futhark rune glyphs** instead of emojis for ALL icons, labels, and decorative elements. The user explicitly rejected emojis ("no quiero emojis Haz algo único"). Every Unicode emoji must be replaced with its corresponding rune + CSS glow class.

## Philosophy

- Emojis are generic and platform-dependent (render differently on Windows/Mac/Linux)
- Elder Futhark runes are Norse-themed, unique, and consistent across all platforms
- The `.ri` CSS system gives each rune a neon glow color matching its realm/semantic domain
- Hover produces an intensified glow + subtle scale animation

## Rune-to-Concept Mapping

### Nine Realms

| Glyph | Rune    | Concept             | Class            | Color   |
|-------|---------|---------------------|------------------|---------|
| ᛊ     | Sól     | Asgard / Power / Command | `.ri-asgard` | #38bdf8 (cyan) |
| ᛉ     | Algiz   | Vanaheim / Agent / AI    | `.ri-vanaheim` | #d946ef (magenta) |
| ᚦ     | Thurisaz| Alfheim / Creation / Design| `.ri-alfheim` | #7dd3fc (aurora) |
| ᚨ     | Ansuz   | Svartalfheim / Knowledge  | `.ri-svartalfheim` | #fbbf24 (gold) |
| ᛏ     | Tiwaz   | Muspelheim / Fire / Active| `.ri-muspelheim` | #ef4444 (red) |
| ᛁ     | Isa     | Niflheim / Ice / Resources| `.ri-niflheim` | #93c5fd (light blue) |
| ᚻ     | Hagall  | Helheim / Archive / Death | `.ri-helheim` | #c026d3 (purple) |
| ᛃ     | Jera    | Jotunheim / Cycle / Enterprise | `.ri-jotunheim` | #f97316 (orange) |
| ᛗ     | Mannaz  | Midgard / Humanity / Home | `.ri-midgard` | #22c55e (green) |

### Semantic Concepts

| Glyph | Rune    | Concept             | Class            | Color   |
|-------|---------|---------------------|------------------|---------|
| ᚠ     | Fehu    | Identity / Brand    | `.ri-identity` | #38bdf8 (cyan) |
| ᚲ     | Kenaz   | CLI / Insight / Craft | `.ri-cli` | #38bdf8 (cyan) |
| ᛋ     | Sowilo  | Search / Discovery  | `.ri-search` | #38bdf8 (cyan) |
| ᛞ     | Dagaz   | Release / Dawn       | `.ri-release` | #d946ef (magenta) |
| ᛜ     | Ingwaz  | Ecosystem / Growth   | `.ri-ecosystem` | #22c55e (green) |
| ᚹ     | Wunjo   | LoRA / Precision / Target | `.ri-lora` | #fbbf24 (gold) |
| ᛒ     | Berkano | Palette / Birth / Creation | `.ri-palette` | #7dd3fc (aurora) |
| ᛈ     | Pertho  | Variants / Mystery   | `.ri-variants` | #d946ef (magenta) |

### Emoji → Rune Replacements

| Emoji | Replacement | Context |
|-------|-------------|---------|
| ⚡ (lightning) | ᛊ Sól | Power, Asgard, energy |
| 🤖 (robot) | ᛉ Algiz | Agents, AI, guardians |
| 🎨 (art) | ᚦ Thurisaz | Design, Alfheim, creation |
| 📜 (scroll) | ᚨ Ansuz | Knowledge, docs |
| 🔥 (fire) | ᛏ Tiwaz | Active, Muspelheim |
| ❄️ (snowflake) | ᛁ Isa | Ice, resources, Niflheim |
| 💀 (skull) | ᚻ Hagall | Death, archive, Helheim |
| 🏔️ (mountain) | ᛃ Jera | Massive, enterprise, Jotunheim |
| 🏠 (house) | ᛗ Mannaz | Home, personal, Midgard |
| 🎯 (target) | ᚹ Wunjo | Precision, LoRA training |
| 🎭 (masks) | ᚠ Fehu | Identity, brand, Lilith |
| 🌳 (tree) | ᛜ Ingwaz | Ecosystem, growth |
| 🏗️ (construction) | ᚦ Thurisaz | Architecture, building |
| 📚 (books) | ᚨ Ansuz | Documentation, knowledge |
| 🔍 (magnifier) | ᛋ Sowilo | Search, discovery |
| 🚀 (rocket) | ᛞ Dagaz | Release, launch, new version |
| ✨ (sparkles) | ᛉ Algiz | Neon, magic, glam |
| 🧠 (brain) | ᛉ Algiz | Intelligence, agents |
| ✅ (check) | ᛏ Tiwaz | Yes, victory, approved |
| ❌ (cross) | ᚻ Hagall | No, denied, removed |
| 📖 (book) | ᚨ Ansuz | Reading, docs |
| 🌍 (globe) | ᛗ Mannaz | World, global |
| 🤝 (handshake) | ᛜ Ingwaz | Community, connection |
| 🗺️ (map) | ᚦ Thurisaz | Map, exploration |
| 🌐 (web) | ᛜ Ingwaz | Network, web |
| 📐 (ruler) | ᚦ Thurisaz | Design, measurement |
| 📱 (phone) | ᚠ Fehu | Device, mobile |
| 🌩️ (cloud-lightning) | ᛊ Sól | Storm, power |
| 📋 (clipboard) | ᚨ Ansuz | Records, list |
| 💡 (bulb) | ᚲ Kenaz | Insight, idea |
| 🎉 (party) | ᛞ Dagaz | Celebration, release |
| 𝕏 (X logo) | ᛋ Sowilo | Twitter/X social link |
| 📷 (camera) | ᚦ Thurisaz | Instagram, visual |

## Usage

### In Markdown/MDX

```html
<span class="ri ri-asgard">ᛊ</span> Asgard — Core Technology
<span class="ri ri-vanaheim">ᛉ</span> Vanaheim — AI Agents
```

### In React/TSX

```tsx
<span className="ri ri-cli">ᚲ</span> CLI Quick Start
<span className="ri ri-lora">ᚹ</span> LoRA Training
```

### In Navbar/Sidebar Labels

```typescript
label: 'ᚨ Docs'    // Ansuz — knowledge
label: 'ᚲ CLI'     // Kenaz — craft
label: 'ᛞ Blog'    // Dagaz — dawn/release
label: 'ᛋ X'       // Sowilo — search/social
```

### In Headings (auto-enhanced glow)

```markdown
# <span class="ri ri-asgard">ᛊ</span> The Nine Realms
```

Headings automatically get stronger glow via:
```css
h1 .ri, h2 .ri, h3 .ri {
  font-size: 1.3em;
  filter: drop-shadow(0 0 6px currentColor) drop-shadow(0 0 12px currentColor);
}
```

## CSS Implementation

The `.ri` system is defined in `src/css/custom.css`:

```css
.ri {
  display: inline-block;
  font-size: 1.15em;
  line-height: 1;
  vertical-align: middle;
  margin: 0 0.15em;
  filter: drop-shadow(0 0 4px currentColor);
  transition: filter 0.2s ease, transform 0.2s ease;
  font-family: 'Inter', sans-serif;
  font-weight: 700;
}

.ri:hover {
  filter: drop-shadow(0 0 8px currentColor) drop-shadow(0 0 16px currentColor);
  transform: scale(1.15);
}

.ri-asgard    { color: #38bdf8; }
.ri-vanaheim  { color: #d946ef; }
/* ... all realm + semantic classes ... */
```

## Batch Emoji Removal

To find remaining emojis in source files, scan for Unicode codepoints:

```python
import os
emoji_ranges = [(0x1F300, 0x1FAFF), (0x2600, 0x27BF), (0x2B50, 0x2B55)]

for root, dirs, files in os.walk('docs-brierstudios'):
    for f in files:
        if f.endswith(('.md', '.mdx', '.tsx', '.ts', '.css')):
            path = os.path.join(root, f)
            content = open(path, encoding='utf-8').read()
            for char in content:
                cp = ord(char)
                if any(lo <= cp <= hi for lo, hi in emoji_ranges):
                    print(f"{path}: {char} ({hex(cp)})")
                    break
```

## Design Principles

1. **One rune per concept** — each semantic domain (realm, action, category) maps to exactly one glyph
2. **Color-consistent** — the rune's `.ri-*` class color matches its realm/section theme
3. **Hover-interactive** — neon glow intensifies on hover with subtle scale
4. **Typography-bold** — `.ri` uses `font-weight: 700` for visual weight matching headings
5. **No emojis ever** — this is a hard constraint from the user, not a suggestion