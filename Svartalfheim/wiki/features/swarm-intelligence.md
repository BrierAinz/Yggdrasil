---
title: Swarm Intelligence — Referencia Completa
last_updated: 2026-05-02
version: v4.0.0+
status: Implemented
category: feature
adr: ADR-006
---

# 🐝 Swarm Intelligence — Referencia Completa

> *Un enjambre de pequeñinos artesanos, cada uno con su fragua, coordinados por el maestro herrero.*

## Resumen

Sistema de multi-agentes que permite dividir tareas complejas entre múltiples workers (SwarmAgents) que cooperan via MessageBus, con persistencia SQLite y resolución de conflictos.

## Arquitectura

```
                    ┌─────────────────┐
                    │   SwarmManager   │
                    │  (Orquestador)   │
                    └────────┬────────┘
                             │
              ┌──────────────┼──────────────┐
              │              │              │
        ┌─────┴─────┐ ┌─────┴─────┐ ┌─────┴─────┐
        │  Agent 1  │ │  Agent 2  │ │  Agent N  │
        │ (Worker)  │ │ (Worker)  │ │ (Worker)  │
        └─────┬─────┘ └─────┬─────┘ └─────┬─────┘
              │              │              │
              └──────────────┼──────────────┘
                             │
                    ┌────────┴────────┐
                    │   MessageBus    │
                    │  (Pub/Sub)      │
                    └────────┬────────┘
                             │
                    ┌────────┴────────┐
                    │ SwarmDatabase   │
                    │ (SQLite persist) │
                    └─────────────────┘
```

## Módulos

### SwarmAgent (`Swarm/agent.py`)

Worker individual con ciclo de vida completo:

| Estado | Descripción |
|--------|-------------|
| `IDLE` | Disponible, esperando tarea |
| `WORKING` | Ejecutando tarea asignada |
| `REVIEWING` | Revisando resultado de otro agent |
| `COMPLETE` | Tarea finalizada exitosamente |
| `ERROR` | Error durante ejecución |
| `STOPPED` | Detenido por usuario o manager |

Propiedades del agente:
- `agent_id`: UUID único
- `task`: Descripción de la subtarea
- `capabilities`: Lista de capacidades declaradas
- `context`: Dict con contexto compartido
- `use_llm`: Si usa LLM para razonamiento
- `files_tracked`: Archivos que el agente está modificando

### SwarmManager (`Swarm/manager.py`)

Orquestador que gestiona el ciclo de vida del enjambre:

- **`spawn(task, capabilities, use_llm)`**: Crea un nuevo agente
- **`status(session_id)`**: Estado de la sesión
- **`kill(agent_id)`**: Termina un agente específico
- **`killall(session_id)`**: Termina todos los agentes de una sesión
- **`result(agent_id)`**: Obtiene el resultado de un agente
- **`save(session_id)`**: Persiste sesión a disco
- **`load(session_id)`**: Restaura sesión desde disco
- **`history(session_id)`**: Historial de mensajes

### MessageBus (`Swarm/message_bus.py`)

Sistema pub/sub para comunicación inter-agent:

-**`publish(channel, message)`**: Publica mensaje en canal
- `subscribe(channel, handler)`: Suscribe handler a canal
- `unsubscribe(channel, handler)`: Desuscribe handler
- Canales predefinidos: `broadcast`, `coordination`, `results`

### ConflictResolver (`Swarm/conflict_resolver.py`)

Resolución de conflictos cuando múltiples agentes editan el mismo archivo:

- Detección de overlapping file edits
- Merge automático cuando es seguro
- Flagging para revisión manual cuando no se puede merge
- Registro de conflictos en `swarm_conflicts` table

### SwarmDatabase (`Swarm/database.py`)

Persistencia SQLite con 4 tablas:

| Tabla | Propósito |
|-------|-----------|
| `swarm_sessions` | Metadatos de sesión (id, status, timestamps) |
| `swarm_agents` | Estado de cada worker |
| `swarm_messages` | Historial completo de mensajes |
| `swarm_conflicts` | Conflictos de edición detectados |

Thread-safe con connections thread-local.

### Executor (`Swarm/executor.py`)

Interfaz con LLM providers para ejecución de tareas:

- Routing a provider correcto (LM Studio local / Kimi remoto)
- Retry con backoff en caso de fallo
- Streaming de resultados parciales
- Token counting y tracking

### Prompts (`Swarm/prompts.py`)

Templates de sistema prompt para los agentes:

- Prompt de coordinación del manager
- Prompt de ejecución del worker
- Prompt de revisión
- Prompt de resolución de conflictos

### CLI Tool (`tools/swarm.py`)

Interfaz CLI para gestionar swarms desde la terminal de Lilith:

```
/swarm spawn <task> [--cap cap1,cap2] [--llm]
/swarm status [session_id]
/swarm kill <agent_id>
/swarm killall [session_id]
/swarm result <agent_id>
/swarm save [session_id]
/swarm load <session_id>
/swarm history [session_id]
```

## Tests

Suite completa en `Swarm/tests/`:

| Archivo | Cobertura |
|---------|-----------|
| `test_swarm.py` | Manager, Agent, Database, MessageBus — 20+ tests |
| `test_fase4_5.py` | Conflict resolver, executor, prompts, integration — 20+ tests |

Total: **40 tests** — todos pasando.

## Flujo de Uso Típico

```
1. Usuario ejecuta: /swarm spawn "Refactorizar auth module"
2. SwarmManager crea sesión y agentes
3. Cada agente recibe subtarea via MessageBus
4. Agentes ejecutan con Executor (LLM o batch)
5. ConflictResolver chequea overlapping edits
6. Resultados se persisten en SwarmDatabase
7. Usuario consulta: /swarm status
8. Usuario obtiene resultado: /swarm result <id>
9. Sesión se guarda: /swarm save
```

## Ver También

- [ADR-006: Swarm Intelligence](adrs/ADR-006-swarm-intelligence.md) — Decisión arquitectónica
- [Batch Mode](features/batch-mode.md) — Ejecución no-interactiva de agentes
- [Kimi Code API](features/kimi-code-api.md) — Provider remoto para swarm workers
