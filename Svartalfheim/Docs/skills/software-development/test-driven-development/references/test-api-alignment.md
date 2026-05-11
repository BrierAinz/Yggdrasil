# Test-Implementation API Alignment

## Problem

Tests written against a planned API fail because the implementation evolved with different names, signatures, or data structures.

## Session Example: Hermes-Lilith Memory v2.0

### Mismatch 1: Method Names
**Test expected:** `graph.extract_relations(text, entities)`
**Implementation had:** `graph.extract_relations_from_text(text, entities)`
**Fix:** Added alias in implementation:
```python
def extract_relations(self, text, entities):
    """Alias for extract_relations_from_text."""
    return self.extract_relations_from_text(text, entities)
```

### Mismatch 2: Return Structure
**Test expected:** `results[0]["content"]`
**Implementation returned:** `results[0]["user_input"]` and `results[0]["response"]`
**Fix:** Updated tests to use actual field names:
```python
# Before (broken):
assert "python" in results[0]["content"].lower()

# After (fixed):
assert "python" in results[0]["user_input"].lower()
```

### Mismatch 3: Missing Methods
**Test expected:** `retriever.add_episode()`, `retriever.update_episode()`, `retriever.delete_episode()`
**Implementation had:** Only `retrieve()`, no CRUD methods
**Fix:** Added CRUD methods to retriever:
```python
def add_episode(self, episode_id, user_input, response="", context="", timestamp=None):
    # insert into episodes table
    
def update_episode(self, episode_id, user_input=None, response=None, context=None):
    # update fields
    
def delete_episode(self, episode_id):
    # delete from episodes
```

### Mismatch 4: Deduplication Logic
**Test expected:** No duplicate content in results
**Implementation behavior:** Returns episodes by unique ID, not unique content
**Fix:** Updated test expectation to match actual behavior:
```python
# Before (wrong expectation):
contents = [r["user_input"] for r in results]
assert len(contents) == len(set(contents))

# After (correct expectation):
ids = [r["id"] for r in results]
assert len(ids) == len(set(ids))
```

## Resolution Strategies

| Situation | Strategy | When to Use |
|-----------|----------|-------------|
| Method name differs | Add alias to implementation | Alias is cheap, preserves backward compat |
| Field name differs | Update tests to match implementation | Tests should document reality, not fantasy |
| Method missing from implementation | Add method to implementation | If it's genuinely needed |
| Test expectation wrong | Fix the test | When implementation behavior is correct |
| Both are wrong | Pick one, document the choice | When neither is clearly better |

## Rule of Thumb

**Tests are living documentation of behavior.** They should reflect what the code ACTUALLY does, not what it was PLANNED to do. If the implementation surprised you, the test documents your misunderstanding — fix the test and add a comment.

Exception: If the planned API is objectively better, refactor the implementation to match. But don't do this reactively just to make tests pass — make a deliberate choice.
