# BrierStudios Site — Deployment Reference

## Live URLs
- **Production**: https://brierstudios.pages.dev
- **Custom domain**: https://brierstudios.com (CNAME proxied via Cloudflare)
- **Repo**: https://github.com/BrierAinz/brierstudios-site

## Cloudflare Setup
- **Zone ID**: `${CLOUDFLARE_ZONE_ID}`
- **Account ID**: `${CLOUDFLARE_ACCOUNT_ID}`
- **Project name**: `brierstudios`
- **DNS**: `brierstudios.com` → CNAME `brierstudios.pages.dev` (proxied), `www.brierstudios.com` → CNAME `brierstudios.pages.dev` (proxied)

## Design Specs
- **Theme**: Anime/cyberpunk neon Nordic — magenta+cyan dual neon, dark void backgrounds, flowing dynamic elements
- **Palette v2.3**: `--void: #060810`, `--frost: #7dd3fc`, `--ice: #38bdf8`, `--glacier: #0ea5e9`, `--silver: #cbd5e1`, `--aurora: #818cf8`, `--neon-magenta: #d946ef`, `--neon-magenta-glow: rgba(217,70,239,0.15)`, `--neon-magenta-dim: rgba(217,70,239,0.4)`
- **Fonts**: Cinzel (headings), JetBrains Mono (tech), Inter (body)
- **Effects**: Rune particles canvas, mouse glow, frost trails, loading screen, scroll animations, card hover glow, aurora gradients, neon magenta glow effects

## Deployment
- **Platform**: Cloudflare Pages (static HTML/CSS/JS)
- **Build command**: (none — static files)
- **Output directory**: `/` (root)
- **Deploy command**: `CLOUDFLARE_API_TOKEN=... CLOUDFLARE_ACCOUNT_ID=... npx wrangler@latest pages deploy . --project-name=brierstudios --branch=main`
- **Auto-deploy**: Push to GitHub `main` branch triggers rebuild

## Logo
- **Original**: `E:\Users\Game_\Downloads\a\x\Logotipo.png` (864x1152 RGBA, amber/gold shield crest)
- **Remastered**: `/tmp/brierstudios-site/logo.png` (frost/cold palette — reds→ice blue, whites→frost)
- **SVG version**: `/tmp/brierstudios-site/logo.svg` (Berkano rune + geometric frost design)

## Security Hardening (applied 2026-05-09)

- **HSTS**: Enabled via dashboard — `max-age=31536000; includeSubDomains; preload`
- **CSP**: `default-src 'self'; script-src 'self' static.cloudflareinsights.com; style-src 'self' fonts.googleapis.com 'unsafe-inline'; font-src fonts.gstatic.com; img-src 'self' data:; connect-src 'self'`
- **X-Frame-Options**: `DENY`
- **Permissions-Policy**: `camera=(), microphone=(), geolocation=()`
- **CORS wildcard removed**: `Access-Control-Allow-Origin: *` stripped via Transform Rule
- **Transform Ruleset ID**: `546a1190006b43299a4e67ac352ca968` (phase: `http_response_headers_transform`)
- **www domain**: Added as Pages custom domain, auto-redirects to apex
- **Rating improved**: C+ → B+

## Lilith Section (v2.3 — Anime/Neon)

Updated v2.2→v2.3 — Lilith section pivoted from dark fantasy to anime/cyberpunk neon aesthetic.

### Key v2.3 Changes
- **CSS variables added**: `--neon-magenta: #d946ef`, `--neon-magenta-glow: rgba(217,70,239,0.15)`, `--neon-magenta-dim: rgba(217,70,239,0.4)`
- **`.lilith-svg`**: max-width 280px (was 260px), triple drop-shadow (cyan 30px + magenta 12px + cyan 60px)
- **Helheim realm**: color changed from `#6b21a8` (purple) to `#c026d3` (dark magenta) — more neon
- **Realm descriptions**: updated to anime/neon language (holográfica, destellos neón, forja digital, etc.)
- **Cache bust**: v2.3 (all 3 locations + CSS comment + SVG img src)

### Structure
- **Section**: `#lilith` between About and Stats in index.html
- **Hero grid**: 2-col (280px SVG silhouette + lore text)
- **Manifesto**: Blockquote with runic border-left gradient
- **Traits**: 3 cards (Tejedora, Runas Vivas, Bifrost en el Pelo)
- **Realms**: 9 realm cards with CSS custom property `--realm-color`
- **Nav**: "LILITH" link added after "ABOUT"

### Key Files
- `/mnt/d/Proyectos/brierstudios-site/lilith-silhouette.svg` — Inline SVG with gradient defs, glow filters, animated eyes
- `/mnt/d/Proyectos/brierstudios-site/index.html` — Section HTML (~600 lines total)
- `/mnt/d/Proyectos/brierstudios-site/styles.css` — ~170 lines Lilith CSS + animations + responsive
- `/mnt/d/Proyectos/brierstudios-site/script.js` — `initLilithSection()` with staggered reveal, eye color change, parallax glow

### CSS Patterns
- `.realm-card { --realm-color: <hex> }` — per-realm accent color, used in border/glow/hover
- `.realm-card:hover { transform: translateY(-6px); }` + `.realm-icon { transform: scale(1.3); }`
- `.lilith-silhouette-wrap { animation: breathe 4s ease-in-out infinite; }` — pulse glow
- `.lilith-svg { animation: lilith-float 6s ease-in-out infinite; }` — vertical float
- `.lilith-eye { animation: eye-pulse 2.5s ease-in-out infinite; }` — pulsating glow
- Responsive: 900px (1-col hero, 3-col realms), 640px (2-col realms, compact traits)

### JS Patterns
- `initLilithSection()`: IntersectionObserver with stagger (100ms delay per card index) for realm cards
- Realm card hover → changes `.lilith-eye` fill to `--realm-color`; mouseleave → resets to `#38bdf8`
- Parallax glow: mousemove on section updates `.lilith-silhouette-glow` background radial-gradient position

### Interactive Scroll Reveal Classes
- `.fade-in-left` / `.fade-in-right` — horizontal reveal with CSS transition, triggered by `.visible`
- `.realm-card` — starts `opacity: 0; transform: translateY(30px)`, reveals to `opacity: 1; translateY(0)`

### Cache Busting
- Version query params: `styles.css?v=2.2`, `script.js?v=2.2`
- Bump version in: (1) preload link, (2) stylesheet link, (3) script tag
- Also append version comment to CSS file to force wrangler content-hash change

### Identity Documents (v2.0 — Anime/Neon direction)
- `/mnt/d/Proyectos/Yggdrasil/Svartalfheim/LILITH_IDENTITY.md` — Full spec v2.0: anime concept, 9 variants, voice, brand applications, neon palette (magenta #d946ef added)
- `/mnt/d/Proyectos/Yggdrasil/Svartalfheim/LILITH_ARTIST_BRIEF.md` — Commission brief v2.0: anime style specs, neon per-realm colors, Printful-ready, DO's and DON'Ts for anime style

### Deployment Checklist v2.5+
After modifying site files:
1. Bump `?v=X.Y` in all 3 locations in index.html (preload CSS link, stylesheet link, script tag src)
2. If you also changed CSS, append a version comment to end of styles.css (`/* vX.Y */`) to force wrangler content-hash change
3. Run: `CLOUDFLARE_API_TOKEN=cfat_xxx CLOUDFLARE_ACCOUNT_ID=${CLOUDFLARE_ACCOUNT_ID} npx wrangler pages deploy . --project-name=brierstudios`
4. Verify in browser: navigate to site, check console for errors, test scroll animations
5. If changes don't appear, it's a CDN cache issue — the `?v=` bump should handle it. If wrangler says "0 files uploaded", force re-upload by appending trivial comment to the changed file.

**Cache-busting details**:
- Query-param `?v=X.Y` busts both CDN and browser caches simultaneously
- Wrangler checks content hashes before uploading — if hash matches a prior deploy, it skips the file
- Account tokens (`cfat_*`) CANNOT purge Cloudflare CDN cache via API — only `cfut_*` user tokens can. Always rely on `?v=` query params instead.

### v2.5 Changes (deployed May 2026)

**f1-2: Terminal Demo** (`#cli-demo` section)
- Animated terminal window with typing effect, cycling 3 scenes (`ygg init`, `ygg build`, `ygg deploy`)
- Prompt: `tú@yggdrasil:~$` with color-coded segments (green user, cyan host, yellow path)
- Output line types: `.t-info`, `.t-success`, `.t-warn`, `.t-error`, `.t-dim`, `.t-ice-bright`
- Scanlines overlay, glow pulse animation, blinking cursor
- IntersectionObserver-triggered (30% threshold), respects `prefers-reduced-motion`
- Quick-install code blocks below terminal with copy buttons

**f1-3: Copy Buttons** (`.copy-btn`)
- Clipboard API with `navigator.clipboard.writeText()` + `document.execCommand('copy')` fallback
- SVG icon swap: clipboard → checkmark on success, reverts after 2s
- Green glow state (`.copied` class)

**f1-4: Releases Page** (`/releases`)
- Standalone `releases.html` sharing main `styles.css` + `script.js`
- Vertical timeline with `.release-card` + `.release-dot` (rune inside)
- Tags: `.tag-latest` (cyan), `.tag-feature` (magenta), `.tag-fix` (green)
- Scroll-reveal animation via IntersectionObserver
- 7 versions documented: v1.0 (Genesis) → v2.5 (Terminal Demo)
- Page-specific `<style>` block for timeline + releases layout
- Mobile responsive (640px breakpoint)

**f1-5: More Whitespace**
- `section { padding }`: `6rem 0` → `8rem 0`
- `.section-header { margin-bottom }`: `4rem` → `5rem`

**Cache Bump**: `?v=2.4` → `?v=2.5` in 3 HTML locations (preload CSS, stylesheet link, script tag)

### Site File Structure (v2.5)
```
/mnt/d/Proyectos/brierstudios-site/
├── index.html              # Main landing (695 lines)
├── releases.html           # Release timeline page (new v2.5)
├── styles.css              # Shared styles (1209 lines)
├── script.js               # Shared scripts (860 lines)
├── manifest.json           # PWA manifest
├── _headers                # CF Pages security headers
├── _redirects              # www → apex redirect
├── 404.html                # Custom 404
├── favicon.svg/ico/png     # Icons
├── og-image.png            # Open Graph image
└── assets/lilith/          # Lilith character images
```

### v2.6 Changes (deployed May 2026)

**SEO + LLM Discovery**
- `llms.txt` at root — full brand/product/tech description for AI crawlers (ChatGPT, Claude, Perplexity, etc.)
- `sitemap.xml` — 13 URLs (landing, releases, all docs pages with priorities)
- `robots.txt` — allows all crawlers plus explicit allows for GPTBot, ChatGPT-User, CCBot, Google-Extended, OAI-SearchBot, PerplexityBot; Disallow: /assets/
- `index.html` meta tags updated: description changed from "Dark fantasy" → "anime cyberpunk neon aesthetics with Norse mythology"; added `<meta name="keywords">`, `<meta name="author">`, `<meta name="robots" content="index, follow">`; OG + Twitter Card + Schema.org descriptions all updated to match
- `releases.html` meta tags similarly updated with keywords, author, robots, richer OG description

**Cache Bump**: `?v=2.5` → `?v=2.6` in 3 HTML locations

### Site File Structure (v2.6)
```
/mnt/d/Proyectos/brierstudios-site/
├── index.html              # Main landing (v2.6)
├── releases.html           # Release timeline page
├── styles.css              # Shared styles
├── script.js               # Shared scripts
├── llms.txt                # AI crawler description (NEW v2.6)
├── sitemap.xml             # XML sitemap (NEW v2.6)
├── robots.txt              # Robots + LLM allows (NEW v2.6)
├── manifest.json           # PWA manifest
├── _headers                # CF Pages security headers
├── _redirects              # www → apex redirect
├── 404.html                # Custom 404
├── favicon.svg/ico/png     # Icons
├── og-image.png            # Open Graph image
└── assets/lilith/          # Lilith character images
```

### Docs Site (docs.brierstudios.com)

- **Project path**: `/home/brierainz/comfy/docs-brierstudios/`
- **Pages project**: `docs-brierstudios`
- **URL**: `https://docs-brierstudios.pages.dev`
- **Custom domain**: `docs.brierstudios.com` (CNAME → docs-brierstudios.pages.dev, proxied)
- **Stack**: Docusaurus v3 + TypeScript, custom neon theme (cyan/magenta/abyss)
- **Sections**: Intro, CLI (19 commands), Lilith v2.0, Architecture, Agents, LoRA Training
- **Build**: `npm run build` → `build/` (98 files); deploy: `CLOUDFLARE_API_TOKEN=cfat_xxx CLOUDFLARE_ACCOUNT_ID=${CLOUDFLARE_ACCOUNT_ID} npx wrangler pages deploy build --project-name=docs-brierstudios`
- **See also**: `docusaurus` skill for full setup/customization details

### Still pending
- Submit to HSTS preload list (https://hstspreload.org/) — one-time manual step
- Add SRI integrity attributes to `script.js` in the HTML
- Generate more Lilith anime variant art (commission artist using v2.0 brief)
- Add `/lilith` dedicated page with full lore, art gallery, variants
- Dark/Light mode toggle (frost-dark / frost-light nordic)
- Blog/Showcase section (needs art content first)
- Printful merch integration (needs product designs)