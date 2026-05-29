☵ Yggdrasil Terminal Dashboard
═══════════════════════════

A [bold #c8a23e]dark-fantasy themed[/] TUI (Textual/Rich) that shows the status of all
Yggdrasil realms, projects, health checks, and allows navigating the ecosystem
from a single terminal screen.

```
             🌲  YGGDRASIL  🌲
           ╔══════════════════════╗
           ║  ☲  Asgard     [bold green]●[/]  ║
           ║  🌿  Vanaheim   [bold green]●[/]  ║
           ║  ✨  Alfheim    [bold yellow]●[/]  ║
           ║  🔨  Svartalf.  [bold green]●[/]  ║
           ║  🔥  Muspelheim [bold green]●[/]  ║
           ║  ❄   Niflheim   [dim]○[/]  ║
           ║  💀  Helheim    [dim]○[/]  ║
           ║  👹  Jotunheim  [bold green]●[/]  ║
           ║  🌍  Midgard    [bold green]●[/]  ║
           ╚══════════════════════╝
```

---

## Features

- **9-Realm Overview** -- Monitor all nine Yggdrasil realms (Asgard, Vanaheim,
  Alfheim, Svartalfheim, Muspelheim, Niflheim, Helheim, Jotunheim, Midgard)
  from a single dashboard.
- **Real-time Health Indicators** -- `[bold green]●[/]` Healthy  `[bold yellow]●[/]` Degraded  `[bold red]○[/]` Down
- **Git Activity per Realm** -- Branch, status, recent commits, dirty/clean at a glance.
- **System Health Monitoring** -- CPU, RAM, swap, disk, GPU (via nvidia-smi), and
  Python process tracking.
- **Auto-refresh with Change Detection** -- Dashboard updater with flash animations
  when values shift significantly.
- **Quick Actions** -- Run tests, check git, open VS Code, open docs, health panel
  -- all with single-key shortcuts.
- **Dark Norse Theme** -- Tokyonight-inspired palette with gold accents (#c8a23e),
  rune-aware iconography, and a persistent dark-fantasy aesthetic.
- **Shell Completion** -- Full tab-completion for Bash, Zsh, Fish, and PowerShell
  via Typer.

---

## Installation

### From source (editable, recommended for development)

```bash
git clone <repo-url> && cd TerminalDashboard
pip install -e ".[dev]"
```

### From PyPI (when published)

```bash
pip install terminaldashboard
```

### Requirements

- Python ≥ 3.11
- [Textual](https://textual.textualize.io/) ≥ 2.0
- [Rich](https://rich.readthedocs.io/) ≥ 13.0
- [psutil](https://psutil.readthedocs.io/) ≥ 5.9
- [Typer](https://typer.tiangolo.com/) ≥ 0.9.0

---

## Usage

### Launch the Dashboard

```bash
# Via entry point
yggdrasil-dashboard

# Or via Python module
python -m tui.cli
```

### Check Version

```bash
yggdrasil-dashboard --version

# Output:
#☵ Yggdrasil Dashboard  v1.0.0
```

### Keybindings

| Key | Action |
|-----|--------|
| `q` | Quit |
| `r` | Refresh all realms |
| `1` | Switch to Asgard |
| `2` | Switch to Vanaheim |
| `3` | Switch to Alfheim |
| `4` | Switch to Svartalfheim |
| `5` | Switch to Muspelheim |
| `6` | Switch to Niflheim |
| `7` | Switch to Helheim |
| `8` | Switch to Jotunheim |
| `9` | Switch to Midgard |
| `t` | Run tests for current realm |
| `g` | Git status / commit summary |
| `h` | Health panel (CPU, RAM, GPU…) |
| `o` | Open project in VS Code |
| `d` | Open docs in browser |

### Screenshots (Rich Console Markup Preview)

```
┌──────────────────────────────────────────────────────────────┐
│  ☲ Yggdrasil Dashboard    Norse-themed AI agent ecosystem   │
│  Monitoring 9 realms                              2026-05-03│
├─────────┬────────────────────────────────────────────────────┤
│☵ Yggdrasil│  🏔  Asgard                                           │
│ Realms   │  Core tech (Lilith)                                   │
│          │                                                        │
│ Filter:  │  Health:  [bold green]HEALTHY[/]                                │
│ ________ │  Git:     [bold green]CLEAN[/]                                  │
│          │  Tests:   [dim]UNKNOWN[/]                                   │
│ 1. 🏔 Asgard●│  Path:    /home/user/Yggdrasil/Asgard                    │
│ 2. 🌿 Vanaheim│                                                        │
│ 3. ✨ Alfheim●│  [bold gold1]Projects (2)[/]                                       │
│ 4. 🔨 Svartalf│      [green]✓[/] Lilith-core   [dim]main[/]                               │
│ 5. 🔥 Muspelh│      [green]✓[/] provider-openai  [dim]dev[/]                            │
│ 6. ❄  Niflhei│                                                        │
│ 7. 💀 Helheim │  [bold gold1]Git Activity[/]                                          │
│ 8. 👹 Jotunhe│  abc1234  feat: add new provider                       │
│ 9. 🌍 Midgard│  def5678  fix: handle rate limit                        │
│          │                                                        │
├─────────┴────────────────────────────────────────────────────┤
│ q:Quit  r:Refresh  1-9:Realm  t:Tests  g:Git  h:Health      │
└──────────────────────────────────────────────────────────────┘
```

---

## Shell Completion

The CLI uses Typer, which provides built-in shell completion for
Bash, Zsh, Fish, and PowerShell.

### Install Completion

```bash
# Auto-install for the current shell
yggdrasil-dashboard --install-completion
```

This detects your shell and installs the appropriate completion script.
You may need to restart your shell or source the relevant file:

| Shell | File to source |
|-------|---------------|
| Bash | `~/.bash_completions/yggdrasil-dashboard.sh` |
| Zsh | `~/.zfunc/_yggdrasil-dashboard` |
| Fish | `~/.config/fish/completions/yggdrasil-dashboard.fish` |
| PowerShell | `Register-ArgumentCompleter` in your profile |

### Show Completion (manual install)

```bash
# Print the completion script for the current shell
yggdrasil-dashboard --show-completion

# For a specific shell:
yggdrasil-dashboard --show-completion bash
yggdrasil-dashboard --show-completion zsh
yggdrasil-dashboard --show-completion fish
yggdrasil-dashboard --show-completion powershell
```

Copy the output into the appropriate location for your shell.

---

## Configuration

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `YGGDRASIL_ROOT` | Auto-detected | Root directory of the Yggdrasil ecosystem |

### Auto-Detection Logic

When `YGGDRASIL_ROOT` is not set, the scanner (`tui/scanner.py`) walks up
from the package installation directory to find a parent directory named
`Yggdrasil`. This means you can usually run the dashboard without any
configuration -- the scanner will locate the realm directories automatically.

To override auto-detection:

```bash
export YGGDRASIL_ROOT=/custom/path/to/Yggdrasil
```

Or pass `base_path` when constructing `RealmScanner` programmatically:

```python
from tui.scanner import RealmScanner
scanner = RealmScanner(base_path="/custom/path/to/Yggdrasil")
```

A `.env.example` file is provided at the project root with default
configuration values -- copy it to `.env` and adjust as needed.

### Programmatic Usage

```python
from tui.scanner import RealmScanner
from tui.health import HealthMonitor
from tui.updater import DashboardUpdater

# Scan all realms
scanner = RealmScanner()
realms = scanner.scan_all()

for name, status in realms.items():
    print(f"{name}: {status.health.value} ({status.project_count} projects)")

# Get system health
monitor = HealthMonitor()
health = monitor.get_health()
print(f"CPU: {health.cpu_pct}%  RAM: {health.ram_pct}%")

# Start auto-refresh updater
updater = DashboardUpdater(interval_seconds=10)
result = updater.refresh()
print(f"Changes detected: {result.has_changes}")
```

---

## Architecture

```
terminaldashboard/
├── pyproject.toml           # Build config, deps, entry points
├── README.md                # This file
├── CHANGELOG.md             # Release history
├── .env.example             # Environment variable template
├── tui/
│   ├── __init__.py          # Package init, __version__
│   ├── cli.py               # Typer CLI (launch + shell completion)
│   ├── app.py               # Main Textual App (YggdrasilDashboard)
│   ├── scanner.py           # RealmScanner, RealmStatus, ProjectInfo
│   ├── git_utils.py         # Git activity helpers (log, status)
│   ├── health.py            # System health (CPU, RAM, GPU, disk)
│   ├── updater.py            # Auto-refresh + change detection
│   ├── actions.py           # Quick keyboard actions (tests, git, vscode…)
│   ├── styles.tcss           # Textual CSS – Dark Norse theme
│   └── widgets/
│       ├── __init__.py
│       ├── detail.py         # RealmDetailView (simple inline view)
│       ├── sidebar.py        # RealmSidebar (navigation + filter)
│       ├── health_panel.py   # SystemHealthPanel (Rich renderable)
│       └── realm_views.py    # Per-realm detailed views + Rich panels
└── tests/
    ├── conftest.py           # Shared fixtures (temp Yggdrasil tree, mocks)
    ├── test_app.py           # App composition, keybindings, navigation
    ├── test_actions.py       # QuickActions unit tests
    ├── test_git_utils.py     # GitActivity tests
    ├── test_health.py        # SystemHealth / HealthMonitor tests
    ├── test_realm_view.py    # RealmDetailView rendering tests
    ├── test_realm_view_helpers.py  # Helper function tests
    ├── test_scanner.py       # RealmScanner unit tests
    ├── test_sidebar_filter.py # Filter regex tests
    └── test_updater.py       # DashboardUpdater + ChangeRecord tests
```

### Module Overview

| Module | Responsibility |
|--------|---------------|
| `tui.cli` | Typer CLI entry point with `--version`, `--install-completion`, `--show-completion` |
| `tui.app` | Textual `YggdrasilDashboard` app class, compose, keybindings, lifecycle |
| `tui.scanner` | `RealmScanner` discovers realm dirs, `RealmStatus`/`ProjectInfo` dataclasses |
| `tui.git_utils` | `get_git_activity()` and `get_realm_git_activities()` for git introspection |
| `tui.health` | `HealthMonitor` + `SystemHealth`/`GPUInfo` dataclasses (psutil + nvidia-smi) |
| `tui.updater` | `DashboardUpdater` -- asyncio periodic refresh, change detection, flash animation |
| `tui.actions` | `QuickActions` -- keyboard-driven actions (tests, git, health, vscode, docs) |
| `tui.widgets.sidebar` | `RealmSidebar` with filter input and realm buttons |
| `tui.widgets.detail` | `RealmDetailView` showing selected realm summary |
| `tui.widgets.health_panel` | `SystemHealthPanel` Rich-based system stats panel |
| `tui.widgets.realm_views` | Full per-realm detail panels with git activity and custom sections |

---

## The Nine Realms

| # | Realm | Icon | Purview |
|---|-------|------|---------|
| 1 | **Asgard** | 🏔 | Core technology (Lilith) |
| 2 | **Vanaheim** | 🌿 | AI agents |
| 3 | **Alfheim** | ✨ | UI prototypes |
| 4 | **Svartalfheim** | 🔨 | Documentation & knowledge |
| 5 | **Muspelheim** | 🔥 | Active development / WIP |
| 6 | **Niflheim** | ❄ | Resources & assets |
| 7 | **Helheim** | 💀 | Graveyard / archived |
| 8 | **Jotunheim** | 👹 | Massive long-term projects |
| 9 | **Midgard** | 🌍 | Personal applications |

Each realm is a directory under the Yggdrasil root containing one or more
project subdirectories. The scanner auto-discovers projects by listing
non-hidden subdirectories within each realm.

---

## Development

### Setup

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
```

### Running Tests

```bash
pytest                              # All tests with coverage
pytest tests/test_scanner.py        # Single module
pytest -x                           # Stop on first failure
pytest --cov=tui --cov-report=html  # HTML coverage report
```

The test suite requires ≥70% code coverage and uses:
- `pytest-asyncio` for async Textual app tests
- `unittest.mock` for git/psutil subprocess isolation
- `pytest-textual-snapshot` for widget snapshot tests

### Code Style

- Python 3.11+ with `from __future__ import annotations`
- Dataclasses for all data models (`RealmStatus`, `SystemHealth`, etc.)
- `to_dict()` methods on all dataclasses for serialization
- Rich console markup for terminal styling (`[bold #c8a23e]☵[/]`)
- Norse-themed naming throughout (realms, rune icons, dark-fantasy palette)

---

## License

Part of the [Yggdrasil](https://github.com/user/yggdrasil) ecosystem.
See root repository for license information.

☵ **May the roots of Yggdrasil guide your code.**
