---
adr_id: ADR-002
title: SQLite como Storage Principal
status: Accepted
date: 2026-04-29
decision_makers:
  - Völundr
  - Hermes
---

# 💎 ADR-002: SQLite como Storage Principal

## Context

Lilith necesita persistir múltiples tipos de datos: sesiones de conversación, memoria vectorial, grafo de conocimiento, estado del swarm, configuración y cache. Las opciones eran: PostgreSQL (requiere servidor), archivos JSON/CSV (frágiles), o SQLite (embebido).

## Decision

Usar **SQLite** como motor de almacenamiento principal para todo el ecosistema:

1. **Sessions**: `session_store` usa SQLite con embeddings y FTS5
2. **Swarm**: `SwarmDatabase` persiste agentes, mensajes y conflictos
3. **Memory**: `lilith_memory.db` con tablas vectoriales + graph + FTS5
4. **Config**: Complementario con TOML files (ver ADR-003)

SQLite se usa con:
- `check_same_thread=False` para thread safety
- **Thread-local connections** en SwarmDatabase
- **WAL mode** para permitir lecturas concurrentes
- **Row factory** para acceso por nombre de columna

## Consequences

### Positivas
- **Zero ops**: No requiere servidor, backup es copiar un archivo
- **Performance**: SQLite es extremadamente rápido para workloads de Lilith
- **Portabilidad**: Un solo archivo `.db` contiene toda la data
- **FTS5**: Full-text search nativo para búsqueda semántica
- **Transaccional**: ACID guarantees sin configuración

### Negativas
- **Concurrencia de escritura**: Solo un writer a la vez (mitigado con WAL)
- **Sin replicación**: No hay distributed storage
- **Sin queries distribuidos**: No se puede escalar horizontalmente
- **Migración de schema**: Manual con ALTER TABLE
