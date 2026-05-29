"""
Freya Agent - Agente de Vanaheim para tareas conversacionales simples.

Especialidad: Saludos, preguntas simples, conversación casual, FAQs.
Modelo: GPT-4o-mini (rápido y económico)
"""
import logging

# Ajustar path para importar desde Lilith Core
import sys
import time
from pathlib import Path
from typing import Any, Dict, Optional

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from core.json_safe import safe_load

logger = logging.getLogger("vanaheim.freya")


class FreyaAgent:
    """
    Agente Freya - Maneja tareas conversacionales simples.
    No requiere DAG ni orquestación compleja.
    """

    def __init__(self, base_path: Optional[Path] = None):
        self.base_path = base_path or Path(__file__).resolve().parents[4]
        self.config = self._load_config()
        self.name = "freya"
        self.specialties = ["conversation", "simple_qa", "greetings"]

        # Métricas
        self._metrics = {"tasks_completed": 0, "tasks_failed": 0, "total_latency_ms": 0}

        logger.info("[Freya] Agente inicializado")

    def _load_config(self) -> Dict[str, Any]:
        """Carga configuración desde sovereign_config.json."""
        config_path = self.base_path / "Config" / "sovereign_config.json"
        try:
            full_config = safe_load(config_path, default={})
            return full_config.get("vanaheim_agents", {}).get("freya", {})
        except Exception as e:
            logger.error("[Freya] Error cargando config: %s", e)
            return {"enabled": True, "model": "gpt-4o-mini", "max_tokens": 1000}

    def execute_task(
        self,
        task: str,
        complexity_level: Optional[str] = None,
        context: Optional[Dict] = None,
    ) -> str:
        """
        Ejecuta una tarea conversacional.

        Args:
            task: Texto de la tarea/pregunta
            complexity_level: Nivel de complejidad (para logging)
            context: Contexto adicional

        Returns:
            Respuesta en string
        """
        start_time = time.time()
        context = context or {}

        try:
            # Detectar tipo de tarea conversacional
            task_lower = task.lower().strip()

            # Saludos
            if any(
                greeting in task_lower
                for greeting in ["hola", "buenos días", "buenas tardes", "hello", "hi"]
            ):
                response = self._handle_greeting(task_lower)

            # Agradecimientos
            elif any(
                thanks in task_lower for thanks in ["gracias", "thanks", "agradecido"]
            ):
                response = self._handle_thanks()

            # Despedidas
            elif any(
                bye in task_lower for bye in ["adiós", "chao", "bye", "hasta luego"]
            ):
                response = self._handle_goodbye()

            # Confirmaciones simples
            elif task_lower in ["sí", "no", "ok", "vale", "perfecto", "confirmo"]:
                response = self._handle_confirmation(task_lower)

            # Preguntas simples sobre Lilith
            elif any(
                q in task_lower
                for q in ["quién eres", "qué eres", "quién es lilith", "what are you"]
            ):
                response = self._handle_identity()

            # Preguntas de hora/fecha
            elif any(
                q in task_lower for q in ["qué hora es", "qué día es", "qué fecha es"]
            ):
                response = self._handle_datetime(task_lower)

            # Fallback: respuesta conversacional simple
            else:
                response = self._handle_conversational(task, context)

            # Registrar métricas
            latency = (time.time() - start_time) * 1000
            self._metrics["tasks_completed"] += 1
            self._metrics["total_latency_ms"] += latency

            logger.debug("[Freya] Tarea completada en %.2fms", latency)
            return response

        except Exception as e:
            self._metrics["tasks_failed"] += 1
            logger.error("[Freya] Error ejecutando tarea: %s", e)
            return f"[Freya] Lo siento, no pude procesar tu mensaje. Error: {str(e)}"

    def execute_node(
        self, tool: str, params: Dict[str, Any], context: Dict[str, Any]
    ) -> Any:
        """
        Ejecuta un nodo DAG (para compatibilidad con Bifrost).
        Freya normalmente no ejecuta nodos DAG, pero implementa la interfaz.
        """
        task = params.get("task", "")
        return self.execute_task(task, context=context)

    def _handle_greeting(self, task: str) -> str:
        """Maneja saludos."""
        import random

        greetings = [
            "¡Hola! ¿En qué puedo ayudarte hoy?",
            "¡Buenas! Estoy aquí para asistirte.",
            "¡Hola! ¿Qué necesitas?",
            "Saludos. ¿Cómo puedo ser útil?",
        ]
        return random.choice(greetings)

    def _handle_thanks(self) -> str:
        """Maneja agradecimientos."""
        import random

        responses = [
            "¡De nada! Estoy aquí para lo que necesites.",
            "Con gusto. ¿Algo más en lo que pueda ayudar?",
            "No hay de qué. ¿Necesitas algo más?",
            "Es un placer ayudar.",
        ]
        return random.choice(responses)

    def _handle_goodbye(self) -> str:
        """Maneja despedidas."""
        import random

        responses = [
            "¡Hasta luego! Que tengas un buen día.",
            "Adiós. Estaré aquí cuando me necesites.",
            "Nos vemos. ¡Cuídate!",
            "Hasta la próxima.",
        ]
        return random.choice(responses)

    def _handle_confirmation(self, task: str) -> str:
        """Maneja confirmaciones simples."""
        if task in ["sí", "yes", "ok", "vale", "perfecto"]:
            return "Entendido. Procediendo."
        else:
            return "Entendido. Cancelado."

    def _handle_identity(self) -> str:
        """Maneja preguntas sobre identidad."""
        return (
            "Soy Freya, agente de Vanaheim. Manejo tareas conversacionales simples "
            "mientras la Soberana Lilith atiende asuntos más complejos. "
            "¿En qué puedo ayudarte?"
        )

    def _handle_datetime(self, task: str) -> str:
        """Maneja preguntas de hora/fecha."""
        from datetime import datetime

        now = datetime.now()

        if "hora" in task:
            return f"Son las {now.strftime('%H:%M')}"
        elif "día" in task or "fecha" in task:
            return f"Hoy es {now.strftime('%d de %B de %Y')}"
        else:
            return (
                f"Son las {now.strftime('%H:%M')} del {now.strftime('%d de %B de %Y')}"
            )

    def _handle_conversational(self, task: str, context: Dict) -> str:
        """
        Maneja conversación general simple.
        En producción, esto llamaría a GPT-4o-mini.
        Por ahora, respuestas simples.
        """
        # TODO: Integrar con LLM real (GPT-4o-mini)
        return (
            f"[Freya] He recibido tu mensaje: '{task[:50]}...' "
            f"(Integración con LLM pendiente - respuesta de placeholder)"
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


# Singleton para uso directo
_agent_instance: Optional[FreyaAgent] = None


def get_freya_agent() -> FreyaAgent:
    """Obtiene instancia singleton de FreyaAgent."""
    global _agent_instance
    if _agent_instance is None:
        _agent_instance = FreyaAgent()
    return _agent_instance
