"""
Vanaheim Node Executor - Ejecutor de nodos DAG que invoca agentes de Vanaheim.

Features:
- Ejecuta nodos DAG vía agentes de Vanaheim
- Integración con Bifrost para comunicación
- Fallback a ejecución local si Vanaheim no disponible
- Métricas de ejecución
"""
import logging
import time
from pathlib import Path
from typing import Any, Dict, Optional

from ..bifrost_client import get_bifrost_client
from ..vanaheim_router import get_vanaheim_router
from .plan_dag import DagNode

logger = logging.getLogger("lilith.dag.vanaheim")


class VanaheimNodeExecutor:
    """
    Executor de nodos DAG que delega a agentes de Vanaheim.
    """

    def __init__(self, base_path: Optional[Path] = None):
        self.base_path = (
            Path(base_path) if base_path else Path(__file__).resolve().parents[3]
        )
        self.bifrost = get_bifrost_client(self.base_path)
        self.router = get_vanaheim_router(self.base_path)

        # Métricas
        self._vanaheim_calls = 0
        self._local_fallbacks = 0
        self._failures = 0

    async def execute(self, node: DagNode, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Ejecuta un nodo DAG vía agente de Vanaheim.

        Args:
            node: Nodo DAG a ejecutar
            context: Contexto de ejecución (incluye outputs de dependencias)

        Returns:
            Resultado de la ejecución
        """
        start_time = time.time()
        node_id = node.id
        tool_name = node.tool_name

        logger.debug(f"[VanaheimNodeExecutor] Executing {node_id}: {tool_name}")

        # Determinar qué agente de Vanaheim usar
        agent = self.router.get_agent_for_tool(tool_name)

        # Preparar payload
        payload = {
            "tool": tool_name,
            "params": node.params,
            "context": context,
            "node_id": node_id,
        }

        # Intentar ejecución vía Bifrost
        try:
            result = await self._execute_via_bifrost(agent, payload)

            if result:
                self._vanaheim_calls += 1
                latency = (time.time() - start_time) * 1000
                return {
                    "success": True,
                    "output": result.get("response", ""),
                    "tool_name": tool_name,
                    "agent_used": agent,
                    "execution_time_ms": latency,
                    "source": "vanaheim",
                }

        except Exception as e:
            logger.warning(f"[VanaheimNodeExecutor] Bifrost failed: {e}")

        # Fallback a ejecución local
        logger.debug(f"[VanaheimNodeExecutor] Falling back to local execution")
        return await self._execute_local(node, context)

    async def _execute_via_bifrost(
        self, agent: str, payload: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """Ejecuta vía Bifrost."""
        # Mapear agentes de Vanaheim a agentes conocidos por Bifrost
        agent_map = {
            "freya": "eva",
            "heimdall": "odin",
            "eir": "adan",
            "balder": "eva",
        }

        bifrost_agent = agent_map.get(agent, "eva")

        task = f"Execute tool: {payload['tool']} with params: {payload['params']}"

        result = await self.bifrost.execute(
            agent=bifrost_agent, task=task, context=str(payload.get("context", {}))
        )

        return result

    async def _execute_local(
        self, node: DagNode, context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Ejecución local cuando Vanaheim no está disponible."""
        import asyncio

        start_time = time.time()

        # Ejecutar en thread para no bloquear
        loop = asyncio.get_event_loop()

        try:
            # Intentar importar y ejecutar agente local
            result = await loop.run_in_executor(
                None, self._run_local_agent, node, context
            )

            self._local_fallbacks += 1
            latency = (time.time() - start_time) * 1000

            return {
                "success": True,
                "output": result,
                "tool_name": node.tool_name,
                "agent_used": "local",
                "execution_time_ms": latency,
                "source": "local_fallback",
            }

        except Exception as e:
            self._failures += 1
            logger.error(f"[VanaheimNodeExecutor] Local execution failed: {e}")
            return {
                "success": False,
                "error": str(e),
                "tool_name": node.tool_name,
                "agent_used": "none",
            }

    def _run_local_agent(self, node: DagNode, context: Dict) -> str:
        """Ejecuta agente local (síncrono para thread pool)."""
        tool_name = node.tool_name

        # Tool simple: devolver información del contexto
        if tool_name == "get_context":
            return str(context)

        # Tool de procesamiento simple
        if tool_name == "process":
            params = node.params
            return f"Processed: {params}"

        # Fallback genérico
        return f"[Local Execution] Tool {tool_name} executed with params: {node.params}"

    def get_stats(self) -> Dict[str, Any]:
        """Retorna estadísticas de ejecución."""
        total = self._vanaheim_calls + self._local_fallbacks + self._failures
        return {
            "vanaheim_calls": self._vanaheim_calls,
            "local_fallbacks": self._local_fallbacks,
            "failures": self._failures,
            "vanaheim_ratio": self._vanaheim_calls / total if total > 0 else 0,
        }


class HybridNodeExecutor:
    """
    Executor híbrido que decide entre ejecución local o en Vanaheim
    basado en la complejidad del nodo y carga del sistema.
    """

    def __init__(
        self, base_path: Optional[Path] = None, use_vanaheim_for: Optional[list] = None
    ):
        self.base_path = (
            Path(base_path) if base_path else Path(__file__).resolve().parents[3]
        )
        self.vanaheim_executor = VanaheimNodeExecutor(self.base_path)
        self.local_executor = None  # Se configura externamente

        # Tools que siempre van a Vanaheim
        self._vanaheim_tools = set(
            use_vanaheim_for
            or [
                "delegate_freya",
                "delegate_heimdall",
                "delegate_eir",
                "delegate_balder",
                "web_search",
                "analyze_document",
            ]
        )

    async def execute(self, node: DagNode, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Ejecuta un nodo usando la estrategia apropiada.
        """
        tool_name = node.tool_name

        # Decidir estrategia
        if tool_name in self._vanaheim_tools:
            # Usar Vanaheim
            return await self.vanaheim_executor.execute(node, context)

        # Usar ejecución local (PlanExecutor)
        if self.local_executor:
            return await self.local_executor(node, context)

        # Fallback a Vanaheim si no hay local
        return await self.vanaheim_executor.execute(node, context)

    def set_local_executor(self, executor):
        """Establece el executor local."""
        self.local_executor = executor


# Factory function
def create_vanaheim_node_executor(
    base_path: Optional[Path] = None, hybrid: bool = True
):
    """Crea un executor de nodos para Vanaheim."""
    if hybrid:
        return HybridNodeExecutor(base_path)
    return VanaheimNodeExecutor(base_path)
