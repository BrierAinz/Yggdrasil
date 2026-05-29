---
sidebar_position: 5
title: lilith-api
---

# lilith-api

REST API for Yggdrasil, built with FastAPI. Provides endpoints for chat, memory, tools, and system status.

## Endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET | `/health` | Lightweight health check |
| GET | `/status` | Detailed system status |
| POST | `/chat` | Send a message to the agent |
| GET | `/tools` | List available tools |
| POST | `/tools/execute` | Execute a tool |
| GET | `/memory` | Search memory |
| POST | `/memory` | Store a memory entry |

## Quick Start

```python
from lilith_api.main import app
from fastapi.testclient import TestClient

client = TestClient(app)

# Health check
r = client.get("/health")
# {"status": "ok", "version": "2.2.0"}

# Chat
r = client.post("/chat", json={"message": "Hello!"})
# {"response": "...", "context": [...], "tool_call": null}

# Search memory
r = client.get("/memory", params={"query": "python"})
# [{"content": "...", "role": "user", ...}]
```

## Running the Server

```bash
# Development
uvicorn lilith_api.main:app --reload --port 8000

# Production
uvicorn lilith_api.main:app --host 0.0.0.0 --port 8000
```

## Dependency Injection

The API uses FastAPI's DI system. Override dependencies for testing:

```python
from lilith_api.main import app, get_config, get_memory, get_engine

app.dependency_overrides[get_config] = lambda: mock_config
app.dependency_overrides[get_memory] = lambda: mock_memory
```
