# Plan 23: Turborepo Monorepo Build Configuration

> **Goal:** Migrate Alfheim frontend builds to Turborepo for faster, consistent builds with shared configurations and intelligent caching.

---

## Overview

Yggdrasil's Alfheim realm has three frontend packages that share UI patterns, TailwindCSS config, and Nordic theme components. Currently, each package manages its own build pipeline independently, leading to:
- Duplicated build configurations
- Inconsistent Tailwind/ESLint/Prettier settings
- No build caching across CI runs
- Slow parallel development workflows

Turborepo unifies these under a single monorepo build system with intelligent caching, parallel execution, and shared configs.

---

## Architecture

```
Yggdrasil/  (Turborepo root)
├── turbo.json                    # Pipeline definitions
├── package.json                  # Workspace config
├── packages/
│   └── shared/                   # Shared Nordic theme + configs
│       ├── package.json
│       ├── tsconfig.json
│       ├── tailwind.config.ts    # Base TailwindCSS config
│       ├── eslint.config.js     # Base ESLint config
│       ├── .prettierrc          # Base Prettier config
│       └── src/
│           ├── components/       # Shared React components
│           │   ├── NordicCard/
│           │   ├── NordicButton/
│           │   ├── NordicModal/
│           │   └── NordicTheme/
│           ├── hooks/            # Shared hooks
│           │   ├── useWebSocket.js  # WS bridge hook
│           │   └── useNordicTheme.ts
│           └── styles/           # Shared styles
│               ├── nordic.css    # Nordic design tokens
│               └── animations.css # Shared transitions
├── Alfheim/
│   ├── YggdrasilStudio/         # Studio UI (React + Vite)
│   │   ├── frontend/
│   │   │   ├── package.json      # "name": "@yggdrasil/studio-ui"
│   │   │   ├── tsconfig.json     # Extends shared
│   │   │   ├── vite.config.ts
│   │   │   └── src/
│   ├── YggdrasilForge/          # Forge UI (React + Vite)
│   │   ├── frontend/
│   │   │   ├── package.json      # "name": "@yggdrasil/forge-ui"
│   │   │   ├── tsconfig.json     # Extends shared
│   │   │   ├── vite.config.ts
│   │   │   └── src/
│   └── Dashboard/               # HTMX Dashboard (no build needed)
│       ├── package.json          # "name": "@yggdrasil/dashboard-ui"
│       └── templates/            # Jinja2 + HTMX
```

---

## Package Definitions

### 1. `@yggdrasil/studio-ui` — YggdrasilStudio React Frontend
- **Build tool:** Vite
- **Framework:** React 18+
- **Language:** TypeScript
- **Location:** `Alfheim/YggdrasilStudio/frontend/`
- **Build output:** `dist/`
- **Current status:** Active, production-ready

### 2. `@yggdrasil/forge-ui` — YggdrasilForge React Frontend
- **Build tool:** Vite
- **Framework:** React 18+
- **Language:** JavaScript (migrating to TypeScript)
- **Location:** `Alfheim/YggdrasilForge/frontend/`
- **Build output:** `dist/`
- **Current status:** Active, in development

### 3. `@yggdrasil/dashboard-ui` — HTMX Dashboard
- **Build tool:** None (HTMX + Jinja2, no bundling needed)
- **Framework:** HTMX + Alpine.js
- **Location:** `Alfheim/dashboard/`
- **Build output:** N/A (served directly by FastAPI)
- **Current status:** Active, minimal build needs
- **Turbo role:** Config tracking only (lint, type-check shared components)

### 4. `@yggdrasil/shared` — Shared Nordic Theme + Configs
- **Build tool:** tsup (for shared component library)
- **Framework:** React (for shared components)
- **Language:** TypeScript
- **Location:** `packages/shared/`
- **Build output:** `dist/` (shared component library)
- **Current status:** To be created

---

## Shared Configurations

### TypeScript (`tsconfig.json`)
```json
{
  "compilerOptions": {
    "target": "ES2022",
    "module": "ESNext",
    "moduleResolution": "bundler",
    "jsx": "react-jsx",
    "strict": true,
    "skipLibCheck": true,
    "paths": {
      "@yggdrasil/shared": ["./packages/shared/src"],
      "@yggdrasil/shared/*": ["./packages/shared/src/*"]
    }
  }
}
```

Each package extends this base with:
```json
{
  "extends": "../../tsconfig.base.json",
  "compilerOptions": {
    "outDir": "./dist",
    "rootDir": "./src"
  }
}
```

### TailwindCSS (`tailwind.config.ts`)
```ts
import { sharedTailwindConfig } from '@yggdrasil/shared/tailwind';
export default sharedTailwindConfig;
```

Shared config defines:
- Nordic color palette (frost, aurora, midnight, rune, mead)
- Custom spacing scale (runes: `rune-1` through `rune-12`)
- Animation presets (Bifrost shimmer, Yggdrasil sway)
- Font families (Inter for body, JetBrains Mono for code)

### ESLint & Prettier
- Shared ESLint config with React hooks plugin
- Shared Prettier config with Nordic code style
- Override per-package if needed

---

## Turbo Pipeline Configuration

### `turbo.json` (at project root)
```json
{
  "$schema": "https://turbo.build/schema.json",
  "globalDependencies": ["**/.env.*local"],
  "globalEnv": ["NODE_ENV", "VITE_API_URL", "VITE_WS_URL"],
  "pipeline": {
    "build": {
      "dependsOn": ["^build"],
      "outputs": ["dist/**", ".next/**", "!.next/cache/**"],
      "env": ["VITE_API_URL", "VITE_WS_URL"]
    },
    "dev": {
      "cache": false,
      "persistent": true,
      "env": ["VITE_API_URL", "VITE_WS_URL", "PORT"]
    },
    "lint": {
      "dependsOn": ["^build"],
      "outputs": []
    },
    "type-check": {
      "dependsOn": ["^build"],
      "outputs": []
    },
    "test": {
      "dependsOn": ["build"],
      "outputs": ["coverage/**"],
      "env": ["CI"]
    },
    "clean": {
      "cache": false
    }
  }
}
```

---

## Build Caching Strategy for CI

### Local Caching
- Turborepo caches build outputs in `.turbo/cache/`
- `.gitignore` includes `.turbo/` — never commit cache
- Cache hit: same input hash → skip build entirely

### Remote Caching (GitHub Actions)
```yaml
# .github/workflows/build.yml
- name: Turbo Cache
  uses: actions/cache@v4
  with:
    path: .turbo
    key: turbo-${{ runner.os }}-${{ github.sha }}
    restore-keys: |
      turbo-${{ runner.os }}-

- name: Build
  run: pnpm turbo build --filter=@yggdrasil/...
```

### Cache Invalidation
- **Content change:** Input file hash changes → cache miss → rebuild
- **Config change:** `tsconfig.json`, `tailwind.config.ts` → full cache miss
- **Dependency change:** `package-lock.yaml` change → full cache miss

---

## Dev Server Parallel Execution

```bash
# Start all dev servers in parallel
pnpm turbo dev --filter=@yggdrasil/...

# Or individually
pnpm turbo dev --filter=@yggdrasil/studio-ui    # Studio on :5174
pnpm turbo dev --filter=@yggdrasil/forge-ui     # Forge on :5175

# Build shared first, then apps
pnpm turbo build --filter=@yggdrasil/shared
pnpm turbo build --filter=@yggdrasil/studio-ui
```

### Vite Config for Dev Server Ports
```ts
// studio-ui/vite.config.ts
export default defineConfig({
  server: {
    port: 5174,
    proxy: {
      '/api': 'http://localhost:8081',
      '/ws': { target: 'ws://localhost:8081', ws: true },
    },
  },
});

// forge-ui/vite.config.ts
export default defineConfig({
  server: {
    port: 5175,
    proxy: {
      '/api': 'http://localhost:8081',
    },
  },
});
```

---

## Migration Phases

### Phase 1: Setup Turborepo + Workspace Config (2 days)
**Goal:** Add Turborepo to the project without breaking existing builds.

- [ ] Create `turbo.json` at project root with pipeline definitions
- [ ] Create/update root `package.json` with workspace config
- [ ] Add `packages/shared/` directory structure with `package.json`
- [ ] Install Turborepo as dev dependency: `pnpm add -Dw turbo`
- [ ] Add `turbo` scripts to root `package.json`
- [ ] Verify existing builds still work: `pnpm turbo build`
- [ ] Add `.turbo/` to `.gitignore`
- [ ] Update CI workflow to use `pnpm turbo build`

**Deliverables:**
- Working Turborepo setup
- All existing builds passing
- CI using Turborepo

### Phase 2: Extract Shared Theme (3 days)
**Goal:** Move common UI patterns to `@yggdrasil/shared`.

- [ ] Create `packages/shared/src/` directory
- [ ] Extract Nordic theme tokens to `packages/shared/src/styles/nordic.css`
- [ ] Create shared TailwindCSS config in `packages/shared/tailwind.config.ts`
- [ ] Move common components to `packages/shared/src/components/`
  - NordicCard, NordicButton, NordicModal, NordicTheme
- [ ] Move `useWebSocket.js` hook to `packages/shared/src/hooks/`
- [ ] Update `studio-ui` and `forge-ui` to import from `@yggdrasil/shared`
- [ ] Verify all apps build and run correctly
- [ ] Update ESLint and Prettier shared configs

**Deliverables:**
- `@yggdrasil/shared` package published
- Both apps consuming shared components
- Single source of truth for theme

### Phase 3: CI Integration + Optimization (2 days)
**Goal:** Optimize CI pipeline and enable remote caching.

- [ ] Add Turborepo remote caching to GitHub Actions
- [ ] Configure `turbo` to use GitHub Actions cache backend
- [ ] Add `lint` and `type-check` pipelines to CI
- [ ] Verify cache hit behavior on PRs (only rebuild changed packages)
- [ ] Add `test` pipeline for shared package
- [ ] Document the build system in `Svartalfheim/docs/build-system.md`
- [ ] Add `pnpm turbo clean` command and verify it works

**Deliverables:**
- Full CI pipeline with caching
- Documentation for build system
- Developer guide for adding new packages

---

## Potential Pitfalls

| Pitfall | Impact | Mitigation |
|---------|--------|------------|
| Turborepo + pnpm workspaces mismatch | Build errors | Pin exact Turborepo version; test with `pnpm list --depth 0` |
| Circular dependencies between packages | Build hangs | Turborepo detects and warns; enforce DAG dependency tree |
| Shared package breaking changes | App build failures | Use semantic versioning; `changesets` for package versioning |
| Vite HMR not working with workspaces | Dev experience regression | Use `vite.config.ts` `optimizeDeps.include` for shared package |
| CI cache invalidation issues | Slow CI builds | Use content-hash based keys; monitor cache hit rates |
| Dashboard has no build step | Turborepo confusion | Explicit `"build": "echo 'No build needed'"` in dashboard package.json |
| WASM loading in Vite | Module resolution issues | Already handled in plan-22 (Photon); coordinate with that plan |

---

## Commands Reference

```bash
# Install dependencies
pnpm install

# Build everything
pnpm turbo build

# Build only studio-ui and its dependencies
pnpm turbo build --filter=@yggdrasil/studio-ui

# Dev all UIs in parallel
pnpm turbo dev

# Lint all packages
pnpm turbo lint

# Type check all packages
pnpm turbo type-check

# Test all packages
pnpm turbo test

# Clean all build artifacts
pnpm turbo clean

# Force rebuild (ignore cache)
pnpm turbo build --force
```

---

## Success Criteria

- [ ] Turborepo installed and configured at project root
- [ ] `pnpm turbo build` successfully builds all Alfheim frontends
- [ ] `pnpm turbo dev` runs studio-ui and forge-ui in parallel
- [ ] Shared Nordic theme extracted to `@yggdrasil/shared`
- [ ] CI uses Turborepo with remote caching
- [ ] Build times reduced by >30% on cache hits
- [ ] Zero regressions in existing frontend functionality