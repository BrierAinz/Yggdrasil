"""
Lilith - Persona Auto-Updater
Analyzes successful sessions and proposes learned instructions for persona.md
"""

import json
import re
import time
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from src.observability.session_logger import SessionLogger
from src.observability.telemetry import AgentTelemetry


@dataclass
class PersonaUpdate:
    """A proposed update to persona.md"""

    update_id: str
    category: str  # "tool_preference", "workflow_pattern", "communication_style", "capability"
    instruction: str  # Natural language instruction to add
    reasoning: str
    confidence: float
    source_sessions: List[str]
    auto_applicable: bool = False  # Always False for safety â€” requires review

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class PersonaAutoUpdater:
    """
    Analyzes session history to learn effective patterns and propose
    additions to persona.md.

    Safety: NEVER overwrites existing persona content.
    Only appends to a dedicated "## Auto-Learned Instructions" section.
    All updates require explicit human approval.
    """

    SECTION_HEADER = "\n\n## Auto-Learned Instructions\n"
    SECTION_MARKER = "## Auto-Learned Instructions"

    def __init__(self, persona_path: str = None):
        """Initialize with persona file path and data sources."""
        if persona_path is None:
            persona_path = str(
                Path(
                    "D:/Proyectos/Yggdrasil/Asgard/Lilith/Core/Workspace/Alma/persona.md"
                )
            )
        self.persona_path = Path(persona_path)

        self.session_logger = SessionLogger()
        self.telemetry = AgentTelemetry()

        # Analysis thresholds
        self.min_success_rate = 0.8  # Tool must have 80%+ success
        self.min_usage_count = 5  # Tool must be used 5+ times
        self.min_confidence = 0.7  # Minimum confidence for proposal

        # Pending updates storage
        self.updates_dir = Path(
            "D:/Proyectos/Yggdrasil/Asgard/Lilith/Core/Backend/core/persona_updates"
        )
        self.updates_dir.mkdir(parents=True, exist_ok=True)

    def analyze_effective_patterns(self) -> List[Dict[str, Any]]:
        """
        Analyze session data to find effective patterns worth learning.

        Returns list of pattern dicts with type, details, and confidence.
        """
        patterns = []

        # 1. Analyze tool preferences (which tools succeed most)
        tool_patterns = self._analyze_tool_preferences()
        patterns.extend(tool_patterns)

        # 2. Analyze successful command patterns
        command_patterns = self._analyze_command_patterns()
        patterns.extend(command_patterns)

        # 3. Analyze session outcomes for workflow effectiveness
        workflow_patterns = self._analyze_workflow_effectiveness()
        patterns.extend(workflow_patterns)

        return patterns

    def _analyze_tool_preferences(self) -> List[Dict[str, Any]]:
        """Identify tools with consistently high success rates."""
        patterns = []

        tool_stats = self.session_logger.get_tool_usage_stats()
        if not tool_stats:
            return patterns

        for tool_name, stats in tool_stats.items():
            total_calls = stats.get("total_calls", 0)
            success_rate = stats.get("success_rate", 0) / 100.0  # Convert from percent
            avg_duration = stats.get("avg_duration_ms", 0)

            if (
                total_calls >= self.min_usage_count
                and success_rate >= self.min_success_rate
            ):
                confidence = min(
                    1.0, success_rate * (total_calls / (self.min_usage_count * 3))
                )

                patterns.append(
                    {
                        "type": "tool_preference",
                        "tool": tool_name,
                        "success_rate": round(success_rate, 3),
                        "total_calls": total_calls,
                        "avg_duration_ms": round(avg_duration, 1),
                        "confidence": round(min(confidence, 1.0), 3),
                    }
                )

        return patterns

    def _analyze_command_patterns(self) -> List[Dict[str, Any]]:
        """Analyze successful vs failed commands to find effective patterns."""
        patterns = []

        recent_sessions = self.session_logger.get_recent_sessions(limit=50)

        # Track command prefixes and their success rates
        prefix_stats = {}
        for session in recent_sessions:
            interactions = self.session_logger.get_session_interactions(
                session.session_id
            )
            for interaction in interactions:
                if interaction.message_type == "user_command":
                    content = interaction.content
                    # Extract command prefix (e.g., @git, @run, @plan)
                    prefix_match = re.match(r"(@\w+)", content)
                    if prefix_match:
                        prefix = prefix_match.group(1)
                        if prefix not in prefix_stats:
                            prefix_stats[prefix] = {"success": 0, "total": 0}
                        prefix_stats[prefix]["total"] += 1
                        # Check if session was successful
                        if session.final_status == "success":
                            prefix_stats[prefix]["success"] += 1

        for prefix, stats in prefix_stats.items():
            if stats["total"] >= self.min_usage_count:
                rate = stats["success"] / stats["total"]
                if rate >= self.min_success_rate:
                    patterns.append(
                        {
                            "type": "command_pattern",
                            "prefix": prefix,
                            "success_rate": round(rate, 3),
                            "total_uses": stats["total"],
                            "confidence": round(min(rate * 0.9, 1.0), 3),
                        }
                    )

        return patterns

    def _analyze_workflow_effectiveness(self) -> List[Dict[str, Any]]:
        """Analyze which multi-step workflows have highest completion rates."""
        patterns = []

        recent_sessions = self.session_logger.get_recent_sessions(limit=50)

        # Count sessions by outcome
        success_count = sum(1 for s in recent_sessions if s.final_status == "success")
        total = len(recent_sessions)

        if total >= 10:
            overall_rate = success_count / total
            if overall_rate >= 0.7:
                patterns.append(
                    {
                        "type": "workflow_effectiveness",
                        "description": "Overall session success rate is strong",
                        "success_rate": round(overall_rate, 3),
                        "sample_size": total,
                        "confidence": round(min(overall_rate * 0.8, 1.0), 3),
                    }
                )

        return patterns

    def extract_instructions(
        self, patterns: List[Dict[str, Any]]
    ) -> List[PersonaUpdate]:
        """Convert analyzed patterns into natural-language persona instructions."""
        updates = []

        for pattern in patterns:
            if pattern.get("confidence", 0) < self.min_confidence:
                continue

            update = self._pattern_to_instruction(pattern)
            if update:
                updates.append(update)

        # Sort by confidence descending
        updates.sort(key=lambda u: u.confidence, reverse=True)
        return updates

    def _pattern_to_instruction(
        self, pattern: Dict[str, Any]
    ) -> Optional[PersonaUpdate]:
        """Convert a single pattern into a PersonaUpdate."""
        ptype = pattern.get("type", "")

        if ptype == "tool_preference":
            tool = pattern["tool"]
            rate = pattern["success_rate"]
            calls = pattern["total_calls"]
            return PersonaUpdate(
                update_id=f"pref_{tool}_{int(time.time())}",
                category="tool_preference",
                instruction=f"- **{tool}** is a reliable tool ({rate:.0%} success over {calls} uses). Prefer it for its domain tasks.",
                reasoning=f"Tool '{tool}' shows {rate:.0%} success rate across {calls} invocations.",
                confidence=pattern["confidence"],
                source_sessions=[],
            )

        elif ptype == "command_pattern":
            prefix = pattern["prefix"]
            rate = pattern["success_rate"]
            return PersonaUpdate(
                update_id=f"cmd_{prefix}_{int(time.time())}",
                category="workflow_pattern",
                instruction=f"- The `{prefix}` command pattern is highly effective ({rate:.0%} success). Continue using it for its intended tasks.",
                reasoning=f"Command prefix '{prefix}' shows {rate:.0%} success rate.",
                confidence=pattern["confidence"],
                source_sessions=[],
            )

        elif ptype == "workflow_effectiveness":
            rate = pattern["success_rate"]
            return PersonaUpdate(
                update_id=f"workflow_{int(time.time())}",
                category="workflow_pattern",
                instruction=f"- Current operational workflow shows {rate:.0%} session success rate. Maintain current approach.",
                reasoning=pattern.get("description", "Strong overall effectiveness"),
                confidence=pattern["confidence"],
                source_sessions=[],
            )

        return None

    def propose_update(self, updates: List[PersonaUpdate]) -> Dict[str, Any]:
        """
        Create a proposal for persona.md changes.
        Returns a dict with the proposed additions and metadata.
        NEVER auto-applies â€” always requires human review.
        """
        if not updates:
            return {"status": "no_updates", "instructions": []}

        # Build the text block to append
        lines = []
        for update in updates:
            lines.append(update.instruction)

        additions_text = "\n".join(lines)

        proposal = {
            "status": "pending_review",
            "timestamp": time.time(),
            "target_file": str(self.persona_path),
            "section": self.SECTION_MARKER,
            "additions_text": additions_text,
            "updates": [u.to_dict() for u in updates],
            "count": len(updates),
        }

        # Save proposal to disk for review
        proposal_file = self.updates_dir / f"proposal_{int(time.time())}.json"
        with open(proposal_file, "w", encoding="utf-8") as f:
            json.dump(proposal, f, indent=2, ensure_ascii=False)

        print(f"[PersonaUpdater] Proposal saved: {proposal_file}")
        print(f"[PersonaUpdater] {len(updates)} instructions proposed")

        return proposal

    def apply_update(self, proposal: Dict[str, Any]) -> bool:
        """
        Apply a reviewed and approved proposal to persona.md.
        SAFETY: Only appends to dedicated section, never overwrites.

        Returns True if applied successfully.
        """
        if proposal.get("status") != "approved":
            print("[PersonaUpdater] ERROR: Proposal not approved. Cannot apply.")
            return False

        additions = proposal.get("additions_text", "")
        if not additions:
            print("[PersonaUpdater] No additions to apply.")
            return False

        # Read existing persona
        if not self.persona_path.exists():
            print(f"[PersonaUpdater] ERROR: {self.persona_path} not found")
            return False

        with open(self.persona_path, "r", encoding="utf-8") as f:
            content = f.read()

        # Check if auto-learned section already exists
        if self.SECTION_MARKER in content:
            # Append to existing section
            # Find the section and append before the next ## or EOF
            marker_pos = content.index(self.SECTION_MARKER)
            section_start = marker_pos + len(self.SECTION_MARKER)

            # Find next section header or EOF
            next_section = content.find("\n## ", section_start + 1)
            if next_section == -1:
                # Append at end
                content = content.rstrip() + "\n" + additions + "\n"
            else:
                # Insert before next section
                content = (
                    content[:next_section] + additions + "\n" + content[next_section:]
                )
        else:
            # Create the section
            content = content.rstrip() + self.SECTION_HEADER + additions + "\n"

        # Write updated persona
        with open(self.persona_path, "w", encoding="utf-8") as f:
            f.write(content)

        print(
            f"[PersonaUpdater] Applied {proposal.get('count', 0)} updates to {self.persona_path}"
        )
        return True

    def get_pending_proposals(self) -> List[Dict[str, Any]]:
        """Get all proposals pending review."""
        pending = []
        for f in self.updates_dir.glob("proposal_*.json"):
            with open(f, "r", encoding="utf-8") as fh:
                data = json.load(fh)
                if data.get("status") == "pending_review":
                    data["_file"] = str(f)
                    pending.append(data)
        return pending

    def run_full_analysis(self) -> Dict[str, Any]:
        """
        Run the complete analysis pipeline:
        1. Analyze patterns from sessions
        2. Extract instructions
        3. Create proposal (for human review)
        """
        print("=" * 70)
        print("PERSONA AUTO-UPDATER ANALYSIS")
        print("=" * 70)

        # 1. Analyze
        print("\n[Phase 1] Analyzing effective patterns...")
        patterns = self.analyze_effective_patterns()
        print(f"[OK] Found {len(patterns)} patterns")

        if not patterns:
            print("[INFO] No patterns meet threshold criteria")
            return {"status": "no_patterns", "patterns": 0, "proposals": 0}

        # 2. Extract instructions
        print("\n[Phase 2] Extracting instructions...")
        updates = self.extract_instructions(patterns)
        print(f"[OK] Generated {len(updates)} instructions")

        # 3. Create proposal
        print("\n[Phase 3] Creating proposal for review...")
        proposal = self.propose_update(updates)

        print("\n" + "=" * 70)
        print("ANALYSIS COMPLETE")
        print("=" * 70)

        return proposal


# ============================================================================
# USAGE
# ============================================================================

if __name__ == "__main__":
    print("Persona Auto-Updater Demo")
    print("=" * 70)

    updater = PersonaAutoUpdater()

    # Run full analysis
    result = updater.run_full_analysis()

    print(f"\nResult: {result.get('status')}")
    print(f"Proposals: {result.get('count', 0)}")

    if result.get("additions_text"):
        print("\n--- Proposed additions ---")
        print(result["additions_text"])
        print("--- End ---")

    print("\nâœ… Demo complete!")
