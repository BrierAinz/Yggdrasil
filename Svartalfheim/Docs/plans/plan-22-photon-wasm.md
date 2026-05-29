# Plan 22: Photon WASM Integration

> **Goal:** Compile select Python components to WebAssembly for browser execution, enabling client-side config validation, memory search, and tool discovery without server round-trips.

---

## Overview

YggdrasilStudio already has a Rust-compiled WASM module for performance-critical operations. Photon takes a complementary approach: compiling **Python components** to WASM via Pyodide, enabling complex logic (validation, search, registry lookups) to run client-side without rewriting in Rust.

The architecture follows the **python-wasm (Pyodide)** approach — NOT Rust-compiled WASM. This preserves Python codebases and leverages the existing lilith-* modules.

---

## Components to Compile

### 1. `lilith-core/config` → WASM Module
- **Purpose:** Client-side configuration validation
- **What it does:** Validates YAML/TOML configs, checks schema compliance, enforces required fields
- **Integration:** YggdrasilStudio frontend preprocess — validate before submitting to backend
- **Size estimate:** ~2KB Python → ~50KB in Pyodide package

### 2. `lilith-memory/search` → WASM Module
- **Purpose:** Client-side memory search and filter
- **What it does:** Full-text search across memory entries, tag filtering, relevance ranking
- **Integration:** YggdrasilStudio Dashboard — instant search without API calls
- **Size estimate:** ~5KB Python → ~80KB in Pyodide package

### 3. `lilith-tools/registry` → WASM Module
- **Purpose:** Client-side tool discovery UI
- **What it does:** Parse tool manifests, build registry trees, suggest compatible tools
- **Integration:** YggdrasilStudio tool palette — show available tools without server query
- **Size estimate:** ~3KB Python → ~60KB in Pyodide package

---

## Architecture

```
┌─────────────────────────────────────────┐
│          Browser (Pyodide WASM)         │
│                                         │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐│
│  │ Config   │ │ Memory   │ │ Tool     ││
│  │ Validator │ │ Search   │ │ Registry ││
│  └────┬─────┘ └────┬─────┘ └────┬─────┘│
│       │              │              │    │
│       └──────────────┼──────────────┘    │
│                      │                   │
│              Pyodide Runtime             │
│              (~25MB initial)             │
└──────────────────────┬──────────────────┘
                       │ WASM Bridge API
┌──────────────────────┴──────────────────┐
│          YggdrasilStudio Frontend        │
│          (React + Vite)                  │
│                                          │
│  ┌──────────────────────────────────────┐│
│  │   WASM Loader (Vite plugin)         ││
│  │   - Lazy loading per module          ││
│  │   - Service Worker caching           ││
│  └──────────────────────────────────────┘│
└──────────────────────────────────────────┘
```

---

## Build Pipeline

### Phase 0: Setup (Day 0)
1. Add `pyodide` as a dev dependency
2. Create `Alfheim/YggdrasilStudio/wasm/` directory structure
3. Create Vite plugin for WASM loading (`vite-plugin-pyodide`)

### Build Steps
```
Python Source (.py)
  → Pyodide Package Build (pyodide build)
  → .whl converted to WASM-compatible package
  → Vite plugin serves via ESM import
  → Browser loads Pyodide runtime + packages on demand
```

### Directory Structure
```
Alfheim/YggdrasilStudio/
├── wasm/
│   ├── packages/
│   │   ├── lilith-config/        # Config validator WASM package
│   │   │   ├── src/
│   │   │   │   └── lilith_config/
│   │   │   │       ├── __init__.py
│   │   │   │       └── validator.py
│   │   │   └── meta.yaml
│   │   ├── lilith-memory/        # Memory search WASM package
│   │   │   ├── src/
│   │   │   │   └── lilith_memory/
│   │   │   │       ├── __init__.py
│   │   │   │       └── search.py
│   │   │   └── meta.yaml
│   │   └── lilith-registry/     # Tool registry WASM package
│   │       ├── src/
│   │       │   └── lilith_registry/
│   │       │       ├── __init__.py
│   │       │       └── discovery.py
│   │       └── meta.yaml
│   └── bridge/
│       ├── index.ts              # WASM bridge API for React
│       ├── loader.ts             # Pyodide lazy loader
│       └── cache.ts              # Service Worker cache strategy
├── vite.config.ts
└── src/
    └── hooks/
        └── useWasm.ts            # React hook for WASM module access
```

---

## Performance Targets

| Metric | Target | Measurement |
|--------|--------|-------------|
| Cold Start | < 100ms | Time from import to first function call |
| Search Operation | < 50ms | Memory search over 1000 entries |
| Config Validation | < 30ms | Full schema validation |
| Pyodide Download | < 5s | Initial 25MB download (cached after first load) |
| Package Load | < 200ms | Loading individual lilith-* package |

---

## Caching Strategy

### Service Worker Approach
1. **First visit:** Download Pyodide runtime (~25MB) + core packages
2. **Subsequent visits:** Serve from Service Worker cache
3. **Updates:** Version-based cache busting (hash in filename)
4. **Offline:** Full functionality for cached modules

### Chunked Loading
```javascript
// Only load Pyodide when a WASM feature is first requested
const pyodide = await loadPyodide({
  indexURL: "/wasm/pyodide/",
  // Load only the required packages
  packages: ["lilith-config"]
});
```

### Main Thread Protection
- **NEVER** load Pyodide on the main thread for initial download
- Use `Web Worker` for Pyodide runtime
- Communicate via `postMessage` for all WASM operations
- Consider `Comlink` for simpler worker-proxy pattern

---

## Implementation Phases

### Phase 1: Proof of Concept (3 days)
**Goal:** Validate that lilith-core/config can run in Pyodide WASM.

- [ ] Create `wasm/` directory structure
- [ ] Write minimal `lilith_config.validator` module
- [ ] Build Pyodide package for lilith-config
- [ ] Create Vite plugin for WASM loading (`vite-plugin-pyodide`)
- [ ] Create `useWasm` React hook
- [ ] Test: Load Pyodide, import module, validate a config from browser
- [ ] Benchmark cold start and validation time
- [ ] Document findings and adjust architecture if needed

**Deliverables:**
- Working proof-of-concept: config validation running in browser
- Performance benchmarks
- Architecture decision: proceed with Pyodide or pivot

### Phase 2: Memory Search Module (5 days)
**Goal:** Port lilith-memory search to WASM for Dashboard use.

- [ ] Extract core search logic from `lilith-memory`
- [ ] Build Pyodide package for lilith-memory
- [ ] Implement Web Worker bridge (avoid main thread blocking)
- [ ] Add search results to Dashboard UI
- [ ] Implement Service Worker caching
- [ ] Performance test: search 1000+ entries under 50ms

**Deliverables:**
- Working client-side search in Dashboard
- Service Worker caching for Pyodide runtime
- Performance report

### Phase 3: Tool Registry + Integration Testing (3 days)
**Goal:** Complete the trio and integrate into production UI.

- [ ] Build Pyodide package for lilith-tools/registry
- [ ] Add tool discovery to YggdrasilStudio tool palette
- [ ] Integration testing across all modules
- [ ] Bundle size optimization
- [ ] Documentation for adding new WASM modules
- [ ] CI integration: build WASM packages in GitHub Actions

**Deliverables:**
- All three WASM modules functional in production
- CI pipeline for WASM package builds
- Developer guide for adding new modules

---

## Pitfalls & Mitigations

| Pitfall | Impact | Mitigation |
|---------|--------|------------|
| Pyodide 25MB initial download | Slow first load | Service Worker caching + lazy loading; show skeleton UI during download |
| Main thread blocking | UI freezes during WASM init | Use Web Workers; Comlink proxy pattern |
| Package version mismatches | Runtime errors in browser | Pin exact Pyodide version; test with same Python version as server |
| Limited stdlib in Pyodide | Some modules unavailable | Pre-test all imports; maintain compatibility list |
| Memory usage in browser | Tab crashes on large datasets | Implement pagination; limit search to 500 entries client-side |
| Build complexity | Dev experience degradation | Vite plugin automates WASM build; single `pnpm build` command |
| Debugging WASM issues | Hard to trace errors | Source maps; detailed error boundaries; fallback to API if WASM fails |

---

## Fallback Strategy

If Pyodide proves too heavy (>5s load time after caching) or has compatibility issues:

1. **Lightweight alternative:** Use `py2wasm` compiler for individual functions (smaller bundles)
2. **Transpilation:** Use `transcrypt` to convert Python to JS for simpler modules
3. **API-only:** Fall back to server-side endpoints for all validation/search (current state)
4. **Hybrid:** Use WASM for hot paths only (config validation), API for cold paths (full search)

---

## Success Criteria

- [x] Phase 1 POC: Config validation runs in browser via Pyodide WASM
- [ ] Cold start < 100ms (after Pyodide runtime loaded)
- [ ] Search operations < 50ms
- [ ] Pyodide runtime cached and loads in < 2s on repeat visits
- [ ] All three modules functional in production
- [ ] CI pipeline builds WASM packages automatically
- [ ] No main thread blocking (Web Worker architecture)