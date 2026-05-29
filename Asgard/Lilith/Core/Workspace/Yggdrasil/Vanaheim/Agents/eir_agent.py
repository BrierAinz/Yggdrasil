"""
Eir Agent - Agente de Vanaheim para tareas de código ligeras.

Especialidad: Explicaciones de código, refactor menor, debugging simple.
Modelo: Qwen 2.5 Coder (Ollama local)
"""
import logging
import re
import sys
import time
from pathlib import Path
from typing import Any, Dict, Optional

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from core.json_safe import safe_load

logger = logging.getLogger("vanaheim.eir")


class EirAgent:
    """
    Agente Eir - Maneja tareas de código simples.
    """

    def __init__(self, base_path: Optional[Path] = None):
        self.base_path = base_path or Path(__file__).resolve().parents[4]
        self.config = self._load_config()
        self.name = "eir"
        self.specialties = ["code_simple", "explanation", "refactor_minor"]

        self._metrics = {"tasks_completed": 0, "tasks_failed": 0, "total_latency_ms": 0}

        logger.info("[Eir] Agente inicializado")

    def _load_config(self) -> Dict[str, Any]:
        """Carga configuración desde sovereign_config.json."""
        config_path = self.base_path / "Config" / "sovereign_config.json"
        try:
            full_config = safe_load(config_path, default={})
            return full_config.get("vanaheim_agents", {}).get("eir", {})
        except Exception as e:
            logger.error("[Eir] Error cargando config: %s", e)
            return {"enabled": True, "model": "qwen2.5-coder:7b", "max_tokens": 2000}

    def execute_task(
        self,
        task: str,
        complexity_level: Optional[str] = None,
        context: Optional[Dict] = None,
    ) -> str:
        """
        Ejecuta una tarea de código.

        Args:
            task: Texto de la tarea
            complexity_level: Nivel de complejidad
            context: Contexto adicional (puede incluir código)

        Returns:
            Resultado de la tarea
        """
        start_time = time.time()
        context = context or {}

        try:
            task_lower = task.lower()
            code = context.get("code", "")

            # Detectar tipo de tarea
            if any(
                kw in task_lower
                for kw in ["explica", "explain", "qué hace", "what does"]
            ):
                response = self._handle_code_explanation(code or task, context)

            elif any(
                kw in task_lower
                for kw in ["refactor", "mejora", "simplifica", "simplify"]
            ):
                response = self._handle_refactor(code or task, context)

            elif any(kw in task_lower for kw in ["debug", "error", "fix", "arregla"]):
                response = self._handle_debug(code or task, context)

            elif any(
                kw in task_lower for kw in ["ejemplo", "example", "muestra", "sample"]
            ):
                response = self._handle_example(task, context)

            else:
                response = self._handle_generic_code(task, context)

            latency = (time.time() - start_time) * 1000
            self._metrics["tasks_completed"] += 1
            self._metrics["total_latency_ms"] += latency

            logger.debug("[Eir] Tarea completada en %.2fms", latency)
            return response

        except Exception as e:
            self._metrics["tasks_failed"] += 1
            logger.error("[Eir] Error ejecutando tarea: %s", e)
            return f"[Eir] Error: {str(e)}"

    def execute_node(
        self, tool: str, params: Dict[str, Any], context: Dict[str, Any]
    ) -> Any:
        """Ejecuta un nodo DAG."""
        task = params.get("task", "")
        return self.execute_task(task, context=context)

    def _handle_code_explanation(self, code: str, context: Dict) -> str:
        """Explica código proporcionado."""
        if not code:
            return "[Eir] No se proporcionó código para explicar."

        # Limitar tamaño para tareas simples
        if len(code) > 2000:
            code = code[:2000] + "\n... (truncado para análisis simple)"

        return (
            f"[Eir] Análisis del código:\n\n"
            f"```\n{code[:500]}\n```\n\n"
            f"(Integración con Qwen Coder pendiente - análisis detallado)\n\n"
            f"El código tiene aproximadamente {len(code)} caracteres. "
            f"Para análisis más profundo, solicita a Lilith."
        )

    def _handle_refactor(self, code: str, context: Dict) -> str:
        """Refactor simple de código."""
        if not code:
            return "[Eir] No se proporcionó código para refactorizar."

        return (
            f"[Eir] Sugerencias de refactorización:\n\n"
            f"Código original: {len(code)} caracteres\n\n"
            f"(Integración con Qwen Coder pendiente - sugerencias de refactor)\n\n"
            f"Para refactor complejo, solicita a Lilith."
        )

    def _handle_debug(self, code: str, context: Dict) -> str:
        """Debugging simple."""
        error_message = context.get("error", "")

        return (
            f"[Eir] Análisis de error:\n\n"
            f"Error: {error_message or 'No especificado'}\n\n"
            f"(Integración con Qwen Coder pendiente - diagnóstico)\n\n"
            f"Para debugging profundo, solicita a Lilith."
        )

    def _handle_example(self, task: str, context: Dict) -> str:
        """Genera ejemplo de código."""
        # Extraer lenguaje
        languages = ["python", "javascript", "java", "c++", "go", "rust"]
        language = None
        task_lower = task.lower()

        for lang in languages:
            if lang in task_lower:
                language = lang
                break

        lang_str = f" en {language}" if language else ""

        return (
            f"[Eir] Ejemplo de código{lang_str}:\n\n"
            f"```\n# Ejemplo{lang_str}\n"
            f"(Integración con Qwen Coder pendiente - ejemplo)\n"
            f"```\n\n"
            f"Para ejemplos más completos, solicita a Lilith."
        )

    def _handle_generic_code(self, task: str, context: Dict) -> str:
        """Tarea genérica de código."""
        return (
            f"[Eir] Tarea recibida: '{task[:100]}...'\n\n"
            f"(Procesando con Qwen Coder - placeholder)\n\n"
            f"Para tareas complejas de código, solicita a Lilith."
        )

    def get_stats(self) -> Dict[str, Any]:
        """Retorna estadísticas del agente."""
        total = self._metrics["tasks_completed"] + self._metrics["tasks_failed"]
        avg_latency = self._metrics["total_latency_ms"] / total if total > 0 else 0
        return {
            "agent": self.name,
            "tasks_completed": self._metrics["tasks_completed"],
            "tasks_failed": self._metrics["tasks_failed"],
            "avg_latency_ms": avg_latency,
            "specialties": self.specialties,
        }


# Singleton
_agent_instance: Optional[EirAgent] = None


def get_eir_agent() -> EirAgent:
    """Obtiene instancia singleton de EirAgent."""
    global _agent_instance
    if _agent_instance is None:
        _agent_instance = EirAgent()
    return _agent_instance
