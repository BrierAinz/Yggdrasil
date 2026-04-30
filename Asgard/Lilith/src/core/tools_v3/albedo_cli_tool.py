"""
Lilith — Tool: delegación a Albedo (Kimi Code CLI con workspace Albedo).
Albedo es el workspace personal del Kimi CLI: AGENTS.md + sessions/ en
Workspace/Yggdrasil/Vanaheim/Albedo. Invoca el mismo Kimi CLI con ese directorio
como -w para que use ese contexto (ejecutora de Ainz, memoria en sessions/).
"""
import logging
from pathlib import Path
from typing import Any, Dict

from .kimi_cli_tool import DEFAULT_TIMEOUT, _run_kimi_cli
from .protocol import LilithTool, ToolResult

logger = logging.getLogger("AlbedoCLITool")

# Ruta relativa al project_root de Lilith (Core): Workspace/Yggdrasil/Vanaheim/Albedo
ALBEDO_WORKSPACE_REL = ["Workspace", "Yggdrasil", "Vanaheim", "Albedo"]


class AlbedoCLITool(LilithTool):
    """Delega una tarea al Kimi Code CLI usando el workspace Albedo (AGENTS.md, sessions/)."""

    def __init__(self, project_root: Path, timeout: int = DEFAULT_TIMEOUT) -> None:
        self.project_root = Path(project_root)
        self._albedo_workspace = self.project_root.joinpath(*ALBEDO_WORKSPACE_REL)
        self.timeout = timeout

    @property
    def name(self) -> str:
        return "delegate_albedo"

    def get_description(self) -> str:
        return (
            "Ejecuta una tarea con Albedo: Kimi Code CLI en el workspace Albedo (AGENTS.md, memoria en sessions/). "
            "Misma CLI que Kimi pero con el contexto y protocolo de Albedo — ejecutora de Ainz."
        )

    def get_parameters_schema(self) -> Dict[str, Any]:
        return {
            "task": "string — La tarea o misión para Albedo.",
            "context": "string — Contexto adicional opcional.",
        }

    def execute(self, params: Dict[str, Any]) -> ToolResult:
        from src.core.input_sanitizer import sanitize_input, validate_instruction

        raw_task = (params.get("task") or "").strip()
        raw_context = (params.get("context") or "").strip()

        task = sanitize_input(raw_task, max_len=4000)
        context = sanitize_input(raw_context, max_len=4000)
        if not task:
            return {"response": "Indica la tarea para Albedo.", "error": True}

        ok_t, err_t = validate_instruction(task, self.project_root)
        if not ok_t:
            return {
                "response": err_t or "La tarea contiene instrucciones no permitidas.",
                "error": True,
            }
        if context:
            ok_c, _ = validate_instruction(context, self.project_root)
            if not ok_c:
                return {
                    "response": "El contexto contiene instrucciones no permitidas.",
                    "error": True,
                }

        max_prompt_len = 8000
        combined = f"{task}\n\n[Contexto]:\n{context}" if context else task
        if len(combined) > max_prompt_len:
            combined = combined[:max_prompt_len].rstrip() + "\n… (truncado)"

        if not self._albedo_workspace.is_dir():
            return {
                "response": f"Workspace de Albedo no encontrado en {self._albedo_workspace}. Crea la carpeta o revisa la ruta.",
                "error": True,
            }

        response, ok = _run_kimi_cli(
            combined,
            self._albedo_workspace,
            timeout=self.timeout,
            project_root=self.project_root,
            model=None,
        )
        return {"response": response, "error": not ok}
