---
name: yggdrasil-studio-dev
description: >
  Development workflow for YggdrasilStudio — start/stop services, health checks,
  startup order, port conflicts, venv issues, ComfyUI integration, and common pitfalls.
  Load when working on YggdrasilStudio or troubleshooting its local dev environment.
trigger: >
  When starting, stopping, debugging, or deploying YggdrasilStudio; when checking
  service health, resolving port conflicts, fixing venv issues, or working with
  ComfyUI integration for YggdrasilStudio.
tags: [yggdrasil-studio, fastapi, react, vite, comfyui, wasm, rust, go-gateway, dev-workflow]
version: 1.0.0
---

# YggdrasilStudio Development

## Project Location

```
/mnt/d/Proyectos/Yggdrasil/Alfheim/YggdrasilStudio/
```

## Architecture Overview

| Component | Language | Port | Purpose |
|-----------|----------|------|---------|
| Backend | Python (FastAPI) | 8080 | API server, ComfyUI proxy, streaming, rate limiting |
| Frontend | React + Vite + Tailwind | 5173 | Nordic dark fantasy UI |
| ComfyUI | Python | 8188 | Image/video generation engine (external dependency) |
| Go Gateway | Go 1.24 | 9090 | API gateway, auth, WebSocket fan-out, job queue (NOT compiled yet) |
| WS Bridge | Python (asyncio) | — | Persistent ComfyUI WS connection with fan-out to N browser clients |
| WASM Image Processor | Rust → WASM | N/A (browser) | Client-side image preprocessing (31KB binary) |

## WebSocket Bridge Architecture

The WS bridge (`ws_bridge.py`) is the **primary** real-time path for ComfyUI progress events. The old per-generation WS endpoint in `routes/generation.py` remains as fallback.

**How it works**:
1. Backend maintains a single persistent WS connection to ComfyUI (`ws://localhost:8188/ws?clientId={client_id}`)
2. Auto-reconnects with exponential backoff (1s → 30s, max 10 retries)
3. Browser clients connect to `WS /ws/comfyui` and send `{action: "subscribe", prompt_id: "..."}` messages
4. Bridge fans out events to only subscribed clients per prompt_id
5. Periodically broadcasts `queue_update` events (every 5s) with running/pending counts

**Event types from bridge**: `progress`, `execution_start`, `executing`, `executed`, `execution_error`, `queue_update`

**Frontend**: `useGeneration.js` hook connects to `/ws/comfyui` (instead of per-generation WS), sends subscribe/unsubscribe based on `promptId`, handles all event types from the bridge.

**Lifespan**: Bridge starts on FastAPI startup (`ws_bridge.start()`), stops on shutdown (`ws_bridge.stop()`). Router registered via `app.include_router(ws_routes_router)`.

**Key files**:
- `backend/ws_bridge.py` (384 lines) — ComfyUIWSBridge class, SubscriptionManager, event fan-out
- `backend/routes/ws_routes.py` (110 lines) — `WS /ws/comfyui` endpoint, message handling
- `frontend/src/hooks/useGeneration.js` — Refactored for bridge-based subscription

**Logging**: All bridge logging uses `logging.getLogger("yggdrasil.ws_bridge")`.

## Hardware

- **GPU**: RTX 3060 12GB VRAM
- **RAM**: 48GB DDR4
- ComfyUI GPU concurrency: max 2 simultaneous jobs via semaphore

## Startup Order

Services MUST be started in this order:

1. **ComfyUI** (:8188) — must be up first, backend depends on it
2. **Backend** (:8080) — connects to ComfyUI on startup
3. **Frontend** (:5173) — connects to backend

### Start ComfyUI

```bash
cd /home/brierainz/comfy/ComfyUI
source .venv/bin/activate
python3 main.py --listen 0.0.0.0 --port 8188
```

ComfyUI model loading can take 2-5 minutes depending on model size. Wait until the
HTTP health check passes before starting the backend.

### Start Backend

```bash
cd /mnt/d/Proyectos/Yggdrasil/Alfheim/YggdrasilStudio/backend
source .venv/bin/activate
python3 -m uvicorn main:app --host 0.0.0.0 --port 8080
```

Alternative: use the project start script:
```bash
cd /mnt/d/Proyectos/Yggdrasil/Alfheim/YggdrasilStudio
./start.sh
```
`start.sh` checks ComfyUI availability, installs deps if needed, and starts the backend.

### Start Frontend (Dev)

```bash
cd /mnt/d/Proyectos/Yggdrasil/Alfheim/YggdrasilStudio/frontend
npm install   # first time or after package changes
npm run dev   # starts Vite dev server on :5173 with HMR
```

### Start Frontend (Production Build)

```bash
cd /mnt/d/Proyectos/Yggdrasil/Alfheim/YggdrasilStudio/frontend
npm install
node_modules/.bin/vite build   # use direct binary (Hermes detects npx as long-running)
```

**Note**: `npx vite build` may be detected as a long-running process by Hermes.
Use `node_modules/.bin/vite build` instead.

## Health Check URLs

| Service | URL | Expected Response |
|---------|-----|-------------------|
| Backend | `http://localhost:8080/health` | `{"status":"partially_rooted","services":{"comfyui":{"url":"http://localhost:8188","online":true},"lokarni":{"url":"http://localhost:8000","online":false}}}` |
| ComfyUI | `http://localhost:8188/system_stats` | JSON with GPU/memory stats |
| ComfyUI | `http://localhost:8188/queue` | JSON with queue state |
| Frontend | `http://localhost:5173/` | React app (SPA) |

**Health endpoint response structure** — access nested path:
- `info?.services?.comfyui?.online` (NOT `info?.comfyui`)
- `info?.services?.lokarni?.online` (NOT `info?.lokarni`)

Status values: `"rooted"` (all services online), `"partially_rooted"` (some offline),
`"withered"` (backend up but no upstream services).

**Script**: Use `health_check.sh` for a quick status check of all services.

## Checking What's Running

```bash
# Check specific ports
ss -tlnp | grep -E '8080|8188|5173'

# Check by process name
ps aux | grep -E 'uvicorn|comfy|vite|node'

# Quick health check via curl
curl -s http://localhost:8080/health | python3 -m json.tool
curl -s http://localhost:8188/system_stats | python3 -m json.tool

# Check GPU utilization (ComfyUI active generation)
nvidia-smi
```

## Stopping Services

```bash
# Stop backend (find uvicorn process)
pkill -f "uvicorn main:app"
# Or by port:
kill $(lsof -ti:8080) 2>/dev/null

# Stop ComfyUI
pkill -f "main.py.*8188"
kill $(lsof -ti:8188) 2>/dev/null

# Stop frontend dev server
pkill -f "vite"
kill $(lsof -ti:5173) 2>/dev/null

# Stop ALL YggdrasilStudio services at once
pkill -f "uvicorn main:app"; pkill -f "main.py.*8188"; pkill -f "vite"
```

## Virtual Environments

| Component | Venv Path | Notes |
|-----------|-----------|-------|
| Backend | `/mnt/d/Proyectos/Yggdrasil/Alfheim/YggdrasilStudio/backend/.venv` | Uses `.venv` (NOT `venv`) |
| ComfyUI | `/home/brierainz/comfy/ComfyUI/.venv` | Separate venv |

### Backend Venv Issues

If the backend `.venv` was created without pip (common on WSL without sudo):

**Option A — Inherit system packages (fastest):**
```bash
cd /mnt/d/Proyectos/Yggdrasil/Alfheim/YggdrasilStudio/backend
python3 -m venv .venv
# Edit .venv/pyvenv.cfg:
# Change: include-system-site-packages = true
```
This makes the venv inherit all packages from system Python (fastapi, httpx, uvicorn, etc.).
Not isolated but acceptable for local dev.

**Option B — Bootstrap pip into venv (isolated):**
```bash
cd /mnt/d/Proyectos/Yggdrasil/Alfheim/YggdrasilStudio/backend
python3 -m venv --without-pip .venv
source .venv/bin/activate
curl -sS https://bootstrap.pypa.io/get-pip.py | python3
pip install -e ".[dev]"
```

**Option C — Use start.sh (auto-installs):**
```bash
cd /mnt/d/Proyectos/Yggdrasil/Alfheim/YggdrasilStudio
./start.sh  # checks and installs deps automatically
```

### ComfyUI Venv Issues

ComfyUI has its own `.venv` at `/home/brierainz/comfy/ComfyUI/.venv`. If it's broken:
```bash
cd /home/brierainz/comfy/ComfyUI
source .venv/bin/activate
pip install -r requirements.txt
```

## Common Issues

### Port Conflicts

| Port | Process | Fix |
|------|---------|-----|
| 8080 | Backend | `kill $(lsof -ti:8080)` then restart |
| 8188 | ComfyUI | `kill $(lsof -ti:8188)` then restart |
| 5173 | Vite | `kill $(lsof -ti:5173)` then restart |
| 3000 | Alternative frontend | `kill $(lsof -ti:3000)` |

If a port is stuck in TIME_WAIT:
```bash
# Check what's using the port
sudo lsof -i :8080

# Wait 60s for TIME_WAIT to clear, or force with:
kill -9 $(lsof -ti:8080)
```

### ComfyUI Model Loading Time

ComfyUI takes **2-5 minutes** to load models on startup. During this time:
- `GET /system_stats` may return 200 but with 0 VRAM used
- `POST /prompt` will fail or queue indefinitely
- The backend health check will show `"comfyui": {"online": false}`

**Wait until** `curl -s http://localhost:8188/system_stats` shows GPU VRAM usage > 0
before starting the backend.

### ComfyUI BrokenPipeError Pitfall

If ComfyUI was launched via `nohup` or `&` (pipelined stdout), pip's rich logging
handler raises `BrokenStdoutLoggingError` inside `post_prompt`, causing ALL `/prompt`
requests to return 500. `GET /system_stats` and `GET /queue` still work — only
POST /prompt is broken.

**Fix**: Patch ComfyUI's `app/logger.py` (add BrokenPipeError handling in `write()` and
`flush()`) and `server.py` (wrap `logging.info("got prompt")` in try/except). Or
start ComfyUI in a foreground terminal.

### Vite Dev Server Proxy

The Vite proxy MUST cover ALL API routes the frontend calls — not just `/api`:

```javascript
// vite.config.js — required proxy routes
server: {
  proxy: {
    '/api': { target: 'http://localhost:8080', changeOrigin: true, ws: true },
    '/health': { target: 'http://localhost:8080', changeOrigin: true },
    '/ws': { target: 'http://localhost:8080', changeOrigin: true, ws: true },
  }
}
```

Missing proxy routes cause 404s that make services appear offline.

### WebSocket Requires Same client_id

The generation WebSocket relay must use the same `client_id` as the ComfyUI prompt
submission. ComfyUI only sends progress events to the `client_id` that submitted
the prompt. If the relay generates a random `client_id`, generations appear stuck at
"queued" forever.

**Fix**: Use `comfyui_client.client_id` (the UUID used by queue_text2img etc.) for
WebSocket connections.

### Image Proxy — Use httpx Streaming, NOT RedirectResponse

The `/api/images/{filename}` endpoint must stream via httpx directly — `RedirectResponse`
causes 500 errors because query params get mangled by the browser.

### Frontend Font Integration

When adding Google Fonts to Tailwind:
1. Import in `index.html` with preconnect + stylesheet link
2. Add to `tailwind.config.js` `fontFamily` (e.g., `cinzel: ['Cinzel', 'serif']`)
3. **Add CSS fallback** in `index.css`: `.font-cinzel { font-family: 'Cinzel', serif !important; }`
4. **Clear Vite cache** after config changes: `rm -rf node_modules/.vite`

HMR alone won't propagate new `fontFamily` entries to CSS output.

### httpx Must Use http2=False

The ComfyUI client in `comfyui_client.py` must use `http2=False` (or omit it).
Setting `http2=True` requires the `h2` package; without it, ALL requests get 502 errors
that look like ComfyUI is down.

### Radix Tooltip Crash

Do NOT use `@radix-ui/react-tooltip` — it crashes the entire React app (white screen)
when `Tooltip.Provider` is missing or misconfigured. Use native `title` attributes or
Framer Motion `AnimatePresence` + `onMouseEnter/Leave` for animated tooltips.

### Hermes Terminal Blocks "uvicorn"

Any command containing the word "uvicorn" is auto-detected as a server process and
blocked by the Hermes terminal tool. Workarounds:
- Use `execute_code` with Python code
- Write a helper script to `/tmp/` and run it
- Check dependency versions via a Python script file (not inline `-c` containing "uvicorn")

### WASM Rebuild Required After Rust Changes

After editing `wasm-image-processor/wasm-image-processor/src/lib.rs`:
```bash
cd /mnt/d/Proyectos/Yggdrasil/Alfheim/YggdrasilStudio/wasm-image-processor/wasm-image-processor
wasm-pack build --target web --out-dir pkg
# Then copy output to frontend:
cp pkg/wasm_image_processor.js pkg/wasm_image_processor_bg.wasm \
   ../../frontend/public/wasm/
```

### Go Gateway Not Compiled

The Go gateway at `gateway/` is code-complete but Go is not installed on this system.
`go build ./cmd/main.go` requires `/usr/local/go` (needs sudo). Options:
1. Install Go manually via user-level tarball to `~/go-sdk/`
2. `make docker` to build in Docker
3. Skip the gateway — the FastAPI backend handles all proxying in dev

### WSL /mnt/d/ Filesystem Slowness

The project lives on `/mnt/d/` (NTFS mount). Operations like `git status`, `npm install`,
and file writes can be significantly slower than native Linux paths. When running
large operations, consider using `/tmp/` for intermediate files.

## Vite Required Proxy Routes

| Route | Target | WebSocket | Notes |
|-------|--------|-----------|-------|
| `/api` | `http://localhost:8080` | Yes | All API + WebSocket progress |
| `/health` | `http://localhost:8080` | No | Service status check |
| `/ws` | `http://localhost:8080` | Yes | Dedicated WebSocket |

## Key File Paths

```
YggdrasilStudio/
├── backend/
│   ├── main.py                 # FastAPI app entry point
│   ├── config.py               # Settings (COMFYUI_URL, ports, paths)
│   ├── models.py               # Pydantic models (WorkflowType, Generation, etc.)
│   ├── database.py              # aiosqlite history DB
│   ├── ws_bridge.py                 # Persistent ComfyUI WS bridge (reconnect, fan-out, subscribe/unsubscribe)
│   ├── comfyui_client.py        # Async ComfyUI client + workflow builders
│   ├── lokarni_bridge.py        # LokArni API bridge
│   ├── routes/                  # Split routers (generation, history, assets, presets, workflows, ws_routes)
│   ├── workflows/               # ComfyUI JSON workflow templates
│   ├── health_check.sh          # Quick service health checker
│   └── .venv/                   # Python venv (NOT venv, NOT ../venv)
├── frontend/
│   ├── src/
│   │   ├── App.jsx              # React.lazy + Suspense code splitting
│   │   ├── api/client.ts        # TypeScript API client + Zod schemas
│   │   ├── hooks/useGeneration  # Submit + WebSocket progress
│   │   ├── wasm/imageProcessor.js # WASM wrapper
│   │   └── theme/nordic.js      # Nordic theme config
│   ├── public/wasm/              # Compiled WASM binary + JS glue
│   └── vite.config.js           # Dev server + proxy config
├── gateway/                      # Go API gateway (not compiled yet)
├── wasm-image-processor/        # Rust → WASM source
├── start.sh                      # Startup script (checks ComfyUI, installs deps, starts backend)
└── start.bat                     # Windows launcher via WSL
```

## ComfyUI Integration Details

- **Location**: `/home/brierainz/comfy/ComfyUI/`
- **Venv**: `/home/brierainz/comfy/ComfyUI/.venv`
- **Output dir**: ComfyUI's `output/` directory (backend proxies images via `/api/images/`)
- **Client ID**: Must be consistent between prompt submission and WebSocket relay
- **Workflow builders**: txt2img, img2img, face_swap, upscale, ipadapter_face, txt2video
- **Streaming proxy**: Backend proxies ComfyUI responses in 64KB chunks
- **Rate limiting**: asyncio.Semaphore(2) + 30 req/min per-IP

## Generation Types

| Type | Workflow | Models Required |
|------|----------|----------------|
| txt2img | Text → Image | Juggernaut XL v9 or similar |
| img2img | Image → Image | SDXL checkpoint |
| face_swap | Face Swap | InsightFace + IP-Adapter |
| upscale | Upscale | RealESRGAN or similar upscaler |
| ipadapter_face | IP-Adapter Face | IP-Adapter + InsightFace |
| txt2video | Text → Video | Wan2.1 / Anima 3.0 + UMT5-XXL |

## Quick Reference Commands

```bash
# Full startup (3 terminals)
# Terminal 1: ComfyUI
cd /home/brierainz/comfy/ComfyUI && source .venv/bin/activate && python3 main.py --listen 0.0.0.0 --port 8188

# Terminal 2: Backend (wait for ComfyUI to fully load)
cd /mnt/d/Proyectos/Yggdrasil/Alfheim/YggdrasilStudio/backend && source .venv/bin/activate && python3 -m uvicorn main:app --host 0.0.0.0 --port 8080

# Terminal 3: Frontend
cd /mnt/d/Proyectos/Yggdrasil/Alfheim/YggdrasilStudio/frontend && npm run dev

# Quick health check
curl -s http://localhost:8080/health | python3 -m json.tool

# Check ComfyUI is ready (VRAM > 0)
curl -s http://localhost:8188/system_stats | python3 -c "import sys,json; d=json.load(sys.stdin); print(f'VRAM: {d[\"devices\"][0][\"vram_total\"] / 1024**3:.1f}GB' if d.get('devices') else 'Not ready')"

# Stop everything
pkill -f "uvicorn main:app"; pkill -f "main.py.*8188"; pkill -f "vite"

# Frontend production build (avoid npx — Hermes blocks it)
cd /mnt/d/Proyectos/Yggdrasil/Alfheim/YggdrasilStudio/frontend && node_modules/.bin/vite build
```