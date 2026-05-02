---
adr_id: ADR-004
title: Hybrid Memory (Vector + Graph + FTS5)
status: Accepted
date: 2026-04-29
decision_makers:
  - Völundr
  - Hermes
---

# 🧠 ADR-004: Hybrid Memory (Vector + Graph + FTS5)

## Context

Lilith necesita memoria persistente con múltiples modos de recuperación: búsqueda semántica (vectorial), búsqueda por keyword (full-text), y relaciones entre conceptos (grafo). Cada enfoque por separado tiene limitaciones — los vectores no capturan relaciones explícitas, el FTS5 no captura significado, y los grafos no escalar con búsqueda libre.

## Decision

Implementar **memoria híbrida** con tres capas en SQLite:

1. **Vector Store**: Embeddings con cosine similarity para búsqueda semántica
   - `EmbeddingModel` con sentence-transformers local
   - Búsqueda por similitud coseno en vectores
2. **Knowledge Graph**: Relaciones explícitas entre entidades
   - `MemoryGraph` con nodos, edges y pesos
   - Decay de relaciones débiles (>30 días sin refuerzo)
3. **FTS5**: Full-text search para búsqueda por keywords
   - Tablas `FTS5` nativas de SQLite
   - Stopwords bilingües (ES/EN)

Ciclo de vida de la memoria:
- **Episodic**: Conversaciones recientes con embeddings
- **Consolidation**: `BackgroundConsolidator` mergea episodios similares (>0.85 cosine)
- **Promotion**: Hechos frecuentes se promueven a memoria permanente
- **Decay**: Relaciones débiles se atenuan con el tiempo

## Consequences

### Positivas
- **Multi-modal**: Búsqueda semántica, por keyword, y por relaciones
- **Evolución**: La memoria se auto-organiza (merge, promotion, decay)
- **Sin servidor**: Todo en SQLite — zero external dependencies
- **Crash-safe**: SQLite WAL mode garantiza durabilidad

### Negativas
- **Complejidad**: Tres sistemas de almacenamiento en una DB
- **Embeddings**: El modelo local es limitado vs OpenAI ada-002
- **Latencia de consolidación**: El daemon thread puede tardar en merge
- **Tamaño de DB**: Los embeddings vectoriales crecen rápido
