"""
Tool de delegación al Archivero - Agente especialista en documentación.
Consulta la Knowledge Base en Svartalfheim (vault "docs").
"""
# Path para imports
import sys
from pathlib import Path
from typing import Any, Dict

from .protocol import LilithTool, ToolResult

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from agents.archivero_agent import ArchiveroAgent


class DelegateArchiveroTool(LilithTool):
    """
    Delega al Archivero: especialista en documentación técnica de Yggdrasil.

    Usa esta tool cuando:
    - Necesitas información sobre arquitectura de Lilith
    - Quieres entender cómo funciona un sistema/componente
    - Buscas decisiones históricas o patrones usados
    - Necesitas documentación de APIs, tools, o agentes
    - Quieres saber "¿dónde está documentado X?"

    El Archivero consulta la Knowledge Base en MuninnDB (vault "docs")
    que contiene ~1.1 MB de documentación organizada:
    - Docs actuales (00-17): arquitectura actual
    - Legacy: documentación histórica
    - El Inicio del Todo: historia del proyecto (docs 18-21)
    """

    def __init__(self):
        self._agent: ArchiveroAgent = None

    @property
    def name(self) -> str:
        return "delegate_archivero"

    def get_description(self) -> str:
        return (
            "Consulta al Archivero (Svartalfheim) para preguntas sobre "
            "documentación técnica, arquitectura, decisiones de diseño, "
            "o historia del ecosistema Lilith. "
            "Usar para: '¿Cómo funciona X?', '¿Dónde está documentado Y?', "
            "'¿Qué es el DAG Executor?', 'Historia del proyecto', etc."
        )

    def get_parameters_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "question": {
                    "type": "string",
                    "description": (
                        "Pregunta sobre documentación o arquitectura. "
                        "Ejemplos: '¿Cómo funciona el DAG Executor?', "
                        "'Explica el sistema de memoria', "
                        "'¿Qué es MuninnDB?', "
                        "'Historia de Cortana a Lilith'"
                    ),
                },
                "context": {
                    "type": "string",
                    "description": "Contexto adicional opcional para enriquecer la búsqueda.",
                    "default": "",
                },
            },
            "required": ["question"],
        }

    def execute(self, params: Dict[str, Any]) -> ToolResult:
        """Ejecuta consulta al Archivero."""
        question = (params.get("question") or "").strip()
        context = params.get("context", "")

        if not question:
            return ToolResult(
                response="", error="Se requiere 'question' para consultar al Archivero"
            )

        # Inicializar agente lazy
        if self._agent is None:
            try:
                self._agent = ArchiveroAgent()
            except Exception as e:
                return ToolResult(
                    response="", error=f"[Archivero] Error inicializando agente: {e}"
                )

        # Ejecutar async
        import asyncio

        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            loop = None

        async def _execute() -> str:
            result = await self._agent.execute(task=question, context=context)
            return result

        try:
            if loop is None:
                result_text = asyncio.run(_execute())
            else:
                # Ya estamos en async context
                import concurrent.futures

                with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
                    future = pool.submit(asyncio.run, _execute())
                    result_text = future.result(timeout=60)

            return ToolResult(response=result_text)

        except Exception as e:
            return ToolResult(
                response="", error=f"[Archivero] Error ejecutando consulta: {e}"
            )


# Instancia singleton
ARCHIVERO_TOOL = DelegateArchiveroTool()
