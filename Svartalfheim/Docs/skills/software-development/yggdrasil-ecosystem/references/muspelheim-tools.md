# Cross-Realm Tool Development Patterns

Auto-generated from AutoSub (plan-01), ForgeMaster (plan-18), and TerminalDashboard
(plan-13) implementation sessions. Applies to all standalone Yggdrasil tools regardless
of realm: Muspelheim (AutoSub, ClipForge, TrendRadar), Niflheim (ForgeMaster),
Alfheim (TerminalDashboard), etc.

## Project Scaffold

Each Muspelheim tool follows this structure:

```
Muspelheim/<ToolName>/
├── pyproject.toml          # [project] + [tool.pytest.ini_options]
├── README.md
├── .gitignore
├── <toolname>/
│   ├── __init__.py         # __version__, public API exports
│   ├── cli.py              # Typer app with Rich console
│   ├── transcriber.py      # Core module(s)
│   ├── exporter.py
│   └── ...
└── tests/
    ├── __init__.py
    ├── test_transcriber.py  # One test file per module
    ├── test_integration.py  # Cross-module integration tests
    └── ...
```

## pyproject.toml Template

```toml
[project]
name = "toolname"
version = "0.1.0"
description = "One-line description"
requires-python = ">=3.11"
dependencies = [
    "rich>=13.0",
    "typer>=0.9",
]

[project.optional-dependencies]
dev = ["pytest>=7.0", "pytest-cov"]

[project.scripts]
toolname = "toolname.cli:app"

[tool.pytest.ini_options]
testpaths = ["tests"]
```

## Commit Prefix by Realm

| Realm | Prefix | Example |
|-------|--------|---------|
| Asgard | `[ASGARD]` | `[ASGARD] feat(lilith-core): add store` |
| Vanaheim | `[VANHEIM]` | `[VANHEIM] fix(agent): routing` |
| Alfheim | `[ALFHEIM]` | `[ALFHEIM] feat(dashboard): panel` |
| Svartalfheim | `[SVARTALFHEIM]` | `[SVARTALFHEIM] docs: plans` |
| Muspelheim | `[MUSPELHEIM]` | `[MUSPELHEIM] feat(autosub): batch` |
| Midgard | `[MIDGARD]` | `[MIDGARD] feat(habits): export` |

## Common Python Pitfalls (Yggdrasil-specific)

### Dataclass Defaults
```python
# WRONG — dataclass fields have no .default class attribute
@classmethod
def from_dict(cls, data):
    return cls(name=data.get("name", cls.name.default))  # AttributeError!

# CORRECT — instantiate to get defaults
defaults = cls()
return cls(name=data.get("name", defaults.name))
```

### Path Type Coercion in Constructors
```python
# WRONG — if user passes str, .mkdir() fails
def __init__(self, cache_dir: Path | None = None):
    self.cache_dir = cache_dir or Path.home() / ".cache"
    self.cache_dir.mkdir(...)  # AttributeError: 'str' has no 'mkdir'

# CORRECT — always coerce to Path
def __init__(self, cache_dir: Path | None = None):
    self.cache_dir = Path(cache_dir) if cache_dir else Path.home() / ".cache"
```

### Nested Return Types
Always verify the actual return shape before writing assertions. If `align_segments()`
returns `list[list[Word]]` (words grouped per segment), do NOT flatten to `list[Word]`
before passing to `words_to_segments()` — it expects the nested structure.

## Testing Patterns

- One test file per module: `test_<module>.py`
- Integration test file: `test_integration.py` for cross-module flows
- Use `tmp_path` fixture for filesystem tests (pytest builtin)
- Use `monkeypatch` for environment/UI overrides
- Mock external APIs (faster-whisper, deep-translator) — tests must pass without GPU or network

## Venv Setup on WSL (No Sudo)

```bash
cd /mnt/d/Proyectos/Yggdrasil/Muspelheim/<ToolName>
python3 -m venv --without-pip .venv
source .venv/bin/activate
curl -sS https://bootstrap.pypa.io/get-pip.py | python3
pip install -e ".[dev]"
```