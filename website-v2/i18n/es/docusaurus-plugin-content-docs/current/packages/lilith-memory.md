---
sidebar_position: 3
title: lilith-memory
---

# lilith-memory

Almacenamiento persistente con backends pluggables (SQLite, ChromaDB, Mem0).

## Inicio Rápido

```python
from lilith_memory.store import MemoryStore

# Crear store (SQLite)
store = MemoryStore("mi_memoria.db")

# Almacenar memorias
store.add("El usuario preguntó sobre Python", role="user")
store.store("default", "assistant", "Aquí está cómo usar Python...")

# Buscar memorias
resultados = store.search("Python")
for r in resultados:
    print(r["content"], r["role"])

# Recientes
recientes = store.recent(limit=5)

# Contar y limpiar
print(store.count())  # 2
store.clear()         # retorna cantidad eliminada
```

## API de MemoryStore

| Método | Firma | Descripción |
|--------|-------|-------------|
| `store()` | `(session_id, role, content, metadata=None) -> int` | Almacenar entrada |
| `add()` | `(content, role="user", ...) -> int` | Wrapper de conveniencia |
| `recall()` | `(session_id, limit=10) -> list[dict]` | Recordar por sesión |
| `search()` | `(query, limit=5) -> list[dict]` | Búsqueda de texto |
| `count()` | `() -> int` | Conteo total |
| `delete()` | `(entry_id) -> bool` | Eliminar por ID |
| `clear()` | `() -> int` | Limpiar todo |
