"""
Heimdall Agent - Agente de Vanaheim para búsquedas y recuperación de información.

Especialidad: Búsquedas web, lookup de información, recuperación de datos.
Modelo: GPT-4o-mini + herramientas de búsqueda
"""
import logging
import sys
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from core.json_safe import safe_load

logger = logging.getLogger("vanaheim.heimdall")


class HeimdallAgent:
    """
    Agente Heimdall - Maneja búsquedas y recuperación de información.
    """

    def __init__(self, base_path: Optional[Path] = None):
        self.base_path = base_path or Path(__file__).resolve().parents[4]
        self.config = self._load_config()
        self.name = "heimdall"
        self.specialties = ["search", "retrieval", "information_lookup"]

        self._metrics = {"tasks_completed": 0, "tasks_failed": 0, "total_latency_ms": 0}

        logger.info("[Heimdall] Agente inicializado")

    def _load_config(self) -> Dict[str, Any]:
        """Carga configuración desde sovereign_config.json."""
        config_path = self.base_path / "Config" / "sovereign_config.json"
        try:
            full_config = safe_load(config_path, default={})
            return full_config.get("vanaheim_agents", {}).get("heimdall", {})
        except Exception as e:
            logger.error("[Heimdall] Error cargando config: %s", e)
            return {"enabled": True, "model": "gpt-4o-mini", "max_tokens": 2000}

    def execute_task(
        self,
        task: str,
        complexity_level: Optional[str] = None,
        context: Optional[Dict] = None,
    ) -> str:
        """
        Ejecuta una tarea de búsqueda.

        Args:
            task: Texto de la búsqueda
            complexity_level: Nivel de complejidad
            context: Contexto adicional

        Returns:
            Resultado de la búsqueda
        """
        start_time = time.time()
        context = context or {}

        try:
            task_lower = task.lower()

            # Detectar tipo de búsqueda
            if any(kw in task_lower for kw in ["busca", "search", "encuentra", "find"]):
                response = self._handle_web_search(task, context)

            elif any(kw in task_lower for kw in ["resume", "summarize", "resumen de"]):
                response = self._handle_summary_search(task, context)

            elif any(
                kw in task_lower for kw in ["qué es", "qué son", "define", "what is"]
            ):
                response = self._handle_definition_search(task, context)

            else:
                response = self._handle_generic_search(task, context)

            latency = (time.time() - start_time) * 1000
            self._metrics["tasks_completed"] += 1
            self._metrics["total_latency_ms"] += latency

            logger.debug("[Heimdall] Búsqueda completada en %.2fms", latency)
            return response

        except Exception as e:
            self._metrics["tasks_failed"] += 1
            logger.error("[Heimdall] Error en búsqueda: %s", e)
            return f"[Heimdall] Error en búsqueda: {str(e)}"

    def execute_node(
        self, tool: str, params: Dict[str, Any], context: Dict[str, Any]
    ) -> Any:
        """Ejecuta un nodo DAG."""
        task = params.get("task", "")
        return self.execute_task(task, context=context)

    def _handle_web_search(self, task: str, context: Dict) -> str:
        """Maneja búsquedas web."""
        # TODO: Integrar con herramienta de búsqueda real
        query = self._extract_query(task)
        return (
            f"[Heimdall] Resultados de búsqueda para: '{query}'\n\n"
            f"(Integración con motor de búsqueda pendiente - placeholder)\n\n"
            f"Query extraída: {query}"
        )

    def _handle_summary_search(self, task: str, context: Dict) -> str:
        """Maneja búsquedas con resumen."""
        topic = self._extract_topic(task)
        return (
            f"[Heimdall] Resumen sobre: {topic}\n\n"
            f"(Integración con motor de búsqueda + LLM pendiente)\n\n"
            f"Tema: {topic}"
        )

    def _handle_definition_search(self, task: str, context: Dict) -> str:
        """Maneja búsquedas de definiciones."""
        term = self._extract_topic(task)
        return (
            f"[Heimdall] Definición de '{term}':\n\n"
            f"(Integración con fuente de definiciones pendiente)\n\n"
            f"Término buscado: {term}"
        )

    def _handle_generic_search(self, task: str, context: Dict) -> str:
        """Maneja búsquedas genéricas."""
        return (
            f"[Heimdall] Búsqueda recibida: '{task[:100]}...'\n\n"
            f"(Procesando búsqueda genérica - placeholder)"
        )

    def _extract_query(self, task: str) -> str:
        """Extrae query de búsqueda del texto."""
        # Remover palabras de comando
        prefixes = ["busca", "search for", "find", "buscar", "encuentra"]
        task_lower = task.lower()

        for prefix in prefixes:
            if task_lower.startswith(prefix):
                return task[len(prefix) :].strip(" :\n")

        return task

    def _extract_topic(self, task: str) -> str:
        """Extrae tema del texto."""
        # Remover palabras comunes
        prefixes = [
            "qué es",
            "qué son",
            "define",
            "what is",
            "what are",
            "resume",
            "summarize",
            "resumen de",
            "summary of",
        ]
        task_lower = task.lower()

        for prefix in prefixes:
            if task_lower.startswith(prefix):
                return task[len(prefix) :].strip(" :\n?.")

        return task

    def search_local_knowledge(self, query: str, top_k: int = 3) -> List[Dict]:
        """
        Busca en conocimiento local de Lilith.
        """
        # TODO: Integrar con sistema de memoria semántica
        return [
            {
                "source": "local",
                "content": f"Placeholder result for: {query}",
                "score": 0.95,
            }
        ]

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
_agent_instance: Optional[HeimdallAgent] = None


def get_heimdall_agent() -> HeimdallAgent:
    """Obtiene instancia singleton de HeimdallAgent."""
    global _agent_instance
    if _agent_instance is None:
        _agent_instance = HeimdallAgent()
    return _agent_instance
