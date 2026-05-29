"""
Lilith 3.3 — ExecuteChainedTool: ejecuta secuencias definidas en Config/chained_tools.json.
Placeholders: {path}, {output_of_step_0}, {output_of_step_1}, ...
"""
import re
from pathlib import Path
from typing import Any, Dict, List, Optional

from .protocol import LilithTool, ToolResult
from .registry import ToolRegistryV3


def _resolve_placeholders(
    params: Dict[str, Any],
    user_params: Dict[str, Any],
    step_outputs: List[str],
) -> Dict[str, Any]:
    """Sustituye {path}, {output_of_step_0}, etc. en los valores de params."""
    out = {}
    for k, v in params.items():
        if not isinstance(v, str):
            out[k] = v
            continue
        s = v
        for key, val in (user_params or {}).items():
            s = s.replace("{" + key + "}", str(val))
        for i, out_val in enumerate(step_outputs):
            s = s.replace("{output_of_step_" + str(i) + "}", out_val)
        out[k] = s
    return out


def _result_to_str(result: Any) -> str:
    if result is None:
        return ""
    if isinstance(result, str):
        return result.strip()
    if isinstance(result, dict) and "response" in result:
        v = result["response"]
        return str(v).strip() if v is not None else ""
    return str(result).strip()


class ExecuteChainedTool(LilithTool):
    """Ejecuta una cadena de tools definida en Config/chained_tools.json (Misión 3.3)."""

    def __init__(self, project_root: Path, registry: ToolRegistryV3):
        self._root = Path(project_root)
        self._registry = registry

    @property
    def name(self) -> str:
        return "execute_chained"

    def get_description(self) -> str:
        return (
            "Ejecuta una receta definida en chained_tools.json. "
            "Params: chain_name (nombre de la cadena), path (opcional), y cualquier otro que use la cadena."
        )

    def get_parameters_schema(self) -> Dict[str, Any]:
        return {
            "chain_name": "string (nombre en chained_tools.json)",
            "path": "string opcional",
            "fact": "string opcional (para cadenas que lo usen)",
        }

    def _load_chains(self) -> List[Dict[str, Any]]:
        from ..json_safe import safe_load

        path = self._root / "Config" / "chained_tools.json"
        data = safe_load(path, default={})
        tools = data.get("tools") if isinstance(data, dict) else []
        return tools if isinstance(tools, list) else []

    def execute(self, params: Dict[str, Any]) -> ToolResult:
        chain_name = (params.get("chain_name") or "").strip()
        if not chain_name:
            return {
                "response": "Indica chain_name (ej. analyze_and_suggest_improvement).",
                "error": True,
            }
        chains = self._load_chains()
        chain_def = None
        for c in chains:
            if isinstance(c, dict) and (c.get("name") or "").strip() == chain_name:
                chain_def = c
                break
        if not chain_def:
            return {
                "response": f"Cadena '{chain_name}' no encontrada en chained_tools.json.",
                "error": True,
            }
        steps = chain_def.get("steps")
        if not steps or not isinstance(steps, list):
            return {
                "response": f"La cadena '{chain_name}' no tiene steps.",
                "error": True,
            }
        user_params = {k: v for k, v in params.items() if k != "chain_name"}
        step_outputs: List[str] = []
        for i, step in enumerate(steps):
            if not isinstance(step, dict):
                continue
            tool_name = (step.get("tool") or "").strip()
            if not tool_name:
                continue
            step_params = _resolve_placeholders(
                dict(step.get("params") or {}),
                user_params,
                step_outputs,
            )
            result = self._registry.execute(tool_name, step_params)
            out_str = _result_to_str(result)
            step_outputs.append(out_str)
        if not step_outputs:
            return {"response": "La cadena no produjo salida.", "error": True}
        return {"response": step_outputs[-1], "data": {"steps_run": len(step_outputs)}}
