---
name: github-pages-project-site
title: Build a GitHub Pages Project Website
description: Create a multi-page static website for a project based on a reference design repo. Extracts project structure, maps it to visual design, and sets up GitHub Pages deployment.
trigger: When the user wants to create a GitHub Pages website for their project, inspired by a reference repo like Aether-Agents.
---

# Build a GitHub Pages Project Website

## Goal
Transform an existing project into a polished, multi-page static site hosted on GitHub Pages, using a reference repository for visual/structural inspiration.

## Prerequisites
- A reference repo URL (e.g. Aether-Agents style) to study
- The user's project files to extract content from
- GitHub account for deployment

## Steps

### 0. Enable GitHub Pages (Programmatic)

Instead of manually clicking in GitHub Settings, activate Pages via the REST API immediately after creating the repo:

```bash
# Requires GITHUB_TOKEN with repo scope
curl -s -X POST \
  -H "Authorization: token $GITHUB_TOKEN" \
  -H "Accept: application/vnd.github.v3+json" \
  -d '{"build_type":"workflow","source":{"branch":"main","path":"/"}}' \
  https://api.github.com/repos/$OWNER/$REPO/pages
```

Response will include `html_url` (e.g. `https://username.github.io/repo/`). If Pages was already enabled, this returns 409 — safe to ignore.

**Why this matters:** GitHub Pages with `build_type: workflow` uses the GitHub Actions workflow (Step 7) instead of branch-based deployment. This is cleaner for sites built from a `website/` directory.

### 1. Study the Reference Repo
- Navigate to the reference repo's `website/` directory and `README.md`
- Download raw files with `curl` to inspect HTML structure, CSS patterns, and page organization
- Identify:
  - Color palette and typography (dark theme conventions)
  - Page structure (landing, docs, setup, architecture)
  - Navigation patterns
  - Card/component patterns for displaying project features

### 2. Extract Project Content
- Read the project's main documentation files (`README.md`, rules files, architecture docs)
- Map project concepts to visual sections (e.g. Norse realms → color-coded cards)
- Identify components to showcase: features, architecture, setup instructions, status tables

### 3. Design the Site Structure
Create this standard layout under `website/`:
```
website/
  index.html          # Landing: hero, overview, features, status
  architecture.html   # System design, data flow, component relationships
  setup.html          # Installation guide, troubleshooting
  [topic].html        # Additional pages as needed
  css/style.css       # Complete dark theme with CSS variables
  js/main.js          # Copy-to-clipboard, mobile nav, scroll animations
  assets/images/      # Static assets
```

### 4. Build the CSS Foundation
- Use CSS custom properties for theming:
  - `--bg-primary`, `--bg-secondary`, `--bg-card`
  - `--text-primary`, `--text-secondary`, `--text-dim`
  - Accent colors mapped to project concepts (each component/realm gets a color)
  - `--font-sans` (Inter) and `--font-mono` (JetBrains Mono)
- Include: navbar with blur backdrop, hero gradient, cards grid, code blocks, tables, footer
- Make it fully responsive with mobile hamburger menu

### 5. Create HTML Pages
For each page include:
- Consistent navigation with active state highlighting
- Hero section with badge, headline, subtitle, install snippet
- Content sections with `.section-label`, `h2`, `.section-desc` pattern
- Copy-to-clipboard buttons on all code snippets
- IntersectionObserver fade-in animations on cards/features

### 6. Write a Spectacular README.md
- Centered header with emoji, tagline, and badges
- Quick start installation block
- ASCII architecture diagram
- Feature comparison table
- Hardware requirements table
- Links to the live GitHub Pages site

### 7. Set Up GitHub Actions
Create `.github/workflows/pages.yml`:
- Trigger on push to main/master
- Use `actions/configure-pages@v5`
- Use `actions/upload-pages-artifact@v3` with `path: './website'`
- Use `actions/deploy-pages@v4`

### 8. Finalize
- Replace all `YOUR_USERNAME` placeholders with actual GitHub username
- Verify file structure with `find` and `wc`
- Remind user to enable GitHub Pages in Settings > Pages > GitHub Actions

## Key Conventions
- **No external JS frameworks** — pure HTML/CSS/JS for zero dependencies
- **Dark theme first** — use `rgba()` borders and subtle gradients
- **Color mapping** — assign a unique accent color to each major project component/realm
- **Mobile-first responsive** — hamburger nav, stacked cards, full-width tables
- **No private info** — never include tokens, keys, or personal data in the website

## SSG Migration Considerations

If the project site needs more than plain HTML (search, Mermaid diagrams, component reuse, versioning, mobile optimization), consider migrating to a Static Site Generator:

- **Docusaurus** — Best for project ecosystems. MDX, Showcase feature, versioning, React components.
- **MkDocs Material** — Best for documentation-heavy sites. Fastest path to polished dark theme (`slate` scheme).
- **Astro** — Best for maximum creative control. Island architecture, zero JS, any UI framework.

See `references/ssg-comparison.md` for full decision matrix with setup difficulty, feature comparison, and migration path. When migrating from plain HTML, extract CSS variables and color palette first, then build incrementally.

For the broader GitHub presence (Topics, community health files, badges, social preview, Discussions, profile README), see the `github-presence-optimization` skill.

## Docusaurus Migration Workflow

When migrating from plain HTML to Docusaurus, follow this sequence:

1. **Scaffold**: `npx create-docusaurus@latest website-v2 classic --skip-install --javascript`
2. **Install**: `npm install` (if `html-minifier-terser` errors, `rm -rf node_modules package-lock.json && npm install`)
3. **Clean boilerplate**: Remove `blog/`, `src/pages/markdown-page.mdx`, `static/img/undraw_*.svg`, `static/img/docusaurus.png`, `static/img/docusaurus-social-card.jpg`
4. **Configure** `docusaurus.config.js` — see `references/docusaurus-setup.md` for full template with Norse dark theme
5. **Write MDX docs** — one file per section, frontmatter with quoted `description` strings only
6. **Create landing page** — `src/pages/index.js` with realm/feature cards
7. **Custom CSS** — `src/css/custom.css` with realm color variables
8. **Copy assets** — SVGs, favicons to `static/img/`
9. **Build & test**: `npx docusaurus build` — must pass zero errors before commit
10. **Deploy workflow**: `.github/workflows/deploy-website.yml` with `working-directory: website-v2`
11. **GitHub Pages**: Set repo Settings > Pages > Source to **"GitHub Actions"** (not "Deploy from branch")
12. **`.gitignore`**: Add `website-v2/build/` and `website-v2/.docusaurus/`

See `references/docusaurus-setup.md` for the complete configuration template and pitfall details.

## Reusable CSS Components

When expanding a multi-page site, these components are commonly needed:

- **Tab bar** (`.tab-bar` / `.tab-btn` / `.tab-content`) — interactive content switchers. Wire with JS: on click, swap `.active` class between tabs and show matching `#id` content panel. Add `data-tab` attribute to buttons.
- **Timeline** (`.timeline` / `.timeline-item`) — vertical timeline with gradient line. Uses `::before` pseudo-element for the connecting line and dot markers.
- **Status badges** (`.status-badge.active / .planned / .deprecated / .experimental`) — pill labels for project component status. Color-coded with rgba backgrounds and borders.
- **404 page** — themed error page with navigation links back to key pages. Use the same nav component as other pages.

## Accessibility & Performance

Every dark-theme site should include:
- `@media (prefers-reduced-motion: reduce)` — disable all animations, hide particle canvases
- `:focus-visible` styles for keyboard navigation (outline with accent color)
- **Visibility-based canvas pause**: `document.addEventListener('visibilitychange', ...)` to stop `requestAnimationFrame` when tab is hidden
- **Reduced motion check on load**: `window.matchMedia('(prefers-reduced-motion: reduce)').matches` — hide #particles-canvas entirely
- **SEO**: `sitemap.xml` (list all pages with `<lastmod>` and `<priority>`) + `robots.txt` pointing to the sitemap URL

## Pitfalls
- Raw GitHub files may not render in browser snapshots; use `curl` to inspect
- Remember to update all hardcoded GitHub URLs before deployment
- GitHub Pages needs the workflow source set to "GitHub Actions" in repo settings
- Keep the website under `website/` folder so the root README stays clean
- Plain HTML doesn't scale — if the site grows past ~5 pages or needs search/diagrams, migrate to Docusaurus or MkDocs Material
- **Never use `querySelector` with pseudo-elements** — `querySelector('.section::before')` returns null. Pseudo-elements are CSS-only constructs; use IntersectionObserver on the parent element instead and toggle CSS custom properties (e.g. `--section-visible: 1`)
- **Add new pages to ALL navigation bars** — when creating a new page, update the `<nav>` in every existing `.html` file, not just the new one. Use a systematic find-and-replace or loop over all HTML files.
- **Large files block commits** — pre-commit `check-added-large-files` rejects anything over 1MB by default. Add generated images, archives, and binary outputs to `.gitignore` before committing. If you need to track large assets, use Git LFS.
- **Black formatter can timeout** — on first run in a large repo, `black` may take 30+ seconds. Use `git commit` with a timeout of at least 120 seconds, or skip hooks with `--no-verify` if CI will catch formatting issues.
- **Docusaurus YAML frontmatter breaks with unquoted special chars** — descriptions containing `—` (em-dash), `:`, or `#` WILL cause build failures in `.mdx` frontmatter. Always wrap `description:` in double quotes. Example: `description: "Short description without special chars"` NOT `description: A long — description: with colons.`
- **Docusaurus `slug: /` on intro.mdx causes broken links** — if you have a React landing page (`src/pages/index.js`), do NOT set `slug: /` on `docs/intro.mdx`. It creates conflicting routes. Let intro default to `/docs/intro`.
- **Docusaurus `onBrokenMarkdownLinks` deprecated** — in v3.10+, use `markdown.hooks.onBrokenMarkdownLinks: 'warn'` instead of the top-level `onBrokenMarkdownLinks` config key, or you get a build warning.
- **html-minifier-terser MODULE_NOT_FOUND** — Docusaurus 3.10.1 may fail on first build with this error. Fix: `rm -rf node_modules package-lock.json && npm install` (clean reinstall resolves dependency tree).
- **Remove Docusaurus boilerplate before commit** — delete `blog/`, `src/pages/markdown-page.mdx`, `static/img/undraw_*.svg`, `static/img/docusaurus.png`, `static/img/docusaurus-social-card.jpg` before committing. These are 200+ KB of unused assets.
- **Delete old Pages workflow when migrating to Docusaurus** — When replacing a static HTML site (`website/`) with Docusaurus (`website-v2/`), the old `pages.yml` that deploys `./website` MUST be deleted. Both workflows typically use `concurrency: group: "pages"` and will silently fight over the deployment slot — only one can win, and the loser either fails or deploys stale content. Keep ONLY the new `deploy-website.yml` that builds `website-v2/` and deploys `website-v2/build`. Also remove the old `website/` directory from git tracking if Docusaurus is the canonical source.
- **GitHub Pages must use "GitHub Actions" source** — for Docusaurus deploy, go to repo Settings > Pages > Source and select "GitHub Actions" instead of "Deploy from a branch". The deploy-pages action won't work with branch-based deployment.
- **Docusaurus `baseUrl` must match repo name** — for a repo at `github.com/User/MyRepo`, set `baseUrl: '/MyRepo/'` in `docusaurus.config.js`. Mismatch causes 404s on deploy.
- **Docusaurus static path: `/img/` NOT `/static/img/`** — Files placed in `static/img/` are served at `/img/` in production. Docusaurus copies the *contents* of `static/` to the build root, stripping the `static/` prefix. In React components (`src/pages/index.js`), use `src="/MyRepo/img/logo.svg"` — NEVER `src="/MyRepo/static/img/logo.svg"`. The latter works in dev (`docusaurus start`) because the dev server serves `static/` directly, but **breaks in production builds** where the `static/` prefix doesn't exist. This is the #1 cause of "works locally, broken on deploy" bugs in Docusaurus sites.
- **Nav update shorthand** — Use a systematic approach: define `old_nav` (existing links) and `new_nav` (with added links) strings, then iterate over all HTML files with `patch()` replacing old → new. This avoids missing pages.
- **Docusaurus `npm run deploy` requires gh-pages branch to already exist** — If the remote has no `gh-pages` branch yet, deploy fails with `fatal: Remote branch gh-pages not found in upstream origin`. Fix: create it via a temp clone (`git clone --depth=1`, `git checkout --orphan gh-pages`, `git rm -rf .`, empty commit, `git push origin gh-pages`), then re-run `npm run deploy`. Alternatively, use a GitHub Actions workflow that creates the branch automatically.
- **Docusaurus `npm run deploy` requires global git identity** — The deploy command does a `git commit` in a temp checkout. If `git config --global user.name/email` is not set, it fails with `fatal: empty ident name not allowed`. Always set these before deploying: `git config --global user.name "Your Name" && git config --global user.email "you@example.com"`. This was the #1 deploy blocker in practice.
- **Docusaurus stale cache serves old content** — After editing `.mdx` files, the build cache (`build/`, `.docusaurus/`, `node_modules/.cache`) may contain outdated HTML. If deployed content doesn't match your source edits, run `rm -rf build .docusaurus node_modules/.cache` then `npm run build` before deploying. This is especially common after a failed deploy attempt where the old build artifacts persist.
- **`git checkout --orphan gh-pages` + `git rm -rf .` destroys uncommitted changes** — Creating an orphan branch and removing all files will wipe your working tree. If you have uncommitted patches (e.g. `.mdx` edits), they will be lost. Always `git add && git commit` your changes BEFORE attempting any orphan branch operations. If you accidentally lose changes, re-apply from your edit history or re-patch.

## Themed SVG Assets for Visual Identity

Custom SVGs dramatically elevate a static project site beyond "template" feel. Create
a consistent icon set mapped to your project's concepts (realms, modules, features).

### Asset Types

| Type | Size | Purpose |
|------|------|---------|
| Section/realm icons | 64×64px viewBox | Replace emoji in cards, feature grids, status tables |
| Hero banner | 960×400px viewBox | Landing page hero image (tree, architecture, landscape) |
| Logo | Height 32-40px | Navbar brand mark |
| Favicon | 32×32px viewBox | Browser tab icon |
| Agent/persona avatars | 120×120px viewBox | Architecture diagrams, team sections |

### SVG Design Pattern (Dark Theme)

Each icon follows the same structure for visual cohesion:

```svg
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 64 64">
  <!-- Background circle -->
  <circle cx="32" cy="32" r="28" fill="rgba(XX,XX,XX,0.15)"
          stroke="rgba(XX,XX,XX,0.6)" stroke-width="1"/>
  <!-- Central symbol (rune, icon, glyph) -->
  <path d="..." fill="#XXXXXX" opacity="0.9"/>
  <!-- Optional: subtle glow on hover (handled via CSS) -->
</svg>
```

### Color Mapping

Assign each major project concept a color. Use CSS variables so icons inherit
the theme automatically:

```css
.realm-icon-svg { width: 64px; height: 64px; transition: all 0.3s ease; }
.realm-icon-svg:hover { transform: scale(1.15); filter: brightness(1.3) drop-shadow(0 0 8px var(--accent)); }
```

### Integration into HTML

Replace static emoji with `<img>` tags pointing to SVG files:

```html
<!-- Before -->
<span class="realm-icon">🏰</span>

<!-- After -->
<img src="assets/images/realm-asgard.svg" alt="Asgard" class="realm-icon-svg">
```

### Integration Checklist

- [ ] Create SVG directory: `website/assets/images/`
- [ ] Design 1 SVG per major section/feature/realm
- [ ] Add hero banner SVG to landing page
- [ ] Add logo SVG to navbar
- [ ] Replace favicon.ico with favicon.svg (or both for compat)
- [ ] Add CSS for `.realm-icon-svg` with hover effects
- [ ] Add CSS for `.hero-banner` with responsive sizing
- [ ] Add CSS for `.logo-svg` with fixed height
- [ ] Verify SVGs render at all viewport sizes (mobile + desktop)
- [ ] Run accessibility check: every `<img>` has meaningful `alt` text

### Workflow Tips

- **Inline vs file reference**: Use `<img src="...">` for reusable icons (easier to
  update one file). Use inline `<svg>` only when you need CSS-animated parts.
- **SVGs are small**: A 64×64 icon with a circle + path is ~300 bytes. Hero banners
  ~2KB. No performance concern — skip sprite sheets for sites with <20 icons.
- **Gradients in SVG**: Use `<linearGradient>` with `id` scoped to each SVG file.
  Avoid global gradient IDs that collide when multiple SVGs appear on one page.
- **Dark theme**: Use semi-transparent fills (`rgba(R,G,B,0.15)`) for backgrounds
  and bright fills (`#hex`) for symbols. This creates depth withouthard edges.

## Visual Overhaul Pattern

When doing a major visual redesign of an existing site (not creating from scratch):

1. **Read all current files first** (HTML, CSS, JS) to understand the full current state
2. **Delegate to subagents** with complete file contents in context — don't make the subagent read files, pass them inline. This avoids context wasted on re-reading
3. **Provide explicit "must preserve" lists** — element IDs, class names, onclick handlers, global JS functions, API endpoints. The #1 risk in visual overhauls is breaking JS wiring
4. **Parallelize** — Website and Dashboard overhauls can run simultaneously via `delegate_task`
5. **Test after** — run the project's test suite to verify no functionality broke
6. **Git commit flow** — pre-commit hooks (trailing whitespace, end-of-file fixes) will modify files, requiring `git add -A && git commit` again. Don't be surprised by this
7. **Hard refresh** — After deploying to GitHub Pages, users may need Ctrl+Shift+R to bust the browser cache