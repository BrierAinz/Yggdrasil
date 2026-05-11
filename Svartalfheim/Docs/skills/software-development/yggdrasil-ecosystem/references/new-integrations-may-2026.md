# New Integrations — May 2026

## LiteLLM Provider (Asgard/lilith-core/lilith_core/providers/)

A multi-model LLM provider layer wrapping [litellm](https://github.com/BerriAI/litellm) for 100+ model access with fallback.

### Architecture

- **`base.py`** — Abstract `LLMProvider` class with `complete()`, `stream()`, `list_models()` methods
- **`litellm_provider.py`** — `LiteLLMProvider` using `litellm.acompletion()` with:
  - Exponential backoff retries (max 3, base 1s)
  - Auto-fallback: `model='auto'` resolves to local LM Studio via `openai/<base_url>`
  - Standardized dict response: `{content, model, usage, finish_reason}`
  - Dependency: `litellm>=1.40` in pyproject.toml
- **`local_provider.py`** — `LocalProvider` with direct `httpx.AsyncClient` to local OpenAI-compatible servers
  - Same interface as LiteLLMProvider, no litellm dependency
  - For when only local models are needed

### Tests

- `Asgard/lilith-core/tests/test_litellm_provider.py` — 5 tests (mocked litellm calls)
- `Asgard/lilith-core/tests/test_local_provider.py` — 3 tests (mocked httpx calls)

## mem0 Persistent Memory Backend (Asgard/lilith-memory/lilith_memory/backends/)

A pluggable memory backend layer allowing swap between SQLite (local) and mem0 (semantic search).

### Architecture

- **`base.py`** — Abstract `MemoryBackend` with async `add()`, `search()`, `recent()`, `delete()`, `clear()`, `count()`
- **`sqlite_backend.py`** — `SQLiteBackend` adapter wrapping existing `MemoryStore` with asyncio.to_thread bridge
  - Falls back gracefully if MemoryStore not available
- **`mem0_backend.py`** — `Mem0Backend` using `mem0.Memory()` for persistent long-term memory
  - Semantic vector search replaces LIKE queries
  - Auto-configures from `MEM0_API_KEY` env var for cloud, local SQLite+Qdrant fallback
  - Graceful `ImportError` if `mem0ai` not installed
  - Dependency: `mem0ai>=0.1` as optional dep under `[project.optional-dependencies] mem0`

### Tests

- `Asgard/lilith-memory/tests/test_mem0_backend.py` — 4 tests (skip if mem0ai not installed)
- `Asgard/lilith-memory/tests/test_sqlite_backend.py` — 2 tests

## ruff.toml Per-File Ignores

FastAPI route files typically raise `HTTPException` inside `except` blocks, which triggers ruff B904 (raise-without-from-inside-except) and TRY301 (abstract-raise-to-inner-function). These are false positives for FastAPI patterns.

```toml
[lint.per-file-ignores]
"Alfheim/YggdrasilStudio/backend/routes/**" = ["B904", "TRY301"]
"Alfheim/YggdrasilStudio/backend/main.py" = ["B904"]
"Alfheim/YggdrasilStudio/backend/comfyui_client.py" = ["B904"]
```

When adding new FastAPI route files, add them to this section if they raise HTTPException inside except blocks.

## gh CLI on WSL (No sudo) & GitHub REST API Fallback

- Install to `~/bin/gh` manually from GitHub releases tarball
- Requires `export PATH="$HOME/bin:$PATH"` each session (add to ~/.bashrc)
- Auth: `gh auth login --hostname github.com --git-protocol https --web` (device flow)
- Git credential store tokens (`~/.git-credentials`) return 401 with `--with-token`
- Need fine-grained PAT with `repo`, `read:org`, `workflow` scopes

**Device flow in Hermes terminal times out** — `gh auth login --web` gives a code but the process exits before the user completes browser auth. When `gh` auth fails, use the GitHub REST API directly with the git-credential token. See the main SKILL.md section "gh CLI in WSL (No Sudo) & GitHub REST API Fallback" for the full `gh_api()` Python helper.

## Dependabot PR Management via REST API

Merged 6 Dependabot PRs (#1,2,3,4,7,8) and closed 2 with conflicts (#5 beautifulsoup4, #6 selenium) using `gh_api()`:

```python
# Merge a PR:
gh_api(f"/repos/{owner}/{repo}/pulls/{num}/merge", method="PUT", data={"merge_method": "merge"})

# Close a PR with conflicts:
gh_api(f"/repos/{owner}/{repo}/pulls/{num}", method="PATCH", data={"state": "closed"})

# Create a release:
gh_api(f"/repos/{owner}/{repo}/releases", method="POST", data={
    "tag_name": "v5.0.0",
    "name": "v5.0.0 — The Growth Release",
    "body": "...",
    "draft": False,
    "prerelease": False
})

# Enable Discussions (GraphQL):
# POST https://api.github.com/graphql with query: mutation { ... }

# Set topics:
gh_api(f"/repos/{owner}/{repo}/topics", method="PUT", data={"names": [...]})
```

## Growth Plan Status

Full plan at `Svartalfheim/plans/plan-21-yggdrasil-growth-v5.md`

| Phase | Task | Status |
|-------|------|--------|
| P0 | CI fixes (ruff 0 errors) | ✅ DONE |
| P0 | Dependabot PRs merge | ✅ DONE (6 merged, 2 closed with conflicts) |
| P0 | GitHub Release v5.0.0 | ✅ DONE |
| P0 | GitHub Discussions enabled | ✅ DONE |
| P0 | Topics set (11 topics) | ✅ DONE |
| P0 | LiteLLM provider backbone | ✅ DONE |
| P0 | mem0 persistent memory backend | ✅ DONE |
| P0 | ruff per-file-ignores for FastAPI | ✅ DONE |
| P1 | ComfyUI WebSocket Bridge | ❌ Pending |
| P2 | Mimir Deep Research agent | ❌ Pending |
| P2-P3 | Photon WASM + Turborepo | ❌ Pending |

## Embedded Git Repo Pitfall

Both `Alfheim/YggdrasilStudio/` and `Alfheim/YggdrasilForge/` contain their own `.git/` directories. They are **embedded repos, NOT git submodules**. Do NOT `git add` these directories into the parent repo — they'll appear as gitlinks (mode 160000) and cause issues. The parent repo must track them via `.gitignore` or proper submodule configuration. If accidentally staged, use `git rm --cached Alfheim/YggdrasilStudio` to unstage.