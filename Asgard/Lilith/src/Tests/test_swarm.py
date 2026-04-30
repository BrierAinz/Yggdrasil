"""
Tests for Agent Swarm

v5.0: Tests unitarios para Task Planner, Swarm y Coordinator.
"""
import asyncio
from typing import Any, Dict
from unittest.mock import AsyncMock, Mock, patch

import pytest
from src.core.agents.coordinator import Coordinator, get_coordinator
from src.core.agents.swarm import Swarm, get_swarm
from src.core.agents.swarm.base import Agent, AgentConfig, AgentRole, AgentStatus
from src.core.agents.task_planner import SubTask, SubTaskStatus, TaskPlanner


class MockAgent(Agent):
    """Agente mock para testing."""

    def __init__(self, name: str, role: AgentRole, capabilities: list = None):
        config = AgentConfig(
            name=name, role=role, capabilities=capabilities or ["execute"]
        )
        super().__init__(config)
        self.execute_mock = AsyncMock()

    async def _execute_impl(self, task: Dict[str, Any], context: Dict[str, Any]) -> Any:
        return await self.execute_mock(task, context)


class TestTaskPlanner:
    """Tests para el planificador de tareas."""

    def setup_method(self):
        """Setup."""
        self.planner = TaskPlanner()

    @pytest.mark.asyncio
    async def test_plan_simple_task(self):
        """Test planificación de tarea simple."""
        subtasks = await self.planner.plan("Ejecutar comando simple")

        assert len(subtasks) >= 1
        assert any(st.task_type == "execute" for st in subtasks)

    @pytest.mark.asyncio
    async def test_plan_research_task(self):
        """Test planificación de tarea de investigación."""
        subtasks = await self.planner.plan("Investigar sobre Python async")

        assert any(st.task_type == "research" for st in subtasks)

    @pytest.mark.asyncio
    async def test_plan_code_task(self):
        """Test planificación de tarea de código."""
        subtasks = await self.planner.plan(
            "Implementar función de ordenamiento en Python"
        )

        task_types = [st.task_type for st in subtasks]
        assert "plan" in task_types or "implement" in task_types

    def test_get_execution_order(self):
        """Test orden de ejecución respetando dependencias."""
        subtasks = [
            SubTask(id="task_1", description="Task 1", task_type="A", dependencies=[]),
            SubTask(
                id="task_2",
                description="Task 2",
                task_type="B",
                dependencies=["task_1"],
            ),
            SubTask(
                id="task_3",
                description="Task 3",
                task_type="C",
                dependencies=["task_2"],
            ),
        ]

        order = self.planner.get_execution_order(subtasks)

        assert len(order) == 3
        assert order[0].id == "task_1"
        assert order[1].id == "task_2"
        assert order[2].id == "task_3"

    def test_get_next_executable(self):
        """Test obtención de siguiente subtarea ejecutable."""
        subtasks = [
            SubTask(id="task_1", description="Task 1", task_type="A", dependencies=[]),
            SubTask(
                id="task_2",
                description="Task 2",
                task_type="B",
                dependencies=["task_1"],
            ),
        ]

        # Sin completadas, solo task_1 es ejecutable
        next_task = self.planner.get_next_executable(subtasks, set())
        assert next_task.id == "task_1"

        # Con task_1 completada, task_2 es ejecutable
        next_task = self.planner.get_next_executable(subtasks, {"task_1"})
        assert next_task.id == "task_2"

    def test_estimate_effort(self):
        """Test estimación de esfuerzo."""
        simple = self.planner._estimate_effort("Hola")
        complex_task = self.planner._estimate_effort(
            "Implementar una arquitectura de microservicios compleja"
        )

        assert 1 <= simple <= 10
        assert 1 <= complex_task <= 10
        assert complex_task > simple


class TestSwarm:
    """Tests para el swarm de agentes."""

    def setup_method(self):
        """Setup."""
        self.swarm = Swarm()

    def test_register_agent(self):
        """Test registro de agente."""
        agent = MockAgent("agent_1", AgentRole.EXECUTOR)

        result = self.swarm.register(agent)

        assert result is True
        assert self.swarm.get_agent("agent_1") == agent
        assert "agent_1" in self.swarm._agents_by_role[AgentRole.EXECUTOR]

    def test_register_duplicate(self):
        """Test registro de agente duplicado."""
        agent = MockAgent("agent_1", AgentRole.EXECUTOR)

        self.swarm.register(agent)
        result = self.swarm.register(agent)

        assert result is False

    def test_unregister_agent(self):
        """Test desregistro de agente."""
        agent = MockAgent("agent_1", AgentRole.EXECUTOR)
        self.swarm.register(agent)

        result = self.swarm.unregister("agent_1")

        assert result is True
        assert self.swarm.get_agent("agent_1") is None

    def test_get_agents_by_role(self):
        """Test obtención de agentes por rol."""
        executor = MockAgent("exec_1", AgentRole.EXECUTOR)
        planner = MockAgent("plan_1", AgentRole.PLANNER)

        self.swarm.register(executor)
        self.swarm.register(planner)

        executors = self.swarm.get_agents_by_role(AgentRole.EXECUTOR)
        planners = self.swarm.get_agents_by_role(AgentRole.PLANNER)

        assert len(executors) == 1
        assert len(planners) == 1

    def test_find_agents_by_capability(self):
        """Test búsqueda por capacidad."""
        agent1 = MockAgent("agent_1", AgentRole.EXECUTOR, ["coding", "testing"])
        agent2 = MockAgent("agent_2", AgentRole.RESEARCHER, ["research"])

        self.swarm.register(agent1)
        self.swarm.register(agent2)

        coders = self.swarm.find_agents_by_capability("coding")

        assert len(coders) == 1
        assert coders[0].config.name == "agent_1"

    def test_get_available_agents(self):
        """Test obtención de agentes disponibles."""
        agent1 = MockAgent("agent_1", AgentRole.EXECUTOR)
        agent2 = MockAgent("agent_2", AgentRole.EXECUTOR)

        # agent1 ocupado
        agent1.status = AgentStatus.BUSY
        # agent2 disponible
        agent2.status = AgentStatus.IDLE

        self.swarm.register(agent1)
        self.swarm.register(agent2)

        available = self.swarm.get_available_agents()

        assert len(available) == 1
        assert available[0].config.name == "agent_2"

    def test_shared_context(self):
        """Test contexto compartido."""
        self.swarm.set_shared_context("key_1", "value_1")

        assert self.swarm.get_shared_context("key_1") == "value_1"

        all_context = self.swarm.get_all_shared_context()
        assert all_context["key_1"] == "value_1"

    @pytest.mark.asyncio
    async def test_execute_parallel(self):
        """Test ejecución paralela."""
        agent1 = MockAgent("agent_1", AgentRole.EXECUTOR)
        agent2 = MockAgent("agent_2", AgentRole.EXECUTOR)

        # Configurar mocks
        async def mock_execute(task, context):
            return {"result": f"done by {task.get('agent')}"}

        agent1.execute_mock = mock_execute
        agent2.execute_mock = mock_execute

        self.swarm.register(agent1)
        self.swarm.register(agent2)

        tasks = [
            ("agent_1", {"id": "task_1", "agent": "agent_1"}),
            ("agent_2", {"id": "task_2", "agent": "agent_2"}),
        ]

        results = await self.swarm.execute_parallel(tasks)

        assert len(results) == 2


class TestCoordinator:
    """Tests para el coordinador."""

    def setup_method(self):
        """Setup con mocks."""
        self.swarm = Swarm()
        self.planner = TaskPlanner()
        self.coordinator = Coordinator(self.swarm, self.planner)

    @pytest.mark.asyncio
    async def test_execute_simple_task(self):
        """Test ejecución de tarea simple."""
        agent = MockAgent("agent_1", AgentRole.EXECUTOR, ["execute"])
        agent.execute_mock.return_value = Mock(
            success=True, output="Result", agent_name="agent_1", task_id="task_1"
        )
        self.swarm.register(agent)

        result = await self.coordinator.execute("Ejecutar tarea simple")

        assert result.success is True
        assert len(result.agents_used) == 1

    @pytest.mark.asyncio
    async def test_execute_with_failure(self):
        """Test ejecución con falla."""
        agent = MockAgent("agent_1", AgentRole.EXECUTOR)
        agent.execute_mock.return_value = Mock(
            success=False,
            output=None,
            agent_name="agent_1",
            task_id="task_1",
            error="Failed",
        )
        self.swarm.register(agent)

        result = await self.coordinator.execute("Tarea que falla")

        assert result.success is False
        assert result.error is not None

    def test_select_agent_for_subtask(self):
        """Test selección de agente para subtarea."""
        agent = MockAgent("coder", AgentRole.EXECUTOR, ["coding"])
        self.swarm.register(agent)

        subtask = SubTask(
            id="task_1",
            description="Code something",
            task_type="code",
            required_capabilities=["coding"],
        )

        selected = self.coordinator._select_agent_for_subtask(subtask, None)

        assert selected is not None
        assert selected.config.name == "coder"

    def test_aggregate_results(self):
        """Test agregación de resultados."""
        subtasks = [
            SubTask(
                id="task_1",
                description="Task 1",
                task_type="A",
                status=SubTaskStatus.COMPLETED,
                result="Result 1",
            ),
            SubTask(
                id="task_2",
                description="Task 2",
                task_type="B",
                status=SubTaskStatus.COMPLETED,
                result="Result 2",
            ),
        ]

        results = [Mock(output="Result 1"), Mock(output="Result 2")]

        aggregated = self.coordinator._aggregate_results(subtasks, results)

        assert "Task 1" in aggregated
        assert "Task 2" in aggregated
        assert "Result 1" in aggregated
        assert "Result 2" in aggregated


class TestAgentBase:
    """Tests para la clase base de agentes."""

    def setup_method(self):
        """Setup."""
        self.config = AgentConfig(
            name="test_agent", role=AgentRole.EXECUTOR, capabilities=["test"]
        )

    @pytest.mark.asyncio
    async def test_execute_success(self):
        """Test ejecución exitosa."""
        agent = MockAgent("test_agent", AgentRole.EXECUTOR)
        agent.execute_mock.return_value = {"status": "ok"}

        result = await agent.execute({"id": "task_1", "description": "Test"}, {})

        assert result.success is True
        assert result.output == {"status": "ok"}
        assert agent.status == AgentStatus.IDLE

    @pytest.mark.asyncio
    async def test_execute_failure(self):
        """Test ejecución con error."""
        agent = MockAgent("test_agent", AgentRole.EXECUTOR)
        agent.execute_mock.side_effect = Exception("Test error")

        result = await agent.execute({"id": "task_1", "description": "Test"}, {})

        assert result.success is False
        assert "Test error" in result.error
        assert agent.status == AgentStatus.ERROR

    def test_can_handle(self):
        """Test verificación de capacidad."""
        agent = MockAgent("test_agent", AgentRole.EXECUTOR, ["coding", "testing"])

        assert agent.can_handle("coding") is True
        assert agent.can_handle("research") is False

    def test_get_stats(self):
        """Test obtención de estadísticas."""
        agent = MockAgent("test_agent", AgentRole.EXECUTOR)

        stats = agent.get_stats()

        assert stats["name"] == "test_agent"
        assert stats["role"] == "executor"
        assert stats["tasks_completed"] == 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
