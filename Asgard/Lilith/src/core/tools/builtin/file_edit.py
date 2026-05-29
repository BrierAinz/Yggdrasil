"""
Lilith 3.0 — Tool: editar archivo (wrapper de CodeEditor).
Solo propone o aplica cambios; confirmación (reacciones Discord) queda para Fase 2.
"""
import json
from pathlib import Path
from typing import Any, Dict

from ..security_guard import SecurityGuard
from .protocol import LilithTool, ToolResult


class FileEditTool(LilithTool):
    """Editar archivo: reemplazar texto o insertar contenido."""

    def __init__(self, project_root: Path) -> None:
        self._root = Path(project_root)

    @property
    def name(self) -> str:
        return "edit_file"

    def get_description(self) -> str:
        return "Editar o escribir en un archivo. Usar cuando pidan modificar, cambiar o escribir código/archivo."

    def get_parameters_schema(self) -> Dict[str, Any]:
        return {
            "path": "string (ruta al archivo)",
            "action": "edit | write | insert",
            "target": "string (texto a reemplazar, para edit)",
            "replacement": "string (nuevo texto, para edit)",
            "content": "string (para write/insert)",
        }

    def execute(self, params: Dict[str, Any]) -> ToolResult:
        path = (params.get("path") or "").strip()
        if not path:
            return {"response": "Indica la ruta del archivo a editar.", "error": True}
        from src.core.input_sanitizer import validate_instruction, validate_path

        ok, err = validate_path(path, self._root)
        if not ok:
            return {"response": err or "Ruta no válida.", "error": True}
        for field in ("instruction", "target", "replacement", "content"):
            raw = params.get(field)
            if raw and isinstance(raw, str):
                ok_i, err_i = validate_instruction(raw, self._root)
                if not ok_i:
                    return {
                        "response": err_i or "Instrucción no permitida.",
                        "error": True,
                    }
        action = (params.get("action") or "edit").lower()
        if action not in ("edit", "write", "insert"):
            action = "edit"

        # SecurityGuard: separar semántica edit vs write
        try:
            file_abs = (self._root / path).expanduser().resolve(strict=False)
            exists = file_abs.exists()
        except Exception:
            exists = False
        op = "edit" if action in ("edit", "insert") else "write"
        # Si el archivo existe y se pretende overwrite completo, exigir write
        if exists and bool(params.get("overwrite", False)):
            op = "write"
        decision = SecurityGuard(self._root).check_path(op, path)
        if not decision.allowed:
            return {
                "response": json.dumps(decision.response, ensure_ascii=False),
                "error": True,
            }
        if (
            action == "edit"
            and not params.get("target")
            and not params.get("replacement")
            and params.get("instruction")
        ):
            return {
                "response": "Para editar con instrucción en lenguaje natural hace falta un paso extra (Fase 2). Por ahora indica 'target' (texto a reemplazar) y 'replacement' (texto nuevo), o usa write/insert con 'content'."
            }

        try:
            from src.tools.enhanced.code_editor import CodeEditor

            editor = CodeEditor(root_path=str(self._root))
            out = editor.execute(
                action,
                file_path=path,
                target=params.get("target", ""),
                replacement=params.get("replacement", ""),
                content=params.get("content", ""),
                line_number=params.get("line_number", 1),
                overwrite=params.get("overwrite", False),
            )
        except Exception as e:
            return {"response": f"Error al editar: {e}", "error": True}

        if not out.get("success"):
            return {
                "response": out.get("error", "Error editando archivo"),
                "error": True,
            }
        return {"response": out.get("message", "Cambio aplicado."), "data": out}
