# LokArni — ComfyUI Asset Manager

LokArni is a standalone React+FastAPI+SQLite webapp for cataloging and
organizing ComfyUI models (checkpoints, LoRAs, VAEs, ControlNets, IPAdapter,
upscalers, etc.) with CivitAI import, favorites, tagging, masonry views, and
a Prompt Studio for building generation configs.

- Repo: https://github.com/Pixel-Arni/lokarni
- Local install: `/home/brierainz/comfy/lokarni/`
- Port: 8000
- Start/stop: `./lokarni.sh start|stop|status|restart`

## Quick Start

```bash
cd /home/brierainz/comfy/lokarni
./lokarni.sh start    # starts uvicorn on :8000
./lokarni.sh status   # check PID
./lokarni.sh stop     # kill process

# UI:  http://localhost:8000
# API: http://localhost:8000/api/categories/
#      http://localhost:8000/api/assets/
```

## Prompt Studio Feature

LokArni v2.6.5+ includes a **Prompt Studio** view (accessible via the 🪄 wand
icon in the sidebar or by selecting "Prompt" category). It provides a QoL
interface for building ComfyUI prompts without leaving the asset manager.

**Features:**
- **Quick Presets** — one-click model/prompt combos (Eir Portrait, Photo
  Portrait, FaceID Transfer, Dark Fantasy, Eir Classic v1)
- **Positive/Negative prompt editors** with copy-to-clipboard buttons
- **Quick fragment buttons** — insert quality (Masterpiece, Photoreal,
  Cinematic, Sharp), lighting (Golden Hour, Neon, Studio, Dramatic), style
  (Dark Fantasy, Oil Paint, Watercolor, Anime), and common negatives
- **Model selectors** — Checkpoint, LoRA (with weight slider + auto trigger
  word display), IPAdapter FaceID (with weight), VAE — populated from catalog
- **Generation settings** — Steps (10-50), CFG Scale (1-20), Sampler dropdown
- **Copy to ComfyUI** — separate buttons for Positive, Negative, and Full Config

**Presets** are defined in `frontend/src/content/PromptBuilder.jsx` as a
`PRESETS` array constant. Each preset specifies: checkpoint, lora, loraWeight,
vae, faceId, faceIdWeight, positive, negative, steps, cfg, sampler. To add/edit
presets, modify the `PRESETS` array and rebuild:

```bash
cd /home/brierainz/comfy/lokarni/frontend
npm run build
# Then restart: cd .. && ./lokarni.sh restart
```

**Adding new views to LokArni** follows this pattern:
1. Create `frontend/src/content/YourView.jsx` — full React component
2. Patch `frontend/src/components/Sidebar.jsx` — add entry to `specialViews` object
3. Patch `frontend/src/App.jsx` — import the component, add it to the render
   section, and add the view name to all exclusion lists (the arrays that check
   `!["Add", "Manage", ...].includes(category)`)
4. Rebuild: `cd frontend && npm run build`, then restart backend

## API Reference

### Categories (hierarchical: Category -> SubCategory)

```
GET  /api/categories/          -> list all categories with subcategories
POST /api/categories/          -> create category
```

**Default category tree (created on first launch):**

| Category   | SubCategories                                      |
|------------|----------------------------------------------------|
| General    | All Assets (1), Favorites (2)                      |
| Models     | Checkpoint (3), LoRA (4), Textual Inversion (5), VAE (6) |
| Styles     | Anime (7), Realistic (8), Cartoon (9), Painting (10), 3D (11) |
| Concepts   | Character (12), Object (13), Scene (14), Effect (15) |
| Tools      | Pose (16), Workflow (17), Inpainting (18), ControlNet (19) |
| Media      | Image (20), Video (21), GIF (22)                  |

### Assets

```
GET    /api/assets/                    -> list all assets
GET    /api/assets/{id}                -> get single asset
POST   /api/assets/                    -> create asset (JSON body)
PATCH  /api/assets/{id}                -> update asset (partial JSON)
DELETE /api/assets/{id}                 -> delete asset
POST   /api/assets/import/             -> import from ZIP (multipart)
```

**AssetCreate schema (POST /api/assets/):**

```json
{
  "name": "My LoRA",
  "type": "LoRA",
  "path": "/absolute/path/to/model.safetensors",
  "preview_image": "",
  "description": "Description of the model",
  "trigger_words": "trigger, word, list",
  "positive_prompt": "recommended positive prompt",
  "negative_prompt": "recommended negative prompt",
  "tags": "tag1, tag2, tag3",
  "model_version": "v1.0",
  "used_resources": "",
  "subcategory_id": 4,
  "slug": "",
  "creator": "",
  "base_model": "SDXL",
  "created_at": "",
  "nsfw_level": "",
  "media_files": [],
  "download_url": "",
  "is_favorite": false,
  "custom_fields": {"key": "value"}
}
```

**AssetUpdate schema (PATCH /api/assets/{id}):**

All fields optional — only included fields are updated:

```json
{
  "subcategory_id": 12,
  "is_favorite": true,
  "tags": "updated, tags"
}
```

### CivitAI Import

```
POST /api/import/from-civitai     -> import model from CivitAI URL
GET  /api/import/civitai/search    -> search CivitAI models
GET  /api/import/from-civitai-image/{image_id}  -> import single image
POST /api/import/from-civitai-image/{image_id}  -> import single image
```

**CivitAI import request:**

```json
{
  "civitai_url": "https://civitai.com/models/133005",
  "api_key": null
}
```

## Current Asset Catalog (13 assets, cleaned May 2026)

| ID | Type | Name | Notes |
|----|------|------|-------|
| 1 | Checkpoint ★ | Juggernaut XL | Best photorealistic SDXL checkpoint |
| 2 | Checkpoint | Pony Diffusion V6 XL | Anime/anthro specialized |
| 3 | Checkpoint | SD XL 1.0 | Base SDXL model |
| 4 | LoRA ★ | Eir Niflheimr v2 Best | Trigger: eir_niflheimr |
| 6 | LoRA | Eir Niflheimr v1 Final (r32) | Trigger: eir_niflheimr |
| 8 | LoRA ★ | IPAdapter FaceID SDXL LoRA | Required companion for FaceID |
| 9 | LoRA | IPAdapter FaceID PlusV2 SDXL LoRA | Requires ViT-bigG-14 |
| 17 | VAE ★ | SDXL VAE | Standard SDXL VAE |
| 19 | Upscaler | RealESRGAN x4plus | General purpose 4x upscaler |
| 20 | Checkpoint | CLIP Vision ViT-H-14 (FaceID) | Vision encoder for FaceID SDXL |
| 21 | Checkpoint ★ | IPAdapter FaceID SDXL | Face identity adapter |
| 22 | Checkpoint | IPAdapter FaceID PlusV2 SDXL | Enhanced face transfer (needs ViT-bigG) |
| 23 | Checkpoint | IPAdapter FaceID SD 1.5 | FaceID for SD 1.5 models |

Deleted assets: Eir v2 Final (redundant — v2 Best is superior), Qwen Image VAE
(not a VAE).

## Pitfalls

### 1. CivitAI slug resolution is broken — use numeric IDs

The `resolve_model_id_from_slug()` function searches CivitAI's
`/api/v1/models?query=<slug>&nsfw=true` and then tries to match
`item.slug == slug`. This often fails because:

- The URL slug (last path segment) isn't always the model's API slug
- Short/generic names return too many results and the exact match fails
- Non-English characters or special characters in slugs break the search

**Fix:** Use the numeric model ID as the URL. For example, instead of
`https://civitai.com/models/juggernaut-xl`, use
`https://civitai.com/models/133005`. The function checks `slug.isdigit()`
first and short-circuits to the numeric path, which always works.

```python
# BROKEN — slug resolution fails
requests.post(url, json={"civitai_url": "https://civitai.com/models/juggernaut-xl"})

# WORKS — numeric ID bypasses slug resolution
requests.post(url, json={"civitai_url": "https://civitai.com/models/133005"})
```

### 2. Assets need subcategory_id to appear in filtered views

Assets created without `subcategory_id` appear ONLY in "All Assets" (which
shows everything regardless). Always set `subcategory_id`:

| subcategory_id | Category -> SubCategory |
|-----------------|------------------------|
| 3 | Models -> Checkpoint |
| 4 | Models -> LoRA |
| 5 | Models -> Textual Inversion |
| 6 | Models -> VAE |
| 7-11 | Styles -> (Anime/Realistic/Cartoon/Painting/3D) |
| 12 | Concepts -> Character |
| 19 | Tools -> ControlNet |

### 3. Locally-trained LoRAs need manual import

LoRAs trained locally (e.g., Kohya_ss outputs like
`eir_niflheimr_v2_best.safetensors`) are not on CivitAI and must be created
via `POST /api/assets/`. Include meaningful `trigger_words`, `description`,
`tags`, and `custom_fields` for searchability.

### 4. CivitAI imports don't fetch the model file

The CivitAI import endpoint fetches metadata (name, description, trigger
words, preview images, tags) but does NOT download the actual `.safetensors`
model file. The `path` field is set to the preview image, not the model file.
You still need to manually download models to the correct ComfyUI `models/`
subdirectory.

### 5. LokArni is German-language in the backend

Error messages and some default data are in German. The UI displays in
English. Don't be confused by German API error responses.

### 6. Frontend rebuild required after JSX changes

LokArni serves the frontend from the `frontend/dist/` build output (via
FastAPI static files). After modifying any `.jsx` file, you MUST rebuild:

```bash
cd /home/brierainz/comfy/lokarni/frontend && npm run build
cd .. && ./lokarni.sh restart
```

The dev server (`npm run dev`) on port 5173 works for live preview during
development, but the production backend on :8000 will only see changes after
`npm run build`.

### 7. Adding views requires patching three files

To add a new sidebar view (e.g., "Prompt") to LokArni:
1. **Create** `frontend/src/content/YourView.jsx` — React component
2. **Patch** `frontend/src/components/Sidebar.jsx` — add entry to the
   `specialViews` object with an icon, label, and color
3. **Patch** `frontend/src/App.jsx` — import the component, add it to the
   render section (`{category === "YourView" && <YourView />}`), and add
   the name to ALL exclusion list arrays (the `!["Add", "Manage", ...]`
   checks). There are 4+ occurrences in App.jsx that must all be updated.

If you miss one of the exclusion list entries, the AssetGrid will render
underneath your custom view when that category is selected.

## Bulk Import Script Pattern

For importing many assets at once (e.g., scanning ComfyUI model directories):

```python
import requests, os

BASE_URL = "http://localhost:8000"
LORAS_DIR = "/home/brierainz/comfy/ComfyUI/models/loras"

# 1. Scan directory for .safetensors files
lora_files = [f for f in os.listdir(LORAS_DIR)
              if f.endswith('.safetensors') and not f.startswith('.')]

# 2. Create assets via API
for f in lora_files:
    payload = {
        "name": f.replace('.safetensors', '').replace('_', ' ').title(),
        "type": "LoRA",
        "path": os.path.join(LORAS_DIR, f),
        "subcategory_id": 4,  # Models -> LoRA
        "tags": "lora",
    }
    resp = requests.post(f"{BASE_URL}/api/assets/", json=payload)
    if resp.status_code == 200:
        print(f"  Created: {f} (ID={resp.json()['id']})")

# 3. Fix subcategory for CivitAI imports (they come with subcategory_id=None)
# PATCH /api/assets/{id} with {"subcategory_id": <correct_id>}
```

## Relationship to ComfyUI-Lora-Manager

- **LokArni** = catalog/gallery layer + Prompt Studio (standalone webapp,
  categories, favorites, CivitAI metadata, prompt building)
- **ComfyUI-Lora-Manager** = in-ComfyUI layer (previews, drag-drop to canvas)
- They complement each other — use LokArni for organizing/browsing your
  collection and building prompts, Lora-Manager for quick access during
  workflow editing in ComfyUI.