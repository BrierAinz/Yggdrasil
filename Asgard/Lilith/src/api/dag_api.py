"""
Lilith 4.2 — DAG API Endpoints

Endpoints para visualización y gestión de DAGs (Directed Acyclic Graphs).
"""

import logging
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

logger = logging.getLogger("DagAPI")

router = APIRouter(prefix="/api/dag", tags=["dag"])


class DagVisualizationRequest(BaseModel):
    """Request para visualizar un DAG."""

    plan_id: Optional[str] = None
    steps: List[Dict[str, Any]] = []


class DagVisualizationResponse(BaseModel):
    """Response con datos de visualización del DAG."""

    plan_id: str
    nodes: List[Dict[str, Any]]
    edges: List[Dict[str, Any]]
    waves: List[List[str]]
    stats: Dict[str, Any]


class DagOptimizationResponse(BaseModel):
    """Response con análisis de optimización."""

    plan_id: str
    estimated_time_ms: float
    critical_path: List[str]
    parallelization_factor: float
    suggestions: List[str]
    wave_times_ms: List[float]


@router.get("/visualize")
async def visualize_dag(
    plan_id: str = Query(..., description="ID del plan a visualizar"),
) -> Dict[str, Any]:
    """
    Visualiza un DAG por su ID.

    Retorna nodos, aristas y estado para renderizar con vis.js o similar.
    """
    try:
        # Importar aquí para evitar circular imports
        from src.core.dag import PlanDag

        # TODO: Cargar plan desde cache/DB
        # Por ahora, retornar estructura de ejemplo
        logger.warning(
            f"[DagAPI] visualize_dag not fully implemented for plan_id={plan_id}"
        )

        # Ejemplo de respuesta
        return {
            "plan_id": plan_id,
            "nodes": [
                {"id": "A", "label": "read_file", "status": "done", "color": "#90EE90"},
                {
                    "id": "B",
                    "label": "delegate_eva",
                    "status": "running",
                    "color": "#FFD700",
                },
                {
                    "id": "C",
                    "label": "store_result",
                    "status": "pending",
                    "color": "#CCCCCC",
                },
            ],
            "edges": [
                {"from": "A", "to": "B", "arrows": "to"},
                {"from": "B", "to": "C", "arrows": "to"},
            ],
            "waves": [["A"], ["B"], ["C"]],
            "stats": {
                "total_nodes": 3,
                "completed": 1,
                "running": 1,
                "pending": 1,
            },
        }

    except Exception as e:
        logger.exception(f"[DagAPI] Error visualizing DAG: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/visualize")
async def visualize_dag_from_steps(
    request: DagVisualizationRequest,
) -> Dict[str, Any]:
    """
    Crea y visualiza un DAG desde una lista de steps.

    Útil para previsualizar planes antes de ejecutarlos.
    """
    try:
        from src.core.dag import PlanDag

        if not request.steps:
            raise HTTPException(status_code=400, detail="No steps provided")

        # Crear DAG desde steps
        dag = PlanDag.from_steps(request.steps, name=request.plan_id or "preview")

        # Validar
        errors = dag.validate()
        if errors:
            return {
                "valid": False,
                "errors": errors,
                "nodes": [],
                "edges": [],
            }

        # Generar visualización
        viz_data = dag.to_visualization_format()
        waves = dag.compute_waves()

        return {
            "valid": True,
            "plan_id": request.plan_id or "preview",
            "nodes": viz_data["nodes"],
            "edges": viz_data["edges"],
            "waves": waves,
            "stats": dag.get_stats(),
        }

    except Exception as e:
        logger.exception(f"[DagAPI] Error creating DAG visualization: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/optimize")
async def optimize_dag(
    request: DagVisualizationRequest,
) -> Dict[str, Any]:
    """
    Analiza y optimiza un DAG.

    Retorna estimaciones de tiempo, camino crítico y sugerencias.
    """
    try:
        from src.core.dag import DagOptimizer, PlanDag

        if not request.steps:
            raise HTTPException(status_code=400, detail="No steps provided")

        # Crear DAG
        dag = PlanDag.from_steps(request.steps, name=request.plan_id or "optimize")

        # Validar
        errors = dag.validate()
        if errors:
            raise HTTPException(status_code=400, detail=f"Invalid DAG: {errors}")

        # Optimizar
        optimizer = DagOptimizer()
        opt = optimizer.optimize(dag)
        wave_times = optimizer.estimate_wave_times(dag)

        return {
            "plan_id": request.plan_id or "optimize",
            "estimated_time_ms": opt.estimated_time_ms,
            "estimated_time_seconds": opt.estimated_time_ms / 1000,
            "critical_path": opt.critical_path,
            "parallelization_factor": opt.parallelization_factor,
            "suggestions": opt.suggestions,
            "wave_times_ms": wave_times,
            "wave_count": len(wave_times),
        }

    except Exception as e:
        logger.exception(f"[DagAPI] Error optimizing DAG: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/stats")
async def get_dag_stats(
    plan_id: str = Query(..., description="ID del plan"),
) -> Dict[str, Any]:
    """
    Obtiene estadísticas de un DAG ejecutado.
    """
    try:
        # TODO: Cargar desde histórico de ejecuciones
        return {
            "plan_id": plan_id,
            "executions": 0,
            "avg_execution_time_ms": 0,
            "success_rate": 0,
        }

    except Exception as e:
        logger.exception(f"[DagAPI] Error getting DAG stats: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/validate")
async def validate_dag(
    request: DagVisualizationRequest,
) -> Dict[str, Any]:
    """
    Valida un DAG y detecta ciclos o dependencias inválidas.
    """
    try:
        from src.core.dag import PlanDag

        if not request.steps:
            raise HTTPException(status_code=400, detail="No steps provided")

        dag = PlanDag.from_steps(request.steps, name="validate")
        errors = dag.validate()

        # Intentar ordenamiento topológico
        topological_order = None
        if not errors:
            try:
                topological_order = dag.topological_sort()
            except Exception as e:
                errors.append(f"Topological sort failed: {e}")

        return {
            "valid": len(errors) == 0,
            "errors": errors,
            "node_count": len(dag.nodes),
            "topological_order": topological_order,
        }

    except Exception as e:
        logger.exception(f"[DagAPI] Error validating DAG: {e}")
        raise HTTPException(status_code=500, detail=str(e))
