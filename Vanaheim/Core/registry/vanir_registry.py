"""Registro dinámico de agentes del Panteón.

Singleton thread-safe que mantiene el estado de todos los agentes
registrados en Vanaheim.
"""

import json
import os
from datetime import datetime
from threading import Lock
from typing import Optional

from Core.models.agent import AgentInfo, AgentState


class VanirRegistry:
    """Registro singleton de agentes en Vanaheim."""

    _instance: Optional["VanirRegistry"] = None
    _lock = Lock()

    def __new__(cls) -> "VanirRegistry":
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._agents: dict[str, AgentInfo] = {}
                    cls._instance._persistence_path = "Config/vanir_registry.json"
        return cls._instance

    def register(self, agent_info: AgentInfo) -> None:
        """Registrar un agente en el registro.

        Args:
            agent_info: Información completa del agente
        """
        with self._lock:
            self._agents[agent_info.agent_id] = agent_info
            self._persist()

    def unregister(self, agent_id: str) -> bool:
        """Eliminar un agente del registro.

        Args:
            agent_id: ID del agente a eliminar

        Returns:
            True si se eliminó, False si no existía
        """
        with self._lock:
            if agent_id in self._agents:
                del self._agents[agent_id]
                self._persist()
                return True
            return False

    def get(self, agent_id: str) -> AgentInfo | None:
        """Obtener información de un agente.

        Args:
            agent_id: ID del agente

        Returns:
            AgentInfo o None si no existe
        """
        return self._agents.get(agent_id)

    def list_all(self) -> list[AgentInfo]:
        """Listar todos los agentes registrados."""
        return list(self._agents.values())

    def list_available(self) -> list[AgentInfo]:
        """Listar agentes disponibles (idle u online)."""
        return [a for a in self._agents.values() if a.state in (AgentState.IDLE, AgentState.BUSY)]

    def update_state(self, agent_id: str, state: AgentState) -> bool:
        """Actualizar estado de un agente.

        Args:
            agent_id: ID del agente
            state: Nuevo estado

        Returns:
            True si se actualizó, False si no existe
        """
        with self._lock:
            if agent_id in self._agents:
                self._agents[agent_id].state = state
                self._agents[agent_id].last_heartbeat = datetime.now().isoformat()
                self._persist()
                return True
            return False

    def update_heartbeat(self, agent_id: str) -> bool:
        """Actualizar heartbeat de un agente.

        Args:
            agent_id: ID del agente

        Returns:
            True si se actualizó, False si no existe
        """
        with self._lock:
            if agent_id in self._agents:
                self._agents[agent_id].last_heartbeat = datetime.now().isoformat()
                return True
            return False

    def get_metrics(self) -> dict:
        """Obtener métricas del registro."""
        total = len(self._agents)
        by_state = {}
        for agent in self._agents.values():
            by_state[agent.state.value] = by_state.get(agent.state.value, 0) + 1

        return {
            "total_agents": total,
            "by_state": by_state,
            "agents": [
                {
                    "agent_id": a.agent_id,
                    "name": a.name,
                    "state": a.state.value,
                    "model": a.config.model,
                }
                for a in self._agents.values()
            ],
        }

    def _persist(self) -> None:
        """Persistir estado a disco."""
        try:
            os.makedirs(os.path.dirname(self._persistence_path), exist_ok=True)
            data = {
                "agents": [json.loads(a.model_dump_json()) for a in self._agents.values()],
                "updated_at": datetime.now().isoformat(),
            }
            with open(self._persistence_path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2)
        except Exception:
            pass  # Fail silently on persistence errors

    def load(self) -> None:
        """Cargar estado desde disco."""
        try:
            if os.path.exists(self._persistence_path):
                # Future: reconstruct AgentInfo from persisted state
                pass
        except Exception:
            pass


def get_registry() -> VanirRegistry:
    """Obtener instancia del registro."""
    return VanirRegistry()
