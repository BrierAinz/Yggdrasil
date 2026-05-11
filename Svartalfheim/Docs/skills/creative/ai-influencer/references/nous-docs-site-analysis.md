# Nous Research Docs Site — Detailed Analysis (May 2026)

Research for building docs.brierstudios.com inspired by Nous Research's approach.

## Tech Stack

- **Docusaurus v3.9.2** — confirmed via `meta generator` tag
- **Hosted on GitHub Pages** (404 pages show GH Pages error)
- **Main site** (nousresearch.com): WordPress + Elementor 3.25.6
- **Hermes landing** (hermes-agent.nousresearch.com): Next.js on Vercel

## Visual Design

### Docs Site (hermes-agent.nousresearch.com/docs)

**Dual theme** (light/dark) with system preference detection + manual toggle:

| Element | Light Mode | Dark Mode |
|---------|-----------|-----------|
| Background | `#fff` white | `#242526` dark surface |
| Text | `#1c1e21` | `#e8e4dc` warm cream |
| Code bg | `#f6f7f8` off-white | `rgba(255,255,255,0.1)` |
| Accent/Links | `#8b6508` gold | `gold` |
| Primary color | Gold/amber `#8b6508` | Gold |

**Fonts:**
- Body: Inter (weight 600 for headings, 400 for body)
- Code: JetBrains Mono / Fira Code / Cascadia Code (font stack priority)
- H1: 2rem, H2: 1.5rem, H3: 1.25rem, line-height 1.25

**Code blocks:**
- Rounded corners (0.4rem border-radius)
- Copy-to-clipboard button
- Word-wrap toggle
- 14.4px font size
- Syntax highlighting via Prism

### Hermes Landing (hermes-agent.nousresearch.com)

- **Dark only** — bg `#041c1c` (very dark teal), text `#ffe6cb` (warm gold/cream)
- **Custom font:** "mondwestFont" (serif/display, editorial feel)
- **Also uses:** Geist Sans + Geist Mono
- **Layout:** Centered single-page hero with install code snippets
- **Framework:** Next.js with Turbopack

### Main Site (nousresearch.com)

- **Light only** — white bg, black text
- **Font:** Times New Roman (serif) — bold editorial choice
- **Also uses:** Courier Prime + Geist Sans + Geist Mono
- **Framework:** WordPress + Elementor
- **Decorative:** "SEED:" and "OUTPUT:" callouts referencing AI generation

## Navigation Structure (Docs)

**Top navbar** (fixed):
- Logo "Hermes Agent" | Docs | Skills | Language switcher (EN / 简体中文) | Home | GitHub | Discord | Dark/Light toggle | Search (Ctrl+K)

**Left sidebar** (collapsible, 300px):
- User Stories & Use Cases
- Getting Started → Quickstart, Installation, Android/Termux, Nix & NixOS, Updating & Uninstalling, Learning Path
- Using Hermes → CLI Interface, TUI, Windows, Configuration, Models, Sessions, Profiles, Docker, Security, Checkpoints
- Features → Overview, Tool Gateway, Core, Automation, Media & Web, Management, Advanced, Skills
- Messaging Platforms
- Integrations
- Guides & Tutorials
- Developer Guide
- Reference

**Content area:** Centered, max-width 1140px (XL: 1320px)

**Footer per page:** "Edit this page" (GitHub link), last-updated timestamp

## Special Features

- **Search:** Algolia-powered or built-in, Ctrl+K shortcut
- **i18n:** English + Simplified Chinese
- **Admonitions:** Docusaurus standard (note, tip, warning, danger, info)
- **Badges:** Custom labels (e.g., "EARLY BETA")
- **YouTube embeds:** Iframe-based
- **Emoji-rich headers:** 🚀, 📖, 🗺️, ⚙️, 💬, etc.

## BrierStudios Adaptation Plan

For docs.brierstudios.com, adapt Nous's approach with our brand:

### What to Keep from Nous
- Docusaurus v3 as framework (mature, well-maintained)
- Sidebar + content + TOC layout
- Dark/light theme toggle
- Search (Ctrl+K)
- Code blocks with copy buttons
- "Edit this page" on GitHub
- Breadcrumbs + pagination

### What to Change for BrierStudios
- **Colors:** Our neon palette (cyan `#38bdf8`, magenta `#d946ef`, abyss `#0f172a`) instead of gold/amber
- **Dark mode primary:** Cyan instead of gold
- **Fonts:** Inter (body) + JetBrains Mono (code) ✅ same, but add Cinzel for headings (Norse runic feel)
- **Content structure:** 
  - 🏠 Inicio — Yggdrasil ecosystem overview
  - 🛠 Yggdrasil CLI — Installation, commands, 9 realms
  - 🎨 Lilith v2.0 — Identity, art, palette, variants
  - 📐 Arquitectura — 9 realms, conventions, REGLAS_YGGDRASIL
  - 🤖 Agentes IA — Bots, personality, config
  - 🎨 LoRA Training — Ehyra guide, Z-Image, PixAI
- **Custom:** Norse rune decorative elements, animated transitions, neon glow effects on active sidebar items
- **Deploy:** Cloudflare Pages (not GH Pages) — already set up for main site

### Docusaurus Config for BrierStudios

```js
// docusaurus.config.js key customizations
const config = {
  title: 'BrierStudios Docs',
  tagline: 'Documentation for the Yggdrasil ecosystem',
  url: 'https://docs.brierstudios.com',
  baseUrl: '/',
  themes: ['@docusaurus/theme-classic'],
  presets: [
    [
      'classic',
      {
        docs: {
          sidebarPath: './sidebars.js',
          editUrl: 'https://github.com/BrierAinz/brierstudios-docs/tree/main/',
        },
      },
    ],
  ],
  themeConfig: {
    colorMode: {
      defaultMode: 'dark',
      disableSwitch: false,
      respectPrefersColorScheme: true,
    },
    navbar: {
      title: 'BrierStudios',
      logo: { alt: 'BrierStudios', src: 'img/logo.svg' },
      items: [
        { label: 'Docs', to: '/docs/intro' },
        { label: 'CLI Reference', to: '/docs/cli' },
        { label: 'GitHub', href: 'https://github.com/BrierAinz' },
      ],
    },
    prism: {
      theme: require('prism-react-renderer/themes/dracula'),
    },
  },
};
```

### CSS Custom Properties (override Docusaurus defaults)

```css
:root {
  --ifm-color-primary: #38bdf8;          /* cyan */
  --ifm-color-primary-dark: #0ea5e9;
  --ifm-color-primary-darker: #0284c7;
  --ifm-color-primary-light: #7dd3fc;    /* aurora */
  --ifm-color-primary-lighter: #bae6fd;
  --ifm-color-secondary: #d946ef;        /* magenta accent */
  --ifm-background-color: #0f172a;        /* abyss */
  --ifm-navbar-background-color: #060810; /* void */
  --ifm-code-font-size: 90%;
  --ifm-font-family-base: 'Inter', system-ui, sans-serif;
  --ifm-font-family-monospace: 'JetBrains Mono', 'Fira Code', monospace;
}
```