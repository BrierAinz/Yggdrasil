"""Dependencias compartidas para los routers FastAPI de Lilith."""
import os
from pathlib import Path

_orchestrator = None


def _project_root() -> Path:
    return Path(__file__).resolve().parent.parent.parent


def _internal_token() -> str | None:
    return os.getenv("LILITH_INTERNAL_TOKEN")


def get_orchestrator():
    """Singleton del Orchestrator (Planner + Registry + MemoryManager)."""
    global _orchestrator
    if _orchestrator is None:
        from src.core.learning import LearningEngine, LocalIntentClassifier
        from src.core.memory import MemoryManager
        from src.core.orchestrator import Orchestrator
        from src.core.planner import Planner
        from src.core.tools.registry import create_default_registry

        project_root = _project_root()
        registry = create_default_registry(project_root)
        memory_manager = MemoryManager(project_root)
        learning_engine = LearningEngine(memory_manager)
        local_classifier = LocalIntentClassifier(project_root)
        planner = Planner(
            memory_manager=memory_manager,
            learning_engine=learning_engine,
            local_intent_classifier=local_classifier,
        )
        _orchestrator = Orchestrator(planner, registry, memory_manager=memory_manager)
        try:
            from src.core.feedback_store import set_base_path

            set_base_path(project_root)
        except Exception:
            pass
    return _orchestrator
