---
sidebar_position: 1
title: Yggdrasil — Nine Realms Ecosystem
slug: /intro
---

# Yggdrasil — Nine Realms Ecosystem

> **Version 5.1.0** — Lilith reforged into modular packages

Yggdrasil is a personal project ecosystem organized under the Norse Nine Realms metaphor. At its heart lies **Lilith v5.1** — a dark-fantasy CLI agent with hybrid memory, multi-provider LLM, skills framework, and Nordic Frost aesthetics.

---

## What is Yggdrasil?

Yggdrasil is not a monorepo — it is a **living ecosystem** where every project has a purpose, a lifecycle, and a destination realm. Inspired by Norse cosmology, each realm serves a distinct function in the development lifecycle.

### Key Principles

1. **One realm per project.** Every project lives in exactly one realm at any time. No duplicates, no chaos.
2. **Enforced lifecycle.** Idea → Muspelheim → [Target Realm] → Helheim (if it dies).
3. **Lilith is the agent.** A local-first AI assistant with memory, skills, and code execution.
4. **All communication flows through the CLI.** No cloud dependencies for the core.

---

## The Nine Realms

Each realm has a single, well-defined purpose. Projects migrate between realms as they evolve.

| Realm | Theme | Purpose |
|-------|-------|---------|
| **Asgard** | Core Technology | Lilith packages, Gateway, LLM providers |
| **Vanaheim** | AI Agents | Bots, agent profiles, communication protocols |
| **Alfheim** | UI Prototypes | Visual experiments, IDE integrations, dashboards |
| **Svartalfheim** | Knowledge | Documentation, ADRs, scripts, deployment guides |
| **Muspelheim** | Active Development | Sprint templates, hotfixes, experiments |
| **Niflheim** | Resources | Datasets, LLM checkpoints, training data |
| **Midgard** | Personal Apps | Completed, battle-tested applications |
| **Jotunheim** | Massive Projects | Long-term, large-scope projects |
| **Helheim** | Graveyard | Archived code, legacy versions, dead projects |

---

## Lilith — The Goddess of Asgard

The crown jewel of Asgard. A modular AI agent framework:

- **8 packages** (`lilith-*`) for core, memory, API, bridge, CLI, orchestrator, skills, tools
- **Hybrid memory** — Vector embeddings + SQLite + full-text search
- **Multi-provider LLM** — MiMo, BytePlus, OpenAI, Anthropic
- **Skills framework** — Procedural knowledge as markdown files
- **Nordic Frost CLI** — Elder Futhark runes, Rich library

```bash
# Get started
git clone https://github.com/BrierAinz/Yggdrasil.git
cd Yggdrasil
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
python ygg.py
```

---

## Current State (v5.1.0)

| Component | Status |
|-----------|--------|
| lilith-core | ✅ Active (config, types, logger, providers) |
| lilith-memory | ✅ Active (SQLite store) |
| 6 other lilith-* packages | 🔲 Skeleton (pyproject + __init__) |
| Horror-GameMaster | ✅ Fases 1-4 DONE (2,200+ JSONL) |
| CLI (ygg.py) | ✅ Nordic Frost theme |
| Docs | ✅ This site |
