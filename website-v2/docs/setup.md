---
sidebar_position: 3
title: Setup
---

# Setup Guide

## Requirements

- **Python** 3.11 or higher
- **Git**
- **pip** (included with Python)

Optional:
- **uv** — Ultra-fast package manager
- **Node.js** — Only for Alfheim frontend

## Installation

```bash
# 1. Clone the repository
git clone https://github.com/BrierAinz/Yggdrasil.git
cd Yggdrasil

# 2. Create virtual environment
python -m venv .venv
source .venv/bin/activate  # Linux/macOS

# 3. Install dependencies
pip install -e ".[dev]"

# 4. Run the CLI
python ygg.py
```

## CLI Commands

```bash
python ygg.py              # Interactive menu
python ygg.py status       # Realm health status
python ygg.py tree         # Project tree
python ygg.py size         # Size per realm
python ygg.py health       # Verify READMEs
python ygg.py clean        # Clean regenerable files
python ygg.py backup       # Backup Svartalfheim + configs
python ygg.py test         # Run pytest
python ygg.py update       # Git pull + deps
```

## Lilith Agent

```bash
python lilith_agent.py     # Start the AI agent
python lilith_cli.py chat  # Chat with Lilith
```

Chat commands: `ayuda`, `resumen`, `memoria`, `borrar`, `salir`

## Configuration

```bash
cp .env.example .env
# Edit .env with your API keys
```

Key variables:
- `OPENAI_API_KEY` — OpenAI
- `ANTHROPIC_API_KEY` — Claude
- `MIMO_API_KEY` — MiMo

## Development

```bash
# Linting
ruff check .
ruff format .

# Tests
pytest

# Pre-commit
pre-commit install
```
