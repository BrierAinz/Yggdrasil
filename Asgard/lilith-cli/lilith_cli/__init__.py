"""Lilith CLI — lazy-loaded entry point."""

__version__ = "2.1.0"

_SUBMODULE_ATTRS = {
    "LilithClient": "lilith_cli.client",
    "Config": "lilith_core.config",
    "MemoryStore": "lilith_memory.store",
    "LilithEngine": "lilith_orchestrator.engine",
}


def __getattr__(name):
    if name in _SUBMODULE_ATTRS:
        import importlib

        module = importlib.import_module(_SUBMODULE_ATTRS[name])
        value = getattr(module, name)
        globals()[name] = value
        return value
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
