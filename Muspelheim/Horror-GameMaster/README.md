# Horror GameMaster

> BrierStudios — Procedural Terror Engine

A text-based horror game engine that adapts to player fears, generates procedural horror narratives, and creates personalized terror experiences using LLM integration.

## Features

- **Fear Adaptation** — Tracks 7 fear dimensions and adapts gameplay
- **Procedural Generation** — 22 scene templates, 12 event types, entity spawning
- **Tension Management** — Dynamic tension curve with cooldown and escalation
- **NPC Intelligence** — Trust system, learning NPCs, doppelganger mechanic
- **Context Memory** — Foreshadowing, callbacks, narrative threads
- **Multi-Provider LLM** — Ollama, OpenAI-compatible, BytePlus Ark
- **1,000+ Training Entries** — JSONL dataset for fine-tuning

## Quick Start

### Terminal UI (Rich)
```bash
pip install pydantic numpy rich requests
python -m src.terminal_ui
```

### Web UI (FastAPI + HTMX)
```bash
pip install pydantic numpy rich requests fastapi uvicorn
python -m src.web_ui --port 8080
```

### Simple UI (no dependencies)
```bash
python -m src.terminal_ui --simple
```

### Docker
```bash
docker build -t horror-gamemaster .
docker run -p 8080:8080 horror-gamemaster
```

## Architecture

```
src/
├── gamemaster.py          # Main orchestrator
├── llm_engine.py          # Multi-provider LLM integration
├── context_manager.py     # Foreshadowing, callbacks, threads
├── npc_intelligence.py    # NPCs, trust, doppelganger
├── pattern_analyzer.py    # Behavior analysis, fear fingerprinting
├── procedural_generator.py # Scenes, events, entities
├── tension_manager.py     # Tension curve, pacing, escalation
├── terminal_ui.py         # Rich terminal interface
├── web_ui.py              # FastAPI + HTMX web interface
└── memory/
    ├── player_memory.py   # Fear profiles, SQLite persistence
    └── embeddings.py      # Semantic embeddings pipeline
```

## Fear Types

| Type | Description |
|------|-------------|
| psychological | Reality breakdown, memory manipulation |
| darkness | What lurks unseen, light failure |
| isolation | Absolute aloneness, communication failure |
| body_horror | Wrongness of flesh, transformation |
| paranoia | Trust erosion, surveillance |
| loss_of_control | Agency removal, predetermination |
| jumpscare | Earned sudden scares |
| false_security | False safety that betrays |

## Fine-Tuning

The dataset is at `data/dataset_final.jsonl` (1,000+ entries).

Recommended: Qwen2.5-7B-Instruct + Unsloth

```bash
python scripts/generate_dataset.py --total 2000  # Expand dataset
```

## Testing

```bash
PYTHONPATH=src python -m pytest tests/ -v
```

## License

BrierStudios — Private Project

## Runes

ᛒᚱᛁᛖᚱᛊᛏᚢᛞᛁᛟᛊ
