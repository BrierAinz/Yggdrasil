"""
AutoExecutor: Motor de ejecución autónoma para tareas en AutoMode.
Integra checkpointing, auto-delegación y reportes.
"""
import asyncio
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional

from src.core.automode.checkpoint_manager import CheckpointManager
from src.core.automode.delegation_detector import DelegationDetector, TaskComplexity
from src.core.automode.progress_reporter import ProgressReporter


class AutoExecutor:
    """
    Ejecutor autónomo de tareas en AutoMode.

    Flujo:
    1. Carga/recupera checkpoint
    2. Para cada paso:
       - Verifica límites de seguridad
       - Decide auto-delegación
       - Ejecuta paso
       - Guarda checkpoint cada N pasos
       - Reporta progreso
    3. Mueve tarea a completed/failed

    Características:
    - Auto-delegación inteligente
    - Checkpointing periódico
    - Reportes automáticos
    - Límites de seguridad configurables
    - Recuperación ante fallos
    """

    def __init__(self, task_id: str, config: Dict[str, Any]):
        """
        Args:
            task_id: ID único de la tarea
            config: Configuración de la tarea
        """
        self.task_id = task_id
        self.config = config

        # Componentes
        self.delegator = DelegationDetector()
        self.checkpoint_mgr = CheckpointManager(task_id)
        self.reporter = ProgressReporter(task_id, config)

        # Estado
        self.completed_steps: List[Dict] = []
        self.current_step = 0
        self.plan: List[Dict] = []
        self.is_running = False
        self.is_paused = False

        # Configuración
        self.checkpoint_interval = config.get("settings", {}).get(
            "checkpoint_interval_steps", 5
        )
        self.report_interval_hours = config.get("settings", {}).get(
            "report_interval_hours", 4
        )
        self.max_retries = config.get("settings", {}).get("max_retries_per_step", 3)
        self.timeout_minutes = config.get("settings", {}).get(
            "timeout_per_step_minutes", 30
        )
        self.security_limits = config.get("security_limits", {})

        # Tracking
        self.last_report_time = datetime.now()
        self.start_time = None

    async def execute_task(
        self, objective: str, plan_steps: List[Dict], context: Optional[Dict] = None
    ):
        """
        Ejecuta tarea completa en modo autónomo.

        Args:
            objective: Descripción del objetivo
            plan_steps: Lista de pasos a ejecutar
            context: Contexto adicional
        """
        context = context or {}
        self.start_time = datetime.now()
        self.is_running = True

        print(f"\n{'='*60}")
        print(f"[AutoMode] Starting task: {self.task_id}")
        print(f"[AutoMode] Objective: {objective}")
        print(f"{'='*60}\n")

        # Verificar si hay checkpoint previo
        checkpoint = self.checkpoint_mgr.load_latest_checkpoint()
        if checkpoint:
            print(
                f"[AutoMode] Resuming from checkpoint (step {checkpoint.step_number})"
            )
            self.completed_steps = checkpoint.completed_steps
            self.current_step = checkpoint.step_number
            self.plan = checkpoint.plan_state
        else:
            # Plan inicial
            self.plan = plan_steps
            print(f"[AutoMode] Fresh start with {len(plan_steps)} steps")

        # Notificar inicio
        await self.reporter.send_start_notification(objective, len(self.plan))

        # Ejecutar pasos
        total_steps = len(self.plan)

        try:
            for i, step in enumerate(
                self.plan[self.current_step :], start=self.current_step
            ):
                if not self.is_running:
                    print("[AutoMode] Execution stopped by user")
                    break

                while self.is_paused:
                    await asyncio.sleep(1)

                step_num = i + 1
                self.current_step = step_num

                print(
                    f"\n[AutoMode] Step {step_num}/{total_steps}: {step.get('tool', 'unknown')}"
                )

                # Verificar límites de seguridad
                if not self._check_security_limits(step):
                    print(f"[AutoMode] Step {step_num} blocked by security limits")
                    await self.reporter.request_approval(step, "límites de seguridad")
                    # Esperar aprobación (en implementación real, esto bloquearía)
                    continue

                # Auto-delegación
                delegation = self.delegator.analyze_task(
                    step.get("description", step.get("tool", "")),
                    step.get("params", {}),
                )

                if delegation.should_delegate:
                    print(
                        f"[AutoMode] Auto-delegating to {delegation.recommended_agent}"
                    )
                    await self.reporter.send_delegation_notice(
                        step_num, delegation.recommended_agent, delegation.reasoning
                    )
                    step["tool"] = f"delegate_{delegation.recommended_agent}"
                    step["delegation_reason"] = delegation.reasoning

                # Ejecutar paso con retries
                result = await self._execute_step_with_retry(step, context, step_num)

                if result is None:
                    print(f"[AutoMode] Step {step_num} failed after retries")
                    await self._handle_step_failure(step_num, "Max retries exceeded")
                    raise Exception(f"Step {step_num} failed")

                # Registrar éxito
                self.completed_steps.append(
                    {
                        "step": step_num,
                        "tool": step.get("tool"),
                        "result": result,
                        "timestamp": datetime.now().isoformat(),
                        "delegated": delegation.should_delegate
                        if "delegation" in locals()
                        else False,
                    }
                )

                # Guardar artifacts si los hay
                if isinstance(result, dict) and "output" in result:
                    self.checkpoint_mgr.save_artifact(
                        f"step_{step_num}_output.txt", str(result["output"])
                    )

                # Checkpoint cada N pasos
                if step_num % self.checkpoint_interval == 0:
                    self.checkpoint_mgr.save_checkpoint(
                        step_num, self.plan, self.completed_steps, context
                    )
                    await self.reporter.send_checkpoint_notification(step_num)

                # Reporte de progreso
                await self._check_and_send_progress_report(step_num, total_steps)

        except Exception as e:
            print(f"[AutoMode] Task failed: {e}")
            await self._handle_task_failure(str(e))
            raise

        # Completar
        if self.is_running:
            await self._complete_task()

    async def _execute_step_with_retry(
        self, step: Dict, context: Dict, step_num: int
    ) -> Optional[Any]:
        """Ejecuta un paso con reintentos."""
        for attempt in range(self.max_retries):
            try:
                # Ejecutar paso (simulado - en realidad llamaría al executor real)
                result = await self._execute_single_step(step, context)
                return result

            except Exception as e:
                print(f"[AutoMode] Step {step_num} attempt {attempt + 1} failed: {e}")
                if attempt < self.max_retries - 1:
                    await asyncio.sleep(2**attempt)  # Exponential backoff
                else:
                    return None

        return None

    async def _execute_single_step(self, step: Dict, context: Dict) -> Any:
        """
        Ejecuta un paso individual.
        En implementación real, esto llamaría al PlanExecutor.
        """
        tool = step.get("tool")
        params = step.get("params", {})

        # Simulación de ejecución
        await asyncio.sleep(0.1)  # Simular trabajo

        return {
            "tool": tool,
            "params": params,
            "output": f"Executed {tool}",
            "success": True,
        }

    def _check_security_limits(self, step: Dict) -> bool:
        """
        Verifica que el paso no viole límites de seguridad.
        """
        limits = self.security_limits

        # Forbidden paths
        if "params" in step:
            params = step["params"]

            # Verificar paths
            if "path" in params:
                path = params["path"]
                for forbidden in limits.get("forbidden_paths", []):
                    if forbidden in path:
                        print(f"[Security] Forbidden path detected: {forbidden}")
                        return False

            # Verificar file_path
            if "file_path" in params:
                path = params["file_path"]
                for forbidden in limits.get("forbidden_paths", []):
                    if forbidden in path:
                        print(f"[Security] Forbidden path detected: {forbidden}")
                        return False

        # Forbidden operations
        tool = step.get("tool", "")
        for forbidden in limits.get("forbidden_operations", []):
            if forbidden in tool:
                print(f"[Security] Forbidden operation: {forbidden}")
                return False

        # Require approval
        if tool in limits.get("require_approval", []):
            print(f"[Security] Operation requires approval: {tool}")
            return False

        return True

    async def _check_and_send_progress_report(self, current: int, total: int):
        """Verifica si es momento de enviar reporte de progreso."""
        now = datetime.now()
        time_since_report = now - self.last_report_time

        # Reporte por tiempo
        if time_since_report > timedelta(hours=self.report_interval_hours):
            pct = (current / total) * 100
            await self.reporter.send_progress_report(current, total, pct)
            self.last_report_time = now
            return

        # Reporte por milestones (25%, 50%, 75%, 100%)
        pct = (current / total) * 100
        milestones = [25, 50, 75, 100]

        for milestone in milestones:
            if abs(pct - milestone) < 1:  # Dentro de 1%
                await self.reporter.send_progress_report(current, total, pct)
                self.last_report_time = now
                return

    async def _handle_step_failure(self, step_num: int, error: str):
        """Maneja fallo de un paso."""
        await self.reporter.report_error(step_num, error, is_recoverable=True)

    async def _handle_task_failure(self, error: str):
        """Maneja fallo de la tarea completa."""
        await self.reporter.report_error(self.current_step, error, is_recoverable=False)

        # Mover a failed
        error_report = f"""# Error Report - {self.task_id}

**Time:** {datetime.now().isoformat()}
**Failed at step:** {self.current_step}
**Error:** {error}

**Completed steps:** {len(self.completed_steps)}
"""
        self.checkpoint_mgr.move_to_failed(error_report)

    async def _complete_task(self):
        """Finaliza tarea exitosamente."""
        duration = datetime.now() - self.start_time

        print(f"\n{'='*60}")
        print(f"[AutoMode] Task completed: {self.task_id}")
        print(f"[AutoMode] Duration: {duration}")
        print(f"{'='*60}\n")

        # Reporte final
        artifacts = self.checkpoint_mgr._list_artifacts()
        await self.reporter.send_final_report(self.completed_steps, artifacts)

        # Mover a completed
        final_report = f"""# Task Report - {self.task_id}

**Completed:** {datetime.now().isoformat()}
**Duration:** {duration}
**Total steps:** {len(self.completed_steps)}

## Steps executed:
"""
        for step in self.completed_steps:
            final_report += f"- Step {step['step']}: {step['tool']}\n"

        self.checkpoint_mgr.move_to_completed(final_report)

    def stop(self):
        """Detiene ejecución."""
        self.is_running = False
        print(f"[AutoMode] Stop requested for {self.task_id}")

    def pause(self):
        """Pausa ejecución."""
        self.is_paused = True
        print(f"[AutoMode] Paused: {self.task_id}")

    def resume(self):
        """Reanuda ejecución."""
        self.is_paused = False
        print(f"[AutoMode] Resumed: {self.task_id}")

    def get_status(self) -> Dict:
        """Retorna estado actual."""
        return {
            "task_id": self.task_id,
            "is_running": self.is_running,
            "is_paused": self.is_paused,
            "current_step": self.current_step,
            "total_steps": len(self.plan),
            "completed_steps": len(self.completed_steps),
            "progress_pct": (self.current_step / len(self.plan) * 100)
            if self.plan
            else 0,
        }
