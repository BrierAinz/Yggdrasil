"""
Lilith - Self-Improvement Engine
Analyzes agent sessions to detect patterns and suggest improvements
"""

import json
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from src.observability.session_logger import SessionLogger
from src.observability.telemetry import AgentTelemetry


@dataclass
class ImprovementSuggestion:
    """Represents a suggested improvement for the agent"""

    suggestion_id: str
    category: str  # 'tool', 'workflow', 'persona', 'prompt'
    description: str
    reasoning: str
    confidence: float  # 0.0 to 1.0
    severity: str  # 'low', 'medium', 'high', 'critical'
    auto_applicable: bool = False
    requires_review: bool = True
    example_session_id: Optional[str] = None
    suggested_changes: Optional[Dict[str, Any]] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "suggestion_id": self.suggestion_id,
            "category": self.category,
            "description": self.description,
            "reasoning": self.reasoning,
            "confidence": self.confidence,
            "severity": self.severity,
            "auto_applicable": self.auto_applicable,
            "requires_review": self.requires_review,
            "example_session_id": self.example_session_id,
            "suggested_changes": self.suggested_changes,
            "created_at": time.time(),
        }


@dataclass
class PatternAnalysis:
    """Analysis result for pattern detection"""

    pattern_type: str  # 'error', 'success', 'inefficiency'
    frequency: int
    affected_tools: List[str]
    common_error: Optional[str] = None
    success_rate_before: Optional[float] = None
    success_rate_after: Optional[float] = None
    recommended_action: Optional[str] = None


class SelfImprovementEngine:
    """
    Analyzes agent sessions to identify improvement opportunities.

    Features:
    - Pattern detection (errors recurrentes)
    - Performance analysis
    - Workflow generation
    - Auto-update suggestions (persona, prompts)
    """

    def __init__(self):
        """Initialize improvement engine"""
        self.session_logger = SessionLogger()
        self.telemetry = AgentTelemetry()

        # Configuration
        self.suggestions_file = Path(
            "D:\\Proyectos\\Lilith\\Core\\memory\\improvement_suggestions.jsonl"
        )
        self.suggestions_file.parent.mkdir(parents=True, exist_ok=True)

        # Learned patterns cache
        self._learned_patterns: Dict[str, PatternAnalysis] = {}

    def analyze_recent_sessions(
        self, session_limit: int = 50
    ) -> List[ImprovementSuggestion]:
        """
        Analyze recent sessions to find improvement opportunities

        Returns:
            List of improvement suggestions ranked by confidence and severity
        """
        suggestions = []

        # Get recent sessions
        recent_sessions = self.session_logger.get_recent_sessions(limit=session_limit)
        print(f"[SelfImprovement] Analyzing {len(recent_sessions)} sessions...")

        # 1. Detect error patterns
        error_pattern_suggestions = self._detect_error_patterns(recent_sessions)
        suggestions.extend(error_pattern_suggestions)

        # 2. Analyze tool performance
        performance_suggestions = self._analyze_tool_performance()
        suggestions.extend(performance_suggestions)

        # 3. Identify workflow opportunities
        workflow_suggestions = self._identify_workflow_opportunities(recent_sessions)
        suggestions.extend(workflow_suggestions)

        # 4. Analyze persona effectiveness
        persona_suggestions = self._analyze_persona_effectiveness()
        suggestions.extend(persona_suggestions)

        # Sort by confidence Ã— severity
        suggestions.sort(
            key=lambda s: (s.confidence * self._severity_weight(s.severity)),
            reverse=True,
        )

        print(f"[SelfImprovement] Generated {len(suggestions)} suggestions")
        return suggestions

    def _severity_weight(self, severity: str) -> float:
        """Convert severity to numeric weight"""
        weights = {"critical": 1.0, "high": 0.7, "medium": 0.4, "low": 0.1}
        return weights.get(severity, 0.1)

    def _detect_error_patterns(self, sessions: List) -> List[ImprovementSuggestion]:
        """Detect recurring error patterns"""
        suggestions = []

        # Get tool usage statistics
        tool_stats = self.telemetry.get_tool_statistics()

        for tool_name, stats in tool_stats.items():
            # Check for high failure rate
            if stats["success_rate_percent"] < 60:
                # Investigate specific errors
                error_counts = {}
                for entry in self.telemetry._historical_data:
                    if (
                        entry.get("type") == "tool_usage"
                        and entry["data"]["tool_name"] == tool_name
                        and not entry["data"]["success"]
                    ):
                        error = entry["data"].get("error_message", "Unknown")
                        error_counts[error] = error_counts.get(error, 0) + 1

                # Find most common error
                if error_counts:
                    most_common_error = max(error_counts.items(), key=lambda x: x[1])

                    suggestion = ImprovementSuggestion(
                        suggestion_id=f"error-pattern-{tool_name}-{int(time.time())}",
                        category="tool",
                        description=f"High failure rate for {tool_name}",
                        reasoning=f"Tool '{tool_name}' has {stats['success_rate_percent']:.1f}% success rate. "
                        f"Most common error: '{most_common_error[0]}' "
                        f"(occurred {most_common_error[1]} times)",
                        confidence=min(
                            0.95, (100 - stats["success_rate_percent"]) / 100
                        ),
                        severity="high"
                        if stats["success_rate_percent"] < 40
                        else "medium",
                        example_session_id=None,  # Could find specific session
                        suggested_changes={
                            "tool": tool_name,
                            "suggested_fix": "Review error handling and add retries",
                            "common_error": most_common_error[0],
                        },
                    )
                    suggestions.append(suggestion)

        return suggestions

    def _analyze_tool_performance(self) -> List[ImprovementSuggestion]:
        """Analyze tool performance and suggest optimizations"""
        suggestions = []

        tool_stats = self.telemetry.get_tool_statistics()

        for tool_name, stats in tool_stats.items():
            # Check for slow performance
            if stats["avg_duration_ms"] > 5000:  # 5 seconds threshold
                suggestion = ImprovementSuggestion(
                    suggestion_id=f"performance-{tool_name}-{int(time.time())}",
                    category="tool",
                    description=f"Optimize {tool_name} performance",
                    reasoning=f"Tool '{tool_name}' average latency is {stats['avg_duration_ms']:.0f}ms "
                    f"(called {stats['calls']} times). Consider caching or parallelization.",
                    confidence=0.8,
                    severity="medium",
                    suggested_changes={
                        "tool": tool_name,
                        "current_avg_latency_ms": stats["avg_duration_ms"],
                        "suggested_optimization": "Implement caching for repeated operations",
                    },
                )
                suggestions.append(suggestion)

            # Check for excessive usage
            if stats["calls"] > 10:  # More than 10 calls in recent window
                suggestion = ImprovementSuggestion(
                    suggestion_id=f"usage-pattern-{tool_name}-{int(time.time())}",
                    category="workflow",
                    description=f"Create workflow for repeated {tool_name} usage",
                    reasoning=f"Tool '{tool_name}' was called {stats['calls']} times in recent sessions. "
                    f"A pre-built workflow could reduce latency.",
                    confidence=0.75,
                    severity="low",
                    suggested_changes={
                        "tool": tool_name,
                        "usage_count": stats["calls"],
                        "action": "Consider creating reusable workflow",
                    },
                )
                suggestions.append(suggestion)

        return suggestions

    def _identify_workflow_opportunities(
        self, sessions: List
    ) -> List[ImprovementSuggestion]:
        """Identify opportunities for new workflows based on repeated patterns"""
        suggestions = []

        # This would analyze interaction patterns to find repeated sequences
        # For now, we'll implement a simple version

        # Analyze recent sessions for repeated tool combinations
        tool_combinations = {}

        for session in sessions[:20]:  # Focus on recent 20 sessions
            session_id = session.session_id
            interactions = self.session_logger.get_session_interactions(session_id)

            # Look for Research â†’ WebBrowser pattern
            research_used = any("Research" in str(i.content) for i in interactions)
            browser_used = any("WebBrowser" in str(i.content) for i in interactions)

            if research_used and browser_used:
                combo_key = "researchâ†’browser"
                tool_combinations[combo_key] = tool_combinations.get(combo_key, 0) + 1

        # Suggest workflow for common combinations
        for combo, count in tool_combinations.items():
            if count >= 3:  # Threshold
                suggestion = ImprovementSuggestion(
                    suggestion_id=f"workflow-{combo}-{int(time.time())}",
                    category="workflow",
                    description=f"Create workflow for {combo} pattern",
                    reasoning=f"The pattern '{combo}' was used {count} times in recent sessions. "
                    f"This suggests a reusable workflow would be valuable.",
                    confidence=0.7,
                    severity="low",
                    suggested_changes={
                        "pattern": combo,
                        "usage_count": count,
                        "workflow_name": f"Auto-Research-Workflow-{combo}",
                    },
                )
                suggestions.append(suggestion)

        return suggestions

    def _analyze_persona_effectiveness(self) -> List[ImprovementSuggestion]:
        """Analyze persona effectiveness and suggest updates"""
        suggestions = []

        # Get overall stats
        overall_stats = self.session_logger.get_overall_stats()

        # Check session completion rate
        status_breakdown = overall_stats.get("status_breakdown", {})
        total_sessions = overall_stats.get("total_sessions", 0)

        if total_sessions > 0:
            failed_sessions = status_breakdown.get("failed", 0)
            failure_rate = failed_sessions / total_sessions

            if failure_rate > 0.3:  # More than 30% failure
                suggestion = ImprovementSuggestion(
                    suggestion_id=f"persona-{int(time.time())}",
                    category="persona",
                    description="Update persona.json with better instructions",
                    reasoning=f"Session failure rate is {failure_rate:.1%}. "
                    f"Consider updating the agent's persona to include clearer "
                    f"instructions or additional examples for common tasks.",
                    confidence=failure_rate,
                    severity="high",
                    suggested_changes={
                        "current_failure_rate": failure_rate,
                        "suggested_action": "Review failed sessions and add clarifications to persona",
                        "priority_areas": ["tool_usage_examples", "error_handling"],
                    },
                )
                suggestions.append(suggestion)

        return suggestions

    def apply_suggestion(self, suggestion: ImprovementSuggestion) -> bool:
        """
        Apply an improvement suggestion (if auto_applicable)
        Returns: True if applied successfully
        """
        if not suggestion.auto_applicable:
            print(
                f"[SelfImprovement] Suggestion requires manual review: {suggestion.suggestion_id}"
            )
            return False

        # This is where we'd actually apply changes
        # For now, we'll just log that it was attempted
        print(f"[SelfImprovement] Applying suggestion: {suggestion.description}")

        # Persist the application attempt
        self._persist_suggestion(suggestion, "applied")

        return True

    def save_suggestions_for_review(self, suggestions: List[ImprovementSuggestion]):
        """Save suggestions to file for human review"""
        for suggestion in suggestions:
            self._persist_suggestion(suggestion, "pending_review")

        print(f"[SelfImprovement] Saved {len(suggestions)} suggestions for review")
        print(f"Location: {self.suggestions_file}")

    def _persist_suggestion(self, suggestion: ImprovementSuggestion, status: str):
        """Persist suggestion to file"""
        entry = {
            "status": status,
            "applied_at": time.time() if status == "applied" else None,
            "suggestion": suggestion.to_dict(),
        }

        with open(self.suggestions_file, "a", encoding="utf-8") as f:
            import json

            f.write(json.dumps(entry, ensure_ascii=False) + "\n")

    def get_pending_suggestions(self) -> List[Dict[str, Any]]:
        """Get all suggestions pending review"""
        suggestions = []
        if not self.suggestions_file.exists():
            return suggestions

        with open(self.suggestions_file, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    entry = json.loads(line)
                    if entry.get("status") == "pending_review":
                        suggestions.append(entry)

        return suggestions


# ============================================================================
# USAGE
# ============================================================================

if __name__ == "__main__":
    print("Self-Improvement Engine Demo")
    print("=" * 70)

    engine = SelfImprovementEngine()

    # Analyze recent sessions
    print("\n[1] Analyzing recent sessions...")
    suggestions = engine.analyze_recent_sessions(session_limit=5)

    # Display suggestions
    print(f"\n[2] Generated {len(suggestions)} suggestions:")

    for i, suggestion in enumerate(suggestions[:3], 1):
        print(f"\n#{i}: {suggestion.description}")
        print(f"   Category: {suggestion.category}")
        print(f"   Severity: {suggestion.severity}")
        print(f"   Confidence: {suggestion.confidence:.1%}")
        print(f"   Reasoning: {suggestion.reasoning[:60]}...")

        if suggestion.auto_applicable:
            print(f"   [AUTO] Can be applied automatically")
        else:
            print(f"   [REVIEW] Requires manual review")

    # Save for review
    engine.save_suggestions_for_review(suggestions)

    print("\n" + "=" * 70)
    print("Demo complete! Suggestions saved for review.")
    print("=" * 70)
