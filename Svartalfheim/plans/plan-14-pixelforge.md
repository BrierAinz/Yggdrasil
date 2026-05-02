# PixelForge — Editor de Pixel Art en la Web

> **For Hermes:** Use subagent-driven-development skill to implement this plan task-by-task.

**Goal:** App web con paletas de NES/Game Boy/PICO-8, capas, animación de sprites, export a sprite sheets. Colaborativo en tiempo real opcional.

**Architecture:** Static web app → Canvas para editing → palette engine → layer system → animation timeline → export engine. Pure HTML/CSS/JS, sin framework.

**Tech Stack:** HTML5 Canvas, CSS Custom Properties, JavaScript ES Modules, WebSocket (optional real-time collab).

**Realm:** Alfheim/PixelForge/

---

## Task 1: Scaffold del proyecto

Files: `Alfheim/PixelForge/`, index.html, css/style.css, js/app.js. Pure static site, no build step.

**Commit:** `feat(pixelforge): scaffold project`

---

## Task 2: Canvas editor core

HTML5 Canvas con:
- Grid overlay (configurable: 8x8, 16x16, 32x32, 64x64)
- Pixel-perfect drawing (fill pixel on click/drag)
- Pencil, eraser, fill bucket, color picker, line tool
- Zoom in/out
- Undo/redo (history stack)

```javascript
class PixelCanvas {
    constructor(width, height, pixelSize) { ... }
    draw(x, y, color) { ... }
    erase(x, y) { ... }
    fill(startX, startY, color) { ... }  // flood fill
    undo() { ... }
    redo() { ... }
}
```

**Commit:** `feat(pixelforge): canvas pixel editor`

---

## Task 3: Palette engine

Paletas predefinidas:
- NES (54 colors)
- Game Boy (4 shades of green)
- PICO-8 (16 colors)
- Commodore 64 (16 colors)
- Custom palette editor

```javascript
const PALETTES = {
    nes: [...],
    gameboy: [...],
    pico8: [...],
    c64: [...],
};
```

**Commit:** `feat(pixelforge): palette engine with retro palettes`

---

## Task 4: Layer system

Capas con: opacity, visibility toggle, reorder, merge down. Cada capa tiene su propio pixel grid.

**Commit:** `feat(pixelforge): layer system`

---

## Task 5: Animation timeline

Frame-based animation:
- Agregar/duplicar/eliminar frames
- Onion skin (ver frame anterior semi-transparente)
- Preview animation
- FPS configurable (1-24)
- Loop modes: forward, ping-pong, once

**Commit:** `feat(pixelforge): animation timeline`

---

## Task 6: Export engine

Export formats:
- PNG (single sprite)
- Sprite sheet (horizontal, all frames in one row)
- Sprite sheet (grid, NxM)
- GIF animation
- JSON (raw pixel data)
- .chr (NES format, optional)

**Commit:** `feat(pixelforge): export engine`

---

## Task 7: UI/UX — Dark theme Yggdrasil

Dark theme con CSS custom properties. Sidebar para tools, panel derecho para paletas, bottom bar para animation timeline. Responsive.

**Commit:** `feat(pixelforge): Yggdrasil dark theme UI`

---

## Task 8: Keyboard shortcuts + accessibility

Shortcuts: B (brush), E (eraser), G (fill), Z (undo), Y (redo), +/- (zoom), Space+drag (pan). Focus-visible states, ARIA labels.

**Commit:** `feat(pixelforge): keyboard shortcuts and accessibility`

---

## Task 9: Optional real-time collaboration

WebSocket server (Python/FastAPI) para sync en tiempo real. Opcional — funciona sin él como static app.

**Commit:** `feat(pixelforge): optional real-time collab`
