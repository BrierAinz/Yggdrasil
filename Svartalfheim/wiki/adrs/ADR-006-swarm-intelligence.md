---
adr_id: ADR-006
title: Swarm Intelligence con AgentSpawner
status: Accepted
date: 2026-04-29
decision_makers:
  - Völundr
  - Hermes
---

# 🐝 ADR-006: Swarm Intelligence con AgentSpawner

## Context

Para tareas complejas (refactoring, multi-file editing, investigación), un solo agente no es suficiente. Se necesita la capacidad de spawnar múltiples agentes workers que cooperen, compartan contexto y eviten conflictos de archivo.

## Decision

Implementar **Swarm Intelligence** con los siguientes componentes:

1. **SwarmAgent**: Worker con estados (`IDLE`, `WORKING`, `REVIEWING`, `COMPLETE`, `ERROR`, `STOPPED`)
2. **MessageBus**: Sistema de mensajería pub/sub entre agentes
3. **SwarmDatabase**: Persistencia SQLite con tablas:
   - `swarm_sessions`: Metadatos de sesión
   - `swarm_agents`: Estado de cada worker
   - `swarm_messages`: Historial de mensajes
   - `swarm_conflicts`: Conflictos de edición detectados
4. **AgentSpawner**: Orquestador que divide tareas y distribuye a workers
5. **File Locks**: Locking por archivo para evitar conflictos de escritura

Cada agente tiene:
- `agent_id`: Identificador único
- `task`: Descripción de la subtarea
- `capabilities`: Lista de capacidades
- `context`: Diccionario con contexto compartido
- `use_llm`: Flag para usar LLM en razonamiento

## Consequences

### Positivas
- **Paralelismo**: Múltiples workers procesan subtareas concurrente
- **Coordinación**: MessageBus y file locks previenen conflictos
- **Persistencia**: SwarmDatabase mantiene estado entre reinicios
- **Observabilidad**: Cada agente reporta estado y progreso

### Negativas
- **Complejidad**: Coordinación de agentes introduce overhead
- **LLM cost**: Si `use_llm=True`, cada agente consume tokens
- **Conflictos**: A pesar de file locks, pueden ocurrir conflictos lógicos
- **Thread safety**: Requiere thread-local connections en SQLite
