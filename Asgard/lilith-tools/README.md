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

# Registry pattern — tools auto-register on import
from lilith_tools import BrowserTool, CodingTool, WebSearchTool
# BrowserTool, CodingTool, WebSearchTool are registered automatically

registry = ToolRegistry()
print(registry.list_tools())  # shows all registered tools

# Custom tool
class MyTool(BaseTool):
    name = "my_tool"
    description = "A custom tool"

    async def execute(self, **kwargs) -> ToolResult:
        return ToolResult(output="done")

registry.register(MyTool())  # extend the forge with your own implement
```

### Built-in Tools

| Tool | Description |
|------|-------------|
| `WebSearchTool` | Web search via SearXNG |
| `BrowserTool` | Headless browser navigation and extraction |
| `CodingTool` | Code generation, analysis, and refactoring |
| `filesystem` | File read, write, and search operations |
| `system` | System information and resource monitoring |

## Architecture

This package is part of the **Asgard** realm in the Yggdrasil ecosystem.

- Part of the Lilith AI agent v2 modular architecture
- Depends on: `lilith-core>=2.0.0`
- Built-in tools: browser, web_search, coding, filesystem, system
- Tools auto-register when their modules are imported

## Exports

| Symbol | Description |
|--------|-------------|
| `BaseTool` | Abstract base class for all tools |
| `ToolResult` | Structured result from tool execution |
| `ToolRegistry` | Global tool registry with discover/list/register |
| `WebSearchTool` | SearXNG-based web search |
| `BrowserTool` | Headless browser automation |
| `CodingTool` | Code generation and analysis |
| `filesystem` | File operations module |
| `system` | System monitoring module |

## License

MIT
