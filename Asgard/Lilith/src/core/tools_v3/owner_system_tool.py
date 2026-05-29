"""
Lilith — Tool solo owner: acciones de sistema (apagar, reiniciar, bloquear PC).
Whitelist en Config/security.json → owner_system_actions. Sin shell=True.
"""
import logging
import platform
import subprocess
from pathlib import Path
from typing import Any, Dict, List

from .protocol import LilithTool, ToolResult

logger = logging.getLogger("owner_system_tool")

# Acciones permitidas por defecto si no hay config
_DEFAULT_ACTIONS = ["shutdown", "restart", "lock"]


def _load_allowed_actions(base_path: Path) -> List[str]:
    """Lee owner_system_actions de Config/security.json."""
    try:
        p = Path(base_path) / "Config" / "security.json"
        if not p.exists():
            return _DEFAULT_ACTIONS
        import json

        data = json.loads(p.read_text(encoding="utf-8"))
        if isinstance(data, dict) and "owner_system_actions" in data:
            actions = data["owner_system_actions"]
            if isinstance(actions, list):
                return [str(a).strip().lower() for a in actions if a]
    except Exception:
        pass
    return _DEFAULT_ACTIONS


class OwnerSystemTool(LilithTool):
    """Ejecuta una acción de sistema permitida (apagar, reiniciar, bloquear). Solo owner."""

    def __init__(self, project_root: Path) -> None:
        self._root = Path(project_root)

    @property
    def name(self) -> str:
        return "owner_system_action"

    def get_description(self) -> str:
        return "Acciones de sistema (solo owner): apagar PC, reiniciar, bloquear. Requiere confirmación."

    def get_parameters_schema(self) -> Dict[str, Any]:
        return {
            "action": "shutdown | restart | lock",
            "delay_seconds": "opcional, para shutdown/restart (default 60)",
        }

    def execute(self, params: Dict[str, Any]) -> ToolResult:
        action = (params.get("action") or "").strip().lower()
        if not action:
            return {
                "response": "Indica la acción: shutdown, restart o lock.",
                "error": True,
            }
        allowed = _load_allowed_actions(self._root)
        if action not in allowed:
            return {
                "response": f"Acción «{action}» no está en la whitelist (Config/security.json → owner_system_actions).",
                "error": True,
            }
        delay = int(params.get("delay_seconds") or 60)
        delay = max(10, min(600, delay))

        system = platform.system().lower()
        try:
            if action == "shutdown":
                if system == "windows":
                    subprocess.run(
                        ["shutdown", "/s", "/t", str(delay)], check=True, timeout=5
                    )
                else:
                    subprocess.run(
                        ["shutdown", "-h", f"+{delay // 60}"], check=True, timeout=5
                    )
                return {
                    "response": f"PC programada para apagarse en {delay} segundos. Cancela con «shutdown /a» (Windows) o «shutdown -c» (Linux)."
                }
            if action == "restart":
                if system == "windows":
                    subprocess.run(
                        ["shutdown", "/r", "/t", str(delay)], check=True, timeout=5
                    )
                else:
                    subprocess.run(
                        ["shutdown", "-r", f"+{delay // 60}"], check=True, timeout=5
                    )
                return {
                    "response": f"PC programada para reiniciar en {delay} segundos."
                }
            if action == "lock":
                if system == "windows":
                    subprocess.run(
                        ["rundll32", "user32.dll,LockWorkStation"],
                        check=True,
                        timeout=5,
                    )
                else:
                    # Linux: xdg-screensaver lock o similar; puede no estar
                    subprocess.run(["xdg-screensaver", "lock"], check=True, timeout=5)
                return {"response": "Pantalla bloqueada."}
        except FileNotFoundError as e:
            logger.warning("owner_system_action %s: %s", action, e)
            return {
                "response": f"No se encontró el comando para «{action}» en este sistema.",
                "error": True,
            }
        except subprocess.CalledProcessError as e:
            return {"response": f"Error al ejecutar «{action}»: {e}.", "error": True}
        except Exception as e:
            logger.exception("owner_system_action %s", action)
            return {"response": str(e), "error": True}
        return {"response": "Acción no implementada.", "error": True}
