---
name: blender-mcp
description: "Control Blender 3D via the Blender MCP addon — execute Python/bpy code, manage scenes, import models, apply textures, and render. Connects Hermes to a running Blender instance through a TCP socket MCP bridge."
version: 1.0.0
author: BrierAinz
license: MIT
platforms: [linux, windows, wsl]
compatibility: "Requires Blender 3.0+ with the BlenderMCP addon installed and running. Hermes MCP server configured via blender-mcp PyPI package."
prerequisites:
  commands: ["blender"]
  running_services: ["Blender with BlenderMCP addon active on port 9876"]
setup:
  help: "Install the BlenderMCP addon in Blender and start its server, then restart Hermes to pick up the MCP tools."
metadata:
  hermes:
    tags:
      - blender
      - 3d-modeling
      - bpy
      - mcp
      - creative
      - rendering
      - polyhaven
      - sketchfab
    related_skills: [comfyui, native-mcp]
    category: creative
---

# Blender MCP

Control a running Blender instance through the Blender MCP addon. The
architecture consists of two parts:

1. **Blender addon** (runs inside Blender) — opens a TCP socket on port 9876
2. **blender-mcp Python package** (runs as MCP server for Hermes) — bridges
   Hermes tool calls to Blender's TCP socket

This gives Hermes full bpy/Python access to Blender, enabling programmatic
3D modeling, material creation, scene management, rendering, and asset
import from PolyHaven/Sketchfab.

## Architecture

```
┌──────────────────────┐       MCP stdio       ┌──────────────────┐
│  Hermes Agent         │◄──────────────────────►│ blender-mcp       │
│  (mcp_blender_*       │                        │ (PyPI package)    │
│   tools)              │                        └────────┬─────────┘
└──────────────────────┘                                 │
                                                  TCP 9876
                                                         │
                                                ┌────────▼─────────┐
                                                │ Blender + Addon   │
                                                │ (bpy Python env)  │
                                                └──────────────────┘
```

## When to Use

- User asks to create, modify, or inspect 3D models in Blender
- User wants to generate images/renders from Blender scenes
- User wants to import assets from PolyHaven, Sketchfab, or Hyper3D
- User wants to apply materials/textures to objects
- User asks for scene information, object info, or viewport screenshots
- User wants to automate repetitive Blender tasks via Python scripts

## Setup

### Step 1: Install the addon in Blender

The addon file is already at:
```
E:\SteamLibrary\steamapps\common\Blender\5.1\scripts\addons\blender_mcp_addon.py
```

In Blender:
1. Edit → Preferences → Add-ons → Install...
2. Select `blender_mcp_addon.py`
3. Enable the **Blender MCP** checkbox
4. In the 3D Viewport sidebar (press `N`), open the **BlenderMCP** tab
5. Click **Start Server** — this opens the TCP socket on port 9876

### Step 2: Hermes MCP configuration

Already configured in `~/.hermes/config.yaml`:

```yaml
mcp_servers:
  blender:
    command: "/home/brierainz/.hermes/hermes-agent/venv/bin/blender-mcp"
    args: []
    timeout: 180
    connect_timeout: 30
```

### Step 3: Restart Hermes

After the addon is running in Blender, restart Hermes. MCP tools will
appear as `mcp_blender_*` and connect automatically.

### Alternative: Blender CLI (headless)

For batch/scripted work without the interactive MCP bridge, Blender can
run headless:

```bash
# Windows path from WSL
"/mnt/e/SteamLibrary/steamapps/common/Blender/blender.exe" \
  --background \
  --python my_script.py

# Or using cmd.exe
cmd.exe /c "E:\\SteamLibrary\\steamapps\\common\\Blender\\blender.exe --background --python my_script.py"
```

Headless mode is useful for:
- Automated rendering pipelines
- Batch model export
- Headless geometry operations
- CI/CD integration

## Available MCP Tools

Once connected, the following tools are available (prefixed `mcp_blender_`):

| Tool | Description |
|------|-------------|
| `get_scene_info` | Get detailed info about the current scene (objects, cameras, lights) |
| `get_object_info` | Get detailed info about a specific object by name |
| `get_viewport_screenshot` | Capture the 3D viewport as a PNG image |
| `execute_blender_code` | Execute arbitrary Python/bpy code in Blender |
| `get_polyhaven_status` | Check if PolyHaven integration is enabled |
| `get_polyhaven_categories` | List PolyHaven asset categories |
| `search_polyhaven_assets` | Search PolyHaven for HDRIs, textures, models |
| `download_polyhaven_asset` | Download and import a PolyHaven asset |
| `set_texture` | Apply a downloaded texture to an object |
| `get_sketchfab_status` | Check if Sketchfab integration is enabled |
| `search_sketchfab_models` | Search Sketchfab for 3D models |
| `get_hyper3d_status` | Check if Hyper3D Rodin integration is enabled |

The `execute_blender_code` tool is the most powerful — it provides full
access to Blender's Python API (bpy). Any bpy operation is possible.

## Common bpy Code Snippets

### Create a simple mesh

```python
import bpy
bpy.ops.mesh.primitive_uv_sphere_add(radius=1, location=(0, 0, 0))
obj = bpy.context.active_object
obj.name = "MySphere"
```

### Create a material with color

```python
import bpy
mat = bpy.data.materials.new(name="RedMaterial")
mat.use_nodes = True
bsdf = mat.node_tree.nodes["Principled BSDF"]
bsdf.inputs["Base Color"].default_value = (0.8, 0.1, 0.1, 1.0)
bpy.context.active_object.data.materials.append(mat)
```

### Set up camera and render

```python
import bpy
# Camera already in scene — position it
cam = bpy.data.objects["Camera"]
cam.location = (5, -5, 5)
cam.rotation_euler = (1.1, 0, 0.78)

# Render settings (Blender 5.x: use 'BLENDER_EEVEE', not 'EEVEE')
bpy.context.scene.render.resolution_x = 1920
bpy.context.scene.render.resolution_y = 1080
bpy.context.scene.render.engine = 'BLENDER_EEVEE'  # or 'CYCLES'
bpy.context.scene.render.filepath = 'C:/tmp/render.png'  # Windows path
bpy.ops.render.render(write_still=True)
```

### Export to formats

```python
import bpy
# OBJ
bpy.ops.export_scene.obj(filepath='/tmp/model.obj')

# GLB/GLTF
bpy.ops.export_scene.gltf(filepath='/tmp/model.glb')

# FBX
bpy.ops.export_scene.fbx(filepath='/tmp/model.fbx')

# STL (for 3D printing)
bpy.ops.export_mesh.stl(filepath='/tmp/model.stl')
```

## Decision Tree

| User says | Tool | Notes |
|-----------|------|-------|
| "show me the scene" | `get_scene_info` | Lists all objects, cameras, lights |
| "info about object X" | `get_object_info` | Detailed transform, geometry, materials |
| "take a screenshot" | `get_viewport_screenshot` | Captures viewport as PNG (unreliable — render to file instead) |
| "create a sphere/cube/etc" | `execute_blender_code` | bpy primitive ops |
| "apply material/color" | `execute_blender_code` | Material node tree via bpy |
| "render the scene" | `execute_blender_code` | Set filepath + `bpy.ops.render.render` |
| "export to GLB/FBX/OBJ" | `execute_blender_code` | Export ops |
| "import an HDRI" | PolyHaven tools | Search → download (auto-sets world) |
| "add texture to object" | PolyHaven tools | Search textures → download → set_texture |
| "download a 3D model" | Sketchfab or PolyHaven | Search → download (imports to scene) |
| "AI-generate a 3D model" | Hyper3D Rodin | Check status first, then generate |
| "make a character/creature" | Sketchfab FIRST, primitives LAST | See Pitfall #17 — characters from primitives look terrible |
| "batch render/automate" | CLI headless | `blender --background --python script.py` |

## Pitfalls

1. **Blender must be running with the addon active** — The MCP bridge
   connects to `localhost:9876`. If Blender isn't running or the addon
   hasn't started its server, all `mcp_blender_*` tools will fail with a
   connection error. Always verify: open Blender → sidebar → BlenderMCP
   tab → "Start Server" should show a green/active status.

2. **TCP socket is single-connection** — The addon's server accepts ONE
   connection at a time. If Hermes connects and you also try connecting
   from another client (e.g., Claude Desktop), the second connection will
   be refused. Disconnect one before using the other.

3. **Headless mode doesn't have the addon** — The BlenderMCP addon
   requires Blender's GUI viewport (it opens a socket via Blender's
   threading). `--background` mode can't run the MCP addon. For headless,
   write standalone bpy scripts and run them with `blender --background
   --python script.py`.

4. **Windows paths from WSL** — When executing bpy code that references
   file paths, use Windows-style paths (`E:\\path`) since Blender runs
   on Windows. The MCP bridge translates paths, but `execute_blender_code`
   runs inside Blender's Python, which expects Windows paths. Render
   outputs to shared locations like `/tmp/` (visible from WSL) or use
   Windows temp (`C:\\Users\\Game_\\AppData\\Local\\Temp\\`).

5. **Version mismatch: addon vs pip package** — The Blender addon
   (`blender_mcp_addon.py`, currently v1.2) and the PyPI bridge
   (`blender-mcp`, currently v1.5.6) can drift. The addon is inside
   Blender's scripts dir and needs manual update. If tools fail with
   "unknown command" errors, check that both are at compatible versions.

6. **Long-running bpy operations timeout** — The MCP bridge has a 180s
   default timeout per command. Heavy rendering or complex operations may
   exceed this. For rendering, reduce samples or use `CYCLES` with
   `adaptive_sampling` to speed up. You can also increase the timeout in
   `~/.hermes/config.yaml` under `mcp_servers.blender.timeout`.

7. **No undo in execute_blender_code** — Commands executed via MCP are
   permanent. There's no undo queue for programmatic operations. Recommend
   saving the `.blend` file before destructive operations:
   ```python
   import bpy
   bpy.ops.wm.save_as_mainfile(filepath='/tmp/backup.blend')
   ```

8. **Screenshot path uses the system temp dir** — The `get_viewport_screenshot`
   tool saves to the OS temp directory. In WSL + Blender on Windows, this
   means the Windows temp dir (`C:\Users\Game_\AppData\Local\Temp\`). The
   MCP bridge reads the file and returns it, so you don't need to worry
   about the path — but if screenshots fail, check that Blender has write
   access to the temp directory.

9. **Blender 5.x Python API changes** — Blender 5.x (the version installed,
   currently 5.1.1) has significant API changes from 4.x. Key differences
   discovered in practice:

   - **Render engine enum**: `'BLENDER_EEVEE'` (not `'EEVEE'`). The old
     `'EEVEE'` string raises `enum not found`. Valid engines:
     `'BLENDER_EEVEE'`, `'BLENDER_WORKBENCH'`, `'CYCLES'`.
   - **SceneEEVEE attributes removed**: `use_gtao`, `use_bloom`,
     `bloom_threshold`, `bloom_intensity` no longer exist on
     `scene.eevee` in 5.x. The entire EEVEE next-gen pipeline removed
     the old toggle-style properties. Check available attributes with
     `[a for a in dir(scene.eevee) if 'keyword' in a.lower()]` before
     setting them.
   - **Light type enum**: Valid values are `'POINT'`, `'SUN'`, `'SPOT'`,
     `'AREA'`. `'LIGHT'` is NOT a valid type — it's the base class name,
     not an enum value. Use `'AREA'` for rectangular/panel lights.
   - **Studio light names**: Valid `space.shading.studio_light` values are
     `'Default'`, `'basic.sl'`, `'outdoor.sl'`, `'paint.sl'`, `'rim.sl'`,
     `'studio.sl'`. The old `.exr` format (e.g. `'studio.exr'`) is invalid.

   When `execute_blender_code` fails with `AttributeError` or
   `enum not found`, check the Blender Python API docs for the matching
   version at `docs.blender.org/api/`.

10. **PolyHaven/Sketchfab require addon-side toggles** — PolyHaven and
    Sketchfab features are enabled via checkboxes in the BlenderMCP
    sidebar panel. If `get_polyhaven_status` returns "disabled", the user
    needs to check the PolyHaven option in Blender's sidebar before
    searching/downloading assets.

11. **WSL2 cannot reach Windows localhost ports** — The Blender addon
    binds its TCP socket to `127.0.0.1` (Windows localhost) by default.
    WSL2 has its own network namespace and **cannot connect** to Windows'
    `127.0.0.1`. `powershell.exe -Command "netstat -an | Select-String '9897'"`
    confirmed the addon listens on `127.0.0.1:9897` only. Neither the WSL
    gateway IP (`172.31.64.1`) nor the DNS relay (`10.255.255.254`) can
    reach it. **Fix**: In the BlenderMCP addon panel, change the **Host**
    field from `localhost`/`127.0.0.1` to `0.0.0.0` so it listens on all
    interfaces. Then in `~/.hermes/config.yaml`, set env vars:

    ```yaml
    mcp_servers:
      blender:
        command: "/home/brierainz/.hermes/hermes-agent/venv/bin/blender-mcp"
        args: []
        timeout: 180
        connect_timeout: 30
        env:
          BLENDER_HOST: "10.255.255.254"   # or the Windows WSL gateway IP
          BLENDER_PORT: "9897"
    ```

    The `blender-mcp` PyPI package reads `BLENDER_HOST` and `BLENDER_PORT`
    env vars (defaults: `localhost` / `9876`). After changing the addon to
    `0.0.0.0`, the MCP bridge from WSL2 can reach Blender via the host IP.

12. **Port is configurable but default is 9876** — The user's current
    Blender addon is set to port **9897** (not the default 9876). The
    `BLENDER_PORT` env var or `--port` CLI arg sets the port for the
    `blender-mcp` bridge to connect to. Always verify with
    `powershell.exe -Command "netstat -an | Select-String '9876|9897'"`

13. **Viewport screenshot can fail silently** — `get_viewport_screenshot`
    may return "Screenshot file was not created" even when the viewport is
    visible. This happens when Blender's GUI thread is busy or the viewport
    isn't fully initialized. **Fallback**: render to file using
    `execute_blender_code` with `bpy.ops.render.render(write_still=True)`
    and a camera, then reference the file path. Always ensure a camera
    exists and is set as `scene.camera` before rendering — objects created
    in code don't auto-become the active camera.

14. **Cameras can be lost between operations** — If you run
    `bpy.ops.object.delete(use_global=False)` to clear a scene, it removes
    ALL objects including the camera. Always recreate and assign a camera
    afterward: `scene.camera = bpy.data.objects["MyCam"]`. Verify with
    `[o for o in bpy.data.objects if o.type == 'CAMERA']` before rendering.

15. **`view_all` override context error** — `bpy.ops.view3d.view_all`
    with a manual context override dict raises "1-2 args execution context
    is supported" in Blender 5.x. To zoom to fit, either use the default
    context (no override) or position the camera manually with explicit
    `location` and `rotation_euler` values.

16. **Rendering to Windows paths from WSL** — Blender on Windows expects
    Windows paths (`C:/path`). When running `execute_blender_code`,
    `bpy.ops.render.render(write_still=True)` with `filepath = "C:/tmp/file.png"`
    works. From WSL, the same file is accessible at `/mnt/c/tmp/file.png`.
    Always use Windows-style paths in bpy code since Python inside Blender
    is Windows Python. Use `os.makedirs("C:/tmp", exist_ok=True)` to ensure
    the directory exists before rendering.

17. **NEVER build characters from primitives** — Building human/character
    models from cubes, spheres, and cylinders produces Minecraft-like results
    that look terrible. The user explicitly rejected a chibi model built this
    way ("si esta fea"). **Always prefer Sketchfab downloads or AI generation
    (Hyper3D/Hunyuan3D) for character/creature models.** Primitives are fine
    for simple props, abstract shapes, backgrounds, or mockups — but not for
    anything that needs to look like a recognizable character.

18. **Sketchfab workflow — full sequence** — Downloading from Sketchfab requires
    several steps and has quirks:

    a. **Check status first**: `get_sketchfab_status` returns a friendly message
       if disabled. If you call `search_sketchfab_models` while disabled, it
       returns the cryptic error `"Unknown command type: search_sketchfab_models"`.
       Always call `get_sketchfab_status` first to verify the integration is on.

    b. **Enable in Blender**: 3D Viewport → press `N` → BlenderMCP panel →
       check **"Use assets from Sketchfab"** → enter API key → restart
       connection. API key is free at
       `https://sketchfab.com/settings/password/api`

    c. **Search**: `search_sketchfab_models` accepts `query`, `count`, and
       `downloadable=True`. The `downloadable` flag is important — without it,
       you'll see models you can't actually import.

    d. **Preview is unreliable**: `get_sketchfab_model_preview` often returns
       an empty result. Don't rely on it — judge models by their face count,
       author, and description from search results instead.

    e. **Download**: `download_sketchfab_model` takes a `uid` (from search
       results) and `target_size` (desired height in meters). It normalizes
       the model to that size, which is very useful for character models
       (e.g. `target_size=1.5` for a ~1.5m tall character).

    f. **Post-import objects have generic names**: Imported FBX objects get
       names like `Object_6`, `Object_8`, `Sketchfab_model`, `RootNode`.
       The meaningful names are in the armature bones and material names
       (e.g. material `RubyRose_A_SD` with texture `RubyRose_A_SD_baseColor.png`).

    g. **Models come with armatures**: Character models typically include a
       full bone hierarchy (e.g. 98 bones for the RWBY model: Bip01 skeleton,
       finger bones, cape bones, weapon bones). The armature object may be
       named generically (e.g. `Object_3`). Inspect bones to understand
       what you can pose/animate.

19. **Sketchfab and Hyper3D return "Unknown command type" when disabled** —
    If you call `search_sketchfab_models`, `get_hyper3d_status`, or any
    asset-integration tool before enabling the feature in the BlenderMCP
    sidebar, Blender returns `"Unknown command type: <tool_name>"`. This is
    NOT a protocol error — it means the addon doesn't recognize that command
    because the feature checkbox is off. Fix: enable the integration in the
    BlenderMCP panel and restart the connection.

## References

- `references/blender-5x-api.md` — Detailed Blender 5.x API changes (render
  engines, SceneEEVEE, light types, studio lights, context override)
- `references/chibi-modeling.md` — Character modeling approach: Sketchfab
  FIRST, primitives LAST resort. Includes helper functions, chibi proportions,
  and scene-setup patterns for when primitives are unavoidable.
- `references/sketchfab-workflow.md` — Full Sketchfab import workflow:
  status check, search, download, post-import analysis, and rendering.
  Covers generic object names, armature inspection, and cleanup.
- `references/install-and-env.md` — Installation steps, environment details,
  TCP protocol, addon architecture

## Verification Checklist

- [ ] Blender is open and the BlenderMCP addon is installed (Edit → Preferences → Add-ons)
- [ ] BlenderMCP server is started (sidebar → BlenderMCP → "Start Server")
- [ ] Hermes config has `mcp_servers.blender` entry pointing to the venv `blender-mcp`
- [ ] Other Hermes MCP packages installed: `mcp` in Hermes venv
- [ ] After Hermes restart, `mcp_blender_*` tools appear in tool list
- [ ] `get_scene_info` returns scene data (not a connection error)