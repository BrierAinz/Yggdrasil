"""
Lilith 4.2 — PlanDag: Representación de planes como grafos dirigidos acíclicos (DAG).

Incluye:
- DagNode: Nodo individual del DAG con dependencias y estado
- PlanDag: Grafo completo con validación de ciclos y ordenamiento topológico
- Validación: Detección de ciclos y dependencias inválidas
"""

import logging
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Set, Tuple

logger = logging.getLogger("PlanDag")


class NodeStatus(Enum):
    """Estados posibles de un nodo en el DAG."""

    PENDING = "pending"
    RUNNING = "running"
    DONE = "done"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class DagNode:
    """
    Nodo individual en el DAG.

    Attributes:
        id: Identificador único del nodo
        tool_name: Nombre de la tool a ejecutar
        params: Parámetros para la tool
        dependencies: Lista de IDs de nodos que deben completarse antes
        status: Estado actual del nodo
        result: Resultado de la ejecución (si está done)
        error: Mensaje de error (si falló)
        execution_time_ms: Tiempo de ejecución en milisegundos
    """

    id: str
    tool_name: str
    params: Dict[str, Any] = field(default_factory=dict)
    dependencies: List[str] = field(default_factory=list)
    status: NodeStatus = NodeStatus.PENDING
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    execution_time_ms: Optional[float] = None

    def is_ready(self, completed_ids: Set[str]) -> bool:
        """Verifica si todas las dependencias están completadas."""
        return all(dep_id in completed_ids for dep_id in self.dependencies)

    def to_dict(self) -> Dict[str, Any]:
        """Serializa el nodo a diccionario."""
        return {
            "id": self.id,
            "tool_name": self.tool_name,
            "params": self.params,
            "dependencies": self.dependencies,
            "status": self.status.value,
            "result": self.result,
            "error": self.error,
            "execution_time_ms": self.execution_time_ms,
        }


class DAGCycleError(ValueError):
    """Error lanzado cuando se detecta un ciclo en el DAG."""

    def __init__(self, message: str, cycle_nodes: Optional[List[str]] = None):
        super().__init__(message)
        self.cycle_nodes = cycle_nodes or []


class DAGValidationError(ValueError):
    """Error de validación del DAG (dependencias inválidas, etc.)."""

    pass


class PlanDag:
    """
    Representa un plan como un grafo dirigido acíclico (DAG).

    Permite:
    - Construcción desde lista de steps
    - Validación de ciclos y dependencias
    - Ordenamiento topológico
    - Consulta de nodos listos para ejecución
    """

    def __init__(self, name: str = "unnamed"):
        self.name = name
        self.nodes: Dict[str, DagNode] = {}
        self._topological_order: Optional[List[str]] = None
        self._waves: Optional[List[List[str]]] = None

    def add_node(
        self,
        node_id: str,
        tool_name: str,
        params: Optional[Dict[str, Any]] = None,
        dependencies: Optional[List[str]] = None,
    ) -> DagNode:
        """
        Añade un nodo al DAG.

        Args:
            node_id: Identificador único
            tool_name: Tool a ejecutar
            params: Parámetros de la tool
            dependencies: IDs de nodos dependientes

        Returns:
            El nodo creado
        """
        if node_id in self.nodes:
            raise DAGValidationError(f"Nodo duplicado: {node_id}")

        node = DagNode(
            id=node_id,
            tool_name=tool_name,
            params=params or {},
            dependencies=dependencies or [],
        )
        self.nodes[node_id] = node

        # Invalidar caché de ordenamiento
        self._topological_order = None
        self._waves = None

        logger.debug(f"[PlanDag] Added node: {node_id} ({tool_name})")
        return node

    def add_edge(self, from_id: str, to_id: str):
        """
        Añade una dependencia (arista) entre dos nodos.

        Args:
            from_id: Nodo que debe completarse primero
            to_id: Nodo que depende del primero
        """
        if from_id not in self.nodes:
            raise DAGValidationError(f"Nodo origen no existe: {from_id}")
        if to_id not in self.nodes:
            raise DAGValidationError(f"Nodo destino no existe: {to_id}")

        if from_id not in self.nodes[to_id].dependencies:
            self.nodes[to_id].dependencies.append(from_id)
            logger.debug(f"[PlanDag] Added edge: {from_id} -> {to_id}")

        # Invalidar caché
        self._topological_order = None
        self._waves = None

    def get_node(self, node_id: str) -> Optional[DagNode]:
        """Obtiene un nodo por su ID."""
        return self.nodes.get(node_id)

    def get_ready_nodes(
        self, completed_ids: Optional[Set[str]] = None
    ) -> List[DagNode]:
        """
        Retorna nodos cuyas dependencias están completas.

        Args:
            completed_ids: Set de IDs de nodos completados

        Returns:
            Lista de nodos listos para ejecutar
        """
        completed = completed_ids or set()

        ready = []
        for node in self.nodes.values():
            if node.status == NodeStatus.PENDING and node.is_ready(completed):
                ready.append(node)

        return ready

    def mark_done(
        self,
        node_id: str,
        result: Dict[str, Any],
        execution_time_ms: Optional[float] = None,
    ):
        """Marca un nodo como completado."""
        if node_id not in self.nodes:
            raise DAGValidationError(f"Nodo no existe: {node_id}")

        node = self.nodes[node_id]
        node.status = NodeStatus.DONE
        node.result = result
        node.execution_time_ms = execution_time_ms

        logger.debug(f"[PlanDag] Marked done: {node_id}")

    def mark_failed(self, node_id: str, error: str):
        """Marca un nodo como fallido."""
        if node_id not in self.nodes:
            raise DAGValidationError(f"Nodo no existe: {node_id}")

        node = self.nodes[node_id]
        node.status = NodeStatus.FAILED
        node.error = error

        logger.debug(f"[PlanDag] Marked failed: {node_id} - {error}")

    def mark_running(self, node_id: str):
        """Marca un nodo como en ejecución."""
        if node_id not in self.nodes:
            raise DAGValidationError(f"Nodo no existe: {node_id}")

        self.nodes[node_id].status = NodeStatus.RUNNING
        logger.debug(f"[PlanDag] Marked running: {node_id}")

    def is_complete(self) -> bool:
        """Verifica si todos los nodos están completos (done o failed)."""
        return all(
            node.status in (NodeStatus.DONE, NodeStatus.FAILED, NodeStatus.CANCELLED)
            for node in self.nodes.values()
        )

    def validate(self) -> List[str]:
        """
        Valida el DAG completo.

        Returns:
            Lista de errores encontrados (vacía si es válido)
        """
        errors = []

        # 1. Verificar dependencias inválidas
        for node in self.nodes.values():
            for dep_id in node.dependencies:
                if dep_id not in self.nodes:
                    errors.append(
                        f"Nodo {node.id} depende de nodo inexistente: {dep_id}"
                    )

        # 2. Detectar ciclos
        try:
            self._detect_cycles()
        except DAGCycleError as e:
            errors.append(str(e))

        # 3. Verificar nodos aislados (warning, no error)
        isolated = [
            n.id
            for n in self.nodes.values()
            if not n.dependencies and not self._is_dependency_of_any(n.id)
        ]
        if isolated and len(self.nodes) > 1:
            logger.warning(
                f"[PlanDag] Nodos sin dependencias ni dependientes (ejecutarán primero): {isolated}"
            )

        return errors

    def _detect_cycles(self) -> Optional[List[str]]:
        """
        Detecta ciclos usando DFS.

        Returns:
            Lista de nodos en el ciclo, o None si no hay ciclo

        Raises:
            DAGCycleError si se detecta un ciclo
        """
        WHITE, GRAY, BLACK = 0, 1, 2
        color = {node_id: WHITE for node_id in self.nodes}
        path = []

        def dfs(node_id: str) -> Optional[List[str]]:
            color[node_id] = GRAY
            path.append(node_id)

            for dep_id in self.nodes[node_id].dependencies:
                if dep_id not in self.nodes:
                    continue  # Ya reportado en validación

                if color[dep_id] == GRAY:
                    # Ciclo detectado
                    cycle_start = path.index(dep_id)
                    cycle = path[cycle_start:] + [dep_id]
                    return cycle

                if color[dep_id] == WHITE:
                    result = dfs(dep_id)
                    if result:
                        return result

            path.pop()
            color[node_id] = BLACK
            return None

        for node_id in self.nodes:
            if color[node_id] == WHITE:
                cycle = dfs(node_id)
                if cycle:
                    raise DAGCycleError(
                        f"Ciclo detectado en DAG: {' -> '.join(cycle)}",
                        cycle_nodes=cycle,
                    )

        return None

    def _is_dependency_of_any(self, node_id: str) -> bool:
        """Verifica si un nodo es dependencia de algún otro."""
        return any(node_id in node.dependencies for node in self.nodes.values())

    def topological_sort(self) -> List[str]:
        """
        Ordenamiento topológico del DAG.

        Returns:
            Lista de IDs en orden de ejecución válido

        Raises:
            DAGCycleError si hay ciclos
        """
        if self._topological_order is not None:
            return self._topological_order

        # Validar primero
        errors = self.validate()
        if errors:
            raise DAGValidationError(f"DAG inválido: {errors}")

        # Algoritmo de Kahn
        in_degree = {node_id: 0 for node_id in self.nodes}
        for node in self.nodes.values():
            for dep_id in node.dependencies:
                if dep_id in in_degree:
                    in_degree[node_id] += 1

        # Cola de nodos sin dependencias
        queue = [node_id for node_id, degree in in_degree.items() if degree == 0]
        result = []

        while queue:
            # Ordenar para determinismo
            queue.sort()
            node_id = queue.pop(0)
            result.append(node_id)

            # Reducir in-degree de nodos que dependen de este
            for other_id, node in self.nodes.items():
                if node_id in node.dependencies and other_id not in result:
                    in_degree[other_id] -= 1
                    if in_degree[other_id] == 0:
                        queue.append(other_id)

        if len(result) != len(self.nodes):
            raise DAGCycleError("Ciclo detectado (algoritmo de Kahn falló)")

        self._topological_order = result
        return result

    def compute_waves(self) -> List[List[str]]:
        """
        Agrupa nodos en oleadas (waves) para ejecución paralela.

        Cada oleada contiene nodos cuyas dependencias están en oleadas anteriores.

        Returns:
            Lista de oleadas, cada una es lista de IDs de nodos
        """
        if self._waves is not None:
            return self._waves

        # Validar
        errors = self.validate()
        if errors:
            raise DAGValidationError(f"DAG inválido: {errors}")

        waves: List[List[str]] = []
        completed: Set[str] = set()
        remaining = set(self.nodes.keys())

        while remaining:
            wave = [
                node_id
                for node_id in remaining
                if self.nodes[node_id].is_ready(completed)
            ]

            if not wave:
                raise DAGCycleError("Ciclo detectado al computar oleadas")

            waves.append(sorted(wave))  # Ordenar para determinismo
            completed.update(wave)
            remaining -= set(wave)

        self._waves = waves
        logger.info(
            f"[PlanDag] Computed {len(waves)} waves for {len(self.nodes)} nodes"
        )
        return waves

    def get_critical_path(self) -> List[str]:
        """
        Calcula el camino crítico (ruta más larga desde un nodo inicial hasta uno final).

        Returns:
            Lista de IDs del camino crítico
        """
        if not self.nodes:
            return []

        # Calcular distancias máximas desde cada nodo
        distances = {node_id: 0 for node_id in self.nodes}

        # Procesar en orden topológico inverso
        topo = self.topological_sort()
        topo.reverse()

        for node_id in topo:
            # Encontrar nodos que dependen de este
            dependents = [
                other_id
                for other_id, node in self.nodes.items()
                if node_id in node.dependencies
            ]

            if dependents:
                max_dist = max(distances.get(dep_id, 0) for dep_id in dependents)
                distances[node_id] = max_dist + 1

        # Reconstruir camino crítico
        # Empezar desde nodo con mayor distancia que no tiene dependientes
        start_node = max(
            (
                node_id
                for node_id in self.nodes
                if not self._is_dependency_of_any(node_id)
            ),
            key=lambda nid: distances.get(nid, 0),
            default=None,
        )

        if not start_node:
            return []

        path = [start_node]
        current = start_node

        while current:
            # Encontrar dependientes
            dependents = [
                other_id
                for other_id, node in self.nodes.items()
                if current in node.dependencies and node.status != NodeStatus.CANCELLED
            ]

            if not dependents:
                break

            # Seguir el de mayor distancia
            current = max(dependents, key=lambda nid: distances.get(nid, 0))
            path.append(current)

        return path

    def get_stats(self) -> Dict[str, Any]:
        """Retorna estadísticas del DAG."""
        total = len(self.nodes)
        by_status = {
            status.value: sum(1 for n in self.nodes.values() if n.status == status)
            for status in NodeStatus
        }

        return {
            "name": self.name,
            "total_nodes": total,
            "by_status": by_status,
            "completed": by_status.get("done", 0) + by_status.get("failed", 0),
            "pending": by_status.get("pending", 0),
            "running": by_status.get("running", 0),
            "waves": len(self._waves) if self._waves else None,
        }

    def to_dict(self) -> Dict[str, Any]:
        """Serializa el DAG completo a diccionario."""
        return {
            "name": self.name,
            "nodes": {node_id: node.to_dict() for node_id, node in self.nodes.items()},
            "stats": self.get_stats(),
            "topological_order": self._topological_order,
            "waves": self._waves,
        }

    def to_visualization_format(self) -> Dict[str, Any]:
        """
        Formato para visualización (frontend).

        Returns:
            Dict con 'nodes' y 'edges' para librerías como vis.js
        """
        nodes = [
            {
                "id": node_id,
                "label": f"{node.tool_name}",
                "status": node.status.value,
                "shape": "box",
                "color": self._status_color(node.status),
            }
            for node_id, node in self.nodes.items()
        ]

        edges = [
            {
                "from": dep_id,
                "to": node_id,
                "arrows": "to",
            }
            for node_id, node in self.nodes.items()
            for dep_id in node.dependencies
        ]

        return {"nodes": nodes, "edges": edges}

    def _status_color(self, status: NodeStatus) -> str:
        """Color para visualización según estado."""
        colors = {
            NodeStatus.PENDING: "#CCCCCC",  # Gris
            NodeStatus.RUNNING: "#FFD700",  # Amarillo
            NodeStatus.DONE: "#90EE90",  # Verde claro
            NodeStatus.FAILED: "#FF6B6B",  # Rojo
            NodeStatus.CANCELLED: "#999999",  # Gris oscuro
        }
        return colors.get(status, "#CCCCCC")

    @classmethod
    def from_steps(cls, steps: List[Any], name: str = "from_steps") -> "PlanDag":
        """
        Construye un PlanDag desde una lista de steps (compatible con planner.py).

        Args:
            steps: Lista de objetos Step (con step_id, tool_name, params, depends_on)
            name: Nombre del DAG

        Returns:
            PlanDag construido
        """
        dag = cls(name=name)

        for step in steps:
            step_id = getattr(step, "step_id", None) or f"step_{len(dag.nodes)}"
            tool_name = getattr(step, "tool_name", "")
            params = getattr(step, "params", {}) or {}
            dependencies = getattr(step, "depends_on", None) or []

            dag.add_node(
                node_id=step_id,
                tool_name=tool_name,
                params=params,
                dependencies=dependencies,
            )

        logger.info(f"[PlanDag] Built DAG '{name}' with {len(steps)} nodes")
        return dag

    def __repr__(self) -> str:
        return f"PlanDag(name='{self.name}', nodes={len(self.nodes)})"
