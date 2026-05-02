# Yggdrasil — Project Context for AI Assistants

This file provides context for AI coding assistants (Claude, Cursor, etc.) working on this project.

## Project Overview

Yggdrasil is a personal project ecosystem organized under the Norse Nine Realms metaphor. The crown jewel is **Hermes-Lilith** — a local-first AI agent platform.

## Architecture

```
Yggdrasil/
├── Asgard/          # Core Technology — Hermes-Lilith backend
│   ├── lilith-core/         # Base types, config, logging
│   ├── lilith-memory/       # Vector memory + SQLite
│   ├── lilith-tools/        # PC control, browser, RAG
│   ├── lilith-orchestrator/ # Agent coordination
│   ├── lilith-api/          # FastAPI Gateway + WebSocket
│   ├── lilith-cli/          # Terminal interface
│   └── Hermes-Lilith/       # Legacy (being migrated)
├── Vanaheim/        # AI Agents — Telegram bot, agent framework
├── Alfheim/         # UI Prototypes — React dashboard, VSCode ext
├── Svartalfheim/    # Knowledge Base — Docs, playbooks, ADRs
├── Muspelheim/      # Active Development — Sprint projects, experiments
├── Niflheim/        # Resources — Datasets, models, assets
├── Midgard/         # Personal Apps — Finished daily-use apps
├── Jotunheim/       # Massive Projects — Long-term builds
└── Helheim/         # Graveyard — Archived projects
```

## Key Rules (REGLAS_YGGDRASIL.md)

1. **One project = one realm** — never duplicate across realms
2. **Lifecycle**: Idea → Muspelheim → Target Realm → Helheim (if dead)
3. **All code follows ruff linting** — `ruff check .`
4. **All packages use `pyproject.toml`** with `[project]` metadata
5. **`.env` files are NEVER committed** — always in `.gitignore`
6. **Telegram bot owner-only** — single user system, no multi-user

## Development Commands

```bash
# Install all packages in dependency order
pip install -e Asgard/lilith-core -e Asgard/lilith-memory -e Asgard/lilith-tools \
             -e Asgard/lilith-orchestrator -e Asgard/lilith-api -e Asgard/lilith-cli \
             -e Vanaheim/vanaheim-framework

# Run tests
pytest

# Lint
ruff check .
ruff format .

# Type check
pyright Asgard/lilith-core/lilith_core
```

## Tech Stack

- **Language**: Python 3.10+
- **Backend**: FastAPI + WebSocket on port 8000
- **LLM Provider**: LM Studio (localhost:1234) — OpenAI-compatible API
- **Fallback Provider**: Kimi Code (api.kimi.com/coding/v1, model: kimi-for-coding, header: X-Client: claude-code)
- **Memory**: Sentence-transformers embeddings + SQLite
- **Bot**: python-telegram-bot
- **Dashboard**: React + TypeScript + Vite (port 3000)
- **Packaging**: pyproject.toml with [project] metadata per module

## Module Dependency Order

`lilith-core` → `lilith-memory` → `lilith-tools` → `lilith-orchestrator` → `lilith-api` → `lilith-cli`

Each module depends on the previous one. Install in order.

## Current Status

- Lilith v4.0.0 released — 838 tests passing
- Modular package architecture (6 packages)
- Swarm coordination (Phase 3) partially implemented
- Active development on batch mode and MCP support
