# Python Circular Import Resolution

## Pattern: Shared Base Module

**Problem:** Module A imports from Module B, Module B imports from Module A. Both fail at import time.

**Solution:** Extract shared constants/functions to a third module that both can import.

### Example from Hermes-Lilith Memory System

**Before (circular):**
```python
# memory_graph.py
from Lilith.memory.enhanced import DB_PATH, cosine_similarity
# ^ enhanced.py imports memory_graph → CIRCULAR

# memory_consolidation.py  
from Lilith.memory.enhanced import DB_PATH, cosine_similarity
# ^ same problem

# enhanced.py
from Lilith.memory.memory_graph import MemoryGraph
from Lilith.memory.memory_consolidation import get_consolidation
# ^ imports both, which try to import from enhanced → DEADLOCK
```

**After (clean):**
```python
# base.py — shared, no external imports
import numpy as np
from pathlib import Path
from typing import List, Optional

DB_PATH = Path(__file__).parent.parent.parent / "memory" / "lilith_memory.db"

def cosine_similarity(a: np.ndarray, b: np.ndarray) -> float:
    return float(np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b) + 1e-8))

class EmbeddingModel:
    # singleton with lazy loading
    ...

# memory_graph.py
from Lilith.memory.base import DB_PATH, cosine_similarity
# ^ only imports base, no circular

# memory_consolidation.py
from Lilith.memory.base import DB_PATH, cosine_similarity
# ^ only imports base, no circular

# enhanced.py
from Lilith.memory.base import DB_PATH, cosine_similarity, EmbeddingModel
from Lilith.memory.memory_graph import MemoryGraph
from Lilith.memory.memory_consolidation import get_consolidation
from Lilith.memory.memory_retrieval import get_retriever
# ^ imports everything after base is loaded, no circular
```

## Rules

1. **base.py must have ZERO imports from sibling modules** — only stdlib + external deps
2. **base.py should contain:** constants, pure functions, simple data classes, singletons with lazy init
3. **Never import from enhanced.py (orchestrator) in leaf modules** — leaf modules import from base, enhanced imports leaves
4. **If you need a type hint from a sibling module** — use `from typing import TYPE_CHECKING` + `if TYPE_CHECKING:` guard

## Detection

Symptoms of circular imports:
- `ImportError: cannot import name 'X' from partially initialized module`
- `AttributeError: module 'Y' has no attribute 'Z'` (module exists but not fully loaded)
- Tests fail at collection time with import errors
- Works when running file directly, fails when imported

## Quick Fix Checklist

- [ ] Identify the two modules that import each other
- [ ] Find what they both need (constants, functions, types)
- [ ] Extract shared needs to `base.py` or `types.py` or `constants.py`
- [ ] Update both modules to import from base
- [ ] Ensure base has no imports from either module
- [ ] Run tests to verify
