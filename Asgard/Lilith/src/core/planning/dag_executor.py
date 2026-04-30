"""
Lilith 4.2 — DagExecutor: Ejecutor paralelo de DAGs.

Ejecuta nodos del DAG en oleadas paralelas, respetando dependencias.
Soporta:
- Ejecución asíncrona con asyncio
- ThreadPoolExecutor para operaciones bloqueantes
- Callbacks de progreso en tiempo real
- Políticas de manejo de errores (fail_fast, continue_on_error)
- Timeouts por nodo y por oleada
"""

import asyncio
import logging
import time
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Set

from .plan_dag import DagNode, DAGValidationError, NodeStatus, PlanDag

logger = logging.getLogger("DagExecutor")


@dataclass
class ExecutionResult:
    """Resultado de la ejecución de un DAG."""

    success: bool
    node_results: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    node_errors: Dict[str, str] = field(default_factory=dict)
    execution_time_ms: float = 0.0
    nodes_completed: int = 0
    nodes_failed: int = 0
    critical_path_executed: Optional[List[str]] = None


@dataclass
class ExecutionProgress:
    """Estado de progreso de la ejecución."""

    total_nodes: int
    completed_nodes: int
    running_nodes: int
    failed_nodes: int
    current_wave: int
    total_waves: int
    node_statuses: Dict[str, str] = field(default_factory=dict)


class DagExecutor:
    """
    Ejecutor paralelo de grafos DAG.

    Ejecuta nodos en oleadas, donde cada oleada contiene nodos cuyas
    dependencias ya están completas. Usa ThreadPoolExecutor para
    paralelización de operaciones bloqueantes.
    """

    def __init__(
        self,
        max_workers: int = 5,
        node_timeout_seconds: Optional[float] = None,
        wave_timeout_seconds: Optional[float] = None,
        failure_policy: str = "fail_fast",
    ):
        """
        Inicializa el executor.

        Args:
            max_workers: Máximo de workers en el ThreadPool
            node_timeout_seconds: Timeout por nodo (None = sin límite)
            wave_timeout_seconds: Timeout por oleada (None = sin límite)
            failure_policy: "fail_fast" | "continue_on_error" | "cancel_dependents"
        """
        self.max_workers = max(1, max_workers)
        self.node_timeout = node_timeout_seconds
        self.wave_timeout = wave_timeout_seconds
        self.failure_policy = failure_policy

        self._executor: Optional[ThreadPoolExecutor] = None
        self._progress_callback: Optional[Callable[[ExecutionProgress], None]] = None
        self._node_executor: Optional[
            Callable[[DagNode, Dict[str, Any]], Dict[str, Any]]
        ] = None

    def set_progress_callback(self, callback: Callable[[ExecutionProgress], None]):
        """Establece callback para notificaciones de progreso."""
        self._progress_callback = callback

    def set_node_executor(
        self, executor: Callable[[DagNode, Dict[str, Any]], Dict[str, Any]]
    ):
        """
        Establece la función que ejecuta un nodo individual.

        Args:
            executor: Función(node, context) -> result_dict
        """
        self._node_executor = executor

    async def execute(
        self,
        dag: PlanDag,
        context: Optional[Dict[str, Any]] = None,
    ) -> ExecutionResult:
        """
        Ejecuta el DAG completo.

        Args:
            dag: PlanDag a ejecutar
            context: Contexto global adicional para todos los nodos

        Returns:
            ExecutionResult con resultados y estadísticas
        """
        start_time = time.time()
        context = context or {}

        # Validar DAG
        errors = dag.validate()
        if errors:
            raise DAGValidationError(f"DAG inválido: {errors}")

        logger.info(
            f"[DagExecutor] Starting execution of '{dag.name}' with {len(dag.nodes)} nodes"
        )

        # Computar oleadas
        waves = dag.compute_waves()
        logger.info(
            f"[DagExecutor] Computed {len(waves)} waves: {[len(w) for w in waves]}"
        )

        # Resultados
        completed_nodes: Set[str] = set()
        failed_nodes: Set[str] = set()
        node_results: Dict[str, Dict[str, Any]] = {}
        node_errors: Dict[str, str] = {}

        # Ejecutar oleadas
        try:
            async with self._get_executor() as executor:
                for wave_idx, wave in enumerate(waves):
                    logger.info(
                        f"[DagExecutor] Executing wave {wave_idx + 1}/{len(waves)}: {wave}"
                    )

                    # Verificar si debemos cancelar por fallos previos
                    if self.failure_policy == "fail_fast" and failed_nodes:
                        logger.warning(
                            f"[DagExecutor] Aborting due to previous failures (fail_fast)"
                        )
                        break

                    # Filtrar nodos cancelados por dependencias fallidas
                    executable_nodes = self._filter_executable_nodes(
                        wave, dag, failed_nodes
                    )

                    if not executable_nodes:
                        logger.warning(
                            f"[DagExecutor] Wave {wave_idx + 1} has no executable nodes"
                        )
                        continue

                    # Ejecutar oleada
                    wave_success = await self._execute_wave(
                        dag=dag,
                        wave_nodes=executable_nodes,
                        wave_idx=wave_idx,
                        total_waves=len(waves),
                        completed_nodes=completed_nodes,
                        failed_nodes=failed_nodes,
                        node_results=node_results,
                        node_errors=node_errors,
                        executor=executor,
                        context=context,
                    )

                    if not wave_success and self.failure_policy == "fail_fast":
                        logger.warning(
                            f"[DagExecutor] Wave {wave_idx + 1} failed, aborting"
                        )
                        break

                    # Verificar si DAG está completo
                    if dag.is_complete():
                        logger.info(
                            f"[DagExecutor] DAG completed after wave {wave_idx + 1}"
                        )
                        break

        except Exception as e:
            logger.error(f"[DagExecutor] Execution failed: {e}")
            raise

        execution_time = (time.time() - start_time) * 1000

        # Compilar resultado final
        result = ExecutionResult(
            success=len(failed_nodes) == 0,
            node_results=node_results,
            node_errors=node_errors,
            execution_time_ms=execution_time,
            nodes_completed=len(completed_nodes),
            nodes_failed=len(failed_nodes),
        )

        logger.info(
            f"[DagExecutor] Execution completed: {result.nodes_completed} completed, "
            f"{result.nodes_failed} failed, {execution_time:.0f}ms"
        )

        return result

    def _get_executor(self):
        """Obtiene o crea el ThreadPoolExecutor."""
        if self._executor is None:
            return ThreadPoolExecutor(max_workers=self.max_workers)
        return self._executor

    def _filter_executable_nodes(
        self,
        wave: List[str],
        dag: PlanDag,
        failed_nodes: Set[str],
    ) -> List[str]:
        """
        Filtra nodos que pueden ejecutarse considerando fallos.

        Con 'cancel_dependents', cancela nodos cuyas dependencias fallaron.
        """
        if self.failure_policy != "cancel_dependents":
            return wave

        executable = []
        for node_id in wave:
            node = dag.get_node(node_id)
            if not node:
                continue

            # Verificar si alguna dependencia falló
            deps_failed = any(dep_id in failed_nodes for dep_id in node.dependencies)

            if deps_failed:
                dag.nodes[node_id].status = NodeStatus.CANCELLED
                failed_nodes.add(node_id)
                logger.debug(
                    f"[DagExecutor] Cancelled {node_id} due to failed dependency"
                )
            else:
                executable.append(node_id)

        return executable

    async def _execute_wave(
        self,
        dag: PlanDag,
        wave_nodes: List[str],
        wave_idx: int,
        total_waves: int,
        completed_nodes: Set[str],
        failed_nodes: Set[str],
        node_results: Dict[str, Dict[str, Any]],
        node_errors: Dict[str, str],
        executor: ThreadPoolExecutor,
        context: Dict[str, Any],
    ) -> bool:
        """
        Ejecuta una oleada de nodos en paralelo.

        Returns:
            True si la oleada se ejecutó correctamente (o parcialmente con continue_on_error)
        """
        # Crear tareas para cada nodo
        tasks = []
        for node_id in wave_nodes:
            task = self._execute_node_with_timeout(
                dag=dag,
                node_id=node_id,
                completed_nodes=completed_nodes,
                node_results=node_results,
                executor=executor,
                context=context,
            )
            tasks.append((node_id, task))

        # Ejecutar todas las tareas
        wave_success = True

        for node_id, task in tasks:
            try:
                result = await task

                if result.get("success"):
                    completed_nodes.add(node_id)
                    node_results[node_id] = result
                    dag.mark_done(node_id, result)
                else:
                    failed_nodes.add(node_id)
                    error_msg = result.get("error", "Unknown error")
                    node_errors[node_id] = error_msg
                    dag.mark_failed(node_id, error_msg)
                    wave_success = False

                    if self.failure_policy == "fail_fast":
                        break

            except asyncio.TimeoutError:
                failed_nodes.add(node_id)
                error_msg = f"Timeout after {self.node_timeout}s"
                node_errors[node_id] = error_msg
                dag.mark_failed(node_id, error_msg)
                wave_success = False

                logger.error(f"[DagExecutor] Node {node_id} timed out")

                if self.failure_policy == "fail_fast":
                    break

            except Exception as e:
                failed_nodes.add(node_id)
                error_msg = str(e)
                node_errors[node_id] = error_msg
                dag.mark_failed(node_id, error_msg)
                wave_success = False

                logger.exception(f"[DagExecutor] Node {node_id} failed: {e}")

                if self.failure_policy == "fail_fast":
                    break

            finally:
                # Notificar progreso
                self._notify_progress(dag, wave_idx, total_waves)

        return wave_success or self.failure_policy == "continue_on_error"

    async def _execute_node_with_timeout(
        self,
        dag: PlanDag,
        node_id: str,
        completed_nodes: Set[str],
        node_results: Dict[str, Dict[str, Any]],
        executor: ThreadPoolExecutor,
        context: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Ejecuta un nodo con timeout opcional."""
        node = dag.get_node(node_id)
        if not node:
            return {"success": False, "error": f"Node {node_id} not found"}

        # Marcar como running
        dag.mark_running(node_id)

        # Construir contexto desde dependencias
        node_context = self._build_context(node, completed_nodes, node_results)
        node_context.update(context)  # Añadir contexto global

        # Ejecutar
        start_time = time.time()

        try:
            if self._node_executor:
                # Usar executor personalizado
                result = await asyncio.get_event_loop().run_in_executor(
                    executor, self._node_executor, node, node_context
                )
            else:
                # Ejecución simulada (para testing)
                result = await self._default_node_executor(node, node_context)

            execution_time = (time.time() - start_time) * 1000

            if isinstance(result, dict):
                result["execution_time_ms"] = execution_time
            else:
                result = {
                    "success": True,
                    "output": result,
                    "execution_time_ms": execution_time,
                }

            return result

        except Exception as e:
            logger.exception(f"[DagExecutor] Error executing node {node_id}: {e}")
            return {"success": False, "error": str(e)}

    def _build_context(
        self,
        node: DagNode,
        completed_nodes: Set[str],
        node_results: Dict[str, Dict[str, Any]],
    ) -> Dict[str, Any]:
        """Construye el contexto para un nodo desde sus dependencias."""
        context = {}

        for dep_id in node.dependencies:
            if dep_id in completed_nodes and dep_id in node_results:
                dep_result = node_results[dep_id]

                # Añadir resultado de dependencia
                context[f"dep_{dep_id}"] = dep_result

                # Si hay output, hacerlo disponible directamente
                if "output" in dep_result:
                    context[f"{dep_id}_output"] = dep_result["output"]

                # Si hay resultado completo
                if "result" in dep_result:
                    context[f"{dep_id}_result"] = dep_result["result"]

        return context

    async def _default_node_executor(
        self, node: DagNode, context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Ejecutor por defecto (simulado para testing)."""
        logger.debug(f"[DagExecutor] Executing node {node.id}: {node.tool_name}")

        # Simular trabajo
        await asyncio.sleep(0.01)

        return {
            "success": True,
            "tool_name": node.tool_name,
            "node_id": node.id,
            "context_keys": list(context.keys()),
        }

    def _notify_progress(self, dag: PlanDag, current_wave: int, total_waves: int):
        """Notifica progreso si hay callback registrado."""
        if not self._progress_callback:
            return

        try:
            stats = dag.get_stats()

            progress = ExecutionProgress(
                total_nodes=stats["total_nodes"],
                completed_nodes=stats["completed"],
                running_nodes=stats["running"],
                failed_nodes=stats.get("failed", 0),
                current_wave=current_wave + 1,
                total_waves=total_waves,
                node_statuses={nid: n.status.value for nid, n in dag.nodes.items()},
            )

            # Llamar callback (puede ser sync o async)
            result = self._progress_callback(progress)
            if asyncio.iscoroutine(result):
                asyncio.create_task(result)

        except Exception as e:
            logger.warning(f"[DagExecutor] Progress callback failed: {e}")

    async def execute_single_node(
        self,
        dag: PlanDag,
        node_id: str,
        context: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Ejecuta un único nodo (útil para reintentos).

        Args:
            dag: PlanDag
            node_id: ID del nodo a ejecutar
            context: Contexto adicional

        Returns:
            Resultado de la ejecución
        """
        context = context or {}

        async with self._get_executor() as executor:
            completed_nodes = {
                nid for nid, n in dag.nodes.items() if n.status == NodeStatus.DONE
            }
            node_results = {nid: n.result for nid, n in dag.nodes.items() if n.result}

            return await self._execute_node_with_timeout(
                dag=dag,
                node_id=node_id,
                completed_nodes=completed_nodes,
                node_results=node_results,
                executor=executor,
                context=context,
            )


class DagExecutorBuilder:
    """Builder para configurar DagExecutor de forma fluida."""

    def __init__(self):
        self.max_workers = 5
        self.node_timeout = None
        self.wave_timeout = None
        self.failure_policy = "fail_fast"
        self.progress_callback = None
        self.node_executor = None

    def with_max_workers(self, n: int) -> "DagExecutorBuilder":
        self.max_workers = n
        return self

    def with_node_timeout(self, seconds: float) -> "DagExecutorBuilder":
        self.node_timeout = seconds
        return self

    def with_wave_timeout(self, seconds: float) -> "DagExecutorBuilder":
        self.wave_timeout = seconds
        return self

    def with_failure_policy(self, policy: str) -> "DagExecutorBuilder":
        self.failure_policy = policy
        return self

    def with_progress_callback(
        self, callback: Callable[[ExecutionProgress], None]
    ) -> "DagExecutorBuilder":
        self.progress_callback = callback
        return self

    def with_node_executor(
        self, executor: Callable[[DagNode, Dict[str, Any]], Dict[str, Any]]
    ) -> "DagExecutorBuilder":
        self.node_executor = executor
        return self

    def build(self) -> DagExecutor:
        executor = DagExecutor(
            max_workers=self.max_workers,
            node_timeout_seconds=self.node_timeout,
            wave_timeout_seconds=self.wave_timeout,
            failure_policy=self.failure_policy,
        )

        if self.progress_callback:
            executor.set_progress_callback(self.progress_callback)

        if self.node_executor:
            executor.set_node_executor(self.node_executor)

        return executor
