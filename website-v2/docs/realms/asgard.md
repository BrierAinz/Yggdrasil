---
sidebar_position: 1
title: "Asgard — Core Infrastructure"
---

# Asgard — Core Infrastructure

Asgard is the heart of Yggdrasil. It contains the 8 `lilith-*` packages that form the core infrastructure.

## Active Packages

### lilith-core (v2.1.0)
Base types, configuration, logging, and LLM provider management.

Modules:
- `config.py` — Centralized configuration
- `types.py` — Base types and dataclasses
- `logger.py` — Structured logging
- `providers.py` — Multi-provider LLM management

### lilith-memory (v1.0.0)
Vector memory store with SQLite backend.

Modules:
- `store.py` — Memory store with embeddings and search

## Skeleton Packages

| Package | Description |
|---------|-------------|
| lilith-api | FastAPI Gateway with WebSocket |
| lilith-bridge | Telegram/Discord bridge |
| lilith-cli | Terminal interface |
| lilith-orchestrator | Agent coordination |
| lilith-skills | Skill management |
| lilith-tools | PC control, browser, RAG |

Each has `pyproject.toml` + `__init__.py` but no implementation yet.HEREDOC
