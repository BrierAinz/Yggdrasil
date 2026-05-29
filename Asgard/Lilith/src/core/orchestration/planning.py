"""
Lilith Task Orchestrator v1.0
Manages autonomous execution loops: Plan -> Execute -> Observe -> Refine
"""

import asyncio
import logging
import time
from typing import Any, Callable, Dict, List, Optional

from src.core.execution_engine import ExecutionEngine, ExecutionStepResult
from src.core.planning.planning_engine import (
    ExecutionPlan,
    PlanningEngine,
    PlanStep,
    PlanStepStatus,
)
from src.core.tool_registry import ToolRegistry, get_tool_registry

logger = logging.getLogger("TaskOrchestrator")


class TaskOrchestrator:
    """
    Orchestrates complex tasks by running agentic loops.
    Handles planning, autonomous execution, observation, and self-correction.
    """

    def __init__(
        self, llm_client, update_callback: Optional[Callable] = None, max_loops: int = 5
    ):
        """
        Args:
            llm_client: LLM client for planning and observation
            update_callback: Function to send real-time updates to UI
            max_loops: Maximum number of re-planning loops allowed
        """
        self.planning_engine = PlanningEngine(llm_client)
        self.execution_engine = ExecutionEngine(max_retries=2)
        self.tool_registry = get_tool_registry()
        self.update_callback = update_callback
        self.max_loops = max_loops
        self.current_plan: Optional[ExecutionPlan] = None

        # Ensure registry is initialized
        if not self.tool_registry._initialized:
            self.tool_registry.initialize()

        logger.info("TaskOrchestrator initialized")

    async def run_goal(
        self, goal: str, context: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """
        Run a high-level goal through the orchestrator loop
        """
        logger.info(f"Starting goal orchestration: {goal}")

        # 1. Initial Plan
        await self._send_update("status", f"Planificando meta: {goal}")

        # Run planning in thread to avoid blocking loop
        self.current_plan = await asyncio.to_thread(
            self.planning_engine.generate_plan, goal, context
        )

        if not self.current_plan or not self.current_plan.steps:
            return {"success": False, "error": "No se pudo generar un plan vÃ¡lido."}

        await self._send_update("plan", self.current_plan.model_dump())

        loop_count = 0
        execution_results = []

        while loop_count < self.max_loops:
            loop_count += 1
            logger.info(f"Orchestration loop {loop_count}/{self.max_loops}")

            # 2. Execute pending steps
            ready_steps = self.current_plan.get_ready_steps()
            if not ready_steps:
                # All steps completed or blocked
                if all(
                    s.status == PlanStepStatus.COMPLETED
                    for s in self.current_plan.steps
                ):
                    logger.info("Goal achieved! All steps completed.")
                    break
                else:
                    return {
                        "success": False,
                        "error": "El plan estÃ¡ bloqueado o fallÃ³.",
                        "plan": self.current_plan.model_dump(),
                    }

            for step in ready_steps:
                # 3. Execution
                step_result = await self._execute_step(step)
                execution_results.append(step_result)

                # 4. Observation & Adaptation
                if not step_result.success:
                    logger.warning(
                        f"Step {step.step_id} failed. Analyzing for auto-healing..."
                    )
                    await self._send_update(
                        "status",
                        f"Paso fallido: {step.title}. Analizando soluciÃ³n con AutoHealer...",
                    )

                    # Use AutoHealer to diagnose
                    healer = self.tool_registry.get_tool("AutoHealer")
                    healing_suggestion = healer.analyze_error(
                        step_result.error, context=step.description
                    )

                    # Inform UI about diagnosis
                    await self._send_update("healing_diagnosis", healing_suggestion)

                    # Try to reformulate plan with healing context
                    new_plan = self.planning_engine.generate_plan(
                        goal,
                        context={
                            "previous_failed_step": step.model_dump(),
                            "healing_suggestion": healing_suggestion,
                            "execution_history": [
                                r.__dict__ for r in execution_results
                            ],
                            "current_plan": self.current_plan.model_dump(),
                        },
                    )

                    if new_plan and len(new_plan.steps) > 0:
                        logger.info("Plan reformulated successfully.")
                        self.current_plan = new_plan
                        await self._send_update(
                            "plan_update", self.current_plan.model_dump()
                        )
                        # Restart loop with new plan
                        break
                    else:
                        return {
                            "success": False,
                            "error": f"Fallo crÃ­tico en {step.title}: {step_result.error}",
                        }

            # Check if we should continue or we've finished
            if all(
                s.status == PlanStepStatus.COMPLETED for s in self.current_plan.steps
            ):
                break

        return {
            "success": True,
            "message": "Meta completada exitosamente.",
            "results": [r.__dict__ for r in execution_results],
            "loop_count": loop_count,
        }

    async def _execute_step(self, step: PlanStep) -> ExecutionStepResult:
        """Execute a single step and update UI"""
        await self._send_update(
            "step_start", {"step_id": step.step_id, "title": step.title}
        )

        tool = self.tool_registry.get_tool(step.tool)
        if not tool:
            result = ExecutionStepResult(
                step_id=step.step_id,
                success=False,
                error=f"Herramienta {step.tool} no encontrada.",
            )
        else:
            # Use execution engine for robust run
            loop = asyncio.get_running_loop()

            def progress(msg):
                asyncio.run_coroutine_threadsafe(
                    self._send_update(
                        "step_progress", {"step_id": step.step_id, "message": msg}
                    ),
                    loop,
                )

            # Note: execute_step is synchronous in current implementation
            result = await asyncio.to_thread(
                self.execution_engine.execute_step, step, tool, progress
            )

        # Update step status in current plan
        if self.current_plan:
            plan_step = self.current_plan.get_step(step.step_id)
            if plan_step:
                plan_step.status = (
                    PlanStepStatus.COMPLETED
                    if result.success
                    else PlanStepStatus.FAILED
                )
                plan_step.result = {"output": result.output} if result.success else None
                plan_step.error = result.error if not result.success else None

        await self._send_update(
            "step_end",
            {
                "step_id": step.step_id,
                "success": result.success,
                "output": result.output if result.success else result.error,
            },
        )

        return result

    async def _send_update(self, update_type: str, data: Any):
        """Send progress update to UI via callback"""
        if self.update_callback:
            if asyncio.iscoroutinefunction(self.update_callback):
                await self.update_callback(update_type, data)
            else:
                self.update_callback(update_type, data)
