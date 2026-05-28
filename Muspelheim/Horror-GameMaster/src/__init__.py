"""
Horror GameMaster — Procedural Terror Engine

A text-based horror game engine that adapts to player fears,
generates procedural horror narratives, and creates personalized
terror experiences using LLM integration.

Modules:
    memory            — Player memory, fear profiles, embeddings
    pattern_analyzer  — Behavioral analysis, fear fingerprinting
    procedural_generator — Scenes, events, entities, narrative
    tension_manager   — Dynamic tension, pacing, escalation
    llm_engine        — LLM integration for narrative generation
    gamemaster        — Main orchestrator
"""

from pattern_analyzer import (
    PatternAnalyzer,
    ExtendedAction,
    ExplorationStyle,
    BraveryIndex,
    FearVelocity,
    PredictionResult,
)
from procedural_generator import (
    ProceduralGenerator,
    SceneType,
    EventType,
    NarrativeAct,
    EntityBehavior,
    SceneTemplate,
    GameEvent2,
    ChainEvent,
    SafeRoom,
    EntitySpawn,
)
from tension_manager import (
    TensionManager,
    TensionState,
    CooldownState,
    DecisionType,
    TensionDecision,
)

__all__ = [
    # Pattern Analyzer
    "PatternAnalyzer",
    "ExtendedAction",
    "ExplorationStyle",
    "BraveryIndex",
    "FearVelocity",
    "PredictionResult",
    # Procedural Generator
    "ProceduralGenerator",
    "SceneType",
    "EventType",
    "NarrativeAct",
    "EntityBehavior",
    "SceneTemplate",
    "GameEvent2",
    "ChainEvent",
    "SafeRoom",
    "EntitySpawn",
    # Tension Manager
    "TensionManager",
    "TensionState",
    "CooldownState",
    "DecisionType",
    "TensionDecision",
]
