# Pre-Commit Hooks: First Attempt Fails, Second Passes

## Pattern

When committing with pre-commit hooks (black, isort, trailing-whitespace, end-of-file-fixer):

**First attempt:**
```
trim trailing whitespace.................................................Failed
fix end of files.........................................................Failed
black....................................................................Failed
isort....................................................................Failed
```

**What happened:** Hooks auto-fixed files but commit was aborted.

**Second attempt (after `git add -A`):**
```
trim trailing whitespace.................................................Passed
fix end of files.........................................................Passed
black....................................................................Passed
isort....................................................................Passed
[main abc1234] feat: ...
```

## Workflow

```bash
# 1. Stage everything
git add -A

# 2. Commit (hooks will auto-fix and abort)
git commit -m "feat: ..."
# → Fails, but files are fixed

# 3. Re-stage fixed files
git add -A

# 4. Commit again (now passes)
git commit -m "feat: ..."
```

## Why This Happens

Pre-commit hooks are configured as "fixing" hooks — they modify files in-place but return non-zero exit code to signal "files were changed, please review and re-stage." This is by design: you should review what the tools changed before committing.

## In Practice (Hermes Agent)

When using the `terminal` tool to commit:

```python
# First attempt — expect failure, it's normal
terminal("cd /project && git add -A && git commit -m 'feat: ...'")
# → exit code 1, hooks fixed files

# Second attempt — should pass
terminal("cd /project && git add -A && git commit -m 'feat: ...'")
# → exit code 0, committed
```

**Don't panic on first failure.** Check if the failure message says "files were modified by this hook" — if so, just re-stage and retry.

## Common Hooks in This Project

| Hook | Fixes |
|------|-------|
| `trailing-whitespace` | Removes trailing spaces from all lines |
| `end-of-file-fixer` | Ensures files end with exactly one newline |
| `black` | Python code formatting |
| `isort` | Python import sorting |

## Prevention

Run formatting before committing:

```bash
black src/ tests/
isort src/ tests/
```

Or configure editor to run black on save.
