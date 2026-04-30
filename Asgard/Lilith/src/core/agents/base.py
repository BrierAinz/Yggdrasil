"""
Base Agent - Clase abstracta para todos los agentes del Panteón
"""
from abc import ABC, abstractmethod
from typing import Optional


class BaseAgent(ABC):
    """
    Clase base abstracta para todos los agentes.
    """

    name: str = "BaseAgent"
    description: str = "Agente base"

    @abstractmethod
    async def execute(self, task: str, context: str = "") -> str:
        """
        Ejecuta una tarea y retorna el resultado.

        Args:
            task: La tarea a ejecutar
            context: Contexto adicional (opcional)

        Returns:
            Resultado de la ejecución como string
        """
        pass

    def get_system_prompt(self) -> str:
        """
        Retorna el system prompt del agente.
        """
        return ""

    def is_available(self) -> bool:
        """
        Verifica si el agente está disponible (API keys, conectividad, etc.)
        """
        return True
