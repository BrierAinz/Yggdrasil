# Yggdrasil Python Pitfalls

## Mutable Class Variable Bug (Fixed May 2026)

**File**: `Asgard/lilith-tools/lilith_tools/registry.py`

**Bug**: `_tools: dict[str, type[BaseTool]] = {}` — mutable class variable shared across all `ToolRegistry` instances. If multiple registries were created, they would share the same `_tools` dict, causing cross-contamination of tool registrations.

**Fix**: Changed to `_tools: dict[str, type[BaseTool]] | None = None` with lazy initialization via `_get_tools()` classmethod:
```python
class ToolRegistry:
    _tools: dict[str, type[BaseTool]] | None = None

    @classmethod
    def _get_tools(cls) -> dict[str, type[BaseTool]]:
        if cls._tools is None:
            cls._tools = {}
        return cls._tools
```

All references to `cls._tools` updated to `cls._get_tools()`.

**Lesson**: In Python, never use `{}`, `[]`, or `set()` as class-level defaults. Use `None` with lazy initialization instead, or define `__init__` with instance-level defaults.

## CORS Production Origins (Fixed May 2026)

**File**: `Asgard/lilith-orchestrator/gateway/gateway.py`

**Bug**: CORS `allow_origins` only had localhost entries. No production domains were listed, so API calls from `brierstudios.com` or `docs.brierstudios.com` would be blocked by the browser.

**Fix**: Added production origins:
```python
allow_origins=[
    "http://localhost:3000",
    "http://localhost:8000",
    "http://127.0.0.1:3000",
    "http://127.0.0.1:8000",
    "https://brierstudios.com",
    "https://docs.brierstudios.com",
    "https://brierstudios.pages.dev",
    "https://docs-brierstudios.pages.dev",
],
```

Also removed the TODO comment about moving origins to env vars since this is now implemented.