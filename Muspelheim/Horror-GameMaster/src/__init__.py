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
    BraveryIndex,
    ExplorationStyle,
    ExtendedAction,
    FearVelocity,
    PatternAnalyzer,
    PredictionResult,
)
from procedural_generator import (
    ChainEvent,
    EntityBehavior,
    EntitySpawn,
    EventType,
    GameEvent2,
    NarrativeAct,
    ProceduralGenerator,
    SafeRoom,
    SceneTemplate,
    SceneType,
)
from tension_manager import (
    CooldownState,
    DecisionType,
    TensionDecision,
    TensionManager,
    TensionState,
)


__all__ = [
    "BraveryIndex",
    "ChainEvent",
    "CooldownState",
    "DecisionType",
    "EntityBehavior",
    "EntitySpawn",
    "EventType",
    "ExplorationStyle",
    "ExtendedAction",
    "FearVelocity",
    "GameEvent2",
    "NarrativeAct",
    # Pattern Analyzer
    "PatternAnalyzer",
    "PredictionResult",
    # Procedural Generator
    "ProceduralGenerator",
    "SafeRoom",
    "SceneTemplate",
    "SceneType",
    "TensionDecision",
    # Tension Manager
    "TensionManager",
    "TensionState",
]
