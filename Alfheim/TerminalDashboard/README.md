# TerminalDashboard

Yggdrasil Terminal Dashboard – a TUI (Textual/Rich) that shows status of all
Yggdrasil realms, projects, health checks, and allows navigating the ecosystem
from one screen.

## Quick Start

```bash
# Install (editable with dev extras)
pip install -e ".[dev]"

# Run the dashboard
tui
# or
python -m tui
```

## Keybindings

| Key | Action |
|-----|--------|
| `q` | Quit |
| `r` | Refresh |
| `1-9` | Switch realm |
| `t` | Run tests for current realm |
| `g` | Git status / commit |
| `h` | Health check |
| `o` | Open in VS Code |
| `d` | Open docs in browser |

## Architecture

- **tui/app.py** – Main Textual App class
- **tui/scanner.py** – RealmScanner, RealmStatus, ProjectInfo
- **tui/updater.py** – Auto-refresh and change detection
- **tui/actions.py** – Quick keyboard actions
- **tui/health.py** – System health (CPU, RAM, GPU, disk)
- **tui/widgets/** – UI components (header, sidebar, realm views, footer)
