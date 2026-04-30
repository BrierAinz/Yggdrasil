"""
Language Router - Maps detected intents to specific tools

Maps conversational intents from ConversationalIntentDetector to specific tool executors
with parameter mapping and context management.
"""

import os
import sys

sys.path.append(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
)

import json
import re
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple

from src.core.memory.manager import MemoryManager
from src.core.tool_registry import ToolRegistry


@dataclass
class ToolMapping:
    """Structure for tool mapping configuration"""

    tool_name: str
    required_params: List[str]
    optional_params: List[str]
    confidence_threshold: float
    parameter_mapping: Dict[str, str]  # Maps intent params to tool params


class LanguageRouter:
    """
    Routes detected intents to appropriate tools with parameter mapping

    Example:
        Intent: code_review -> Tool: CodeAnalyzer
        Intent: research -> Tool: Research + WebBrowser
    """

    def __init__(self, tool_registry: ToolRegistry, memory_manager: MemoryManager):
        self.tool_registry = tool_registry
        self.memory = memory_manager
        self.mappings = self._build_tool_mappings()

    def _build_tool_mappings(self) -> Dict[str, ToolMapping]:
        """Build intent-to-tool mapping configuration"""
        return {
            "code_review": ToolMapping(
                tool_name="CodeAnalyzer",
                required_params=["target", "analysis_type"],
                optional_params=["file_path", "code_snippet"],
                confidence_threshold=0.7,
                parameter_mapping={"target": "target_path", "analysis_type": "mode"},
            ),
            "research": ToolMapping(
                tool_name="Research",
                required_params=["query"],
                optional_params=["sources", "depth", "format"],
                confidence_threshold=0.8,
                parameter_mapping={
                    "query": "search_query",
                    "sources": "source_preference",
                },
            ),
            "web_visit": ToolMapping(
                tool_name="WebBrowser",
                required_params=["url"],
                optional_params=["action", "wait_time"],
                confidence_threshold=0.9,
                parameter_mapping={"url": "url", "action": "operation"},
            ),
            "system_execute": ToolMapping(
                tool_name="SystemExecutor",
                required_params=["command"],
                optional_params=["timeout", "working_dir"],
                confidence_threshold=0.85,
                parameter_mapping={"command": "command", "working_dir": "cwd"},
            ),
            "generate": ToolMapping(
                tool_name="ImageProcessor",
                required_params=["prompt"],
                optional_params=["style", "size", "quality"],
                confidence_threshold=0.8,
                parameter_mapping={
                    "prompt": "prompt",
                    "style": "art_style",
                    "size": "dimensions",
                },
            ),
            "git": ToolMapping(
                tool_name="GitTools",
                required_params=["action"],
                optional_params=["path"],
                confidence_threshold=0.8,
                parameter_mapping={"action": "action", "path": "path"},
            ),
            "code_edit": ToolMapping(
                tool_name="CodeEditor",
                required_params=["action", "file_path"],
                optional_params=[
                    "target",
                    "replacement",
                    "content",
                    "line_number",
                    "overwrite",
                ],
                confidence_threshold=0.85,
                parameter_mapping={
                    "action": "action",
                    "file": "file_path",
                    "target": "target",
                    "replacement": "replacement",
                    "content": "content",
                },
            ),
            "code_search": ToolMapping(
                tool_name="GrepTool",
                required_params=["action", "pattern"],
                optional_params=["glob_pattern", "is_regex", "context_lines"],
                confidence_threshold=0.8,
                parameter_mapping={
                    "action": "action",
                    "pattern": "pattern",
                    "glob": "glob_pattern",
                },
            ),
            "memory_query": ToolMapping(
                tool_name="MemoryManager",
                required_params=["query"],
                optional_params=["context", "limit"],
                confidence_threshold=0.75,
                parameter_mapping={"query": "query", "context": "search_context"},
            ),
            "plan": ToolMapping(
                tool_name="PlanningEngine",
                required_params=["task"],
                optional_params=["constraints", "tools"],
                confidence_threshold=0.8,
                parameter_mapping={
                    "task": "task_description",
                    "constraints": "limitations",
                },
            ),
            "vision_analysis": ToolMapping(
                tool_name="VisualAnalyzer",
                required_params=["action"],
                optional_params=["prompt"],
                confidence_threshold=0.8,
                parameter_mapping={"action": "action", "query": "prompt"},
            ),
            "clarify": ToolMapping(
                tool_name="Self",
                required_params=["question"],
                optional_params=["context", "options"],
                confidence_threshold=0.9,
                parameter_mapping={"question": "clarification_request"},
            ),
            # ==================== CONVERSACIÃ“N GENERAL ====================
            "identity_query": ToolMapping(
                tool_name="Self",
                required_params=[],
                optional_params=["question"],
                confidence_threshold=0.6,
                parameter_mapping={"question": "identity_info"},
            ),
            "greeting": ToolMapping(
                tool_name="Self",
                required_params=[],
                optional_params=["time_of_day"],
                confidence_threshold=0.6,
                parameter_mapping={},
            ),
            "farewell": ToolMapping(
                tool_name="Self",
                required_params=[],
                optional_params=[],
                confidence_threshold=0.6,
                parameter_mapping={},
            ),
            "general_conversation": ToolMapping(
                tool_name="Self",
                required_params=[],
                optional_params=["topic"],
                confidence_threshold=0.6,
                parameter_mapping={"topic": "conversation_topic"},
            ),
        }

    async def route_intent(
        self, detected_intent: Dict, context: Dict = None
    ) -> Dict[str, Any]:
        """
        Route detected intent to appropriate tool(s) with parameter mapping

        Args:
            detected_intent: Intent from ConversationalIntentDetector
            context: Session context including conversation history

        Returns:
            Dict with tool_name, mapped_params, and execution_plan
        """
        intent_type = detected_intent.get("intent")
        confidence = detected_intent.get("confidence", 0.0)

        if not intent_type or intent_type not in self.mappings:
            # Try to infer tool from suggestions
            tool_suggestions = detected_intent.get("tool_suggestions", [])
            if tool_suggestions:
                return self._route_by_tool_suggestion(
                    tool_suggestions[0], detected_intent, context
                )
            else:
                return self._build_fallback_route(detected_intent, context)

        mapping = self.mappings[intent_type]

        # Check confidence threshold
        if confidence < mapping.confidence_threshold:
            # Low confidence - request clarification
            return self._build_clarification_route(detected_intent, mapping, context)

        # Map parameters
        mapped_params = self._map_parameters(detected_intent, mapping, context)

        # Validate required parameters
        missing_params = [
            param
            for param in mapping.required_params
            if param not in mapped_params or not mapped_params[param]
        ]

        if missing_params:
            # Missing required params - request clarification
            return self._build_parameter_request_route(
                detected_intent, missing_params, context
            )

        # Build execution plan
        execution_plan = {
            "tool_name": mapping.tool_name,
            "parameters": mapped_params,
            "intent_type": intent_type,
            "confidence": confidence,
            "requires_approval": self._requires_approval(
                mapping, mapped_params, context
            ),
        }

        return execution_plan

    def _map_parameters(
        self, intent: Dict, mapping: ToolMapping, context: Dict = None
    ) -> Dict[str, Any]:
        """Map intent parameters to tool parameters"""
        mapped = {}
        intent_params = intent.get("parameters", {})

        # Direct parameter mapping
        for intent_param, tool_param in mapping.parameter_mapping.items():
            if intent_param in intent_params:
                mapped[tool_param] = intent_params[intent_param]

        # Handle extracted_constraints
        constraints = intent.get("extracted_constraints", {})
        for intent_param, tool_param in mapping.parameter_mapping.items():
            if intent_param in constraints and tool_param not in mapped:
                mapped[tool_param] = constraints[intent_param]

        # Infer from context if needed
        if context:
            self._infer_parameters_from_context(mapped, mapping, context)

        return mapped

    def _infer_parameters_from_context(
        self, mapped: Dict, mapping: ToolMapping, context: Dict
    ):
        """Infer missing parameters from conversation context"""
        context_data = context.get("current_context", {})

        # If target is missing but we have active file/code context
        if (
            "target_path" in mapping.parameter_mapping.values()
            and "target_path" not in mapped
        ):
            if "active_file" in context_data:
                mapped["target_path"] = context_data["active_file"]
            elif "code_snippet" in context_data:
                mapped["code_snippet"] = context_data["code_snippet"]

        # If working directory is missing
        if "cwd" in mapping.parameter_mapping.values() and "cwd" not in mapped:
            if "working_directory" in context_data:
                mapped["cwd"] = context_data["working_directory"]

    def _route_by_tool_suggestion(
        self, tool_name: str, intent: Dict, context: Dict = None
    ) -> Dict[str, Any]:
        """Route based on direct tool suggestion"""
        # Try to find matching intent type for tool
        for intent_type, mapping in self.mappings.items():
            if mapping.tool_name == tool_name:
                # Use the mapping but with tool suggestions as params
                mapped_params = {"query": intent.get("raw_query", "")}

                return {
                    "tool_name": tool_name,
                    "parameters": mapped_params,
                    "intent_type": intent_type,
                    "confidence": intent.get("confidence", 0.5),
                    "requires_approval": True,  # Be cautious with direct tool suggestions
                }

        # Fallback: direct tool execution
        return {
            "tool_name": tool_name,
            "parameters": {"query": intent.get("raw_query", "")},
            "intent_type": "direct_tool",
            "confidence": intent.get("confidence", 0.5),
            "requires_approval": True,
        }

    def _build_clarification_route(
        self, intent: Dict, mapping: ToolMapping, context: Dict = None
    ) -> Dict[str, Any]:
        """Build route for requesting clarification"""
        return {
            "tool_name": "Self",
            "parameters": {
                "clarification_request": self._generate_clarification_question(
                    intent, mapping
                ),
                "intent_data": intent,
            },
            "intent_type": "clarify",
            "confidence": intent.get("confidence", 0.0),
            "requires_approval": False,
        }

    def _build_parameter_request_route(
        self, intent: Dict, missing_params: List[str], context: Dict = None
    ) -> Dict[str, Any]:
        """Build route for requesting missing parameters"""
        return {
            "tool_name": "Self",
            "parameters": {
                "clarification_request": self._generate_parameter_question(
                    intent, missing_params
                ),
                "missing_parameters": missing_params,
                "intent_data": intent,
            },
            "intent_type": "clarify",
            "confidence": intent.get("confidence", 0.7),
            "requires_approval": False,
        }

    def _build_fallback_route(
        self, intent: Dict, context: Dict = None
    ) -> Dict[str, Any]:
        """Build fallback route when intent is unclear"""
        return {
            "tool_name": "Self",
            "parameters": {
                "clarification_request": f"No entendi tu solicitud: '{intent.get('raw_query', '')}'. Por favor, podrias reformularla?",
                "intent_data": intent,
            },
            "intent_type": "clarify",
            "confidence": 0.0,
            "requires_approval": False,
        }

    def _generate_clarification_question(
        self, intent: Dict, mapping: ToolMapping
    ) -> str:
        """Generate clarification question for low confidence"""
        intent_type = intent.get("intent", "unknown")
        confidence = intent.get("confidence", 0.0)

        questions = {
            "code_review": f"Quieres que revise codigo? (confianza: {confidence:.0%})",
            "research": f"Buscas informacion sobre algo? (confianza: {confidence:.0%})",
            "web_visit": f"Quieres que visite una pagina web? (confianza: {confidence:.0%})",
            "system_execute": f"Quieres que ejecute un comando? (confianza: {confidence:.0%})",
            "generate": f"Quieres que genere una imagen? (confianza: {confidence:.0%})",
        }

        return questions.get(
            intent_type,
            f"No estoy seguro de tu intencion (confianza: {confidence:.0%}). Podrias aclarar?",
        )

    def _generate_parameter_question(
        self, intent: Dict, missing_params: List[str]
    ) -> str:
        """Generate question for missing parameters"""
        intent_type = intent.get("intent", "unknown")

        questions = {
            "code_review": {
                "target": "Que codigo quieres que revise? Por favor, proporciona archivo o codigo.",
                "analysis_type": "Que tipo de analisis quieres? (seguridad, performance, errores)",
            },
            "research": {"query": "Que tema quieres que investigue?"},
            "web_visit": {"url": "Que pagina web quieres que visite?"},
            "system_execute": {"command": "Que comando quieres que ejecute?"},
            "generate": {
                "prompt": "Que imagen quieres que genere? Describe lo que quieres ver."
            },
            "git": {
                "action": "Que accion git quieres realizar? (commit, push, pull, status)"
            },
        }

        # Get first missing param question
        param_questions = questions.get(intent_type, {})
        for param in missing_params:
            if param in param_questions:
                return param_questions[param]

        return f"Necesito mas informacion para completar tu solicitud. Por favor, especifica: {', '.join(missing_params)}"

    def _requires_approval(
        self, mapping: ToolMapping, params: Dict, context: Dict = None
    ) -> bool:
        """Determine if tool execution requires user approval"""
        # High-risk tools always require approval
        high_risk_tools = {
            "GitTools": ["push", "reset", "checkout", "branch -d"],
            "SystemExecutor": [],  # All system commands require approval
            "ImageProcessor": [],  # All image generations require approval
        }

        tool_name = mapping.tool_name

        # Check if tool is high-risk
        if tool_name in high_risk_tools:
            # For GitTools, check specific actions
            if tool_name == "GitTools":
                action = params.get("operation", "")
                if any(risky in action for risky in high_risk_tools["GitTools"]):
                    return True
            else:
                return True

        # Check if user has disabled auto-approval in context
        if context and context.get("require_approval_all", False):
            return True

        # Check parameter sensitivity
        sensitive_params = [
            "delete",
            "remove",
            "force",
            "overwrite",
            "sudo",
            "rm -rf",
            "format",
        ]

        param_values = json.dumps(params).lower()
        if any(sensitive in param_values for sensitive in sensitive_params):
            return True

        return False

    def validate_tool_availability(self, tool_name: str) -> Tuple[bool, str]:
        """Check if tool is available for execution"""
        try:
            # Check if tool exists in registry
            tool_class = self.tool_registry.get_tool(tool_name)
            if not tool_class:
                return False, f"Tool '{tool_name}' not found in registry"

            # Check if tool has required dependencies
            if hasattr(tool_class, "check_dependencies"):
                available, reason = tool_class.check_dependencies()
                if not available:
                    return (
                        False,
                        f"Tool '{tool_name}' dependencies not available: {reason}",
                    )

            return True, "Tool available"

        except Exception as e:
            return False, f"Error checking tool '{tool_name}': {str(e)}"

    def get_compatible_tools(self, intent_type: str, confidence: float) -> List[str]:
        """Get list of tools compatible with intent"""
        compatible = []

        # Primary mapping
        if intent_type in self.mappings:
            mapping = self.mappings[intent_type]
            if confidence >= mapping.confidence_threshold:
                compatible.append(mapping.tool_name)

        # Additional tool suggestions based on intent type
        tool_suggestions = {
            "code_review": ["CodeAnalyzer"],
            "research": ["Research", "WebBrowser"],
            "web_visit": ["WebBrowser"],
            "system_execute": ["SystemExecutor"],
            "generate": ["ImageProcessor"],
            "git": ["GitTools"],
            "memory_query": ["MemoryManager"],
            "plan": ["PlanningEngine"],
        }

        if intent_type in tool_suggestions:
            for tool in tool_suggestions[intent_type]:
                if tool not in compatible:
                    # Check if tool is available
                    available, _ = self.validate_tool_availability(tool)
                    if available:
                        compatible.append(tool)

        return compatible


# Test harness for development
if __name__ == "__main__":
    import asyncio

    class MockToolRegistry:
        def get_tool(self, tool_name):
            # Mock tool registry for testing
            class MockTool:
                @staticmethod
                def check_dependencies():
                    return True, "OK"

            return MockTool()

    class MockMemoryManager:
        pass

    async def test_router():
        """Test the language router"""
        print("Testing Language Router")
        print("=" * 60)

        registry = MockToolRegistry()
        memory = MockMemoryManager()
        router = LanguageRouter(registry, memory)

        # Test cases
        test_cases = [
            {
                "name": "Code review with low confidence",
                "intent": {
                    "intent": "code_review",
                    "confidence": 0.6,
                    "parameters": {"target": "test.py"},
                    "raw_query": "revisa este codigo",
                },
            },
            {
                "name": "Research with high confidence",
                "intent": {
                    "intent": "research",
                    "confidence": 0.95,
                    "parameters": {"query": "async Python"},
                    "raw_query": "busca sobre async en Python",
                },
            },
            {
                "name": "Web visit missing URL",
                "intent": {
                    "intent": "web_visit",
                    "confidence": 0.85,
                    "parameters": {},
                    "raw_query": "visita la pagina",
                },
            },
            {
                "name": "Unknown intent",
                "intent": {
                    "intent": "unknown_intent",
                    "confidence": 0.3,
                    "parameters": {},
                    "tool_suggestions": ["Research"],
                    "raw_query": "haz algo desconocido",
                },
            },
            {
                "name": "System command (requires approval)",
                "intent": {
                    "intent": "system_execute",
                    "confidence": 0.9,
                    "parameters": {"command": "ls -la"},
                    "raw_query": "ejecuta ls -la",
                },
            },
        ]

        for test in test_cases:
            print(f"\n[Test] {test['name']}")
            print(f"Query: {test['intent']['raw_query']}")

            result = await router.route_intent(test["intent"])

            print(f"  Tool: {result['tool_name']}")
            print(f"  Intent Type: {result['intent_type']}")
            print(f"  Confidence: {result['confidence']:.2f}")
            print(f"  Requires Approval: {result['requires_approval']}")
            print(f"  Parameters: {result['parameters']}")

            if result["tool_name"] == "Self":
                print(
                    f"  Clarification: {result['parameters']['clarification_request']}"
                )

        print("\n[OK] Tests completed!")

    # Run tests
    asyncio.run(test_router())
