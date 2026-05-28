---
adr_id: ADR-009
title: Session Store con Crash Recovery
status: Accepted
date: 2026-04-29
decision_makers:
  - Völundr
  - Hermes
---

# 🔄 ADR-009: Session Store con Crash Recovery

## Context

Las sesiones de conversación con Lilith son valiosas — contienen contexto, decisiones y aprendizaje. Si Lilith se crashea o se cierra inesperadamente, toda la memoria de la sesión se pierde sin persistencia. Se necesita un sistema que guarde sesiones incrementalmente y permita recuperarlas tras un crash.

## Decision

Implementar **SessionStore** con crash recovery:

1. **Persistencia incremental**: Cada mensaje se guarda en SQLite tan pronto se genera
2. **Embeddings de sesión**: Cada sesión tiene un embedding vectorial para búsqueda semántica
3. **Resumen automático**: Keyword extraction sin LLM para generar resúmenes
4. **Crash recovery**: Al reiniciar, `SessionStore` detecta sesiones sin `completed_at` y las marca como `interrupted`
5. **Stopwords bilingües**: Filtro de stopwords ES/EN para resúmenes de calidad
6. **Cosine similarity**: Búsqueda de sesiones similares vía embeddings

Schema de `session_store`:
```sql
CREATE TABLE sessions (
    id TEXT PRIMARY KEY,
    title TEXT,
    summary TEXT,
    embedding BLOB,        -- numpy array serializado
    episode_count INTEGER,
    metadata JSON,
    created_at TIMESTAMP,
    updated_at TIMESTAMP,
    completed_at TIMESTAMP  -- NULL si crash
);
```

## Consequences

### Positivas
- **Durabilidad**: Sesiones sobreviven crashes
- **Búsqueda**: Encontrar sesiones previas por similitud semántica
- **Sin LLM para resúmenes**: Keyword extraction es determinista y gratuito
- **Context recovery**: Se puede restaurar contexto de sesiones interrumpidas

### Negativas
- **Overhead de I/O**: Cada mensaje requiere un SQLite write
- **Embedding quality**: Sentence-transformers local es menos preciso que modelos grandes
- **Storage growth**: Sesiones con embeddings crecen significativamente
- **Stopwords limitados**: Filtro de keywords puede perder términos importantes
