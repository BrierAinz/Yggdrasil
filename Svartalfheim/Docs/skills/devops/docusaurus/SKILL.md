---
name: docusaurus
category: devops
description: Set up, customize, and deploy Docusaurus documentation sites. Covers project scaffolding, theme customization, content structure, Cloudflare Pages deployment with custom domains, and iterative updates.
triggers:
  - docusaurus
  - docs site
  - documentation site
  - docs.brierstudios.com
  - setup docs
  - deploy docs
---

# Docusaurus Documentation Sites

## Overview

Docusaurus v3 (TypeScript) is the standard for static documentation sites. Use it for any project docs, API references, or knowledge bases that need sidebar navigation, search, dark mode, and versioned content.

## Project Setup

### Scaffold New Project

```bash
npx create-docusaurus@latest /path/to/project classic --skip-install --typescript
cd /path/to/project
npm install
```

**PITFALL**: `create-docusaurus` launches an interactive prompt. Always pass `--typescript` (or `--javascript`) to skip the language picker. The `--skip-install` flag lets you run `npm install` separately for better control.

### Build & Preview

```bash
npm run build       # Production build → ./build/
npm run serve       # Preview production build on :3000
npm run start       # Dev server with hot reload on :3000
```

### Directory Structure

```
project/
├── blog/              # Blog posts (MDX)
├── docs/              # Documentation pages (MDX)
│   ├── intro.md
│   ├── cli/
│   │   ├── getting-started.md
│   │   ├── commands.md
│   │   └── _category_.json
│   ├── architecture/
│   └── ...
├── src/
│   ├── css/
│   │   └── custom.css     # Theme overrides (CRITICAL)
│   ├── components/         # Custom React components
│   └── pages/
│       ├── index.tsx       # Homepage
│       └── styles.module.css
├── static/             # Static assets (img/, favicon, CNAME)
├── docusaurus.config.ts
├── sidebars.ts
├── package.json
└── tsconfig.json
```

## Theme Customization

### BrierStudios Neon Palette (Primary Example)

Edit `src/css/custom.css` to override Infima variables. This is the **canonical way** to theme Docusaurus — never edit node_modules.

```css
:root {
  --ifm-color-primary: #38bdf8;           /* cyan */
  --ifm-color-primary-dark: #0ea5e9;
  --ifm-color-primary-darker: #0284c7;
  --ifm-color-primary-light: #7dd3fc;     /* aurora */
  --ifm-color-primary-lighter: #bae6fd;
  --ifm-background-color: #0f172a;        /* abyss */
  --ifm-navbar-background-color: #0c1322;
  --ifm-sidebar-background-color: #0f172a;
  --ifm-font-family-base: 'Inter', system-ui, sans-serif;
  --ifm-font-family-monospace: 'JetBrains Mono', monospace;
}

[data-theme='dark'] {
  --ifm-color-primary: #38bdf8;
  --ifm-background-color: #0f172a;
  --ifm-code-background: #1e293b;
  /* Accent: magenta for links, hover states */
  --ifm-color-secondary: #d946ef;
}
```

### Fonts

Add Google Fonts to `docusaurus.config.ts`:

```typescript
stylesheets: [
  {
    href: 'https://fonts.googleapis.com/css2?family=Cinzel:wght@400;700&family=Inter:wght@300;400;600;700&family=JetBrains+Mono:wght@400;700&display=swap',
  },
],
```

Apply via CSS:
```css
h1, h2, h3, .hero__title {
  font-family: 'Cinzel', serif;
}
code, pre {
  font-family: 'JetBrains Mono', monospace;
}
```

### Homepage Hero

Edit `src/pages/index.tsx` for a custom hero with neon glow effects:

```tsx
<header className="hero hero--dark">
  <div className="container">
    <h1 className="hero__title">🌲 Docs</h1>
    <p>Documentation for your project</p>
    <div className="hero-buttons">
      <Link className="button button--primary" to="/docs/intro">Enter →</Link>
      <Link className="button button--outline" to="/docs/cli/getting-started">CLI Quick Start</Link>
    </div>
  </div>
</header>
```

## Content Structure

### Sidebar Configuration

Use `sidebars.ts` with categorized docs:

```typescript
import type {SidebarsConfig} from '@docusaurus/plugin-content-docs';

const sidebars: SidebarsConfig = {
  docsSidebar: [
    'intro',
    {type: 'category', label: 'CLI', link: {type: 'doc', id: 'cli/getting-started'}, items: ['cli/getting-started', 'cli/commands', 'cli/realms']},
    {type: 'category', label: 'Lilith v2.0', link: {type: 'doc', id: 'lilith/identity'}, items: ['lilith/identity', 'lilith/palette', 'lilith/variants']},
    {type: 'category', label: 'Architecture', link: {type: 'doc', id: 'architecture/overview'}, items: ['architecture/overview', 'architecture/realms', 'architecture/conventions']},
    {type: 'category', label: 'Agents', link: {type: 'doc', id: 'agents/overview'}, items: ['agents/overview', 'agents/discord', 'agents/telegram']},
    {type: 'category', label: 'LoRA Training', link: {type: 'doc', id: 'lora/overview'}, items: ['lora/overview', 'lora/z-image', 'lora/pipeline']},
  ],
};

export default sidebars;
```

### Category Metadata

Add `_category_.json` in each doc folder:

```json
{
  "label": "CLI",
  "position": 2,
  "collapsible": true,
  "collapsed": true
}
```

### Navbar Configuration

In `docusaurus.config.ts`:

```typescript
navbar: {
  title: 'BrierStudios',
  logo: {alt: 'BrierStudios Logo', src: 'img/logo.svg'},
  items: [
    {type: 'docSidebar', sidebarId: 'docsSidebar', position: 'left', label: 'ᚨ Docs'},
    {to: '/docs/cli/getting-started', label: 'ᚲ CLI', position: 'left'},
    {to: '/blog', label: 'ᛞ Blog', position: 'left'},
    {href: 'https://x.com/BrierAinz', label: 'ᛋ X', position: 'right'},
    {href: 'https://www.instagram.com/brier_studios', label: 'ᚦ IG', position: 'right'},
    {href: 'https://github.com/BrierAinz', label: 'ᚠ GH', position: 'right'},
  ],
},
```

**NO EMOJIS**: Use Elder Futhark rune glyphs instead of emojis for all UI labels and icons. The user explicitly rejected emojis ("no quiero emojis"). See the **Rune Icon System** below for the full mapping.

### Footer Configuration

```typescript
footer: {
  style: 'dark',
  links: [
    {title: 'Docs', items: [{label: 'Introduction', to: '/docs/intro'}, {label: 'CLI Reference', to: '/docs/cli/commands'}, {label: 'Architecture', to: '/docs/architecture/overview'}]},
    {title: 'Community', items: [{label: 'Discord', href: '#'}, {label: 'GitHub', href: 'https://github.com/BrierAinz'}]},
    {title: 'More', items: [{label: 'Blog', to: '/blog'}, {label: 'GitHub', href: 'https://github.com/BrierAinz'}]},
  ],
  copyright: 'ᛊ ᛃ 2024–2025 BrierStudios. Forged in Yggdrasil.',
},
```

## Cloudflare Pages Deployment

### One-Time Setup

```bash
# Create the Pages project
CLOUDFLARE_API_TOKEN=cfat_xxx CLOUDFLARE_ACCOUNT_ID=xxx \
  npx wrangler@latest pages project create docs-myproject --production-branch=main

# Add custom domain via API
curl -s -X POST "https://api.cloudflare.com/client/v4/accounts/$ACCOUNT_ID/pages/projects/docs-myproject/domains" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"name":"docs.myproject.com"}'

# Add DNS CNAME
curl -s -X POST "https://api.cloudflare.com/client/v4/zones/$ZONE_ID/dns_records" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"type":"CNAME","name":"docs","content":"docs-myproject.pages.dev","proxied":true}'
```

### Deploy

```bash
cd /path/to/project
npm run build
CLOUDFLARE_API_TOKEN=cfat_xxx CLOUDFLARE_ACCOUNT_ID=xxx \
  npx wrangler pages deploy build --project-name=docs-myproject
```

**PITFALL**: Always set BOTH `CLOUDFLARE_API_TOKEN` AND `CLOUDFLARE_ACCOUNT_ID` env vars for non-interactive deploys. Without account ID, wrangler fails with "Failed to automatically retrieve account IDs."

**PITFALL**: The project name passed to `--project-name` must match EXACTLY the name used when creating the project. Mismatch = error 8000007.

### Cache Busting

After deploys, if changes aren't visible:
1. Bump version query strings in any hardcoded asset URLs
2. Docusaurus auto-hashes JS/CSS bundles, so usually no issue
3. If stale: `rm -rf .docusaurus build && npm run build && npx wrangler pages deploy build --project-name=docs-myproject`

## BrierStudios Docs (Active Project)

- **Project path**: `/home/brierainz/comfy/docs-brierstudios/`
- **Pages project**: `docs-brierstudios`
- **URLs**: `https://docs-brierstudios.pages.dev` + `https://docs.brierstudios.com` (CNAME proxied)
- **Zone**: `${CLOUDFLARE_ZONE_ID}` (brierstudios.com)
- **CF Account**: `${CLOUDFLARE_ACCOUNT_ID}`
- **Theme**: Dark neon (cyan/magenta/abyss), Cinzel headings, JetBrains Mono code, Inter body
- **Sections**: Intro, CLI (4 pages), Lilith v2.0 (4 pages), Architecture (3 pages), Agents, LoRA Training (2 pages)
- **Blog**: 3 release posts (v2.3, v2.5, v2.6)
- **Custom Components**: RealmBadge, ColorSwatch, CommandBlock, RuneDivider (registered via MDXComponents.tsx)
- **Custom Admonitions**: realm (ᛊ cyan), neon (ᛉ magenta), runic (ᚨ gold)
- **Rune Icon System (`.ri`)**: Elder Futhark glyphs replace ALL emojis site-wide. Each rune maps to a semantic concept with a neon-glow CSS class. See `references/rune-icon-system.md` for full mapping.
- **Theme Swizzles**: Root.tsx (ScrollProgressBar), MDXComponents.tsx, Admonition.tsx
- **CSS Effects**: Floating runes hero, glow pulse headings, scanline overlay, gradient card borders, sidebar hover glow, TOC neon ticks, scroll progress bar, page fade transition
- **SEO**: Metadata array, Algolia placeholder, llms-full.txt, sitemap, RSS
- **Social links**: Navbar (ᛋ X, ᚦ IG, ᚠ GH, ᛊ Home pill button → brierstudios.com), Footer (X, Instagram, GitHub, BrierStudios.com — Home)
- **Navbar Home**: Logo + title links to brierstudios.com via Navbar.tsx swizzle. ᛊ Home pill button with cyan→magenta gradient. Footer also has explicit "— Home" link.
- **SVG Logo**: Custom Yggdrasil tree logo (`static/img/logo.svg`)
- **Build output**: `build/` (~163 files, ~2s upload). Always `npm run build` before deploy — Docusaurus must regenerate static files.

## Iterative Updates

After modifying docs content or theme:

```bash
cd /home/brierainz/comfy/docs-brierstudios
npm run build
CLOUDFLARE_API_TOKEN=${CLOUDFLARE_API_TOKEN} \
CLOUDFLARE_ACCOUNT_ID=${CLOUDFLARE_ACCOUNT_ID} \
  npx wrangler pages deploy build --project-name=docs-brierstudios
```

## Custom Components & Theme Swizzling

Docusaurus v3 supports "swizzling" — overriding theme components by placing files in `src/theme/`. This is how you inject custom React components, admonitions, and global wrappers.

### MDX Components (`src/theme/MDXComponents.tsx`)

Register custom inline components usable in `.md` / `.mdx` docs:

```tsx
import React from 'react';
import MDXComponents from '@theme-original/MDXComponents';
import RealmBadge from '@site/src/components/RealmBadge';
import ColorSwatch from '@site/src/components/ColorSwatch';
import CommandBlock from '@site/src/components/CommandBlock';
import RuneDivider from '@site/src/components/RuneDivider';

export default {
  ...MDXComponents,
  RealmBadge,
  ColorSwatch,
  CommandBlock,
  RuneDivider,
};
```

Components live in `src/components/` and are standard React components with their own CSS classes (styled in `src/css/custom.css`).

### Custom Admonitions (`src/theme/Admonition.tsx`)

Add custom admonition types beyond the built-in `note`, `tip`, `warning`, etc.:

```tsx
import React from 'react';
import type {Props} from '@theme/Admonition';

const CUSTOM_TYPES = {
  realm:  { icon: 'ᛊ', title: 'Realm',  cssClasses: ['admonition--realm'] },
  neon:   { icon: 'ᛉ', title: 'Neon',   cssClasses: ['admonition--neon'] },
  runic:  { icon: 'ᚨ', title: 'Runic',  cssClasses: ['admonition--runic'] },
} as const;

let OriginalAdmonition;
try { OriginalAdmonition = require('@theme-original/Admonition').default; } catch {}

export default function Admonition(props: Props): JSX.Element {
  const customType = (CUSTOM_TYPES as any)[props.type as string];
  if (customType) {
    return (
      <div className={`admonition admonition--${props.type} ${customType.cssClasses.join(' ')}`}>
        <div className="admonition-heading">
          <span className="admonition-icon"><span className={`ri ri-${props.type === 'realm' ? 'asgard' : props.type === 'neon' ? 'vanaheim' : 'svartalfheim'}`}>{customType.icon}</span></span>
          {props.title || customType.title}
        </div>
        <div className="admonition-content">{props.children}</div>
      </div>
    );
  }
  return OriginalAdmonition ? <OriginalAdmonition {...props} /> : /* fallback */;
}
```

Use in docs: `:::realm[Realm Name] Content here :::`

### Root Component (`src/theme/Root.tsx`)

Inject global components (scroll progress bars, analytics, etc.):

```tsx
import React from 'react';
import Root from '@theme-original/Root';
import ScrollProgressBar from '@site/src/theme/ScrollProgressBar';

export default function RootWrapper({children}) {
  return (
    <>
      <ScrollProgressBar />
      {children}
    </>
  );
}
```

### Scroll Progress Bar (`src/theme/ScrollProgressBar.tsx`)

```tsx
import { useEffect } from 'react';

export default function ScrollProgressBar(): null {
  useEffect(() => {
    const bar = document.createElement('div');
    bar.className = 'scroll-progress-bar';
    document.body.prepend(bar);
    const onScroll = () => {
      const pct = window.scrollY / (document.documentElement.scrollHeight - window.innerHeight) * 100;
      bar.style.width = `${pct}%`;
    };
    window.addEventListener('scroll', onScroll, { passive: true });
    onScroll();
    return () => { window.removeEventListener('scroll', onScroll); bar.remove(); };
  }, []);
  return null;
}
```

CSS in `custom.css`:
```css
.scroll-progress-bar {
  position: fixed; top: 0; left: 0; width: 0%;
  height: 3px;
  background: linear-gradient(90deg, #38bdf8, #d946ef, #fbbf24);
  z-index: 9999; transition: width 0.1s linear;
  box-shadow: 0 0 8px rgba(56, 189, 248, 0.5);
}
```

## Blog Setup

### Authors (`blog/authors.yml`)

```yaml
AuthorName:
  name: Display Name
  title: Role
  url: https://github.com/username
  image_url: https://github.com/username.png
```

### Tags (`blog/tags.yml`)

```yaml
release:
  label: Release
  permalink: /blog/tags/release
design:
  label: Design
  permalink: /blog/tags/design
```

**CRITICAL**: Docusaurus v3 tags.yml must be **flat YAML** — no `tags:` top-level key. Nesting under `tags:` causes `"tags.release" is not allowed` validation error.

### Blog Post Format

```markdown
---
slug: v2-6-release
title: 'v2.6: Feature Name'
authors: [AuthorName]
tags: [release, design]
description: 'Short description for SEO and previews.'
---

Intro paragraph here.

## What's New

{/* truncate */}

Details continue below the fold...
```

**CRITICAL**: Use `{/* truncate */}` for blog post truncation in MDX files. HTML comments `<!-- truncate -->` cause MDX compilation errors (`Unexpected character ! before name`).

### Linking Docs to Main Site (Navbar Home Button)

Docusaurus navbar title/logo links to the docs root (`/`) by default. To make it link to the **main site** (e.g., `brierstudios.com`), create a Navbar swizzle:

**`src/theme/Navbar.tsx`** — overrides the logo/title href:
```tsx
import React from 'react';
import Navbar from '@theme-original/Navbar';
import type {Props} from '@theme/Navbar';

export default function NavbarWrapper(props: Props) {
  return (
    <>
      <Navbar {...props} />
      <script dangerouslySetInnerHTML={{ __html: `
(function() {
  var logo = document.querySelector('.navbar__brand');
  var title = document.querySelector('.navbar__title');
  if (logo) { logo.href = 'https://brierstudios.com'; }
  if (title) { title.href = 'https://brierstudios.com'; }
})();
      `}} />
    </>
  );
}
```

Also add a prominent **"Home" button** in `docusaurus.config.ts` navbar items with a neon pill style:
```typescript
{ href: 'https://brierstudios.com', label: 'ᛊ Home', position: 'right' },
```

**PITFALL**: Docusaurus navbar logo/title always links to the docs site root (`baseUrl`). To override this to point to an external main site, you need a Navbar swizzle (`src/theme/Navbar.tsx`) that runs a client-side script to change the href. There is NO config option to change the logo link in Docusaurus — only the swizzle approach works.

CSS for the pill button:
```css
.navbar-home-link {
  background: linear-gradient(135deg, #38bdf8 0%, #d946ef 100%) !important;
  color: #0f172a !important;
  font-weight: 700 !important;
  padding: 0.35em 1em !important;
  border-radius: 9999px !important;
  box-shadow: 0 0 8px rgba(56,189,248,0.4), 0 0 16px rgba(217,70,239,0.2) !important;
}
```

This gives users 3 ways to navigate back: (1) logo/title click, (2) Home pill button in navbar, (3) footer link labeled "— Home".

## SEO Configuration

### Metadata & Open Graph

In `docusaurus.config.ts` themeConfig:

```typescript
themeConfig: {
  image: 'img/og-social-card.png',
  metadata: [
    { name: 'description', content: 'Site description for search engines.' },
    { name: 'keywords', content: 'keyword1, keyword2, keyword3' },
    { property: 'og:site_name', content: 'Site Name' },
  ],
  algolia: {
    appId: 'PENDING',   // Apply at https://docsearch.algolia.com/apply/
    apiKey: 'PENDING',
    indexName: 'myproject',
  },
}
```

### llms-full.txt

Create `static/llms-full.txt` with structured documentation for LLM crawlers. Accessible at `/llms-full.txt` after deploy.

### Sitemap & RSS

Docusaurus generates `sitemap.xml` and Atom RSS feed automatically (built-in plugins). Blog plugin enables RSS at `/blog/rss.xml`.

## Pitfalls

1. **Interactive scaffolding**: `create-docusaurus` without `--typescript` or `--javascript` flag prompts interactively. Always pass the flag.

2. **Custom CSS only**: Never edit `node_modules/` or Docusaurus core CSS. Use `src/css/custom.css` with Infima variable overrides. Changes there persist across updates.

3. **Build before deploy**: Docusaurus requires `npm run build` to generate the `build/` directory. Deploying `src/` directly won't work.

4. **CNAME file for custom domains**: Place a `static/CNAME` file containing `docs.myproject.com` if using Git-based deploys. For direct upload (wrangler), use the API approach above.

5. **Markdown front matter**: Docusaurus MDX supports `---` front matter with `title`, `description`, `slug`, `hide_title`, `hide_table_of_contents`. Use these for SEO.

6. **Internal links**: Use relative paths for internal doc links: `[Link](./other-page.md)` or `[Link](/docs/category/page)`. Absolute paths without base URL.

7. **`mdx` config field not valid**: Docusaurus v3.10+ does NOT accept a top-level `mdx` field in `docusaurus.config.ts`. Putting `mdx: { autoIncludes: true }` causes a validation error. MDX auto-includes are the default.

8. **Blog tags.yml must be flat**: In Docusaurus v3, `blog/tags.yml` must be flat YAML without a `tags:` wrapper key. Nesting under `tags:` causes `"tags.release" is not allowed` error at build time.

9. **MDX truncate syntax**: In `.md` blog files processed as MDX, use `{/* truncate */}` NOT `<!-- truncate -->`. HTML-style comments cause MDX parsing errors.

10. **Theme packages need npm install**: Plugins like `@docusaurus/theme-mermaid` must be `npm install`ed before adding to `themes` array in config. Missing packages cause `"Unable to resolve theme"` build errors.

11. **Swizzle imports**: Always import from `@theme-original/ComponentName` (not `@theme/ComponentName`) in swizzled components. The `-original` prefix ensures you extend rather than replace the base component, avoiding infinite loops.

12. **Component registration**: Custom React components in `src/components/` are NOT automatically available in MDX. You MUST register them in `src/theme/MDXComponents.tsx` to use them as JSX tags in `.md`/`.mdx` files.

13. **NO EMOJIS — use runes instead**: The user explicitly rejected emojis ("no quiero emojis"). All site icons, labels, and decorative elements use Elder Futhark rune glyphs with `.ri` CSS classes for neon glow. Never use Unicode emojis (⚡🤖🎨🔥❄️💀🏔🏠🎯🎭🌳📚🔍✅❌etc) anywhere in Docusaurus files. Use the Rune Icon System (see `references/rune-icon-system.md`) instead.

14. **Batch emoji removal**: When replacing emojis with runes across many files, use a programmatic scan for Unicode emoji codepoints (U+1F300–U+1FAFF, U+2600–U+27BF, U+2B50–U+2B55) rather than manual grep. This catches emojis missed by visual inspection.

15. **Blog author keys must match `authors.yml` exactly**: The `authors` front-matter field references key names from `blog/authors.yml`, NOT display names. Using `authors: [ainz]` when the key is `BrierAinz` causes a build error: `Unable to build website for locale en — getAuthorsMapAuthor`. Always check `authors.yml` for the exact key name before writing blog post front matter.

16. **Git repository required for blog builds**: Docusaurus blog plugin requires the project to be inside a git worktree. If `npm run build` fails with `This Docusaurus site is outside any Git worktree`, run `git init && git add -A && git commit -m "initial"` in the project root. Blog posts use git history for dates and author info (even if front matter specifies them explicitly, the plugin still checks for a git repo).

17. **Static asset references must point to existing files**: The `themeConfig.image` field (for OG/social cards) must reference a file that actually exists in `static/img/`. If `docusaurus.config.ts` says `image: 'img/og-social-card.png'` but only `docusaurus-social-card.jpg` exists in `static/img/`, the OG image will be broken. Always verify the referenced file exists and the extension matches.

18. **robots.txt for docs sites**: Every docs site should include a `static/robots.txt` with explicit LLM bot allowances (GPTBot, CCBot, PerplexityBot, etc.) and a sitemap link. Never block `/assets/` (it contains social card images). Block only internal paths like `/sw.js` and `/worker-`. See `references/robots-llm.md` for the full template.

## Reference Files

- **`references/neon-decoration-css.md`** — Reusable CSS patterns for cyberpunk/neon themed docs: floating runes, scanlines, gradient borders, sidebar glow, TOC ticks, scroll progress bar, custom admonitions, page transitions, and glow pulse headings. Copy patterns into `src/css/custom.css`.
- **`references/rune-icon-system.md`** — Elder Futhark rune icon system replacing ALL emojis site-wide. Full glyph-to-concept mapping, CSS `.ri` class implementation, emoji→rune replacement table, batch removal script, and design principles.
- **`references/robots-llm.md`** — robots.txt template for docs sites with explicit LLM bot allowances, sitemap link, and block rules for internal paths.