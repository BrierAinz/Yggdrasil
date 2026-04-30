<div align="center">

# 🌳 Yggdrasil

> *"Del caos del vacio, Yggdrasil crece con raices profundas y ramas que tocan todos los cielos."*

**A personal project ecosystem organized under the Norse Nine Realms metaphor.**

[![License: MIT](https://img.shields.io/badge/License-MIT-f59e0b.svg)](LICENSE)
[![Python 3.10+](https://img.shields.io/badge/Python-3.10+-22d3ee.svg)](https://python.org)
[![Status](https://img.shields.io/badge/Status-Active-34d399.svg)]()
[![GitHub Stars](https://img.shields.io/github/stars/BrierAinz/Yggdrasil?style=flat&color=fbbf24)](https://github.com/BrierAinz/Yggdrasil/stargazers)
[![GitHub Last Commit](https://img.shields.io/github/last-commit/BrierAinz/Yggdrasil?color=a78bfa)](https://github.com/BrierAinz/Yggdrasil/commits/main)
[![Repo Size](https://img.shields.io/github/repo-size/BrierAinz/Yggdrasil?color=fb7185)](https://github.com/BrierAinz/Yggdrasil)

[Website](https://brierainz.github.io/Yggdrasil) · [Setup](#quick-start) · [Architecture](#architecture) · [Realms](#the-nine-realms)

</div>

---

## What is Yggdrasil?

Yggdrasil is not a monorepo — it is a **living ecosystem** where every project has a purpose, a lifecycle, and a destination realm. Inspired by Norse cosmology, each of the **Nine Realms** serves a distinct function in the development lifecycle.

The crown jewel is **Hermes-Lilith**: a local-first AI agent that runs entirely on your hardware via LM Studio, with no cloud lock-in. Control it from anywhere through Telegram. It remembers conversations with vector embeddings, delegates tasks to sub-agents, schedules jobs, and can literally control your PC.

### Key Principles

- **Every project lives in exactly one realm** at any time. No duplicates, no chaos.
- **Strict lifecycle**: Idea → Muspelheim → [Target Realm] → Helheim (if it dies).
- **Local-first AI**: The LLM runs on your machine. Your data never leaves.
- **Single owner**: Designed for personal use. Telegram bot only responds to you.

---

## Quick Start

```bash
# Clone the tree
git clone https://github.com/BrierAinz/Yggdrasil.git
cd Yggdrasil

# Configure environment
cp Asgard/Hermes-Lilith/.env.example Asgard/Hermes-Lilith/.env
# Edit .env with your Telegram bot token and chat ID

# Start LM Studio with a loaded model on localhost:1234

# Launch everything
start_lilith.bat        # Windows
# Or manually:
#   cd Asgard/lilith-orchestrator/gateway && uvicorn gateway:app --port 8000
#   cd Vanaheim/Bots_Lilith_v5/telegram && python bot.py
```

---

## The Nine Realms

| Realm | Purpose | Projects |
|-------|---------|----------|
| 🏰 **Asgard** | Core Technology | Hermes-Lilith, Gateway, Memory, Scheduler |
| 🤖 **Vanaheim** | AI Agents | Telegram Bot, Bridge, Agent Framework |
| ✨ **Alfheim** | UI Prototypes | VSCode Extension, Visual Experiments |
| 📚 **Svartalfheim** | Knowledge Base | Docs, Playbooks, Architecture Decisions |
| 🔥 **Muspelheim** | Active Development | Sprint projects, quick experiments |
| ❄️ **Niflheim** | Resources | Datasets, Models, Assets |
| 🌍 **Midgard** | Personal Apps | Finished applications for daily use |
| 🐉 **Jotunheim** | Massive Projects | Long-term builds (>1 month) |
| ☠️ **Helheim** | Graveyard | Archived, dead, or quarantined projects |

[Explore all realms →](https://brierainz.github.io/Yggdrasil/realms.html)

---

## Architecture

```
You (Telegram)
      ↓
Telegram Bot  ---------→  VSCode Ext  ---------→  CLI
      ↓                        ↓                  ↓
      ┌────────────────────────────────────┐
      │         Gateway (FastAPI :8000)          │
      └────────────────────────────────────┘
                          ↓
      ┌────────────────────────────────────┐
      │      Hermes-Lilith (Orchestrator)       │
      │  ┌──────┐ ┌──────┐ ┌──────┐ ┌──────┐  │
      │  │Memory│ │Agents│ │Sched.│ │Plugin│  │
      │  └──────┘ └──────┘ └──────┘ └──────┘  │
      └────────────────────────────────────┘
                          ↓
                    LM Studio (localhost:1234)
```

[Full architecture details →](docs/architecture.html)

---

## Hermes-Lilith Features

| Feature | Description |
|---------|-------------|
| 🔍 **Vector Memory** | Sentence-transformer embeddings + SQLite. Auto-compression, entity extraction, semantic retrieval. |
| 🤖 **Sub-Agent Delegation** | Spawn autonomous coding agents with isolated contexts for parallel workstreams. |
| 📅 **Task Scheduler** | Cron-like scheduling with persistent SQLite backend and REST API. |
| 🔑 **PC Control** | File system, process management, Windows automation, browser, screenshots. |
| 📚 **RAG Pipeline** | Document ingestion, chunking, embedding, semantic search for knowledge bases. |
| 🚀 **Plugin System** | Hot-pluggable tools with dynamic discovery and runtime enable/disable. |
| 📱 **Telegram Control** | Remote interface from anywhere. Owner-only access. |

[Agent specs →](https://brierainz.github.io/Yggdrasil/hermes-lilith.html)

---

## Hardware Requirements

| Tier | RAM | GPU | Models | Performance |
|------|-----|-----|--------|-------------|
| Minimum | 16GB | — | 7B (Q4) | Functional |
| Recommended | 32GB+ | 4GB+ VRAM | 13-27B | Fast, good context |
| Reference | 48GB DDR4 | RTX 3060 4GB | Up to 27B | Comfortable |

---

## Development

```bash
# Run tests
pytest

# Format code
pre-commit install
pre-commit run --all-files
```

---

## License

MIT ¹ See [LICENSE](LICENSE) for details.

---

<div align="center">

🌳 **Built with patience in the Nine Realms.**

[Website](https://brierainz.github.io/Yggdrasil) · [GitHub](https://github.com/BrierAinz/Yggdrasil)

</div>
