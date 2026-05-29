# Sketchfab Model Import Workflow

Complete reference for downloading and importing Sketchfab models via
Blender MCP. See SKILL.md Pitfall #18 for the quick-reference version.

## Prerequisites

1. **Enable in BlenderMCP panel**: 3D Viewport → press `N` → BlenderMCP tab
   → check "Use assets from Sketchfab" → enter API key.
2. **API key**: Free at https://sketchfab.com/settings/password/api
3. **Restart connection** after toggling the checkbox.

## Status Check (ALWAYS do first)

```
mcp_blender_get_sketchfab_status
```

Returns "disabled" with instructions if not enabled. If you skip this and
call `search_sketchfab_models` while disabled, you get the confusing error:
`"Unknown command type: search_sketchfab_models"` — this does NOT mean the
tool is broken, it means the feature is disabled.

## Search

```
mcp_blender_search_sketchfab_models(
    query="character name franchise style",
    count=10,
    downloadable=True   # IMPORTANT — filters to CC-licensed models
)
```

Returns list of models with:
- **UID**: Required for download (e.g. `ee2c2d567ce6477e8f4f9e6ff36d2822`)
- **Author**: Creator name
- **Face count**: Poly count — lower = better for performance
- **License**: Typically CC Attribution
- **Downloadable**: Should be True if you filtered correctly

### Choosing a Model

- For **characters/chibi**: look for "SD", "chibi", "low-poly", "game rip"
  keywords. Game-rip models (like Amity Arena) have proper textures and
  armatures.
- **Face count guide**: <5K = very low poly (mobile game style), 5-50K =
  moderate, 50K+ = detailed, 1M+ = extremely heavy.
- Prefer models where `downloadable=True` and license is CC Attribution.

## Preview (Unreliable)

```
mcp_blender_get_sketchfab_model_preview(uid="...")
```

In practice this often returns an empty string. Don't depend on it — use
the metadata from search results (face count, author, title) to judge models.

## Download

```
mcp_blender_download_sketchfab_model(
    uid="ee2c2d567ce6477e8f4f9e6ff36d2822",
    target_size=1.5   # desired height in meters
)
```

- `target_size` normalizes the model to that height. Use 1.5 for a human-
  sized character, 0.3 for a small prop, etc.
- Returns confirmation with dimensions, bounding box, and scale factor.
- Import usually takes 5-15 seconds depending on model complexity.
- Model is placed at world origin.

## Post-Import Analysis

Imported models have **generic object names**. Run this to understand
structure:

```python
import bpy
from mathutils import Vector

for obj in bpy.data.objects:
    if obj.type == 'MESH':
        mats = [(m.name, [n.image.name for n in m.node_tree.nodes
                          if n.type == 'TEX_IMAGE' and n.image])
                for m in obj.data.materials if m]
        uvs = [uv.name for uv in obj.data.uv_layers] if obj.data.uv_layers else []
        print(f"  {obj.name}: verts={len(obj.data.vertices)}, "
              f"parent={obj.parent.name if obj.parent else 'None'}, "
              f"mats={mats}, uvs={uvs}")
    elif obj.type == 'ARMATURE':
        print(f"  {obj.name}: bones={len(obj.data.bones)}")
    elif obj.type in ('EMPTY', 'LIGHT', 'CAMERA'):
        print(f"  {obj.name}: {obj.type}")
```

## Typical Imported Structure

```
Sketchfab_model (EMPTY, root)
  └─ ModelName.fbx (EMPTY)
      └─ RootNode (EMPTY)
          └─ Object_3 (ARMATURE) — the skeleton/rig
          ├─ Object_5 (EMPTY) — may contain metadata
          ├─ Object_6 (MESH) — typically the body mesh
          ├─ Object_7 (EMPTY) — accessory point
          ├─ Object_8 (MESH) — typically weapon/accessory mesh
          ├─ Rose_A_SD_0 (EMPTY) — bone group empty
          └─ Rose_Weapon_0 (EMPTY) — weapon bone group
```

The material/texture names are the key identifiers. Search those instead
of object names when targeting specific parts.

## Rendering Imported Models

```python
# Models are often tiny after import — position camera accordingly
# Check bounding box first:
for obj in bpy.data.objects:
    if obj.type == 'MESH' and obj.hide_render == False:
        bbox = [obj.matrix_world @ Vector(c) for c in obj.bound_box]
        xs, ys, zs = zip(*[(v.x, v.y, v.z) for v in bbox])
        print(f"{obj.name}: X[{min(xs):.2f},{max(xs):.2f}] "
              f"Y[{min(ys):.2f},{max(ys):.2f}] Z[{min(zs):.2f},{max(zs):.2f}]")

# Set up camera based on bounds
import bpy, os
cam = bpy.data.objects["SomeCamera"]
cam.location = (max_x*1.5, min_y*2, max_z*1.5)
cam.rotation_euler = (1.2, 0, 0.5)  # 3/4 view

bpy.context.scene.render.engine = 'BLENDER_EEVEE'
bpy.context.scene.render.filepath = "C:/tmp/model_render.png"
bpy.ops.render.render(write_still=True)
```

## Cleaning Up Before Import

If replacing an existing primitive model with a Sketchfab download:

```python
import bpy
bpy.ops.object.select_all(action='SELECT')
bpy.ops.object.delete(use_global=False)
# Then call mcp_blender_download_sketchfab_model
```

This removes ALL objects including lights and cameras. Re-add them
after import.