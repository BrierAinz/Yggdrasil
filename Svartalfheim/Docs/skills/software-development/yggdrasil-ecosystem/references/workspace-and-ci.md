# Yggdrasil Workspace Configuration

## Root pyproject.toml (excerpt)

```toml
[project]
name = "yggdrasil"
version = "5.0.0"
requires-python = ">=3.9"

[tool.uv.workspace]
members = [
    "Asgard/lilith-core",
    "Asgard/lilith-memory",
    "Asgard/lilith-tools",
    "Asgard/lilith-orchestrator",
    "Asgard/lilith-api",
    "Asgard/lilith-cli",
    "Alfheim/dashboard",
    "Midgard/finanzas",
    "Midgard/habits",
    "Midgard/recipes",
]

[tool.poe.tasks]
test = "pytest"
lint = "ruff check ."
format = "ruff format ."
dashboard = "uvicorn alfheim.dashboard.app:create_app --factory --host 0.0.0.0 --port 8000"
tui = "python -m lilith_cli.tui.app"
api = "python -m lilith_api.run"
clean = "python scripts/clean.py"
```

## CI Workflow (ci.yml) — Key Details

- **Triggers**: push/PR to main, targeting `Asgard/`, `Alfheim/`, `Vanaheim/`, `Midgard/`
- **Lint job**: `ruff check .` (no manual excludes — ruff.toml handles all config)
- **Format job**: `ruff format --check .` (enforced consistency)
- **Test job**: Runs per sub-package in dependency order:
  1. lilith-core (no deps)
  2. lilith-memory (depends on core)
  3. lilith-tools (depends on core)
  4. lilith-api (depends on core + memory + tools; orch skipped with pytest.importorskip)
  5. lilith-cli (depends on api)
  6. alfheim-dashboard (depends on api)
  7. Midgard packages (finanzas, habits, recipes — each with their own deps)
  8. ForgeMaster (Muspelheim/ForgeMaster)
  9. TerminalDashboard (Alfheim/TerminalDashboard)
- **lilith-orchestrator NOT in CI tests**: It's not a proper Python package (no `__init__.py`, just `gateway/gateway.py`). Tests that need it use `pytest.importorskip("lilith_orchestrator")`.
- **Type check**: pyright with `--pythonversion 3.12`, continue-on-error true. Only run on actual packages (not orchestrator).
- **Reliability**: Uses `pip install -e` (not `uv sync` yet — pending workspace maturity)

## pytest.ini (root)

```ini
[pytest]
testpaths = tests Asgard/lilith-core/tests Asgard/lilith-tools/tests Asgard/lilith-memory/tests Asgard/lilith-api/tests Asgard/lilith-cli/tests
python_files = test_*.py *_test.py
python_classes = Test*
python_functions = test_*
addopts = -v --tb=short --strict-markers --ignore=Asgard/Lilith --ignore=Asgard/Hermes-Lilith --ignore=Asgard/Dashboards --ignore=Helheim --ignore=Niflheim --ignore=Jotunheim --ignore=Svartalfheim
markers =
    slow: marks tests as slow (deselect with '-m "not slow"')
    integration: marks tests as integration tests
    unit: marks tests as unit tests
```

**Key points:**
- `--ignore` flags only exclude legacy/archive directories, NOT active packages (Midgard, Alfheim, Muspelheim are included)
- lilith-orchestrator is NOT in testpaths (no proper package, no tests dir)
- Vanaheim/vanaheim-framework is NOT in testpaths (separate test runner if needed)

## ruff.toml (root)

### CRITICAL: `extend-exclude` MUST be at top level

```toml
# ✅ CORRECT — top level
extend-exclude = ["Helheim", ...]

# ❌ WRONG — inside [lint] section (ruff ignores it there)
[lint]
extend-exclude = ["Helheim", ...]   # THIS DOES NOTHING
```

Ruff requires `extend-exclude` at the top level of `ruff.toml`, NOT inside `[lint]`. Placing it in `[lint]` is a silent failure — no error, no warning, but directories won't be excluded. This caused a CI failure with 10,630+ lint errors that should have been excluded.

### Full ruff.toml configuration (May 2026)

```toml
line-length = 100
target-version = "py39"

# TOP LEVEL — not inside [lint]!
extend-exclude = [
    "Helheim",
    "Niflheim",
    "Muspelheim",
    "Svartalfheim",
    "Jotunheim",
    "Asgard/Lilith",
    "Asgard/Hermes-Lilith",
    "Asgard/Dashboards",
    "Asgard/Lilith_backup*",
    "Vanaheim/Agents",
    "Vanaheim/Bots_Lilith_v5",
    "Vanaheim/Config",
    "Vanaheim/Core",
    "Vanaheim/Council",
    "Vanaheim/bots",
    "Vanaheim/bifrost",
    "website-v2",
]

[lint]
select = ["E", "F", "W", "I", "N", "UP", "B", "A", "C4", "T20", "PLC", "PLE", "PLW", "RUF", "TRY", "PTH", "ERA", "FLY", "PERF", "SIM", "TCH", "FIX"]
ignore = [
    "PLC0415",    # import inside function (common in plugin patterns)
    "RUF001",     # ambiguous unicode char in string (Norse runes, emojis)
    "RUF003",     # ambiguous unicode char in comment (Norse runes, emojis)
    "RUF012",     # mutable class default (FastAPI Depends pattern)
    "PTH",        # os.path vs pathlib (legacy code, gradual migration)
    "PLW1510",    # subprocess without check (intentional in many places)
    "TRY301",     #raise inside try (FastAPI error handling pattern)
    "B904",       # raise from None in except (re-raise pattern)
    "ERA001",     # commented-out code (development notes)
    "E402",       # module-level import not at top (sys.path hack)
    "E722",       # bare except (intentional fallback patterns)
    "B008",       # function call in default arg (FastAPI Depends)
    "FIX002",     # line with TODO (development notes)
    "T201",       # print statements (CLI output)
    "A002",       # shadowing builtin (common in web frameworks)
]

[lint.per-file-ignores]
"tests/**" = ["F401", "PTH", "ERA001", "PLW1510", "TRY301"]
"scripts/**" = ["T201", "PTH", "PLW1510"]

[format]
quote-style = "double"
indent-style = "space"
```

### Why these ignore rules:
- **RUF001/RUF003**: Norse runes (ᚠᚢᚦ...), emojis (🪵, ⚔️), and accented chars in docstrings are intentional — not ambiguous
- **PLC0415**: Plugin-style lazy imports where modules import inside functions to avoid circular deps
- **PTH**: os.path→pathlib migration is gradual; legacy dirs excluded, active dirs migrated
- **PLW1510**: Many `subprocess.run()` calls intentionally don't use `check=True`
- **TRY301/B904**: FastAPI error handlers re-raise with different patterns
- **B008**: FastAPI `Depends(function)` pattern requires function calls in default args
- **E402**: `sys.path.insert()` hack in gateway.py and test files

## Known Gaps (as of v5.0.0)

1. CI uses `pip install -e` instead of `uv sync` — needs migration when workspace stabilizes
2. Legacy monolith `Asgard/Hermes-Lilith/` (directory NOT renamed — intentional) is NOT in workspace; 838 tests excluded from CI
3. `sys.path.insert(0, ...)` hack in gateway.py imports from legacy monolith — marked TEMP
4. Dashboard endpoints use mock data with TODO comments for real service integration
5. Gateway ThreadPool was 2 workers, now `min(32, cpu+4)` — may need tuning for production
6. `Alfheim/dashboard/__init__.py` has a backward-compat shim that user declined to delete
7. **Branding migration complete**: All visible-text references updated. Directory paths like `Asgard/Hermes-Lilith/` remain as-is.
8. **Git hygiene gap**: Several file types were committed before .gitignore rules existed. Fixed May 2026 via `git rm --cached`.
9. **ForgeMaster location**: CI workflow must reference `Muspelheim/ForgeMaster/` (NOT `Niflheim/ForgeMaster/`). The project migrated realms but CI paths must be kept in sync.
10. **Duplicate agent files in Vanaheim**: Loose files removed May 2026. The `Name/agent.py` pattern is canonical.
11. **lilith-orchestrator is not a proper Python package**: No `__init__.py`, no `lilith_orchestrator/` package dir, just `gateway/gateway.py`. Tests that import it use `pytest.importorskip("lilith_orchestrator")` to skip gracefully.
12. **lilith-tools ToolRegistry requires explicit import**: Tools don't auto-register on `import ToolRegistry` alone — they register on import + instantiation. Tests must import and instantiate tool classes (e.g., `SystemInfoTool`) before checking `ToolRegistry.list_tools()`.