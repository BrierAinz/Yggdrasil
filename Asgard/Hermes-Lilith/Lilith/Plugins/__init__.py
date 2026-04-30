"""
Lilith Plugin System
====================
Sistema de plugins extensible para agregar capacidades.
"""
from .plugin_manager import Plugin, PluginCapability, PluginManager
from .registry import get_plugin_registry

__all__ = ["PluginManager", "Plugin", "PluginCapability", "get_plugin_registry"]
