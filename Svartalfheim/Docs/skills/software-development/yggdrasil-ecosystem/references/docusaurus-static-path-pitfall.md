# Docusaurus Static Path Pitfall

## The Bug

When referencing static assets (images, SVGs, etc.) in Docusaurus React components (`src/pages/index.js`, custom components), the path must NOT include the `static/` prefix.

**WRONG (works in dev, breaks in production):**
```jsx
<img src="/Yggdrasil/static/img/realm-asgard.svg" />
<img src="/Yggdrasil/static/img/logo-yggdrasil.svg" />
```

**CORRECT (works everywhere):**
```jsx
<img src="/Yggdrasil/img/realm-asgard.svg" />
<img src="/Yggdrasil/img/logo-yggdrasil.svg" />
```

## Why

Docusaurus copies the **contents** of `static/` to the build root. So a file at `static/img/realm-asgard.svg` ends up at `build/img/realm-asgard.svg` — the `static/` prefix is stripped.

In development mode (`docusaurus start`), the dev server serves `static/` directly, so both `/static/img/X` and `/img/X` work. This masks the bug until deploy.

## How to Detect

After building and deploying a Docusaurus site, check for broken images. The URL that returns 404 will typically contain `/static/img/` — that's this bug.

## Fix Pattern

Search all React/JS files in `src/` for `static/img` references:

```bash
grep -rn 'static/img' website-v2/src/
```

Replace all occurrences with the correct path (remove `static/` from the URL).

## When This Matters

- Any `<img>` tag in `src/pages/index.js` or custom components
- Any `require()` or `import` of static assets from JS
- CSS `url()` references in `src/css/` that point to static assets — these actually DO use the `static/` path in source but get rewritten by Docusaurus build, so they're fine

## Session Reference

This bug was found and fixed in the Yggdrasil website-v2 deployment (May 2026). The Docusaurus site built and deployed successfully, but all realm card SVGs and the hero logo were broken (404) because `src/pages/index.js` used `/Yggdrasil/static/img/` paths. Fixed by removing `static/` from all image `src` attributes. Commit: `b9507d4`.