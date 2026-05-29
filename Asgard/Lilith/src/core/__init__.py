"""
Core Module - Lilith AI Core.

Provides core functionality for session management, task tracking,
and personality modes.
"""

# Attention Stack
from .attention_stack import (
    AttentionItem,
    AttentionStack,
    ItemStatus,
    format_stack_for_prompt,
    get_attention_stack,
)

# Orchestrator with Stack
from .orchestration.orchestrator_v2 import (
    OrchestratorV2,
    enrich_context_for_planner,
    extract_and_push_tasks,
)

# Personality Mode Manager
from .persona.manager import (
    ModeTransition,
    PersonalityMode,
    PersonalityModeManager,
    detect_and_set_mode,
    get_mode_for_session,
    get_personality_mode_manager,
    set_mode_for_session,
)

# Task Extractor
from .task_extractor import (
    ExtractedTask,
    TaskExtractor,
    extract_tasks,
    extract_tasks_simple,
    get_task_extractor,
)

__all__ = [
    # Attention Stack
    "AttentionStack",
    "AttentionItem",
    "ItemStatus",
    "get_attention_stack",
    "format_stack_for_prompt",
    # Task Extractor
    "TaskExtractor",
    "ExtractedTask",
    "get_task_extractor",
    "extract_tasks",
    "extract_tasks_simple",
    # Personality Modes
    "PersonalityMode",
    "ModeTransition",
    "PersonalityModeManager",
    "get_personality_mode_manager",
    "get_mode_for_session",
    "set_mode_for_session",
    "detect_and_set_mode",
    # Orchestrator
    "OrchestratorV2",
    "enrich_context_for_planner",
    "extract_and_push_tasks",
]
