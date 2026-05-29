---
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
