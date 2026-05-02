---
name: Asgard
realm: Asgard
status: Activo
stack:
  - Python 3.11+
  - SQLite (sessions, swarm, memory)
  - httpx (LLM providers)
  - Pydantic
  - TOML (config)
  - pytest (testing)
  - Electron + React (Dashboard)
dependencies:
  - Niflheim/Models (LLM local inference)
  - Svartalfheim/docs (documentation)
  - Vanaheim (external bot tools)
---

# ⚡ Asgard — Reino del Core Tecnológico

> *Donde los Aesir forjan las armas del destino.*

## 📜 Propósito

Asgard es el corazón del ecosistema Yggdrasil — el reino donde reside **Hermes-Lilith**, el agente CLI principal con memoria persistente, skills dinámicos, swarm intelligence y conectividad multi-provider. Todo lo que es motor, orquestador o infraestructura core vive aquí.

## 🏗️ Arquitectura

```
Asgard/
└── Hermes-Lilith/
    ├── Lilith/
    │   ├── Core/           # Orquestador, config, resilience, LLM provider
    │   ├── Dashboard/      # Web UI con FastAPI + JS frontend
    │   ├── Swarm/          # Agent spawner, executor, database
    │   ├── MCP/            # Model Context Protocol client
    │   ├── memory/         # Session store, graph, RAG, consolidator
    │   ├── skills/         # YAML+MD skill definitions
    │   └── tools/          # Native tools (files, system, network, browser, coding)
    ├── data/               # swarm.db
    └── memory/             # lilith_memory.db
```

## 🔧 Componentes Clave

| Componente | Archivo | Función |
|-----------|---------|---------|
|| Orchestrator | `Core/orchestrator.py` | Loop principal de conversación, tool dispatch |
|| LLM Provider | `Core/llm_provider.py` | Multi-provider con fallback automático |
|| Resilience | `Core/resilience.py` | Circuit breaker + retry con backoff |
|| Config (TOML) | `Core/toml_config.py` | Config unificada, PEP 680 |
|| Batch Mode | `batch/runner.py` | Ejecución no-interactiva (CLI flags --batch) |
|| Session Store | `memory/session_store.py` | Persistencia con embeddings y crash recovery |
|| Swarm Agent | `Swarm/agent.py` | Worker con estados, file tracking |
|| Swarm Manager | `Swarm/manager.py` | Orquestador: spawn, kill, status, result |
|| MessageBus | `Swarm/message_bus.py` | Pub/sub inter-agent |
|| ConflictResolver | `Swarm/conflict_resolver.py` | Detección y merge de edits overlapping |
|| Swarm Database | `Swarm/database.py` | SQLite para persistencia del swarm |
|| Executor | `Swarm/executor.py` | Routing a LLM providers |
|| Swarm CLI | `tools/swarm.py` | /swarm spawn|status|kill|result|save|load|history |
|| MCP Protocol | `MCP/protocol.py` | JSON-RPC 2.0 para tool discovery |
|| Skill Parser | `Core/skill_parser.py` | YAML frontmatter + Markdown body |
|| Background Consolidator | `memory/background_consolidator.py` | Merge, promotion, decay en daemon thread |

## 🔗 Dependencias

- **Niflheim**: Modelos LLM para inferencia local (LM Studio)
- **Svartalfheim**: Documentación y runbooks
- **Vanaheim**: Herramientas externas de bots

## 📊 Estado

- **Versión**: v4.0.0 (RELEASED, tag v4.0.0)
- **Tests**: 838 tests, 2 skipped
- **Providers**: LM Studio (local), Kimi Code (remoto fallback)
- **Memoria**: Vector + Graph + FTS5 (hibrido)
- **Dashboard**: FastAPI + frontend JS
- **Batch Mode**: Ejecución no-interactiva via CLI
- **Swarm Intelligence**: Multi-agent con MessageBus y ConflictResolver
