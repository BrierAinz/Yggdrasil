# Dark Fantasy Nordic Tech — Design System (Frost Edition)

## Overview

This is the visual identity for BrierStudios and the Yggdrasil ecosystem. The aesthetic fuses **dark fantasy**, **Norse mythology**, and **modern tech** — with a **cold/frost palette** (ice blue, aurora violet) as of the v2 redesign. The original warm gold palette has been retired.

## Palette

| Token | Hex | Usage |
|---|---|---|
| --void | #060810 | Page background (deep cold black) |
| --void-lighter | #0c1018 | Section alternate bg |
| --void-card | #101620 | Card backgrounds |
| --void-border | #182030 | Borders, dividers |
| --ice | #38bdf8 | Primary accent (links, glow, headings) |
| --ice-bright | #7dd3fc | Bright ice (hover states, highlights) |
| --ice-deep | #0284c7 | Deep ice (button gradients) |
| --ice-glow | rgba(56,189,248,0.12) | Subtle ice glow backgrounds |
| --ice-glow-strong | rgba(56,189,248,0.25) | Hover glow, focus ring |
| --ice-dim | rgba(56,189,248,0.4) | Dim borders, inactive states |
| --frost | #bae6fd | Frost white (hero text glow) |
| --frost-dim | rgba(186,230,253,0.6) | Dim frost text |
| --aurora | #818cf8 | Secondary accent (tech tags, section accents) |
| --aurora-dim | rgba(129,140,248,0.4) | Dim aurora |
| --crystal | #e0f2fe | Crystal white (brightest text) |
| --text | #cbd5e1 | Body text |
| --text-dim | #64748b | Secondary/dim text |
| --text-bright | #f1f5f9 | Bright text, headings |

## Typography

| Role | Font | Weights | Sizes |
|---|---|---|---|
| Headings | Cinzel (serif) | 600-900 | clamp(2rem, 4vw, 2.75rem) |
| Body | Inter (sans) | 300-600 | 0.9rem-1.15rem |
| Code/Tech | JetBrains Mono (mono) | 300-500 | 0.65rem-0.9rem |

## Key Design Elements

1. **Loading Screen**: Animated rune ᛒ (Berkano) with pulse glow, progress bar with ice sweep animation. Auto-dismisses after page load (3s fallback).
2. **Mouse Glow**: Fixed radial gradient that follows cursor with smooth lerp (`0.08` easing). Creates subtle ice-blue spotlight effect. Never blocks pointer events.
3. **Floating Rune Canvas**: 35+ Elder Futhark characters drift upward on `<canvas>`, with ice-blue glow (`rgba(56,189,248,opacity)`). Runes gently repel from mouse position (150px radius). Respects `prefers-reduced-motion`.
4. **Frost Trail Particles**: Small ice-blue dots spawn near cursor, drift upward with slight randomness, fade out over 40-80 frames. Maximum 50 concurrent trails.
5. **Runic Circle SVG**: 8 rune characters on concentric circles, spinning at 60s/revolution. Circles pulse independently. Characters flicker with glow.
6. **Card Hover Glow**: Radial gradient follows mouse position within card using CSS custom properties `--mouse-x`/`--mouse-y`. Combined with translateY and ice-blue box-shadow.
7. **Scroll Animations**: IntersectionObserver with `.fade-in`, `.fade-in-left`, `.fade-in-right` classes (opacity 0 → 1, translate).
8. **Navbar Frosted Glass**: Transparent at top, transitions to `rgba(6,8,16,0.85)` with `backdrop-filter: blur(20px)` on scroll.
9. **Section Dividers**: Horizontal gradient lines `linear-gradient(90deg, transparent, --ice-dim, transparent)` with box-shadow glow.
10. **Footer Rune Shuffle**: Random rune character flickers briefly every 300ms, then restores to original.
11. **Contact Form**: Ice glow on focus (`box-shadow: 0 0 20px var(--ice-glow-strong)`), submit button with rune prefix and state animation.
12. **Parallax**: Rune circle translates with scroll at 0.15x rate.

## Animation Keyframes Reference

| Name | What | Duration |
|---|---|---|
| `rune-pulse` | Scale + opacity pulse for loading rune | 1.5s |
| `loading-slide` | Ice gradient sweep for progress bar | 1.5s |
| `slow-spin` | 360° rotation for rune circle SVG | 60s |
| `float` | Gentle vertical bob (+/-15px) | 6s |
| `ring-pulse` | Opacity pulse for SVG circle strokes | 2.5-5s |
| `rune-flicker` | Opacity + drop-shadow flicker for chars | 3-4s |
| `scroll-bounce` | Vertical bounce for scroll indicator | 2s |
| `rune-shimmer` | Opacity pulse for footer rune strip | 4s |

## User Preference: Cold + Movement

The user explicitly prefers **colder palettes** (ice/frost over gold/warm) and **more animation and movement**. When designing for this brand:
- Always lean frost/ice blue, never gold
- Add at least 2-3 dynamic elements (particles, mouse tracking, parallax, hover effects)
- Canvas-based particles and cursor effects are expected, not extras
- Loading screens with animated runes are on-brand

## Logo Remastering

The original logo (white + red on dark) was remastered to ice palette using PIL/numpy:
- Red pixels → ice blue (#38bdf8 gradient mapped)
- White pixels → frost (#bae6fd with brightness preservation)
- Dark pixels → void (#060810)
- Fully transparent pixels stay transparent

Technique: Create boolean masks for each color channel range, then use normalized channel values as intensity multipliers for the target palette.

## Elder Futhark Rune Reference

- ᚠ Fehu (wealth) — Footer decoration
- ᚢ Uruz (strength)
- ᚦ Thurisaz (giant/thorn) — Value: Thruth
- ᚨ Ansuz (god/inspiration) — About section, project card
- ᚱ Raidho (journey)
- ᚲ Kenaz (torch/knowledge)
- ᚷ Gebo (gift) — Contact: GitHub
- ᚹ Wunjo (joy) — Value: Wyrd
- ᚺ Hagalaz (hail) — Hero rune circle
- ᚾ Nauthiz (need)
- ᛁ Isa (ice)
- ᛃ Jera (harvest)
- ᛇ Eihwaz (yew/world tree) — Yggdrasil project
- ᛈ Pertho (fate/mystery) — Projects section
- ᛉ Algiz (protection)
- ᛊ Sowilo (sun/victory) — Contact: Ecosystem
- ᛏ Tiwaz (victory/justice) — Form success
- ᛒ Berkano (birch/new beginnings) — Logo rune
- ᛖ Ehwaz (horse/movement) — Ehyra project
- ᛗ Mannaz (human) — Value: Manna, Contact section
- ᛚ Laguz (water/flow) — Lilith project
- ᛜ Ingwaz (fertility/new)
- ᛞ Dagaz (dawn/breakthrough)
- ᛟ Othala (heritage/home)

## Responsive Breakpoints

- `900px`: Stack about grid, projects grid single column, contact grid single column, hide rune divider
- `640px`: Hamburger mobile menu (full-screen overlay), smaller rune circle, stacked hero CTA

## Cloudflare Pages Deployment

This site is designed for static deployment on Cloudflare Pages:
1. `wrangler pages deploy ./site-dir --project-name=brierstudios`
2. Add custom domain in Pages dashboard (auto-configures DNS + SSL)
3. No build step needed — plain HTML/CSS/JS