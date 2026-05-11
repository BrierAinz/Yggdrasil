# Modernization Patterns for Yggdrasil

## CLI: argparse -> Cyclopts + Rich

### Why Cyclopts
- Type hints become CLI arguments automatically — no manual argparse definitions
- Subcommands from function names, nested groups from classes
- Built-in Rich integration for styled output
- No Click/Typer dependency chain

### Pattern: yggdrasil_cli.py

```python
from cyclopts import App
from rich.console import Console
from rich.table import Table

app = App(
    name="yggdrasil",
    help="Yggdrasil Ecosystem CLI",
)

@app.command
def status():
    """Show realm status."""
    console = Console()
    table = Table(title="Nine Realms", style="bold gold1")
    table.add_column("Realm", style="cyan")
    table.add_column("Status", style="green")
    # ...
    console.print(table)

if __name__ == "__main__":
    app()
```

### Key Decisions
- Gold (`gold1`) primary accent, cyan secondary
- Rich Table/Tree for structured output, never plain text
- `--version` flag loads version from `importlib.metadata` (no heavy imports)
- Lazy imports for heavy deps (Textual, SQLite, etc.)

## TUI: Textual Dashboard

### Structure
```
lilith_cli/tui/
├── __init__.py        # Export App
├── app.py             # Main Textual App with 3 tabs
├── realm_view.py      # Realm status panel
├── agent_view.py      # Agent monitor panel
├── log_view.py        # RichLog panel
└── styles.tcss        # Textual CSS (dark fantasy theme)
```

### Key Pattern: Auto-refresh
```python
async def _auto_refresh(self) -> None:
    while True:
        await asyncio.sleep(30)
        self._refresh_data()
```

### Key Bindings
```python
BINDINGS = [
    Binding("q", "quit", "Quit"),
    Binding("r", "refresh", "Refresh"),
    Binding("1", "tab('realms')", "Realms"),
    Binding("2", "tab('agents')", "Agents"),
    Binding("3", "tab('logs')", "Logs"),
]
```

## Web Dashboard: React -> HTMX + Alpine.js + Jinja2

### Why This Stack
- **No build pipeline** — no npm, webpack, vite, or node_modules
- **CDN-only deps** — HTMX 2.0 and Alpine.js loaded via CDN `<script>` tags
- **Server-rendered** — FastAPI + Jinja2 templates, no client-side routing
- **Real-time** — SSE and WebSocket for live updates
- **Dark fantasy CSS** — Matches the previous React dashboard pixel-for-pixel

### FastAPI App Structure
```python
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

app = create_app()  # Factory pattern for testing

# SSE for live logs
@app.get("/api/logs/stream")
async def stream_logs(request: Request):
    async def event_generator():
        while True:
            logs = await _fetch_recent_logs()
            yield f"data: {orjson.dumps(logs).decode()}\n\n"
            await asyncio.sleep(30)  # heartbeat
    return StreamingResponse(event_generator(), media_type="text/event-stream")

# WebSocket for agent chat
@app.websocket("/api/ws/chat")
async def ws_chat(websocket: WebSocket):
    await websocket.accept()
    while True:
        data = await websocket.receive_json()
        response = await _process_message(data)
        await websocket.send_json(response)
```

### HTMX Patterns for Auto-Refresh
```html
<!-- Panel auto-refreshes every 5 seconds -->
<div hx-get="/api/memory/stats"
     hx-trigger="every 5s"
     hx-target="#memory-panel"
     hx-swap="innerHTML">
</div>
```

### Alpine.js for Interactive State
```html
<div x-data="{ activeTab: 'graph' }">
  <button @click="activeTab = 'graph'" :class="{ 'active': activeTab === 'graph' }">
    Memory Graph
  </button>
  <div x-show="activeTab === 'graph'" x-cloak>
    <!-- Canvas content -->
  </div>
</div>
```

## Performance: Lazy Initialization + orjson + uvloop

### LazyState Pattern
```python
class _LazyState:
    """Thread-safe lazy initialization of expensive resources."""
    _memory = None
    _config = None
    _tool_registry = None
    _lock = threading.Lock()

    def _ensure_memory(self):
        if self._memory is None:
            from lilith_memory import MemoryStore
            self._memory = MemoryStore()
        return self._memory

def get_memory():
    with _lock:
        return _state._ensure_memory()
```

### uvloop Entry Point
```python
# run.py
import uvicorn

if __name__ == "__main__":
    uvicorn.run(
        "lilith_api.main:app",
        host="0.0.0.0",
        port=8000,
        loop="auto",    # Uses uvloop when available
        http="auto",    # Uses httptools when available
    )
```

### orjson Response Class
```python
try:
    import orjson
    class _ORJSONResponse(JSONResponse):
        media_type = "application/json"
        def render(self, content: typing.Any) -> bytes:
            return orjson.dumps(content)
    DEFAULT_RESPONSE = _ORJSONResponse
except ImportError:
    DEFAULT_RESPONSE = JSONResponse

app = FastAPI(default_response_class=DEFAULT_RESPONSE)
```

## ThreadPool Sizing

OLD (broken): `ThreadPoolExecutor(max_workers=2)` — 2 threads for entire gateway.
NEW (correct):
```python
import os
max_workers = min(32, (os.cpu_count() or 4) + 4)
# On Ryzen 5 5500 (6c/12t): max_workers = 16
```

This follows Python's `concurrent.futures` recommendation and scales with hardware.