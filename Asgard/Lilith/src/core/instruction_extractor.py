"""
Lilith - Instruction Extractor
Extracts persona instructions from successful command patterns
"""

import json
import re
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional


@dataclass
class ExtractedInstruction:
    """Represents a persona instruction extracted from patterns"""

    instruction_id: str
    category: str
    system_prompt: str
    quality_score: float
    evidence: Dict[str, Any]
    auto_applicable: bool
    requires_review: bool

    def to_dict(self) -> Dict[str, Any]:
        return {
            "instruction_id": self.instruction_id,
            "category": self.category,
            "system_prompt": self.system_prompt,
            "quality_score": round(self.quality_score, 3),
            "evidence": self.evidence,
            "auto_applicable": self.auto_applicable,
            "requires_review": self.requires_review,
            "created_at": time.time(),
        }


@dataclass
class QualityScore:
    """Represents quality metrics for an instruction"""

    overall_score: float
    sample_size: int
    success_rate: float
    diversity_score: float
    clarity_score: float
    uniqueness_score: float


class InstructionExtractor:
    """Extracts persona instructions from command patterns"""

    def __init__(self):
        self.min_sample_size = 5
        self.min_success_rate = 0.70  # Lower threshold for testing
        self.min_clarity_score = 0.6
        self.min_uniqueness_score = 0.5
        self.auto_apply_threshold = 0.9
        self.review_threshold = 0.7

    def extract_instructions(self, patterns) -> List[ExtractedInstruction]:
        print(
            f"[InstructionExtractor] Extracting instructions from {len(patterns)} patterns"
        )
        instructions = []

        for pattern in patterns:
            if not self._validate_pattern_quality(pattern):
                continue

            instruction = self._generate_instruction(pattern)
            if instruction:
                instructions.append(instruction)
                print(f"[InstructionExtractor] Generated: {instruction.category}")

        print(f"[InstructionExtractor] Extracted {len(instructions)} instructions")
        return instructions

    def _validate_pattern_quality(self, pattern) -> bool:
        if pattern.frequency < self.min_sample_size:
            return False
        if pattern.success_rate < self.min_success_rate:
            return False
        if len(set(pattern.user_phrases)) < 2:
            return False
        return True

    def _generate_instruction(self, pattern) -> Optional[ExtractedInstruction]:
        system_prompt = self._generate_system_prompt(pattern)
        if not system_prompt:
            return None

        quality = self._calculate_quality_score(pattern)
        auto_apply = quality.overall_score >= self.auto_apply_threshold
        needs_review = quality.overall_score < self.review_threshold

        instruction = ExtractedInstruction(
            instruction_id=f"ins_{pattern.pattern_id}_{int(time.time())}",
            category=pattern.category,
            system_prompt=system_prompt,
            quality_score=quality.overall_score,
            evidence={
                "sample_size": pattern.frequency,
                "success_rate": pattern.success_rate,
                "command_variations": pattern.user_phrases,
                "common_constraints": pattern.common_constraints,
                "quality_breakdown": quality.__dict__,
            },
            auto_applicable=auto_apply,
            requires_review=needs_review,
        )

        return instruction

    def _generate_system_prompt(self, pattern) -> str:
        intent_type = self._classify_intent_type(pattern)

        if intent_type == "tool_selection":
            return self._generate_tool_selection_prompt(pattern)
        elif intent_type == "constraint_handling":
            return self._generate_constraint_prompt(pattern)
        elif intent_type == "workflow_sequence":
            return self._generate_workflow_prompt(pattern)
        elif intent_type == "clarification":
            return self._generate_clarification_prompt(pattern)
        else:
            return self._generate_generic_prompt(pattern)

    def _classify_intent_type(self, pattern) -> str:
        if pattern.common_constraints:
            return "constraint_handling"

        if hasattr(pattern, "suggested_action") and "Use" in pattern.suggested_action:
            return "tool_selection"

        if "clarification" in pattern.suggested_action.lower():
            return "clarification"

        return "generic"

    def _generate_tool_selection_prompt(self, pattern) -> str:
        keywords = self._extract_keywords(pattern.user_phrases)
        prompt = f"""When user intent involves {', '.join(keywords[:3])}:

1. Focus on understanding the core task
2. Select the most appropriate tool based on intent
3. Prioritize direct tool execution over explanation"""

        if pattern.frequency:
            prompt += (
                f"\n4. This pattern has proven effective {pattern.frequency} times"
            )

        return prompt

    def _generate_constraint_prompt(self, pattern) -> str:
        if not pattern.common_constraints:
            return ""

        prompt = """When user provides constraints:

1. Identify explicit constraints immediately
2. Apply constraints directly to tool parameters
3. Respect constraint priority: explicit > implied"""

        if pattern.common_constraints:
            prompt += f"\n\nCommon effective constraints: {', '.join(pattern.common_constraints[:3])}"

        return prompt

    def _generate_workflow_prompt(self, pattern) -> str:
        return """When handling multi-step workflows:

1. Break down complex requests into sequential steps
2. Ensure each step has clear dependencies
3. Verify intermediate results before proceeding"""

    def _generate_clarification_prompt(self, pattern) -> str:
        return """When user request is ambiguous:

1. Ask clarifying questions before executing
2. Focus on scope, priority, and depth
3. Provide constrained examples"""

    def _generate_generic_prompt(self, pattern) -> str:
        keywords = self._extract_keywords(pattern.user_phrases)
        return f"""For requests involving {', '.join(keywords[:2])}:

1. Follow standard tool execution
2. Apply best practices from previous successful sessions"""

    def _extract_keywords(self, phrases: List[str]) -> List[str]:
        keywords = []
        for phrase in phrases:
            words = phrase.lower().split()
            keywords.extend([w for w in words if len(w) > 3])
        return list(set(keywords))[:5]

    def _calculate_quality_score(self, pattern) -> QualityScore:
        sample_size = pattern.frequency
        success_rate = pattern.success_rate

        diversity = len(set(pattern.user_phrases)) / len(pattern.user_phrases)

        clarity = self._calculate_clarity(pattern)
        uniqueness = self._calculate_uniqueness(pattern)

        overall = (
            success_rate * 0.4 + diversity * 0.2 + clarity * 0.2 + uniqueness * 0.2
        )

        return QualityScore(
            overall_score=overall,
            sample_size=sample_size,
            success_rate=success_rate,
            diversity_score=diversity,
            clarity_score=clarity,
            uniqueness_score=uniqueness,
        )

    def _calculate_clarity(self, pattern) -> float:
        avg_length = sum(len(phrase) for phrase in pattern.user_phrases) / len(
            pattern.user_phrases
        )
        return min(1.0, 100 / avg_length) if avg_length > 0 else 0.5

    def _calculate_uniqueness(self, pattern) -> float:
        words = []
        for phrase in pattern.user_phrases:
            words.extend(phrase.lower().split())
        unique_ratio = len(set(words)) / len(words) if words else 0.5
        return unique_ratio
