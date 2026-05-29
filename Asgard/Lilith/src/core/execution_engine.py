"""
Lilith Execution Engine v1.0
Robust plan execution with retries, timeouts, and error recovery
"""

import logging
import threading
import time
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Callable, Dict, Optional

logger = logging.getLogger("ExecutionEngine")


@dataclass
class ExecutionStepResult:
    step_id: str
    success: bool
    output: Optional[str] = None
    error: Optional[str] = None
    duration_seconds: float = 0.0
    attempts: int = 1
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None


@dataclass
class ExecutionStatistics:
    total_steps: int = 0
    successful_steps: int = 0
    failed_steps: int = 0
    total_duration: float = 0.0
    retry_count: int = 0


class ExecutionEngine:
    """
    Executes plans with robustness features:
    - Retry logic
    - Per-step timeouts
    - Progress tracking
    - Detailed logging
    """

    def __init__(
        self,
        max_retries: int = 2,
        default_timeout_seconds: int = 30,
        max_timeout_seconds: int = 300,
    ):
        self.max_retries = max_retries
        self.default_timeout = default_timeout_seconds
        self.max_timeout = max_timeout_seconds
        self.stats = ExecutionStatistics()
        logger.info(f"ExecutionEngine initialized (max_retries={max_retries})")

    def execute_step(
        self,
        step: Any,  # PlanStep
        tool_instance: Any,
        on_progress: Optional[Callable] = None,
    ) -> ExecutionStepResult:
        """Execute a single step with retry logic"""

        start_time = datetime.now()
        last_error = None
        output = None
        success = False
        attempts_made = 0

        for attempt in range(1, self.max_retries + 1):
            try:
                if on_progress:
                    on_progress(
                        f"Attempt {attempt}/{self.max_retries} for step {step.step_id}"
                    )

                # Execute with timeout
                output = self._execute_with_timeout(
                    tool_instance, step, timeout=self.default_timeout
                )
                success = True
                attempts_made = attempt

                if attempt > 1:
                    self.stats.retry_count += 1
                    logger.info(f"Step {step.step_id} succeeded on attempt {attempt}")

                break  # Success, exit retry loop

            except Exception as e:
                last_error = e
                attempts_made = attempt
                logger.warning(f"Attempt {attempt} failed for step {step.step_id}: {e}")

                if attempt < self.max_retries:
                    # Exponential backoff
                    backoff_time = 2 ** (attempt - 1)
                    logger.info(f"Retrying in {backoff_time}s...")
                    time.sleep(backoff_time)
                    # Continue to next attempt
                else:
                    # All retries exhausted - will handle after loop
                    logger.error(
                        f"Step {step.step_id} failed after {self.max_retries} attempts"
                    )

        end_time = datetime.now()
        duration = (end_time - start_time).total_seconds()

        # Build result object
        self.stats.total_steps += 1
        if success:
            self.stats.successful_steps += 1
            self.stats.total_duration += duration
            return ExecutionStepResult(
                step_id=step.step_id,
                success=True,
                output=output,
                duration_seconds=duration,
                attempts=attempts_made,
                start_time=start_time,
                end_time=end_time,
            )
        else:
            self.stats.failed_steps += 1
            self.stats.total_duration += duration
            return ExecutionStepResult(
                step_id=step.step_id,
                success=False,
                error=f"Failed after {attempts_made} attempts: {str(last_error)}",
                duration_seconds=duration,
                attempts=attempts_made,
                start_time=start_time,
                end_time=end_time,
            )

    def _execute_with_timeout(self, tool_instance: Any, step: Any, timeout: int) -> str:
        """Execute step with timeout protection"""

        output = None
        error = None

        def target():
            nonlocal output, error
            try:
                if hasattr(tool_instance, "execute"):
                    output = tool_instance.execute(step.parameters.get("command", ""))
                else:
                    output = tool_instance.run(**step.parameters)
            except Exception as e:
                error = e

        thread = threading.Thread(target=target)
        thread.start()
        thread.join(timeout)

        if thread.is_alive():
            # Timeout occurred
            raise TimeoutError(f"Step execution exceeded {timeout} seconds timeout")

        if error:
            raise error

        return output or ""

    def get_progress(self) -> Dict[str, Any]:
        """Return execution progress statistics"""
        return {
            "total_steps": self.stats.total_steps,
            "successful_steps": self.stats.successful_steps,
            "failed_steps": self.stats.failed_steps,
            "completion_rate": self.stats.successful_steps
            / max(self.stats.total_steps, 1),
            "total_duration_seconds": self.stats.total_duration,
            "retry_count": self.stats.retry_count,
        }


# Implementation note: Full integration with main.py pending
# This provides the foundation for robust execution
