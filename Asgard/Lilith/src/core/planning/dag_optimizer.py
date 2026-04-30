"""
Lilith 4.2 — DagOptimizer: Optimizaciones y análisis de DAGs.

Incluye:
- Estimación de tiempo de ejecución
- Cálculo de camino crítico (critical path)
- Auto-paralelización de planes secuenciales
- Métricas históricas de ejecución
"""

import json
import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

from .plan_dag import DagNode, PlanDag

logger = logging.getLogger("DagOptimizer")


@dataclass
class NodeMetrics:
    """Métricas históricas de un nodo/tool."""

    tool_name: str
    avg_latency_ms: float
    min_latency_ms: float
    max_latency_ms: float
    total_executions: int
    success_rate: float


@dataclass
class OptimizationResult:
    """Resultado de la optimización de un DAG."""

    estimated_time_ms: float
    critical_path: List[str]
    parallelization_factor: float
    suggestions: List[str]


class MetricsStore:
    """Almacén de métricas históricas de ejecución."""

    def __init__(self, storage_path: Optional[Path] = None):
        self.storage_path = storage_path or Path("Data/dag_metrics.json")
        self._metrics: Dict[str, NodeMetrics] = {}
        self._load()

    def _load(self):
        """Carga métricas desde disco."""
        if self.storage_path.exists():
            try:
                with open(self.storage_path, "r") as f:
                    data = json.load(f)
                    for tool_name, m in data.items():
                        self._metrics[tool_name] = NodeMetrics(**m)
            except Exception as e:
                logger.warning(f"[MetricsStore] Failed to load: {e}")

    def _save(self):
        """Guarda métricas a disco."""
        try:
            self.storage_path.parent.mkdir(parents=True, exist_ok=True)
            with open(self.storage_path, "w") as f:
                data = {
                    tool: {
                        "tool_name": m.tool_name,
                        "avg_latency_ms": m.avg_latency_ms,
                        "min_latency_ms": m.min_latency_ms,
                        "max_latency_ms": m.max_latency_ms,
                        "total_executions": m.total_executions,
                        "success_rate": m.success_rate,
                    }
                    for tool, m in self._metrics.items()
                }
                json.dump(data, f, indent=2)
        except Exception as e:
            logger.warning(f"[MetricsStore] Failed to save: {e}")

    def record_execution(
        self,
        tool_name: str,
        execution_time_ms: float,
        success: bool,
    ):
        """Registra una ejecución para actualizar métricas."""
        if tool_name not in self._metrics:
            self._metrics[tool_name] = NodeMetrics(
                tool_name=tool_name,
                avg_latency_ms=execution_time_ms,
                min_latency_ms=execution_time_ms,
                max_latency_ms=execution_time_ms,
                total_executions=1,
                success_rate=1.0 if success else 0.0,
            )
        else:
            m = self._metrics[tool_name]

            # Actualizar promedio móvil
            total = m.total_executions
            m.avg_latency_ms = (m.avg_latency_ms * total + execution_time_ms) / (
                total + 1
            )
            m.min_latency_ms = min(m.min_latency_ms, execution_time_ms)
            m.max_latency_ms = max(m.max_latency_ms, execution_time_ms)
            m.total_executions += 1

            # Actualizar tasa de éxito
            success_val = 1.0 if success else 0.0
            m.success_rate = (m.success_rate * total + success_val) / (total + 1)

        self._save()

    def get_metrics(self, tool_name: str) -> Optional[NodeMetrics]:
        """Obtiene métricas para una tool."""
        return self._metrics.get(tool_name)

    def get_avg_latency(self, tool_name: str, default_ms: float = 5000.0) -> float:
        """Obtiene latencia promedio para una tool."""
        m = self._metrics.get(tool_name)
        return m.avg_latency_ms if m else default_ms

    def get_default_metrics(self) -> Dict[str, NodeMetrics]:
        """Métricas por defecto para tools comunes."""
        return {
            "read_file": NodeMetrics("read_file", 100, 50, 500, 100, 0.99),
            "edit_file": NodeMetrics("edit_file", 500, 200, 2000, 100, 0.95),
            "delegate_odin": NodeMetrics("delegate_odin", 3000, 1000, 10000, 100, 0.98),
            "delegate_eva": NodeMetrics("delegate_eva", 5000, 2000, 15000, 100, 0.95),
            "delegate_adan": NodeMetrics("delegate_adan", 4000, 1500, 12000, 100, 0.95),
            "lore_extractor": NodeMetrics(
                "lore_extractor", 8000, 3000, 30000, 50, 0.90
            ),
            "store_semantic_fact": NodeMetrics(
                "store_semantic_fact", 200, 100, 1000, 200, 0.99
            ),
            "browser_goto": NodeMetrics("browser_goto", 3000, 1000, 10000, 50, 0.85),
            "browser_click": NodeMetrics("browser_click", 1000, 500, 3000, 50, 0.90),
        }


class DagOptimizer:
    """
    Optimizador de DAGs.

    Proporciona análisis y optimizaciones para planes DAG:
    - Estimación de tiempo total
    - Identificación de camino crítico
    - Sugerencias de paralelización
    """

    def __init__(self, metrics_store: Optional[MetricsStore] = None):
        self.metrics = metrics_store or MetricsStore()

    def estimate_execution_time(self, dag: PlanDag) -> float:
        """
        Estima el tiempo total de ejecución del DAG.

        Usa métricas históricas y calcula el tiempo del camino crítico.

        Args:
            dag: PlanDag a analizar

        Returns:
            Tiempo estimado en milisegundos
        """
        # Calcular camino crítico
        critical_path = dag.get_critical_path()

        if not critical_path:
            # Sin camino crítico, sumar todos
            total = 0.0
            for node in dag.nodes.values():
                latency = self.metrics.get_avg_latency(node.tool_name)
                total += latency
            return total

        # Sumar tiempos del camino crítico
        total_ms = 0.0
        for node_id in critical_path:
            node = dag.get_node(node_id)
            if node:
                latency = self.metrics.get_avg_latency(node.tool_name)
                total_ms += latency

        logger.debug(
            f"[DagOptimizer] Estimated time for '{dag.name}': {total_ms:.0f}ms "
            f"(critical path: {critical_path})"
        )

        return total_ms

    def estimate_wave_times(self, dag: PlanDag) -> List[float]:
        """
        Estima el tiempo de cada oleada.

        Returns:
            Lista de tiempos estimados por oleada (ms)
        """
        waves = dag.compute_waves()
        wave_times = []

        for wave in waves:
            # Tiempo de la oleada = máximo de sus nodos (ejecutan en paralelo)
            max_time = 0.0
            for node_id in wave:
                node = dag.get_node(node_id)
                if node:
                    latency = self.metrics.get_avg_latency(node.tool_name)
                    max_time = max(max_time, latency)
            wave_times.append(max_time)

        return wave_times

    def calculate_parallelization_factor(self, dag: PlanDag) -> float:
        """
        Calcula el factor de paralelización.

        Factor = (tiempo secuencial) / (tiempo paralelo)

        Returns:
            Factor de paralelización (1.0 = secuencial, >1 = paralelo)
        """
        # Tiempo secuencial (suma de todos)
        sequential_time = sum(
            self.metrics.get_avg_latency(node.tool_name) for node in dag.nodes.values()
        )

        # Tiempo paralelo (suma de máximos por oleada)
        wave_times = self.estimate_wave_times(dag)
        parallel_time = sum(wave_times)

        if parallel_time == 0:
            return 1.0

        factor = sequential_time / parallel_time

        logger.debug(
            f"[DagOptimizer] Parallelization factor for '{dag.name}': {factor:.2f}x"
        )

        return factor

    def find_bottlenecks(self, dag: PlanDag, top_n: int = 3) -> List[Tuple[str, float]]:
        """
        Identifica los nodos más lentos (cuellos de botella).

        Args:
            dag: PlanDag
            top_n: Cuántos retornar

        Returns:
            Lista de (node_id, tiempo_estimado_ms)
        """
        node_times = [
            (node_id, self.metrics.get_avg_latency(node.tool_name))
            for node_id, node in dag.nodes.items()
        ]

        # Ordenar por tiempo descendente
        node_times.sort(key=lambda x: x[1], reverse=True)

        return node_times[:top_n]

    def suggest_optimizations(self, dag: PlanDag) -> List[str]:
        """
        Genera sugerencias de optimización para el DAG.

        Args:
            dag: PlanDag a analizar

        Returns:
            Lista de sugerencias en texto
        """
        suggestions = []

        # 1. Verificar nodos secuenciales que podrían paralelizarse
        waves = dag.compute_waves()
        if len(waves) == len(dag.nodes):
            # Cada nodo en su propia oleada = completamente secuencial
            suggestions.append(
                "El plan es completamente secuencial. "
                "Considere añadir dependencias explícitas solo donde sea necesario "
                "para permitir paralelización."
            )

        # 2. Identificar cuellos de botella
        bottlenecks = self.find_bottlenecks(dag, top_n=3)
        for node_id, time_ms in bottlenecks[:2]:
            node = dag.get_node(node_id)
            if node and time_ms > 5000:  # Más de 5 segundos
                suggestions.append(
                    f"Nodo '{node_id}' ({node.tool_name}) es un cuello de botella "
                    f"(~{time_ms/1000:.1f}s). Considere optimizar o dividir la tarea."
                )

        # 3. Verificar balance de oleadas
        wave_sizes = [len(w) for w in waves]
        if wave_sizes:
            avg_size = sum(wave_sizes) / len(wave_sizes)
            max_size = max(wave_sizes)

            if max_size > avg_size * 2 and max_size > 3:
                # Una oleada mucho más grande que las demás
                suggestions.append(
                    f"Desbalance en oleadas: una oleada tiene {max_size} nodos "
                    f"(promedio: {avg_size:.1f}). Considere reorganizar dependencias."
                )

        # 4. Verificar nodos sin dependencias ni dependientes
        isolated = [
            node_id
            for node_id, node in dag.nodes.items()
            if not node.dependencies and not self._is_dependency_of_any(dag, node_id)
        ]
        if len(isolated) == 1 and len(dag.nodes) > 1:
            suggestions.append(
                f"Nodo '{isolated[0]}' está aislado. "
                "Verifique si debería integrarse con otros nodos."
            )

        # 5. Factor de paralelización
        factor = self.calculate_parallelization_factor(dag)
        if factor < 1.2 and len(dag.nodes) > 3:
            suggestions.append(
                f"Bajo factor de paralelización ({factor:.1f}x). "
                "El plan podría beneficiarse de más independencia entre tareas."
            )

        return suggestions

    def _is_dependency_of_any(self, dag: PlanDag, node_id: str) -> bool:
        """Verifica si un nodo es dependencia de algún otro."""
        return any(node_id in node.dependencies for node in dag.nodes.values())

    def auto_parallelize(self, steps: List[Any]) -> List[Any]:
        """
        Intenta detectar dependencias automáticamente en steps secuenciales.

        Analiza los parámetros de cada step para inferir dependencias
        basadas en outputs de steps anteriores.

        Args:
            steps: Lista de steps (probablemente sin depends_on)

        Returns:
            Steps con depends_on inferido
        """
        # Asignar IDs si no tienen
        for i, step in enumerate(steps):
            if not getattr(step, "step_id", None):
                step.step_id = f"step_{i}"

        # Para cada step, buscar referencias a outputs de steps anteriores
        for i, step in enumerate(steps):
            step.dependencies = step.dependencies or []

            # Buscar en params referencias a steps anteriores
            params_str = json.dumps(step.params)

            for j in range(i):
                prev_step = steps[j]
                prev_id = prev_step.step_id

                # Heurísticas de dependencia
                if self._has_dependency_reference(params_str, prev_id, prev_step):
                    if prev_id not in step.dependencies:
                        step.dependencies.append(prev_id)
                        logger.debug(
                            f"[DagOptimizer] Inferred dependency: {step.step_id} -> {prev_id}"
                        )

        return steps

    def _has_dependency_reference(
        self, params_str: str, prev_id: str, prev_step: Any
    ) -> bool:
        """
        Detecta si params_str hace referencia al output de un step previo.

        Heurísticas:
        - Referencia directa al ID: {{step_0}}, {{step_0.output}}
        - Referencia al resultado: {{result}}, {{output}}
        - Referencia a tool específica
        """
        # Patrones de referencia
        patterns = [
            f"{{{{{prev_id}}}}}",
            f"{{{{{prev_id}}}}}.",  # {{prev_id}}.
            f"{{{{result}}}}",
            f"{{{{output}}}}",
        ]

        return any(p in params_str for p in patterns)

    def optimize(self, dag: PlanDag) -> OptimizationResult:
        """
        Ejecuta todas las optimizaciones y análisis en el DAG.

        Args:
            dag: PlanDag a optimizar

        Returns:
            OptimizationResult con todos los análisis
        """
        estimated_time = self.estimate_execution_time(dag)
        critical_path = dag.get_critical_path()
        parallel_factor = self.calculate_parallelization_factor(dag)
        suggestions = self.suggest_optimizations(dag)

        result = OptimizationResult(
            estimated_time_ms=estimated_time,
            critical_path=critical_path,
            parallelization_factor=parallel_factor,
            suggestions=suggestions,
        )

        logger.info(
            f"[DagOptimizer] Optimization for '{dag.name}': "
            f"{estimated_time/1000:.1f}s, {parallel_factor:.1f}x parallel, "
            f"{len(suggestions)} suggestions"
        )

        return result

    def print_report(self, dag: PlanDag):
        """Imprime un reporte de optimización en logs."""
        opt = self.optimize(dag)

        logger.info(f"\n{'='*60}")
        logger.info(f"DAG Optimization Report: {dag.name}")
        logger.info(f"{'='*60}")
        logger.info(f"Nodes: {len(dag.nodes)}")
        logger.info(f"Waves: {len(dag.compute_waves())}")
        logger.info(f"Estimated time: {opt.estimated_time_ms/1000:.1f}s")
        logger.info(f"Critical path: {' -> '.join(opt.critical_path)}")
        logger.info(f"Parallelization: {opt.parallelization_factor:.2f}x")

        if opt.suggestions:
            logger.info(f"\nSuggestions:")
            for i, suggestion in enumerate(opt.suggestions, 1):
                logger.info(f"  {i}. {suggestion}")

        logger.info(f"{'='*60}\n")


# Instancia global
_default_optimizer: Optional[DagOptimizer] = None


def get_optimizer() -> DagOptimizer:
    """Obtiene instancia global del optimizador."""
    global _default_optimizer
    if _default_optimizer is None:
        _default_optimizer = DagOptimizer()
    return _default_optimizer
