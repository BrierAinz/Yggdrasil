# CI Fixes — May 2026 Round 2

## Root Cause 10: Pydantic mock type mismatch

`conftest.py` returned `{"response": "stub", "tool_call": None, "context": []}` but
the endpoint builds a `ChatResponse` pydantic model with `tool_call: dict[str, Any]`
(not `Optional[dict[str, Any]]`). Pydantic validates at the response boundary, so
`None` on a non-optional dict field raises `ValidationError`.

**Fix**: Match mock return values to the Pydantic model definition exactly:
```python
_mock_engine.process = MagicMock(
    return_value={"response": "stub", "tool_call": {}, "context": []}
)
```

Always inspect the Pydantic model before writing mock return values. A `dict` field
MUST return `{}`, not `None`, unless the model explicitly marks it `Optional`.

## Root Cause 11: Typer >=0.12 completion command names changed

Tests asserting `"install-completion" in output` or `"show-completion" in output`
break on Typer >=0.12, which renamed these to `shell-completion`.

**Fix**: Use a version-agnostic check:
```python
def test_help_shows_completion_option(self) -> None:
    result = runner.invoke(app, ["--help"])
    assert result.exit_code == 0
    assert "completion" in result.output.lower()
```

## Root Cause 12: Local ruff format version mismatch with CI

Running `pip install ruff` locally may install a different version than what CI uses
(from `uv.lock`). A format that looks correct locally can fail `ruff format --check`
in CI.

**Fix**: Always use `uv run ruff format <file>` and `uv run ruff check <file>`,
not bare `ruff` or `pip install ruff`. This uses the pinned version from the lockfile.

## Security Bumps (May 2026)

- `litellm>=1.83.7` — fixes 1 critical + 2 high CVEs (SQL injection, command
  execution via MCP stdio endpoints, SSTI in /prompts/test)
- `vite ^6.4.2` — replaces `^6.0.0` / `^5.1.0`
- `postcss ^8.5.10` — replaces `^8.4.49` / `^8.4.35`
- lodash and serialize-javascript are transitive JS deps — no direct fix possible

## Commit Trail (Round 2)

1. `0b6e2e3` [ASGARD] security: bump litellm >=1.83.7, vite ^6.4.2, postcss ^8.5.10
2. `2b67f63` [ASGARD] fix: ruff format conftest.py
3. `36e8cb4` [ASGARD] fix: ChatResponse mock tool_call None->empty dict, merge tyler completion tests
4. `b2a9ece` [ASGARD] fix: ruff format conftest.py (final — used `uv run ruff format`)

## Final State

CI is **GREEN** as of commit b2a9ece:
- Lint (ruff): ✅ success
- Test (pytest, Python 3.11): ✅ success
- Test (pytest, Python 3.12): ✅ success
- Type check (pyright): ✅ success

98 tracked files with hardcoded `D:\Proyectos\Yggdrasil` paths — all in legacy
Lilith monolith (Asgard/Lilith) and Helheim (archives). Not worth refactoring;
active sub-packages (lilith-core, lilith-api, etc.) use relative paths.

Hermes Agent updated to v0.13.0 (338 files, 45k+ insertions from upstream).