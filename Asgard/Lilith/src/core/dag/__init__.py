"""
Lilith 4.2 — DAG Execution Engine

Paquete para ejecución paralela de planes como grafos dirigidos acíclicos (DAG).

Uso básico:
    from src.core.dag import PlanDag, DagExecutor, DagOptimizer

    # Crear DAG
    dag = PlanDag(name="mi_plan")
    dag.add_node("A", "read_file", {"path": "x.py"})
    dag.add_node("B", "delegate_eva", {...}, dependencies=["A"])

    # Ejecutar
    executor = DagExecutor(max_workers=5)
    result = await executor.execute(dag)

    # Optimizar
    optimizer = DagOptimizer()
    opt = optimizer.optimize(dag)
    print(f"Tiempo estimado: {opt.estimated_time_ms}ms")
"""

from .dag_executor import (
    DagExecutor,
    DagExecutorBuilder,
    ExecutionProgress,
    ExecutionResult,
)
from .dag_optimizer import (
    DagOptimizer,
    MetricsStore,
    NodeMetrics,
    OptimizationResult,
    get_optimizer,
)
from .plan_dag import DAGCycleError, DagNode, DAGValidationError, NodeStatus, PlanDag

__all__ = [
    # Plan DAG
    "PlanDag",
    "DagNode",
    "NodeStatus",
    "DAGCycleError",
    "DAGValidationError",
    # Executor
    "DagExecutor",
    "DagExecutorBuilder",
    "ExecutionResult",
    "ExecutionProgress",
    # Optimizer
    "DagOptimizer",
    "NodeMetrics",
    "OptimizationResult",
    "MetricsStore",
    "get_optimizer",
]

__version__ = "4.2.0"
