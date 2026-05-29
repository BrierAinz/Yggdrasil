# YggdrasilStudio Frontend — Nordic Dark Fantasy Theme System

## Overview

YggdrasilStudio uses a comprehensive Nordic dark fantasy theme built on TailwindCSS custom colors, CSS component classes, and Cinzel typography. The theme system lives in:

- `frontend/tailwind.config.js` — Custom colors, fonts, animations, shadows
- `frontend/src/index.css` — TailwindCSS layers with Nordic component classes + manual `.font-cinzel` fallback
- `frontend/index.html` — Google Fonts import (Cinzel)
- `frontend/src/components/*.jsx` — `font-cinzel` applied to headings

## Color Palette

| Name | Hex | Purpose |
|------|-----|---------|
| midnight | `#0a0e1a` | Primary background (deep space) |
| midnight-100 | `#151a28` | Card backgrounds, inputs |
| midnight-200 | `#111827` | Sidebar, elevated surfaces |
| gold | `#c9a84c` | Primary accent (rune gold) |
| gold-300 | `#f0c94a` | Bright gold hover |
| gold-500 | `#c9a84c` | Default gold |
| bifrost | `#7dd3fc` | Secondary accent (ice blue) |
| blood | `#8b0000` | Error/destructive |
| deep-purple | `#2d1b4e` | Accent background |
| yggdrasil | `#22c55e` | Success/nature |
| card | `#1a1a2e` | Card surface |
| card-border | `#2a2a3e` | Borders |
| rune | `#c9a84c` | Rune decorations |
| rune-dim | `#8b7634` | Dimmed rune text |
| rune-glow | `#f0d878` | Glowing rune text |

## Font Integration (Critical)

### Integration Pattern

Three parts are ALL required for Cinzel to work:

**1. HTML import** (in `index.html` `<head>`):
```html
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Cinzel:wght@400;600;700;900&display=swap" rel="stylesheet">
```

**2. Tailwind config** (in `tailwind.config.js`):
```js
fontFamily: {
  sans: ['Inter', 'system-ui', 'sans-serif'],
  mono: ['JetBrains Mono', 'Fira Code', 'monospace'],
  cinzel: ['Cinzel', 'serif'],
},
```

**3. Manual CSS fallback** (in `index.css`, OUTSIDE `@layer`):
```css
.font-cinzel {
  font-family: 'Cinzel', serif !important;
}
```

Apply via `font-cinzel` class on headings:
```jsx
<h1 className="font-cinzel text-gold-500 text-xl">Yggdrasil</h1>
<h2 className="font-cinzel text-gold-500">Recent Creations</h2>
```

### Pitfalls

1. **Tailwind v3 JIT class purging**: When you add a new `fontFamily` entry to `tailwind.config.js` AFTER the dev server has started, Tailwind JIT will NOT generate the `font-{name}` utility class — even though `font-cinzel` appears in your JSX source files. The class simply won't exist in the CSS output. **Always add a manual CSS rule in `index.css` as a safety net** (part 3 above).

2. **Vite HMR won't propagate config changes**: After modifying `tailwind.config.js` to add new fontFamily entries, Vite's HMR will log `page reload tailwind.config.js` but the new utility classes won't be generated. **You MUST** `rm -rf node_modules/.vite` and do a full dev server restart. A simple page reload is not enough.

3. **Verifying font application**: Check via browser console:
   ```js
   getComputedStyle(document.querySelector('h1')).fontFamily
   // Should show: "Cinzel, serif" — if it shows "Inter, system-ui, sans-serif", the class isn't applied
   ```
   Also check if the class exists in rendered HTML:
   ```js
   document.querySelector('h1')?.className
   // Should include "font-cinzel"
   ```
   And verify the CSS rule exists:
   ```js
   let found = false;
   for (const sheet of document.styleSheets) {
     try { for (const rule of sheet.cssRules) {
       if (rule.cssText?.includes('font-cinzel')) { found = true; break; }
     }} catch(e) {}
   }
   found; // true = CSS rule exists
   ```

## CSS Component Classes

### Buttons
- `.btn-nordic` — Gold gradient button with hover glow and lift effect
- `.btn-ghost-gold` — Transparent button with gold border, gold text on hover

### Cards
- `.card-frost` — Frosted glass card with backdrop blur and ice/purple gradient overlay
- `.card-rune` — Card with animated gradient border (gold → bifrost → purple → gold)

### Dividers
- `.rune-divider` — Horizontal line with gold-to-ice gradient fade
- `.rune-divider-ornate` — Divider with centered rune character and gradient lines

### Inputs
- `.input-nordic` — Dark input with bifrost blue focus ring
- `.select-nordic` — Custom select with gold chevron dropdown icon

### Typography
- `.heading-runic` — Gold heading with text-shadow glow
- `.heading-runic-lg` — Larger heading with triple glow (5px, 15px, 30px)

### Progress
- `.progress-runic` — Progress bar track with animated rune character
- `.runefill-bar` — Gradient fill (blood red → gold → ice blue) with gold glow shadow

### Backgrounds
- `.bg-aurora` — Animated aurora gradient (5s infinite)
- `.bg-yggdrasil-sidebar` — Vertical green-to-gold-to-dark gradient
- `.bg-starfield` — Dot pattern of ice-blue and gold particles

### Utilities
- `.text-shadow-gold` / `.text-shadow-gold-lg` — Gold glow text shadows
- `.text-shadow-bifrost` — Ice blue text shadow
- `.text-shadow-blood` — Red text shadow
- `.glow-gold` / `.glow-bifrost` / `.glow-yggdrasil` / `.glow-blood` — Box shadow utilities

## Animations

| Animation | Duration | Effect |
|-----------|----------|--------|
| `aurora` | 15s infinite | Background position shift for aurora gradient |
| `glow-pulse` | 2s infinite | Gold box-shadow pulse (5px → 15px) |
| `rune-flicker` | 3s infinite | Opacity flicker (1 → 0.7 → 0.9) |
| `frost-shimmer` | 4s infinite | Background position sweep (shimmer effect) |
| `rune-glow` | 2.5s infinite | Text-shadow pulse (gold glow) |
| `rune-dim` | 4s infinite | Opacity cycle (0.4 → 0.8) |
| `tree-sway` | 8s infinite | ScaleX micro-animation (1 → 1.02) |
| `slide-in-left` | 0.3s ease-out | Transform X + opacity entrance |
| `slide-in-right` | 0.3s ease-out | Transform X + opacity entrance |
| `fade-in` | 0.3s ease-out | Opacity entrance |
| `scale-in` | 0.2s ease-out | Scale + opacity entrance |

## Nordic Character Presets (v2 — with runes)

Quick character buttons in PromptBuilder, each with a rune icon:
| Character | Rune | Description |
|-----------|------|-------------|
| Eir Niflheimr | ᛁ | Healer, serene frost mage |
| Thor Stormbringer | ᚦ | Thunder warrior |
| Freya Vanadis | ᚠ | Beauty and war |
| Loki Trickster | ᚨ | Chaos and illusion |
| Brynhildr Shieldmaiden | ᛉ | Valkyrie shield warrior |
| Nidhogg Wyrm | ᛏ | Dragon of destruction |

Character buttons use native HTML `title` attributes for tooltips on hover. **Do NOT use Radix `@radix-ui/react-tooltip`** for simple tooltips — it crashes the entire React app when `Tooltip.Provider` is missing or misconfigured, producing only a white screen with no error boundary. Use native `title="description text"` instead. After applying a preset, prompt textarea auto-focuses.

## Navigation Runes

| Nav Item | Rune |
|----------|------|
| Invoke | ᛟ (Othala) |
| Gallery | ᛏ (Tiwaz) |
| Warriors | ᛦ (Ehwaz variant) |
| Runes of the Past | ᚠ (Fehu) |
| Forge | ᚦ (Thurisaz) |

## QoL Features (v2)

### Keyboard Shortcuts
| Shortcut | Action |
|----------|--------|
| Ctrl+Enter | Invoke generation |
| Ctrl+Shift+R | Randomize seed |
| Ctrl+Shift+X | Clear prompt |
| Escape | Close modal |

Hint text shown below prompt: "Ctrl+Enter to invoke · Ctrl+Shift+R randomize · Ctrl+Shift+X clear"

### Drag & Drop
Prompt area accepts dropped image files. Overlay shows "ᛟ Drop image for img2img" with Framer Motion animation. Drops automatically switch to `img2img` workflow and set `sourceImage` as base64.

### Toast Notifications
Simple toast system with custom React state + Framer Motion (`Toaster.jsx` component):
- Generation queued: "ᛟ The runes hear your call..."
- Generation completed: "ᛟ Your vision has been forged!"
- Generation failed: "ᛦ The runes failed to respond"
- Auto-dismiss after 3-4 seconds with slide-in/slide-out animation
- Styles defined in `index.css` as `.toast-nordic` and `.toast-item`

### Radix Tooltip Crash (DO NOT RE-INTRODUCE)
**TL;DR**: Never use `@radix-ui/react-tooltip` for simple tooltip use cases in YggdrasilStudio. Use native `title` attributes instead.

The Radix Tooltip component crashed the entire React app (white screen, `<div id="root"></div>` empty) when `Tooltip.Provider` was missing from the component tree or misconfigured. The error propagated up to the root and prevented ANY rendering. Debugging was difficult because:
1. The error overlay didn't show (React 18 error boundaries don't always surface in dev)
2. `document.querySelector('h1')` returned null (nothing rendered)
3. The fix was simple: replace `import * as Tooltip from '@radix-ui/react-tooltip'` + `Tooltip.Root/Trigger/Content` with `title="description"` on each button

If tooltips more advanced than native `title` are needed in the future, use a simpler animation-based approach (Framer Motion `AnimatePresence` + `onMouseEnter/Leave`) rather than Radix UI's component tree.

### Default Checkpoint
Auto-selects first real checkpoint (Juggernaut XL v9) instead of placeholder "Default Checkpoint" on initial load.

## API Integration Notes

- **Generate endpoint**: `POST /api/generate` — accepts `workflow_type`, `positive_prompt`, `checkpoint`, `width`, `height`, `steps`, `cfg_scale`, `sampler`, `scheduler`, `seed`
- **Status endpoint**: `GET /api/generate/{prompt_id}/status` — returns `"queued"`, `"running"`, `"completed"`, or `"failed"` (plain English, NOT Nordic-themed)
- **Image proxy**: `GET /api/images/{filename}` — uses httpx streaming response (NOT RedirectResponse which causes 500 errors with query params)
- **WebSocket**: `ws://host:8080/ws` — real-time generation progress updates
- **Invoke button click**: The "Invoke Yggdrasil" button uses `motion.button` (Framer Motion) with `whileHover`/`whileTap` gestures. Automated browser clicks (headless/playwright) may NOT fire the React onClick handler — this is a Framer Motion gesture layer issue, not a bug. Use `Ctrl+Enter` or direct API calls to test generation. Handler chain: PromptBuilder.handleGenerate → onGenerate → Studio.handleGenerate → useGeneration.submit → POST /api/generate.

### Health Check Integration

The sidebar (`Layout.jsx`) fetches `/health` to display service status (green/gray dots for ComfyUI/LokArni online/offline).

**Backend response structure** (`GET /health`):
```json
{
  "status": "partially_rooted",
  "services": {
    "comfyui": { "url": "http://localhost:8188", "online": true },
    "lokarni": { "url": "http://localhost:8000", "online": false }
  }
}
```

**Frontend correct parsing path**: `info?.services?.comfyui?.online` and `info?.services?.lokarni?.online`. A common bug is accessing `info?.comfyui` directly (missing the `services` nesting), which makes services always appear offline.

**Vite proxy requirement**: The frontend calls `fetch('/health')` which must be proxied to the backend. In `vite.config.js`, ALL API paths must have proxy entries — not just `/api`. Current required proxy routes:
```js
proxy: {
  '/api': { target: 'http://localhost:8080', changeOrigin: true },
  '/health': { target: 'http://localhost:8080', changeOrigin: true },
  '/ws': { target: 'ws://localhost:8080', ws: true },
}
```
If `/health` is missing from the proxy config, the fetch returns a 404 or Vite's SPA fallback, making all services appear offline. Always audit `fetch()` calls in ALL frontend components when adding new proxy routes.