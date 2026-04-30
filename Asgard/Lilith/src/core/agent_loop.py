"""
Agent Loop - Permite a Lilith encadenar herramientas autónomamente.

Máximo 10 iteraciones para evitar loops infinitos.
"""
from typing import Any, Dict, List, Optional

from .agent_router import AgentRouter


class AgentLoop:
    """
    Loop de ejecución de agentes.
    Permite encadenar múltiples agentes para completar un objetivo complejo.
    """

    def __init__(self, tool_registry=None, max_iterations: int = 10):
        """
        Inicializa el AgentLoop.

        Args:
            tool_registry: Registro de herramientas (opcional)
            max_iterations: Máximo número de iteraciones para evitar loops
        """
        self.tool_registry = tool_registry
        self.router = AgentRouter()
        self.max_iterations = max_iterations

    async def run(self, objetivo: str, context: str = "") -> Dict[str, Any]:
        """
        Ejecuta un objetivo usando el agente más apropiado.

        Args:
            objetivo: El objetivo a cumplir
            context: Contexto adicional

        Returns:
            Dict con los resultados de la ejecución
        """
        results = []
        iteration = 0

        # Estimar tokens del contexto (aproximado: 4 chars = 1 token)
        context_tokens = len(context) // 4 if context else 0

        # Seleccionar agente apropiado
        agent_name = self.router.select_agent(objetivo, context_tokens)

        if agent_name == "grok":
            # Lilith maneja directamente, no necesita delegación
            return {
                "objetivo": objetivo,
                "iteraciones": 0,
                "resultados": [],
                "completado": False,
                "delegado_a": "grok",
                "mensaje": "Lilith maneja esta tarea directamente.",
            }

        # Delegar al agente seleccionado
        result = await self.router.execute(
            task=objetivo,
            agent_name=agent_name,
            context=context,
            context_tokens=context_tokens,
        )

        results.append(result)

        return {
            "objetivo": objetivo,
            "iteraciones": 1,
            "resultados": results,
            "completado": result.get("delegated", False),
            "delegado_a": agent_name,
            "agent_display": result.get("agent_display", agent_name),
        }

    async def run_multi_step(self, pasos: List[Dict[str, str]]) -> Dict[str, Any]:
        """
        Ejecuta múltiples pasos secuencialmente.

        Args:
            pasos: Lista de dicts con 'agent' (opcional) y 'task'

        Returns:
            Dict con los resultados de todos los pasos
        """
        results = []
        accumulated_context = ""

        for i, paso in enumerate(pasos[: self.max_iterations]):
            task = paso.get("task", "")
            agent_name = paso.get("agent")  # None para auto-selección

            # Ejecutar el paso
            result = await self.router.execute(
                task=task, agent_name=agent_name, context=accumulated_context
            )

            results.append({"paso": i + 1, "task": task, "result": result})

            # Acumular contexto para el siguiente paso
            if result.get("result"):
                accumulated_context += f"\n\n[Paso {i+1}]: {result['result']}"

        return {
            "objetivo": "multi-step execution",
            "iteraciones": len(results),
            "resultados": results,
            "completado": True,
        }

    def explain_routing(self, task: str, context_tokens: int = 0) -> Dict[str, Any]:
        """
        Explica por qué se seleccionó un agente específico.
        Útil para debugging y transparencia.
        """
        agent_name = self.router.select_agent(task, context_tokens)
        agent_info = self.router.get_agent_info().get(agent_name, {})

        task_lower = task.lower()
        reasons = []

        if agent_name == "eva":
            if context_tokens > 50000:
                reasons.append(f"Contexto largo ({context_tokens} tokens estimados)")
            eva_keywords = ["analiza", "documenta", "resume", "audita"]
            for kw in eva_keywords:
                if kw in task_lower:
                    reasons.append(f"Palabra clave detectada: '{kw}'")
                    break

        elif agent_name == "adan":
            reasons.append("Tarea de generación/refactorización de código")

        elif agent_name == "lucifer":
            reasons.append(
                "Tarea creativa/privada que requiere pensamiento no convencional"
            )

        else:
            reasons.append("Tarea general, mejor manejada por Lilith directamente")

        return {
            "task": task,
            "selected_agent": agent_name,
            "agent_display": agent_info.get("name", agent_name),
            "reasons": reasons,
            "context_tokens": context_tokens,
            "all_agents": self.router.get_agent_info(),
        }
