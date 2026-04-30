"""
PCMacros — Macros predefinidas para operaciones comunes de PC Agent.
Shortcuts de alto nivel que descomponen en operaciones individuales.
"""
import logging
import os
import re
from typing import Any, Dict, List, Optional

from src.core.planner import Step


def _expand_path_params(params: Dict[str, Any]) -> Dict[str, Any]:
    """Expande variables de entorno en parámetros de ruta."""
    expanded = {}
    for key, value in params.items():
        if isinstance(value, str):
            expanded[key] = os.path.expandvars(value)
        else:
            expanded[key] = value
    return expanded


logger = logging.getLogger("lilith.pc_macros")


# Definición de macros
PC_MACROS = {
    "limpiar_downloads": {
        "description": "Elimina archivos temporales de Downloads (.tmp, .log, .crdownload, .part)",
        "triggers": [
            "limpia downloads",
            "limpia descargas",
            "borra basura de downloads",
            "limpiar downloads",
            "limpiar descargas",
            "clean downloads",
        ],
        "steps": [
            {
                "tool": "pc_delete",
                "params": {"path": r"%USERPROFILE%\Downloads\*.tmp"},
                "desc": "Eliminar .tmp",
            },
            {
                "tool": "pc_delete",
                "params": {"path": r"%USERPROFILE%\Downloads\*.log"},
                "desc": "Eliminar .log",
            },
            {
                "tool": "pc_delete",
                "params": {"path": r"%USERPROFILE%\Downloads\*.crdownload"},
                "desc": "Eliminar descargas incompletas",
            },
            {
                "tool": "pc_delete",
                "params": {"path": r"%USERPROFILE%\Downloads\*.part"},
                "desc": "Eliminar .part",
            },
        ],
        "risk": "high",
    },
    "organizar_downloads": {
        "description": "Mueve PDFs, imágenes, videos y ZIPs a subcarpetas organizadas",
        "triggers": [
            "organiza downloads",
            "ordena descargas",
            "organizar downloads",
            "organiza la carpeta downloads",
            "organizar descargas",
        ],
        "steps": [
            {
                "tool": "pc_mkdir",
                "params": {"path": r"%USERPROFILE%\Downloads\PDFs"},
                "desc": "Crear carpeta PDFs",
            },
            {
                "tool": "pc_mkdir",
                "params": {"path": r"%USERPROFILE%\Downloads\Imagenes"},
                "desc": "Crear carpeta Imagenes",
            },
            {
                "tool": "pc_mkdir",
                "params": {"path": r"%USERPROFILE%\Downloads\Videos"},
                "desc": "Crear carpeta Videos",
            },
            {
                "tool": "pc_mkdir",
                "params": {"path": r"%USERPROFILE%\Downloads\Comprimidos"},
                "desc": "Crear carpeta Comprimidos",
            },
            {
                "tool": "pc_move",
                "params": {
                    "source": r"%USERPROFILE%\Downloads\*.pdf",
                    "destination": r"%USERPROFILE%\Downloads\PDFs",
                },
                "desc": "Mover PDFs",
            },
            {
                "tool": "pc_move",
                "params": {
                    "source": r"%USERPROFILE%\Downloads\*.jpg",
                    "destination": r"%USERPROFILE%\Downloads\Imagenes",
                },
                "desc": "Mover JPGs",
            },
            {
                "tool": "pc_move",
                "params": {
                    "source": r"%USERPROFILE%\Downloads\*.png",
                    "destination": r"%USERPROFILE%\Downloads\Imagenes",
                },
                "desc": "Mover PNGs",
            },
            {
                "tool": "pc_move",
                "params": {
                    "source": r"%USERPROFILE%\Downloads\*.mp4",
                    "destination": r"%USERPROFILE%\Downloads\Videos",
                },
                "desc": "Mover MP4s",
            },
            {
                "tool": "pc_move",
                "params": {
                    "source": r"%USERPROFILE%\Downloads\*.zip",
                    "destination": r"%USERPROFILE%\Downloads\Comprimidos",
                },
                "desc": "Mover ZIPs",
            },
            {
                "tool": "pc_move",
                "params": {
                    "source": r"%USERPROFILE%\Downloads\*.rar",
                    "destination": r"%USERPROFILE%\Downloads\Comprimidos",
                },
                "desc": "Mover RARs",
            },
        ],
        "risk": "medium",
    },
    "backup_lilith": {
        "description": "Realiza backup de Config y Data de Lilith con fecha",
        "triggers": [
            "backup de lilith",
            "respalda lilith",
            "haz backup",
            "backup lilith",
            "respaldo lilith",
        ],
        "steps": [
            {
                "tool": "pc_exec",
                "params": {
                    "command": "powershell",
                    "args": [
                        "-Command",
                        'New-Item -ItemType Directory -Force -Path "D:\\Backups\\Lilith\\Config_$(Get-Date -Format yyyyMMdd_HHmm)"',
                    ],
                },
                "desc": "Crear carpeta de backup Config",
            },
            {
                "tool": "pc_exec",
                "params": {
                    "command": "robocopy",
                    "args": [
                        r"D:\Proyectos\Yggdrasil\Asgard\Lilith\Core\Config",
                        r"D:\Backups\Lilith\Config_%DATE%",
                        "/MIR",
                        "/R:3",
                        "/W:5",
                    ],
                },
                "desc": "Copiar Config",
            },
            {
                "tool": "pc_exec",
                "params": {
                    "command": "robocopy",
                    "args": [
                        r"D:\Proyectos\Yggdrasil\Asgard\Lilith\Core\Data",
                        r"D:\Backups\Lilith\Data_%DATE%",
                        "/MIR",
                        "/R:3",
                        "/W:5",
                    ],
                },
                "desc": "Copiar Data",
            },
        ],
        "risk": "medium",
    },
    "status_sistema": {
        "description": "Muestra uso de disco, RAM y procesos activos",
        "triggers": [
            "status del sistema",
            "como esta la PC",
            "uso de recursos",
            "status sistema",
            "estado del sistema",
            "info del sistema",
        ],
        "steps": [
            {
                "tool": "pc_exec",
                "params": {
                    "command": "wmic",
                    "args": [
                        "logicaldisk",
                        "get",
                        "size,freespace,caption",
                        "/format:value",
                    ],
                },
                "desc": "Espacio en disco",
            },
            {
                "tool": "pc_exec",
                "params": {
                    "command": "wmic",
                    "args": ["computersystem", "get", "totalphysicalmemory"],
                },
                "desc": "RAM total",
            },
            {
                "tool": "pc_exec",
                "params": {
                    "command": "tasklist",
                    "args": ["/FI", "MEMUSAGE gt 100000", "/FO", "CSV"],
                },
                "desc": "Procesos con alto uso de memoria",
            },
        ],
        "risk": "low",
    },
    "abrir_proyecto": {
        "description": "Abre la carpeta de un proyecto en el explorador",
        "triggers": [
            "abre el proyecto",
            "abrir proyecto",
            "abre proyecto",
            "muestra el proyecto",
            "abre la carpeta del proyecto",
        ],
        "steps": [
            {
                "tool": "pc_exec",
                "params": {
                    "command": "explorer",
                    "args": [r"D:\Proyectos\Yggdrasil\Asgard\Lilith"],
                },
                "desc": "Abrir explorador en Lilith",
            },
        ],
        "risk": "low",
    },
}


class MacroRegistry:
    """
    Registro de macros PC. Permite detectar si un texto matchea una macro
    y expandirla a steps individuales.
    """

    def __init__(self):
        self._macros = PC_MACROS

    def match(self, text: str) -> Optional[Dict[str, Any]]:
        """
        Intenta matchear el texto contra las triggers de macros.

        Args:
            text: Texto del usuario

        Returns:
            La macro completa si hay match, None si no.
        """
        if not text:
            return None

        text_lower = text.lower().strip()

        for macro_name, macro in self._macros.items():
            for trigger in macro.get("triggers", []):
                # Match exacto o parcial al inicio
                if text_lower == trigger or text_lower.startswith(trigger):
                    logger.debug("Macro matched: %s (trigger: %s)", macro_name, trigger)
                    return macro
                # Match con palabras adicionales (ej: "organiza downloads ahora")
                if trigger in text_lower:
                    logger.debug("Macro matched (contained): %s", macro_name)
                    return macro

        return None

    def to_steps(self, macro: Dict[str, Any]) -> List[Step]:
        """
        Convierte una macro en lista de Steps.

        Args:
            macro: Dict de la macro (retornado por match())

        Returns:
            Lista de Step objects
        """
        steps = []
        for step_def in macro.get("steps", []):
            # Expandir variables de entorno en los parámetros
            params = _expand_path_params(step_def.get("params", {}))
            step = Step(tool_name=step_def["tool"], params=params)
            steps.append(step)
        return steps

    def list_macros(self) -> Dict[str, str]:
        """
        Lista todas las macros disponibles con descripción.
        Útil para ayuda/comandos.
        """
        return {name: macro["description"] for name, macro in self._macros.items()}

    def get_macro(self, name: str) -> Optional[Dict[str, Any]]:
        """Obtiene una macro por nombre exacto."""
        return self._macros.get(name)


# Singleton
_registry: Optional[MacroRegistry] = None


def get_macro_registry() -> MacroRegistry:
    """Obtiene el singleton del MacroRegistry."""
    global _registry
    if _registry is None:
        _registry = MacroRegistry()
    return _registry


def match_macro(text: str) -> Optional[List[Step]]:
    """
    Helper rápido: intenta matchear texto a macro y retorna steps.

    Args:
        text: Texto del usuario

    Returns:
        Lista de Steps si hay match, None si no.
    """
    registry = get_macro_registry()
    macro = registry.match(text)
    if macro:
        return registry.to_steps(macro)
    return None
