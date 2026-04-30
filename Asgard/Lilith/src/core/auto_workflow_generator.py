"""
Lilith - Auto Workflow Generator
Analyzes session patterns to automatically generate reusable workflows
"""

import json
import re
import sqlite3
import time
from collections import Counter, defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

from src.observability.session_logger import InteractionEntry, SessionLogger
from src.observability.telemetry import AgentTelemetry


@dataclass
class ToolSequence:
    """Represents a sequence of tool usage in a session"""

    tools: List[str]  # List of tool names in order
    actions: List[str]  # List of corresponding actions
    frequency: int = 1
    avg_duration: float = 0.0
    success_rate: float = 0.0
    example_session_id: Optional[str] = None
    first_seen: float = None
    last_seen: float = None

    def __post_init__(self):
        if self.first_seen is None:
            self.first_seen = time.time()
        if self.last_seen is None:
            self.last_seen = time.time()

    @property
    def id(self) -> str:
        """Generate unique ID for this sequence"""
        sequence_str = "â†’".join(self.tools)
        return f"seq_{hash(sequence_str) & 0xFFFFFFFF}"

    @property
    def name(self) -> str:
        """Generate human-readable name"""
        if len(self.tools) == 1:
            return f"auto_{self.tools[0].lower()}_workflow"
        else:
            tools_str = "_to_".join(self.tools)
            return f"auto_{tools_str.lower()}_workflow"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "tools": self.tools,
            "actions": self.actions,
            "frequency": self.frequency,
            "avg_duration_ms": round(self.avg_duration, 2),
            "success_rate_percent": round(self.success_rate * 100, 1),
            "example_session_id": self.example_session_id,
            "first_seen": self.first_seen,
            "last_seen": self.last_seen,
        }


@dataclass
class GeneratedWorkflow:
    """Represents a workflow generated from patterns"""

    workflow_id: str
    name: str
    description: str
    steps: List[Dict[str, Any]]
    metadata: Dict[str, Any]
    source_pattern: ToolSequence

    def to_dict(self) -> Dict[str, Any]:
        return {
            "workflow_id": self.workflow_id,
            "name": self.name,
            "description": self.description,
            "steps": self.steps,
            "metadata": self.metadata,
            "source_pattern": self.source_pattern.to_dict(),
        }


class AutoWorkflowGenerator:
    """
    Analyzes session history to automatically generate reusable workflows

    Process:
    1. Load recent session data from SessionLogger
    2. Extract tool usage sequences
    3. Identify frequently repeated patterns
    4. Generate workflow templates
    5. Save to backend/workflows/auto_generated/
    """

    # Umbrales por defecto para generación de workflows.
    # Se exponen como atributos de clase para poder ser monkeypatcheados en tests
    MIN_SUCCESS_RATE: float = 0.7
    MIN_QUALITY_SCORE: float = 0.7

    def __init__(self):
        """Initialize with data sources"""
        self.session_logger = SessionLogger()
        self.telemetry = AgentTelemetry()

        # Configuration
        self.workflows_dir = Path(
            "D:\\Proyectos\\Lilith\\Core\\Backend\\workflows\\auto_generated"
        )
        self.workflows_dir.mkdir(parents=True, exist_ok=True)

        # Pattern analysis thresholds
        self.min_frequency = 3  # Minimum times pattern must appear
        # Usar los umbrales de clase por defecto (configurables vía monkeypatch en tests)
        self.min_confidence = (
            self.MIN_SUCCESS_RATE
        )  # Minimum confidence to auto-generate
        self.max_sequence_length = 5  # Max tools in sequence
        self.lookback_days = 7  # Analyze sessions from last N days

    def analyze_recent_sessions(self, limit: int = 100) -> List[ToolSequence]:
        """Analyze recent sessions to find repeated tool sequences"""
        print(f"[AutoWorkflow] Analyzing up to {limit} recent sessions...")

        # Get recent sessions
        sessions = self.session_logger.get_recent_sessions(limit=limit)
        print(f"[AutoWorkflow] Found {len(sessions)} sessions")

        if not sessions:
            return []

        # Extract sequences from all sessions
        all_sequences = []
        for session in sessions:
            sequences = self._extract_sequences_from_session(session.session_id)
            all_sequences.extend(sequences)

        print(f"[AutoWorkflow] Extracted {len(all_sequences)} raw sequences")

        # Group by sequence pattern
        sequences_by_pattern = self._group_sequences(all_sequences)

        # Filter by frequency and calculate stats
        frequent_sequences = self._filter_frequent_sequences(sequences_by_pattern)

        print(f"[AutoWorkflow] Found {len(frequent_sequences)} frequent patterns")

        return frequent_sequences

    def _extract_sequences_from_session(self, session_id: str) -> List[ToolSequence]:
        """Extract tool sequences from a single session"""
        # Get tool usage directly for this session
        with sqlite3.connect(self.session_logger.db_path) as conn:
            cursor = conn.execute(
                """
                SELECT tool_name, action, duration_ms, id
                FROM tool_usage
                WHERE session_id = ?
                ORDER BY id
            """,
                (session_id,),
            )

            tool_records = cursor.fetchall()

        if not tool_records:
            return []

        sequences = []
        current_sequence = []

        for record in tool_records:
            tool_name = record[0]
            action = record[1]
            tool_id = record[3]
            # Use id as timestamp proxy (it's sequential)
            timestamp = float(tool_id)

            current_sequence.append(
                {"tool": tool_name, "action": action, "timestamp": timestamp}
            )

            # If sequence is getting long, save it and start new
            if len(current_sequence) >= self.max_sequence_length:
                if len(current_sequence) >= 2:  # Only save multi-step sequences
                    sequence = ToolSequence(
                        tools=[t["tool"] for t in current_sequence],
                        actions=[t["action"] for t in current_sequence],
                        example_session_id=session_id,
                        first_seen=current_sequence[0]["timestamp"],
                        last_seen=current_sequence[-1]["timestamp"],
                    )
                    sequences.append(sequence)

                # Overlapping windows - keep last tool
                current_sequence = current_sequence[-1:]

        # Don't forget the last sequence
        if len(current_sequence) >= 2:
            sequence = ToolSequence(
                tools=[t["tool"] for t in current_sequence],
                actions=[t["action"] for t in current_sequence],
                example_session_id=session_id,
                first_seen=current_sequence[0]["timestamp"],
                last_seen=current_sequence[-1]["timestamp"],
            )
            sequences.append(sequence)

        return sequences

    def _group_sequences(
        self, sequences: List[ToolSequence]
    ) -> Dict[str, List[ToolSequence]]:
        """Group sequences by their tool pattern"""
        grouped = defaultdict(list)

        for seq in sequences:
            # Use tuple of tools as key
            key = tuple(seq.tools)
            grouped[key].append(seq)

        return grouped

    def _filter_frequent_sequences(
        self, grouped_sequences: Dict[tuple, List[ToolSequence]]
    ) -> List[ToolSequence]:
        """Filter groups by frequency and calculate statistics"""
        filtered = []

        for key, sequences in grouped_sequences.items():
            frequency = len(sequences)

            if frequency >= self.min_frequency:
                # Calculate average duration and success rate
                total_duration = sum(seq.avg_duration for seq in sequences)
                total_success_rate = sum(seq.success_rate for seq in sequences)

                # Create aggregated sequence
                aggregated = ToolSequence(
                    tools=sequences[0].tools,
                    actions=sequences[0].actions,
                    frequency=frequency,
                    avg_duration=total_duration / frequency,
                    success_rate=total_success_rate / frequency,
                    example_session_id=sequences[0].example_session_id,
                    first_seen=min(seq.first_seen for seq in sequences),
                    last_seen=max(seq.last_seen for seq in sequences),
                )

                filtered.append(aggregated)

        return filtered

    def _get_sequence_duration(self, sequence: ToolSequence) -> float:
        """Get total duration for a sequence from telemetry"""
        # Get tool usage for the example session
        if not sequence.example_session_id:
            return 0.0

        tool_stats = self.session_logger.get_tool_usage_stats(
            sequence.example_session_id
        )

        total_duration = 0.0
        for tool in sequence.tools:
            if tool in tool_stats:
                total_duration += tool_stats[tool]["avg_duration_ms"]

        return total_duration

    def _get_sequence_success_rate(self, sequence: ToolSequence) -> float:
        """Get success rate for a sequence from telemetry"""
        if not sequence.example_session_id:
            return 0.0

        tool_stats = self.session_logger.get_tool_usage_stats(
            sequence.example_session_id
        )

        # Sequence is successful if all tools were successful
        for tool in sequence.tools:
            if tool in tool_stats and tool_stats[tool]["success_rate"] < 50:
                return 0.0

        return 1.0

    def generate_workflows(
        self, sequences: List[ToolSequence]
    ) -> List[GeneratedWorkflow]:
        """Generate workflow definitions from tool sequences"""
        workflows = []

        for sequence in sequences:
            # Check if sequence meets quality threshold
            if sequence.frequency < self.min_frequency:
                continue

            # Umbral de éxito configurable (por defecto alto en producción)
            if sequence.success_rate < self.MIN_QUALITY_SCORE:
                continue

            # Generate workflow
            workflow = self._create_workflow_from_sequence(sequence)
            workflows.append(workflow)

            print(f"[AutoWorkflow] Generated: {workflow.name}")
            tools_str = " -> ".join(sequence.tools)
            print(f"  Tools: {tools_str}")
            print(f"  Frequency: {sequence.frequency}")
            print(f"  Success Rate: {sequence.success_rate:.1%}")

        return workflows

    def _create_workflow_from_sequence(
        self, sequence: ToolSequence
    ) -> GeneratedWorkflow:
        """Convert a tool sequence into a workflow definition"""
        # Generate workflow ID
        workflow_id = f"auto_{int(time.time())}_{sequence.id}"

        # Create human-readable name
        if len(sequence.tools) == 1:
            description = (
                f"Auto-generated workflow for single tool: {sequence.tools[0]}"
            )
        else:
            tools_str = " -> ".join(sequence.tools)
            description = f"Auto-generated workflow for sequence: {tools_str}"

        # Create workflow steps
        steps = []
        for i, (tool_name, action) in enumerate(zip(sequence.tools, sequence.actions)):
            step = {
                "step_id": f"step_{i+1}",
                "tool": tool_name,
                "action": action,
                "parameters": {},  # Will be filled from examples
                "description": f"Execute {tool_name}.{action}",
                "depends_on": [steps[-1]["step_id"]] if steps else [],
            }
            steps.append(step)

        # Metadata
        metadata = {
            "auto_generated": True,
            "generation_time": time.time(),
            "source": "session_pattern_analysis",
            "frequency": sequence.frequency,
            "confidence": sequence.success_rate,
            "example_session": sequence.example_session_id,
        }

        return GeneratedWorkflow(
            workflow_id=workflow_id,
            name=sequence.name,
            description=description,
            steps=steps,
            metadata=metadata,
            source_pattern=sequence,
        )

    def save_workflows(self, workflows: List[GeneratedWorkflow]) -> int:
        """Save generated workflows to disk"""
        saved_count = 0

        for workflow in workflows:
            # Generate filename
            filename = f"{workflow.workflow_id}.json"
            filepath = self.workflows_dir / filename

            # Save as JSON
            with open(filepath, "w", encoding="utf-8") as f:
                json.dump(workflow.to_dict(), f, indent=2, ensure_ascii=False)

            saved_count += 1
            print(f"[AutoWorkflow] Saved: {filepath}")

        # Save index file
        self._update_workflow_index(workflows)

        return saved_count

    def _update_workflow_index(self, workflows: List[GeneratedWorkflow]):
        """Update index of auto-generated workflows"""
        index_file = self.workflows_dir / "_index.json"

        # Load existing index or create new
        if index_file.exists():
            with open(index_file, "r", encoding="utf-8") as f:
                index = json.load(f)
        else:
            index = {"auto_generated": True, "created_at": time.time(), "workflows": []}

        # Add new workflows
        for workflow in workflows:
            index["workflows"].append(
                {
                    "workflow_id": workflow.workflow_id,
                    "name": workflow.name,
                    "file": f"{workflow.workflow_id}.json",
                    "metadata": workflow.metadata,
                }
            )

        # Update metadata
        index["updated_at"] = time.time()
        index["total_workflows"] = len(index["workflows"])

        # Save index
        with open(index_file, "w", encoding="utf-8") as f:
            json.dump(index, f, indent=2, ensure_ascii=False)

        print(f"[AutoWorkflow] Updated index: {index_file}")

    def load_generated_workflows(self) -> List[GeneratedWorkflow]:
        """Load previously generated workflows"""
        workflows = []

        # Check for index file
        index_file = self.workflows_dir / "_index.json"
        if not index_file.exists():
            return workflows

        # Load index
        with open(index_file, "r", encoding="utf-8") as f:
            index = json.load(f)

        # Load each workflow
        for entry in index.get("workflows", []):
            filepath = self.workflows_dir / entry["file"]
            if filepath.exists():
                with open(filepath, "r", encoding="utf-8") as f:
                    data = json.load(f)

                    # Skip if not valid GeneratedWorkflow
                    if "source_pattern" in data:
                        # This would need proper deserialization
                        # For now, just count them
                        workflows.append(data)

        return workflows

    def find_matching_workflow(self, intent: str) -> Optional[Dict[str, Any]]:
        """Search cached workflows for one matching the user's intent.

        Uses keyword overlap between the intent and workflow tool names/descriptions.
        Returns the best match if confidence >= min_confidence, else None.
        """
        workflows = self.load_generated_workflows()
        if not workflows:
            return None

        intent_lower = intent.lower()
        intent_words = set(re.findall(r"\w+", intent_lower))

        best_match = None
        best_score = 0.0

        for wf in workflows:
            # Build keyword set from workflow
            wf_text = f"{wf.get('name', '')} {wf.get('description', '')}"
            for step in wf.get("steps", []):
                wf_text += f" {step.get('tool', '')} {step.get('action', '')} {step.get('description', '')}"
            wf_words = set(re.findall(r"\w+", wf_text.lower()))

            # Calculate Jaccard-like overlap score
            if not wf_words:
                continue
            overlap = intent_words & wf_words
            score = len(overlap) / max(len(intent_words), 1)

            # Boost by stored confidence
            metadata = wf.get("metadata", {})
            stored_confidence = metadata.get("confidence", 0.5)
            final_score = score * 0.6 + stored_confidence * 0.4

            if final_score > best_score:
                best_score = final_score
                best_match = wf

        if best_match and best_score >= self.min_confidence:
            best_match.setdefault("metadata", {})["match_score"] = round(best_score, 3)
            return best_match

        return None

    def run_full_analysis(
        self, session_limit: int = 100, auto_save: bool = True
    ) -> Tuple[List[ToolSequence], List[GeneratedWorkflow]]:
        """Run complete analysis and workflow generation pipeline"""
        print("=" * 70)
        print("AUTO-WORKFLOW GENERATION PIPELINE")
        print("=" * 70)

        # 1. Analyze sessions for patterns
        print("\n[Phase 1] Analyzing session patterns...")
        patterns = self.analyze_recent_sessions(limit=session_limit)

        if not patterns:
            print("[WARNING] No patterns found in recent sessions")
            return [], []

        print(f"[OK] Found {len(patterns)} patterns")

        # 2. Generate workflows from patterns
        print("\n[Phase 2] Generating workflows...")
        workflows = self.generate_workflows(patterns)

        if not workflows:
            print(
                "[WARNING] No workflows generated (patterns didn't meet quality threshold)"
            )
            return patterns, []

        print(f"[OK] Generated {len(workflows)} workflows")

        # 3. Save workflows
        if auto_save:
            print("\n[Phase 3] Saving workflows...")
            saved_count = self.save_workflows(workflows)
            print(f"[OK] Saved {saved_count} workflows to {self.workflows_dir}")

        print("\n" + "=" * 70)
        print("PIPELINE COMPLETE")
        print("=" * 70)

        return patterns, workflows


# ============================================================================
# USAGE EXAMPLES
# ============================================================================

if __name__ == "__main__":
    print("AutoWorkflow Generator Demo")
    print("=" * 70)

    generator = AutoWorkflowGenerator()

    # Example: Load a mock session and generate workflows
    # In real usage, this would run on actual session data

    print("\n[Demo] Running pattern analysis on recent sessions...")
    patterns, workflows = generator.run_full_analysis(session_limit=10, auto_save=False)

    print(f"\n[Results] Patterns found: {len(patterns)}")
    print(f"[Results] Workflows generated: {len(workflows)}")

    if workflows:
        print("\n[Sample Workflow]")
        wf = workflows[0]
        print(f"Name: {wf.name}")
        print(f"Description: {wf.description}")
        print(f"Steps: {len(wf.steps)}")
        for step in wf.steps:
            print(f"  - {step['tool']}.{step['action']}")

    print("\nâœ… Demo complete!")
