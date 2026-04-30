"""
Tests para el modo Soberano de Lilith.

Coverage:
- SovereignComplexityAnalyzer
- SovereignState
- SovereignMode (integración)
- VanaheimRouter
"""
import sys
from pathlib import Path

import pytest

# Ajustar path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from core.sovereign_complexity import (
    ExecutionMode,
    SovereignComplexityAnalyzer,
    SovereignComplexityResult,
)
from core.sovereign_mode import SovereignMode
from core.sovereign_state import SovereignState, SovereignStatus
from core.vanaheim_router import VanaheimRouter


class TestSovereignComplexityAnalyzer:
    """Tests para el analizador de complejidad soberana."""

    def test_analyze_trivial_task(self):
        """Tarea trivial debe retornar DELEGATE."""
        analyzer = SovereignComplexityAnalyzer()
        result = analyzer.analyze_for_sovereign("hola")

        assert result.should_delegate is True
        assert result.should_orchestrate is False
        assert result.sovereign_score < 40
        assert result.recommended_mode == ExecutionMode.DELEGATE

    def test_analyze_simple_task(self):
        """Tarea simple debe retornar DELEGATE."""
        analyzer = SovereignComplexityAnalyzer()
        result = analyzer.analyze_for_sovereign("qué hora es")

        assert result.should_delegate is True
        assert result.sovereign_score < 40

    def test_analyze_complex_task(self):
        """Tarea compleja debe retornar ORCHESTRATE."""
        analyzer = SovereignComplexityAnalyzer()
        result = analyzer.analyze_for_sovereign(
            "diseña una arquitectura de microservicios completa con kubernetes, "
            "incluyendo service mesh, observabilidad, y estrategia de despliegue"
        )

        assert result.should_orchestrate is True
        assert result.sovereign_score >= 60
        assert result.recommended_mode == ExecutionMode.ORCHESTRATE

    def test_analyze_task_with_dependencies(self):
        """Tarea con dependencias debe aumentar score."""
        analyzer = SovereignComplexityAnalyzer()
        result = analyzer.analyze_for_sovereign(
            "primero investiga sobre X, luego analiza los resultados, "
            "después compara con Y y finalmente genera un reporte"
        )

        assert result.factors["has_dependencies"] is True
        assert result.factors["estimated_steps"] > 1

    def test_analyze_multi_agent_task(self):
        """Tarea que requiere múltiples agentes debe aumentar score."""
        analyzer = SovereignComplexityAnalyzer()
        result = analyzer.analyze_for_sovereign(
            "investiga y analiza este código, luego documenta los hallazgos"
        )

        assert result.factors["requires_multiple_agents"] is True


class TestSovereignState:
    """Tests para el estado soberano."""

    def test_is_lilith_busy_initially_false(self):
        """Inicialmente Lilith no está busy."""
        state = SovereignState()
        assert state.is_lilith_busy() is False

    def test_is_lilith_busy_with_projects(self):
        """Lilith está busy cuando hay proyectos activos."""
        state = SovereignState()
        state.start_project("test1", "Test Project 1")
        state.start_project("test2", "Test Project 2")

        assert state.is_lilith_busy() is True
        assert state.get_status() == SovereignStatus.BUSY_PROJECT

    def test_project_lifecycle(self):
        """Ciclo de vida de un proyecto."""
        state = SovereignState()

        # Iniciar proyecto
        result = state.start_project("test1", "Test", estimated_nodes=5)
        assert result is True

        # Verificar que está activo
        assert "test1" in [p.project_id for p in state.get_snapshot().active_projects]

        # Finalizar proyecto
        state.end_project("test1")
        assert state.is_lilith_busy() is False

    def test_should_delegate_when_busy(self):
        """Debe delegar cuando está busy y la tarea es simple."""
        state = SovereignState()
        state.start_project("big_project", "Big Project", estimated_nodes=20)

        should_delegate, reason = state.should_delegate_task(30, "simple task")
        assert should_delegate is True
        assert "busy" in reason.lower()

    def test_should_not_delegate_complex_when_busy(self):
        """No debe delegar tareas complejas incluso si está busy."""
        state = SovereignState()
        state.start_project("big_project", "Big Project", estimated_nodes=20)

        should_delegate, reason = state.should_delegate_task(85, "complex task")
        assert should_delegate is False
        assert "compleja" in reason.lower() or "complex" in reason.lower()


class TestVanaheimRouter:
    """Tests para el router de Vanaheim."""

    def test_select_agent_conversation(self):
        """Debe seleccionar Freya para conversación."""
        router = VanaheimRouter()
        agent, confidence = router.select_agent("hola, cómo estás?")

        assert agent == "freya"
        assert confidence > 0

    def test_select_agent_search(self):
        """Debe seleccionar Heimdall para búsquedas."""
        router = VanaheimRouter()
        agent, confidence = router.select_agent("busca información sobre Python")

        assert agent == "heimdall"

    def test_select_agent_code(self):
        """Debe seleccionar Eir para código."""
        router = VanaheimRouter()
        agent, confidence = router.select_agent("explica este código")

        assert agent == "eir"

    def test_get_agent_for_tool(self):
        """Debe mapear tools a agentes correctamente."""
        router = VanaheimRouter()

        assert router.get_agent_for_tool("web_search") == "heimdall"
        assert router.get_agent_for_tool("generate_reply") == "freya"


class TestSovereignMode:
    """Tests de integración para el modo soberano."""

    def test_decide_mode_delegate(self):
        """Decisión DELEGATE para tarea simple."""
        sovereign = SovereignMode()
        mode, metadata = sovereign.decide_mode("hola")

        assert mode == ExecutionMode.DELEGATE
        assert metadata["complexity_score"] < 40

    def test_decide_mode_orchestrate(self):
        """Decisión ORCHESTRATE para tarea compleja."""
        sovereign = SovereignMode()
        mode, metadata = sovereign.decide_mode(
            "diseña un sistema completo de autenticación con OAuth2, "
            "incluyendo refresh tokens, rate limiting y auditoría"
        )

        assert mode == ExecutionMode.ORCHESTRATE
        assert metadata["complexity_score"] >= 60

    def test_force_patterns(self):
        """Patrones forzados deben sobreescribir decisión."""
        sovereign = SovereignMode()

        # Forzar DELEGATE
        mode, metadata = sovereign.decide_mode("hola")
        assert mode == ExecutionMode.DELEGATE
        assert "Force pattern" in metadata["reason"]

    def test_stats_initially_zero(self):
        """Stats inician en cero."""
        sovereign = SovereignMode()
        stats = sovereign.get_stats()

        assert stats["delegate_count"] == 0
        assert stats["orchestrate_count"] == 0


class TestIntegration:
    """Tests de integración end-to-end."""

    def test_full_flow_simple_task(self):
        """Flujo completo para tarea simple."""
        # Crear componentes
        analyzer = SovereignComplexityAnalyzer()
        state = SovereignState()
        router = VanaheimRouter()

        # Tarea simple
        task = "qué hora es"
        complexity = analyzer.analyze_for_sovereign(task)

        # Verificar que debe delegar
        assert complexity.should_delegate is True

        # Seleccionar agente
        agent, _ = router.select_agent(task)
        assert agent in ["freya", "heimdall"]

    def test_full_flow_complex_task(self):
        """Flujo completo para tarea compleja."""
        analyzer = SovereignComplexityAnalyzer()
        state = SovereignState()

        # Tarea compleja
        task = (
            "analiza completamente este proyecto, identifica deuda técnica, "
            "propón refactorizaciones y genera un plan de migración"
        )
        complexity = analyzer.analyze_for_sovereign(task)

        # Verificar que debe orquestar
        assert complexity.should_orchestrate is True

        # Verificar que el estado no afecta la decisión
        state.start_project("other", "Other")
        should_delegate, _ = state.should_delegate_task(
            complexity.sovereign_score, task
        )
        assert should_delegate is False  # No delegar tareas complejas


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
