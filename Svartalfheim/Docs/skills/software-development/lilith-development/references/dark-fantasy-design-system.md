# Dark Fantasy / Norse / Lovecraftian Design System

Used in: Lilith Dashboard (`Dashboard/frontend/`) and Yggdrasil Website (`website/`).

## Color Palette (CSS Variables)

### Dashboard (Lilith)
```css
--bg-primary: #050510      /* The Void — deepest black-purple */
--bg-secondary: #0f0a14    /* Subtle purple undertone */
--bg-tertiary: #1a0a1e     /* Elevated panels */
--bg-pane: #0c0c16         /* Pane backgrounds */
--bg-input: #0e0a16        /* Input fields */

--accent-red: #ff3366       /* Blood — active, danger, user messages */
--accent-green: #00ff88     /* Necrotic green — success, terminal */
--accent-yellow: #ffcc00    /* Gold — warnings, connecting */
--accent-blue: #3366ff      /* Arcane blue — secondary accent */
--accent-magenta: #ff00ff  /* Eldritch magenta — memory, typing circle */
--accent-cyan: #00eeff     /* Spectral cyan — system info */
--accent-purple: #aa55ff   /* Mystical purple — borders, decorations */

--text-primary: #d8d0e8    /* Main text */
--text-secondary: #8878aa  /* Dimmed text */
--text-dim: #5a4a6e        /* Very dim */
--text-bright: #f0e8ff     /* Headlines */

--border: #2a1a3e          /* Default borders */
--border-active: #ff3366   /* Active pane border */
--border-focus: #aa55ff80  /* Input focus border */
```

### Website (Yggdrasil)
```css
--bg-primary: #0a0a0f      /* Void black */
--rune-gold: #C7A44A       /* Rune gold — primary accent */
--eldritch-purple: #aa55ff  /* Deep purple */
--necrotic-green: #00ff88   /* Success green */
--blood: #ff3366            /* Blood red */
```

## Typography
- **Display:** Cinzel Decorative (headings, titles)
- **Mono:** JetBrains Mono (code, terminal, pane labels)
- **Sans:** Inter (body text, UI elements)

## Rune System
Primary runes for decoration: ᛭ ᚺ ᛏ ᚱ ᚹ ᛉ ᛊ ᛒ ᛖ ᛗ ᛚ ᛜ ᛞ ᛟ ᚠ ᚢ ᚦ ᚨ ᚲ ᚷ ᛁ ᛃ ᛈ ᛇ

Eldritch symbols for particles: ⌬ ⍟ ⎔ ⎈ ⏣ ◈ ◇ △ ▽ ☽ ☾ ⊛ ⊕ ⊗

## Key Visual Effects

### Particles (Canvas)
- 35-55 rune/eldritch characters floating upward
- Horizontal drift + slow rotation
- Mouse proximity → particles glow brighter & move away
- 3-layer parallax speeds based on scroll position
- Occasional golden "shooting rune" streaks

### Glitch Effect
- Periodic (every 8-20s) title text corruption
- Character substitution with rune symbols before recovery
- CSS via `.glitch` / `.glitching` class toggling
- Keyframes: `glitch-text` with skewX + text-shadow color shifts

### Summoning Circle (Typing Indicator)
- 3 concentric rotating rings
- 6 orbiting rune characters
- Label "Communing" below
- Counter-rotating inner dashed ring

### Vortex / Fog
- 3 rotating cosmic gradient rings (120s, 80s, 50s cycles)
- Drifting fog layers with gradient orbs
- Body background: radial-gradient layers + noise texture SVG overlay

### Chat Messages
- **User (blood-drip):** Right-aligned, red left border, gradient `#1a1028 → #120a20`
- **Assistant (essence-rise):** Left-aligned, purple left border, purple mist glow, radial overlay with pulse animation

### Pane Active State
- Border shifts to `--accent-red`
- Breathing glow animation `pane-breathe`
- Corner rune characters (᛭) become visible
- "Power surge" random border flash events

### Modal
- Animated gradient border shimmer
- `backdrop-filter: blur(4px)` overlay
- Scale-in entrance animation

## Animation Catalog
| Animation | Duration | Usage |
|-----------|----------|-------|
| `rune-drift` | 25-45s | CSS floating rune particles |
| `pane-breathe` | 4s | Active pane glow |
| `pulse-glow` | 3s | Logo/connected status |
| `pulse-distress` | 1.5s | Disconnected status |
| `glitch-text` | 0.3s | Title distortion |
| `msg-appear` | 0.4s | Chat message entrance |
| `mem-appear` | 0.3s | Memory item slide-in |
| `circle-rotate` | 3-6s | Typing indicator rings |
| `candlelight` | 3s | Pane header flicker |
| `input-rune-glow` | 2s | Focused input glow |
| `elder-glow` | 4s | Logo pulsing ring |
| `mist-pulse` | 4s | Assistant message overlay |

## Frontend File Sizes (post mega-overhaul)
- `style.css`: ~2000 lines (full CSS)
- `app.js`: ~680 lines (full JS)
- `index.html`: ~200 lines (structure)

## Key CSS Patterns
- Use `@property --angle` for animated rotating conic-gradient borders
- Gradient panic: `linear-gradient(180deg, ...)` for vertical depth, `linear-gradient(135deg, ...)` for cards
- Glow shadows: always dual-layer (`0 0 Xpx color40, 0 0 Ypx color20`) for depth
- `::before`/`::after` pseudo-elements for scanlines, top-line decorations, corner runes
- `@media (hover: hover)` guards for interactive hover effects (skip on touch)

## Key JS Patterns
- WebSocket connection with exponential backoff reconnect
- Canvas particle system with `requestAnimationFrame` loop
- DOM-spawned cursor trail dots that auto-remove after animation
- MutationObserver for status class changes (connection animations)
- IntersectionObserver for scroll reveal animations
- Debounced search for memory panel (500ms)

## Important: Element IDs (Must Preserve)
- `app`, `header`, `title-lilith`, `connection-status`, `status-text`
- `pane-chat`, `pane-terminal`, `pane-system`, `pane-memory`
- `chat-messages`, `chat-input`, `chat-send`, `typing-indicator`
- `terminal-output`, `terminal-input`
- `system-info`, `sys-model`, `sys-memory`, `sys-swarm`, `sys-mcp`, `sys-uptime`, `sys-clients`
- `memory-search-input`, `memory-results`
- `settings-modal`, `setting-ws-url`, `setting-theme`, `setting-font-size`
- `particle-canvas`, `rune-particles`
- `main-content` (layout grid container)
- `btn-layout`, `btn-settings`

## Important: Global Functions (Must Preserve)
- `toggleLayout()`, `toggleSettings()`, `sendChat()`
- `connect()`, `send()`, `addChatMessage()`, `addTerminalLine()`
- `updateSystemStatus()`, `updateSwarmStatus()`, `updateMcpStatus()`
- `searchMemory()`, `updateMemoryResults()`
- `init()`, `initParticleCanvas()`, `spawnCSSRunes()`, `initTitleGlitch()`