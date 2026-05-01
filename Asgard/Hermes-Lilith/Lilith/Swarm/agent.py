"""
SwarmAgent - Agente worker en el swarm
========================================
Worker con estados, file tracking, y notificaciones.
"""
import threading
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Set

from Lilith.Swarm.message_bus import Message, MessageBus, MessageType


class AgentStatus(Enum):
    """Estados posibles de un agente."""

    IDLE = "idle"
    WORKING = "working"
    REVIEWING = "reviewing"
    COMPLETE = "complete"
    ERROR = "error"
    STOPPED = "stopped"


@dataclass
class TaskResult:
    """Resultado de una tarea."""

    success: bool
    output: str = ""
    error: Optional[str] = None
    files_modified: List[str] = field(default_factory=list)
    duration_seconds: float = 0.0

    def to_dict(self) -> Dict:
        return {
            "success": self.success,
            "output": self.output,
            "error": self.error,
            "files_modified": self.files_modified,
            "duration_seconds": self.duration_seconds,
        }


class SwarmAgent:
    """Agente worker en el swarm."""

    def __init__(
        self,
        agent_id: str,
        task: str,
        capabilities: List[str],
        context: Dict,
        message_bus: MessageBus,
        file_locks: Dict[str, str],
        executor: Optional[Any] = None,
        use_llm: bool = False,
    ):
        self.id = agent_id
        self.task = task
        self.capabilities = capabilities
        self.context = context
        self.message_bus = message_bus
        self.file_locks = file_locks
        self.executor = executor
        self.use_llm = use_llm

        self.status = AgentStatus.IDLE
        self.files_read: Set[str] = set()
        self.files_written: Set[str] = set()
        self.result: Optional[TaskResult] = None
        self._thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()
        self._lock = threading.RLock()

        # Metricas
        self.started_at: Optional[float] = None
        self.completed_at: Optional[float] = None

    def start(self):
        """Inicia el agente en un thread separado."""
        with self._lock:
            if self.status != AgentStatus.IDLE:
                return False
            self.status = AgentStatus.WORKING
            self.started_at = time.time()
            self._stop_event.clear()

        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()
        return True

    def stop(self):
        """Solicita parada del agente."""
        self._stop_event.set()
        with self._lock:
            self.status = AgentStatus.STOPPED

    def _run(self):
        """Loop principal del agente."""
        try:
            # 1. Leer archivos de contexto
            for file_path in self.context.get("files_to_read", []):
                if self._stop_event.is_set():
                    break
                if self._acquire_lock(file_path):
                    self.files_read.add(file_path)

            if not self._stop_event.is_set():
                # 2. Ejecutar tarea (placeholder - en practica llamaria a tools)
                result = self._execute_task()
                self.result = result

                # 3. Liberar locks
                for f in list(self.files_written):
                    self._release_lock(f)

                # 4. Notificar completado
                with self._lock:
                    if self.status == AgentStatus.STOPPED:
                        # Fue detenido externamente, no cambiar status
                        pass
                    else:
                        self.status = (
                            AgentStatus.COMPLETE
                            if result.success
                            else AgentStatus.ERROR
                        )
                        self.completed_at = time.time()

                self.message_bus.broadcast(
                    from_id=self.id,
                    msg_type=MessageType.TASK_COMPLETE,
                    data={
                        "result": result.to_dict()
                        if hasattr(result, "to_dict")
                        else str(result),
                        "files_modified": list(self.files_written),
                        "duration": self.completed_at - (self.started_at or 0),
                    },
                )

        except Exception as e:
            with self._lock:
                if self.status != AgentStatus.STOPPED:
                    self.status = AgentStatus.ERROR
                    self.result = TaskResult(success=False, error=str(e))
            self.message_bus.broadcast(
                from_id=self.id,
                msg_type=MessageType.ERROR,
                data={"error": str(e)},
            )

    def _execute_task(self) -> TaskResult:
        """Ejecuta la tarea asignada. Usa LLM si esta configurado."""
        start = time.time()

        if self.use_llm and self.executor:
            return self._execute_with_llm(start)
        else:
            return self._execute_simulated(start)

    def _execute_with_llm(self, start: float) -> TaskResult:
        """Ejecuta tarea usando LLM real y tools."""

        def progress_callback(msg: Dict):
            self.message_bus.broadcast(
                from_id=self.id,
                msg_type=MessageType.PROGRESS,
                data=msg,
            )

        try:
            result = self.executor.execute_task(
                task=self.task,
                context=self.context,
                capabilities=self.capabilities,
                stop_event=self._stop_event,
                progress_callback=progress_callback,
            )

            # Actualizar files_written desde el resultado
            for f in result.get("files_modified", []):
                self.files_written.add(f)

            return TaskResult(
                success=result.get("success", False),
                output=result.get("output", ""),
                error=result.get("error"),
                files_modified=result.get("files_modified", []),
                duration_seconds=time.time() - start,
            )
        except Exception as e:
            return TaskResult(
                success=False,
                error=str(e),
                duration_seconds=time.time() - start,
            )

    def _execute_simulated(self, start: float) -> TaskResult:
        """Simulacion de trabajo (para tests y modo offline)."""
        for i in range(5):
            if self._stop_event.is_set():
                return TaskResult(
                    success=False,
                    error="Agent stopped by user",
                    duration_seconds=time.time() - start,
                )
            time.sleep(0.1)

        return TaskResult(
            success=True,
            output=f"Task '{self.task}' completed by {self.id}",
            duration_seconds=time.time() - start,
        )

    def _acquire_lock(self, file_path: str) -> bool:
        """Adquiere lock para un archivo."""
        with self._lock:
            if file_path in self.file_locks:
                return self.file_locks[file_path] == self.id
            self.file_locks[file_path] = self.id
            return True

    def _release_lock(self, file_path: str):
        """Libera lock de un archivo."""
        with self._lock:
            if self.file_locks.get(file_path) == self.id:
                del self.file_locks[file_path]

    def notify_code_shift(self, file_path: str, diff: str):
        """Notifica al agente que codigo cambio bajo sus pies."""
        relevance = self._assess_relevance(file_path, diff)

        if relevance > 0.8:
            with self._lock:
                if self.status == AgentStatus.WORKING:
                    self.status = AgentStatus.REVIEWING

            self.message_bus.send(
                Message(
                    msg_type=MessageType.CODE_SHIFT,
                    from_id="system",
                    to_id=self.id,
                    data={"file": file_path, "diff": diff, "relevance": relevance},
                )
            )
        elif relevance > 0.5:
            self.message_bus.send(
                Message(
                    msg_type=MessageType.CODE_SHIFT_NOTICE,
                    from_id="system",
                    to_id=self.id,
                    data={"file": file_path, "summary": self._summarize_diff(diff)},
                )
            )

    def _assess_relevance(self, file_path: str, diff: str) -> float:
        """Evalua relevancia de un cambio para este agente (0-1)."""
        # Si el agente leyo o escribio el archivo, es muy relevante
        if file_path in self.files_read or file_path in self.files_written:
            return 1.0

        # Si la tarea menciona el archivo
        if file_path.lower() in self.task.lower():
            return 0.9

        # Si las capabilities son relevantes
        for cap in self.capabilities:
            if cap.lower() in file_path.lower():
                return 0.7

        return 0.3

    def _summarize_diff(self, diff: str, max_len: int = 200) -> str:
        """Resume un diff."""
        lines = diff.split("\n")
        added = sum(1 for l in lines if l.startswith("+"))
        removed = sum(1 for l in lines if l.startswith("-"))
        summary = f"+{added}/-{removed} lines"
        if len(diff) > max_len:
            summary += f" | {diff[:max_len]}..."
        else:
            summary += f" | {diff}"
        return summary

    def to_dict(self) -> Dict:
        """Serializa estado del agente."""
        with self._lock:
            return {
                "id": self.id,
                "status": self.status.value,
                "task": self.task,
                "capabilities": self.capabilities,
                "files_read": list(self.files_read),
                "files_written": list(self.files_written),
                "started_at": self.started_at,
                "completed_at": self.completed_at,
                "result": self.result.to_dict() if self.result else None,
            }

    @property
    def is_active(self) -> bool:
        with self._lock:
            return self.status in (AgentStatus.WORKING, AgentStatus.REVIEWING)

    @property
    def is_complete(self) -> bool:
        with self._lock:
            return self.status in (
                AgentStatus.COMPLETE,
                AgentStatus.ERROR,
                AgentStatus.STOPPED,
            )

    @property
    def duration(self) -> float:
        if not self.started_at:
            return 0.0
        end = self.completed_at or time.time()
        return end - self.started_at
