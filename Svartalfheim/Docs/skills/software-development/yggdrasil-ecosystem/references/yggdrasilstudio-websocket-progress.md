# YggdrasilStudio WebSocket Progress Relay

## Architecture

```
Frontend (React)          Vite Proxy (:5173)        Backend (:8080)         ComfyUI (:8188)
     │                         │                         │                       │
     │ POST /api/generate      │ → /api/...              │                       │
     │────────────────────────→│─────────────────────────→│  POST /prompt          │
     │                         │                         │──────────────────────→│
     │  prompt_id returned     │                         │  (with client_id)      │
     │←────────────────────────│←────────────────────────│                       │
     │                         │                         │                       │
     │ WS /api/generate/       │ (ws: true)              │  WS /ws?clientId=X     │
     │   {prompt_id}/ws        │─────────────────────────→│──────────────────────→│
     │                         │                         │                       │
     │← type: progress         │←────────────────────────│← type: progress        │
     │← type: complete         │←────────────────────────│← type: executing      │
```

## Key Fix: Same client_id

The backend's `comfyui_client.py` generates a single `self.client_id` (UUID) on initialization. This same ID MUST be used for:

1. **POST /prompt** — the `client_id` field in the prompt submission payload
2. **WS /ws?clientId=X** — the WebSocket connection that listens for progress

The generation route handler (`generation.py`) was creating `client_id = str(uuid.uuid4())` for the WebSocket connection, which was a **different** ID from the one used in prompt submission. ComfyUI only sends events to the client_id that submitted the job, so all progress events were silently dropped.

**Fix**: Use `comfyui_client.client_id` (the singleton's fixed UUID) everywhere.

## Vite Proxy Config

The Vite dev server must have `ws: true` on the `/api` proxy route because WebSocket connections go through `/api/generate/{id}/ws`:

```javascript
// vite.config.js
'/api': {
  target: 'http://localhost:8080',
  changeOrigin: true,
  ws: true  // REQUIRED for WebSocket upgrade on /api/generate/{id}/ws
},
'/ws': {
  target: 'http://localhost:8080',
  changeOrigin: true,
  ws: true
},
'/health': {
  target: 'http://localhost:8080',
  changeOrigin: true
}
```

Without `ws: true` on `/api`, WebSocket upgrade requests are not proxied — the browser connects to Vite's HTTP handler which returns nothing, and progress tracking silently fails.

## ComfyUI WebSocket Events

```json
{"type": "execution_start", "data": {"prompt_id": "abc-123"}}
{"type": "progress", "data": {"value": 5, "max": 20, "prompt_id": "abc-123"}}
{"type": "executing", "data": {"node": "9", "prompt_id": "abc-123"}}
{"type": "executing", "data": {"node": null, "prompt_id": "abc-123"}}  // COMPLETE
{"type": "execution_error", "data": {"prompt_id": "abc-123", "exception_message": "..."}}
```

The `node: null` in `executing` signals completion. The backend relays this as `type: "complete"` to the frontend.

## Frontend WebSocket Hook

`useGeneration.js` (line ~56-60) connects to `getWsUrl(promptId)` which returns `/api/generate/${promptId}/ws`. It listens for:

- `type: "progress"` → update progress bar
- `type: "complete"` → mark generation as complete, fetch images
- `type: "error"` → show error toast