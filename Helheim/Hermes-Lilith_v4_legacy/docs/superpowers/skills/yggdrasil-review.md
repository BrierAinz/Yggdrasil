---
name: yggdrasil-review
description: Use before committing any code change in Yggdrasil/Lilith
trigger:
  - "commit"
  - "push"
  - "merge"
  - "pull request"
  - "review"
  - "listo"
  - "terminado"
  - "hecho"
priority: 85
---

# Yggdrasil Pre-Commit Review

## Checklist

Before every commit, run through this checklist:

### Code Quality
- [ ] No `print()` statements left (use `logging`)
- [ ] No hardcoded secrets (use environment variables)
- [ ] No commented-out code (delete it, git has history)
- [ ] Functions are <50 lines
- [ ] Classes are <300 lines
- [ ] No TODO without issue number (TODO #123)

### Testing
- [ ] New code has tests
- [ ] All tests pass (`pytest`)
- [ ] Coverage didn't decrease
- [ ] Edge cases are tested (empty input, None, etc.)

### Documentation
- [ ] Docstrings for public functions
- [ ] Type hints for function signatures
- [ ] README updated if behavior changed
- [ ] Comments explain WHY, not WHAT

### Style
- [ ] Consistent with project style (black formatter)
- [ ] Variable names are meaningful
- [ ] No magic numbers (use constants)
- [ ] Error messages are helpful

### Performance
- [ ] No N+1 queries
- [ ] No unnecessary loops
- [ ] Large operations are batched
- [ ] Memory leaks checked

### Security
- [ ] No SQL injection (use parameterized queries)
- [ ] No command injection (validate inputs)
- [ ] No path traversal (validate paths)
- [ ] Secrets not in logs

## Review Process

### Self-Review
```bash
# 1. Review your own diff
git diff

# 2. Check for issues
# - Look for debugging prints
# - Check for hardcoded values
# - Verify error handling

# 3. Run tests
pytest

# 4. Run linter
black --check Lilith/
flake8 Lilith/

# 5. If all good, commit
git commit -m "feat: add semantic memory graph

- Add NetworkX graph for memory relations
- Implement cosine similarity search
- Add tests for graph operations

Closes #123"
```

### Peer Review (if applicable)
```
1. Create PR with description
2. Link to plan document
3. Tag relevant people
4. Address feedback
5. Merge only after approval
```

## Commit Message Format

```
type: short description (50 chars max)

Longer explanation if needed (wrap at 72 chars).

- Bullet points for changes
- Reference issues: Closes #123
- Breaking changes: BREAKING: description

Types:
  feat:     New feature
  fix:      Bug fix
  docs:     Documentation
  style:    Formatting (no code change)
  refactor: Code restructuring
  perf:     Performance improvement
  test:     Tests only
  chore:    Build/tooling
```

## Example Reviews

### Good Commit
```
feat: add memory graph with entity extraction

- Add NetworkX graph for episodic memory
- Extract entities using regex + NER
- Link episodes to entities via relations
- Add graph query with multi-hop traversal
- Tests: 15 new tests, 92% coverage

Closes #45
```

### Bad Commit
```
fix stuff

some changes to memory
```

## Automated Checks

### Pre-Commit Hook
```bash
#!/bin/sh
# .git/hooks/pre-commit

# Run tests
pytest || exit 1

# Run linter
black --check Lilith/ || exit 1

# Check for secrets
grep -r "API_KEY\|SECRET\|TOKEN" Lilith/ && exit 1

# Check for debug prints
grep -r "print(" Lilith/Core/ && exit 1
```

### CI Pipeline
```yaml
# .github/workflows/ci.yml
name: CI
on: [push, pull_request]
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: '3.11'
      - run: pip install -r requirements-dev.txt
      - run: pytest --cov=Lilith --cov-report=xml
      - run: black --check Lilith/
      - run: flake8 Lilith/
```

## Anti-Patterns

- ❌ Committing without review
- ❌ Large commits (>500 lines)
- ❌ Committing broken code ("will fix later")
- ❌ No commit message
- ❌ Committing secrets
- ❌ Committing generated files (cache, build)

## Yggdrasil-Specific

### Realm Changes
- Asgard changes → Review by core team
- Vanaheim changes → Review by AI team
- Cross-realm → Review by both

### Memory Changes
- Any change to memory/ → Run full memory test suite
- Database schema changes → Migration required
- Embedding model changes → Re-index all data

### Tool Changes
- New tool → Add to `TOOL_EXECUTORS` + tests
- Tool schema change → Update all callers
- Tool removal → Check for references
