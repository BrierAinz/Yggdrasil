# Character Modeling in Blender via MCP

## CRITICAL: Primitives Are a Last Resort for Characters

Building characters (humanoids, creatures, anime figures, chibis) from
cubes/spheres/cylinders produces blocky, Minecraft-like results. The user
has explicitly rejected this approach. **Always try these FIRST:**

1. **Sketchfab** — `search_sketchfab_models` → `download_sketchfab_model`
   Thousands of CC-licensed models with textures, armatures, and proper UV
   mapping. See the main SKILL.md Pitfall #18 for full workflow.

2. **Hyper3D Rodin / Hunyuan3D** — AI-generated 3D models from text prompts.
   Enable in the BlenderMCP sidebar panel first.

3. **Primitives** — ONLY for simple props, abstract shapes, placeholders, or
   non-organic objects (crates, platforms, basic architecture). NEVER for
   characters or anything that needs to look recognizable.

## Sketchfab Import Pattern (Preferred for Characters)

```python
# 1. Always check status first (avoids "Unknown command type" error)
#    mcp_blender_get_sketchfab_status  →  Should say enabled

# 2. Search with downloadable=True
#    mcp_blender_search_sketchfab_models(query="Ruby Rose RWBY", count=10, downloadable=True)

# 3. Download with target_size (meters) for proper scale
#    mcp_blender_download_sketchfab_model(uid="ee2c2d567ce6477e8f4f9e6ff36d2822", target_size=1.5)

# 4. Post-import: objects have generic names, inspect them
import bpy
for obj in bpy.data.objects:
    if obj.type == 'MESH':
        mats = [m.name for m in obj.data.materials]
        verts = len(obj.data.vertices)
        print(f"  {obj.name}: {verts} verts, mats={mats}")
```

### Post-Import Analysis

Imported models come with:
- Generic object names: `Object_6`, `Object_8`, `RootNode`, etc.
- Meaningful material names: e.g. `RubyRose_A_SD` with texture
  `RubyRose_A_SD_baseColor.png`
- Full armature (up to 98+ bones for character models)
- UV mapping already applied
- Textures auto-loaded from the FBX archive

Always check for armatures and verify which mesh belongs to which part
(character body vs weapon vs accessories).

## Primitive Character Pattern (LAST RESORT ONLY)

Use this ONLY for placeholders or non-organic props. Characters built this
way look like Minecraft — the user rejected this approach for anime/chibi
characters.

### Chibi Proportions Reference

If you must use primitives for a quick placeholder:
- Total height: ~2.3 Blender units
- Head: radius ~0.5, centered at z=1.75
- Eyes: big, at z=1.78, spread ±0.2 from center
- Body: z=0.5 to 1.3
- Legs: z=0.1 to 0.45
- Arms: short nubs, barely extend past body

### Helper Functions

```python
def make_mat(name, color, metallic=0, roughness=0.5):
    mat = bpy.data.materials.new(name=name)
    mat.use_nodes = True
    bsdf = mat.node_tree.nodes["Principled BSDF"]
    bsdf.inputs["Base Color"].default_value = (*color, 1)
    bsdf.inputs["Metallic"].default_value = metallic
    bsdf.inputs["Roughness"].default_value = roughness
    return mat

def add_sphere(name, loc, scale, mat, segments=24):
    bpy.ops.mesh.primitive_uv_sphere_add(
        radius=1, segments=segments,
        ring_count=segments//2, location=loc)
    obj = bpy.context.active_object
    obj.name = name; obj.scale = scale
    obj.data.materials.append(mat)
    return obj

def add_cube(name, loc, scale, mat):
    bpy.ops.mesh.primitive_cube_add(size=1, location=loc)
    obj = bpy.context.active_object
    obj.name = name; obj.scale = scale
    obj.data.materials.append(mat)
    return obj

def add_cylinder(name, loc, scale, mat, segments=16):
    bpy.ops.mesh.primitive_cylinder_add(
        radius=1, depth=1, vertices=segments, location=loc)
    obj = bpy.context.active_object
    obj.name = name; obj.scale = scale
    obj.data.materials.append(mat)
    return obj
```

### Scene Setup After Scene Clear

```python
# WARNING: bpy.ops.object.delete removes ALL objects (cameras, lights, etc.)
# You MUST recreate them after clearing the scene.

bpy.ops.object.select_all(action='SELECT')
bpy.ops.object.delete(use_global=False)

# ...build model...

# Add camera (REQUIRED — scene clear removes all cameras)
bpy.ops.object.camera_add(location=(2, -2.5, 1.8))
cam = bpy.context.active_object
cam.name = "Camera_Char"
cam.rotation_euler = (1.15, 0, 0.65)
bpy.context.scene.camera = cam  # CRITICAL: must be set explicitly

# Add lights (use valid types: POINT, SUN, SPOT, AREA)
bpy.ops.object.light_add(type='SUN', radius=1, location=(3, -2, 5))

# Render to Windows path (Blender runs on Windows)
import os
os.makedirs("C:/tmp", exist_ok=True)
bpy.context.scene.render.engine = 'BLENDER_EEVEE'  # NOT 'EEVEE'
bpy.context.scene.render.filepath = "C:/tmp/render.png"
bpy.ops.render.render(write_still=True)
```