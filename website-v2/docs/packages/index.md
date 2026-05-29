---
sidebar_position: 1
title: Packages Reference
---

# Packages Reference

Yggdrasil is built on 8 modular packages, each living in its own realm under `Asgard/`.

## Package Overview

| Package | Version | Description |
|---------|---------|-------------|
| [lilith-core](./lilith-core) | 2.1.0 | Configuration, types, logging, LLM providers |
| [lilith-memory](./lilith-memory) | 1.0.0 | Persistent storage with pluggable backends |
| [lilith-tools](./lilith-tools) | 1.0.0 | Tool registry and execution |
| [lilith-api](./lilith-api) | 1.0.0 | REST API with FastAPI |
| [lilith-cli](./lilith-cli) | 1.0.0 | Interactive CLI |
| [lilith-bridge](./lilith-bridge) | 1.0.0 | Component bridge |
| [lilith-orchestrator](./lilith-orchestrator) | 1.0.0 | Agent orchestration engine |
| [lilith-skills](./lilith-skills) | 1.0.0 | Skill loading system |

## Installation

All packages are part of the Yggdrasil workspace:

```bash
git clone https://github.com/BrierAinz/Yggdrasil.git
cd Yggdrasil
uv sync --all-packages --dev
```

Individual packages can be installed separately:

```bash
uv pip install -e Asgard/lilith-core
uv pip install -e Asgard/lilith-memory
```
