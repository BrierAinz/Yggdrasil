"""
SwarmManager - Gestor de agentes multi-agente
===============================================
Orquesta spawn, coordinacion, y resolucion de conflictos.
"""
import asyncio
import threading
import time
from pathlib import Path
from typing import Dict, List, Optional, Set
from uuid import uuid4

from Lilith.Swarm.agent import AgentStatus, SwarmAgent
from Lilith.Swarm.message_bus import MessageBus, MessageType


class ConflictInfo:
    """Informacion de un conflicto detectado."""

    def __init__(self, file_path: str, agent_ids: List[str], diffs: List[str]):
        self.file_path = file_path
        self.agent_ids = agent_ids
        self.diffs = diffs
        self.detected_at = time.time()
        self.resolved = False

    def to_dict(self) -> Dict:
        return {
            "file": self.file_path,
            "agents": self.agent_ids,
            "detected_at": self.detected_at,
            "resolved": self.resolved,
        }


class SwarmManager:
    """Gestiona multiples agentes trabajando en el mismo repo."""

    def __init__(self, repo_path: Optional[Path] = None):
        self.repo = repo_path or Path.cwd()
        self.agents: Dict[str, SwarmAgent] = {}
        self.message_bus = MessageBus()
        self.file_locks: Dict[str, str] = {}  # file -> agent_id
        self.conflicts: List[ConflictInfo] = []
        self._lock = threading.RLock()
        self._coordinator_thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()
        self._running = False

    def spawn_agent(
        self,
        task: str,
        capabilities: Optional[List[str]] = None,
        context: Optional[Dict] = None,
    ) -> str:
        """Spawnea un nuevo agente worker."""
        agent_id = f"agent_{len(self.agents)}_{uuid4().hex[:8]}"

        agent = SwarmAgent(
            agent_id=agent_id,
            task=task,
            capabilities=capabilities or ["coding"],
            context=context or {},
            message_bus=self.message_bus,
            file_locks=self.file_locks,
        )

        with self._lock:
            self.agents[agent_id] = agent

        # Suscribir al bus
        self.message_bus.subscribe(agent_id)

        # Iniciar
        agent.start()
        return agent_id

    def spawn_swarm(
        self,
        task: str,
        num_agents: int = 2,
        capabilities: Optional[List[str]] = None,
    ) -> List[str]:
        """Spawnea multiples agentes para una tarea."""
        agent_ids = []
        for i in range(num_agents):
            ctx = {"parent_task": task, "agent_index": i, "total_agents": num_agents}
            aid = self.spawn_agent(
                task=f"{task} [part {i+1}/{num_agents}]",
                capabilities=capabilities,
                context=ctx,
            )
            agent_ids.append(aid)
        return agent_ids

    def kill_agent(self, agent_id: str) -> bool:
        """Mata un agente."""
        with self._lock:
            agent = self.agents.get(agent_id)
            if not agent:
                return False
            agent.stop()
            self.message_bus.unsubscribe(agent_id)
            # Liberar locks
            for file_path, owner in list(self.file_locks.items()):
                if owner == agent_id:
                    del self.file_locks[file_path]
            return True

    def kill_all(self):
        """Mata todos los agentes."""
        with self._lock:
            for agent in self.agents.values():
                agent.stop()
            self.file_locks.clear()
        self.agents.clear()
        self.message_bus.clear()

    def notify_file_change(self, agent_id: str, file_path: str, diff: str):
        """Notifica a otros agentes cuando un archivo cambia."""
        with self._lock:
            for other_id, other_agent in self.agents.items():
                if other_id != agent_id and other_agent.is_active:
                    other_agent.notify_code_shift(file_path, diff)

    def get_status_report(self) -> Dict:
        """Reporte de estado del swarm."""
        with self._lock:
            agents_data = []
            for agent in self.agents.values():
                agents_data.append(agent.to_dict())

            active = sum(1 for a in self.agents.values() if a.is_active)
            complete = sum(1 for a in self.agents.values() if a.is_complete)

            return {
                "total_agents": len(self.agents),
                "active": active,
                "complete": complete,
                "errors": sum(
                    1 for a in self.agents.values() if a.status == AgentStatus.ERROR
                ),
                "file_locks": dict(self.file_locks),
                "pending_messages": self.message_bus.size,
                "agents": agents_data,
                "conflicts": [c.to_dict() for c in self.conflicts if not c.resolved],
            }

    def get_agent_results(self, agent_id: str) -> Optional[Dict]:
        """Obtiene resultado de un agente."""
        with self._lock:
            agent = self.agents.get(agent_id)
            if not agent:
                return None
            return {
                "id": agent.id,
                "status": agent.status.value,
                "result": agent.result.to_dict() if agent.result else None,
                "duration": agent.duration,
            }

    def wait_for_completion(
        self, agent_ids: Optional[List[str]] = None, timeout: float = 30.0
    ) -> bool:
        """Espera a que agentes completen."""
        start = time.time()
        ids = set(agent_ids or list(self.agents.keys()))

        while time.time() - start < timeout:
            with self._lock:
                done = all(
                    self.agents.get(
                        aid, SwarmAgent("", "", [], {}, self.message_bus, {})
                    ).is_complete
                    for aid in ids
                )
            if done:
                return True
            time.sleep(0.5)

        return False

    def start_coordinator(self):
        """Inicia thread de coordinacion."""
        if self._running:
            return
        self._running = True
        self._stop_event.clear()
        self._coordinator_thread = threading.Thread(
            target=self._coordinate_loop, daemon=True
        )
        self._coordinator_thread.start()

    def stop_coordinator(self):
        """Detiene coordinador."""
        self._running = False
        self._stop_event.set()
        if self._coordinator_thread:
            self._coordinator_thread.join(timeout=2)

    def _coordinate_loop(self):
        """Loop principal de coordinacion."""
        while not self._stop_event.is_set():
            # 1. Procesar mensajes
            self._process_messages()

            # 2. Detectar conflictos
            self._detect_conflicts()

            # 3. Limpiar agentes completados
            self._cleanup_agents()

            time.sleep(1.0)

    def _process_messages(self):
        """Procesa mensajes del bus."""
        msgs = self.message_bus.get_all_messages(clear=True)
        for msg in msgs:
            if msg.msg_type == MessageType.LOCK_REQUEST:
                # Procesar request de lock
                file_path = msg.data.get("file")
                agent_id = msg.from_id
                if file_path:
                    with self._lock:
                        if file_path not in self.file_locks:
                            self.file_locks[file_path] = agent_id
            elif msg.msg_type == MessageType.LOCK_RELEASE:
                file_path = msg.data.get("file")
                if file_path:
                    with self._lock:
                        if self.file_locks.get(file_path) == msg.from_id:
                            del self.file_locks[file_path]

    def _detect_conflicts(self):
        """Detecta conflictos entre agentes."""
        with self._lock:
            # Archivos escritos por multiples agentes
            file_writers: Dict[str, List[str]] = {}
            for agent_id, agent in self.agents.items():
                if agent.is_complete:
                    for f in agent.files_written:
                        if f not in file_writers:
                            file_writers[f] = []
                        file_writers[f].append(agent_id)

            for file_path, writers in file_writers.items():
                if len(writers) > 1:
                    # Conflicto detectado
                    conflict = ConflictInfo(
                        file_path=file_path,
                        agent_ids=writers,
                        diffs=[],  # Se llenarian con diffs reales
                    )
                    self.conflicts.append(conflict)

    def _cleanup_agents(self):
        """Limpia agentes completados."""
        with self._lock:
            to_remove = [
                aid
                for aid, agent in self.agents.items()
                if agent.is_complete
                and agent.completed_at
                and time.time() - agent.completed_at > 60
            ]
            for aid in to_remove:
                del self.agents[aid]


# Instancia global
_swarm_manager: Optional[SwarmManager] = None


def get_swarm_manager(repo_path: Optional[Path] = None) -> SwarmManager:
    """Obtiene instancia global del swarm manager."""
    global _swarm_manager
    if _swarm_manager is None:
        _swarm_manager = SwarmManager(repo_path)
    return _swarm_manager
