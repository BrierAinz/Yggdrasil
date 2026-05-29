"""
Function Executor - Ejecutor de funciones

v5.0: Ejecuta funciones registradas con manejo de errores, timeouts y logging.
"""
import asyncio
import io
import logging
import time
import traceback
from contextlib import redirect_stderr, redirect_stdout
from typing import Any, Callable, Dict, Optional

from .registry import FunctionRegistry, get_function_registry
from .schemas import ToolResponse

logger = logging.getLogger("lilith.functions.executor")


class FunctionExecutor:
    """
    Ejecutor de funciones con manejo seguro.

    Features:
    - Validación de argumentos antes de ejecución
    - Manejo de errores y excepciones
    - Captura de logs/output
    - Timeouts configurables
    - Tracking de métricas
    """

    def __init__(
        self,
        registry: Optional[FunctionRegistry] = None,
        default_timeout: float = 30.0,
        capture_output: bool = True,
    ):
        self.registry = registry or get_function_registry()
        self.default_timeout = default_timeout
        self.capture_output = capture_output
        self._execution_count = 0
        self._error_count = 0

    async def execute(
        self,
        function_name: str,
        arguments: Dict[str, Any],
        timeout: Optional[float] = None,
        context: Optional[Dict[str, Any]] = None,
    ) -> ToolResponse:
        """
        Ejecuta una función con los argumentos proporcionados.

        Args:
            function_name: Nombre de la función
            arguments: Argumentos para la función
            timeout: Timeout en segundos
            context: Contexto adicional (session_id, etc.)

        Returns:
            ToolResponse con resultado o error
        """
        start_time = time.time()
        self._execution_count += 1

        # Validar que la función existe
        handler = self.registry.get_handler(function_name)
        if not handler:
            return ToolResponse.error_response(
                error=f"Función '{function_name}' no encontrada",
                tool_name=function_name,
                execution_time_ms=(time.time() - start_time) * 1000,
            )

        # Validar argumentos
        valid, error_msg = self.registry.validate_arguments(function_name, arguments)
        if not valid:
            self._error_count += 1
            return ToolResponse.error_response(
                error=f"Validación fallida: {error_msg}",
                tool_name=function_name,
                execution_time_ms=(time.time() - start_time) * 1000,
            )

        # Ejecutar con manejo de errores
        try:
            # Configurar timeout
            timeout_seconds = timeout or self.default_timeout

            # Capturar output si está habilitado
            if self.capture_output:
                stdout_capture = io.StringIO()
                stderr_capture = io.StringIO()

                with redirect_stdout(stdout_capture), redirect_stderr(stderr_capture):
                    result = await self._execute_with_timeout(
                        handler, arguments, timeout_seconds
                    )

                logs = []
                stdout_content = stdout_capture.getvalue()
                stderr_content = stderr_capture.getvalue()

                if stdout_content:
                    logs.extend(
                        [
                            f"[stdout] {line}"
                            for line in stdout_content.strip().split("\n")
                            if line
                        ]
                    )
                if stderr_content:
                    logs.extend(
                        [
                            f"[stderr] {line}"
                            for line in stderr_content.strip().split("\n")
                            if line
                        ]
                    )
            else:
                result = await self._execute_with_timeout(
                    handler, arguments, timeout_seconds
                )
                logs = []

            execution_time_ms = (time.time() - start_time) * 1000

            return ToolResponse.success_response(
                result=result,
                tool_name=function_name,
                execution_time_ms=execution_time_ms,
                logs=logs,
                arguments=arguments,
                context=context or {},
            )

        except asyncio.TimeoutError:
            self._error_count += 1
            execution_time_ms = (time.time() - start_time) * 1000
            return ToolResponse.error_response(
                error=f"Timeout después de {timeout_seconds}s",
                tool_name=function_name,
                execution_time_ms=execution_time_ms,
            )

        except Exception as e:
            self._error_count += 1
            execution_time_ms = (time.time() - start_time) * 1000
            error_trace = traceback.format_exc()
            logger.error(f"Error ejecutando {function_name}: {e}\n{error_trace}")

            return ToolResponse.error_response(
                error=f"{type(e).__name__}: {str(e)}",
                tool_name=function_name,
                execution_time_ms=execution_time_ms,
            )

    async def _execute_with_timeout(
        self, handler: Callable, arguments: Dict[str, Any], timeout: float
    ) -> Any:
        """Ejecuta handler con timeout."""
        # Determinar si es función async o sync
        if asyncio.iscoroutinefunction(handler):
            return await asyncio.wait_for(handler(**arguments), timeout=timeout)
        else:
            # Para funciones sync, ejecutar en thread pool
            loop = asyncio.get_event_loop()
            return await asyncio.wait_for(
                loop.run_in_executor(None, lambda: handler(**arguments)),
                timeout=timeout,
            )

    async def execute_batch(
        self,
        calls: list[tuple[str, Dict[str, Any]]],
        context: Optional[Dict[str, Any]] = None,
    ) -> list[ToolResponse]:
        """
        Ejecuta múltiples funciones en paralelo.

        Args:
            calls: Lista de (function_name, arguments)
            context: Contexto compartido

        Returns:
            Lista de respuestas
        """
        tasks = [self.execute(name, args, context=context) for name, args in calls]
        return await asyncio.gather(*tasks, return_exceptions=True)

    def get_stats(self) -> Dict[str, Any]:
        """Obtiene estadísticas de ejecución."""
        total = self._execution_count
        errors = self._error_count
        success = total - errors

        return {
            "total_executions": total,
            "successful": success,
            "errors": errors,
            "success_rate": (success / total * 100) if total > 0 else 0,
            "default_timeout": self.default_timeout,
        }


# Singleton global
_executor: Optional[FunctionExecutor] = None


def get_executor(
    registry: Optional[FunctionRegistry] = None, default_timeout: float = 30.0
) -> FunctionExecutor:
    """Obtiene instancia singleton del executor."""
    global _executor
    if _executor is None:
        _executor = FunctionExecutor(registry, default_timeout)
    return _executor
