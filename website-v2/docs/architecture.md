---
sidebar_position: 2
title: Architecture
---

# Architecture

Yggdrasil follows a modular architecture organized in 9 realms with clear separation of concerns.

## Monorepo Structure

```
Yggdrasil/
├── Asgard/          # Core — 8 lilith-* packages
├── Vanaheim/        # AI Agents
├── Alfheim/         # UI
├── Svartalfheim/    # Docs, scripts, plans
├── Muspelheim/      # WIP projects
├── Niflheim/        # Assets (gitignored)
├── Helheim/         # Archive
├── Jotunheim/       # Massive (reserved)
├── Midgard/         # Personal
├── ygg.py           # CLI principal (Nordic Frost)
├── lilith_agent.py  # Agente IA
├── lilith_cli.py    # Chat CLI
└── pyproject.toml   # Workspace config (uv)
```

## Package Architecture (Asgard)

```
lilith-core (2.1.0)          lilith-memory (1.0.0)
├── config.py                └── store.py
├── types.py                     (SQLite + embeddings)
├── logger.py
└── providers.py

lilith-api                   lilith-bridge
(FastAPI Gateway)            (Telegram/Discord)

lilith-cli                   lilith-orchestrator
(Terminal Interface)         (Agent Coordination)

lilith-skills                lilith-tools
(Skill Management)           (PC Control, Browser, RAG)
```

## Services

| Service | Port | Package | Description |
|---------|------|---------|-------------|
| API Gateway | 8000 | lilith-orchestrator | REST + WebSocket |
| Model Orchestrator | 8001 | lilith-orchestrator | LLM management |
| Memory Service | 8002 | lilith-memory | Vector memory |

## Build System

- **Python:** >=3.11
- **Package manager:** uv (workspace members)
- **Build backend:** hatchling
- **Linting:** ruff
- **Testing:** pytest
- **CI:** GitHub Actions
