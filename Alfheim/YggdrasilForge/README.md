# YggdrasilForge — Viking 3D Asset Studio

3D asset creation and management studio. The 3D counterpart to [YggdrasilStudio](../YggdrasilStudio/) (2D).

## Architecture

```
YggdrasilForge/
├── backend/                  # FastAPI :8081
│   ├── main.py              # App + lifespan + routes
│   ├── config.py            # Pydantic Settings (.env)
│   ├── models.py            # Request/Response Pydantic models
│   ├── database.py          # SQLite async (generations + assets)
│   ├── blender_client.py    # Async HTTP client → Blender MCP :9897
│   └── routes/
│       ├── generation.py    # Text/Image → 3D, poll, history
│       ├── assets.py        # PolyHaven + Sketchfab search/download
│       ├── blender.py       # Scene info, screenshots, code exec
│       └── render.py        # Eevee/Cycles rendering
├── frontend/                 # React + Vite + TailwindCSS :5174
│   └── src/
│       ├── api/client.ts    # Typed API client
│       ├── hooks/           # React hooks (useGenerations, useAssets)
│       ├── pages/           # Forge, Library, Viewport, History
│       ├── components/      # Layout, shared components
│       └── theme/           # Nordic dark palette + TailwindCSS
├── data/                     # SQLite DB + generated outputs
├── tests/                    # Pytest with Blender MCP mocks
├── pyproject.toml            # Python deps
├── start.sh                  # Start backend + frontend
└── .env.example              # Environment template
```

## Quick Start

```bash
# 1. Copy environment
cp .env.example .env

# 2. Start everything
chmod +x start.sh
./start.sh all

# Or start separately:
./start.sh backend   # FastAPI on :8081
./start.sh frontend  # Vite on :5174
```

## Prerequisites

- **Python 3.11+** with venv
- **Node.js 18+** with npm
- **Blender 5.x** with MCP addon on port **9897** (not default 9876!)
  - On WSL2: set addon host to `0.0.0.0` in Blender panel

## API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET | `/health` | Health check + Blender status |
| POST | `/api/generation/text-to-3d` | Generate 3D from text |
| POST | `/api/generation/image-to-3d` | Generate 3D from image |
| GET | `/api/generation/{id}` | Get generation status |
| GET | `/api/generation/` | List generation history |
| POST | `/api/assets/polyhaven/search` | Search PolyHaven |
| POST | `/api/assets/polyhaven/download` | Download PolyHaven asset |
| POST | `/api/assets/polyhaven/apply-texture` | Apply texture to object |
| POST | `/api/assets/sketchfab/search` | Search Sketchfab |
| POST | `/api/assets/sketchfab/download` | Download Sketchfab model |
| GET | `/api/blender/status` | Blender MCP status |
| GET | `/api/blender/scene` | Scene info |
| GET | `/api/blender/screenshot` | Viewport screenshot |
| POST | `/api/blender/execute` | Execute Python in Blender |
| POST | `/api/render/` | Render scene (Eevee/Cycles) |

## Free Integrations Only

| Service | Type | Cost |
|---------|------|------|
| Hunyuan3D | Text/Image → 3D | Free |
| Hyper3D Rodin | Text/Image → 3D | Free trial |
| PolyHaven | Textures/HDRIs/Models | CC0 Free |
| Sketchfab | 3D Models | Free (account: gameoverhf12) |

**No Meshy, no Tripo3D** — those require paid API keys.

## Ports

| Service | Port | Note |
|---------|------|------|
| Forge Backend | 8081 | FastAPI |
| Forge Frontend | 5174 | Vite dev |
| Studio Backend | 8080 | (sibling) |
| Studio Frontend | 5173 | (sibling) |
| Blender MCP | 9897 | Custom port |
| ComfyUI | 8188 | (sibling) |

## WSL2 → Blender

The Blender MCP addon runs on Windows. On WSL2:

1. Open Blender → Edit → Preferences → Addons → Blender MCP
2. Set **host** to `0.0.0.0` (not just `127.0.0.1`)
3. In `.env`, set `BLENDER_MCP_URL=http://<WINDOWS_IP>:9897`
   - Find Windows IP: `cat /etc/resolv.conf | grep nameserver`
   - Or use port forwarding: `socat TCP-LISTEN:9897,fork TCP:$(win_ip):9897 &`

## License

Part of the Yggdrasil ecosystem.
