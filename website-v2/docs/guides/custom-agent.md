---
sidebar_position: 2
title: Creating a Custom Agent
---

# Creating a Custom Agent

Build an agent with custom tools, memory, and personality.

## Step 1: Define Configuration

```python
from lilith_core import YggdrasilConfig

config = YggdrasilConfig(
    root_path="./my-agent",
    model="gpt-4",
    temperature=0.8,
)
```

## Step 2: Set Up Memory

```python
from lilith_memory.store import MemoryStore

memory = Store(config.root / "agent_memory.db")
```

## Step 3: Register Custom Tools

```python
from lilith_tools.registry import ToolRegistry

@ToolRegistry.tool(description="Fetch weather data")
def get_weather(city: str) -> dict:
    # Your implementation
    return {"city": city, "temp": 22, "condition": "sunny"}

@ToolRegistry.tool(description="Send an email")
def send_email(to: str, subject: str, body: str) -> bool:
    # Your implementation
    return True
```

## Step 4: Create the Engine

```python
from lilith_orchestrator.engine import LilithEngine

engine = LilithEngine(config, memory)
```

## Step 5: Run

```python
result = engine.process("What's the weather in Tokyo?")
print(result["response"])
# "The weather in Tokyo is currently sunny with a temperature of 22°C."
```

## Adding Memory Persistence

Every interaction is automatically stored in memory. Search past conversations:

```python
memories = memory.search("weather")
for m in memories:
    print(f"[{m['role']}] {m['content']}")
```
