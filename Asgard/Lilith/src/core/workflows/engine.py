"""
Workflows - Motor de ejecución

v4.2.8: Motor de ejecución DAG para workflows
"""
import asyncio
import json
import logging
import secrets
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Set

from src.core.json_safe import safe_load

from .nodes import NodeType, WorkflowNode, create_node

logger = logging.getLogger("lilith.workflows.engine")


class WorkflowStatus(Enum):
    """Estados de un workflow."""

    DRAFT = "draft"
    ACTIVE = "active"
    PAUSED = "paused"
    DISABLED = "disabled"


class ExecutionStatus(Enum):
    """Estados de ejecución."""

    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class Workflow:
    """Workflow con nodos y configuración."""

    id: str
    name: str
    description: str
    status: WorkflowStatus
    nodes: List[WorkflowNode] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)
    metadata: Dict[str, Any] = field(default_factory=dict)
    trigger_config: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "status": self.status.value,
            "nodes": [n.to_dict() for n in self.nodes],
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "metadata": self.metadata,
            "trigger_config": self.trigger_config,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Workflow":
        return cls(
            id=data["id"],
            name=data["name"],
            description=data.get("description", ""),
            status=WorkflowStatus(data.get("status", "draft")),
            nodes=[create_node(n) for n in data.get("nodes", [])],
            created_at=datetime.fromisoformat(data["created_at"])
            if "created_at" in data
            else datetime.utcnow(),
            updated_at=datetime.fromisoformat(data["updated_at"])
            if "updated_at" in data
            else datetime.utcnow(),
            metadata=data.get("metadata", {}),
            trigger_config=data.get("trigger_config", {}),
        )

    def get_node(self, node_id: str) -> Optional[WorkflowNode]:
        """Obtiene un nodo por ID."""
        for node in self.nodes:
            if node.id == node_id:
                return node
        return None

    def get_trigger_nodes(self) -> List[WorkflowNode]:
        """Obtiene todos los nodos trigger."""
        return [n for n in self.nodes if n.type == NodeType.TRIGGER]


@dataclass
class NodeExecution:
    """Resultado de ejecución de un nodo."""

    node_id: str
    status: ExecutionStatus
    started_at: datetime
    finished_at: Optional[datetime] = None
    output: Any = None
    error: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "node_id": self.node_id,
            "status": self.status.value,
            "started_at": self.started_at.isoformat(),
            "finished_at": self.finished_at.isoformat() if self.finished_at else None,
            "output": self.output,
            "error": self.error,
        }


@dataclass
class WorkflowExecution:
    """Ejecución completa de un workflow."""

    id: str
    workflow_id: str
    status: ExecutionStatus
    started_at: datetime
    finished_at: Optional[datetime] = None
    context: Dict[str, Any] = field(default_factory=dict)
    node_executions: Dict[str, NodeExecution] = field(default_factory=dict)
    current_nodes: List[str] = field(default_factory=list)
    error: Optional[str] = None
    triggered_by: str = "manual"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "workflow_id": self.workflow_id,
            "status": self.status.value,
            "started_at": self.started_at.isoformat(),
            "finished_at": self.finished_at.isoformat() if self.finished_at else None,
            "context": self.context,
            "node_executions": {
                k: v.to_dict() for k, v in self.node_executions.items()
            },
            "current_nodes": self.current_nodes,
            "error": self.error,
            "triggered_by": self.triggered_by,
        }


class WorkflowEngine:
    """
    Motor de ejecución de workflows.

    Features:
    - Ejecución DAG con manejo de dependencias
    - Paralelización de nodos independientes
    - Persistencia de ejecuciones
    - Manejo de errores y reintentos
    """

    def __init__(self, base_path: Optional[Path] = None):
        self.base_path = (
            Path(base_path) if base_path else Path(__file__).resolve().parents[3]
        )
        self.workflows_path = self.base_path / "Config" / "workflows.json"
        self.executions_path = self.base_path / "Config" / "workflow_executions.json"

        self._workflows: Dict[str, Workflow] = {}
        self._executions: Dict[str, WorkflowExecution] = {}
        self._running_executions: Set[str] = set()

        self._load_data()

        logger.info(f"WorkflowEngine: Cargados {len(self._workflows)} workflows")

    def _load_data(self):
        """Carga workflows y ejecuciones."""
        # Cargar workflows
        data = safe_load(self.workflows_path, default={"workflows": []})
        for wf_data in data.get("workflows", []):
            try:
                workflow = Workflow.from_dict(wf_data)
                self._workflows[workflow.id] = workflow
            except Exception as e:
                logger.warning(f"Error cargando workflow: {e}")

        # Cargar ejecuciones (solo las recientes)
        exec_data = safe_load(self.executions_path, default={"executions": []})
        for ex_data in exec_data.get("executions", [])[-100:]:  # Últimas 100
            try:
                execution = WorkflowExecution(
                    id=ex_data["id"],
                    workflow_id=ex_data["workflow_id"],
                    status=ExecutionStatus(ex_data.get("status", "completed")),
                    started_at=datetime.fromisoformat(ex_data["started_at"]),
                    finished_at=datetime.fromisoformat(ex_data["finished_at"])
                    if ex_data.get("finished_at")
                    else None,
                    context=ex_data.get("context", {}),
                    node_executions={
                        k: NodeExecution(
                            node_id=v["node_id"],
                            status=ExecutionStatus(v["status"]),
                            started_at=datetime.fromisoformat(v["started_at"]),
                            finished_at=datetime.fromisoformat(v["finished_at"])
                            if v.get("finished_at")
                            else None,
                            output=v.get("output"),
                            error=v.get("error"),
                        )
                        for k, v in ex_data.get("node_executions", {}).items()
                    },
                    triggered_by=ex_data.get("triggered_by", "manual"),
                )
                self._executions[execution.id] = execution
            except Exception as e:
                logger.warning(f"Error cargando ejecución: {e}")

    def _save_workflows(self):
        """Guarda workflows en disco."""
        data = {
            "workflows": [w.to_dict() for w in self._workflows.values()],
            "updated_at": datetime.utcnow().isoformat(),
        }
        try:
            self.workflows_path.parent.mkdir(parents=True, exist_ok=True)
            with open(self.workflows_path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
        except Exception as e:
            logger.error(f"Error guardando workflows: {e}")

    def _save_executions(self):
        """Guarda ejecuciones en disco (solo las últimas 200)."""
        # Ordenar por fecha y mantener las últimas 200
        sorted_execs = sorted(
            self._executions.values(), key=lambda x: x.started_at, reverse=True
        )[:200]

        data = {
            "executions": [e.to_dict() for e in sorted_execs],
            "updated_at": datetime.utcnow().isoformat(),
        }
        try:
            self.executions_path.parent.mkdir(parents=True, exist_ok=True)
            with open(self.executions_path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
        except Exception as e:
            logger.error(f"Error guardando ejecuciones: {e}")

    # CRUD Workflows

    def create_workflow(
        self,
        name: str,
        description: str = "",
        nodes: Optional[List[Dict]] = None,
        trigger_config: Optional[Dict] = None,
    ) -> Workflow:
        """Crea un nuevo workflow."""
        workflow = Workflow(
            id=secrets.token_hex(8),
            name=name,
            description=description,
            status=WorkflowStatus.DRAFT,
            nodes=[create_node(n) for n in (nodes or [])],
            trigger_config=trigger_config or {},
        )

        self._workflows[workflow.id] = workflow
        self._save_workflows()

        logger.info(f"Workflow creado: {workflow.id}")
        return workflow

    def get_workflow(self, workflow_id: str) -> Optional[Workflow]:
        """Obtiene un workflow por ID."""
        return self._workflows.get(workflow_id)

    def list_workflows(self) -> List[Workflow]:
        """Lista todos los workflows."""
        return list(self._workflows.values())

    def update_workflow(self, workflow_id: str, **kwargs) -> Optional[Workflow]:
        """Actualiza un workflow."""
        workflow = self._workflows.get(workflow_id)
        if not workflow:
            return None

        allowed = {
            "name",
            "description",
            "status",
            "nodes",
            "trigger_config",
            "metadata",
        }
        for key, value in kwargs.items():
            if key in allowed:
                if key == "status" and isinstance(value, str):
                    value = WorkflowStatus(value)
                elif key == "nodes" and isinstance(value, list):
                    value = [create_node(n) for n in value]
                setattr(workflow, key, value)

        workflow.updated_at = datetime.utcnow()
        self._save_workflows()
        return workflow

    def delete_workflow(self, workflow_id: str) -> bool:
        """Elimina un workflow."""
        if workflow_id in self._workflows:
            del self._workflows[workflow_id]
            self._save_workflows()
            return True
        return False

    # Ejecución

    async def execute_workflow(
        self,
        workflow_id: str,
        trigger_data: Optional[Dict] = None,
        triggered_by: str = "manual",
    ) -> Optional[WorkflowExecution]:
        """
        Ejecuta un workflow.

        Args:
            workflow_id: ID del workflow
            trigger_data: Datos del trigger
            triggered_by: Quién/que disparó la ejecución

        Returns:
            Ejecución iniciada
        """
        workflow = self._workflows.get(workflow_id)
        if not workflow:
            logger.error(f"Workflow no encontrado: {workflow_id}")
            return None

        if workflow.status != WorkflowStatus.ACTIVE:
            logger.warning(f"Workflow {workflow_id} no está activo")
            return None

        # Crear ejecución
        execution = WorkflowExecution(
            id=secrets.token_hex(8),
            workflow_id=workflow_id,
            status=ExecutionStatus.RUNNING,
            started_at=datetime.utcnow(),
            context={
                "trigger": trigger_data or {},
                "workflow_id": workflow_id,
                "execution_id": secrets.token_hex(8),
            },
            triggered_by=triggered_by,
        )

        self._executions[execution.id] = execution
        self._running_executions.add(execution.id)

        # Iniciar ejecución en background
        asyncio.create_task(self._run_execution(execution, workflow))

        logger.info(f"Workflow {workflow_id} iniciado: {execution.id}")
        return execution

    async def _run_execution(self, execution: WorkflowExecution, workflow: Workflow):
        """Ejecuta el workflow nodo por nodo."""
        try:
            # Encontrar nodos trigger
            trigger_nodes = workflow.get_trigger_nodes()
            if not trigger_nodes:
                raise ValueError("Workflow sin nodos trigger")

            # Iniciar desde triggers
            execution.current_nodes = [n.id for n in trigger_nodes]

            visited = set()
            max_iterations = 100  # Prevenir loops infinitos
            iteration = 0

            while execution.current_nodes and iteration < max_iterations:
                iteration += 1

                # Ejecutar nodos actuales en paralelo si son independientes
                next_nodes = []

                tasks = []
                for node_id in execution.current_nodes:
                    if node_id in visited:
                        continue
                    visited.add(node_id)

                    node = workflow.get_node(node_id)
                    if not node or not node.enabled:
                        continue

                    tasks.append(self._execute_node(node, execution, workflow))

                if not tasks:
                    break

                results = await asyncio.gather(*tasks, return_exceptions=True)

                # Procesar resultados y determinar siguientes nodos
                for result in results:
                    if isinstance(result, Exception):
                        logger.error(f"Error en ejecución: {result}")
                        continue

                    node_id, node_result = result

                    if node_result.get("branch"):  # Nodo condition
                        branch_nodes = node_result.get("next_nodes", [])
                        next_nodes.extend(branch_nodes)
                    else:
                        # Obtener conexiones del nodo
                        node = workflow.get_node(node_id)
                        if node:
                            next_nodes.extend(node.connections)

                execution.current_nodes = list(
                    dict.fromkeys(next_nodes)
                )  # Eliminar duplicados

            execution.status = ExecutionStatus.COMPLETED
            execution.finished_at = datetime.utcnow()

        except Exception as e:
            logger.error(f"Error ejecutando workflow: {e}")
            execution.status = ExecutionStatus.FAILED
            execution.error = str(e)
            execution.finished_at = datetime.utcnow()

        finally:
            self._running_executions.discard(execution.id)
            self._save_executions()

    async def _execute_node(
        self, node: WorkflowNode, execution: WorkflowExecution, workflow: Workflow
    ) -> tuple[str, Dict]:
        """Ejecuta un nodo individual."""
        node_exec = NodeExecution(
            node_id=node.id,
            status=ExecutionStatus.RUNNING,
            started_at=datetime.utcnow(),
        )
        execution.node_executions[node.id] = node_exec

        try:
            # Preparar contexto
            context = {
                **execution.context,
                "node_id": node.id,
                "workflow_id": workflow.id,
            }

            # Ejecutar
            result = await node.execute(context)

            node_exec.status = ExecutionStatus.COMPLETED
            node_exec.output = result
            node_exec.finished_at = datetime.utcnow()

            # Actualizar contexto con output
            execution.context[f"node_{node.id}_output"] = result

            return node.id, result

        except Exception as e:
            logger.error(f"Error ejecutando nodo {node.id}: {e}")
            node_exec.status = ExecutionStatus.FAILED
            node_exec.error = str(e)
            node_exec.finished_at = datetime.utcnow()

            return node.id, {"success": False, "error": str(e)}

    def get_execution(self, execution_id: str) -> Optional[WorkflowExecution]:
        """Obtiene una ejecución por ID."""
        return self._executions.get(execution_id)

    def list_executions(
        self, workflow_id: Optional[str] = None, limit: int = 50
    ) -> List[WorkflowExecution]:
        """Lista ejecuciones, opcionalmente filtradas por workflow."""
        executions = list(self._executions.values())

        if workflow_id:
            executions = [e for e in executions if e.workflow_id == workflow_id]

        executions.sort(key=lambda x: x.started_at, reverse=True)
        return executions[:limit]

    def cancel_execution(self, execution_id: str) -> bool:
        """Cancela una ejecución en curso."""
        execution = self._executions.get(execution_id)
        if not execution or execution.status != ExecutionStatus.RUNNING:
            return False

        self._running_executions.discard(execution_id)
        execution.status = ExecutionStatus.CANCELLED
        execution.finished_at = datetime.utcnow()
        self._save_executions()

        return True

    # Trigger handlers

    async def handle_health_status_change(
        self, component: str, old_status: str, new_status: str, details: Dict[str, Any]
    ):
        """Handler para cambios de estado de health checks."""
        for workflow in self._workflows.values():
            if workflow.status != WorkflowStatus.ACTIVE:
                continue

            trigger_config = workflow.trigger_config
            if trigger_config.get("type") != "health_status_change":
                continue

            # Verificar si aplica
            target_component = trigger_config.get("component", "*")
            if target_component != "*" and target_component != component:
                continue

            target_status = trigger_config.get("status", "*")
            if target_status != "*" and target_status != new_status:
                continue

            # Disparar workflow
            await self.execute_workflow(
                workflow.id,
                trigger_data={
                    "event": "health_status_change",
                    "component": component,
                    "old_status": old_status,
                    "new_status": new_status,
                    "details": details,
                },
                triggered_by="health_monitor",
            )

    async def handle_webhook_event(self, event_type: str, payload: Dict[str, Any]):
        """Handler para eventos de webhook entrantes."""
        for workflow in self._workflows.values():
            if workflow.status != WorkflowStatus.ACTIVE:
                continue

            trigger_config = workflow.trigger_config
            if trigger_config.get("type") != "webhook":
                continue

            target_event = trigger_config.get("event_type", "*")
            if target_event != "*" and target_event != event_type:
                continue

            await self.execute_workflow(
                workflow.id,
                trigger_data={
                    "event": "webhook",
                    "event_type": event_type,
                    "payload": payload,
                },
                triggered_by="webhook",
            )


# Singleton
_engine: Optional[WorkflowEngine] = None


def get_workflow_engine(base_path: Optional[Path] = None) -> WorkflowEngine:
    """Obtiene instancia del WorkflowEngine."""
    global _engine
    if _engine is None:
        _engine = WorkflowEngine(base_path)
    return _engine
