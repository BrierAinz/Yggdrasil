from __future__ import annotations


class AgentYieldException(Exception):
    """
    Señal de control de flujo para handoff horizontal supervisado.
    No debe ser atrapada por ToolRegistry/AgentCaller; el PlanExecutor la intercepta.
    """

    def __init__(self, target: str, task_description: str, context_payload: str):
        self.target = (target or "").strip().lower()
        self.task_description = (task_description or "").strip()
        self.context_payload = (context_payload or "").strip()
        super().__init__(f"Yield to {self.target}")
