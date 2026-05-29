---
sidebar_position: 4
title: lilith-tools
---

# lilith-tools

Tool registry and execution framework. Register tools with decorators, execute them safely.

## Quick Start

```python
from lilith_tools.registry import ToolRegistry

# Register a tool
@ToolRegistry.tool(description="Get system information")
def system_info():
    import platform
    return {"os": platform.system(), "arch": platform.machine()}

# List registered tools
tools = ToolRegistry.list_tools()
# {"system_info": "Get system information"}

# Execute a tool
result = ToolRegistry.execute("system_info", {})
# {"os": "Linux", "arch": "x86_64"}
```

## Built-in Tools

### Filesystem Tools

```python
from lilith_tools.filesystem import read_file, write_file, list_directory
```

### Browser Tools

```python
from lilith_tools.browser import navigate, screenshot, click_element
```

### Coding Tools

```python
from lilith_tools.coding import execute_code, run_tests, lint_code
```

## Tool Registry

The `ToolRegistry` is a singleton that manages all available tools:

```python
from lilith_tools.registry import ToolRegistry

# List all tools
for name, desc in ToolRegistry.list_tools().items():
    print(f"{name}: {desc}")

# Execute with parameters
result = ToolRegistry.execute("tool_name", {"param": "value"})
```
