# Website Conventions (GitHub Pages)

## Active Site: website-v2/ (Docusaurus)

The **canonical** website is `website-v2/` (Docusaurus v3.10.1), deployed via `.github/workflows/deploy-website.yml`. The old `website/` (static HTML) still exists on disk but is no longer deployed — its workflow (`pages.yml`) was deleted May 2026 to avoid concurrency conflicts.

### Docusaurus Structure

```
website-v2/
├── docusaurus.config.js     # Norse dark theme, Inter + JetBrains Mono, baseUrl: '/Yggdrasil/'
├── sidebars.js              # Auto-generated from docs/
├── src/
│   ├── css/custom.css       # Realm color variables, dark fantasy theme (~350 lines)
│   ├── pages/index.js       # React landing page with realm cards
│   └── components/          # HomepageFeatures component
├── docs/                    # 6 MDX pages (sidebar_position frontmatter)
│   ├── intro.mdx            # Overview (1)
│   ├── architecture.mdx     # System design (2)
│   ├── setup.mdx            # Installation (3)
│   ├── lilith.mdx           # Agent docs (4)
│   ├── changelog.mdx        # Release history (5)
│   └── apps.mdx             # Midgard apps (6)
├── static/img/              # Realm + agent SVGs, logo, favicon, hero banner
└── package.json
```

### Docusaurus Frontmatter Rules

- ALWAYS quote `description` strings — em-dashes (`—`), colons (`:`), and `#` break YAML parsing
- Use `description: "Short description"` NOT `description: A long — description: with colons.`
- NEVER use `slug: /` on `docs/intro.mdx` when there's a React landing page — it causes broken link conflicts
- Use `markdown.hooks.onBrokenMarkdownLinks: 'warn'` (not the deprecated top-level `onBrokenMarkdownLinks`)

### Content Update Pattern

When adding new projects, updating versions, or changing documentation:

1. **Version bumps**: Search all `.mdx` files for the old version string (e.g. `v4.0`) and replace with the new version. Check `description` frontmatter too.
2. **New projects**: Add to the agents table in `intro.mdx`, ecosystem health table in `intro.mdx`, and add a changelog entry in `changelog.mdx`.
3. **Test count and spec updates**: Search for hardcoded numbers (test counts, GPU specs, etc.) in docs — they get stale fast.
4. **Build verification**: Always run `npx docusaurus build` after content changes. Zero errors required before commit.
5. **Realm assignments**: When a project moves realms (e.g. Dashboard from Midgard to Alfheim), update all table entries consistently.

### Docusaurus Concurrency Fix (Critical)

When migrating from static HTML (`website/` + `pages.yml`) to Docusaurus (`website-v2/` + `deploy-website.yml`):

- **DELETE the old `pages.yml`** — Both workflows use `concurrency: group: "pages"` and will silently fight over the deployment slot. Only the new workflow should exist.
- **GitHub Pages source must be "GitHub Actions"** — Go to repo Settings > Pages > Source > select "GitHub Actions" (not "Deploy from a branch"). This is a manual step; it cannot be done via `gh` CLI without authentication.
- **baseUrl must match repo name** — For `github.com/BrierAinz/Yggdrasil`, set `baseUrl: '/Yggdrasil/'` in `docusaurus.config.js`.

### Theme: Norse Dark Fantasy

CSS variables in `src/css/custom.css`:
- Background: `#1a1b26` (dark), `#16161e` (navbar), `#0f0f14` (footer)
- Accent: `#c8a23e` (gold, primary)
- Realm colors each have a CSS class (`.realm-asgard`, `.realm-vanaheim`, etc.)
- Fonts: Inter (body) + JetBrains Mono (code)
- Cards, tables, code blocks, admonitions all themed
- Responsive with `@media (max-width: 768px)` breakpoint

### Build & Deploy

```bash
cd website-v2
npx docusaurus build    # Must complete with zero errors
npx docusaurus serve    # Preview at localhost:3000
```

Deploy workflow triggers on push to `main` when `website-v2/**` or `.github/workflows/deploy-website.yml` changes. Also has `workflow_dispatch` for manual triggers.

---

## Legacy: website/ (Static HTML, NOT Deployed)

Below is the reference for the old static HTML site. It is kept on disk for reference but is **no longer deployed**.

### File Structure

```
website/
├── index.html              # Main landing page (9 realms, agent gallery, status)
├── architecture.html       # System architecture diagram
├── hermes-lilith.html      # Lilith agent deep-dive (URL preserved, visible name "Lilith")
├── realms.html             # 9 realms detail page
├── setup.html              # Setup/install guide
├── vanaheim-agents.html    # Vanaheim agent framework
├── midgard-apps.html        # Midgard personal apps
├── changelog.html           # Version changelog
├── 404.html                # Custom dark fantasy 404
├── css/style.css            # ~56KB, 2400+ lines, CSS custom properties
├── js/main.js               # Particles, scroll animations, cursor trail, tabs
├── assets/images/
│   ├── agent-{name}.svg     # 9 agent icons (Lilith, Eir, ForgeMaster, etc.)
│   ├── realm-{name}.svg     # 9 realm icons (Asgard through Helheim)
│   ├── hero-yggdrasil.svg   # Hero banner tree
│   ├── favicon.svg          # Rune circle favicon
│   └── logo.svg             # Nav logo
├── sitemap.xml
└── robots.txt
```

### CSS Architecture (Legacy)

- All colors via CSS custom properties in `:root` (dark fantasy palette)
- Key classes: `.agent-card`, `.agent-card-image`, `.agent-card-name`, `.agent-grid`, `.realm-icon-svg`, `.lilith-node`, `.status-badge`
- Responsive grid: `repeat(auto-fill, minmax(200px, 1fr))` for agent cards
- Mobile break at 640px: 2-column grid, smaller images

### Visible Text vs File Paths (Critical, Legacy)

The agent was originally named "Hermes-Lilith" and the directory/file remain `Asgard/Hermes-Lilith/` and `hermes-lilith.html`. **Do NOT rename these** — it would break all git history and internal links. Only change **visible UI text** to "Lilith". This means:

- In HTML: replace "Hermes-Lilith" in headings, descriptions, nav links, status badges
- Preserve: `href="hermes-lilith.html"`, `cd Asgard/Hermes-Lilith`, `HERMES_PATH=`, `data-copy` attributes, any actual filesystem path or command
- CSS class `.hermes-node` was renamed to `.lilith-node` (3 HTML files + CSS)
- Version references: update in visible descriptions only (changelog/history stays as-is)

### Agent SVG Pattern

Each agent SVG uses:
- viewBox="0 0 200 200"
- Dark background circle with realm accent color
- Rune + archetype symbol theme (e.g., Lilith = CLI terminal, Eir = paintbrush + Eihwaz rune)
- Subtle glow/gradient effects
- Filename: `agent-{lowercasename}.svg`

Agent SVGs are **temporary placeholders** — they will be replaced with ComfyUI-generated images once the Eir LoRA is fully trained. Keep the same filenames and dimensions when replacing.