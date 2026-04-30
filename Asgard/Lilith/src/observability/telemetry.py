"""
Lilith - Agent Telemetry
Performance and usage metrics tracking for the AI agent
"""

import json
import time
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional


@dataclass
class ToolUsageMetric:
    """Metrics for a single tool invocation"""

    tool_name: str
    action: str
    timestamp: float
    duration_ms: float
    success: bool
    error_message: Optional[str] = None
    parameters: Optional[Dict[str, Any]] = None

    def to_dict(self) -> Dict[str, Any]:
        data = asdict(self)
        data["timestamp_iso"] = datetime.fromtimestamp(self.timestamp).isoformat()
        return data


@dataclass
class DecisionMetric:
    """Metrics for agent decision-making"""

    decision_type: str  # 'tool_selection', 'plan_generation', 'clarification'
    timestamp: float
    llm_model: str
    tokens_used: int
    confidence_score: Optional[float] = None
    context_used: Optional[int] = None  # chars of context
    result: Optional[str] = None  # success, failure, pending

    def to_dict(self) -> Dict[str, Any]:
        data = asdict(self)
        data["timestamp_iso"] = datetime.fromtimestamp(self.timestamp).isoformat()
        return data


@dataclass
class SessionSummary:
    """Summary metrics for a complete session"""

    session_id: str
    start_time: float
    end_time: Optional[float] = None
    user_intent: Optional[str] = None
    final_status: str = "ongoing"
    tool_calls: List[ToolUsageMetric] = None
    decisions: List[DecisionMetric] = None

    def __post_init__(self):
        if self.tool_calls is None:
            self.tool_calls = []
        if self.decisions is None:
            self.decisions = []

    @property
    def duration_ms(self) -> Optional[float]:
        """Calculate session duration in milliseconds"""
        if self.end_time and self.start_time:
            return (self.end_time - self.start_time) * 1000
        return None

    @property
    def success_rate(self) -> float:
        """Calculate tool success rate"""
        if not self.tool_calls:
            return 0.0
        successful = sum(1 for call in self.tool_calls if call.success)
        return successful / len(self.tool_calls) * 100

    @property
    def avg_tool_latency(self) -> float:
        """Calculate average tool latency"""
        if not self.tool_calls:
            return 0.0
        return sum(call.duration_ms for call in self.tool_calls) / len(self.tool_calls)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "session_id": self.session_id,
            "start_time": self.start_time,
            "start_time_iso": datetime.fromtimestamp(self.start_time).isoformat(),
            "end_time": self.end_time,
            "end_time_iso": datetime.fromtimestamp(self.end_time).isoformat()
            if self.end_time
            else None,
            "duration_ms": self.duration_ms,
            "user_intent": self.user_intent,
            "final_status": self.final_status,
            "success_rate_percent": round(self.success_rate, 1),
            "avg_tool_latency_ms": round(self.avg_tool_latency, 2),
            "total_tool_calls": len(self.tool_calls),
            "total_decisions": len(self.decisions),
        }


class AgentTelemetry:
    """
    Centralized telemetry collection for agent performance monitoring
    Integrates with SessionLogger for persistent storage
    """

    def __init__(self, metrics_file: str = None):
        """Initialize telemetry engine"""
        if metrics_file is None:
            # Default to Lilith's data directory
            self.metrics_file = Path(
                "D:\\Proyectos\\Lilith\\Core\\memory\\agent_metrics.jsonl"
            )
        else:
            self.metrics_file = Path(metrics_file)

        self.metrics_file.parent.mkdir(parents=True, exist_ok=True)

        # In-memory buffers
        self.current_session_id: Optional[str] = None
        self._tool_buffer: List[ToolUsageMetric] = []
        self._decision_buffer: List[DecisionMetric] = []

        # Load historical metrics
        self._historical_data = self._load_historical()

    def _load_historical(self) -> List[Dict[str, Any]]:
        """Load historical metrics from file"""
        if not self.metrics_file.exists():
            return []

        data = []
        with open(self.metrics_file, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    try:
                        data.append(json.loads(line))
                    except json.JSONDecodeError:
                        continue
        return data

    def start_session(self, session_id: str, user_intent: str = None):
        """Start tracking a new session"""
        self.current_session_id = session_id
        self._tool_buffer.clear()
        self._decision_buffer.clear()

    def log_tool_usage(
        self,
        tool_name: str,
        action: str,
        duration_ms: float,
        success: bool,
        error_message: str = None,
        parameters: Dict[str, Any] = None,
    ):
        """Log a tool invocation"""
        metric = ToolUsageMetric(
            tool_name=tool_name,
            action=action,
            timestamp=time.time(),
            duration_ms=duration_ms,
            success=success,
            error_message=error_message,
            parameters=parameters,
        )

        self._tool_buffer.append(metric)

        # Persist immediately (append-only log)
        self._persist_metric("tool_usage", metric.to_dict())

    def log_decision(
        self,
        decision_type: str,
        llm_model: str,
        tokens_used: int,
        confidence_score: float = None,
        context_used: int = None,
        result: str = None,
    ):
        """Log a decision made by the agent"""
        metric = DecisionMetric(
            decision_type=decision_type,
            timestamp=time.time(),
            llm_model=llm_model,
            tokens_used=tokens_used,
            confidence_score=confidence_score,
            context_used=context_used,
            result=result,
        )

        self._decision_buffer.append(metric)
        self._persist_metric("decision", metric.to_dict())

    def end_session(self, session_id: str, status: str = "success"):
        """End current session and generate summary"""
        if session_id != self.current_session_id:
            print(
                f"Warning: ending session {session_id} but current is {self.current_session_id}"
            )

        # Create session summary
        summary = SessionSummary(
            session_id=session_id,
            start_time=self._get_session_start_time(session_id),
            end_time=time.time(),
            user_intent=self._get_user_intent(session_id),
            final_status=status,
            tool_calls=self._tool_buffer.copy(),
            decisions=self._decision_buffer.copy(),
        )

        # Persist summary
        self._persist_metric("session_summary", summary.to_dict())

        # Clear buffers
        self.current_session_id = None
        self._tool_buffer.clear()
        self._decision_buffer.clear()

        return summary

    def _get_session_start_time(self, session_id: str) -> Optional[float]:
        """Retrieve session start time from historical data or buffer"""
        # Check historical data first
        for entry in self._historical_data:
            if (
                entry.get("type") == "session_summary"
                and entry.get("session_id") == session_id
            ):
                return entry.get("start_time")

        # Fallback to earliest tool/decision in buffer
        if self._tool_buffer:
            return min(call.timestamp for call in self._tool_buffer)
        if self._decision_buffer:
            return min(d.timestamp for d in self._decision_buffer)

        return time.time()

    def _get_user_intent(self, session_id: str) -> Optional[str]:
        """Retrieve user intent from historical data"""
        for entry in self._historical_data:
            if (
                entry.get("type") == "session_summary"
                and entry.get("session_id") == session_id
            ):
                return entry.get("user_intent")
        return None

    def _persist_metric(self, metric_type: str, data: Dict[str, Any]):
        """Persist a metric to the log file"""
        entry = {"type": metric_type, "timestamp": time.time(), "data": data}

        with open(self.metrics_file, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")

    def get_tool_statistics(self, tool_name: str = None) -> Dict[str, Any]:
        """Get aggregated tool usage statistics"""
        stats = {}

        # Process historical data
        for entry in self._historical_data:
            if entry.get("type") == "tool_usage":
                tool = entry["data"]
                name = tool["tool_name"]

                if tool_name and name != tool_name:
                    continue

                if name not in stats:
                    stats[name] = {
                        "calls": 0,
                        "total_duration_ms": 0,
                        "successes": 0,
                        "failures": 0,
                        "errors": [],
                    }

                stats[name]["calls"] += 1
                stats[name]["total_duration_ms"] += tool["duration_ms"]

                if tool["success"]:
                    stats[name]["successes"] += 1
                else:
                    stats[name]["failures"] += 1
                    if tool.get("error_message"):
                        stats[name]["errors"].append(tool["error_message"])

        # Process current buffer
        for tool in self._tool_buffer:
            if tool_name and tool.tool_name != tool_name:
                continue

            name = tool.tool_name
            if name not in stats:
                stats[name] = {
                    "calls": 0,
                    "total_duration_ms": 0,
                    "successes": 0,
                    "failures": 0,
                    "errors": [],
                }

            stats[name]["calls"] += 1
            stats[name]["total_duration_ms"] += tool.duration_ms

            if tool.success:
                stats[name]["successes"] += 1
            else:
                stats[name]["failures"] += 1
                if tool.error_message:
                    stats[name]["errors"].append(tool.error_message)

        # Calculate averages
        for name in stats:
            calls = stats[name]["calls"]
            if calls > 0:
                stats[name]["avg_duration_ms"] = round(
                    stats[name]["total_duration_ms"] / calls, 2
                )
                stats[name]["success_rate_percent"] = round(
                    stats[name]["successes"] / calls * 100, 1
                )
                stats[name]["failure_rate_percent"] = round(
                    stats[name]["failures"] / calls * 100, 1
                )

        return stats

    def get_decision_statistics(self) -> Dict[str, Any]:
        """Get aggregated decision-making statistics"""
        stats = {
            "total_decisions": 0,
            "by_type": {},
            "by_model": {},
            "total_tokens_used": 0,
            "avg_confidence": 0,
            "confidence_scores": [],
        }

        decisions = []

        # Process historical data
        for entry in self._historical_data:
            if entry.get("type") == "decision":
                decisions.append(entry["data"])

        # Process current buffer
        for decision in self._decision_buffer:
            decisions.append(decision.to_dict())

        # Aggregate
        for decision in decisions:
            stats["total_decisions"] += 1
            stats["total_tokens_used"] += decision["tokens_used"]

            # By type
            dtype = decision["decision_type"]
            if dtype not in stats["by_type"]:
                stats["by_type"][dtype] = 0
            stats["by_type"][dtype] += 1

            # By model
            model = decision["llm_model"]
            if model not in stats["by_model"]:
                stats["by_model"][model] = 0
            stats["by_model"][model] += 1

            # Confidence
            if decision.get("confidence_score") is not None:
                stats["confidence_scores"].append(decision["confidence_score"])

        # Calculate averages
        if stats["confidence_scores"]:
            stats["avg_confidence"] = round(
                sum(stats["confidence_scores"]) / len(stats["confidence_scores"]), 2
            )
        else:
            stats["avg_confidence"] = 0.0

        return stats

    def export_session_report(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Generate a comprehensive report for a session"""
        # This integrates with SessionLogger to get full picture
        from .session_logger import SessionLogger

        # Get session data from logger
        logger = SessionLogger()
        session = logger.get_session(session_id)

        if not session:
            return None

        interactions = logger.get_session_interactions(session_id)
        tool_stats = logger.get_tool_usage_stats(session_id)
        telemetry_stats = self.get_tool_statistics()

        return {
            "session_id": session_id,
            "session_info": session.to_dict(),
            "interactions_count": len(interactions),
            "tool_usage": tool_stats,
            "performance_metrics": {"tool_performance": telemetry_stats},
        }


# ============================================================================
# USAGE
# ============================================================================

if __name__ == "__main__":
    print("Agent Telemetry Demo")
    print("=" * 60)

    telemetry = AgentTelemetry()

    # Simulate a session
    session_id = "test-session-001"
    telemetry.start_session(session_id, "Analyze codebase and generate report")

    # Simulate tool usage
    telemetry.log_tool_usage(
        tool_name="CodeAnalyzer",
        action="analyze_project",
        duration_ms=2345.0,
        success=True,
        parameters={"path": "D:\\Proyectos\\Lilith\\Core", "depth": 2},
        result="Found 12 files, 3 classes, 2 potential issues",
    )

    telemetry.log_tool_usage(
        tool_name="Research",
        action="search",
        duration_ms=892.0,
        success=False,
        error_message="DuckDuckGo rate limited",
        parameters={"query": "Python async patterns"},
    )

    # Simulate decisions
    telemetry.log_decision(
        decision_type="tool_selection",
        llm_model="grok-4-fast-reasoning",
        tokens_used=325,
        confidence_score=0.85,
        context_used=2048,
        result="success",
    )

    # End session
    summary = telemetry.end_session(session_id, "success")

    print(f"Session ID: {session_id}")
    print(f"Duration: {summary.duration_ms:.0f} ms")
    print(f"Success Rate: {summary.success_rate:.1f}%")
    print(f"Avg Latency: {summary.avg_tool_latency:.2f} ms")
    print()

    # Show statistics
    print("TOOL STATISTICS:")
    tool_stats = telemetry.get_tool_statistics()
    for tool, stats in tool_stats.items():
        print(
            f"  {tool}: {stats['calls']} calls, {stats['success_rate_percent']}% success"
        )

    print("\nDECISION STATISTICS:")
    decision_stats = telemetry.get_decision_statistics()
    print(f"  Total: {decision_stats['total_decisions']} decisions")
    print(f"  Tokens: {decision_stats['total_tokens_used']:,}")
    print(f"  Avg Confidence: {decision_stats['avg_confidence']:.2f}")

    print("\nâœ… Demo complete!")
    print(f"\nMetrics stored in: {telemetry.metrics_file}")
