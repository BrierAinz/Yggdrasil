# Yggdrasil Architecture

## Module Dependency Order
lilith-core → lilith-memory → lilith-tools → lilith-orchestrator → lilith-api → lilith-cli

## Services
| Service | Port | Package |
|---------|------|---------|
| API Gateway | 8000 | lilith-api |
| Model Orchestrator | 8001 | lilith-orchestrator |
| Memory Service | 8002 | lilith-memory |

## Tech Stack
- Python 3.11+
- FastAPI + WebSocket
- SQLite (memory)
- Rich + Cyclopts (CLI)
