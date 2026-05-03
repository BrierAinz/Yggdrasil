---
name: yggdrasil-debugging
description: Use when there is a bug, error, or unexpected behavior in Yggdrasil/Lilith
trigger:
  - "bug"
  - "error"
  - "fix"
  - "broken"
  - "not working"
  - "traceback"
  - "exception"
  - "falla"
  - "error"
  - "no funciona"
priority: 95
---

# Yggdrasil Systematic Debugging

## 4-Phase Debugging Protocol

### Phase 1: Understand (Don't Fix Yet!)

**Goal**: Understand the bug before touching code.

**Steps**:
1. Read the error message COMPLETELY
2. Identify the file and line number
3. Understand what the code is SUPPOSED to do
4. Understand what it's ACTUALLY doing
5. Form a hypothesis about the root cause

**Questions**:
- What changed recently? (git log)
- Does it happen consistently? (repro steps)
- What is the expected vs actual behavior?
- Is it environmental? (works on my machine?)

**Output**: Written hypothesis in `docs/superpowers/reviews/debug-{date}.md`

### Phase 2: Reproduce

**Goal**: Make the bug happen on demand.

**Steps**:
1. Create minimal reproduction case
2. Remove all unrelated code
3. Confirm the bug still happens
4. Document exact steps to reproduce

**Example**:
```python
# Minimal reproduction for "memory query returns wrong results"
from Lilith.memory.enhanced import EnhancedMemory

memory = EnhancedMemory()
memory.add_episode("Python async patterns", embedding=[0.1, 0.2, 0.3])
memory.add_episode("JavaScript promises", embedding=[0.9, 0.8, 0.7])

# This should return the Python episode
results = memory.query("async python")
print(results[0].content)  # BUG: Returns JavaScript instead!
```

### Phase 3: Isolate

**Goal**: Find the exact line causing the bug.

**Techniques**:

#### Binary Search
```python
# If function has 100 lines, comment out half
# If bug still happens, it's in the remaining half
# Repeat until you find the exact line
```

#### Print Debugging
```python
# Add prints to trace data flow
def query(self, text):
    print(f"Input: {text}")
    embedding = self.embed(text)
    print(f"Embedding: {embedding[:5]}...")
    results = self.search(embedding)
    print(f"Raw results: {results}")
    return results
```

#### Rubber Duck
Explain the code line by line to yourself (or a rubber duck):
- "This line gets the embedding..."
- "This line searches the database..."
- "Wait, why is it using cosine similarity here?"

#### Git Bisect
```bash
# Find which commit introduced the bug
git bisect start
git bisect bad HEAD
git bisect good v2.0.0  # last known good version
git bisect run python -m pytest tests/test_memory.py
```

### Phase 4: Fix

**Goal**: Fix the root cause, not the symptom.

**Steps**:
1. Write a test that FAILS with the current bug
2. Make the MINIMUM change to fix it
3. Run the test, confirm it PASSES
4. Run ALL tests, confirm nothing broke
5. Document the fix

**Rules**:
- Fix ONE thing at a time
- If the fix is complex, the hypothesis was wrong
- If tests break, the fix is wrong
- Document WHY the fix works

## Common Bug Patterns in Lilith

### Memory Bugs
| Symptom | Likely Cause | Fix |
|---------|-------------|-----|
| Wrong results | Embedding mismatch | Check embedder model |
| Slow queries | Missing index | Add SQLite index on embeddings |
| Data loss | Transaction not committed | Add `db.commit()` |
| Duplicates | No unique constraint | Add `UNIQUE` constraint |

### Async Bugs
| Symptom | Likely Cause | Fix |
|---------|-------------|-----|
| "RuntimeError: Event loop closed" | Loop closed before task done | Use `asyncio.run()` properly |
| Tasks not running | Forgot to `await` | Add `await` |
| Race condition | Shared mutable state | Use locks or immutable data |

### Tool Bugs
| Symptom | Likely Cause | Fix |
|---------|-------------|-----|
| Tool not found | Not registered | Add to `TOOL_EXECUTORS` |
| Wrong arguments | Schema mismatch | Update tool schema |
| Timeout | Tool takes too long | Increase timeout or optimize |

## Debugging Tools

### Python Debugger (pdb)
```python
# Add breakpoint
import pdb; pdb.set_trace()

# Commands:
# n - next line
# s - step into function
# c - continue
# p variable - print variable
# l - list code around current line
# q - quit
```

### Logging
```python
import logging

logger = logging.getLogger("lilith.debug")
logger.setLevel(logging.DEBUG)

# Add to code
logger.debug(f"Memory query: {query}")
logger.debug(f"Results: {results}")
```

### Stack Traces
```python
import traceback

try:
    risky_operation()
except Exception as e:
    print(f"Error: {e}")
    traceback.print_exc()  # Full stack trace
```

## Anti-Patterns

- ❌ Fixing without understanding
- ❌ Changing multiple things at once
- ❌ Not writing a test for the bug
- ❌ Ignoring the root cause (fixing symptoms)
- ❌ Not documenting the fix
- ❌ "It works on my machine" (reproduce first!)

## Yggdrasil-Specific

### Realm Debugging
```
Bug in Asgard (Lilith core) → Check Core/ modules
Bug in Vanaheim (agents) → Check Agents/ modules
Bug in memory → Check memory/ modules
Bug in tools → Check tools/ modules
```

### Common Lilith Issues
1. **LM Studio not responding**: Check if LM Studio is running on port 1234
2. **Embeddings slow**: First load takes time, subsequent are fast
3. **Memory DB locked**: Another Lilith instance is running
4. **Tool timeout**: Increase `TOOL_TIMEOUT` in config

### Debug Script Template
```python
#!/usr/bin/env python3
"""Debug script for issue #{number}"""

import sys
sys.path.insert(0, "Lilith")

from Lilith.memory.enhanced import EnhancedMemory

# Reproduction case
memory = EnhancedMemory()
# ... your reproduction code here ...

if __name__ == "__main__":
    # Run and observe
    pass
```
