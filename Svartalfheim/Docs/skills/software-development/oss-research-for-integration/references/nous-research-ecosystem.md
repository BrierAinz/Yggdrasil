# Nous Research — Ecosystem Analysis (May 2026)

Comprehensive competitive analysis of nousresearch.com and all subdomains.
Purpose: design reference for BrierStudios and future dark-fantasy themed sites.

## Ecosystem Map

```
NOUS RESEARCH ECOSYSTEM
├── nousresearch.com              (WordPress + Elementor — Hub)
│   ├── /releases                 (Data table of models/papers/frameworks)
│   ├── /careers                  (7 open roles)
│   └── /blog                     (10+ research posts)
├── hermes-agent.nousresearch.com (Custom landing — Autonomous agent)
├── portal.nousresearch.com      (Custom SPA — API management dashboard)
├── psyche.network               (Custom SPA — Distributed training / Solana)
├── shop.nousresearch.com         (Shopify — Merch store)
├── sims.nousresearch.com         (Custom — Social simulators)
├── chat.nousresearch.com         (Custom SPA — Chat interface)
└── hermes4.nousresearch.com      (Offline/404 — was Hermes 4 landing)
```

## Per-Subdomain Breakdown

### 1. nousresearch.com (Main Hub)
- **Stack:** WordPress + Elementor Pro (Hello Elementor theme)
- **Style:** Cinematic/photographic hero backgrounds (jangs.jpg, shack.webp) with dark overlays
- **Layout:** 3 sections — LANGUAGE MODELS, COMMITMENT TO DEVELOPMENT, APPLIED AI RESEARCH
- **Design tokens:** Background images with `background_motion_fx` parallax (scale + translateY), `linear-gradient(to right, rgba(0,0,0,0.5) 60%, rgba(255,255,255,0) 0%)` overlays
- **Typography:** Times New Roman (serif base), uppercase section headers
- **Signature detail:** "SEED: <hash>" and "OUTPUT <number>" decorative text blocks as generative-art signatures
- **Nav:** HOME, HERMES AGENT, API PORTAL, PSYCHE, HERMES 4, RELEASES, CAREERS, SHOP, BLOG
- **Mobile:** Burger menu with popup overlay
- **No canvas/WebGL** — pure CSS + Elementor motion FX

### 2. hermes-agent.nousresearch.com (Product Landing)
- **Stack:** Custom static site (likely Next.js or Astro)
- **Style:** Ultra-minimalist, warm-toned dark default with light-mode toggle
- **Typography:** Mondwest (custom serif display font), monospace for code
- **Color palette:** Amber/warm (#ffe6cb on #041c1c dark teal-black)
- **Hero:** "THE AGENT THAT / GROWS WITH YOU." in massive serif type
- **Code blocks:** `curl -fssl https://hermes-agent.nousresearch.com/install.sh | bash` + `hermes setup`, each with Copy button
- **Terminal demo:** Screenshot/GIF of CLI in action
- **Features (6 cards):** Lives Where You Do, Grows The Longer It Runs, Scheduled Automations, Delegates & Parallelizes, Real Sandboxing, Full Web & Browser Control
- **Card style:** `border-current/20` (20% opacity borders), generous whitespace
- **Footer:** v0.13.0, MIT License 2026
- **Key takeaway for BrierStudios:** Copy buttons on code blocks, terminal demo GIF, dramatic serif type, dark/light toggle

### 3. portal.nousresearch.com (API Dashboard)
- **Stack:** Custom SPA (React/Next.js)
- **Style:** Clean dashboard with sidebar navigation
- **Sections:** Models, Products, API, Usage, Preferences, Chat, API Docs, Help
- **Function:** API key management, usage tracking, model catalog, direct chat
- **Requires login** for full access
- **Key takeaway:** Dashboard SPA pattern — sidebar nav, clean cards, auth-gated

### 4. psyche.network (Distributed Training)
- **Stack:** Custom SPA
- **Style:** Cyberpunk/blockchain aesthetic, Unicode gothic title (𝔫𝔬𝔲𝔰 𝔭𝔰𝛾𝔠𝔥𝔢)
- **Layout:** "DISTRIBUTED INTELLIGENCE NETWORK" + TESTNET badge + "CONTRIBUTE COMPUTE" CTA
- **Key feature:** Live leaderboard of compute contributors (Solana wallet addresses + contribution %)
- **Pool stats:** 100% capacity, Mining Pool $500,000.00
- **Tech:** Solana blockchain, DisTrO + DeMo (distributed training optimization)
- **Navigation:** GITHUB, FORUM, ABOUT PSYCHE, DOCS, LIGHT/DARK toggle
- **Key takeaway:** Gamified contribution leaderboards, wallet integration, status badges (TESTNET)

### 5. nousresearch.com/releases (Release Catalog)
- **Stack:** WordPress + Elementor + DataTables (sortable, searchable)
- **Columns:** #, Project Name, Type, Details, Release Date, Size
- **Types represented:** AGENT, MODEL, PAPER, RESEARCH, TRAINING, FRAMEWORK, DATASET, SIMULATOR
- **Notable releases:**
  - Hermes Agent (02/25/26)
  - NousCoder-14B (01/06/26, 29.6 GB)
  - Nomos 1 (12/09/25, 120 GB)
  - Hermes-4.3-Seed-36B (12/03/25, 72 GB — trained on Psyche network)
  - Hermes-4-Llama-3.1-405B (08/26/25, 802 GB)
  - Atropos RL Framework (04/29/25)
  - DeMo Paper (11/29/24)
- **Key takeaway:** Sortable release table with type badges, multiple content types

### 6. nousresearch.com/careers
- **Style:** Clean page with mission statement, team description ("distributed, weird, and small")
- **Expectations:** "chaos, long months of grinding, pivots, with breakthroughs in the event of setbacks"
- **7 open roles:** General Counsel, MLE General Training Infra, MLE RL Training Infra, MLE Pretraining Data, Data/Evals Engineer, Research Scientist, Security Engineer (Part Time)
- **Apply:** recruiting@nousresearch.com

### 7. shop.nousresearch.com (Merch)
- **Stack:** Shopify
- **Products (15):** HERMES SWEATER, HERMES AGENT SHIRT, SCAFFOLDING TEE, OPEN SOURCE TEE, GOOD TECHNOLOGY SWEATER, NOUS GIRL NEON, NOUS HERMES SHIRT, REBEL CREWNECK, SWEATS BUNDLE, BADGE SWEATPANTS, BADGE HOODIE, NOUS COMBO PACK (Sale), DECENTRALIZE T-SHIRT, NOUS-HAT, CAT T-SHIRT, FORGE DIVISION
- **Key takeaway:** Brand merch as community building — naming products after internal projects (Scaffolding, Forge Division)

### 8. sims.nousresearch.com (Social Simulators)
- **4 simulators:** WORLDSIM, GOD & S8N, DOOMSCROLL, TEE
- **Style:** Dark grid with image preview cards, click to expand details
- **Key takeaway:** Product grid for experimental/research products

### 9. chat.nousresearch.com (Chat UI)
- **Stack:** Custom SPA
- **Style:** ChatGPT-like interface running Hermes models
- **Features:** Notifications, model selection
- **Requires login**

### 10. nousresearch.com/blog
- **Recent posts (10+):**
  - Field Notes on Scaling MoE Expert Parallelism with DeepEP
  - NousCoder-14B: A Competitive Olympiad Programming Model
  - Introducing Hermes 4.3
  - Tinker-Atropos Integration
  - The Next Phase of Psyche
  - Measuring Thinking Efficiency in Reasoning Models
  - Steering the Shoggoth: Taming LLMs with Sequential Monte Carlo
  - Democratizing AI: The Psyche Network Architecture
  - Introducing Atropos
  - Forge Reasoning API Beta and Nous Chat

## Cross-Cutting Design Patterns

| Pattern | Implementation |
|---------|---------------|
| **Dark theme default** | All subdomains default to dark; most have light toggle |
| **Monospace/terminal accents** | Code blocks, SEED: hashes, wallet addresses |
| **Product naming = branding** | Hermes, Psyche, Atropos, Forge, DisTrO, DeMo — mythological naming |
| **Open source emphasis** | MIT license badges, "OPEN SOURCE" labels, model weights public |
| **Generative art signatures** | SEED/OUTPUT numbers on main site (like output hashes) |
| **Multi-product ecosystem** | Each product gets its own subdomain with distinct visual identity |
| **Typography variety** | Main site: serif/TNR. Hermes: Mondwest. Psyche: Gothic Unicode. Portal: clean sans |
| **Status badges** | TESTNET (Psyche), v0.13.0 (Hermes), MIT LICENSE |
| **Copy buttons** | Code blocks with one-click copy |
| **Community engagement** | Leaderboards, merch store, Discord/GitHub links everywhere |

## Design Takeaways for BrierStudios

1. **Copy buttons on code blocks** — essential for any install/quick-start section
2. **Terminal demo GIF** — show the Yggdrasil CLI in action
3. **Status badges** — version tags, license badges, realm status indicators
4. **Dark/light toggle** — frost-dark / frost-light mode swap
5. **Generative signatures** — could use rune-generation or seed-hashes as decorative elements
6. **Product grid** — 9 realms as product cards like sims.nousresearch.com
7. **Typographic hierarchy** — massive serif display for hero, clean sans for body
8. **Whitespace** — Hermes Agent uses generous vertical spacing between sections
9. **Merch naming** — use realm/project names for hypothetical merch (Asgard hoodie, etc.)