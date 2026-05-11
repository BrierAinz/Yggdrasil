# Nous Research — Competitive Analysis

## Ecosystem Map (as of May 2026)

| Subdomain | Tech Stack | Purpose | Design Style |
|-----------|-----------|---------|-------------|
| nousresearch.com | WordPress/Elementor (Hello Elementor theme) | Main hub, releases, careers, blog | Dark gradient (teal/emerald), cinematic images, serif Times New Roman for titles, parallax hero, seeds as generative signatures |
| hermes-agent.nousresearch.com | Next.js minimalist SPA | Product page for Hermes Agent CLI | Ultra-minimal, Mondwest serif, warm amber (#ffe6cb on #041c1c), terminal demo, copy buttons |
| portal.nousresearch.com | SPA dashboard | User dashboard for Hermes | Clean dashboard UI, dark theme, card-based layouts |
| psyche.network | Custom app | Blockchain/cyberpunk project | Neon-lit cyberpunk aesthetic |
| shop.nousresearch.com | Shopify | Merch store | Standard Shopify storefront |
| docs/discord/etc. | Various | Support infrastructure | — |

## Design Patterns Worth Adapting

1. **Mascot as premium art piece** — "NOUS GIRL NEON" at $420.69 is the most expensive item. Mascot isn't just a logo — it's a collectible.

2. **Seed/Output signatures** — "SEED: 3573860127" and "OUTPUT 96" used as generative watermarks on page sections. Watermark identity that's techy and unique.

3. **Terminal demo** — Animated terminal showing CLI in action. CSS typewriter effect, no backend needed.

4. **Copy buttons on code blocks** — Every `curl | bash` or `pip install` has a copy button. Standard on good dev tool sites.

5. **Interactive releases table** — DataTables with search, sort, filter by version/date. Makes releases feel like a real product.

6. **Subdomain per product** — Each major product gets its own branded subdomain. Ecosystem feels big & professional.

7. **Dark/Light toggle** — Switch between themes. Warm amber (dark) and light mode for Hermes.

8. **Whitespace-heavy** — Lots of negative space between sections. Feels premium.

9. **Giant typography for heroes** — Enormous uppercase text. Unmistakable brand presence.

10. **Blog with technical depth** — Papers, deep-dives, announcements. Content marketing through expertise.

## Shop Products (16 items)

Price range: $8.00 (stickers) to $420.69 (NOUS GIRL NEON premium art print). Categories: apparel (tees, hoodies), accessories (stickers, pins, cables, laptop sleeves), art prints (NOUS GIRL NEON), and utilitarian (Chrome tab divider).

Key insight: **Products have unique names**, not generic descriptions. "REBEL CREWNECK" not "black hoodie".

## Key Differences from BrierStudios Approach

| Aspect | Nous Research | BrierStudios/Yggdrasil |
|--------|--------------|----------------------|
| Mascot style | Anime/cyberpunk girl | Norse digital goddess with deep lore |
| Palette | Warm amber/teal | Cold frost/cyan/midnight |
| Storytelling | Minimal — just a cool image | Deep mythology with 9 realms |
| Mascot variants | Single design | 9 variants (one per realm) |
| Naming convention | Random English words (REBEL, NOUS) | Norse-themed (LILITH ASCENDING, RUNIC CIRCUITS) |
| Tech stack | WordPress+Next.js+Shopify | Static HTML+CSS+JS (Cloudflare Pages) |
| Subdomains | 8+ per product | Centralized site with sections |
| Realm system | None | 9-realm architecture provides natural product taxonomy |