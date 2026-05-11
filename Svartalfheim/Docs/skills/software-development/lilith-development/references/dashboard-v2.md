# Dashboard v2 (FASE 10) — Reference

## Architecture

Dashboard upgraded from FASE 5 (basic chat + settings) to FASE 10 (Memory Visualization, REST API, Swarm Panel, Settings Editor).

```
Dashboard/
  __init__.py              # Exports DashboardServer, get_dashboard
  server.py                # DashboardServer: aiohttp WS+HTTP, command handlers, REST API
  frontend/
    index.html             # Dark fantasy UI with tabbed memory pane, rune particles
    style.css              # 1400+ lines — Norse/Lovecraftian CSS, memory tabs, graph styles
    app.js                 # 1700+ lines — WS client, pane management, memory graph canvas
  tests/
    test_dashboard.py       # 39 original tests (frontend files, theme, basic server)
    test_dashboard_api.py   # 143 new tests (API endpoints, WebSocket handlers, JS validation)
```

## REST API Endpoints

| Endpoint | Method | Handler | Description |
|----------|--------|---------|-------------|
| `/api/memory/stats` | GET | `do_GET` | Memory statistics (episodes, entities, facts, errors) |
| `/api/memory/entities` | GET | `do_GET` | Entity listing with `type` and `min_mentions` query params |
| `/api/memory/facts` | GET | `do_GET` | Fact listing with `category` query param |
| `/api/memory/graph` | GET | `do_GET` | Knowledge graph: nodes (entities) + edges (relations) |
| `/api/memory/episodes` | GET | `do_GET` | Episode listing with `count` and `session_id` query params |
| `/api/memory/search` | GET | `do_GET` | Semantic search with `q` query param |

All API responses are JSON. Embedding blobs are stripped before serialization.

## WebSocket Command Handlers

| Command | Handler | Data Source |
|---------|---------|-------------|
| `memory_stats` | `_handle_memory_stats` | KnowledgeGraph + EnhancedMemory counts |
| `memory_entities` | `_handle_memory_entities` | KnowledgeGraph.get_all_nodes() with filter |
| `memory_facts` | `_handle_memory_facts` | KnowledgeGraph.get_all_facts() with filter |
| `memory_graph` | `_handle_memory_graph` | KnowledgeGraph visualization data |
| `memory_episodes` | `_handle_memory_episodes` | EnhancedMemory recent episodes |

All handlers use defensive `hasattr()` checks to work without a Lilith instance.

## Frontend Memory Pane

Tabbed interface with 4 tabs:
- **Graph** — Force-directed canvas visualization (nodes = entities, edges = relations)
- **Entities** — Filterable entity list with type badges
- **Facts** — Category-filtered facts display
- **Episodes** — Recent conversation episodes timeline

### Canvas Graph Implementation (`drawMemoryGraph`)

- Force-directed layout with spring + repulsion physics
- Node styling: color by type (Person=skyblue, Location=limegreen, Concept=gold, Thing=plum)
- Edge styling: strength-based opacity
- Zoom: mouse wheel + buttons (`memoryGraphZoom(1.2)`, `memoryGraphZoom(0.8)`, `memoryGraphReset()`)
- Drag: click-drag nodes with `setupGraphInteraction()`
- Tooltips: hover shows entity name + type + mention count
- Physics: configurable iteration count, cooling, spring length/force, repulsion

### JS Functions Added (13)

```
updateMemoryStats, updateMemoryEntities, updateMemoryFacts,
updateMemoryGraph → drawMemoryGraph, updateMemoryEpisodes,
switchMemoryTab, fetchMemoryData, fetchMemoryStats, fetchAllMemoryData,
memoryGraphZoom, memoryGraphReset, setupGraphInteraction
```

## Settings Panel

TOML config editor with syntax-highlighted textarea. GET `/api/config` returns current config, POST `/api/config` saves changes.

## Test Structure

- `test_dashboard_api.py`: 143 tests
  - 20 tests: Memory API WebSocket handlers (stats, entities, facts, graph, episodes, search)
  - 47 tests: Frontend JS function validation (all 13 new functions present, correct signatures)
  - 13 tests: Frontend HTML/CSS validation (memory pane tabs, graph canvas, stats bar)
  - 47 tests: Command routing and WebSocket message handling
  - 16 tests: REST API endpoint tests

## Defensive Patterns

All memory handlers check `hasattr(self, '_lilith_instance')` before accessing memory. Without an instance, they return empty/null data structures:
- `memory_stats` → `{"episodes": 0, "entities": 0, "facts": 0, "errors": 0}`
- `memory_entities` → `{"entities": []}`
- `memory_graph` → `{"nodes": [], "edges": []}`

This allows the dashboard to run standalone for UI testing without a Lilith backend.

## Test Count: 704 (143 new for FASE 10)