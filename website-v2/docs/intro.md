---
sidebar_position: 1
title: Yggdrasil — Nine Realms Ecosystem
description: "A personal project ecosystem organized under the Norse Nine Realms metaphor"
---

# Nine Realms. One Tree.

**Yggdrasil** is a personal project ecosystem organized under the Norse Nine Realms metaphor. At its heart lies **Lilith v5.0** — a dark-fantasy CLI agent with hybrid memory, swarm intelligence, MCP protocol, multi-provider LLM, skills framework, batch mode, and real-time dashboard.

```bash
$ git clone https://github.com/BrierAinz/Yggdrasil.git
$ cd Yggdrasil
$ cp Asgard/Lilith/.env.example Asgard/Lilith/.env
$ cd Asgard/Lilith && lilith
```

## What is Yggdrasil?

Yggdrasil is not a monorepo — it is a **living ecosystem** where every project has a purpose, a lifecycle, and a destination realm. Inspired by Norse cosmology, each realm serves a distinct function in the development lifecycle.

> **᛭ Key Principles**
>
> - Every project lives in **exactly one realm** at any time. No duplicates, no chaos.
> - The lifecycle is enforced: `Idea → Muspelheim → [Target Realm] → Helheim (if it dies)`.
> - Lilith is the orchestrator — a local LLM-powered agent with Telegram control, RAG memory, and sub-agent delegation.
> - All communication with the AI flows through a REST Gateway. No cloud dependencies for the core.

## The Nine Realms

Each realm has a single, well-defined purpose. Projects migrate between realms as they evolve, following strict rules defined in `REGLAS_YGGDRASIL.md`.

| Realm | Theme | Purpose |
|-------|-------|---------|
| **Asgard** | Core Technology | Permanent core projects — Lilith, Gateway, LLM providers |
| **Vanaheim** | AI Agents | Bots, agent profiles, communication protocols |
| **Alfheim** | UI Prototypes | Visual experiments, IDE integrations |
| **Svartalfheim** | Knowledge | Documentation, architecture decisions, deployment guides |
| **Muspelheim** | Active Development | Sprint templates, hotfixes, active work |
| **Niflheim** | Resources | Datasets, LLM checkpoints, training data |
| **Midgard** | Personal Apps | Completed, battle-tested applications |
| **Jotunheim** | Massive Projects | Long-term, large-scope projects |
| **Helheim** | Graveyard | Archived code, legacy versions, regenerable trash |

## Lilith — The Crown Jewel of Asgard

The crown jewel of Asgard. A local-first AI assistant that runs entirely on your hardware via LM Studio, with no cloud lock-in. Control it from anywhere through Telegram.

**Request Flow:**

```
You (Telegram) → Telegram Bot → Gateway (FastAPI) → Lilith (Orchestrator) → LM Studio (Local LLM)
```

### Features

- **ᛒ Hybrid Memory** — Vector embeddings + knowledge graph + full-text search (FTS5). Automatic compression, entity extraction, and semantic recall across sessions.
- **ᚹ Swarm Intelligence** — LLM-powered specialist agents (researcher, coder, writer, critic) with file locking, conflict resolution, and persistent sessions via SQLite.
- **ᛏ Task Scheduler** — Cron-like job scheduling with persistent SQLite backend and REST API exposure.
- **ᛇ Multi-Provider LLM** — LM Studio (local) + Kimi (remote) + any OpenAI-compatible provider. Automatic fallback, model auto-detection, and zero-config startup.
- **ᚦ Skills & MCP** — Hot-reloadable skill packs with auto-trigger. MCP (Model Context Protocol) connects external tool servers dynamically. 35+ native tools.
- **ᚠ Plugin Architecture** — Hot-pluggable tools with dynamic discovery, enable/disable, and custom tool registration.
- **ᛗ Real-time Dashboard** — Web dashboard with WebSocket live updates, multi-pane layout, terminal widget, and system monitoring. Dark fantasy aesthetic.
- **ᚨ TOML Config & Resilience** — Unified configuration in `~/.lilith/config.toml`. Circuit breaker, graceful shutdown, error tracking, and automatic recovery.

## Agents of Yggdrasil

Four active agents power the ecosystem, each a specialized LLM personality with a distinct role and context window.

| Agent | Backend Model | Specialty | Context |
|-------|-------------|-----------|---------|
| **Shalltear** | Venice AI (llama-3.3-70b) | Classification, NL parsing, triage | 32k |
| **Adán** | Ollama (qwen2.5-coder:7b) | Code generation, tests, refactoring | 8k |
| **Eva** | Grok (grok-4-fast-reasoning) | Long-context analysis, documentation | 128k |
| **Odín** | Kimi (kimi-for-coding) | Deep analysis, research, creative writing | 262k |

Non-agent components that complement the pantheon:

| Component | Realm | Role |
|-----------|-------|------|
| **Lilith** | Asgard | Core orchestrator — CLI agent with hybrid memory, swarm intelligence, and command over all sub-agents |
| **Bifrost** | Vanaheim | Telegram gateway — the rainbow bridge connecting the ecosystem to the mortal plane |
| **ForgeMaster** | Muspelheim | Build automator — model catalog, GPU detection, VRAM calculator |
| **Dashboard** | Alfheim | Real-time terminal UI — system metrics, Git activity, live telemetry |

## Ecosystem Health

Current state of the major components across all realms.

| Component | Realm | Status | Description |
|-----------|-------|--------|-------------|
| `Lilith` | Asgard | ᛏ Active | Core orchestrator v5.0 — CLI, memory, swarm, MCP, skills, batch, dashboard |
| `Gateway` | Asgard | ᛏ Active | FastAPI REST bridge exposing Telegram, Scheduler, Agents, Plugins |
| `ForgeMaster` | Muspelheim | ᛏ Active | Model catalog, GPU detection, GGUF/safetensors metadata, download manager |
| `TerminalDashboard` | Alfheim | ᛏ Active | Terminal UI with scanner, Git activity, sidebar search, Rich panels |
| `LLM Providers` | Asgard | ᛏ Active | Multi-provider: LM Studio (local), Kimi (remote), OpenAI-compatible, auto-fallback |
| `Hybrid Memory` | Asgard | ᛏ Active | Vector embeddings + knowledge graph + FTS5, auto-compression, entity extraction, session search |
| `Swarm Intelligence` | Asgard | ᛏ Active | LLM-powered specialist agents with file locking, conflict resolution, persistent SQLite sessions |
| `Skills & MCP` | Asgard | ᛏ Active | Hot-reloadable skill packs, MCP protocol, dynamic tool registration, 35+ native tools |
| `Task Scheduler` | Asgard | ᛏ Active | Cron-like scheduling with REST API and persistent storage |
| `Dashboard` | Asgard | ᛏ Active | Real-time web dashboard with WebSocket, multi-pane layout, terminal widget |
| `TOML Config & Resilience` | Asgard | ᛏ Active | Unified config, circuit breaker, graceful shutdown, error tracking, auto-recovery |
| `Telegram Bot` | Vanaheim | ᛏ Active | Remote control interface for the entire ecosystem |
| `VSCode Extension` | Alfheim | ᚦ Prototype | Visual interface for Lilith inside VS Code |
| `Website` | Svartalfheim | ᛏ Active | GitHub Pages documentation site (this page) |