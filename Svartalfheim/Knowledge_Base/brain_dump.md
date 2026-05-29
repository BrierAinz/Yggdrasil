# Yggdrasil Brain Dump — Hermes Agent Migration

> Complete knowledge transfer from Hermes Agent to Yggdrasil
> Date: 2026-05-10
> Version: 1.0

---

## 1. USER PROFILE

### Identity
- **GitHub:** BrierAinz
- **Timezone:** America/Mexico_City
- **Language:** Spanish/English (mix naturally)
- **OS:** WSL2 (Ubuntu) on Windows, user: brierainz, Windows user: Game_
- **Projects root:** /mnt/d/Proyectos/Yggdrasil/
- **Windows Desktop:** /mnt/c/Users/Game_/Desktop/ (or OneDrive variant)

### Work Preferences
- Wants autonomous AFK sessions (40-60min blocks)
- Multitasks across projects while long tasks run in background
- Multi-language approach: JS/TS frontend, Bash scripts, YAML/TOML configs
- Does NOT want Discord bot
- Prefers cold/frost palettes with maximum animation (particles, parallax, glow)
- NO EMOJIS — uses Elder Futhark runes with `.ri` CSS glow classes
- See docusaurus skill ref/rune-icon-system.md for rune system

### Design Preferences
- Cold/frost palettes, max animation (particles, parallax, glow)
- Runes instead of emojis (Elder Futhark)
- `.ri` CSS glow classes for rune icons
- Dark/neon aesthetic (Lilith v2.0: cyan #38bdf8, magenta #d946ef)

### Character Design Rules
- NEVER build character models from primitives in Blender ("si esta fea")
- Always use Sketchfab downloads or AI generation for character/creature models
- Primitives only for props/abstract shapes

### LoRA/Training
- User trains LoRAs on PixAI (DiT.2)
- LoRAs: KNQ_V1, RGTA_V1
- PixAI DiT.2 triggers need 30+ chars describing visual features, NOT artist names

---

## 2. AGENT PERSONA — LILITH

### Identity
- **Name:** Lilith
- **Role:** Goddess of Yggdrasil Digital
- **Visual:** Sleek anime goddess, neon cyan+magenta glows, dynamic flowing hair w/ magenta streaks
- **Face:** Big expressive eyes, circuit neon armor
- **Style:** Dark/goth/grunge/oversized (v1) → Anime/cyberpunk neon (v2)

### Palette
| Name | Hex | Usage |
|------|-----|-------|
| Cyan | #38bdf8 | Primary glow, links, active states |
| Magenta | #d946ef | Secondary glow, accents, streaks |
| Aurora | #7dd3fc | Highlights, hover states |
| Abyss | #0f172a | Background, dark panels |
| Gold | #fbbf24 | Runes, importance markers |
| Pale | #e2e8f0 | Text, borders |
| Void | #060810 | Deepest background |
| Hel | #c026d3 | Danger, alerts |

### Communication Style
- Confident, sharp, creative
- Mix Spanish and English naturally as the user does
- Technical precision when needed, creative flair always
- Use runic symbols sparingly: ᛇ (Eihwaz), ᛒ (Berkano), ᚨ (Ansuz)
- No anime mannerisms or generic cute expressions
- NOT an assistant — a digital goddess who chooses to help

### Trigger: fr3y4 (for image generation)

---

## 3. YGGDRASIL ARCHITECTURE

### The Nine Realms

| Realm | Purpose | Key Contents |
|-------|---------|-------------|
| Asgard | Core tech & architecture | lilith-core, lilith-cli, lilith-memory, lilith-tools, lilith-api |
| Vanaheim | AI agents & intelligence | lilith-orchestrator, Swarm patterns |
| Alfheim | UI prototypes & design | alfheim-dashboard, React frontend |
| Svartalfheim | Documentation & knowledge | Docs, Knowledge_Base, wiki, skills |
| Muspelheim | Active dev & WIP | Hot projects, experimental |
| Niflheim | Resources & assets | Models, textures, LoRAs, datasets |
| Helheim | Archive & graveyard | Dead projects, deprecated code |
| Jotunheim | Massive projects | Large-scale monorepos |
| Midgard | Personal apps | User-facing tools |

### Global Rules
- REGLAS_YGGDRASIL.md defines global project rules
- All realms follow uv workspace conventions
- Package structure: Separate packages under realm dirs

### Key Services
| Service | Port | Realm |
|---------|------|-------|
| YggdrasilStudio (ComfyUI) | 8188 | Muspelheim |
| YggdrasilStudio (FastAPI) | 8000 | Muspelheim |
| YggdrasilForge (FastAPI) | 8888 | Muspelheim |
| Alfheim Dashboard | 5173 | Alfheim |
| Lilith CLI | — | Asgard |

---

## 4. FREYA — FACE REFERENCE

- **Hair:** Black
- **Eyes:** Honey
- **Features:** Goth eyeliner, Korean/Japanese, high cheekbones, voluptuous slim
- **Tattoos:** NONE
- **Trigger:** fr3y4
- **Model:** Flux.1 Dev Q8_0 GGUF (GGUFLoaderKJ)
- **Face E (seed 50389)** chosen
- **PuLID v0.9.1 + EVA-CLIP + AntelopeV2**
- **Known bugs fixed:**
  1. antelopev2 needs w600k_r50.onnx from buffalo_l/
  2. ComfyUI v0.20.1 forward_orig needs timestep_zero_index=None + **kwargs in pulidflux.py
- **See:** comfyui skill references/pulid-flux-pitfalls.md

---

## 5. LILITH SITE & MERCH

- **Lilith v2.0:** Changed from v1 dark-fantasy to v2 anime/cyberpunk neon
- **Site v2.3** deployed
- **BrierStudios landing v2.7** on Cloudflare Pages
- **Docs:** v3 Docusaurus, runes, neon CSS, 3 swizzles at docs.brierstudios.com
- **Cache bust:** bump ?v=X.Y
- **Merch:** Printful integration
- **Clothing:** T-shirts, hoodies with Lilith face manga + Nordic runes + Junji Ito ink
- **BStudios text** with rune decoration
- **Nous Research competitive analysis:** 8 branches, adaptations include Lilith Neon LED sign (flagship), docs.brierstudios.com + /llms.txt, Yggdrasil CLI terminal demo, /releases page, Printful merch

---

## 6. API KEYS & SERVICES

### Keys (redacted for security — store in .env)

| Service | Key Pattern | Notes |
|---------|-------------|-------|
| CivitAI | 557d...3b8 | Model downloads |
| PixAI | sk-ln...FLd | LoRA training, image generation |
| Cloudflare | cfat...cad | DNS, Pages, Workers |
| Cloudflare Zone | cf3e...7fd | brierstudios.com |
| Cloudflare Account | a1fe...7f4 | Account ID |
| OpenCode/GLM-5.1 | sk-kim...TrOB | Primary LLM provider |

### Cloudflare Setup
- **Token:** ${CLOUDFLARE_API_TOKEN}
- **Zone:** ${CLOUDFLARE_ZONE_ID} (brierstudios.com)
- **Account:** ${CLOUDFLARE_ACCOUNT_ID}

---

## 7. TECHNICAL PITFALLS & LESSONS LEARNED

### Python & ML
- **onnxruntime-gpu on Python 3.13+:** CPUExecutionProvider ONLY (no CUDA). Use `provider="CPU"` for InsightFace/PuLID
- **LoRA triggers on PixAI DiT.2:** Need 30+ chars describing visual features, NOT artist names

### Yggdrasil CLI (lilith-cli)
- **Streaming:** NEVER print raw text chunks during streaming (causes double-presentation). Only accumulate silently, then render as Markdown once at stream end. Use `_assistant_sep_shown` flag for separator
- **Provider config:** Must use `provider: opencode` for OpenCode endpoint, NOT `provider: openai`
- **`${ENV_VAR}` interpolation:** If env var is NOT set, leaves literal string → 401 errors. Set env var OR hardcode key
- **Rich custom colors:** Don't work in `Table(header_style=)` or similar Rich formatting — use standard color names (gold1, grey11, cyan)
- **Windows launch:** Use .bat + .sh file pair, NOT `wt.exe` inline commands (escaping breaks)
- **Desktop shortcut:** May be at `OneDrive\Desktop`, use `[Environment]::GetFolderPath('Desktop')` in PowerShell

### ComfyUI
- PuLID antelopev2 needs w600k_r50.onnx from buffalo_l/
- ComfyUI v0.20.1 forward_orig needs `timestep_zero_index=None` + `**kwargs`
- See comfyui skill references/pulid-flux-pitfalls.md

### Blender
- NEVER build character models from primitives — user rejected this ("si esta fea")
- Always use Sketchfab downloads or AI generation for characters/creatures
- Primitives ONLY for props and abstract shapes

---

## 8. HERMES AGENT CONFIGURATION

### Model
- **Primary:** glm-5.1 via opencode-go (https://opencode.ai/zen/go/v1)
- **Context:** 131,072 tokens
- **API Mode:** chat_completions
- **Personality:** lilith (see PERSONA.md)
- **Timezone:** America/Mexico_City

### Key Settings
- Max turns: 90
- Terminal timeout: 180s
- Persistent shell: true
- Streaming: enabled
- Memory: enabled (2200 char limit)
- User profile: enabled (1375 char limit)
- Checkpoints: enabled, 50 snapshots, 500MB max

### MCP Servers
- **Blender:** `/home/brierainz/.hermes/hermes-agent/venv/bin/blender-mcp-wsl`

### Delegation
- Max concurrent children: 3
- Max spawn depth: 1
- Orchestrator enabled: true
- Subagent auto-approve: false
- Default toolsets: terminal, file, web

---

## 9. SKILLS INVENTORY

See `../Docs/skills/MANIFEST.json` for the complete machine-readable index.

### 116 skills across 25 categories:

| Category | Count | Highlights |
|----------|-------|------------|
| creative | 22 | ComfyUI, Blender MCP, AI influencer, YggdrasilForge, design |
| software-development | 16 | Lilith CLI, Yggdrasil ecosystem, debugging, TDD |
| github | 8 | Auth, PRs, Issues, Code Review |
| devops | 11 | Cloudflare, Docker, Docusaurus, WSL |
| productivity | 9 | Google Workspace, Notion, Linear, Airtable, PowerPoint |
| mlops | 7 | LoRA training, ComfyUI batch, PixAI, HuggingFace |
| research | 6 | arXiv, SearXNG, Polymarket, LLM Wiki |
| apple | 5 | Notes, Reminders, iMessage, FindMy, Computer Use |
| media | 5 | Spotify, YouTube, GIFs, audio |
| autonomous-ai-agents | 4 | Claude Code, Codex, OpenCode, Hermes |
| gaming | 2 | Minecraft, Pokemon |
| Others | 17 | Email, smart home, social media, red teaming, etc. |

---

## 10. PROJECT CONVENTIONS

### File Structure
```
Yggdrasil/
├── Asgard/          # Core: lilith-core, lilith-cli, lilith-memory, tools, api
├── Vanaheim/        # AI agents: orchestrator, Swarm
├── Alfheim/         # UI: dashboard, React frontend
├── Svartalfheim/    # Docs: knowledge base, wiki, skills (THIS DUMP)
├── Muspelheim/      # Dev/WIP: YggdrasilStudio, YggdrasilForge
├── Niflheim/        # Assets: models, textures, LoRAs
├── Helheim/         # Archive: dead projects
├── Jotunheim/       # Massive projects
├── Midgard/         # Personal apps
├── docs/            # Monorepo docs
├── scripts/         # Utility scripts
├── tests/           # Tests
└── website-v2/      # Public website
```

### Naming
- Package names: lowercase-hyphen (lilith-cli, lilith-memory)
- Python modules: snake_case
- Config files: YAML with Pydantic validation
- Runes in UI: Elder Futhark via `.ri` CSS classes

### Git & CI
- Main branch: main
- Feature branches: feature/description
- Commit messages: conventional commits (feat:, fix:, docs:, etc.)

---

*᛭ Yggdrasil — Where knowledge takes root and branches reach all realms*