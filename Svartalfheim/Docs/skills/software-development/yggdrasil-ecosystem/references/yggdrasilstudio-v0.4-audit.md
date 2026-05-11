# YggdrasilStudio v0.4 Audit — Session Findings

**Date:** 2026-05-05
**Plan:** `Svartalfheim/plans/plan-19-yggdrasilstudio-v0.4.md`

## Current Metrics

| Metric | Value |
|--------|-------|
| Backend LOC | 3023 (6 route files + 6 core files) |
| Frontend LOC | 4231 (5 pages + 8 components + 5 hooks) |
| Tests | **0** (zero) |
| Version in main.py | 0.1.0 (should be 0.3.0+) |
| Known TODOs | 1 — "wire PromptBuilder's img2img input" in Studio.jsx:177 |

## Component Sizes (Lines of Code)

### Backend
| File | LOC |
|------|-----|
| comfyui_client.py | 809 |
| main.py | 448 |
| database.py | 328 |
| routes/generation.py | 316 |
| routes/presets.py | 224 |
| routes/assets.py | 234 |
| routes/history.py | 187 |
| models.py | 139 |
| lokarni_bridge.py | 127 |
| config.py | 59 |

### Frontend
| File | LOC |
|------|-----|
| components/PromptBuilder.jsx | **809** (refactor target) |
| pages/Settings.jsx | **530** (refactor target) |
| pages/History.jsx | 502 |
| api/client.ts | 402 |
| pages/Studio.jsx | 326 |
| components/ImageGrid.jsx | 292 |
| pages/Gallery.jsx | 240 |
| pages/Characters.jsx | 230 |
| components/GenerationProgress.jsx | 229 |
| components/Sidebar.jsx | 171 |
| components/CharacterSelector.jsx | 90 |
| components/Toaster.jsx | 88 |
| components/Layout.jsx | 72 |
| components/StatsCharts.jsx | 70 |
| components/ErrorBoundary.jsx | 67 |

## API Endpoints

### Routes
- `GET /api/assets/checkpoints` / `loras` / `vaes` / `upscale-models` / `samplers` / `schedulers`
- `GET /api/assets/lokarni` / `lokarni/categories` / `lokarni/{asset_id}`
- `POST /api/assets/lokarni/import`
- `POST /api/generate` / `POST /api/generate/batch`
- `GET /api/generate/{prompt_id}/status`
- `WS /api/generate/{prompt_id}/ws`
- `POST /api/generate/interrupt/{prompt_id}`
- `GET /api/history` / `GET /api/history/search` / `GET /api/history/stats`
- `DELETE /api/history/{entry_id}` / `DELETE /api/history/clear` / `POST /api/history/bulk-delete`
- `POST /api/history/{entry_id}/favorite`
- `GET /api/history/favorites` / `GET /api/history/{entry_id}`
- `GET /api/presets` / `POST /api/presets` / `PUT /api/presets/{id}` / `DELETE /api/presets/{id}`
- `GET /api/workflows` / `GET /api/workflows/{type}`
- `GET /api/images/{filename}` / `GET /health` / `GET /api/system/info` / `GET /api/system/queue` / `POST /api/system/interrupt`

### Missing Frontend Wiring
- **img2img**: WorkflowType exists, workflow template exists, but Studio.jsx TODO at line 177
- **upscale**: WorkflowType + template exist, no UI tab
- **ipadapter_face**: WorkflowType + template exist, no UI tab (face swap)
- **batch generation**: Backend supports it, no UI

## Frontend Hooks
- `useGeneration.js` — submit + WS progress + cancel + time estimation
- `useAssets.js` — load checkpoints, loras, vaes, samplers, schedulers
- `useDebounce.js` — 300ms debounce
- `useWebSocket.js` — WebSocket connection
- `useKeyboardShortcuts.js` — G/H/F/S navigation

## Refactor Plan Targets

### PromptBuilder → 5 sub-components
1. `PromptTabs.jsx` — Tab container
2. `PromptInput.jsx` — Textarea + negative prompt
3. `GenerationSettings.jsx` — Steps, CFG, sampler, scheduler, seed
4. `ImageUpload.jsx` — Drag-drop + WASM preprocess
5. `PromptBuilder.jsx` — Orchestrator (< 200 LOC)

### Settings → 4 sub-components
1. `SettingsGeneration.jsx` — Generation defaults
2. `SettingsServer.jsx` — ComfyUI connection
3. `SettingsUI.jsx` — UI preferences
4. `Settings.jsx` — Tabs + state (< 150 LOC)