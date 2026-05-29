"""
TrustScoreEngine - Automatic execution decision system for Lilith
Evaluates operation risk and decides execution mode based on trust scoring
"""
import json
import logging
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


class ExecutionMode(Enum):
    """Execution decision modes"""

    AUTO = "auto"  # Execute automatically
    CONFIRM = "confirm"  # Show preview, ask for confirmation
    BLOCK = "block"  # Block execution (high risk)


class RiskLevel(Enum):
    """Risk levels for operations"""

    LOW = 0.2
    MEDIUM = 0.5
    HIGH = 0.8
    CRITICAL = 1.0


@dataclass
class OperationHistory:
    """Record of past operations"""

    tool_name: str
    action: str
    success: bool
    timestamp: str
    execution_mode: str
    user_confirmed: Optional[bool] = None


@dataclass
class TrustScoreResult:
    """Result of trust score evaluation"""

    score: float  # 0.0 to 1.0
    execution_mode: ExecutionMode
    confidence: float  # Confidence in the decision
    reasons: List[str]  # Why this decision was made
    preview: Optional[Dict] = None  # Preview of what would happen
    alternatives: List[str] = field(default_factory=list)


class TrustScoreEngine:
    """
    Evaluates trust scores for tool operations and decides execution mode.

    Features:
    - Risk-based operation classification
    - User behavior learning
    - Context-aware decision making
    - Configurable thresholds
    - Audit logging
    """

    # Default thresholds (can be configured)
    DEFAULT_THRESHOLDS = {
        "auto_execute_min": 0.75,  # Score >= this -> AUTO
        "confirm_min": 0.40,  # Score >= this -> CONFIRM
        # Score < confirm_min -> BLOCK
    }

    # Risk weights for different operation types
    OPERATION_RISK_WEIGHTS = {
        # File operations
        "FileManager": {
            "read": RiskLevel.LOW,
            "list": RiskLevel.LOW,
            "search": RiskLevel.LOW,
            "info": RiskLevel.LOW,
            "write": RiskLevel.MEDIUM,
            "delete": RiskLevel.HIGH,
        },
        # Code operations
        "CodeRefactor": {
            "rename": RiskLevel.MEDIUM,
            "extract_method": RiskLevel.MEDIUM,
            "optimize_imports": RiskLevel.LOW,
            "convert_async": RiskLevel.MEDIUM,
            "add_type_hints": RiskLevel.LOW,
            "convert_comprehension": RiskLevel.LOW,
        },
        # Git operations
        "GitTools": {
            "status": RiskLevel.LOW,
            "log": RiskLevel.LOW,
            "diff": RiskLevel.LOW,
            "branch": RiskLevel.LOW,
            "remote": RiskLevel.LOW,
            "commit": RiskLevel.MEDIUM,
            "clone": RiskLevel.LOW,
            "pull": RiskLevel.HIGH,
            "push": RiskLevel.HIGH,
        },
        # Test operations
        "TestRunner": {
            "detect_framework": RiskLevel.LOW,
            "run_tests": RiskLevel.LOW,
            "coverage": RiskLevel.LOW,
            "find_missing": RiskLevel.LOW,
        },
        # Dependency operations
        "DependencyManager": {
            "list": RiskLevel.LOW,
            "search": RiskLevel.LOW,
            "install": RiskLevel.MEDIUM,
            "update": RiskLevel.MEDIUM,
            "audit": RiskLevel.LOW,
            "remove": RiskLevel.HIGH,
        },
        # Web operations
        "WebBrowser": {
            "visit": RiskLevel.LOW,
            "search": RiskLevel.LOW,
            "extract_links": RiskLevel.LOW,
            "extract_text": RiskLevel.LOW,
            "get_title": RiskLevel.LOW,
        },
        # Research operations
        "Research": {
            "quick_search": RiskLevel.LOW,
            "deep_research": RiskLevel.LOW,
            "fact_check": RiskLevel.LOW,
            "compare_sources": RiskLevel.LOW,
            "summarize_topic": RiskLevel.LOW,
            "find_expert_sources": RiskLevel.LOW,
        },
        # Project operations
        "ProjectScanner": {
            "scan": RiskLevel.LOW,
        },
        "TaskTracker": {
            "create_plan": RiskLevel.LOW,
            "get_plan": RiskLevel.LOW,
            "list_plans": RiskLevel.LOW,
            "execute_plan": RiskLevel.MEDIUM,
        },
    }

    # Destructive keywords that increase risk
    DESTRUCTIVE_KEYWORDS = [
        "delete",
        "remove",
        "drop",
        "destroy",
        "clean",
        "clear",
        "reset",
        "overwrite",
        "replace",
        "eliminar",
        "borrar",
        "limpiar",
        "destruir",
        "resetear",
        "sobrescribir",
    ]

    # Protected paths (system-critical)
    PROTECTED_PATHS = [
        "/",
        "C:\\Windows",
        "C:\\Program Files",
        "C:\\System",
        "/etc",
        "/usr",
        "/bin",
        "/sbin",
        "/lib",
        "/sys",
        "/dev",
        ".git",
        "__pycache__",
        ".venv",
        "node_modules",
    ]

    def __init__(self, user_id: str = "default", config_path: Optional[str] = None):
        self.user_id = user_id
        self.thresholds = self.DEFAULT_THRESHOLDS.copy()
        self.operation_history: List[OperationHistory] = []
        self.user_preferences: Dict[str, Any] = {}
        self.success_rate_cache: Dict[str, float] = {}

        # Load persisted data
        self._load_data(config_path)

        logger.info(f"TrustScoreEngine initialized for user: {user_id}")

    def _get_data_path(self, config_path: Optional[str] = None) -> Path:
        """Get path for persistence"""
        if config_path:
            return Path(config_path)

        # Default: store in user home
        base_path = Path.home() / ".Lilith" / "trust_scores"
        base_path.mkdir(parents=True, exist_ok=True)
        return base_path / f"{self.user_id}.json"

    def _load_data(self, config_path: Optional[str] = None):
        """Load persisted trust data"""
        data_path = self._get_data_path(config_path)

        if data_path.exists():
            try:
                with open(data_path, "r", encoding="utf-8") as f:
                    data = json.load(f)

                self.thresholds = data.get("thresholds", self.DEFAULT_THRESHOLDS)
                self.user_preferences = data.get("preferences", {})

                # Load recent history (last 100 ops)
                history_data = data.get("history", [])[-100:]
                self.operation_history = [OperationHistory(**op) for op in history_data]

                logger.info(
                    f"Loaded {len(self.operation_history)} operations from history"
                )

            except Exception as e:
                logger.warning(f"Failed to load trust data: {e}")

    def _save_data(self, config_path: Optional[str] = None):
        """Persist trust data"""
        data_path = self._get_data_path(config_path)

        try:
            data = {
                "user_id": self.user_id,
                "thresholds": self.thresholds,
                "preferences": self.user_preferences,
                "history": [
                    {
                        "tool_name": op.tool_name,
                        "action": op.action,
                        "success": op.success,
                        "timestamp": op.timestamp,
                        "execution_mode": op.execution_mode,
                        "user_confirmed": op.user_confirmed,
                    }
                    for op in self.operation_history[-100:]  # Keep last 100
                ],
                "last_saved": datetime.now().isoformat(),
            }

            with open(data_path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)

        except Exception as e:
            logger.warning(f"Failed to save trust data: {e}")

    def evaluate_operation(
        self,
        tool_name: str,
        action: str,
        parameters: Dict[str, Any],
        context: Optional[Dict[str, Any]] = None,
    ) -> TrustScoreResult:
        """
        Evaluate trust score for an operation and decide execution mode.

        Args:
            tool_name: Name of the tool
            action: Action being performed
            parameters: Operation parameters
            context: Additional context

        Returns:
            TrustScoreResult with decision and metadata
        """
        context = context or {}
        reasons = []

        # 1. Get base risk from operation type
        base_risk = self._get_operation_risk(tool_name, action)
        reasons.append(f"Base risk for {tool_name}.{action}: {base_risk.name}")

        # 2. Check for destructive parameters
        param_risk = self._evaluate_parameters(parameters)
        if param_risk > 0:
            reasons.append(
                f"Destructive keywords detected in parameters: +{param_risk:.2f} risk"
            )

        # 3. Check for protected paths
        path_risk = self._evaluate_paths(parameters)
        if path_risk > 0:
            reasons.append(f"Protected path access: +{path_risk:.2f} risk")

        # 4. Get user success rate for this operation
        success_rate = self._get_success_rate(tool_name, action)
        reasons.append(f"Historical success rate: {success_rate:.1%}")

        # 5. Calculate recency bonus (more recent = more trusted)
        recency_score = self._calculate_recency_score(tool_name, action)
        reasons.append(f"Recency score: {recency_score:.2f}")

        # 6. Calculate final score
        # Start with 1.0 (full trust) and subtract risks
        score = 1.0
        score -= base_risk.value  # Subtract base risk
        score -= param_risk  # Subtract parameter risk
        score -= path_risk  # Subtract path risk
        score += success_rate * 0.2  # Add bonus for good history
        score += recency_score * 0.1  # Add bonus for recent use

        # Clamp between 0 and 1
        score = max(0.0, min(1.0, score))

        # 7. Decide execution mode
        if score >= self.thresholds["auto_execute_min"]:
            execution_mode = ExecutionMode.AUTO
            reasons.append(
                f"Score {score:.2f} >= AUTO threshold ({self.thresholds['auto_execute_min']})"
            )
        elif score >= self.thresholds["confirm_min"]:
            execution_mode = ExecutionMode.CONFIRM
            reasons.append(
                f"Score {score:.2f} in CONFIRM range ({self.thresholds['confirm_min']}-{self.thresholds['auto_execute_min']})"
            )
        else:
            execution_mode = ExecutionMode.BLOCK
            reasons.append(
                f"Score {score:.2f} < CONFIRM threshold ({self.thresholds['confirm_min']})"
            )

        # 8. Generate preview if needed
        preview = None
        if execution_mode != ExecutionMode.AUTO:
            preview = self._generate_preview(tool_name, action, parameters)

        # 9. Calculate confidence
        confidence = self._calculate_confidence(
            score, success_rate, len(self.operation_history)
        )

        result = TrustScoreResult(
            score=round(score, 3),
            execution_mode=execution_mode,
            confidence=round(confidence, 3),
            reasons=reasons,
            preview=preview,
            alternatives=self._suggest_alternatives(tool_name, action, parameters),
        )

        logger.info(
            f"Trust evaluation: {tool_name}.{action} = {score:.2f} -> {execution_mode.value}"
        )

        return result

    def _get_operation_risk(self, tool_name: str, action: str) -> RiskLevel:
        """Get base risk level for operation type"""
        tool_risks = self.OPERATION_RISK_WEIGHTS.get(tool_name, {})
        return tool_risks.get(action, RiskLevel.MEDIUM)

    def _evaluate_parameters(self, parameters: Dict[str, Any]) -> float:
        """Evaluate parameter risk based on destructive keywords"""
        risk = 0.0

        param_str = json.dumps(parameters).lower()

        for keyword in self.DESTRUCTIVE_KEYWORDS:
            if keyword in param_str:
                risk += 0.15  # Each destructive keyword adds risk

        return min(0.5, risk)  # Cap at 0.5

    def _evaluate_paths(self, parameters: Dict[str, Any]) -> float:
        """Evaluate path risk for protected paths"""
        risk = 0.0

        # Extract paths from parameters
        paths = []
        for key, value in parameters.items():
            if isinstance(value, str) and (
                "/" in value or "\\" in value or "." in value
            ):
                paths.append(value.lower())
            elif isinstance(value, list):
                for item in value:
                    if isinstance(item, str) and ("/" in item or "\\" in item):
                        paths.append(item.lower())

        # Check against protected paths
        for path in paths:
            for protected in self.PROTECTED_PATHS:
                if protected.lower() in path or path.endswith(protected.lower()):
                    risk += 0.3
                    break

        return min(0.6, risk)  # Cap at 0.6

    def _get_success_rate(self, tool_name: str, action: str) -> float:
        """Get historical success rate for this operation type"""
        cache_key = f"{tool_name}.{action}"

        if cache_key in self.success_rate_cache:
            return self.success_rate_cache[cache_key]

        # Find relevant history
        relevant = [
            op
            for op in self.operation_history
            if op.tool_name == tool_name and op.action == action
        ]

        if not relevant:
            return 0.5  # Neutral if no history

        # Weight recent operations more heavily
        success_count = sum(1 for op in relevant if op.success)
        rate = success_count / len(relevant)

        self.success_rate_cache[cache_key] = rate
        return rate

    def _calculate_recency_score(self, tool_name: str, action: str) -> float:
        """Calculate score based on how recently this operation was used"""
        relevant = [
            op
            for op in self.operation_history
            if op.tool_name == tool_name and op.action == action
        ]

        if not relevant:
            return 0.0

        # Get most recent operation
        last_op = max(relevant, key=lambda x: x.timestamp)
        last_time = datetime.fromisoformat(last_op.timestamp)

        # Calculate hours since last use
        hours_ago = (datetime.now() - last_time).total_seconds() / 3600

        if hours_ago < 1:
            return 0.3  # Used within last hour
        elif hours_ago < 24:
            return 0.2  # Used today
        elif hours_ago < 168:  # 1 week
            return 0.1
        else:
            return 0.0

    def _calculate_confidence(
        self, score: float, success_rate: float, history_size: int
    ) -> float:
        """Calculate confidence in the decision"""
        # More history = more confidence
        history_factor = min(1.0, history_size / 20)  # Max at 20 operations

        # Clear decisions (near thresholds) have less confidence
        distance_from_threshold = min(
            abs(score - self.thresholds["auto_execute_min"]),
            abs(score - self.thresholds["confirm_min"]),
        )
        clarity_factor = 1.0 - (
            distance_from_threshold * 2
        )  # Penalize being near thresholds

        return (history_factor * 0.4) + (success_rate * 0.3) + (clarity_factor * 0.3)

    def _generate_preview(
        self, tool_name: str, action: str, parameters: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Generate a preview of what the operation will do"""
        preview = {
            "tool": tool_name,
            "action": action,
            "parameters": {k: v for k, v in parameters.items() if k != "content"},
            "estimated_duration": "5-30 seconds",
            "can_undo": False,
        }

        # Add tool-specific preview info
        if tool_name == "FileManager" and action == "write":
            preview["can_undo"] = True
            preview["backup_created"] = True
            preview["estimated_duration"] = "1-5 seconds"

        elif tool_name == "GitTools" and action == "commit":
            preview["can_undo"] = True
            preview["estimated_duration"] = "2-5 seconds"

        elif tool_name == "CodeRefactor":
            preview["can_undo"] = True
            preview["backup_created"] = True
            preview["estimated_duration"] = "5-15 seconds"

        return preview

    def _suggest_alternatives(
        self, tool_name: str, action: str, parameters: Dict[str, Any]
    ) -> List[str]:
        """Suggest alternative approaches"""
        alternatives = []

        if tool_name == "FileManager" and action == "delete":
            alternatives.append("Use 'move to trash' instead of permanent delete")
            alternatives.append("Archive the file instead of deleting")

        elif tool_name == "GitTools" and action in ["push", "pull"]:
            alternatives.append("Review changes with 'git diff' first")
            alternatives.append("Create a backup branch before pushing")

        elif tool_name == "DependencyManager" and action == "install":
            alternatives.append("Use virtual environment for isolation")
            alternatives.append("Check for security vulnerabilities first")

        return alternatives

    def record_operation(
        self,
        tool_name: str,
        action: str,
        success: bool,
        execution_mode: ExecutionMode,
        user_confirmed: Optional[bool] = None,
    ):
        """
        Record operation result for learning.

        Args:
            tool_name: Tool used
            action: Action performed
            success: Whether operation succeeded
            execution_mode: Execution mode used
            user_confirmed: Whether user explicitly confirmed (for CONFIRM mode)
        """
        op = OperationHistory(
            tool_name=tool_name,
            action=action,
            success=success,
            timestamp=datetime.now().isoformat(),
            execution_mode=execution_mode.value,
            user_confirmed=user_confirmed,
        )

        self.operation_history.append(op)

        # Clear cache since we have new data
        cache_key = f"{tool_name}.{action}"
        if cache_key in self.success_rate_cache:
            del self.success_rate_cache[cache_key]

        # Persist periodically
        if len(self.operation_history) % 10 == 0:
            self._save_data()

        logger.info(f"Recorded operation: {tool_name}.{action} success={success}")

    def update_thresholds(self, auto_min: float, confirm_min: float):
        """Update decision thresholds"""
        self.thresholds["auto_execute_min"] = max(0.5, min(0.95, auto_min))
        self.thresholds["confirm_min"] = max(0.1, min(0.5, confirm_min))
        self._save_data()

        logger.info(
            f"Updated thresholds: auto={self.thresholds['auto_execute_min']}, confirm={self.thresholds['confirm_min']}"
        )

    def get_statistics(self) -> Dict[str, Any]:
        """Get trust system statistics"""
        if not self.operation_history:
            return {
                "total_operations": 0,
                "success_rate": 0,
                "auto_executed": 0,
                "confirmed": 0,
                "blocked": 0,
            }

        total = len(self.operation_history)
        successful = sum(1 for op in self.operation_history if op.success)

        modes = {"auto": 0, "confirm": 0, "block": 0}
        for op in self.operation_history:
            modes[op.execution_mode] = modes.get(op.execution_mode, 0) + 1

        return {
            "total_operations": total,
            "success_rate": successful / total,
            "auto_executed": modes.get("auto", 0),
            "confirmed": modes.get("confirm", 0),
            "blocked": modes.get("block", 0),
            "thresholds": self.thresholds,
            "most_used_tools": self._get_most_used_tools(),
        }

    def _get_most_used_tools(self, limit: int = 5) -> List[Dict[str, Any]]:
        """Get most frequently used tools"""
        from collections import Counter

        tool_counts = Counter(op.tool_name for op in self.operation_history)

        result = []
        for tool, count in tool_counts.most_common(limit):
            tool_ops = [op for op in self.operation_history if op.tool_name == tool]
            success_rate = sum(1 for op in tool_ops if op.success) / len(tool_ops)
            result.append(
                {"tool": tool, "count": count, "success_rate": round(success_rate, 2)}
            )

        return result


# Global instance cache
_trust_engine_cache: Dict[str, TrustScoreEngine] = {}


def get_trust_engine(user_id: str = "default") -> TrustScoreEngine:
    """Get or create trust engine for user"""
    if user_id not in _trust_engine_cache:
        _trust_engine_cache[user_id] = TrustScoreEngine(user_id)
    return _trust_engine_cache[user_id]
