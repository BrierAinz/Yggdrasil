"""
Lilith 3.0 — Tools seguras para usuarios Trusted (Discord).
Chiste y meme: delegan en Lucifer con un prompt acotado. Sin acceso a archivos ni agentes pesados.
"""
from typing import Any, Dict

from .generate_reply_tool import _call_lucifer_sync
from .protocol import LilithTool, ToolResult


class ChisteTool(LilithTool):
    """Responde con un chiste corto. Tool segura para Trusted."""

    @property
    def name(self) -> str:
        return "chiste"

    def get_description(self) -> str:
        return "Cuenta un chiste corto y apropiado. Usar cuando el usuario pida un chiste o algo gracioso."

    def get_parameters_schema(self) -> Dict[str, Any]:
        return {"context": "string opcional (personalidad/tono)"}

    def execute(self, params: Dict[str, Any]) -> ToolResult:
        context = (params.get("context") or "").strip()
        task = "Responde con un solo chiste corto, apropiado y en español. Sin explicaciones adicionales."
        try:
            response = _call_lucifer_sync(task, context=context)
            return {"response": response or "(Sin respuesta)"}
        except Exception as e:
            return {"response": f"Error: {e}", "error": True}


class MemeTool(LilithTool):
    """Responde con una frase de meme o graciosa en texto. Tool segura para Trusted."""

    @property
    def name(self) -> str:
        return "meme"

    def get_description(self) -> str:
        return "Responde con una frase de meme, referencia graciosa o respuesta en tono meme (solo texto)."

    def get_parameters_schema(self) -> Dict[str, Any]:
        return {
            "context": "string opcional (personalidad/tono)",
            "message": "string opcional (petición del usuario)",
        }

    def execute(self, params: Dict[str, Any]) -> ToolResult:
        context = (params.get("context") or "").strip()
        user_msg = (params.get("message") or "").strip()
        task = "Responde con una frase de meme, referencia graciosa o en tono meme, en una o dos líneas, en español."
        if user_msg:
            task = f"{task} El usuario dijo: {user_msg}"
        try:
            response = _call_lucifer_sync(task, context=context)
            return {"response": response or "(Sin respuesta)"}
        except Exception as e:
            return {"response": f"Error: {e}", "error": True}
