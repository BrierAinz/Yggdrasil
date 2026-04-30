"""
Lilith 4.1 — Plugin de ejemplo: get_weather.
Demuestra cómo crear un plugin que registra una tool.

Para activar: POST /api/plugins/load {"name": "example_weather_plugin"}
"""
import logging
from typing import Any, Dict

from src.core.plugin_manager import BasePlugin, PluginManager

logger = logging.getLogger("lilith.plugin.weather")


def _get_weather(params: Dict[str, Any]) -> Dict[str, Any]:
    """
    Tool: get_weather
    Obtiene el clima actual de una ubicación usando wttr.in (no requiere API key).
    Params: location (str)
    """
    location = (params.get("location") or "Madrid").strip()
    try:
        import urllib.request

        url = f"https://wttr.in/{urllib.parse.quote(location)}?format=3"
        import urllib.parse

        url = f"https://wttr.in/{urllib.parse.quote(location)}?format=3"
        with urllib.request.urlopen(url, timeout=10) as r:
            text = r.read().decode("utf-8").strip()
        return {"response": text, "location": location}
    except Exception as e:
        return {
            "response": f"No se pudo obtener el clima de '{location}': {e}",
            "error": True,
        }


class Plugin(BasePlugin):
    name = "example_weather_plugin"
    version = "1.0.0"
    description = "Plugin de ejemplo: registra la tool get_weather usando wttr.in"

    def on_load(self, manager: PluginManager) -> None:
        schema = {
            "type": "object",
            "properties": {
                "location": {
                    "type": "string",
                    "description": "Ciudad o ubicación (ej. 'Madrid', 'Buenos Aires')",
                }
            },
            "required": ["location"],
        }
        manager.register_tool(
            plugin_name=self.name,
            tool_name="get_weather",
            tool_func=_get_weather,
            schema=schema,
        )
        logger.info("[WeatherPlugin] Tool get_weather registrada.")

    def on_unload(self) -> None:
        logger.info("[WeatherPlugin] Descargada.")
