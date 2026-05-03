# Plan: FASE 2 - Semantic Memory v2.0

## Goal
Mejorar el sistema de memoria existente con grafo de conocimiento, consolidación inteligente y retrieval híbrido.

## Scope
- IN: Grafo de entidades+relaciones, consolidación de episodios, retrieval híbrido
- OUT: Cambios al dashboard, bots, MCP

## Architecture
```
EnhancedMemory v2.0
├── episodios (existente)
├── summaries (existente)
├── entities (existente) + graph
├── facts (existente)
├── errors (existente)
├── NEW: relations (entity1, relation, entity2, strength)
├── NEW: memory_index (hybrid search index)
└── NEW: consolidation_queue (episodes pending merge)
```

## Tasks
1. Crear `memory_graph.py` - grafo de entidades y relaciones
2. Crear `memory_consolidation.py` - merge de episodios similares
3. Crear `memory_retrieval.py` - hybrid: vector + keyword + graph
4. Integrar en `enhanced.py`
5. Actualizar `orchestrator.py` para usar retrieval híbrido
6. Actualizar comandos `/memory`, `/recall` en `main.py`
7. Tests (30+)
8. Commit

## Files
- NEW: Lilith/memory/memory_graph.py
- NEW: Lilith/memory/memory_consolidation.py
- NEW: Lilith/memory/memory_retrieval.py
- NEW: Lilith/memory/tests/test_*.py
- MOD: Lilith/memory/enhanced.py
- MOD: Lilith/Core/orchestrator.py
- MOD: Lilith/main.py

## Risks
- Migración de DB existente: añadir tablas nuevas, no romper datos
- sentence-transformers puede no estar disponible: fallback a keyword

## Success Criteria
- [ ] 30+ tests pasan
- [ ] Grafo construye relaciones entre entidades
- [ ] Consolidación reduce ruido en memoria
- [ ] Retrieval híbrido mejora precisión vs solo vector
- [ ] Comandos /memory y /recall funcionan
