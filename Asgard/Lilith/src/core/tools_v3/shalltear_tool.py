"""
Shalltear Tool — Delegate tasks to Shalltear (Venice/llama-3.3-70b).
Tactical agent for classification, NL parsing, and quick responses.
"""
from typing import Any, Dict

from .protocol import LilithTool, ToolResult


class DelegateShalltearTool(LilithTool):
    """
    Delega a Shalltear (Venice/llama-3.3-70b): clasificación, parsing NL, respuestas rápidas.
    Útil para triaje inicial antes de llamar a agentes más pesados (Odín, Eva).
    """

    @property
    def name(self) -> str:
        return "delegate_shalltear"

    def get_description(self) -> str:
        return (
            "Delega a Shalltear (Venice/llama-3.3-70b): "
            "clasificación de intenciones, parsing de lenguaje natural a JSON, "
            "scoring de importancia, respuestas rápidas. "
            "Usar para tareas tácticas que no requieren contexto largo ni creatividad."
        )

    def get_parameters_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "task": {
                    "type": "string",
                    "enum": [
                        "classify_intent",
                        "parse_nl",
                        "score_importance",
                        "quick_answer",
                    ],
                    "description": "Tipo de tarea a realizar",
                },
                "user_message": {
                    "type": "string",
                    "description": "Mensaje/texto a procesar",
                },
                "context": {
                    "type": "string",
                    "description": "Contexto adicional (opcional)",
                },
                "categories": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Categorías para classify_intent (opcional)",
                },
                "operation": {
                    "type": "string",
                    "description": "Tipo de operación para parse_nl (ej: filesystem_batch)",
                },
            },
            "required": ["task", "user_message"],
        }

    def execute(self, params: Dict[str, Any]) -> ToolResult:
        task = params.get("task", "quick_answer")
        user_message = params.get("user_message", "")
        context = params.get("context", "")
        categories = params.get("categories")
        operation = params.get("operation", "filesystem_batch")

        if not user_message:
            return {"response": "(mensaje vacío)", "error": True}

        try:
            from src.core.agents.panteon.shalltear import ShalltearAgent

            agent = ShalltearAgent()

            if not agent.is_available():
                return {
                    "response": "[Shalltear offline] VENICE_API_KEY no configurada. Fallback a Adán o Lilith.",
                    "error": True,
                    "fallback": "delegate_adan",
                }

            if task == "classify_intent":
                result = agent.classify_intent(user_message, categories)
                return {"response": result, "agent": "Shalltear", "task": task}

            elif task == "parse_nl":
                result = agent.parse_nl_to_params(user_message, operation)
                if result is None:
                    return {
                        "response": "ESCALATE",
                        "agent": "Shalltear",
                        "task": task,
                        "error": True,
                    }
                return {
                    "response": json.dumps(result, ensure_ascii=False),
                    "agent": "Shalltear",
                    "task": task,
                }

            elif task == "score_importance":
                result = agent.score_importance(user_message)
                return {
                    "response": str(result),
                    "agent": "Shalltear",
                    "task": task,
                    "score": result,
                }

            else:  # quick_answer
                result = agent.quick_answer(user_message, context)
                if result == "ESCALATE":
                    return {"response": "ESCALATE", "agent": "Shalltear", "error": True}
                return {"response": result, "agent": "Shalltear", "task": task}

        except Exception as e:
            return {"response": f"Error en Shalltear: {e}", "error": True}


class ShalltearParseTool(LilithTool):
    """
    Tool específica para parsing NL a operaciones PC.
    Wrapper conveniente sobre delegate_shalltear con task=parse_nl.
    """

    @property
    def name(self) -> str:
        return "shalltear_parse_pc"

    def get_description(self) -> str:
        return (
            "Parsea lenguaje natural a operaciones de filesystem PC. "
            "Ej: 'mueve los PDFs de downloads a documentos' → JSON con operaciones pc_move."
        )

    def get_parameters_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "user_message": {
                    "type": "string",
                    "description": "Comando en lenguaje natural",
                }
            },
            "required": ["user_message"],
        }

    def execute(self, params: Dict[str, Any]) -> ToolResult:
        user_message = params.get("user_message", "")

        if not user_message:
            return {
                "response": '{"operations": [], "error": "mensaje vacío"}',
                "error": True,
            }

        try:
            from src.core.agents.panteon.shalltear import ShalltearAgent

            agent = ShalltearAgent()

            if not agent.is_available():
                return {
                    "response": "ESCALATE",
                    "error": True,
                    "reason": "Venice API not available",
                }

            result = agent.parse_nl_to_params(
                user_message, operation="filesystem_batch"
            )

            if result is None:
                return {
                    "response": '{"operations": [], "error": "parse failed"}',
                    "error": True,
                }

            import json

            return {
                "response": json.dumps(result, ensure_ascii=False),
                "agent": "Shalltear",
            }

        except Exception as e:
            return {
                "response": f'{{"operations": [], "error": "{str(e)}"}}',
                "error": True,
            }
