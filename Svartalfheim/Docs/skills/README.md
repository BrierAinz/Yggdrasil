# Yggdrasil Skills Knowledge Base

> Migrated from Hermes Agent — all skills, memory, and abilities
> Date: 2026-05-10

## Structure

```
skills/
├── MANIFEST.json                    # Machine-readable index
├── README.md                        # This file
├── autonomous-ai-agents/            # AI agent orchestration
│   ├── claude-code/SKILL.md
│   ├── codex/SKILL.md
│   ├── hermes-agent/SKILL.md
│   └── opencode/SKILL.md
├── creative/                        # Content generation
│   ├── ai-influencer/SKILL.md      # Lilith character, content pipeline
│   ├── blender-mcp/SKILL.md
│   ├── comfyui/SKILL.md
│   ├── yggdrasilforge/SKILL.md
│   └── ... (22 skills)
├── devops/                          # Infrastructure & deployment
│   ├── cloudflare/SKILL.md
│   ├── docusaurus/SKILL.md
│   └── ... (11 skills)
├── mlops/                           # ML/AI training & deployment
│   ├── lora-training-pipeline/SKILL.md
│   ├── comfyui-batch-generate/SKILL.md
│   └── ... (7 skills)
├── software-development/            # Dev workflows
│   ├── lilith-cli-setup/SKILL.md
│   ├── yggdrasil-ecosystem/SKILL.md
│   └── ... (16 skills)
└── ... (25 categories total)
```

## Categories (25)

| Category | Skills | Key Topics |
|----------|--------|------------|
| apple | 5 | macOS, Notes, Reminders, iMessage |
| autonomous-ai-agents | 4 | Claude Code, Codex, OpenCode, Hermes |
| creative | 22 | ComfyUI, Blender, AI influencers, design |
| data-science | 1 | Jupyter, data exploration |
| devops | 11 | Cloudflare, Docker, Docusaurus, WSL |
| email | 1 | Himalaya IMAP/SMTP |
| gaming | 2 | Minecraft, Pokemon |
| github | 8 | Auth, PRs, Issues, Code Review |
| mcp | 1 | MCP client protocol |
| media | 5 | Spotify, YouTube, GIFs, audio |
| mlops | 7 | LoRA training, ComfyUI batch, PixAI |
| note-taking | 1 | Obsidian vault |
| productivity | 9 | Google Workspace, Notion, Linear, Airtable |
| red-teaming | 1 | Jailbreak techniques |
| research | 6 | arXiv, SearXNG, Polymarket |
| smart-home | 1 | Philips Hue |
| social-media | 1 | X/Twitter |
| software-development | 16 | Lilith CLI, Yggdrasil, debugging, TDD |
| yuanbao | 1 | Tencent Yuanbao groups |
| dogfood | 1 | Web app QA testing |
| diagramming | 0 | SVG diagrams (placeholder) |
| domain | 0 | (placeholder) |
| feeds | 0 | (placeholder) |
| gifs | 0 | (placeholder) |
| inference-sh | 0 | (placeholder) |

## Key Skills for Yggdrasil

### Core Architecture
- **yggdrasil-ecosystem** — 9-realm monorepo architecture, conventions, CI/CD
- **yggdrasil-studio-dev** — YggdrasilStudio dev workflow, services, ports
- **lilith-cli-setup** — Yggdrasil CLI agent v6.5+, config, providers, REPL
- **lilith-development** — Development patterns, testing, module conventions

### Creative Pipeline
- **ai-influencer** — Lilith v2.0 anime/cyberpunk neon, content strategy, Printful merch
- **comfyui** — Image/video/audio generation, workflow automation
- **blender-mcp** — 3D asset creation via Blender MCP bridge
- **yggdrasilforge** — Viking 3D Asset Studio (FastAPI + React + Blender MCP)

### Infrastructure
- **cloudflare** — DNS, Pages, Workers, security headers
- **docusaurus** — Docs site with runes, neon CSS, swizzles
- **docker-management** — Container lifecycle, Compose stacks

### ML/AI
- **lora-training-pipeline** — Full LoRA training: dataset prep → captioning → training → evaluation
- **pixai-generation** — PixAI API with custom LoRAs
- **comfyui-batch-generate** — Batch image generation with IPAdapter FaceID

## Usage

Each skill directory contains:
- **SKILL.md** — Main skill document with YAML frontmatter (name, description, trigger, tags, version)
- **references/** — Supplementary documentation, API details, pitfalls
- **scripts/** — Executable scripts and tools
- **templates/** — File templates for project scaffolding

Lilith CLI can load skills via:
```bash
# Reference a skill by path
yggdrasil --skill /path/to/skills/mlops/lora-training-pipeline/SKILL.md

# Or via the knowledge base
yggdrasil --knowledge Svartalfheim/Docs/skills/
```

## Origin

All skills migrated from Hermes Agent (`~/.hermes/skills/`) on 2026-05-10.
Contains 116 skills across 25 categories, 598+ supporting files, 11MB of specialized knowledge.

---

*᛭ Yggdrasil — The World Tree of Knowledge*