from __future__ import annotations

from typing import Any, Dict

from ..agent_yield import AgentYieldException
from .protocol import LilithTool, ToolResult


class YieldToAgentTool(LilithTool):
    @property
    def name(self) -> str:
        return "yield_to_agent"

    def get_description(self) -> str:
        return (
            "Pausa tu ejecución actual y delega una subtarea estructurada a otro agente "
            "(solo 'eva'). El supervisor (Lucifer/PlanExecutor) reanudará el plan."
        )

    def get_parameters_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "target": {
                    "type": "string",
                    "enum": ["eva"],
                    "description": "Agente receptor.",
                },
                "task_description": {
                    "type": "string",
                    "description": "Instrucción imperativa (1-3 frases).",
                },
                "context_payload": {
                    "type": "string",
                    "description": "Contexto/formato exacto requerido. Sé exhaustivo.",
                },
            },
            "required": ["target", "task_description", "context_payload"],
        }

    def execute(self, params: Dict[str, Any]) -> ToolResult:
        target = (params.get("target") or "").strip().lower()
        task = (params.get("task_description") or "").strip()
        payload = (params.get("context_payload") or "").strip()
        if target != "eva":
            return {"response": "target inválido (solo 'eva').", "error": True}
        if not task or not payload:
            return {
                "response": "Faltan task_description o context_payload.",
                "error": True,
            }
        raise AgentYieldException(
            target=target, task_description=task, context_payload=payload
        )
