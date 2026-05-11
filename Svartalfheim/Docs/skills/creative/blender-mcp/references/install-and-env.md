# Blender MCP — Installation & Environment Details

## Environment (BrierAinz's setup)

- **Blender**: 5.1.1 (Steam install at `E:\SteamLibrary\steamapps\common\Blender\`)
  - Full path from WSL: `/mnt/e/SteamLibrary/steamapps/common/Blender/blender.exe`
  - Blender Python: bundled with Blender (NOT system Python)
  - Scripts dir: `E:\SteamLibrary\steamapps\common\Blender\5.1\scripts\addons\`
- **Blender MCP addon**: `blender_mcp_addon.py` (v1.2) — copied to Blender addons dir
- **blender-mcp bridge**: v1.5.6 — installed in Hermes venv at
  `/home/brierainz/.hermes/hermes-agent/venv/bin/blender-mcp`
- **Hermes config**: `~/.hermes/config.yaml` has `mcp_servers.blender` entry
- **Hermes venv**: `/home/brierainz/.hermes/hermes-agent/venv/` (Python 3.11)
  - `pip` not available in this venv; use `uv pip install` instead
  - Both `mcp` and `blender-mcp` installed via `uv pip install`

## Installation steps performed

1. **Found Blender** at Steam path via WSL mount
2. **Verified Blender version**: `blender.exe --version` → Blender 5.1.1
3. **Cloned blender-mcp repo**: `git clone https://github.com/ahujasid/blender-mcp.git`
4. **Copied addon to Blender scripts**: `cp addon.py → scripts/addons/blender_mcp_addon.py`
5. **Installed blender-mcp PyPI pkg**: `uv pip install blender-mcp --python <hermes-venv>/python3.11`
   - Pulled in `mcp`, `httpx`, and other deps
6. **Added MCP config**: `~/.hermes/config.yaml` → `mcp_servers.blender`
7. **User action**: Open Blender → Preferences → Add-ons → Install → enable BlenderMCP → Start Server
8. **User action**: Restart Hermes to discover MCP tools

## Addon architecture

The addon (`addon.py` from the GitHub repo) is a Blender add-on that:
- Uses `bl_info` metadata (name: "Blender MCP", version: (1, 2), blender: (3, 0, 0))
- Creates a `BlenderMCPServer` class that opens a TCP socket on port 9876
- Handles commands via a JSON protocol: `{"type": "command_name", "params": {...}}`
- Registers a Blender panel in View3D → Sidebar → BlenderMCP
- Supports PolyHaven, Sketchfab, and Hyper3D Rodin integrations (toggled in-panel)
- The MCP bridge (`blender-mcp` PyPI package) connects to this TCP socket

## Key differences from other MCP setups

- **Not npx/uvx based** — blender-mcp is a Python package, runs via direct path
  to the Hermes venv binary, not via `npx` or `uvx`
- **Requires a running GUI app** — The addon needs Blender's event loop and viewport
- **Single TCP connection** — Only one MCP client can connect at a time

## Tcp protocol details

Default host: `localhost`, default port: `9876`. Configurable via env vars:
- `BLENDER_HOST` — override host (default: localhost)
- `BLENDER_PORT` — override port (default: 9876)

The protocol sends JSON commands and receives JSON responses:
- Request: `{"type": "get_scene_info", "params": {}}`
- Response: `{"status": "success", "result": {...}}` or `{"status": "error", "message": "..."}`

Timeout is 180s per command (matches the addon's socket timeout).