"""
Balder Agent - Agente de Vanaheim para análisis de documentos y resúmenes.

Especialidad: Análisis de documentos, resúmenes, extracción de información.
Modelo: GPT-4o-mini
"""
import logging
import sys
import time
from pathlib import Path
from typing import Any, Dict, Optional

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from core.json_safe import safe_load

logger = logging.getLogger("vanaheim.balder")


class BalderAgent:
    """
    Agente Balder - Maneja análisis de documentos y resúmenes.
    """

    def __init__(self, base_path: Optional[Path] = None):
        self.base_path = base_path or Path(__file__).resolve().parents[4]
        self.config = self._load_config()
        self.name = "balder"
        self.specialties = ["document_analysis", "summarization", "extraction"]

        self._metrics = {"tasks_completed": 0, "tasks_failed": 0, "total_latency_ms": 0}

        logger.info("[Balder] Agente inicializado")

    def _load_config(self) -> Dict[str, Any]:
        """Carga configuración desde sovereign_config.json."""
        config_path = self.base_path / "Config" / "sovereign_config.json"
        try:
            full_config = safe_load(config_path, default={})
            return full_config.get("vanaheim_agents", {}).get("balder", {})
        except Exception as e:
            logger.error("[Balder] Error cargando config: %s", e)
            return {"enabled": True, "model": "gpt-4o-mini", "max_tokens": 3000}

    def execute_task(
        self,
        task: str,
        complexity_level: Optional[str] = None,
        context: Optional[Dict] = None,
    ) -> str:
        """
        Ejecuta una tarea de análisis de documento.

        Args:
            task: Texto de la tarea
            complexity_level: Nivel de complejidad
            context: Contexto adicional (puede incluir documento)

        Returns:
            Resultado del análisis
        """
        start_time = time.time()
        context = context or {}

        try:
            task_lower = task.lower()
            document = context.get("document", "")

            # Detectar tipo de tarea
            if any(kw in task_lower for kw in ["resume", "summarize", "resumen"]):
                response = self._handle_summary(document or task, context)

            elif any(kw in task_lower for kw in ["extrae", "extract", "saca"]):
                response = self._handle_extraction(document or task, context)

            elif any(kw in task_lower for kw in ["analiza", "analyze"]):
                response = self._handle_analysis(document or task, context)

            elif any(kw in task_lower for kw in ["traduce", "translate"]):
                response = self._handle_translation(document or task, context)

            else:
                response = self._handle_generic_document(task, context)

            latency = (time.time() - start_time) * 1000
            self._metrics["tasks_completed"] += 1
            self._metrics["total_latency_ms"] += latency

            logger.debug("[Balder] Tarea completada en %.2fms", latency)
            return response

        except Exception as e:
            self._metrics["tasks_failed"] += 1
            logger.error("[Balder] Error ejecutando tarea: %s", e)
            return f"[Balder] Error: {str(e)}"

    def execute_node(
        self, tool: str, params: Dict[str, Any], context: Dict[str, Any]
    ) -> Any:
        """Ejecuta un nodo DAG."""
        task = params.get("task", "")
        return self.execute_task(task, context=context)

    def _handle_summary(self, document: str, context: Dict) -> str:
        """Genera resumen de documento."""
        max_length = context.get("max_length", 200)

        if not document:
            return "[Balder] No se proporcionó documento para resumir."

        # Limitar para tareas simples
        if len(document) > 5000:
            document = document[:5000] + "\n... (truncado para resumen simple)"

        return (
            f"[Balder] Resumen del documento:\n\n"
            f"Longitud original: {len(document)} caracteres\n"
            f"Longitud máxima solicitada: {max_length} palabras\n\n"
            f"(Integración con LLM pendiente - resumen generado)\n\n"
            f"Para análisis más profundo del documento, solicita a Lilith."
        )

    def _handle_extraction(self, document: str, context: Dict) -> str:
        """Extrae información específica."""
        extraction_type = context.get("extraction_type", "key_points")

        return (
            f"[Balder] Extracción ({extraction_type}):\n\n"
            f"(Integración con LLM pendiente - extracción)\n\n"
            f"Para extracción compleja, solicita a Lilith."
        )

    def _handle_analysis(self, document: str, context: Dict) -> str:
        """Analiza documento."""
        analysis_type = context.get("analysis_type", "general")

        return (
            f"[Balder] Análisis ({analysis_type}):\n\n"
            f"(Integración con LLM pendiente - análisis)\n\n"
            f"Para análisis detallado, solicita a Lilith."
        )

    def _handle_translation(self, document: str, context: Dict) -> str:
        """Traduce documento."""
        target_lang = context.get("target_language", "es")

        return (
            f"[Balder] Traducción ({target_lang}):\n\n"
            f"(Integración con LLM pendiente - traducción)\n\n"
            f"Para traducción profesional, solicita a Lilith."
        )

    def _handle_generic_document(self, task: str, context: Dict) -> str:
        """Tarea genérica de documento."""
        return (
            f"[Balder] Tarea recibida: '{task[:100]}...'\n\n"
            f"(Procesando documento - placeholder)\n\n"
            f"Para análisis complejo de documentos, solicita a Lilith."
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
_agent_instance: Optional[BalderAgent] = None


def get_balder_agent() -> BalderAgent:
    """Obtiene instancia singleton de BalderAgent."""
    global _agent_instance
    if _agent_instance is None:
        _agent_instance = BalderAgent()
    return _agent_instance
