# BrierStudios Site Enhancement — Session Reference

## Context
- **Site**: https://brierstudios.com (anime/cyberpunk neon portfolio)
- **Repo**: BrierAinz/brierstudios-site (GitHub)
- **Pages project**: `brierstudios` — direct upload mode (no Git auto-deploy)
- **Account ID**: ${CLOUDFLARE_ACCOUNT_ID}
- **Zone ID**: ${CLOUDFLARE_ZONE_ID}
- **Worker subdomain**: `brierstudios-contact.gameoverhf12.workers.dev`
- **Worker custom domain**: `contact.brierstudios.com` (configured via Workers Domains API)
- **Current version**: v2.7 (SEO, OG, social links, sitemap, robots.txt, llms.txt)

## What Was Added

### v2.7 — Social Links + SEO
- **Contact section**: Twitter/X (@BrierAinz) + Instagram (@brier_studios) items with runas (ᛉ, ᛁ)
- **Footer social bar**: `.footer-links` div with emoji links (𝕏, 📷, ⌘, 📖), hover cyan glow + translateY
- **Ecosystem link**: Updated from old GitHub Pages to `docs.brierstudios.com`
- **SEO meta tags**: `<meta name="keywords">`, `<meta name="author">`, `<meta name="robots">` on index + releases
- **OG/Twitter Card descriptions**: Updated from "dark fantasy" to "anime cyberpunk neon aesthetics"
- **Schema.org JSON-LD**: Updated description to match v2.0 identity
- **`llms.txt`**: Full brand/product/tech description for AI crawlers (GPTBot, Claude, Perplexity)
- **`robots.txt`**: Allows all crawlers + explicit allows for LLM bots (GPTBot, ChatGPT-User, CCBot, Google-Extended, OAI-SearchBot, PerplexityBot)
- **`sitemap.xml`**: 13 URLs covering landing, releases, and all docs pages
- **Cache-bust**: Bumped `?v=2.5` → `?v=2.6` on CSS/JS links in index.html
- **Docs site**: Docusaurus v3 deployed at `docs-brierstudios.pages.dev` + `docs.brierstudios.com`
  - Navbar: Added 𝕏 and 📷 social links (position: right)
  - Footer: Added Twitter/X, Instagram to Community section; Main Site link in More section
  - 6 doc sections: Intro, CLI, Lilith v2.0, Architecture, Agents, LoRA Training

### v2.6 — SEO Foundation
- `llms.txt`, `robots.txt`, `sitemap.xml` added
- Open Graph + Twitter Card tags updated (anime/cyberpunk descriptions)
- Schema.org JSON-LD description updated
- Cache-bust `?v=2.5` → `?v=2.6`

### SEO
- `<link rel="canonical">` — https://brierstudios.com/
- Favicon suite: `favicon.svg`, `favicon.ico` (16+32), `favicon-512.png`, `apple-touch-icon.png` (180x180)
- Open Graph: og:title, og:description, og:image (custom 1200x630), og:url, og:type
- Twitter Card: summary_large_image with og-image.png
- Schema.org JSON-LD (Organization type)
- robots.txt + sitemap.xml

### Performance
- `<script src="script.js" defer>` (was blocking)
- `<link rel="preconnect">` for Google Fonts domains
- `<link rel="preload">` for styles.css + script.js
- Cache headers in `_headers` (CSS/JS 1yr, assets immutable)
- SRI integrity hash on Google Fonts stylesheet link

### Visual Effects (script.js + styles.css)
- **Aurora borealis**: CSS animated gradient in hero, follows mouse via CSS custom properties `--aurora-x`, `--aurora-y`
- **Constellation lines**: Canvas draws lines between nearby rune particles (dist < 120px), semi-transparent frost color
- **Glitch title**: CSS `clip-path` + `text-shadow` offset on hover of `.hero-title`
- **Stats counter**: IntersectionObserver triggers animated count-up (ease-out cubic, 2s duration)
- **Enhanced cursor trail**: Frost particles spawn near mouse position with random offsets
- **3D tilt cards**: Project cards tilt on mouse via `perspective(800px)`, glare overlay follows cursor
- **Typing effect**: Hero subtitle types out character-by-character with blinking cursor, pauses on punctuation
- **Navbar shrink**: Navbar reduces height (64px→48px) after 200px scroll, transitions on font-size and logo
- **Skills section**: 12 rune cards with hover glow/scale, animated progress bars fill on `.visible`

### PWA (Progressive Web App)
- `manifest.json`: name, icons (512, 180, SVG), theme_color #38bdf8, background_color #060810
- `sw.js`: network-first for HTML, cache-first for assets, precaches 10 core URLs
- `<link rel="manifest">` + apple-mobile-web-app meta tags in HTML
- `registerServiceWorker()` in script.js with silent catch

### Security
- `_headers` — CSP enforcing (NOT report-only), full directives including connect-src for contact Worker
- HSTS (via Cloudflare dashboard + submit to hstspreload.org, status: pending)
- X-Content-Type-Options, X-Frame-Options, Referrer-Policy, Permissions-Policy, COOP, CORP
- SRI integrity hash on Google Fonts CSS link
- CSP: `default-src 'self'; script-src 'self' static.cloudflareinsights.com; style-src 'self' fonts.googleapis.com 'unsafe-inline'; font-src 'self' fonts.gstatic.com; img-src 'self' data: https:; connect-src 'self' contact.brierstudios.com; frame-ancestors 'none'; base-uri 'self'; form-action 'self' contact.brierstudios.com`

### UX
- **Contact form**: Functional via Cloudflare Worker (was fake setTimeout), POSTs to `contact.brierstudios.com`
- **404.html**: Custom "Realm Not Found" page with same design system
- **Stats section**: 4 animated numbers between About and Projects sections
- **Scroll animations**: IntersectionObserver with `.visible` class toggle for fade-in elements (includes `.skill-rune-card`)
- **OG image**: Custom 1200x630 PNG for social sharing

### Workers
- **Worker name**: `brierstudios-contact`
- **KV namespace**: `brierstudios-contacts` (ID: 3fb19e866d3042efaf521d27c3a7efa8)
- **Worker URL**: https://brierstudios-contact.gameoverhf12.workers.dev
- **Custom domain**: `contact.brierstudios.com` — configured via Workers Domains API (NOT manual CNAME)
- **wrangler.toml** at repo root (excluded from Pages deploy)

## Bug Fixes Applied

### Stats Section Invisible (opacity: 0)
**Problem**: `.stat-item` elements had class `fade-in` (which sets `opacity: 0`) but the IntersectionObserver selector didn't include `.stat-item` specifically.

**Fix**: Added `.stat-item` to the IntersectionObserver selector.

**Lesson**: When adding new animated sections, always include their specific class in the observer selector, even if they also have `.fade-in`. Makes the intent explicit and avoids subtle timing issues.

### Stats Counter Race Condition (Two Observers)
**Problem**: Two separate IntersectionObservers on overlapping elements caused visible stat items showing `0`.

**Fix**: 
1. Lower counter observer threshold from 0.3 to 0.1
2. Counter observer explicitly adds `.visible` class before animating
3. 300ms delay between visibility and counter start
4. `observer.disconnect()` after trigger

**Lesson**: When multiple IntersectionObservers target overlapping elements, consolidate visibility logic.

### Worker Custom Domain 522 Error
**Problem**: Manual CNAME for Worker caused 522 error.

**Fix**: Delete CNAME, use Workers Domains API (`PUT /accounts/{id}/workers/domains`).

**Lesson**: Never manually create DNS records for Worker custom domains. Use Workers Domains API.

## Design System (for future changes)

```
--bg: #060810        (deep navy-black)
--bg-light: #0f1219  (slightly lighter)
--frost: #bae6fd     (ice blue light)
--accent: #38bdf8    (primary ice blue)
--aurora: #818cf8    (purple accent)
--text: #e2e8f0      (light gray)
--text-muted: #64748b (muted)
--rune: #38bdf8      (rune glow)
```

Font: Inter (Google Fonts), Cinzel (headings), JetBrains Mono (code)

## Deploy Commands

```bash
# Pages site — simple deploy from repo root
cd /mnt/d/Proyectos/brierstudios-site
CLOUDFLARE_API_TOKEN=${CLOUDFLARE_API_TOKEN} \
CLOUDFLARE_ACCOUNT_ID=${CLOUDFLARE_ACCOUNT_ID} \
npx wrangler pages deploy . --project-name=brierstudios

# Worker (from repo root, has wrangler.toml)
cd /mnt/d/Proyectos/brierstudios-site
npx wrangler deploy
```

**Pitfall**: Project name is `brierstudios` (NOT `brierstudios-site`). Using the wrong name returns error 8000007 "Project not found".

**Pitfall**: For direct-upload projects, `git push` does NOT auto-deploy. Must run `wrangler pages deploy` manually after each change.

## Skills Section Redesign (v2.1)

The original skills section had plain cards with `fade-in` class — visually boring with small runes (16px) and no depth.

### Redesigned with:
- **Large rune symbols** (2.8rem / 44.8px) with cyan glow text-shadow
- **Card backgrounds**: linear-gradient from `void-card` to `rgba(56,189,248,0.03)`
- **Staggered reveal**: Each `.skill-rune-card:nth-child(N)` has `transition-delay: 0.05s * N`. Cards start with `opacity: 0; transform: translateY(30px)` and animate to `.visible` state via IntersectionObserver (`initSkillReveal()`)
- **Shimmer sweep** on hover: `::after` pseudo-element with linear-gradient + `translateX` animation
- **Glow border on hover**: `::before` with `rgba(56,189,248,0.3)` border + box-shadow
- **Progress bars**: 4px height, animated width via `var(--skill-pct)`, glowing dot at end (`::after` with `box-shadow`)
- **Percentage labels**: `.skill-pct` div that fades in after bar animation
- **Grid**: 4 columns desktop, 3 tablet, 2 mobile
- **Radial gradient section background**: `radial-gradient(ellipse at 50% 30%, rgba(56,189,248,0.06), transparent 70%)`

### CSS variables used by skill cards:
- `--skill-pct` (set inline on each card, e.g. `95%`)
- `--void-card` (#101620)
- `--void-border` (#182030)
- `--frost` (#bae6fd)
- `--accent` (#38bdf8)

### Bug Fix — CDN Cache
**Problem**: After redesigning skills CSS and deploying, live site showed old styles. Wrangler said "0 files uploaded" because content-hash matched cached version. Cloudflare CDN cached the old CSS.

**Fix**: Two steps:
1. Append version comment to CSS: `echo "/* v2.1 */" >> styles.css` → forces different file hash → wrangler detects change
2. Add `?v=2.1` cache-bust query param to `<link>` and `<script>` URLs in HTML → forces CDN and browser bypass

**Pitfall**: Account tokens cannot purge zone-level cache via `POST /zones/{id}/purge_cache` (returns 10000 auth error). Cache-busting URLs is the only programmatic solution.

## Completed
- [x] DNS for contact.brierstudios.com — configured via Workers Domains API
- [x] HSTS preload — submitted and pending at hstspreload.org
- [x] All visual effects working (aurora, constellations, glitch, stats counter, tilt cards, typing, navbar shrink)
- [x] Contact form functional with Worker + KV
- [x] PWA (manifest.json + service worker)
- [x] Skills section with 12 animated rune cards (redesigned v2.1 with staggered reveal, shimmer, glow, progress dots, pct labels)
- [x] CSP enforcing (not report-only)
- [x] Favicon suite (SVG, ICO 16+32, 512 PNG, apple-touch-icon 180)
- [x] OG image 1200x630
- [x] SRI integrity hash on Google Fonts link
- [x] Cache-busting (`?v=2.6`) on CSS/JS URLs
- [x] SEO meta tags (keywords, author, robots) on index + releases pages
- [x] OG + Twitter Card descriptions updated (anime/cyberpunk neon)
- [x] Schema.org description updated
- [x] llms.txt, robots.txt, sitemap.xml deployed
- [x] Social links (Twitter/X @BrierAinz, Instagram @brier_studios) in contact section + footer
- [x] Footer social bar with hover cyan glow
- [x] Docs site (docs.brierstudios.com) with social links in navbar + footer
- [x] Ecosystem link updated to docs.brierstudios.com