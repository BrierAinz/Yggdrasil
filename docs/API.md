# Yggdrasil API Reference

Lilith exposes two HTTP APIs for integration with external tools and UIs.

---

## 1. Lilith Core API (`Asgard/Lilith/src/api/server.py`)

FastAPI server that bridges the Lilith Core with external consumers via HTTP and WebSocket.

### Base URL
```
http://localhost:8000
```

### Endpoints

#### System
| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/api/status` | Health check + running state |
| `GET` | `/api/version` | Current version string |
| `GET` | `/api/meta-report` | Metadata report of the session |
| `GET` | `/api/audit/summary` | Audit summary |

#### Tools
| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/api/tools` | List all available tools |
| `GET` | `/api/tools/{tool_name}` | Get schema for a specific tool |

#### Chat & Execution
| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/api/chat` | Send a message, get LLM response |
| `POST` | `/api/execute` | Execute a tool directly |
| `POST` | `/api/confirm` | Confirm a pending action |

#### Context & History
| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/api/history` | Conversation history |
| `GET` | `/api/stats` | Usage statistics |
| `GET` | `/api/suggestions/presets` | Suggestion presets |

#### Git Integration
| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/api/git/status` | Git status of current project |
| `GET` | `/api/git/context` | Git context for LLM prompts |
| `GET` | `/api/git/suggestions` | AI-powered git suggestions |

#### Project
| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/api/project/context` | Current project context |
| `GET` | `/api/project/recent` | Recently accessed projects |

#### Sessions
| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/api/sessions` | Create new session |
| `GET` | `/api/sessions` | List sessions |
| `GET` | `/api/sessions/current` | Get current session |
| `POST` | `/api/sessions/{id}/load` | Load a session |
| `POST` | `/api/sessions/{id}/save` | Save session state |
| `DELETE` | `/api/sessions/{id}` | Delete session |
| `POST` | `/api/sessions/{id}/rename` | Rename session |

#### Patterns
| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/api/patterns/record` | Record a new pattern |
| `GET` | `/api/patterns/predict` | Predict next pattern |

#### Real-time
| Method | Path | Description |
|--------|------|-------------|
| `WebSocket` | `/ws` | Standard WebSocket stream |
| `WebSocket` | `/ws/conversational` | Conversational WebSocket stream |

---

## 2. Lilith Standalone API (`Asgard/lilith-api/`)

Lightweight FastAPI wrapper for headless Lilith usage.

### Base URL
```
http://localhost:8000
```

### Endpoints

#### Chat
```http
POST /chat
Content-Type: application/json

{
  "message": "Hello Lilith",
  "model": "optional-model-name"
}
```

**Response:**
```json
{
  "response": "Recibido: Hello Lilith",
  "context_used": ["..."],
  "tool_call": {}
}
```

#### Tool Execution
```http
POST /tools/execute
Content-Type: application/json

{
  "tool": "file_read",
  "params": {"path": "README.md"}
}
```

#### Tool Registry
```http
GET /tools
```

#### Health
```http
GET /health
```

**Response:**
```json
{
  "status": "ok",
  "version": "2.1.0",
  "tools": 42,
  "model": "auto"
}
```

#### Status
```http
GET /status
```

**Response:**
```json
{
  "version": "2.1.0",
  "model": "auto",
  "tools_available": 42,
  "memory_entries": 128
}
```

#### Memory
```http
GET /memory?query=python&k=5
```

```http
POST /memory
Content-Type: application/json

{
  "text": "Important fact about Python",
  "metadata": {"source": "conversation"}
}
```

---

## Authentication

Both APIs currently run on `localhost` without authentication in development mode.
For production, set `LILITH_INTERNAL_TOKEN` and send it as a Bearer token:

```http
Authorization: Bearer ${LILITH_INTERNAL_TOKEN}
```

---

## WebSocket Protocol

Connect to `/ws` or `/ws/conversational` and send JSON messages:

```json
{"type": "chat", "payload": "Hello"}
```

The server streams responses as JSON frames:

```json
{"type": "token", "data": "Hello"}
{"type": "done"}
```
