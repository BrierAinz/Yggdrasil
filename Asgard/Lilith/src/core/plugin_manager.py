"""
Lilith 4.1 — E.13 Plugin Manager.
Carga, recarga y descarga plugins hot-reload para tools, personas y transportes.
Seguridad: checksum SHA256, imports bloqueados, timeout heredado.
"""
import hashlib
import importlib.util
import logging
import sys
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Type

logger = logging.getLogger("lilith.plugins")

# Imports que los plugins NO pueden usar
_DISALLOWED_IMPORTS = frozenset(
    [
        "os.system",
        "subprocess",
        "pty",
        "commands",
        "popen",
        "ctypes",
        "winreg",
        "msvcrt",
    ]
)


# ── Interfaz base ─────────────────────────────────────────────────────────────


class BasePlugin(ABC):
    """Clase base para todos los plugins de Lilith."""

    #: Nombre único del plugin (snake_case)
    name: str = ""
    #: Versión semántica
    version: str = "0.1.0"
    #: Descripción breve
    description: str = ""

    @abstractmethod
    def on_load(self, manager: "PluginManager") -> None:
        """Llamado al cargar el plugin. Registrar tools/personas aquí."""
        pass

    @abstractmethod
    def on_unload(self) -> None:
        """Llamado al descargar el plugin. Limpiar recursos."""
        pass


# ── Plugin Manager ─────────────────────────────────────────────────────────────


class PluginManager:
    """
    E.13 — Gestor de plugins con hot-reload.
    Permite registrar tools, personas y transportes sin reiniciar Lilith.
    """

    def __init__(self, base_path: Path):
        self.base_path = Path(base_path)
        self._plugins: Dict[str, BasePlugin] = {}  # name → instancia
        self._plugin_modules: Dict[str, Any] = {}  # name → módulo
        self._registered_tools: Dict[str, List[str]] = {}  # plugin → [tool_names]
        self._registered_personas: Dict[str, List[str]] = {}
        self._plugin_dir = self.base_path / "Backend" / "plugins"
        self._cfg_path = self.base_path / "Config" / "plugins.json"

    def _load_config(self) -> Dict[str, Any]:
        try:
            from src.core.json_safe import safe_load

            cfg = safe_load(self._cfg_path, default={})
            return cfg if isinstance(cfg, dict) else {}
        except Exception:
            return {}

    def _save_config(self, cfg: Dict[str, Any]) -> None:
        import json

        try:
            with open(self._cfg_path, "w", encoding="utf-8") as f:
                json.dump(cfg, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.warning("[PluginManager] No se pudo guardar plugins.json: %s", e)

    # ── Seguridad ─────────────────────────────────────────────────────────────

    def _compute_checksum(self, path: Path) -> str:
        try:
            return hashlib.sha256(path.read_bytes()).hexdigest()
        except Exception:
            return ""

    def _validate_security(self, path: Path) -> tuple:
        """
        Verifica que el plugin no use imports prohibidos.
        Devuelve (ok: bool, reason: str).
        """
        try:
            import ast

            source = path.read_text(encoding="utf-8", errors="replace")
            tree = ast.parse(source, filename=str(path))
            for node in ast.walk(tree):
                # import os.system / from os import system
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        if alias.name in _DISALLOWED_IMPORTS:
                            return False, f"Import prohibido: {alias.name}"
                elif isinstance(node, ast.ImportFrom):
                    mod = node.module or ""
                    for alias in node.names:
                        full = f"{mod}.{alias.name}" if mod else alias.name
                        if full in _DISALLOWED_IMPORTS or mod in _DISALLOWED_IMPORTS:
                            return False, f"Import prohibido: {full}"
        except SyntaxError as e:
            return False, f"Syntax error en plugin: {e}"
        except Exception as e:
            return False, f"Error de validación: {e}"
        return True, ""

    def _verify_checksum(self, plugin_name: str, path: Path) -> bool:
        """Verifica checksum SHA256 contra plugins.json si verify_checksum=True."""
        cfg = self._load_config()
        security = cfg.get("security", {})
        if not security.get("verify_checksum", False):
            return True
        plugins_cfg = cfg.get("plugins", {})
        registered = plugins_cfg.get(plugin_name, {})
        stored = registered.get("checksum", "")
        if not stored:
            return True  # Sin checksum registrado: permitir (primer load)
        current = self._compute_checksum(path)
        if current != stored:
            logger.error(
                "[PluginManager] Checksum mismatch para '%s': esperado %s, actual %s",
                plugin_name,
                stored[:12],
                current[:12],
            )
            return False
        return True

    # ── Carga dinámica ────────────────────────────────────────────────────────

    def load_plugin(self, plugin_name: str, path: Optional[Path] = None) -> tuple:
        """
        Carga un plugin por nombre. Busca en plugin_dir si no se da path.
        Devuelve (ok: bool, message: str).
        """
        if plugin_name in self._plugins:
            return (
                False,
                f"Plugin '{plugin_name}' ya está cargado. Usa reload_plugin().",
            )

        if path is None:
            path = self._plugin_dir / f"{plugin_name}.py"
        path = Path(path)

        if not path.exists():
            return False, f"Plugin no encontrado: {path}"

        # Validación de seguridad
        ok, reason = self._validate_security(path)
        if not ok:
            logger.error(
                "[PluginManager] Security violation en '%s': %s", plugin_name, reason
            )
            return False, f"[PluginManager] Security violation: {reason}"

        # Verificar checksum
        if not self._verify_checksum(plugin_name, path):
            return False, f"Checksum mismatch para '{plugin_name}'"

        # Cargar módulo (forzar recarga limpia ignorando cache)
        try:
            mod_key = f"lilith_plugin_{plugin_name}"
            sys.modules.pop(mod_key, None)  # Limpiar cache ANTES de crear spec
            importlib.invalidate_caches()  # Invalidar cache de filesystem de importlib
            spec = importlib.util.spec_from_file_location(mod_key, path)
            if spec is None or spec.loader is None:
                return False, f"No se pudo crear spec para {path}"
            module = importlib.util.module_from_spec(spec)
            sys.modules[mod_key] = module
            spec.loader.exec_module(module)
        except Exception as e:
            logger.error(
                "[PluginManager] Error cargando módulo '%s': %s", plugin_name, e
            )
            return False, f"Error cargando módulo: {e}"

        # Instanciar clase BasePlugin
        plugin_cls = getattr(module, "Plugin", None)
        if plugin_cls is None:
            # Buscar cualquier subclase de BasePlugin
            for attr in vars(module).values():
                if (
                    isinstance(attr, type)
                    and issubclass(attr, BasePlugin)
                    and attr is not BasePlugin
                ):
                    plugin_cls = attr
                    break
        if plugin_cls is None:
            return (
                False,
                f"Plugin '{plugin_name}' no define clase 'Plugin' (subclase de BasePlugin)",
            )

        try:
            instance = plugin_cls()
            instance.on_load(self)
        except Exception as e:
            logger.error("[PluginManager] Error en on_load de '%s': %s", plugin_name, e)
            return False, f"Error en on_load: {e}"

        self._plugins[plugin_name] = instance
        self._plugin_modules[plugin_name] = module
        self._registered_tools.setdefault(plugin_name, [])
        self._registered_personas.setdefault(plugin_name, [])

        # Actualizar checksum en plugins.json
        checksum = self._compute_checksum(path)
        cfg = self._load_config()
        cfg.setdefault("plugins", {})[plugin_name] = {
            "path": str(path),
            "enabled": True,
            "checksum": checksum,
            "version": getattr(instance, "version", "0.1.0"),
            "description": getattr(instance, "description", ""),
        }
        self._save_config(cfg)

        logger.info("[PluginManager] Plugin '%s' cargado exitosamente.", plugin_name)
        return True, f"Plugin '{plugin_name}' cargado."

    def reload_plugin(self, plugin_name: str) -> tuple:
        """Hot-reload: descarga y vuelve a cargar el plugin."""
        if plugin_name not in self._plugins:
            return self.load_plugin(plugin_name)

        cfg = self._load_config()
        path_str = cfg.get("plugins", {}).get(plugin_name, {}).get("path", "")
        path = Path(path_str) if path_str else self._plugin_dir / f"{plugin_name}.py"

        self.unload_plugin(plugin_name)
        ok, msg = self.load_plugin(plugin_name, path)
        if ok:
            logger.info(
                "[PluginManager] Reloaded plugin '%s' successfully.", plugin_name
            )
        return ok, msg

    def unload_plugin(self, plugin_name: str) -> tuple:
        """Descarga un plugin y limpia sus registros."""
        if plugin_name not in self._plugins:
            return False, f"Plugin '{plugin_name}' no está cargado."

        instance = self._plugins[plugin_name]
        try:
            instance.on_unload()
        except Exception as e:
            logger.warning(
                "[PluginManager] Error en on_unload de '%s': %s", plugin_name, e
            )

        # Limpiar tools registradas
        for tool_name in self._registered_tools.get(plugin_name, []):
            self._unregister_tool(tool_name)

        # Limpiar módulo de sys.modules
        mod_key = f"lilith_plugin_{plugin_name}"
        sys.modules.pop(mod_key, None)

        del self._plugins[plugin_name]
        del self._plugin_modules[plugin_name]
        self._registered_tools.pop(plugin_name, None)
        self._registered_personas.pop(plugin_name, None)

        logger.info("[PluginManager] Plugin '%s' descargado.", plugin_name)
        return True, f"Plugin '{plugin_name}' descargado."

    # ── Registro de tools ─────────────────────────────────────────────────────

    def register_tool(
        self,
        plugin_name: str,
        tool_name: str,
        tool_func: Callable,
        schema: Dict[str, Any],
    ) -> None:
        """Registra una tool en ToolRegistryV3."""
        try:
            from src.core.tools.registry import get_registry

            registry = get_registry()
            registry.register(tool_name, tool_func, schema)
            self._registered_tools.setdefault(plugin_name, []).append(tool_name)
            logger.info(
                "[PluginManager] Tool '%s' registrada por plugin '%s'.",
                tool_name,
                plugin_name,
            )
        except Exception as e:
            logger.warning(
                "[PluginManager] Error registrando tool '%s': %s", tool_name, e
            )

    def _unregister_tool(self, tool_name: str) -> None:
        try:
            from src.core.tools.registry import get_registry

            registry = get_registry()
            if hasattr(registry, "unregister"):
                registry.unregister(tool_name)
        except Exception:
            pass

    def register_persona(
        self, plugin_name: str, persona_config: Dict[str, Any]
    ) -> None:
        """Añade una persona al Panteón en tiempo de ejecución."""
        persona_name = persona_config.get("name", "")
        if not persona_name:
            logger.warning("[PluginManager] Persona sin nombre, ignorada.")
            return
        try:
            import json

            personas_path = self.base_path / "Config" / "personas.json"
            personas = {}
            if personas_path.exists():
                from src.core.json_safe import safe_load

                personas = safe_load(personas_path, default={})
                if not isinstance(personas, dict):
                    personas = {}
            personas[persona_name] = persona_config
            with open(personas_path, "w", encoding="utf-8") as f:
                json.dump(personas, f, ensure_ascii=False, indent=2)
            self._registered_personas.setdefault(plugin_name, []).append(persona_name)
            logger.info(
                "[PluginManager] Persona '%s' registrada por plugin '%s'.",
                persona_name,
                plugin_name,
            )
        except Exception as e:
            logger.warning(
                "[PluginManager] Error registrando persona '%s': %s", persona_name, e
            )

    def register_transport(self, plugin_name: str, transport_class: Type) -> None:
        """Registra un nuevo transporte (WhatsApp, Slack, etc.)."""
        transport_name = getattr(
            transport_class, "transport_name", transport_class.__name__
        )
        logger.info(
            "[PluginManager] Transporte '%s' registrado por plugin '%s'.",
            transport_name,
            plugin_name,
        )
        # Los transportes se instancian externamente; solo logueamos el registro.
        # El plugin es responsable de iniciar el transporte en on_load().

    # ── Estado ────────────────────────────────────────────────────────────────

    def list_plugins(self) -> List[Dict[str, Any]]:
        """Lista todos los plugins activos con metadata."""
        result = []
        for name, instance in self._plugins.items():
            result.append(
                {
                    "name": name,
                    "version": getattr(instance, "version", "?"),
                    "description": getattr(instance, "description", ""),
                    "status": "active",
                    "tools": self._registered_tools.get(name, []),
                    "personas": self._registered_personas.get(name, []),
                }
            )
        return result

    def get_plugin(self, plugin_name: str) -> Optional[BasePlugin]:
        return self._plugins.get(plugin_name)

    def is_loaded(self, plugin_name: str) -> bool:
        return plugin_name in self._plugins

    # ── Auto-load al arranque ──────────────────────────────────────────────────

    def auto_load(self) -> None:
        """Carga los plugins definidos en plugins.json → auto_load."""
        cfg = self._load_config()
        if not cfg.get("enabled", True):
            return
        auto = cfg.get("auto_load", [])
        for plugin_name in auto or []:
            ok, msg = self.load_plugin(plugin_name)
            if not ok:
                logger.warning(
                    "[PluginManager] Auto-load '%s' falló: %s", plugin_name, msg
                )


# ── Singleton ──────────────────────────────────────────────────────────────────

_manager_instance: Optional[PluginManager] = None


def get_plugin_manager(base_path: Optional[Path] = None) -> PluginManager:
    global _manager_instance
    if _manager_instance is None:
        if base_path is None:
            base_path = Path(__file__).resolve().parent.parent.parent
        _manager_instance = PluginManager(base_path)
    return _manager_instance
