"""
Tests for Workflows Engine

v4.2.8: Tests unitarios para el motor de workflows.
"""
import asyncio
from typing import Any, Dict
from unittest.mock import AsyncMock, Mock, patch

import pytest
from src.core.workflows import (
    ExecutionStatus,
    Workflow,
    WorkflowEngine,
    WorkflowStatus,
    get_workflow_engine,
)
from src.core.workflows.conditions import ConditionEvaluator
from src.core.workflows.nodes import (
    ActionNode,
    ConditionNode,
    NodeType,
    TriggerNode,
    WorkflowNode,
)


class TestWorkflowNodes:
    """Tests para nodos de workflow."""

    @pytest.mark.asyncio
    async def test_trigger_node_execute(self):
        """Test ejecución de nodo trigger."""
        node = TriggerNode(
            id="trigger_1",
            config={"trigger_type": "manual", "initial_data": {"key": "value"}},
        )

        result = await node.execute({"context": "test"})

        assert result["success"] is True
        assert result["trigger_type"] == "manual"
        assert result["output"]["key"] == "value"

    @pytest.mark.asyncio
    async def test_action_node_execute(self):
        """Test ejecución de nodo acción."""
        node = ActionNode(
            id="action_1",
            config={
                "action_type": "log",
                "action_config": {"event_type": "test", "message": "Test message"},
            },
        )

        result = await node.execute({"context": "test"})

        assert result["success"] is True
        assert result["action_type"] == "log"

    @pytest.mark.asyncio
    async def test_condition_node_true_branch(self):
        """Test nodo condición - rama verdadera."""
        node = ConditionNode(
            id="condition_1",
            config={
                "condition_type": "equals",
                "condition_config": {"left": "value", "right": "value"},
                "true_branch": ["action_1"],
                "false_branch": ["action_2"],
            },
        )

        result = await node.execute({"value": "value"})

        assert result["success"] is True
        assert result["result"] is True
        assert result["branch"] == "true_branch"
        assert "action_1" in result["next_nodes"]

    @pytest.mark.asyncio
    async def test_condition_node_false_branch(self):
        """Test nodo condición - rama falsa."""
        node = ConditionNode(
            id="condition_1",
            config={
                "condition_type": "equals",
                "condition_config": {"left": "a", "right": "b"},
                "true_branch": ["action_1"],
                "false_branch": ["action_2"],
            },
        )

        result = await node.execute({})

        assert result["success"] is True
        assert result["result"] is False
        assert result["branch"] == "false_branch"


class TestConditionEvaluator:
    """Tests para el evaluador de condiciones."""

    def setup_method(self):
        """Setup."""
        self.evaluator = ConditionEvaluator()

    @pytest.mark.asyncio
    async def test_equals_true(self):
        """Test condición equals - verdadero."""
        result = await self.evaluator.evaluate(
            "equals", {"left": "test", "right": "test"}, {}
        )
        assert result is True

    @pytest.mark.asyncio
    async def test_equals_false(self):
        """Test condición equals - falso."""
        result = await self.evaluator.evaluate(
            "equals", {"left": "a", "right": "b"}, {}
        )
        assert result is False

    @pytest.mark.asyncio
    async def test_contains_string(self):
        """Test condición contains con string."""
        result = await self.evaluator.evaluate(
            "contains", {"left": "hello world", "right": "world"}, {}
        )
        assert result is True

    @pytest.mark.asyncio
    async def test_gt_number(self):
        """Test condición mayor que."""
        result = await self.evaluator.evaluate("gt", {"left": "10", "right": "5"}, {})
        assert result is True

    @pytest.mark.asyncio
    async def test_regex_match(self):
        """Test condición regex."""
        result = await self.evaluator.evaluate(
            "regex", {"left": "test@example.com", "pattern": r"^\S+@\S+\.\S+$"}, {}
        )
        assert result is True

    @pytest.mark.asyncio
    async def test_exists_true(self):
        """Test condición exists - existe."""
        result = await self.evaluator.evaluate(
            "exists", {"path": "data.value"}, {"data": {"value": "exists"}}
        )
        assert result is True

    @pytest.mark.asyncio
    async def test_all_conditions(self):
        """Test operador compuesto all."""
        result = await self.evaluator.evaluate(
            "all",
            {
                "conditions": [
                    {"operator": "equals", "config": {"left": "a", "right": "a"}},
                    {"operator": "equals", "config": {"left": "b", "right": "b"}},
                ]
            },
            {},
        )
        assert result is True

    @pytest.mark.asyncio
    async def test_any_conditions(self):
        """Test operador compuesto any."""
        result = await self.evaluator.evaluate(
            "any",
            {
                "conditions": [
                    {"operator": "equals", "config": {"left": "a", "right": "b"}},
                    {"operator": "equals", "config": {"left": "c", "right": "c"}},
                ]
            },
            {},
        )
        assert result is True


class TestWorkflow:
    """Tests para la clase Workflow."""

    def test_workflow_creation(self):
        """Test creación de workflow."""
        workflow = Workflow(
            id="wf_1",
            name="Test Workflow",
            description="A test workflow",
            status=WorkflowStatus.DRAFT,
        )

        assert workflow.id == "wf_1"
        assert workflow.name == "Test Workflow"
        assert workflow.status == WorkflowStatus.DRAFT

    def test_workflow_to_dict(self):
        """Test serialización a dict."""
        workflow = Workflow(
            id="wf_1", name="Test", description="Test", status=WorkflowStatus.ACTIVE
        )

        data = workflow.to_dict()

        assert data["id"] == "wf_1"
        assert data["status"] == "active"

    def test_get_node(self):
        """Test obtención de nodo por ID."""
        node1 = TriggerNode(id="trigger_1", config={})
        node2 = ActionNode(id="action_1", config={})

        workflow = Workflow(
            id="wf_1",
            name="Test",
            description="Test",
            status=WorkflowStatus.ACTIVE,
            nodes=[node1, node2],
        )

        assert workflow.get_node("trigger_1") == node1
        assert workflow.get_node("action_1") == node2
        assert workflow.get_node("nonexistent") is None

    def test_get_trigger_nodes(self):
        """Test obtención de nodos trigger."""
        trigger = TriggerNode(id="trigger_1", config={})
        action = ActionNode(id="action_1", config={})

        workflow = Workflow(
            id="wf_1",
            name="Test",
            description="Test",
            status=WorkflowStatus.ACTIVE,
            nodes=[trigger, action],
        )

        triggers = workflow.get_trigger_nodes()

        assert len(triggers) == 1
        assert triggers[0].id == "trigger_1"


class TestWorkflowEngine:
    """Tests para el motor de workflows."""

    def setup_method(self):
        """Setup con mocks."""
        with patch("Backend.core.workflows.engine.Path"):
            self.engine = WorkflowEngine.__new__(WorkflowEngine)
            self.engine._workflows = {}
            self.engine._executions = {}
            self.engine._running_executions = set()

    def test_create_workflow(self):
        """Test creación de workflow."""
        workflow = self.engine.create_workflow(
            name="Test Workflow", description="A test workflow"
        )

        assert workflow.id in self.engine._workflows
        assert workflow.name == "Test Workflow"
        assert workflow.status == WorkflowStatus.DRAFT

    def test_get_workflow(self):
        """Test obtención de workflow."""
        workflow = self.engine.create_workflow(name="Test")

        retrieved = self.engine.get_workflow(workflow.id)

        assert retrieved == workflow

    def test_list_workflows(self):
        """Test listado de workflows."""
        self.engine.create_workflow(name="WF 1")
        self.engine.create_workflow(name="WF 2")

        workflows = self.engine.list_workflows()

        assert len(workflows) == 2

    def test_update_workflow(self):
        """Test actualización de workflow."""
        workflow = self.engine.create_workflow(name="Original")

        updated = self.engine.update_workflow(
            workflow.id, name="Updated", status="active"
        )

        assert updated.name == "Updated"
        assert updated.status == WorkflowStatus.ACTIVE

    def test_delete_workflow(self):
        """Test eliminación de workflow."""
        workflow = self.engine.create_workflow(name="To Delete")

        result = self.engine.delete_workflow(workflow.id)

        assert result is True
        assert workflow.id not in self.engine._workflows

    @pytest.mark.asyncio
    async def test_execute_workflow_inactive(self):
        """Test ejecución de workflow inactivo."""
        workflow = self.engine.create_workflow(name="Test")
        # Workflow está en DRAFT por defecto

        result = await self.engine.execute_workflow(workflow.id)

        assert result is None  # No se ejecuta si no está activo

    @pytest.mark.asyncio
    async def test_execute_workflow_not_found(self):
        """Test ejecución de workflow inexistente."""
        result = await self.engine.execute_workflow("nonexistent")

        assert result is None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
