---
<<<<<<< HEAD
sidebar_position: 5
title: Lilith v5.1
---

# Lilith — The AI Agent

Lilith is a modular AI coding agent inspired by Hermes Agent and Claude Code. She lives in Asgard and manages the entire Yggdrasil ecosystem.

## Architecture

| Component | File | Description |
|-----------|------|-------------|
| Agent | `lilith_agent.py` | Main AI agent engine |
| Chat CLI | `lilith_cli.py` | Interactive chat interface |
| CLI | `ygg.py` | Nordic Frost CLI (Rich) |
| Memory | `advanced_memory.py` | Embeddings + semantic search |
| Skills | `skill_creator.py` | Auto-create skills from conversations |
| Auto-improve | `auto_improvement.py` | Pattern analysis and auto-improvement |
| Permissions | `agent_permissions.json` | Access control |

## Memory System

SQLite backend with Sentence Transformer embeddings:

- **Storage:** Content + metadata + 384-dim vectors
- **Search:** Semantic similarity (not just text matching)
- **Commands:** `memoria`, `resumen`, `borrar`

## Skills

Reusable procedures stored as markdown:

```
~/.hermes/skills/category/skill-name/SKILL.md
```

Skills have: trigger conditions, numbered steps, pitfalls, verification.

## Multi-Provider LLM

| Provider | Models | Config |
|----------|--------|--------|
| MiMo | V2.5-Pro, V2.5, V2.5-TTS | `MIMO_API_KEY` |
| BytePlus | Seed 2.0, DeepSeek, GLM-4 | `BYTEPLUS_API_KEY` |
| OpenAI | GPT-4, GPT-3.5 | `OPENAI_API_KEY` |
| Anthropic | Claude 3.5 | `ANTHROPIC_API_KEY` |

## v5.1 Modular Packages

Lilith v5.0 broke the 83MB monolith into 8 packages:

| Package | Version | Status | Description |
|---------|---------|--------|-------------|
| lilith-core | 2.1.0 | Active | Types, config, logger, providers |
| lilith-memory | 1.0.0 | Active | SQLite memory store |
| lilith-api | 1.0.0 | Skeleton | FastAPI Gateway |
| lilith-bridge | 1.0.0 | Skeleton | Telegram/Discord bridge |
| lilith-cli | 3.0.0 | Skeleton | Terminal interface |
| lilith-orchestrator | 1.0.0 | Skeleton | Agent coordination |
| lilith-skills | 1.0.0 | Skeleton | Skill management |
| lilith-tools | 1.0.0 | Skeleton | PC control, browser, RAG |
=======
sidebar_position: 4
title: Lilith v5.0
description: "Lilith v5.0: dark-fantasy CLI agent — hybrid memory, swarm intelligence, and forged-iron runic architecture"
---

# Lilith v5.0

A **dark-fantasy CLI agent** forged in the ancient fires of Yggdrasil. Hybrid memory, swarm intelligence, MCP protocol, multi-provider LLM, batch mode, skills with hot-reload, and real-time dashboard. No cloud lock-in. No subscription. Control your realm from Telegram or the terminal.

```bash
$ cd Asgard/Lilith
$ cp .env.example .env      # Configure your API keys
$ lilith                    # Run from anywhere
```

## Why local-first?

Lilith is forged on an ancient principle: **your data stays in your hall**. The LLM runs through LM Studio (localhost:1234). Memory is stored in local SQLite. Files never leave your drive. Telegram is just the raven messenger — the brain resides in your own forge.

> **᛭ Key Facts**
>
> - **No API keys required** for the core. LM Studio serves the model locally. Kimi available as remote fallback.
> - **Works offline** once LM Studio is loaded. Telegram needs internet, but the agent brain doesn't.
> - **48GB RAM + RTX 3060** can run models up to ~27B parameters with CPU offload.
> - **Multi-provider** — automatic fallback from LM Studio to Kimi to any OpenAI-compatible API.
> - **Model auto-detection** — "auto" in config picks the best loaded model from LM Studio.
> - **838 tests passing** — Core, Memory, Swarm, MCP, Dashboard, CLI, TOML Config, Batch, E2E.

## How it works

Lilith v5.0 is organized in Six Realinos — each a module with its own law, all nourished by the same roots. The Orchestrator coordinates Skills, Memory, LLM Providers, Swarm, MCP, and Tools through a unified TOML configuration.

```
You (Telegram App) → Telegram Bot (Vanaheim) → [HTTP] → Gateway (FastAPI :8000) → Lilith (Orchestrator) → LM Studio (Local LLM)
```

## The Gateway

The Gateway is the single point of contact for all external interfaces. It exposes REST endpoints for Telegram, file system operations, scheduler tasks, agents, plugins, memory, swarm, skills, and MCP.

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/api/telegram/chat` | POST | Main chat endpoint for Telegram messages |
| `/api/telegram/pregunta_rapida` | POST | Quick questions (no context persistence) |
| `/api/telegram/confirm` | POST | Human-in-the-loop confirmation |
| `/api/pc/fs` | GET/POST | File system operations |
| `/api/scheduler/tasks` | GET/POST | List or create scheduled tasks |
| `/api/agents` | GET/POST | List or spawn sub-agents |
| `/api/plugins` | GET | List available plugins and tools |
| `/api/memory/*` | Various | Vector memory read/write/search |
| `/api/swarm/*` | GET/POST | Swarm management: spawn, status, kill, save, load, history |
| `/api/skills` | GET/POST | List registered skills, trigger, hot-reload |
| `/api/mcp` | GET/POST | MCP server connection status and management |

## Core Components

### ᛒ Hybrid Memory (FASE 2)

Three-layer memory: vector embeddings (sentence-transformers), knowledge graph (NetworkX), and full-text search (FTS5). Auto-compression, entity extraction, session search, and context injection into every prompt. The agent remembers who you are and what you did.

### ᚨ Multi-Provider LLM (FASE 7)

LM Studio for local inference, Kimi (Moonshot) for remote, and any OpenAI-compatible provider. Automatic fallback when the primary provider fails. Model auto-detection via `/models`. Zero-config startup — just start LM Studio and go.

### ᚹ Swarm Intelligence (FASE 9)

Spawn LLM-powered specialist agents — researcher, coder, writer, critic — each with its own context and tool access. File locking prevents conflicts. Code shift notifications keep agents aware. Persistent sessions via SQLite. `/swarm spawn`, `/swarm status`, `/swarm history`.

### ᛏ Skills & MCP (FASE 8)

Hot-reloadable skill packs with auto-trigger. Skills inject context into prompts when relevant. MCP (Model Context Protocol) connects external tool servers dynamically. 35+ native tools for files, system, network, browser, desktop, coding, and more.

### ᛗ Task Scheduler

Cron-like scheduling with persistent SQLite storage. Create, list, run, and delete tasks via REST or CLI. The scheduler wakes up the agent at the right time to execute background jobs.

### ᛇ Real-time Dashboard (FASE 10)

Web dashboard with WebSocket live updates, multi-pane layout, terminal widget, and system monitoring. Watch agent activity, memory recall, swarm coordination, and tool invocations as they happen. Dark fantasy aesthetic throughout.

### ᚺ Plugin Architecture

Hot-pluggable tools with dynamic discovery. Enable/disable plugins at runtime. Custom tools registered by dropping a Python file in the plugins directory. Dynamic Tool Registry integrates MCP and native tools seamlessly.

### ᛚ RAG Pipeline

Document ingestion with chunking, embedding via sentence-transformers, and semantic retrieval. Build a personal knowledge base the agent queries in real time. Index with `/index`, search with `/search`.

### ᚦ PC Control

35+ native tools: file system, process management, Windows automation, browser interaction, coding assistant, network operations, desktop control. The agent can literally use your computer.

### ᛊ TOML Config & Resilience (FASE 10)

Unified configuration in `~/.lilith/config.toml`. Priority: TOML \> env vars \> defaults. Circuit breaker for provider failures, graceful shutdown, error tracking, and automatic recovery.

## CLI & Telegram Commands

Control Lilith through the terminal CLI or remotely via Telegram. Both interfaces share the same Orchestrator, memory, and tools.

| Command | Description |
|---------|-------------|
| `/start` | Initialize the bot and show welcome message |
| `/status` | Check Gateway health, memory stats, and active agents |
| `/memory` | Inject a memory entry into the vector database |
| `/recall` | Search memories by semantic similarity |
| `/tasks` | List scheduled tasks (via Gateway scheduler API) |
| `/agents` | List active sub-agents and their stats |
| `/swarm spawn <task>` | Spawn a swarm of specialist agents for parallel work |
| `/swarm status` | Show active swarm agents and their progress |
| `/swarm history` | List past swarm sessions from SQLite |
| `/skills` | List registered skill packs and their status |
| `/mcp` | Show MCP server connection status and available tools |
| `/recall <query>` | Semantic search across all memories (vector + graph + FTS5) |
| `/compact` | Compress old memories to free context window |
| `/index <path>` | Index files/folder for RAG semantic search |
| `/search <query>` | Search indexed documents semantically |
| `/dashboard` | Start/stop the real-time web dashboard |
| `/stream` | Toggle streaming mode on/off |
| `/plugins` | List available plugins and tools |
| `/batch <prompt>` | Run Lilith in batch mode with no interactive session |
| `(any text)` | Sent to Lilith for processing with full context |

## Recommended Specs

Lilith is designed to run on consumer hardware. You don't need a data center — just a worthy forge.

| | Minimum | Recommended | Reference Build |
|---|---------|-------------|-----------------|
| RAM | 16GB | 32GB+ | 48GB DDR4 |
| CPU | Any modern | 6+ core | AMD Ryzen 5 5500 (6c/12t) |
| GPU | — | NVIDIA 12GB+ VRAM | NVIDIA RTX 3060 12GB |
| Disk | ~10GB free | SSD | Dual SSD setup |
| Models | 7B params (Q4) | 13-27B params | 27B comfortably |
| Experience | Slow but functional | Fast responses, good context | Smooth |
>>>>>>> origin/main
