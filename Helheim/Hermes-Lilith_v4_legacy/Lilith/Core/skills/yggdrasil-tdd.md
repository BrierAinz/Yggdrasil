---
name: yggdrasil-tdd
description: Use when implementing any feature, bugfix, or refactor in Yggdrasil/Lilith
trigger:
  - "implement"
  - "feature"
  - "bugfix"
  - "refactor"
  - "test"
  - "testing"
priority: 90
---

# Yggdrasil Test-Driven Development (TDD)

## Iron Law
**NO PRODUCTION CODE WITHOUT A FAILING TEST FIRST.**

This is non-negotiable. Every line of production code must be justified by a test that failed before the code existed.

## Red-Green-Refactor Cycle

### RED (Write the test)
1. Understand the requirement
2. Write a test that FAILS
3. Run the test, confirm it fails
4. If the test passes, the test is wrong - rewrite it

### GREEN (Make it pass)
1. Write the MINIMUM code to make the test pass
2. Copy-paste from StackOverflow is allowed
3. Hard-coding is allowed (for now)
4. Run the test, confirm it passes

### REFACTOR (Clean it up)
1. Remove duplication
2. Improve names
3. Extract methods/classes
4. Run tests after each change
5. All tests must still pass

## Rules

### 1. Tests First, Always
```python
# ❌ WRONG: Writing production code first
def calculate_total(items):
    return sum(item.price for item in items)

# Then writing test
def test_calculate_total():
    assert calculate_total([Item(10), Item(20)]) == 30

# ✅ CORRECT: Test first
def test_calculate_total():
    assert calculate_total([Item(10), Item(20)]) == 30

# Run test → FAILS (function doesn't exist yet)

# Then production code
def calculate_total(items):
    return sum(item.price for item in items)

# Run test → PASSES
```

### 2. One Concept Per Test
```python
# ❌ WRONG: Testing multiple things
def test_user():
    user = User("Alice")
    assert user.name == "Alice"
    user.set_age(25)
    assert user.age == 25
    user.save()
    assert user.id is not None

# ✅ CORRECT: Separate tests
def test_user_has_name():
    assert User("Alice").name == "Alice"

def test_user_can_set_age():
    user = User("Alice")
    user.set_age(25)
    assert user.age == 25

def test_user_can_save():
    user = User("Alice")
    user.save()
    assert user.id is not None
```

### 3. Test Names Are Sentences
```python
# ❌ WRONG
def test_1():
def test_user():

# ✅ CORRECT
def test_user_can_register_with_valid_email():
def test_user_cannot_register_with_duplicate_email():
def test_user_password_must_be_at_least_8_characters():
```

### 4. Arrange-Act-Assert
```python
def test_user_can_login():
    # ARRANGE
    user = User("alice", password="secret123")
    user.save()

    # ACT
    result = login("alice", "secret123")

    # ASSERT
    assert result.success is True
    assert result.user == user
```

## Testing Patterns for Lilith

### Async Code
```python
import pytest
import asyncio

@pytest.mark.asyncio
async def test_memory_can_store_episode():
    memory = EnhancedMemory()
    episode = Episode(content="test", embedding=[0.1, 0.2])

    result = await memory.add_episode(episode)

    assert result.id is not None
    assert await memory.get_episode(result.id) == episode
```

### Mocking External Services
```python
from unittest.mock import Mock, patch

def test_llm_client_retries_on_failure():
    with patch('httpx.AsyncClient.post') as mock_post:
        mock_post.side_effect = [Exception("Timeout"), MockResponse("OK")]

        client = LMStudioClient()
        result = client.complete("test")

        assert result == "OK"
        assert mock_post.call_count == 2
```

### Testing with Real Database (Integration)
```python
@pytest.fixture
def memory_db(tmp_path):
    db = EnhancedMemory(db_path=tmp_path / "test.db")
    yield db
    db.cleanup()

def test_memory_query_returns_relevant_results(memory_db):
    memory_db.add_episodes([
        Episode("Python async patterns", embedding=...),
        Episode("JavaScript promises", embedding=...),
    ])

    results = memory_db.query("async python")

    assert len(results) == 1
    assert "Python" in results[0].content
```

## Test File Organization

```
Lilith/
├── Core/
│   ├── skill_registry.py
│   └── tests/
│       ├── __init__.py
│       ├── test_skill_registry.py
│       └── test_skill_parser.py
├── memory/
│   ├── enhanced.py
│   └── tests/
│       ├── __init__.py
│       ├── test_enhanced.py
│       └── test_graph.py
```

## Running Tests

```bash
# All tests
pytest

# Specific module
pytest Lilith/Core/tests/

# With coverage
pytest --cov=Lilith --cov-report=html

# Watch mode (rerun on file change)
pytest -f

# Parallel (faster)
pytest -n auto
```

## Coverage Goals

| Module | Minimum Coverage |
|--------|---------------|
| Core | 90% |
| memory | 85% |
| tools | 80% |
| Swarm | 85% |
| MCP | 80% |

## Anti-Patterns

- ❌ Writing production code before tests
- ❌ Tests that don't fail when code is broken
- ❌ Tests that depend on other tests
- ❌ Tests that hit real external APIs (mock them)
- ❌ Tests with random data (use fixed inputs)
- ❌ Tests that take >1 second (unless integration)
- ❌ Testing implementation details (test behavior)

## Yggdrasil-Specific Testing

### Testing Memory
- Always test with fresh database (use tmp_path)
- Test embedding similarity, not exact values
- Test graph traversal with known structures

### Testing Tools
- Mock file system operations
- Mock network calls
- Test error handling (what if file doesn't exist?)

### Testing Swarm
- Use in-memory message bus for tests
- Test conflict detection with known overlaps
- Test agent lifecycle (spawn → work → complete)
