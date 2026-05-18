# Yggdrasil Implementation Plans — Master Index

## Active Plans

| # | Plan | Realm | Status | Description |
|---|------|-------|--------|-------------|
| 19 | YggdrasilStudio v0.4 | Alfheim | In Progress | Studio improvements: refactor PromptBuilder/Settings, tests, new endpoints |
| 20 | YggdrasilForge v0.1 | Alfheim | Active | Viking 3D Asset Studio — AI generation + Blender Bridge |
| 21 | Yggdrasil Growth v5 | Cross-realm | Active | Growth plan — WS bridge, Mimir agent, build system |
| 22 | Photon WASM | Alfheim | Planned | Python→WASM via Pyodide for client-side modules |
| 23 | Turborepo Monorepo | Alfheim | Planned | Turborepo migration for Alfheim frontend builds |

## Completed Plans

| # | Plan | Realm | Version | Description |
|---|------|-------|---------|-------------|
| 01 | AutoSub | Muspelheim | v0.1.0 | Generador automático de subtítulos (Whisper → SRT) |
| 13 | TerminalDashboard | Alfheim | v1.0.0 | TUI dashboard del ecosistema Yggdrasil |
| 15 | Mimir | Vanaheim | Active | Investigador profundo (SearXNG + arXiv), agente VanirAgent |
| 18 | ForgeMaster | Muspelheim | v1.0.0 | Gestión de modelos LLM, VRAM, y disk usage |

## Plan-to-Realm Mapping

| Realm | Plans |
|-------|-------|
| Alfheim | 13-TerminalDashboard ✅, 14-PixelForge, 17-YggSiteGenerator, 19-YggdrasilStudio v0.4, 20-YggdrasilForge |
| Muspelheim | 01-AutoSub ✅, 02-ClipForge, 03-TrendRadar, 18-ForgeMaster ✅ |
| Vanaheim | 15-Mimir ✅ |

## Cross-Realm Dependencies

```
YggdrasilStudio (2D) ←──── YggdrasilForge (3D)
   :8080                       :8081
   ComfyUI :8188               Blender MCP :9897
        │                          │
        └── Image → 3D bridge ─────┘
```

## YggdrasilForge — Key Architecture

```
Alfheim/YggdrasilForge/
├── backend/          # FastAPI :8081
│   ├── main.py       # App + CORS + routers
│   ├── config.py     # Settings (BLENDER_MCP_URL, etc.)
│   ├── models.py     # Pydantic models (Generation, Asset, etc.)
│   ├── database.py   # SQLite (generations + assets tables)
│   ├── blender_client.py  # Async MCP client (all Blender tools)
│   └── routes/
│       ├── generation.py  # Text-to-3D, Image-to-3D
│       ├── assets.py      # PolyHaven, Sketchfab search/download
│       ├── blender.py     # Scene info, execute code, screenshot
│       └── render.py      # Eevee/Cycles rendering
├── frontend/         # React + Vite + TailwindCSS :5174
│   └── src/
│       ├── pages/
│       │   ├── Forge.jsx      # Text/Image → 3D generation
│       │   ├── Library.jsx    # PolyHaven + Sketchfab browser
│       │   ├── Viewport.jsx   # Blender viewport live view
│       │   └── History.jsx    # Past generations
│       └── components/        # GenerationForm, AssetGrid, etc.
├── data/             # SQLite DB + exported models
├── tests/            # pytest tests
├── start.sh          # Startup script
├── start.bat         # Windows launcher
└── README.md         # Full documentation
```

**Free Services Only (no API keys needed):**
- Hunyuan3D — text-to-3D, image-to-3D via Blender MCP
- Hyper3D Rodin — text-to-3D, image-to-3D via Blender MCP (free trial)
- PolyHaven — HDRI, textures, models (CC0) via Blender MCP
- Sketchfab — search/download models (logged in: gameoverhf12) via Blender MCP

**Future (when budget available):** Meshy API, Tripo3D API — same provider interface pattern

## Conventions

- Plan files: `plan-NN-projectname.md`
- Zero-padded prefix
- Project name in kebab-case
- Each plan: Goal, Architecture, Tech Stack, Realm, Tasks
- Task format: Objective, Files, Steps, Verification, Commit