# Yggdrasil GitHub Pages Website (FASE 11) — Reference

## File Structure

```
Yggdrasil/                              # Root repo (separate from Hermes-Lilith)
  .github/workflows/
    deploy-website.yml                  # GitHub Actions: auto-deploy on push to main
  website/
    CNAME                               # yggdrasil.brierainz.dev
    index.html                          # Home page — hero, features, ecosystem health
    realms.html                         # Nine realms overview
    hermes-lilith.html                  # Lilith product page — architecture, commands, gateway
    architecture.html                   # Tech architecture — request lifecycle, component diagram
    setup.html                          # Setup guide — install, config, first run
    changelog.html                      # Version history — releases, timeline, security model
    css/
      style.css                         # 2148 lines — dark fantasy/Norse/Lovecraftian theme
    js/
      main.js                           # 626 lines — animations, navigation, theme switch
    assets/
      images/                           # Site images (currently empty)
```

## Design System

- **Fonts:** Inter (body) + JetBrains Mono (code)
- **Colors:** Dark theme with purple/gold accents (`#0B0F19` bg, `#D4AF37` gold, `#8B5CF6` purple)
- **Icons:** Runic characters (ᚱ ᛏ ᚻ ᛖ ᛉ ᛗ) for section markers
- **Animations:** Loading tree SVG, card hover glow effects, fade-in transitions
- **Meta:** OpenGraph tags, Twitter cards, canonical URL, theme-color

## GitHub Actions Deploy

```yaml
# .github/workflows/deploy-website.yml
on:
  push:
    branches: [main]
    paths:
      - 'website/**'
      - '.github/workflows/deploy-website.yml'
  workflow_dispatch:
```

Uses `actions/configure-pages@v4`, `actions/upload-pages-artifact@v3`, `actions/deploy-pages@v4`.

## Update Checklist

When adding features to Lilith that affect the website:
1. Update `hermes-lilith.html` if new CLI commands, architecture changes, or component additions
2. Update `index.html` if new top-level features or ecosystem health changes
3. Update `architecture.html` if request lifecycle or component relationships change
4. Update `changelog.html` for every release
5. Ensure all 6 pages have consistent navigation (add new page links to all nav bars)
6. No build step — just push to main and GitHub Actions deploys automatically

## URLs

- Website: https://brierainz.github.io/Yggdrasil/ (or https://yggdrasil.brierainz.dev)
- GitHub: https://github.com/BrierAinz/Yggdrasil