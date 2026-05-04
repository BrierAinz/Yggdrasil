# lilith-tools

> *Dvergr forge — each tool shaped for a god's hand.*

Tool system providing the registry, base classes, and built-in tools (browser, web search, coding, filesystem, system) that the Lilith agent can wield.

## Installation

```bash
pip install -e .
```

## Usage

```python
from lilith_tools import BaseTool, ToolRegistry, ToolResult

registry = ToolRegistry()
registry.register(MyCustomTool())  # extend the forge with your own implement
```

## Architecture

This package is part of the **Asgard** realm in the Yggdrasil ecosystem.

- Part of the Lilith AI agent v2 modular architecture
- Depends on: `lilith-core>=2.0.0`
- Built-in tools: browser, web_search, coding, filesystem, system

## License

MIT
