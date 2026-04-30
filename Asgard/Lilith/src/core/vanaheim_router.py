"""
Vanaheim Router - Selecciona el agente de Vanaheim más adecuado para cada tarea.

Features:
- Routing basado en especialidades
- Fallback inteligente
- Métricas de routing
"""
import logging
import re
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from .json_safe import safe_load

logger = logging.getLogger("lilith.vanaheim_router")


class VanaheimRouter:
    """
    Router que selecciona el mejor agente de Vanaheim para una tarea.
    """

    # Mapeo de agentes a sus especialidades
    AGENT_SPECIALTIES = {
        "freya": {
            "keywords": [
                "hola",
                "gracias",
                "adiós",
                "bye",
                "saludos",
                "greeting",
                "conversation",
                "chat",
            ],
            "task_types": ["conversation", "simple_qa", "greetings"],
            "score_weight": 1.0,
        },
        "heimdall": {
            "keywords": [
                "busca",
                "search",
                "encuentra",
                "find",
                "lookup",
                "information",
                "info",
            ],
            "task_types": ["search", "retrieval", "information_lookup"],
            "score_weight": 1.0,
        },
        "eir": {
            "keywords": [
                "código",
                "code",
                "programa",
                "programming",
                "debug",
                "refactor",
                "function",
            ],
            "task_types": ["code_simple", "explanation", "refactor_minor"],
            "score_weight": 1.0,
        },
        "balder": {
            "keywords": [
                "documento",
                "document",
                "resume",
                "summarize",
                "analiza",
                "analyze",
                "texto",
            ],
            "task_types": ["document_analysis", "summarization", "extraction"],
            "score_weight": 1.0,
        },
    }

    def __init__(self, base_path: Optional[Path] = None):
        self.base_path = (
            Path(base_path) if base_path else Path(__file__).resolve().parents[2]
        )
        self.config = self._load_config()

        # Cargar agentes habilitados
        vanaheim_config = self.config.get("vanaheim_agents", {})
        self.enabled_agents = [
            name for name, cfg in vanaheim_config.items() if cfg.get("enabled", True)
        ]

        # Métricas
        self._routing_stats = {
            "total_routings": 0,
            "agent_selections": {agent: 0 for agent in self.AGENT_SPECIALTIES.keys()},
        }

        logger.info(
            "[VanaheimRouter] Inicializado. Agentes habilitados: %s",
            self.enabled_agents,
        )

    def _load_config(self) -> Dict[str, Any]:
        """Carga configuración desde sovereign_config.json."""
        config_path = self.base_path / "Config" / "sovereign_config.json"
        try:
            return safe_load(config_path, default={})
        except Exception as e:
            logger.error("[VanaheimRouter] Error cargando config: %s", e)
            return {}

    def select_agent(
        self,
        task: str,
        complexity_level: Optional[str] = None,
        preferred_agent: Optional[str] = None,
    ) -> Tuple[str, float]:
        """
        Selecciona el mejor agente para la tarea.

        Args:
            task: Descripción de la tarea
            complexity_level: Nivel de complejidad (trivial, simple, etc.)
            preferred_agent: Agente preferido si se conoce

        Returns:
            Tuple de (agent_name, confidence_score)
        """
        self._routing_stats["total_routings"] += 1

        # Si hay agente preferido y está habilitado, usarlo
        if preferred_agent and preferred_agent in self.enabled_agents:
            self._routing_stats["agent_selections"][preferred_agent] += 1
            return preferred_agent, 1.0

        # Calcular scores para cada agente
        scores = self._calculate_scores(task)

        # Filtrar solo agentes habilitados
        scores = {k: v for k, v in scores.items() if k in self.enabled_agents}

        if not scores:
            # Fallback a freya si nada más está disponible
            logger.warning(
                "[VanaheimRouter] No hay agentes habilitados, usando fallback"
            )
            return "freya", 0.5

        # Seleccionar agente con mayor score
        best_agent = max(scores, key=scores.get)
        best_score = scores[best_agent]

        self._routing_stats["agent_selections"][best_agent] += 1

        logger.debug(
            "[VanaheimRouter] Seleccionado %s con score %.2f", best_agent, best_score
        )
        return best_agent, best_score

    def _calculate_scores(self, task: str) -> Dict[str, float]:
        """Calcula scores de matching para cada agente."""
        task_lower = task.lower()
        scores = {}

        for agent, specialties in self.AGENT_SPECIALTIES.items():
            score = 0.0

            # Score por keywords
            for keyword in specialties["keywords"]:
                if keyword in task_lower:
                    score += 1.0

            # Bonus por múltiples matches
            keyword_matches = sum(
                1 for kw in specialties["keywords"] if kw in task_lower
            )
            if keyword_matches >= 2:
                score += 0.5

            # Aplicar peso
            score *= specialties.get("score_weight", 1.0)

            scores[agent] = score

        return scores

    def get_agent_for_tool(self, tool_name: str) -> str:
        """
        Obtiene el agente recomendado para un tool específico.

        Args:
            tool_name: Nombre del tool

        Returns:
            Nombre del agente
        """
        # Mapeo de tools a agentes
        tool_mappings = {
            "web_search": "heimdall",
            "search": "heimdall",
            "generate_reply": "freya",
            "delegate_freya": "freya",
            "delegate_heimdall": "heimdall",
            "delegate_eir": "eir",
            "delegate_balder": "balder",
        }

        return tool_mappings.get(tool_name, "freya")

    def get_available_agents(self) -> List[str]:
        """Retorna lista de agentes disponibles."""
        return self.enabled_agents.copy()

    def get_agent_info(self, agent_name: str) -> Optional[Dict[str, Any]]:
        """Retorna información de un agente."""
        if agent_name not in self.AGENT_SPECIALTIES:
            return None

        specialties = self.AGENT_SPECIALTIES[agent_name]
        return {
            "name": agent_name,
            "enabled": agent_name in self.enabled_agents,
            "specialties": specialties["task_types"],
            "keywords": specialties["keywords"],
        }

    def get_stats(self) -> Dict[str, Any]:
        """Retorna estadísticas de routing."""
        total = self._routing_stats["total_routings"]
        selections = self._routing_stats["agent_selections"]

        distribution = {}
        if total > 0:
            distribution = {
                agent: (count / total * 100) for agent, count in selections.items()
            }

        return {
            "total_routings": total,
            "agent_distribution": distribution,
            "enabled_agents": self.enabled_agents,
        }

    def force_agent(self, agent_name: str) -> bool:
        """
        Verifica si un agente puede ser forzado para una tarea.
        Retorna True si el agente está habilitado.
        """
        return agent_name in self.enabled_agents


# Singleton
_router_instance: Optional[VanaheimRouter] = None


def get_vanaheim_router(base_path: Optional[Path] = None) -> VanaheimRouter:
    """Obtiene instancia singleton del router."""
    global _router_instance
    if _router_instance is None:
        _router_instance = VanaheimRouter(base_path)
    return _router_instance


def select_agent(
    task: str,
    complexity_level: Optional[str] = None,
    preferred_agent: Optional[str] = None,
) -> Tuple[str, float]:
    """Función conveniencia para seleccionar agente."""
    router = get_vanaheim_router()
    return router.select_agent(task, complexity_level, preferred_agent)


__all__ = ["VanaheimRouter", "get_vanaheim_router", "select_agent"]
