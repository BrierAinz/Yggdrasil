"""
Robust Plan Executor - Integration of ExecutionEngine
"""

import logging
import threading
import time
from datetime import datetime

from src.core.execution_engine import ExecutionEngine, ExecutionStepResult
from src.core.planning import PlanStepStatus
from src.core.tool_registry import get_tool_registry

logger = logging.getLogger("RobustExecutor")


def execute_plan_robust(plan, server, stats):
    """
    Execute a plan with robustness features:
    - Retries
    - Timeouts
    - Progress tracking
    - Failure recovery
    """

    logger.info(f"Starting robust execution of plan: {plan.plan_id}")

    # Initialize execution engine
    execution_engine = ExecutionEngine(max_retries=2, default_timeout_seconds=30)

    server.send(EventStatusUpdate(payload={"state": "busy"}))
    server.send(
        EventChatDelta(
            payload={
                "delta": "\nðŸš€ **Ejecutando plan robusto** {plan.plan_id}\n\n",
                "type": "execution_start",
            }
        )
    )

    try:
        # Get tool instances from registry
        registry = get_tool_registry()

        # Track progress
        total_steps = len(plan.steps)
        completed_steps = 0
        failed_steps = 0

        for i, step in enumerate(plan.steps, 1):
            # Check dependencies
            deps_ready = all(
                dep_step.status == PlanStepStatus.COMPLETED
                for dep_step in plan.steps
                if dep_step.step_id in step.dependencies
            )

            if not deps_ready:
                step.status = PlanStepStatus.BLOCKED
                server.send(
                    EventChatDelta(
                        payload={
                            "delta": f"â¸ï¸ **Paso {i} bloqueado**: Esperando dependencias\n",
                            "type": "step_blocked",
                        }
                    )
                )
                continue

            # Execute step
            step.status = PlanStepStatus.IN_PROGRESS

            progress_percent = int((i - 1) / total_steps * 100)
            server.send(
                EventChatDelta(
                    payload={
                        "delta": f"\nâ–¶ï¸ **[{i}/{total_steps}] {step.title}** ({progress_percent}% complete)\n",
                        "type": "step_start",
                    }
                )
            )

            # Get tool for this step
            tool = registry.get_tool(step.tool) if step.tool else None

            if not tool:
                step.status = PlanStepStatus.FAILED
                step.error = f"Tool {step.tool} not available"
                failed_steps += 1
                server.send(
                    EventChatDelta(
                        payload={
                            "delta": f"   [FAIL] Tool no disponible: {step.tool}\n",
                            "type": "step_failed",
                        }
                    )
                )
                continue

            # Execute with robust engine
            def progress_callback(msg):
                server.send(
                    EventChatDelta(
                        payload={"delta": f"   â†³ {msg}\n", "type": "step_progress"}
                    )
                )

            try:
                result = execution_engine.execute_step(step, tool, progress_callback)

                if result.success:
                    step.status = PlanStepStatus.COMPLETED
                    step.result = {"output": result.output}
                    completed_steps += 1

                    server.send(
                        EventChatDelta(
                            payload={
                                "delta": f"   [OK] Completado (took {result.duration_seconds:.1f}s, {result.attempts} attempt(s))\n",
                                "type": "step_complete",
                            }
                        )
                    )
                else:
                    step.status = PlanStepStatus.FAILED
                    step.error = result.error
                    failed_steps += 1

                    server.send(
                        EventChatDelta(
                            payload={
                                "delta": f"   [FAIL] {result.error[:100]}\n",
                                "type": "step_failed",
                            }
                        )
                    )

            except Exception as e:
                logger.error(f"Step {step.step_id} execution error: {e}")
                step.status = PlanStepStatus.FAILED
                step.error = f"Execution error: {str(e)}"
                failed_steps += 1

                server.send(
                    EventChatDelta(
                        payload={
                            "delta": f"   [ERROR] {str(e)[:100]}\n",
                            "type": "step_error",
                        }
                    )
                )

            time.sleep(0.5)  # Small delay between steps

        # Final summary
        server.send(
            EventChatDelta(
                payload={
                    "delta": f"\nðŸ“Š **EjecuciÃ³n completada** {completed_steps}/{total_steps} pasos\n",
                    "type": "execution_summary",
                }
            )
        )

        if failed_steps > 0:
            server.send(
                EventChatDelta(
                    payload={
                        "delta": f"[INFO] {failed_steps} pasos fallidos (revisar logs)\n",
                        "type": "summary_failed",
                    }
                )
            )

        # Send final
        server.send(
            EventChatFinal(
                payload={
                    "text": "",
                    "plan_id": plan.plan_id,
                    "execution_completed": True,
                    "success_rate": f"{completed_steps}/{total_steps}",
                }
            )
        )

        # Log stats
        stats = execution_engine.get_progress()
        logger.info(f"Plan execution complete: {stats}")

    except Exception as e:
        logger.error(f"Plan execution error: {e}", exc_info=True)
        server.send(
            EventChatFinal(
                payload={
                    "text": f"Error durante ejecuciÃ³n robusta: {str(e)}",
                    "plan_id": plan.plan_id,
                    "execution_failed": True,
                }
            )
        )

    server.send(EventStatusUpdate(payload={"state": "idle"}))
