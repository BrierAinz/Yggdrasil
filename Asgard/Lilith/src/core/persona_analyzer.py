"""
Lilith - Persona Analyzer
Analyzes successful commands to identify effective patterns for persona updates
"""

import json
import re
import time
from collections import Counter, defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from src.observability.session_logger import SessionLogger
from src.observability.telemetry import AgentTelemetry


@dataclass
class CommandPattern:
    """Represents a pattern in successful commands"""

    pattern_id: str
    command_type: str  # "@plan", "@git", "@run", "chat"
    user_phrases: List[str]  # How users phrase this intent
    success_rate: float
    frequency: int
    average_confidence: float
    common_constraints: List[str]
    suggested_action: str
    example_sessions: List[str]
    first_seen: float
    last_seen: float

    def to_dict(self) -> Dict[str, Any]:
        return {
            "pattern_id": self.pattern_id,
            "command_type": self.command_type,
            "user_phrases": self.user_phrases,
            "success_rate": round(self.success_rate, 3),
            "frequency": self.frequency,
            "average_confidence": round(self.average_confidence, 3),
            "common_constraints": self.common_constraints,
            "suggested_action": self.suggested_action,
            "example_sessions": self.example_sessions,
            "first_seen": self.first_seen,
            "last_seen": self.last_seen,
            "timespan_days": (self.last_seen - self.first_seen) / 86400,
        }


@dataclass
class PersonaLearning:
    """Represents learning to apply to persona"""

    learning_id: str
    category: str
    command_patterns: List[CommandPattern]
    extracted_instructions: List[str]
    confidence_score: float
    evidence_summary: Dict[str, Any]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "learning_id": self.learning_id,
            "category": self.category,
            "patterns_analyzed": len(self.command_patterns),
            "confidence_score": round(self.confidence_score, 3),
            "extracted_instructions": self.extracted_instructions,
            "evidence_summary": self.evidence_summary,
            "timestamp": time.time(),
        }


class PersonaAnalyzer:
    """
    Analyzes successful commands to identify patterns for persona updates

    Process:
    1. Query SessionLogger for successful sessions
    2. Categorize commands by type (@plan, @git, @run, chat)
    3. Extract patterns in phrasing, constraints, structure
    4. Correlate patterns with success rates
    5. Generate learning recommendations
    """

    def __init__(self):
        """Initialize with data sources"""
        self.session_logger = SessionLogger()
        self.telemetry = AgentTelemetry()

        # Configuration
        self.min_session_sample = 10  # Minimum sessions to analyze
        self.min_pattern_frequency = 3  # Pattern must appear at least 3 times
        self.success_rate_threshold = 0.75  # Consider commands >75% success
        self.lookback_days = 7  # Analyze last 7 days

    def analyze_all_patterns(self, session_limit: int = 100) -> List[PersonaLearning]:
        """Analyze all command patterns across categories"""
        print(f"[PersonaAnalyzer] Analyzing up to {session_limit} recent sessions...")

        # Get recent successful sessions
        sessions = self._get_successful_sessions(limit=session_limit)
        print(f"[PersonaAnalyzer] Found {len(sessions)} successful sessions")

        if len(sessions) < self.min_session_sample:
            print(
                f"[PersonaAnalyzer] Insufficient data (need {self.min_session_sample}, got {len(sessions)})"
            )
            return []

        # Categorize by command type
        categorized = self._categorize_sessions(sessions)
        print(f"[PersonaAnalyzer] Categorized into {len(categorized)} command types")

        # Analyze patterns per category
        learnings = []
        for command_type, sessions_list in categorized.items():
            if len(sessions_list) >= self.min_pattern_frequency:
                learning = self._analyze_category(command_type, sessions_list)
                if learning:
                    learnings.append(learning)

        print(f"[PersonaAnalyzer] Generated {len(learnings)} learning insights")
        return learnings

    def _get_successful_sessions(self, limit: int) -> List:
        """Get recent sessions with high success rates"""
        sessions = self.session_logger.get_recent_sessions(limit=limit)

        successful = []
        for session in sessions:
            # Check if session was successful
            if session.final_status == "success":
                # Also check tool success rate
                tool_stats = self.session_logger.get_tool_usage_stats(
                    session.session_id
                )
                if tool_stats:
                    # Calculate overall success rate
                    total_calls = sum(stats["calls"] for stats in tool_stats.values())
                    if total_calls > 0:
                        total_successes = sum(
                            stats["calls"] * (stats["success_rate_percent"] / 100)
                            for stats in tool_stats.values()
                        )
                        success_rate = total_successes / total_calls

                        if success_rate >= self.success_rate_threshold:
                            successful.append(session)

        return successful

    def _categorize_sessions(self, sessions: List) -> Dict[str, List]:
        """Categorize sessions by command type"""
        categorized = defaultdict(list)

        for session in sessions:
            if session.user_intent:
                if session.user_intent.startswith("@plan"):
                    categorized["@plan"].append(session)
                elif session.user_intent.startswith("@git"):
                    categorized["@git"].append(session)
                elif session.user_intent.startswith("@run"):
                    categorized["@run"].append(session)
                else:
                    categorized["chat"].append(session)

        return categorized

    def _analyze_category(
        self, command_type: str, sessions: List
    ) -> Optional[PersonaLearning]:
        """Analyze patterns within a command category"""
        print(f"[PersonaAnalyzer] Analyzing {command_type} ({len(sessions)} sessions)")

        # Extract command phrases
        phrases = []
        command_to_session = {}

        for session in sessions:
            if session.user_intent:
                phrases.append(session.user_intent)
                command_to_session[session.user_intent] = session.session_id

        if not phrases:
            return None

        # Find patterns in phrasing
        patterns = self._extract_patterns(phrases, command_to_session)

        if not patterns:
            return None

        # Generate learning
        learning = PersonaLearning(
            learning_id=f"learning_{command_type}_{int(time.time())}",
            category=command_type,
            command_patterns=patterns,
            extracted_instructions=[],  # Will be filled by InstructionExtractor
            confidence_score=self._calculate_confidence(patterns),
            evidence_summary={
                "sessions_analyzed": len(sessions),
                "patterns_found": len(patterns),
                "command_sample": phrases[:5],
            },
        )

        return learning

    def _extract_patterns(
        self, phrases: List[str], session_map: Dict[str, str]
    ) -> List[CommandPattern]:
        """Extract patterns from command phrases"""
        patterns = []

        # Group similar phrases
        phrase_groups = self._group_similar_phrases(phrases)

        for group_key, phrases_list in phrase_groups.items():
            if len(phrases_list) >= self.min_pattern_frequency:
                # Calculate success rate for this pattern
                success_rate, avg_confidence = self._calculate_pattern_stats(
                    [session_map[phrase] for phrase in phrases_list]
                )

                # Extract constraints
                constraints = self._extract_constraints(phrases_list)

                pattern = CommandPattern(
                    pattern_id=f"pattern_{hash(group_key) & 0xFFFFFFFF}",
                    command_type=self._detect_command_type(phrases_list[0]),
                    user_phrases=phrases_list,
                    success_rate=success_rate,
                    frequency=len(phrases_list),
                    average_confidence=avg_confidence,
                    common_constraints=constraints,
                    suggested_action=self._suggest_action(group_key),
                    example_sessions=[
                        session_map[phrase] for phrase in phrases_list[:3]
                    ],
                    first_seen=min(
                        self._get_session_time(session_map[phrase])
                        for phrase in phrases_list
                    ),
                    last_seen=max(
                        self._get_session_time(session_map[phrase])
                        for phrase in phrases_list
                    ),
                )

                patterns.append(pattern)

        return patterns

    def _group_similar_phrases(self, phrases: List[str]) -> Dict[str, List[str]]:
        """Group similar command phrases"""
        groups = defaultdict(list)

        for phrase in phrases:
            # Extract the core intent (remove @ commands)
            core_intent = self._extract_core_intent(phrase)

            # Find or create group
            matched = False
            for group_key in list(groups.keys()):
                if self._phrase_similarity(core_intent, group_key) > 0.7:
                    groups[group_key].append(phrase)
                    matched = True
                    break

            if not matched:
                groups[core_intent].append(phrase)

        return groups

    def _extract_core_intent(self, phrase: str) -> str:
        """Extract core intent from a command"""
        # Remove @ commands if present
        if phrase.startswith("@"):
            # Remove @command prefix
            parts = phrase.split(" ", 1)
            if len(parts) > 1:
                return parts[1].lower().strip()
            return ""

        return phrase.lower().strip()

    def _phrase_similarity(self, phrase1: str, phrase2: str) -> float:
        """Calculate similarity between two phrases"""
        # Simple similarity based on word overlap
        words1 = set(phrase1.split())
        words2 = set(phrase2.split())

        if not words1 or not words2:
            return 0.0

        overlap = len(words1.intersection(words2))
        total = len(words1.union(words2))

        return overlap / total

    def _calculate_pattern_stats(self, session_ids: List[str]) -> Tuple[float, float]:
        """Calculate success rate and average confidence for a pattern"""
        total_sessions = len(session_ids)
        if total_sessions == 0:
            return 0.0, 0.0

        success_count = 0
        confidence_sum = 0.0

        for session_id in session_ids:
            tool_stats = self.session_logger.get_tool_usage_stats(session_id)
            if tool_stats:
                # Session success if all tools succeeded
                session_success = all(
                    stats["success_rate_percent"] > 50
                    for stats in tool_stats.values()
                    if stats["calls"] > 0
                )

                if session_success:
                    success_count += 1

                # Average confidence
                if hasattr(self.session_logger, "get_session"):
                    session = self.session_logger.get_session(session_id)
                    if session and session.metadata:
                        confidence_sum += session.metadata.get("confidence", 0.7)
                else:
                    confidence_sum += 0.7
            else:
                # Assume success if no tool usage recorded
                success_count += 1
                confidence_sum += 0.8

        return success_count / total_sessions, confidence_sum / total_sessions

    def _detect_command_type(self, phrase: str) -> str:
        """Detect command type from phrase"""
        if phrase.startswith("@plan"):
            return "@plan"
        elif phrase.startswith("@git"):
            return "@git"
        elif phrase.startswith("@run"):
            return "@run"
        else:
            return "chat"

    def _extract_constraints(self, phrases: List[str]) -> List[str]:
        """Extract common constraint patterns"""
        constraints = []

        # Common constraint indicators
        constraint_markers = [
            "but",
            "except",
            "only",
            "focus on",
            "limit to",
            "especially",
            "mainly",
            "primarily",
            "specifically",
        ]

        for phrase in phrases:
            phrase_lower = phrase.lower()
            for marker in constraint_markers:
                if marker in phrase_lower:
                    # Extract constraint clause
                    parts = phrase_lower.split(marker)
                    if len(parts) > 1:
                        constraint = f"{marker} {parts[1].strip()}"
                        if constraint not in constraints:
                            constraints.append(constraint)

        return constraints[:5]  # Return top 5

    def _suggest_action(self, pattern_key: str) -> str:
        """Suggest action based on pattern"""
        # Based on pattern keywords
        if any(word in pattern_key for word in ["analyze", "check", "review"]):
            return "Use CodeAnalyzer tool with specific file targeting"
        elif any(word in pattern_key for word in ["research", "find", "search"]):
            return "Use Research tool before WebBrowser, follow up with CodeAnalyzer"
        elif any(word in pattern_key for word in ["git", "commit", "push"]):
            return "Use GitTools with explicit path specification"
        else:
            return "Ask for clarification on scope and constraints"

    def _get_session_time(self, session_id: str) -> float:
        """Get timestamp for a session"""
        session = self.session_logger.get_session(session_id)
        if session:
            return session.start_time
        return time.time()

    def _calculate_confidence(self, patterns: List[CommandPattern]) -> float:
        """Calculate overall confidence for a learning"""
        if not patterns:
            return 0.0

        # Weight by frequency and success rate
        total_weight = 0.0
        confidence_sum = 0.0

        for pattern in patterns:
            weight = pattern.frequency * pattern.success_rate
            total_weight += weight
            confidence_sum += weight * pattern.success_rate

        if total_weight == 0:
            return 0.0

        return confidence_sum / total_weight

    def export_learning_report(
        self, learnings: List[PersonaLearning], filepath: str = None
    ):
        """Export learning report to JSON file"""
        if filepath is None:
            filepath = Path(
                f"D:\\Proyectos\\Lilith\\Core\\memory\\persona_learning_{int(time.time())}.json"
            )

        report = {
            "generated_at": time.time(),
            "total_learnings": len(learnings),
            "learnings": [learning.to_dict() for learning in learnings],
        }

        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(report, f, indent=2, ensure_ascii=False)

        print(f"[PersonaAnalyzer] Report saved: {filepath}")
        return str(filepath)


# ============================================================================
# USAGE
# ============================================================================

if __name__ == "__main__":
    print("Persona Analyzer Demo")
    print("=" * 60)

    analyzer = PersonaAnalyzer()

    # Run analysis on recent sessions (if available)
    learnings = analyzer.analyze_all_patterns(session_limit=10)

    if learnings:
        print(f"\n[Results] Generated {len(learnings)} learning insights:")

        for i, learning in enumerate(learnings[:3], 1):
            print(f"\n#{i}: {learning.category}")
            print(f"   Confidence: {learning.confidence_score:.1%}")
            print(f"   Patterns: {len(learning.command_patterns)}")

            for j, pattern in enumerate(learning.command_patterns[:2], 1):
                print(
                    f"      Pattern {j}: {pattern.tools if hasattr(pattern, 'tools') else 'command'}"
                )
    else:
        print("\n[Results] No patterns found in recent sessions")

    # Export report
    if learnings:
        filepath = analyzer.export_learning_report(learnings)
        print(f"\n[Export] Learning report saved:")
        print(f"   {filepath}")

    print("\nâœ… Demo complete!")
