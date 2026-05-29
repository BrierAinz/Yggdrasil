"""
AutonomousToolBase - Base class for autonomous tools with trust scoring
Provides automatic execution decision and safety features
"""
import logging
from abc import ABC, abstractmethod
from typing import Any, Dict, Optional

from src.core.trust_score_engine import (
    ExecutionMode,
    TrustScoreEngine,
    get_trust_engine,
)

logger = logging.getLogger(__name__)


class AutonomousToolBase(ABC):
    """
    Base class for autonomous tools with integrated trust scoring.

    Features:
    - Automatic execution mode decision (AUTO/CONFIRM/BLOCK)
    - Operation preview for confirmation mode
    - Success/failure tracking for learning
    - Consistent error handling
    """

    def __init__(self, tool_name: str):
        self.tool_name = tool_name
        self.trust_engine: Optional[TrustScoreEngine] = None
        self._initialized = False

    def _ensure_trust_engine(self):
        """Lazy initialization of trust engine"""
        if self.trust_engine is None:
            self.trust_engine = get_trust_engine("default")
        self._initialized = True

    async def execute_with_trust(
        self,
        action: str,
        parameters: Dict[str, Any],
        context: Optional[Dict[str, Any]] = None,
        force_mode: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Execute operation with trust scoring evaluation.

        Args:
            action: The action to perform
            parameters: Operation parameters
            context: Additional context
            force_mode: Override trust decision ('auto', 'confirm', 'block')

        Returns:
            Operation result or trust evaluation result
        """
        self._ensure_trust_engine()
        context = context or {}

        # Evaluate trust score
        trust_result = self.trust_engine.evaluate_operation(
            tool_name=self.tool_name,
            action=action,
            parameters=parameters,
            context=context,
        )

        # Check for force mode override
        if force_mode:
            if force_mode == "auto":
                trust_result.execution_mode = ExecutionMode.AUTO
            elif force_mode == "confirm":
                trust_result.execution_mode = ExecutionMode.CONFIRM
            elif force_mode == "block":
                trust_result.execution_mode = ExecutionMode.BLOCK

        # Handle based on execution mode
        if trust_result.execution_mode == ExecutionMode.BLOCK:
            return {
                "success": False,
                "error": "Operation blocked due to high risk",
                "trust_score": trust_result.score,
                "reasons": trust_result.reasons,
                "alternatives": trust_result.alternatives,
                "requires_confirmation": True,
                "confirmation_prompt": self._generate_confirmation_prompt(
                    action, parameters, trust_result
                ),
            }

        elif trust_result.execution_mode == ExecutionMode.CONFIRM:
            return {
                "success": None,  # Not executed yet
                "pending_confirmation": True,
                "trust_score": trust_result.score,
                "preview": trust_result.preview,
                "reasons": trust_result.reasons,
                "alternatives": trust_result.alternatives,
                "confirmation_prompt": self._generate_confirmation_prompt(
                    action, parameters, trust_result
                ),
                # Include callback info for confirmation
                "tool_name": self.tool_name,
                "action": action,
                "parameters": parameters,
                "context": context,
            }

        # AUTO mode - execute directly
        try:
            result = await self._do_execute(action, parameters)

            # Record success
            self.trust_engine.record_operation(
                tool_name=self.tool_name,
                action=action,
                success=result.get("success", False),
                execution_mode=ExecutionMode.AUTO,
                user_confirmed=None,
            )

            # Add trust info to result
            result["_trust_info"] = {
                "score": trust_result.score,
                "mode": "auto",
                "confidence": trust_result.confidence,
            }

            return result

        except Exception as e:
            logger.error(f"Operation failed: {e}")

            # Record failure
            self.trust_engine.record_operation(
                tool_name=self.tool_name,
                action=action,
                success=False,
                execution_mode=ExecutionMode.AUTO,
                user_confirmed=None,
            )

            return {
                "success": False,
                "error": str(e),
                "trust_score": trust_result.score,
                "_trust_info": {
                    "score": trust_result.score,
                    "mode": "auto",
                    "failed": True,
                },
            }

    async def confirm_and_execute(
        self,
        action: str,
        parameters: Dict[str, Any],
        context: Optional[Dict[str, Any]] = None,
        user_confirmed: bool = True,
    ) -> Dict[str, Any]:
        """
        Execute after user confirmation.

        Args:
            action: The action to perform
            parameters: Operation parameters
            context: Additional context
            user_confirmed: Whether user confirmed execution

        Returns:
            Operation result
        """
        self._ensure_trust_engine()

        if not user_confirmed:
            return {
                "success": False,
                "error": "Operation cancelled by user",
                "cancelled": True,
            }

        try:
            result = await self._do_execute(action, parameters)

            # Record result
            self.trust_engine.record_operation(
                tool_name=self.tool_name,
                action=action,
                success=result.get("success", False),
                execution_mode=ExecutionMode.CONFIRM,
                user_confirmed=True,
            )

            return result

        except Exception as e:
            logger.error(f"Confirmed operation failed: {e}")

            self.trust_engine.record_operation(
                tool_name=self.tool_name,
                action=action,
                success=False,
                execution_mode=ExecutionMode.CONFIRM,
                user_confirmed=True,
            )

            return {"success": False, "error": str(e)}

    @abstractmethod
    async def _do_execute(
        self, action: str, parameters: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Actual tool execution logic. Must be implemented by subclasses.

        Args:
            action: Action to perform
            parameters: Operation parameters

        Returns:
            Operation result dict
        """
        pass

    def _generate_confirmation_prompt(
        self, action: str, parameters: Dict[str, Any], trust_result
    ) -> str:
        """Generate human-readable confirmation prompt"""
        lines = [
            f"[CONFIRMACION REQUERIDA]",
            f"",
            f"Operacion: {self.tool_name}.{action}",
            f"Nivel de confianza: {trust_result.score:.0%}",
            f"",
            f"Razones:",
        ]

        for reason in trust_result.reasons[:3]:
            lines.append(f"  - {reason}")

        if trust_result.preview:
            lines.extend(
                [
                    f"",
                    f"Vista previa:",
                    f"  Duracion estimada: {trust_result.preview.get('estimated_duration', 'unknown')}",
                ]
            )

            if trust_result.preview.get("can_undo"):
                lines.append(f"  Se puede deshacer: Si")

            if trust_result.preview.get("backup_created"):
                lines.append(f"  Backup: Se creara automaticamente")

        if trust_result.alternatives:
            lines.extend([f"", f"Alternativas:"])
            for alt in trust_result.alternatives[:2]:
                lines.append(f"  - {alt}")

        lines.extend([f"", f"Confirmar ejecucion? (si/no)"])

        return "\n".join(lines)


class SimpleAutonomousTool(AutonomousToolBase):
    """
    Simple autonomous tool wrapper for existing tools.
    Wraps a tool instance and adds trust scoring.
    """

    def __init__(self, tool_name: str, tool_instance):
        super().__init__(tool_name)
        self.tool_instance = tool_instance

    async def _do_execute(
        self, action: str, parameters: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Delegate to wrapped tool"""
        if hasattr(self.tool_instance, "execute"):
            return await self.tool_instance.execute(action, **parameters)
        else:
            raise NotImplementedError(f"Tool {self.tool_name} has no execute method")
