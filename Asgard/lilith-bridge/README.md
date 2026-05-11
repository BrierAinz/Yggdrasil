# Lilith Bridge

Bidirectional gateway connecting **Yggdrasil** to **Hermes Agent** via MCP protocol and HTTP API.

## Architecture

```
  HERMES AGENT                    YGGDRASIL
  ┌──────────┐   HTTP/MCP     ┌──────────────────┐
  │  Hermes   │◄═════════════► │  lilith-bridge    │
  │  Agent    │   Bridge API   │  ┌─────────────┐  │
  │  (yo)    │                │  │ HermesBridge │  │
  └──────────┘                │  └──────┬───────┘  │
                              │         │          │
                              │  ┌──────▼───────┐  │
                              │  │ LilithEngine │  │
                              │  │ MemoryStore  │  │
                              │  │ SkillContext  │  │
                              │  └──────────────┘  │
                              └──────────────────────┘
```

## Features

- **Hermes → Yggdrasil**: Send messages to Lilith, query memory, list/search skills
- **Yggdrasil → Hermes**: Delegate complex tasks to Hermes as a powerful LLM backend
- **MCP Bridge**: Expose Hermes tool server to Yggdrasil via Model Context Protocol
- **OpenAI-Compatible Proxy**: Lilith can use Hermes as an OpenAI-compatible endpoint
- **WebSocket Streaming**: Real-time streaming responses from Hermes
- **Auth**: JWT-based with shared secret support

## Quick Start

```bash
# Install
uv pip install -e ./Asgard/lilith-bridge

# Run bridge server
lilith-bridge

# Or with uvicorn
uvicorn lilith_bridge.app:app --port 9001 --reload
```

## Configuration

Set in `~/.yggdrasil/config.yaml`:

```yaml
bridge:
  hermes_url: "http://localhost:9001"     # Hermes Agent API Server
  hermes_api_key: "${HERMES_API_KEY}"     # Optional auth key
  bridge_host: "0.0.0.0"
  bridge_port: 9001
  bridge_auth_token: "${YGGDRASIL_BRIDGE_TOKEN}"
  max_retries: 3
  timeout: 120
```

## API Endpoints

### Inbound (Hermes → Yggdrasil)

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/bridge/health` | GET | Bridge health check |
| `/api/bridge/chat` | POST | Chat with Lilith |
| `/api/bridge/memory` | GET | Query Lilith's memory |
| `/api/bridge/memory` | POST | Store in Lilith's memory |
| `/api/bridge/skills` | GET | List available skills |
| `/api/bridge/skills/search` | POST | Search skills |

### Outbound (Yggdrasil → Hermes)

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/bridge/hermes/chat` | POST | Delegate to Hermes |
| `/api/bridge/hermes/tools` | GET | List Hermes tools |
| `/api/bridge/hermes/execute` | POST | Execute Hermes tool |