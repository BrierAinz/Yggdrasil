# SSG Comparison for Project Websites

Decision matrix for choosing a Static Site Generator when migrating or creating a project website on GitHub Pages.

## Overview

For a project ecosystem website (multiple components, dark theme, architecture diagrams, feature showcases), the SSG choice determines development speed, maintenance burden, and visual ceiling.

## Detailed Comparison

### Docusaurus (React-based) — BEST FOR ECOSYSTEMS
- **Setup**: Medium — `npx create-docusaurus`, Node.js required
- **Dark theme**: Excellent — polished Infima design system, CSS variable customization, smooth toggle
- **Mermaid**: Official `@docusaurus/theme-mermaid` plugin, first-class support with dark/light awareness
- **Search**: Requires Algolia DocSearch (free for OSS, needs application)
- **Mobile**: Excellent — fully responsive, hamburger nav, smooth transitions
- **GH Pages**: GitHub Actions workflow, well-documented
- **Versioning**: Built-in — multiple doc versions, version selector dropdown
- **MDX**: React components in Markdown — perfect for interactive realm cards, diagrams as components
- **Showcase**: Has a built-in Showcase feature for displaying projects
- **Used by**: Vite, Redux, Supabase — proven for ecosystem sites
- **Customization**: Swizzling (ejecting components) for full control

**Pros**: Best-in-class ecosystem site. MDX for interactive components. Versioning. Showcase feature.
**Cons**: Requires Algolia for search. React dependency (heavier). Build step required.

### MkDocs Material (Python) — BEST FOR DOCS
- **Setup**: Easy-Medium — `pip install mkdocs-material`
- **Dark theme**: Excellent — `slate` color scheme is stunning out-of-the-box. Best OOB dark theme.
- **Mermaid**: Native via `pymdownx.superfences`, auto-adapts to dark/light
- **Search**: Built-in Lunr/minisearch. No external dependency.
- **Mobile**: Excellent — mobile-first responsive design
- **GH Pages**: `mkdocs gh-deploy` or GitHub Actions
- **Versioning**: Via `mike` plugin (extra setup)
- **Annotations**: Built-in feature grids, tabbed content, annotations, 10k+ icons
- **Customization**: CSS overrides + YAML config. Limited page layouts.

**Pros**: Most beautiful dark theme OOB. Built-in search. Python-native. Fastest to polished docs.
**Cons**: Best features locked behind Insiders ($15/mo). Limited to docs-style layouts. No React components.

### Just the Docs (Jekyll) — BEST FOR SIMPLE DOCS
- **Setup**: Easy — GitHub Pages native, add to Gemfile
- **Dark theme**: Basic — built-in `color_scheme: dark`, utilitarian docs style
- **Mermaid**: Via plugin, basic support
- **Search**: Built-in Lunr search
- **Mobile**: Good — sidebar collapses to hamburger
- **GH Pages**: NATIVE — zero config, push and done
- **Customization**: SCSS overrides (can add Norse colors via `_sass/color_schemes/norse.scss`)

**Pros**: Zero DevOps. Built-in search. Lightweight. Jekyll = GitHub Pages native.
**Cons**: Rigidly docs-oriented. No interactive components. Limited layout flexibility. No versioning.

### Astro — BEST FOR CREATIVE PORTFOLIOS
- **Setup**: Medium-Hard — `npm create astro@latest`, full framework
- **Dark theme**: No default — choose/build your own. Maximum freedom.
- **Mermaid**: Community integrations or embed directly. More work but more flexible.
- **Search**: Pagefind (free, static), Algolia, or custom
- **Mobile**: Depends on theme. Most starters are responsive.
- **GH Pages**: Official `@astrojs/github-pages` adapter
- **Islands**: Embed React/Vue/Svelte components only where needed. Zero JS by default.
- **Content Collections**: TypeScript-validated content schemas
- **View Transitions**: Built-in smooth page transitions

**Pros**: Maximum creative control. Fastest load (zero JS default). Any UI framework. View Transitions.
**Cons**: No default theme — you must design. No built-in search/versioning. Most setup work. Smaller plugin ecosystem.

### Plain HTML/CSS — MINIMAL
- **Setup**: N/A — just push files
- **Dark theme**: Custom — whatever you build
- **Mermaid**: Manual JS inclusion per page
- **Search**: Must add manually (MiniSearch, Fuse.js, Pagefind)
- **Mobile**: Needs improvement for most projects
- **GH Pages**: NATIVE

**Pros**: Maximum control. Zero dependencies. Already done.
**Cons**: No search, no diagram rendering, no component reuse, no versioning, doesn't scale to 9 realm pages.

## Decision Framework

```
Is this a project ECOSYSTEM (multiple components, showcase)?
  → YES: Docusaurus
  → NO: Is this primarily DOCUMENTATION?
      → YES: MkDocs Material
      → NO: Do you need MAXIMUM CREATIVE CONTROL?
          → YES: Astro
          → NO: Just the Docs (for simple docs) or Plain HTML (for minimal sites)
```

## Migration from Plain HTML

If migrating an existing plain HTML/CSS site (like Yggdrasil's current website/):

1. **Preserve the visual identity** — extract CSS custom properties, color palette, fonts
2. **Map pages to sections** — each realm becomes a nav section or docs page
3. **Keep it incremental** — start with a single section, verify build, expand
4. **Don't duplicate** — the SSG renders from Markdown, not from maintaining parallel HTML files
5. **Use Mermaid for architecture** — replace ASCII diagrams with Mermaid code blocks
6. **GitHub Actions deploy** — push to main triggers build + deploy to gh-pages

## Key Insight: Norse Theme Customization

For a Norse/dark-fantasy themed project:
- **Docusaurus**: CSS variables (`--ifm-color-primary: #f59e0b`, etc.) + custom components with rune/amber aesthetics
- **MkDocs Material**: `color_scheme: slate` + custom palette override in `mkdocs.yml`
- **Astro**: Full control — replicate the exact current aesthetic, then enhance with components
- **Just the Docs**: SCSS override `_sass/color_schemes/norse.scss` based on dark scheme