"""
Lilith 3.0 — Registry de tools con interfaz unificada (Fase 1).
3.5 B.2: lazy loading — las tools se instancian en la primera invocación.
"""
import logging
from typing import Any, Callable, Dict, List, Optional

from .protocol import LilithTool, ToolResult

logger = logging.getLogger("ToolRegistryV3")


class ToolRegistryV3:
    """Catálogo dinámico de tools 3.0. register_lazy: instanciar solo al primer uso."""

    def __init__(self) -> None:
        self._tools: Dict[str, LilithTool] = {}
        self._factories: Dict[str, Callable[[], LilithTool]] = {}

    def register(self, tool: LilithTool) -> None:
        """Registra una tool por su nombre."""
        name = tool.name
        if name in self._tools or name in self._factories:
            logger.warning("Tool %s ya registrada; se sobrescribe.", name)
            self._factories.pop(name, None)
        self._tools[name] = tool
        logger.debug("Tool registrada: %s", name)

    def register_lazy(self, name: str, factory: Callable[[], LilithTool]) -> None:
        """B.2: Registra una factory; la tool se crea en el primer get/execute."""
        if name in self._tools:
            logger.warning("Tool %s ya instanciada; se ignora factory.", name)
            return
        self._factories[name] = factory
        logger.debug("Tool lazy registrada: %s", name)

    def get(self, name: str) -> Optional[LilithTool]:
        """Devuelve la tool por nombre; si hay factory, instancia y guarda."""
        if name in self._tools:
            return self._tools[name]
        if name in self._factories:
            try:
                tool = self._factories[name]()
                self._tools[name] = tool
                del self._factories[name]
                return tool
            except Exception as e:
                logger.warning("Tool lazy %s failed to instantiate: %s", name, e)
                return None
        return None

    def has(self, name: str) -> bool:
        return name in self._tools or name in self._factories

    def execute(self, name: str, params: Dict[str, Any]) -> ToolResult:
        """
        Ejecuta la tool por nombre. Params según la tool.
        Si la tool no existe o falla, devuelve dict con "response" de error.
        """
        tool = self.get(name)
        if not tool:
            return {"response": f"Tool desconocida: {name}", "error": True}
        try:
            result = tool.execute(params or {})
            if isinstance(result, str):
                return {"response": result}
            return result
        except Exception as e:
            # Control-flow: yield debe llegar al supervisor (PlanExecutor)
            try:
                from ..agent_yield import AgentYieldException
            except Exception:
                AgentYieldException = None  # type: ignore
            if AgentYieldException is not None and isinstance(e, AgentYieldException):  # type: ignore[arg-type]
                raise
            logger.exception("Error ejecutando tool %s: %s", name, e)
            return {"response": f"Error en {name}: {e}", "error": True}

    def list_tools(self) -> List[Dict[str, str]]:
        """Lista nombre y descripción de cada tool (para el router/orquestador)."""
        return [
            {"name": t.name, "description": t.get_description()}
            for t in self._tools.values()
        ]

    def names(self) -> List[str]:
        """Nombres registrados (incluye lazy no instanciados)."""
        return list(self._tools.keys()) + list(self._factories.keys())
