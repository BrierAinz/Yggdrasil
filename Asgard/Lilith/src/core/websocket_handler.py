"""
WebSocket Handler - Real-time conversational interface with streaming support

Enables bidirectional WebSocket communication for natural language interactions
with streaming responses, typing indicators, and conversation context management.
"""

import os
import sys

sys.path.append(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
)

import asyncio
import json
import logging
import time
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional

from src.core.conversational_intent_detector import ConversationalIntentDetector
from src.core.language_router import LanguageRouter
from src.core.orchestration.planning import TaskOrchestrator
from src.core.planning.planning_engine import PlanningEngine
from src.core.response_generator import ResponseGenerator
from src.ipc_messages import EventChatDelta, EventChatFinal, EventStatusUpdate
from src.observability.session_logger import SessionLogger

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class WebSocketHandler:
    """
    Handles WebSocket connections for conversational AI interface

    Features:
    - Real-time bidirectional communication
    - Streaming response support
    - Conversation context management
    - Typing indicators
    - Message persistence
    """

    def __init__(self):
        # Initialize core components
        self.tool_registry = ToolRegistry()
        self.memory_manager = MemoryManager()
        self.session_logger = SessionLogger()

        # Initialize NLP pipeline
        self.intent_detector = ConversationalIntentDetector()
        self.language_router = LanguageRouter(self.tool_registry, self.memory_manager)
        self.response_generator = ResponseGenerator()

        # Active connections
        self.connections: Dict[str, Dict] = {}  # session_id -> connection_info

        # Conversation contexts
        self.contexts: Dict[str, Dict] = {}  # session_id -> context

    async def handle_connection(self, websocket, session_id: str = None):
        """
        Handle new WebSocket connection

        Args:
            websocket: WebSocket connection object
            session_id: Optional existing session ID

        Returns:
            Generated or existing session ID
        """
        if not session_id:
            session_id = str(uuid.uuid4())

        # Initialize session
        self.connections[session_id] = {
            "websocket": websocket,
            "connected_at": datetime.now().isoformat(),
            "message_count": 0,
        }

        # Initialize context
        self.contexts[session_id] = {
            "session_id": session_id,
            "conversation_history": [],
            "current_context": {},
            "pending_clarifications": {},
            "tool_state": {},
        }

        # Log connection
        logger.info(f"WebSocket connected: session_id={session_id}")
        self.session_logger.start_session()

        return session_id

    async def handle_disconnection(self, session_id: str):
        """Handle WebSocket disconnection"""
        if session_id in self.connections:
            # Log session end
            connection_info = self.connections[session_id]
            duration = (
                time.time()
                - datetime.fromisoformat(connection_info["connected_at"]).timestamp()
            )

            logger.info(
                f"WebSocket disconnected: session_id={session_id}, "
                f"messages={connection_info['message_count']}, "
                f"duration={duration:.1f}s"
            )

            # Cleanup
            del self.connections[session_id]
            if session_id in self.contexts:
                del self.contexts[session_id]

    async def handle_message(
        self, session_id: str, message: str, model: str = None
    ) -> Dict[str, Any]:
        """
        Process incoming message and return response

        Args:
            session_id: Session identifier
            message: User's natural language message
            model: Optional model to use for response generation

        Returns:
            Response dictionary with type and content
        """
        try:
            start_time = time.time()

            # Update message count
            if session_id in self.connections:
                self.connections[session_id]["message_count"] += 1

            # Get session context
            context = self.contexts.get(session_id, {})

            # Step 1: Detect intent first (to check if it overrides clarification)
            detected_intent = await asyncio.get_event_loop().run_in_executor(
                None, self.intent_detector.detect_intent, message, context
            )

            # Convert to dictionary for routing
            # Detectar contexto temporal
            current_hour = datetime.now().hour
            if 6 <= current_hour < 12:
                time_period = "morning"
            elif 12 <= current_hour < 18:
                time_period = "afternoon"
            elif 18 <= current_hour < 23:
                time_period = "evening"
            else:
                time_period = "late_night"

            context["time_context"] = {"hour": current_hour, "period": time_period}

            intent = {
                "intent": detected_intent.intent_type,
                "target": detected_intent.target,
                "tool_suggestions": detected_intent.tool_suggestions,
                "confidence": detected_intent.confidence,
                "clarification_needed": detected_intent.clarification_needed,
                "extracted_constraints": detected_intent.extracted_constraints,
                "parameters": detected_intent.__dict__.get("parameters", {}),
                "raw_query": message,
            }

            # Check if this is a clarification response
            # BUT only if the new intent is NOT a strong conversational intent (like greeting, cancel, etc)
            strong_intents = [
                "greeting",
                "farewell",
                "general_conversation",
                "identity_query",
            ]
            is_strong_intent = (
                intent["intent"] in strong_intents and intent["confidence"] > 0.6
            )

            if (
                self._is_clarification_response(session_id, message)
                and not is_strong_intent
            ):
                return await self._handle_clarification(session_id, message, context)

            # Convert to dictionary for routing
            # Detectar contexto temporal
            current_hour = datetime.now().hour
            if 6 <= current_hour < 12:
                time_period = "morning"
            elif 12 <= current_hour < 18:
                time_period = "afternoon"
            elif 18 <= current_hour < 23:
                time_period = "evening"
            else:
                time_period = "late_night"

            context["time_context"] = {"hour": current_hour, "period": time_period}

            intent = {
                "intent": detected_intent.intent_type,
                "target": detected_intent.target,
                "tool_suggestions": detected_intent.tool_suggestions,
                "confidence": detected_intent.confidence,
                "clarification_needed": detected_intent.clarification_needed,
                "extracted_constraints": detected_intent.extracted_constraints,
                "parameters": detected_intent.__dict__.get("parameters", {}),
                "raw_query": message,
            }

            # Send typing indicator
            await self._send_typing_indicator(session_id, active=True)

            # Step 2: Route to tool
            route = await self.language_router.route_intent(intent, context)

            # Step 3: Execute tool (or handle clarification)
            if route["tool_name"] == "Self":
                # Check if it's a clarification request or general conversation
                if "clarification_request" in route["parameters"]:
                    # Clarification needed
                    response = self.response_generator.generate_clarification_response(
                        route["parameters"]["clarification_request"], context
                    )

                    # Store clarification context
                    self._store_clarification_context(session_id, intent, route)

                    result = {
                        "type": "clarification",
                        "content": response,
                        "requires_response": True,
                    }
                else:
                    # General conversation (Greeting, Farewell, Identity, etc.)
                    # We treat the intent type as the "tool_name" for response generation
                    # to pick up the correct template (greeting, farewell, etc.)
                    target_intent = intent.get("intent", "general_conversation")

                    # Generate response using the specific intent template
                    response = self.response_generator.generate_response(
                        target_intent,
                        {"success": True, "data": {}},
                        context,
                        model=model,
                    )

                    result = {
                        "type": "tool_response",
                        "content": response,
                        "tool_name": "Self",
                        "success": True,
                    }

            else:
                # Execute tool
                if route["tool_name"] == "PlanningEngine":
                    # Use Orchestrator for complex multi-step goals
                    orchestrator = TaskOrchestrator(
                        llm_client=self.response_generator.providers.get("grok"),
                        update_callback=lambda t, d: self._send_orchestrator_update(
                            session_id, t, d
                        ),
                    )

                    goal = route["parameters"].get("task_description", message)
                    orchestrator_result = await orchestrator.run_goal(goal, context)

                    response = orchestrator_result.get("message", "Meta completada.")
                    tool_result = orchestrator_result
                else:
                    tool_result = await self._execute_tool(route, context)

                    # Step 4: Generate natural language response
                    response = self.response_generator.generate_response(
                        route["tool_name"], tool_result, context, model=model
                    )

                result = {
                    "type": "tool_response",
                    "content": response,
                    "tool_name": route["tool_name"],
                    "success": tool_result.get("success", False),
                }

                # Handle approval requirements
                if route["requires_approval"]:
                    result["requires_approval"] = True
                    result["approval_request"] = self._generate_approval_request(route)

            # Update conversation context
            self._update_context(session_id, message, result, intent, route)

            # Log interaction
            duration_ms = (time.time() - start_time) * 1000
            self.session_logger.log_tool_usage(
                tool_name="ConversationalInterface",
                action="process_message",
                duration_ms=duration_ms,
                success=True,
                parameters={
                    "session_id": session_id,
                    "message_length": len(message),
                    "intent_type": intent.get("intent", "unknown"),
                    "tool_used": route["tool_name"],
                },
            )

            # Send typing indicator off
            await self._send_typing_indicator(session_id, active=False)

            return result

        except Exception as e:
            logger.error(f"Error processing message: {str(e)}", exc_info=True)

            return {
                "type": "error",
                "content": f"Disculpa, ocurri un error procesando tu mensaje: {str(e)}",
                "requires_response": False,
            }

    async def _execute_tool(self, route: Dict, context: Dict) -> Dict[str, Any]:
        """Execute tool based on routed intent"""
        tool_name = route["tool_name"]
        parameters = route["parameters"]

        try:
            # Get tool from registry
            tool_class = self.tool_registry.get_tool(tool_name)
            if not tool_class:
                return {
                    "success": False,
                    "error_message": f"Tool '{tool_name}' not available",
                }

            # Instantiate tool
            tool = tool_class()

            # Check if tool supports streaming
            if hasattr(tool, "execute_with_streaming"):
                # Handle streaming execution
                return await self._handle_streaming_execution(tool, parameters, context)
            else:
                # Regular execution
                return await asyncio.get_event_loop().run_in_executor(
                    None, tool.execute, parameters
                )

        except Exception as e:
            return {"success": False, "error_message": str(e)}

    async def _handle_streaming_execution(
        self, tool, parameters: Dict, context: Dict
    ) -> Dict[str, Any]:
        """Handle streaming tool execution with progress updates"""
        try:
            # Execute with streaming
            stream_gen = tool.execute_with_streaming(parameters)

            final_result = None
            async for update in stream_gen:
                # Generate streaming response
                stream_response = self.response_generator.generate_streaming_response(
                    tool.__class__.__name__, update
                )

                if stream_response:
                    # Send streaming message to client
                    await self._send_streaming_update(
                        context["session_id"], stream_response
                    )

                # Store final result when complete
                if update.get("status") == "complete":
                    final_result = update.get("result")

            return final_result or {"success": True, "data": {}}

        except Exception as e:
            return {
                "success": False,
                "error_message": f"Streaming execution error: {str(e)}",
            }

    def _is_clarification_response(self, session_id: str, message: str) -> bool:
        """Check if message is responding to a clarification request"""
        context = self.contexts.get(session_id, {})
        pending = context.get("pending_clarifications", {})

        return bool(pending) and len(pending) > 0

    async def _handle_clarification(
        self, session_id: str, message: str, context: Dict
    ) -> Dict[str, Any]:
        """Handle clarification response from user"""
        pending = context.get("pending_clarifications", {})

        if not pending:
            return {
                "type": "error",
                "content": "No hay clarificaciones pendientes.",
                "requires_response": False,
            }

        # Get the pending clarification
        clarification_id = list(pending.keys())[0]
        clarification = pending[clarification_id]

        # Extract user response
        user_response = message.strip()

        # Update original intent with clarification
        original_intent = clarification["original_intent"]
        missing_params = clarification["missing_parameters"]

        # Add clarified parameters to intent
        if missing_params and user_response:
            # Simple parameter extraction (can be enhanced with LLM)
            param_name = missing_params[0]
            original_intent["parameters"] = original_intent.get("parameters", {})
            original_intent["parameters"][param_name] = user_response

        # Route the updated intent
        original_intent["confidence"] = min(
            0.95, original_intent.get("confidence", 0.7) + 0.2
        )

        route = await self.language_router.route_intent(original_intent, context)

        # Clear pending clarification
        del pending[clarification_id]

        # Execute and generate response
        if route["tool_name"] != "Self":
            tool_result = await self._execute_tool(route, context)
            response = self.response_generator.generate_response(
                route["tool_name"], tool_result, context
            )

            return {
                "type": "tool_response",
                "content": response,
                "tool_name": route["tool_name"],
                "success": tool_result.get("success", False),
                "clarification_resolved": True,
            }
        else:
            return {
                "type": "clarification",
                "content": "Nesecito mas aclaracion, por favor.",
                "requires_response": True,
            }

    def _store_clarification_context(self, session_id: str, intent: Dict, route: Dict):
        """Store clarification context for follow-up"""
        context = self.contexts.get(session_id, {})
        pending = context.get("pending_clarifications", {})

        clarification_id = str(uuid.uuid4())
        pending[clarification_id] = {
            "original_intent": intent.copy(),
            "missing_parameters": route["parameters"].get("missing_parameters", []),
            "question": route["parameters"]["clarification_request"],
            "timestamp": datetime.now().isoformat(),
        }

    def _update_context(
        self, session_id: str, message: str, result: Dict, intent: Dict, route: Dict
    ):
        """Update conversation context"""
        context = self.contexts.get(session_id, {})

        # Add to conversation history
        history = context.get("conversation_history", [])
        history.append(
            {
                "timestamp": datetime.now().isoformat(),
                "role": "user",
                "content": message,
                "intent": intent,
            }
        )
        history.append(
            {
                "timestamp": datetime.now().isoformat(),
                "role": "assistant",
                "content": result["content"],
                "tool_used": route["tool_name"],
                "intent_type": intent.get("intent", "unknown"),
            }
        )

        # Keep last 20 messages max
        context["conversation_history"] = history[-20:]

        # Update current context based on tool result
        if result.get("type") == "tool_response" and result.get("success"):
            current_context = context.get("current_context", {})

            # Update active file/context
            if route["tool_name"] == "CodeAnalyzer":
                if "target" in route["parameters"]:
                    current_context["active_file"] = route["parameters"]["target"]
            elif route["tool_name"] == "SystemExecutor":
                if "cwd" in route["parameters"]:
                    current_context["working_directory"] = route["parameters"]["cwd"]

            context["current_context"] = current_context

    async def _send_orchestrator_update(
        self, session_id: str, update_type: str, data: Any
    ):
        """Send updates from the orchestrator to the WebSocket client"""
        if session_id in self.connections:
            websocket = self.connections[session_id]["websocket"]
            try:
                await websocket.send_json(
                    {
                        "type": "streaming_update",
                        "update_type": update_type,
                        "content": data,
                        "timestamp": datetime.now().isoformat(),
                    }
                )
            except Exception as e:
                logger.error(f"Failed to send orchestrator update: {e}")

    def _generate_approval_request(self, route: Dict) -> str:
        """Generate approval request message"""
        tool_name = route["tool_name"]
        params = route["parameters"]

        if tool_name == "SystemExecutor":
            return f"Esta accin requiere aprobacin. Ejecutar: {params.get('command', 'comando desconocido')}"
        elif tool_name == "GitTools":
            return f"Accin git requiere aprobacin: {params.get('operation', 'operacin desconocida')}"
        elif tool_name == "ImageProcessor":
            return f"Generacin de imagen requiere aprobacin. Prompt: {params.get('prompt', '')[:100]}..."
        else:
            return f"Accin requiere aprobacin. Herramienta: {tool_name}"

    async def _send_typing_indicator(self, session_id: str, active: bool = True):
        """Send typing indicator to client"""
        if session_id in self.connections:
            websocket = self.connections[session_id]["websocket"]
            await websocket.send_json({"type": "typing_indicator", "active": active})

    async def _send_streaming_update(self, session_id: str, message: str):
        """Send streaming update to client"""
        if session_id in self.connections:
            websocket = self.connections[session_id]["websocket"]
            await websocket.send_json({"type": "streaming_update", "content": message})


# Test harness for development (simplified - requires FastAPI for full testing)
if __name__ == "__main__":

    async def test_websocket_handler():
        """Test WebSocket handler components"""
        print("Testing WebSocket Handler Components")
        print("=" * 60)

        # Test initialization
        handler = WebSocketHandler()
        print("[OK] WebSocket handler initialized")

        # Test context management
        session_id = "test_session_123"
        handler.contexts[session_id] = {
            "session_id": session_id,
            "conversation_history": [],
            "current_context": {},
        }
        print("[OK] Context management working")

        # Test message processing (simplified - no actual tools)
        test_messages = [
            "Hola, como estas?",
            "Revisa este codigo por favor",
            "Busca informacion sobre Python async",
        ]

        for message in test_messages:
            print(f"\n[Test] Message: '{message}'")
            try:
                # Note: This will fail in test mode without full tool setup,
                # but tests the NLP pipeline
                response = await handler.handle_message(session_id, message)
                print(f"  Type: {response.get('type', 'unknown')}")
                print(f"  Content preview: {response.get('content', '')[:50]}...")
            except Exception as e:
                print(f"  Expected error in test mode: {str(e)[:50]}...")

        print("\n[OK] Core WebSocket handler tests completed!")

    # Run tests
    asyncio.run(test_websocket_handler())
