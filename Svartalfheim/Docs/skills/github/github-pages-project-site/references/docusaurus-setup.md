# Docusaurus Setup Reference

Step-by-step reference for setting up a Docusaurus v3 site with a dark Norse theme, tested with v3.10.1.

## Scaffold Commands

```bash
npx create-docusaurus@latest website-v2 classic --skip-install --javascript
cd website-v2
npm install  # if html-minifier-terser error: rm -rf node_modules package-lock.json && npm install
```

## docusaurus.config.js Template (Norse Dark Theme)

```js
// @ts-check
import {themes as prismThemes} from 'prism-react-renderer';

const config = {
  title: 'ProjectName',
  tagline: 'Tagline here',
  favicon: 'img/favicon.svg',
  future: { v4: true },
  url: 'https://USERNAME.github.io',
  baseUrl: '/RepoName/',           // MUST match repo name with trailing slash

  organizationName: 'USERNAME',
  projectName: 'RepoName',

  onBrokenLinks: 'throw',
  markdown: {                       // NOT top-level onBrokenMarkdownLinks (deprecated)
    hooks: { onBrokenMarkdownLinks: 'warn' },
  },

  i18n: { defaultLocale: 'en', locales: ['en'] },

  presets: [
    [
      'classic',
      ({
        docs: {
          sidebarPath: './sidebars.js',
          editUrl: 'https://github.com/USERNAME/RepoName/tree/main/website-v2/',
        },
        blog: false,                // Disable blog unless needed
        theme: { customCss: './src/css/custom.css' },
      }),
    ],
  ],

  themeConfig: ({
    image: 'img/hero-banner.svg',
    colorMode: { defaultMode: 'dark', respectPrefersColorScheme: true },
    navbar: {
      title: 'ProjectName',
      logo: { alt: 'Logo', src: 'img/logo.svg' },
      items: [
        { type: 'docSidebar', sidebarId: 'docs', position: 'left', label: 'Docs' },
        { href: 'https://github.com/USERNAME/RepoName', label: 'GitHub', position: 'right' },
      ],
    },
    footer: { /* ... */ },
    prism: {
      theme: prismThemes.github,
      darkTheme: prismThemes.dracula,
      additionalLanguages: ['python', 'bash', 'yaml', 'ini'],
    },
    announcementBar: {
      id: 'announcement',
      content: 'Announcement text here',
      backgroundColor: '#1a1b26',
      textColor: '#c8a23e',
      isCloseable: true,
    },
  }),
};

export default config;
```

## MDX Frontmatter Rules

ALWAYS quote descriptions — unquoted strings with `—`, `:`, or `#` will break the YAML parser:

```mdx
---
sidebar_position: 1
title: Page Title
description: "Short description without em-dashes or colons"
---
```

WRONG (will break build):
```mdx
---
description: A long description — with em-dash: and colons.
---
```

## GitHub Actions Deploy Workflow

`.github/workflows/deploy-website.yml`:

```yaml
name: Deploy Docusaurus to GitHub Pages
on:
  push:
    branches: [main]
    paths: ['website-v2/**', '.github/workflows/deploy-website.yml']
  workflow_dispatch:

permissions:
  contents: read
  pages: write
  id-token: write

concurrency:
  group: "pages"
  cancel-in-progress: false

jobs:
  deploy:
    environment:
      name: github-pages
      url: ${{ steps.deployment.outputs.page_url }}
    runs-on: ubuntu-latest
    defaults:
      run:
        working-directory: website-v2
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
        with:
          node-version: 22
          cache: npm
          cache-dependency-path: website-v2/package-lock.json
      - run: npm ci
      - run: npm run build
      - uses: actions/configure-pages@v5
      - uses: actions/upload-pages-artifact@v3
        with:
          path: website-v2/build
      - id: deployment
        uses: actions/deploy-pages@v4
```

## .gitignore Additions

```
website-v2/build/
website-v2/.docusaurus/
```

## Boilerplate Cleanup Checklist

After scaffolding, delete these unused files:

- [ ] `blog/` (entire directory)
- [ ] `src/pages/markdown-page.mdx`
- [ ] `static/img/undraw_*.svg` (3 default illustration SVGs)
- [ ] `static/img/docusaurus.png`
- [ ] `static/img/docusaurus-social-card.jpg`

## Build & Verify

```bash
cd website-v2
npx docusaurus build   # Must complete with SUCCESS and zero broken links
npx docusaurus serve    # Local preview at localhost:3000
```

## Critical: GitHub Pages Source

After first push, go to:
**Repo > Settings > Pages > Source > select "GitHub Actions"**

The default is "Deploy from a branch" which won't work with the deploy-pages action.

## Norse Dark Theme CSS Variables

Key variables for a dark Norse aesthetic in `src/css/custom.css`:

```css
:root {
  --ifm-color-primary: #c8a23e;        /* Gold/amber accent */
  --ifm-color-primary-dark: #b8922e;
  --ifm-color-primary-darker: #a8821e;
  --ifm-background-color: #1a1b26;     /* Dark base */
  --ifm-background-surface-color: #24283b; /* Card background */
  --ifm-font-family-base: 'Inter', system-ui, sans-serif;
  --ifm-font-family-monospace: 'JetBrains Mono', monospace;
}
[data-theme='dark'] {
  --ifm-background-color: #1a1b26;
  --ifm-background-surface-color: #24283b;
}
```

## Realm Color Palette (for cards/sections)

```
Asgard:     #c8a23e  (gold)
Vanaheim:   #7c3aed  (violet)
Alfheim:    #10b981  (emerald)
Svartalfheim: #6366f1 (indigo)
Muspelheim: #ef4444  (red)
Niflheim:   #06b6d4  (cyan)
Helheim:    #64748b  (slate)
Jotunheim:  #f97316  (orange)
Midgard:    #8b5cf6  (purple)
```