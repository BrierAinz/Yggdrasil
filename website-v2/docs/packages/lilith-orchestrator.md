---
sidebar_position: 6
title: lilith-orchestrator
---

# lilith-orchestrator

Agent orchestration engine. Connects configuration, memory, and LLM providers into a unified processing pipeline.

## Quick Start

```python
from lilith_orchestrator.engine import LilithEngine
from lilith_core import YggdrasilConfig
from lilith_memory.store import MemoryStore

config = YggdrasilConfig()
memory = Store("memory.db")
engine = LilithEngine(config, memory)

# Process a message
result = engine.process("What's the weather like?")
# {
#   "response": "I don't have access to weather data...",
#   "usage": {"tokens": 45},
#   "tool_call": null
# }
```

## Pipeline

```
User Input
    ↓
┌───────────────┐
│ LilithEngine  │
│  ┌─────────┐  │
│  │ Context  │  │ ← Memory recall
│  │ Builder  │  │
│  └────┬────┘  │
│       ↓       │
│  ┌─────────┐  │
│  │   LLM   │  │ ← Provider (OpenAI, LM Studio, etc.)
│  │ Provider │  │
│  └────┬────┘  │
│       ↓       │
│  ┌─────────┐  │
│  │  Tool   │  │ ← Tool execution if needed
│  │ Handler │  │
│  └────┬────┘  │
│       ↓       │
│  ┌─────────┐  │
│  │ Memory  │  │ ← Store interaction
│  │ Writer  │  │
│  └─────────┘  │
└───────────────┘
    ↓
Response
```

## Tool Handling

When the LLM returns a tool call, the engine automatically executes it:

```python
result = engine.process("Search for Python tutorials")
# If LLM requests tool_call: {"tool": "search", "params": {"query": "Python tutorials"}}
# Engine executes the tool and feeds results back to LLM
```
