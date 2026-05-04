# lilith-cli

> *Valkyrie's console — command the nine realms from a single terminal.*

Command-line interface and interactive TUI dashboard for Yggdrasil, built with Textual for rich terminal interaction with the Lilith agent.

## Installation

```bash
pip install -e .
```

## Usage

```bash
# Launch the agent CLI
lilith

# Or start the full TUI dashboard
yggdrasil-tui
```

```python
from lilith_cli import LilithClient

client = LilithClient()
response = client.ask("Summon wisdom from the well of Mimir")
```

## Architecture

This package is part of the **Asgard** realm in the Yggdrasil ecosystem.

- Part of the Lilith AI agent v2 modular architecture
- Depends on: `lilith-core>=2.0.0`, `lilith-memory>=2.0.0`, `lilith-orchestrator>=2.0.0`, `lilith-tools>=2.0.0`, `textual>=0.50.0`

## License

MIT
