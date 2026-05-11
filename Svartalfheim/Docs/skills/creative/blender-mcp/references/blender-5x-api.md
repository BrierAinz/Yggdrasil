# Blender 5.x API Changes & Pitfalls

Applies to: **Blender 5.1.1** (current installed version)

## Render Engine Enum

```python
# WRONG (Blender 4.x style)
scene.render.engine = 'EEVEE'

# CORRECT (Blender 5.x)
scene.render.engine = 'BLENDER_EEVEE'
```

Valid engines: `'BLENDER_EEVEE'`, `'BLENDER_WORKBENCH'`, `'CYCLES'`
Invalid: `'EEVEE'` (raises `enum not found`)

## SceneEEVEE — Removed Properties

The following properties no longer exist on `scene.eevee` in Blender 5.x:

- `use_gtao` — ambient occlusion toggle removed
- `use_bloom` — bloom toggle removed
- `bloom_threshold` — removed
- `bloom_intensity` — removed

EEVEE Next (5.x) handles these via the compositor and View Layer properties
instead. To check what's available:

```python
attrs = [a for a in dir(scene.eevee) if not a.startswith('_')]
print(attrs)
```

## Light Type Enum

```python
# WRONG — 'LIGHT' is the base class, not a valid enum
bpy.ops.object.light_add(type='LIGHT', ...)

# CORRECT — valid types:
type='POINT'   # point light
type='SUN'     # directional sun
type='SPOT'    # spot light
type='AREA'    # area/rectangular light
```

## Viewport Studio Light Names

```python
space.shading.studio_light = 'studio.sl'  # CORRECT
space.shading.studio_light = 'studio.exr'  # WRONG — .exr format no longer used
```

Valid names: `'Default'`, `'basic.sl'`, `'outdoor.sl'`, `'paint.sl'`,
`'rim.sl'`, `'studio.sl'`

## View3D View All — Context Override Error

```python
# WRONG — manual context override dict crashes in 5.x
override = bpy.context.copy()
override['area'] = area
override['region'] = region
bpy.ops.view3d.view_all(override, center=True)
# Error: "1-2 args execution context is supported"
```

Workaround: position the camera manually instead of relying on view_all.

```python
cam.location = (2.0, -2.5, 1.8)
cam.rotation_euler = (1.15, 0, 0.65)
```