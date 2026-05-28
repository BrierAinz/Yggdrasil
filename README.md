# ᛒ YGGDRASIL

> **BrierStudios** — The World Tree

```
          ╦ ╦ ╔═╗ ╔═╗ ╔╗╗ ╔═╗ ╦   ╔═╗
          ╚╦╝ ║╣  ║ ╦ ║║║ ║╣  ║   ╚═╗
           ╩  ╚═╝ ╚═╝ ╝╚╝ ╚═╝ ╩═╝ ╚═╝
```

Ecosistema de software organizado bajo la mitologia nordica.

## Nine Realms

| Realm | Proposito | Estado |
|-------|-----------|--------|
| **Asgard** | Core — lilith-core, memory, tools, orchestrator, api, cli, skills, bridge | Activo |
| **Vanaheim** | Agentes IA — vanaheim-framework, bifrost | Activo |
| **Alfheim** | UI — dashboards, frontends | Prototipos |
| **Svartalfheim** | Documentacion, planes, conocimiento | Activo |
| **Muspelheim** | Desarrollo activo — ForgeMaster, AutoSub, AI-Influencer | WIP |
| **Niflheim** | Assets, modelos, datasets | Gitignored |
| **Helheim** | Cementerio — proyectos archivados | Read-only |
| **Jotunheim** | Proyectos masivos (>1 mes) | Esperando |
| **Midgard** | Apps personales | Activo |

## Quick Start

```bash
# Install
cd Yggdrasil
python -m venv .venv
source .venv/bin/activate
pip install -e Asgard/lilith-core -e Asgard/lilith-memory

# Run CLI
python ygg.py status
python ygg.py chat

# Or use alias
ygg status
```

## Tech Stack

- **Python** 3.11+
- **FastAPI** + WebSocket (port 8000)
- **SQLite** memory store
- **Rich** + **Cyclopts** CLI
- **PipeWire** audio routing

## LLM Providers

| Provider | Model | Base URL |
|----------|-------|----------|
| MiMo | MiMo-V2.5-Pro | token-plan-sgp.xiaomimimo.com |
| BytePlus | dola-seed-2.0-pro | ark.ap-southeast.bytepluses.com |
| Alibaba | qwen3.7-max | maas.aliyuncs.com |
| LM Studio | local-model | localhost:1234 |

## Module Dependency

```
lilith-core → lilith-memory → lilith-tools → lilith-orchestrator → lilith-api → lilith-cli
```

## Reglas

Consulta [REGLAS_YGGDRASIL.md](REGLAS_YGGDRASIL.md) para las reglas del ecosistema.

---

**BrierStudios** — ᛒᚱᛁᛖᚱᛊᛏᚢᛞᛁᛟᛊ
