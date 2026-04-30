"""
Learning Module - Auto-Discovery & Learning

v5.0-Fase4B: Detección de patrones, sugerencias inteligentes y analytics.
"""

# Legacy (mantener compatibilidad)
from .learning_engine import LearningEngine
from .local_classifier import LocalIntentClassifier

# Nuevo sistema v5.0-Fase4B
from .pattern_discovery import (
    Action,
    Pattern,
    PatternConfidence,
    PatternDiscovery,
    PatternType,
    get_pattern_discovery,
)
from .suggestion_engine import (
    Suggestion,
    SuggestionEngine,
    SuggestionPriority,
    SuggestionType,
    get_suggestion_engine,
)
from .usage_analytics import UsageAnalytics, get_analytics

__all__ = [
    # Legacy
    "LearningEngine",
    "LocalIntentClassifier",
    # Pattern Discovery
    "PatternDiscovery",
    "Pattern",
    "PatternType",
    "PatternConfidence",
    "Action",
    "get_pattern_discovery",
    # Suggestion Engine
    "SuggestionEngine",
    "Suggestion",
    "SuggestionType",
    "SuggestionPriority",
    "get_suggestion_engine",
    # Analytics
    "UsageAnalytics",
    "get_analytics",
]
