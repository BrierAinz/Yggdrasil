"""
Workflows Module - Sistema de automatización visual

v4.2.8: Motor de workflows con nodos tipo DAG
"""
from .conditions import ConditionEvaluator
from .engine import (
    ExecutionStatus,
    Workflow,
    WorkflowEngine,
    WorkflowExecution,
    WorkflowStatus,
    get_workflow_engine,
)
from .nodes import (
    ActionNode,
    ConditionNode,
    DelayNode,
    NodeType,
    TriggerNode,
    WorkflowNode,
)

__all__ = [
    "WorkflowEngine",
    "get_workflow_engine",
    "Workflow",
    "WorkflowExecution",
    "WorkflowStatus",
    "ExecutionStatus",
    "NodeType",
    "WorkflowNode",
    "TriggerNode",
    "ActionNode",
    "ConditionNode",
    "DelayNode",
    "ConditionEvaluator",
]
