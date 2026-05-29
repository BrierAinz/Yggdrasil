"""
PC Macro Engine — Sistema de macros para PC Agent (F.17).

Features:
- Macros predefinidas desde JSON
- Detección desde lenguaje natural
- Validación de parámetros
- 1 confirmación para todo el batch
"""
import json
import logging
import re
import time
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from src.core.json_safe import safe_load

logger = logging.getLogger("lilith.pc.macro")


@dataclass
class MacroStep:
    """Un paso en una macro."""

    operation: str
    params: Dict[str, Any]

    def to_pc_step(self) -> Dict[str, Any]:
        """Convierte a formato de step para PC Agent."""
        return {"op": self.operation, **self.params}


@dataclass
class Macro:
    """Definición de una macro."""

    name: str
    description: str
    requires_confirmation: bool
    steps: List[MacroStep]
    params: Dict[str, Any]

    @classmethod
    def from_dict(cls, name: str, data: dict) -> "Macro":
        steps = [
            MacroStep(
                operation=s.get("operation", s.get("op", "")),
                params={k: v for k, v in s.items() if k not in ("operation", "op")},
            )
            for s in data.get("steps", [])
        ]
        return cls(
            name=name,
            description=data.get("description", ""),
            requires_confirmation=data.get("requires_confirmation", True),
            steps=steps,
            params=data.get("params", {}),
        )


class PCMacroEngine:
    """
    Motor de macros para PC Agent.
    Carga macros desde config y permite ejecutarlas.
    """

    def __init__(self, base_path: Path):
        self.base_path = Path(base_path)
        self.config_path = self.base_path / "Config" / "pc_agent_macros.json"
        self.macros: Dict[str, Macro] = {}
        self.detection_keywords: Dict[str, List[str]] = {}
        self._load_macros()

    def _load_macros(self):
        """Carga macros desde archivo de configuración."""
        cfg = safe_load(self.config_path, default={})

        macros_data = cfg.get("macros", {})
        for name, data in macros_data.items():
            try:
                self.macros[name] = Macro.from_dict(name, data)
                logger.debug("[PCMacroEngine] Macro cargada: %s", name)
            except Exception as e:
                logger.warning("[PCMacroEngine] Error cargando macro %s: %s", name, e)

        # Cargar keywords de detección
        self.detection_keywords = cfg.get("detection_keywords", {})

        logger.info("[PCMacroEngine] Cargadas %d macros", len(self.macros))

    def list_macros(self) -> List[Dict[str, str]]:
        """Lista macros disponibles."""
        return [
            {"name": name, "description": macro.description}
            for name, macro in self.macros.items()
        ]

    def get_macro(self, name: str) -> Optional[Macro]:
        """Obtiene una macro por nombre."""
        return self.macros.get(name)

    def detect_macro(self, text: str) -> Optional[Tuple[str, float]]:
        """
        Detecta si el texto corresponde a una macro.
        Retorna (macro_name, confidence) o None.
        """
        text_lower = text.lower()
        scores: Dict[str, int] = {}

        for macro_name, keywords in self.detection_keywords.items():
            score = 0
            for keyword in keywords:
                if keyword.lower() in text_lower:
                    score += 1
                    # Bonus si la keyword está al inicio
                    if text_lower.startswith(keyword.lower()):
                        score += 1
            if score > 0:
                scores[macro_name] = score

        if not scores:
            return None

        # Elegir la macro con mayor score
        best_match = max(scores.items(), key=lambda x: x[1])
        confidence = min(best_match[1] / 3, 1.0)  # Normalizar a 0-1

        logger.debug(
            "[PCMacroEngine] Detectada macro '%s' con confianza %.2f",
            best_match[0],
            confidence,
        )
        return best_match[0], confidence

    def extract_params(self, text: str, macro_name: str) -> Dict[str, Any]:
        """
        Extrae parámetros del texto para una macro.
        Usa heurísticas simples y valores por defecto.
        """
        macro = self.macros.get(macro_name)
        if not macro:
            return {}

        params = {}
        text_lower = text.lower()

        for param_name, param_config in macro.params.items():
            param_type = param_config.get("type", "string")

            if param_type == "auto":
                # Valores automáticos
                auto_value = param_config.get("value", "")
                if auto_value == "{{auto_timestamp}}":
                    params[param_name] = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
                elif auto_value == "{{auto_date}}":
                    params[param_name] = datetime.now().strftime("%Y-%m-%d")
                else:
                    params[param_name] = auto_value

            elif param_type == "path":
                # Extraer posible ruta del texto
                # Buscar patrones como "proyecto X", "en X", "ruta X"
                patterns = [
                    rf"{param_name}\s+([\w\\/:\-. ]+)",
                    rf"proyecto\s+([\w\\/:\-. ]+)",
                    rf"en\s+([\w\\/:\-. ]+)",
                ]
                for pattern in patterns:
                    match = re.search(pattern, text, re.IGNORECASE)
                    if match:
                        path = match.group(1).strip()
                        # Expandir atajos comunes
                        path = self._expand_path_shortcuts(path)
                        params[param_name] = path
                        break
                else:
                    # Usar valor por defecto si existe
                    if "default" in param_config:
                        params[param_name] = param_config["default"]

            elif param_type == "string":
                # Extraer string del texto
                # Buscar después de ciertas palabras clave
                patterns = [
                    rf"{param_name}\s+['\"]?([\w\s\-]+)['\"]?",
                    rf"con\s+mensaje\s+['\"]?([\w\s\-]+)['\"]?",
                ]
                for pattern in patterns:
                    match = re.search(pattern, text, re.IGNORECASE)
                    if match:
                        params[param_name] = match.group(1).strip()
                        break
                else:
                    if "default" in param_config:
                        params[param_name] = param_config["default"]

        return params

    def _expand_path_shortcuts(self, path: str) -> str:
        """Expande atajos de ruta comunes."""
        import os

        _module_dir = Path(__file__).resolve().parent
        _yggdrasil_root = Path(os.environ.get("YGGDRASIL_ROOT", str(_module_dir.parents[4])))
        _proyectos_root = _yggdrasil_root.parent
        _lilith_root = _yggdrasil_root / "Asgard" / "Lilith"

        shortcuts = {
            "proyectos": str(_proyectos_root),
            "lilith": str(_lilith_root),
            "core": str(_lilith_root / "Core"),
            "backend": str(_lilith_root / "Core" / "Backend"),
            "config": str(_lilith_root / "Core" / "Config"),
            "desktop": os.path.expandvars(r"%USERPROFILE%\Desktop"),
            "downloads": os.path.expandvars(r"%USERPROFILE%\Downloads"),
        }

        path_lower = path.lower().strip()
        if path_lower in shortcuts:
            return shortcuts[path_lower]

        # Reemplazar si el primer componente es un shortcut
        parts = path.replace("\\", "/").split("/")
        if parts and parts[0].lower() in shortcuts:
            parts[0] = shortcuts[parts[0].lower()]
            return "/".join(parts)

        return path

    def validate_params(
        self, macro_name: str, params: Dict[str, Any]
    ) -> Tuple[bool, str]:
        """
        Valida los parámetros para una macro.
        Retorna (is_valid, error_message).
        """
        macro = self.macros.get(macro_name)
        if not macro:
            return False, f"Macro '{macro_name}' no encontrada"

        for param_name, param_config in macro.params.items():
            if param_config.get("required", False):
                if param_name not in params or not params[param_name]:
                    return False, f"Parámetro requerido '{param_name}' no proporcionado"

            # Validar tipo path
            if param_config.get("type") == "path" and param_name in params:
                path = params[param_name]
                # Verificar que no contenga caracteres peligrosos
                dangerous = ["..", "~", "$", "|", ";", "&&", "||"]
                for d in dangerous:
                    if d in str(path):
                        return (
                            False,
                            f"Parámetro '{param_name}' contiene caracteres no permitidos",
                        )

        return True, ""

    def build_batch_steps(
        self, macro_name: str, params: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """
        Construye los steps para ejecutar una macro con los parámetros dados.
        Reemplaza placeholders en los steps.
        """
        macro = self.macros.get(macro_name)
        if not macro:
            return []

        steps = []
        for step in macro.steps:
            step_params = {}
            for key, value in step.params.items():
                # Reemplazar placeholders {param_name}
                if isinstance(value, str):
                    for param_name, param_value in params.items():
                        placeholder = f"{{{param_name}}}"
                        value = value.replace(placeholder, str(param_value))
                step_params[key] = value

            steps.append({"op": step.operation, **step_params})

        return steps

    def generate_preview(self, macro_name: str, params: Dict[str, Any]) -> str:
        """Genera preview de la macro para confirmación."""
        macro = self.macros.get(macro_name)
        if not macro:
            return "Macro no encontrada"

        lines = [
            f"🔧 **Macro: {macro_name}**",
            f"_{macro.description}_",
            "",
            "**Operaciones:**",
        ]

        steps = self.build_batch_steps(macro_name, params)
        for i, step in enumerate(steps, 1):
            op = step.get("op", step.get("operation", "unknown"))
            if op in ("copy", "move"):
                lines.append(
                    f"{i}. {op}: `{step.get('source', step.get('src', '?'))}` → `{step.get('destination', step.get('dst', '?'))}`"
                )
            elif op == "mkdir":
                lines.append(f"{i}. Crear carpeta: `{step.get('path', '?')}`")
            elif op == "exec":
                lines.append(
                    f"{i}. Ejecutar: `{step.get('command', step.get('cmd', '?'))}`"
                )
            elif op == "write_file":
                lines.append(f"{i}. Escribir archivo: `{step.get('path', '?')}`")
            else:
                lines.append(f"{i}. {op}")

        if params:
            lines.extend(["", "**Parámetros:**"])
            for k, v in params.items():
                lines.append(f"- {k}: `{v}`")

        return "\n".join(lines)


# Singleton
_macro_engine = None


def get_macro_engine(base_path: Optional[Path] = None) -> PCMacroEngine:
    """Obtiene instancia singleton del motor de macros."""
    global _macro_engine
    if _macro_engine is None:
        if base_path is None:
            base_path = Path(__file__).resolve().parent.parent.parent
        _macro_engine = PCMacroEngine(base_path)
    return _macro_engine
