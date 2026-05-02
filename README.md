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
[![CI](https://github.com/BrierAinz/Yggdrasil/actions/workflows/ci.yml/badge.svg)](https://github.com/BrierAinz/Yggdrasil/actions/workflows/ci.yml)
[![Deploy](https://github.com/BrierAinz/Yggdrasil/actions/workflows/deploy-website.yml/badge.svg)](https://github.com/BrierAinz/Yggdrasil/actions/workflows/deploy-website.yml)
[![Security](https://img.shields.io/badge/Security-Policy-blue.svg)](SECURITY.md)
[![PRs Welcome](https://img.shields.io/badge/PRs-Welcome-brightgreen.svg)](CONTRIBUTING.md)

[Website](https://brierainz.github.io/Yggdrasil) · [Setup](#quick-start) · [Architecture](#architecture) · [Realms](#the-nine-realms) · [Docs](#documentation)

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

<details>
<summary><b>📦 Alternative: GitHub Codespaces</b></summary>

Click the **Code** button on the repo page and select **Codespaces** → **Create codespace on main**. The devcontainer will auto-install Python 3.11, all dependencies, and pre-commit hooks.

You'll still need to set up:
1. LM Studio running locally (or configure a remote LLM endpoint)
2. A `.env` file with your `TELEGRAM_BOT_TOKEN` and `CHAT_ID`

</details>

<details>
<summary><b>🐍 Manual Python Setup</b></summary>

```bash
# Create virtual environment
python -m venv .venv
source .venv/bin/activate  # Linux/macOS
# .venv\Scripts\activate   # Windows

# Install core dependencies
pip install -r requirements.txt

# Install each Lilith module in dependency order
pip install -e Asgard/lilith-core
pip install -e Asgard/lilith-memory
pip install -e Asgard/lilith-tools
pip install -e Asgard/lilith-orchestrator
pip install -e Asgard/lilith-api
pip install -e Asgard/lilith-cli
pip install -e Vanaheim/vanaheim-framework

# Run tests
pytest

# Format & lint
pre-commit install
pre-commit run --all-files
```

</details>

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
| 🔄 **Batch Mode** | Run prompts from CLI with `--batch` flag for automation pipelines. |

<details>
<summary><b>🔍 Technical Architecture Details</b></summary>

### Modular Package Structure (v4.0+)

Hermes-Lilith is now a modular package ecosystem:

| Package | Purpose | Key Exports |
|---------|---------|-------------|
| `lilith-core` | Base types, config, logging | `LilithConfig`, `LilithBase` |
| `lilith-memory` | Vector memory + SQLite | `EnhancedMemory`, `EntityTracker` |
| `lilith-tools` | PC control, browser, RAG | `ToolRegistry`, `FileSystemTool` |
| `lilith-orchestrator` | Agent coordination | `Orchestrator`, `AgentConfig` |
| `lilith-api` | FastAPI Gateway + WebSocket | `Gateway`, health endpoints |
| `lilith-cli` | Terminal interface | `LilithCLI`, batch mode |

### Swarm Coordination (Phase 3)

The `Lilith/Swarm/` module provides:
- **MessageBus**: Thread-safe pub/sub for inter-agent communication
- **SwarmAgent**: Autonomous agents with status tracking and file locking
- **SwarmManager**: Lifecycle management, conflict detection, background coordination

</details>

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

<details>
<summary><b>🧪 Testing Details</b></summary>

The test suite runs across all Lilith modules:

```bash
# Run all tests
pytest

# Run specific module tests
pytest Asgard/lilith-core/tests     # Core functionality
pytest Asgard/lilith-memory/tests    # Memory & embeddings
pytest Asgard/lilith-tools           # Tools & PC control
pytest Asgard/lilith-orchestrator    # Agent orchestration
pytest Asgard/lilith-api/tests       # API endpoints
pytest Asgard/lilith-cli/tests       # CLI interface
pytest Vanaheim/vanaheim-framework   # Agent framework
```

CI runs on every push to `main` with ruff linting, pytest, and pyright type checking.

</details>

---

## Documentation

| Doc | Description |
|-----|-------------|
| [API Reference](docs/API.md) | Complete HTTP and WebSocket endpoint documentation |
| [Architecture](docs/ARCHITECTURE.md) | System diagrams, data flow, and deployment topology |
| [Tutorials by Realm](docs/TUTORIALS.md) | Step-by-step guides for each of the Nine Realms |
| [Changelog](CHANGELOG.md) | Version history and release notes |
| [Contributing](CONTRIBUTING.md) | How to contribute, realm rules, and PR guidelines |
| [Security](SECURITY.md) | Vulnerability reporting and security policy |

---

## Contributing

We welcome contributions! Whether you're fixing a bug, adding a feature, or improving documentation, please read our [Contributing Guide](CONTRIBUTING.md) first.

Key points:
- Every project belongs to exactly one **Realm** — check `REGLAS_YGGDRASIL.md` for the rules
- Use the [bug report](https://github.com/BrierAinz/Yggdrasil/issues/new?template=bug_report.yml) or [feature request](https://github.com/BrierAinz/Yggdrasil/issues/new?template=feature_request.yml) templates
- All PRs must pass CI (ruff lint, pytest, pyright)
- New projects start in **Muspelheim** — the realm of active development

---

## License

MIT — See [LICENSE](LICENSE) for details.

---

<div align="center">

🌳 **Built with patience in the Nine Realms.**

[Website](https://brierainz.github.io/Yggdrasil) · [GitHub](https://github.com/BrierAinz/Yggdrasil) · [Issues](https://github.com/BrierAinz/Yggdrasil/issues) · [Discussions](https://github.com/BrierAinz/Yggdrasil/discussions)

</div>
