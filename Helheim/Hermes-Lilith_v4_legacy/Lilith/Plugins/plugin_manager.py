"""
Lilith Plugin Manager
=====================
Gestor central de plugins para Lilith.
Permite cargar, habilitar, deshabilitar y ejecutar plugins.
"""
import importlib
import json
import sys
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

# Path para imports
PLUGINS_DIR = Path(__file__).parent
DATA_DIR = PLUGINS_DIR.parent / "Data" / "plugins"
DATA_DIR.mkdir(parents=True, exist_ok=True)


class PluginCapability(Enum):
    """Capacidades que puede提供 un plugin"""

    TOOL = "tool"  # Añade tools al orchestrator
    MEMORY = "memory"  # Extiende la memoria
    NOTIFICATION = "notification"  # Envía notificaciones
    WEB = "web"  # Accede a web
    INTEGRATION = "integration"  # Integra con servicios externos
    PROCESSING = "processing"  # Procesa datos
    SCHEDULED = "scheduled"  # Tiene tareas programadas


class PluginState(Enum):
    """Estado del plugin"""

    UNLOADED = "unloaded"
    LOADED = "loaded"
    ENABLED = "enabled"
    DISABLED = "disabled"
    ERROR = "error"


@dataclass
class Plugin:
    """Representa un plugin de Lilith"""

    id: str
    name: str
    version: str
    description: str
    author: str
    capabilities: List[PluginCapability]
    dependencies: List[str] = field(default_factory=list)

    # Funcionalidad
    tools: List[Dict[str, Any]] = field(default_factory=list)  # Herramientas que añade
    memory_schema: Optional[Dict] = None  # Schema de memoria extendida
    notification_handler: Optional[Callable] = None

    # Estado
    state: PluginState = PluginState.UNLOADED
    config: Dict[str, Any] = field(default_factory=dict)
    installed_at: str = field(default_factory=lambda: datetime.now().isoformat())
    enabled_at: Optional[str] = None
    error_message: Optional[str] = None

    def to_dict(self) -> Dict:
        return {
            "id": self.id,
            "name": self.name,
            "version": self.version,
            "description": self.description,
            "author": self.author,
            "capabilities": [c.value for c in self.capabilities],
            "dependencies": self.dependencies,
            "state": self.state.value,
            "config": self.config,
            "installed_at": self.installed_at,
            "enabled_at": self.enabled_at,
            "error_message": self.error_message,
        }

    @classmethod
    def from_dict(cls, data: Dict) -> "Plugin":
        return cls(
            id=data["id"],
            name=data["name"],
            version=data["version"],
            description=data["description"],
            author=data["author"],
            capabilities=[PluginCapability(c) for c in data["capabilities"]],
            dependencies=data.get("dependencies", []),
            state=PluginState(data.get("state", "unloaded")),
            config=data.get("config", {}),
            installed_at=data.get("installed_at", datetime.now().isoformat()),
            enabled_at=data.get("enabled_at"),
        )


class PluginManager:
    """
    Gestor de plugins para Lilith.

    Carga plugins desde el directorio Plugins/,
    manage su estado y expone sus capacidades.
    """

    def __init__(self):
        self.plugins: Dict[str, Plugin] = {}
        self._tools_registry: Dict[str, Callable] = {}
        self._memory_extensions: Dict[str, Any] = {}
        self._notification_handlers: List[Callable] = []
        self._config_file = DATA_DIR / "plugins.json"

        self._load_plugin_registry()
        self._discover_plugins()

    def _load_plugin_registry(self):
        """Carga el registro de plugins desde archivo."""
        if self._config_file.exists():
            try:
                with open(self._config_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    for p_data in data.get("plugins", []):
                        plugin = Plugin.from_dict(p_data)
                        self.plugins[plugin.id] = plugin
            except Exception as e:
                print(f"Error cargando plugins: {e}")

    def _save_registry(self):
        """Guarda el registro de plugins."""
        with open(self._config_file, "w", encoding="utf-8") as f:
            json.dump(
                {"plugins": [p.to_dict() for p in self.plugins.values()]},
                f,
                indent=2,
                ensure_ascii=False,
            )

    def _discover_plugins(self):
        """Descubre plugins en el directorio Plugins/."""
        for item in PLUGINS_DIR.iterdir():
            if item.is_dir() and not item.name.startswith("_"):
                plugin_file = item / "plugin.py"
                if plugin_file.exists():
                    self._register_plugin_from_file(item.name, plugin_file)

    def _register_plugin_from_file(self, plugin_id: str, plugin_file: Path):
        """Registra un plugin desde archivo Python."""
        try:
            # Importar dinámicamente
            module_name = f"Lilith.Plugins.{plugin_id}.plugin"
            if module_name not in sys.modules:
                spec = importlib.util.spec_from_file_location(module_name, plugin_file)
                if spec and spec.loader:
                    module = importlib.util.module_from_spec(spec)
                    sys.modules[module_name] = module
                    spec.loader.exec_module(module)

            module = sys.modules.get(module_name)
            if module and hasattr(module, "get_plugin"):
                plugin = module.get_plugin()
                if isinstance(plugin, Plugin):
                    plugin.id = plugin_id
                    self.plugins[plugin_id] = plugin
                    self._save_registry()
                    print(f"Plugin discovered: {plugin.name} v{plugin.version}")
        except Exception as e:
            print(f"Error loading plugin {plugin_id}: {e}")

    def load_plugin(self, plugin_id: str) -> bool:
        """Carga un plugin específico."""
        plugin = self.plugins.get(plugin_id)
        if not plugin:
            return False

        try:
            plugin.state = PluginState.LOADED
            self._save_registry()
            return True
        except Exception as e:
            plugin.state = PluginState.ERROR
            plugin.error_message = str(e)
            self._save_registry()
            return False

    def enable_plugin(self, plugin_id: str) -> bool:
        """Habilita un plugin."""
        plugin = self.plugins.get(plugin_id)
        if not plugin:
            return False

        try:
            plugin.state = PluginState.ENABLED
            plugin.enabled_at = datetime.now().isoformat()

            # Registrar capabilities
            for tool in plugin.tools:
                tool_name = tool["function"]["name"]
                self._tools_registry[tool_name] = tool

            # Registrar extensiones de memoria
            if plugin.memory_schema:
                self._memory_extensions[plugin_id] = plugin.memory_schema

            # Registrar handlers de notificación
            if plugin.notification_handler:
                self._notification_handlers.append(plugin.notification_handler)

            self._save_registry()
            return True
        except Exception as e:
            plugin.state = PluginState.ERROR
            plugin.error_message = str(e)
            return False

    def disable_plugin(self, plugin_id: str) -> bool:
        """Deshabilita un plugin."""
        plugin = self.plugins.get(plugin_id)
        if not plugin:
            return False

        plugin.state = PluginState.DISABLED
        plugin.enabled_at = None

        # Desregistrar capabilities
        for tool in plugin.tools:
            tool_name = tool["function"]["name"]
            self._tools_registry.pop(tool_name, None)

        self._memory_extensions.pop(plugin_id, None)

        if plugin.notification_handler:
            self._notification_handlers = [
                h
                for h in self._notification_handlers
                if h != plugin.notification_handler
            ]

        self._save_registry()
        return True

    def get_all_tools(self) -> List[Dict[str, Any]]:
        """Obtiene todas las herramientas de plugins habilitados."""
        tools = []
        for plugin in self.plugins.values():
            if plugin.state == PluginState.ENABLED:
                tools.extend(plugin.tools)
        return tools

    def get_tool(self, tool_name: str) -> Optional[Dict[str, Any]]:
        """Obtiene una herramienta por nombre."""
        return self._tools_registry.get(tool_name)

    def list_plugins(self, state: Optional[PluginState] = None) -> List[Plugin]:
        """Lista plugins, opcionalmente filtrados por estado."""
        plugins = list(self.plugins.values())
        if state:
            plugins = [p for p in plugins if p.state == state]
        return plugins

    def get_memory_extensions(self) -> Dict[str, Any]:
        """Obtiene todas las extensiones de memoria."""
        return self._memory_extensions.copy()

    def send_notification(self, message: str, level: str = "info"):
        """Envía notificación a través de todos los handlers."""
        for handler in self._notification_handlers:
            try:
                handler(message, level)
            except Exception as e:
                print(f"Notification handler error: {e}")

    def update_config(self, plugin_id: str, config: Dict[str, Any]) -> bool:
        """Actualiza la configuración de un plugin."""
        plugin = self.plugins.get(plugin_id)
        if not plugin:
            return False

        plugin.config.update(config)
        self._save_registry()
        return True


# Plugin base para heredar
class BasePlugin(Plugin):
    """Clase base para crear plugins."""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._initialized = False

    def initialize(self) -> bool:
        """Inicialización del plugin. Override en subclases."""
        self._initialized = True
        return True

    def shutdown(self):
        """Limpieza al deshabilitar. Override en subclases."""
        pass


# Instancia global
_plugin_manager: Optional[PluginManager] = None


def get_plugin_registry() -> PluginManager:
    """Obtiene la instancia global del gestor de plugins."""
    global _plugin_manager
    if _plugin_manager is None:
        _plugin_manager = PluginManager()
    return _plugin_manager
