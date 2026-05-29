# CI + uv Workspace Debugging Log (May 2026)

## Problem: Yggdrasil CI failing at "Install workspace dependencies"

The GitHub Actions CI workflow was failing when running `uv sync --all-packages`
because the YggdrasilForge sub-package couldn't be built.

### Root Cause 1: Wrong build-backend string

`Alfheim/YggdrasilForge/pyproject.toml` had:
```toml
build-backend = "hatchling.backends"
```
Correct value:
```toml
build-backend = "hatchling.build"
```
`hatchling.backends` is not a valid module — it must be `hatchling.build`.

### Root Cause 2: Missing extra-build-dependencies

`uv sync --all-packages` builds workspace members but doesn't auto-resolve
their build dependencies. Hatchling needs to be declared at the root level:

```toml
# Root pyproject.toml
[tool.uv.extra-build-dependencies]
hatchling = ["hatchling"]
```

### Root Cause 3: Hatchling can't find package code

YggdrasilForge stores its code in `backend/` (not `src/`). Without explicit
configuration, hatchling doesn't know where the code is:

```toml
# Alfheim/YggdrasilForge/pyproject.toml
[tool.hatch.build.targets.wheel]
packages = ["backend"]
```

### Root Cause 4: pytest import failures from root

When running `uv run pytest` from the workspace root, pytest imports fail for
sub-packages because their source directories aren't on sys.path. Fix per
sub-package:

```toml
[tool.pytest.ini_options]
pythonpath = ["."]
```

### Root Cause 5: uv sync doesn't install pytest into root venv

`uv sync --all-packages --dev` installs dev dependencies for sub-packages but
does NOT install them into the root venv where `uv run` spawns. The root
pyproject.toml's `[project.optional-dependencies] dev` is NOT the same as uv's
dependency groups.

**Fix**: Use `[dependency-groups]` (PEP 735) in root pyproject.toml, NOT
`[tool.uv.dev-dependencies]` (deprecated in uv >= 0.4):

```toml
# Root pyproject.toml — CORRECT format for uv >= 0.4
[dependency-groups]
dev = [
    "pytest>=8.0",
    "pytest-asyncio>=0.23",
    "httpx>=0.27",
]
```

**WRONG** (old format, causes parse errors in uv >= 0.11):
```toml
[tool.uv.dev-dependencies]
pytest = ">=8.0"  # This is a map, uv expects a sequence
```

**ALSO WRONG** (valid TOML but uv rejects it as "invalid type: map, expected a sequence"):
```toml
[tool.uv.dev-dependencies]
dev = ["pytest>=8.0"]  # Still fails — use [dependency-groups] instead
```

### Root Cause 6: conftest conflicts across sub-packages

Running a single `uv run pytest` across all workspace members causes
`ImportPathMismatchError` because conftest.py files from different packages
shadow each other. Fix: iterate per-package with `--rootdir=$pkg`.

### Root Cause 7: Sub-package missing runtime dependencies

`Asgard/lilith-core` had `import litellm` in its source code but didn't declare
`litellm` in `[project.dependencies]`. This caused `ModuleNotFoundError` in CI
where no local packages are pre-installed.

**Lesson**: Always audit `grep -r 'import X' <pkg>/` against `[project.dependencies]`
in each sub-package's pyproject.toml. Runtime imports MUST be declared as
dependencies, even if they're "optional" in practice.

### Root Cause 8: Sub-package pytest addopts leaking into CI

`Alfheim/TerminalDashboard/pyproject.toml` had:
```toml
[tool.pytest.ini_options]
addopts = "--cov=tui --cov-report=term-missing --cov-fail-under=70"
```
This gets inherited when running pytest from the monorepo root. `pytest-cov`
isn't installed in CI, causing `unrecognized arguments` error.

**Fix**: Pass `--override-ini="addopts="` when running pytest in CI to clear
any inherited addopts from sub-packages.

### Root Cause 9: Cross-package import failures in tests

When sub-package A imports sub-package B at module level, but B isn't installed
as a proper dependency or its module name doesn't match its package name, tests
fail with `ModuleNotFoundError`.

Example: `lilith-api` does `from lilith_orchestrator.engine import LilithEngine`
but `lilith-orchestrator` installs as `gateway` (its `[tool.hatch.build.targets.wheel]
packages = ["gateway"]`), so `lilith_orchestrator` as a module doesn't exist.

**Fix**: Create `conftest.py` in the test directory that injects mock stubs
into `sys.modules` before the real module is imported. Pattern from
`Asgard/lilith-orchestrator/tests/conftest.py`:

```python
import sys, types
from unittest.mock import MagicMock

def _make_stub(name, **attrs):
    mod = types.ModuleType(name)
    for k, v in attrs.items():
        setattr(mod, k, v)
    return mod

# Must match the return values the real module would produce
_mock_engine = MagicMock()
_mock_engine.process = MagicMock(return_value={"response": "stub", "tool_call": None, "context": []})

_lilith_orchestrator = _make_stub(
    "lilith_orchestrator",
    engine=_make_stub("lilith_orchestrator.engine", LilithEngine=MagicMock(return_value=_mock_engine)),
)
sys.modules.setdefault("lilith_orchestrator", _lilith_orchestrator)
sys.modules.setdefault("lilith_orchestrator.engine", _lilith_orchestrator.engine)
```

**Critical**: Stubs must return values matching the real API's **Pydantic**
contract — including field types. If `ChatResponse.tool_call` is `dict[str, Any]`
(not `Optional`), the mock MUST return `{}` not `None`. Pydantic validates at
the response boundary, so `None` on a non-optional dict field raises
`ValidationError`. Always check the Pydantic model definition before writing
mock return values.

See also `references/ci-fixes-may-2026-2.md` — Root Causes 10-12.

## Final Working CI Configuration

```yaml
# .github/workflows/ci.yml — test job
- name: Install workspace dependencies
  run: uv sync --all-packages --dev

- name: Verify pytest available
  run: uv run python -m pytest --version

- name: Run pytest (per-package)
  run: |
    FAILED=0
    for pkg in $(uv run python -c "
    import tomllib, pathlib
    root = tomllib.loads(pathlib.Path('pyproject.toml').read_text())
    for m in root['tool']['uv']['workspace']['members']:
      print(m)
    "); do
      if [ -d "$pkg/tests" ]; then
        echo "::group::pytest $pkg"
        uv run python -m pytest "$pkg/tests" --tb=short -q --rootdir="$pkg" \
          --override-ini="addopts=" -p no:cacheprovider || FAILED=1
        echo "::endgroup::"
      fi
    done
    exit $FAILED
```

Key flags:
- `uv run python -m pytest` — use `python -m` instead of bare `pytest` (more reliable)
- `--rootdir="$pkg"` — isolates each package's conftest
- `--override-ini="addopts="` — clears sub-package addopts (like --cov flags)
- `-p no:cacheprovider` — avoids cache conflicts between packages

## Commit Trail

1. `b17830a` [ASGARD] ruff fix 13 lint issues + format
2. `32ff44a` [MIDGARD] remove stray YggdrasilForge/ from root
3. `f125794` [ASGARD] skip continue-on-error, bump checkout v6
4. `c825df6` [ALFHEIM] add YggdrasilForge to workspace
5. `7cb59f0` [ALFHEIM] track YggdrasilForge source + 41 tests
6. `199286b` [ASGARD] hatchling build-backend, per-package pytest, extra-build-deps
7. `e258a52` [ASGARD] install pytest into venv (superseded by dependency-groups)
8. `2fee079` [ASGARD] [dependency-groups] dev for pytest, litellm dep, verify step

### Resolved (Round 2, May 2026)

- lilith-api conftest.py stubs committed — mock `tool_call` changed from `None` to `{}` to match Pydantic `dict[str, Any]` type
- `--override-ini="addopts="` flag in CI pytest command — committed
- Typer completion tests merged into version-agnostic single test
- ruff format fix — always use `uv run ruff format`, not local `ruff`
- CI is **GREEN** as of commit b2a9ece

### Key Takeaway

**uv workspace + hatchling + pytest CI is a 9-layer debugging onion.** Each
layer reveals the next: build-backend string → missing build deps → package
discovery → pythonpath → venv pytest → conftest conflicts → missing runtime
deps → addopts leaking → cross-package import stubs. Test locally with
`uv run python -m pytest` from root AFTER each fix before pushing.

## Dependabot Cleanup

Closed PRs #9, #10, #11, #12 — all targeted `Helheim/Dashboards_legacy/web`
which is archived legacy code. Don't invest time fixing legacy dependencies.

## GitHub Pages First Deploy

Successfully triggered `deploy-website.yml` via `gh workflow run`.
Site live at: https://brierainz.github.io/Yggdrasil/