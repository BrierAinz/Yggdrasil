"""
Lilith 3.0 — Protocolo unificado de tools (Fase 1).
Todas las herramientas exponen get_description() y execute(params).
"""
from abc import ABC, abstractmethod
from typing import Any, Dict, Union

# Respuesta estándar: str directo o dict con "response" (texto para usuario) y opcional "data"
ToolResult = Union[str, Dict[str, Any]]


class LilithTool(ABC):
    """Interfaz que debe implementar toda tool del núcleo 3.0."""

    @property
    @abstractmethod
    def name(self) -> str:
        """Nombre único de la tool (ej. read_file, delegate_eva)."""
        ...

    @abstractmethod
    def get_description(self) -> str:
        """Descripción breve para el router y el orquestador."""
        ...

    def get_parameters_schema(self) -> Dict[str, Any]:
        """Esquema opcional de parámetros (nombre -> tipo/descripción). Por defecto vacío."""
        return {}

    @abstractmethod
    def execute(self, params: Dict[str, Any]) -> ToolResult:
        """
        Ejecuta la tool con los parámetros dados.
        Returns: str (respuesta al usuario) o dict con al menos "response" (str).
        """
        ...
