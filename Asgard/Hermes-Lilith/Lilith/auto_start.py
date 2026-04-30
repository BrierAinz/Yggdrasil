"""
Lilith Auto-Start - Configuración de auto-arranque
=================================================
Configura Lilith para iniciar con Windows.
"""
import os
import sys
from pathlib import Path
from typing import Optional

# Solo funciona en Windows
if sys.platform == "win32":
    import winreg


class AutoStartManager:
    """
    Gestor de auto-arranque para Lilith.

    Permite:
    - Agregar/eliminar del startup de Windows
    - Ejecutar como servicio
    - Minimizar a bandeja del sistema
    """

    APP_NAME = "Lilith"
    REG_KEY = r"Software\Microsoft\Windows\CurrentVersion\Run"

    def __init__(self):
        self.script_path = self._get_main_script_path()

    def _get_main_script_path(self) -> str:
        """Obtiene la ruta del script principal."""
        # Buscar launch_lilith.ps1
        current = Path(__file__).parent
        ps1_path = current / "launch_lilith.ps1"

        if ps1_path.exists():
            return str(ps1_path.absolute())

        # Caerback a main.py
        main_path = current / "main.py"
        return f'python "{main_path.absolute()}"'

    def is_enabled(self) -> bool:
        """Verifica si auto-arranque está habilitado."""
        if sys.platform != "win32":
            return False

        try:
            key = winreg.OpenKey(
                winreg.HKEY_CURRENT_USER, self.REG_KEY, 0, winreg.KEY_READ
            )
            try:
                value, _ = winreg.QueryValueEx(key, self.APP_NAME)
                return True
            except FileNotFoundError:
                return False
            finally:
                winreg.CloseKey(key)
        except Exception:
            return False

    def enable(self) -> bool:
        """Habilita auto-arranque."""
        if sys.platform != "win32":
            return False

        try:
            key = winreg.OpenKey(
                winreg.HKEY_CURRENT_USER, self.REG_KEY, 0, winreg.KEY_WRITE
            )
            winreg.SetValueEx(key, self.APP_NAME, 0, winreg.REG_SZ, self.script_path)
            winreg.CloseKey(key)
            return True
        except Exception as e:
            print(f"Error enabling auto-start: {e}")
            return False

    def disable(self) -> bool:
        """Deshabilita auto-arranque."""
        if sys.platform != "win32":
            return False

        try:
            key = winreg.OpenKey(
                winreg.HKEY_CURRENT_USER, self.REG_KEY, 0, winreg.KEY_WRITE
            )
            try:
                winreg.DeleteValue(key, self.APP_NAME)
            except FileNotFoundError:
                pass
            winreg.CloseKey(key)
            return True
        except Exception as e:
            print(f"Error disabling auto-start: {e}")
            return False

    def get_status(self) -> dict:
        """Obtiene estado de auto-arranque."""
        return {
            "enabled": self.is_enabled(),
            "app_name": self.APP_NAME,
            "script_path": self.script_path,
            "platform": sys.platform,
        }


# Instancia global
_auto_start_manager: Optional[AutoStartManager] = None


def get_auto_start() -> AutoStartManager:
    """Obtiene la instancia global del gestor de auto-arranque."""
    global _auto_start_manager
    if _auto_start_manager is None:
        _auto_start_manager = AutoStartManager()
    return _auto_start_manager
