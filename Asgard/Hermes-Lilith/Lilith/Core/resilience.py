"""
Resilience System
=================
Circuit breaker y retry con backoff exponencial para Lilith v3.

Las Norns tejen los hilos del destino — cuando un provider cae, el circuito
se abre como las puertas de Asgard ante el caos. Cuando la calma retorna,
el half-open permite susurros de prueba antes de reabrir el camino completo.

Estados del Circuit Breaker:
  CLOSED   — El camino de Midgard fluye libremente (normal)
  OPEN     — Las puertas de Muspelheim sellan el paso (bloqueado)
  HALF_OPEN— Un susurro de Niflheim prueba si el puente resiste (probando)
"""

import threading
import time
import functools
from typing import Any, Callable, Dict, List, Optional

import httpx


class CircuitBreakerError(Exception):
    """Raised when circuit breaker is open.

    Las Norns han sellado este camino — el provider yace bajo las raices
    del Yggdrasil y no debe ser perturbado hasta que pase el tiempo de
    recuperacion.
    """
    pass


class CircuitBreaker:
    """Circuit breaker para LLM providers.

    Protege contra cascading failures abriendo el circuito tras N fallos
    consecutivos. Tras un periodo de recuperacion, permite llamadas de prueba
    en estado HALF_OPEN antes de volver a cerrarse.

    Thread-safe: usa un Lock para proteger transiciones de estado.

    Args:
        failure_threshold: Fallos consecutivos necesarios para abrir el circuito.
        recovery_timeout: Segundos en OPEN antes de transicionar a HALF_OPEN.
        half_max_calls: Llamadas permitidas en HALF_OPEN antes de decidir.
    """

    def __init__(
        self,
        failure_threshold: int = 3,
        recovery_timeout: float = 60.0,
        half_max_calls: int = 1,
    ):
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.half_max_calls = half_max_calls

        self._state = "CLOSED"
        self._failure_count = 0
        self._last_failure_time: Optional[float] = None
        self._half_open_calls = 0
        self._success_count = 0
        self._lock = threading.Lock()

    def call(self, func: Callable, *args, **kwargs) -> Any:
        """Ejecuta func si el circuito lo permite.

        Si el circuito esta OPEN y el timeout no ha expirado, lanza
        CircuitBreakerError. Si esta HALF_OPEN, permite un numero
        limitado de llamadas de prueba.

        Args:
            func: Callable a ejecutar.
            *args, **kwargs: Argumentos para func.

        Returns:
            Resultado de func(*args, **kwargs).

        Raises:
            CircuitBreakerError: Si el circuito esta OPEN.
        """
        with self._lock:
            self._check_state()

            if self._state == "OPEN":
                raise CircuitBreakerError(
                    f"Circuit breaker OPEN — provider bloqueado. "
                    f"Ultimo fallo hace {time.time() - (self._last_failure_time or time.time()):.1f}s. "
                    f"Reintento posible en {self.recovery_timeout - (time.time() - (self._last_failure_time or time.time())):.1f}s."
                )

            if self._state == "HALF_OPEN":
                self._half_open_calls += 1

        # Ejecutar fuera del lock para no bloquear otros hilos
        try:
            result = func(*args, **kwargs)
            self.record_success()
            return result
        except Exception:
            self.record_failure()
            raise

    def record_success(self) -> None:
        """Registra un exito — reinicia failure_count y cierra el circuito.

        Cuando la runa de Raido brilla, el camino se restaura y las
        sombras de los fallos previos se desvanecen.
        """
        with self._lock:
            self._failure_count = 0
            self._success_count += 1

            if self._state == "HALF_OPEN":
                # Si era HALF_OPEN y tuvo exito, cerrar el circuito
                self._state = "CLOSED"
                self._half_open_calls = 0

    def record_failure(self) -> None:
        """Registra un fallo — incrementa failure_count y abre el circuito si supera threshold.

        Cada fallo es una runa de Isa grabada en las raices del Yggdrasil.
        Cuando las runas acumulan suficiente oscuridad, el circuito se abre
        como las fauces del lobo Fenris.
        """
        with self._lock:
            self._failure_count += 1
            self._last_failure_time = time.time()

            if self._state == "HALF_OPEN":
                # Fallo en half-open — volver a abrir
                self._state = "OPEN"
                self._half_open_calls = 0
            elif self._failure_count >= self.failure_threshold:
                self._state = "OPEN"

    def _check_state(self) -> None:
        """Verifica si el circuito debe transicionar de OPEN a HALF_OPEN.

        Debe llamarse dentro de un bloque con self._lock adquirido.
        """
        if self._state == "OPEN" and self._last_failure_time is not None:
            elapsed = time.time() - self._last_failure_time
            if elapsed >= self.recovery_timeout:
                self._state = "HALF_OPEN"
                self._half_open_calls = 0

    @property
    def state(self) -> str:
        """Retorna el estado actual del circuito (CLOSED, OPEN, HALF_OPEN)."""
        with self._lock:
            self._check_state()
            return self._state

    @property
    def failure_count(self) -> int:
        """Retorna el conteo de fallos consecutivos actual."""
        with self._lock:
            return self._failure_count

    @property
    def is_open(self) -> bool:
        """True si el circuito esta OPEN (bloqueado)."""
        with self._lock:
            self._check_state()
            return self._state == "OPEN"

    @property
    def stats(self) -> Dict[str, Any]:
        """Retorna estadisticas del circuit breaker.

        Los Norns leen estas runas para conocer el estado de los caminos
        entre los nueve mundos.
        """
        with self._lock:
            self._check_state()
            return {
                "state": self._state,
                "failure_count": self._failure_count,
                "failure_threshold": self.failure_threshold,
                "success_count": self._success_count,
                "last_failure_time": self._last_failure_time,
                "recovery_timeout": self.recovery_timeout,
                "half_open_calls": self._half_open_calls,
            }

    def reset(self) -> None:
        """Resetea el circuit breaker a estado CLOSED.

        Las Norns reescriben el destino — el camino queda despejado.
        """
        with self._lock:
            self._state = "CLOSED"
            self._failure_count = 0
            self._last_failure_time = None
            self._half_open_calls = 0


class RetryConfig:
    """Configuracion de retry con backoff exponencial.

    Los viajeros que buscan la sabiduria del Yggdrasil saben que los
    caminos son inciertos — el retry con backoff es la paciencia de
    quien espera el momento correcto para cruzar el Bifrost.

    Attributes:
        max_retries: Numero maximo de reintentos antes de rendirse.
        base_delay: Segundos de espera antes del primer retry.
        max_delay: Segundos maximos de espera entre retries.
        backoff_factor: Multiplicador para calcular delays sucesivos.
        retryable_errors: Codigos de estado HTTP que merecen retry,
                          o tipos de excepcion que merecen retry.
    """

    max_retries: int = 3
    base_delay: float = 1.0
    max_delay: float = 30.0
    backoff_factor: float = 2.0
    retryable_errors: List = [429, 500, 502, 503, 504]

    def __init__(
        self,
        max_retries: int = 3,
        base_delay: float = 1.0,
        max_delay: float = 30.0,
        backoff_factor: float = 2.0,
        retryable_errors: Optional[List] = None,
    ):
        self.max_retries = max_retries
        self.base_delay = base_delay
        self.max_delay = max_delay
        self.backoff_factor = backoff_factor
        if retryable_errors is not None:
            self.retryable_errors = retryable_errors
        else:
            self.retryable_errors = [429, 500, 502, 503, 504]

    def get_delay(self, attempt: int) -> float:
        """Calcula el delay para el intento dado (0-indexed).

        El delay sigue un patron exponencial como las raices del
        Yggdrasil que se hunden cada vez mas profundo.

        Args:
            attempt: Numero de intento (0 = primer retry).

        Returns:
            Segundos de espera antes del siguiente intento.
        """
        delay = self.base_delay * (self.backoff_factor ** attempt)
        return min(delay, self.max_delay)

    def is_retryable(self, error: Exception) -> bool:
        """Determina si un error merece retry.

        Los errores transitorios son como las nieblas de Niflheim —
        temporales y dignos de esperar a que se disipen.

        Args:
            error: La excepcion a evaluar.

        Returns:
            True si el error es retryable.
        """
        # httpx.HTTPStatusError tiene response.status_code
        if isinstance(error, httpx.HTTPStatusError):
            return error.response.status_code in self.retryable_errors

        # httpx timeout errors son retryable
        if isinstance(error, (httpx.TimeoutException, httpx.ConnectError)):
            return True

        # ConnectionError es retryable
        if isinstance(error, (ConnectionError, ConnectionRefusedError, OSError)):
            return True

        return False


def retry_with_backoff(
    func: Callable,
    retry_config: Optional[RetryConfig] = None,
    circuit_breaker: Optional[CircuitBreaker] = None,
) -> Any:
    """Ejecuta func con retry y circuit breaker.

    Si circuit_breaker.is_open -> lanza CircuitBreakerError inmediatamente.
    Si falla -> retry con backoff exponencial.
    Si agota retries -> record_failure en circuit_breaker y relanza.
    Si exitosa -> record_success en circuit_breaker y retorna resultado.

    Nota: No usa circuit_breaker.call() internamente para evitar doble
    conteo de success/failure. En su lugar, consulta is_open y registra
    manualmente tras cada intento.

    Args:
        func: Callable a ejecutar sin argumentos.
        retry_config: Configuracion de retry. Default si es None.
        circuit_breaker: Circuit breaker para proteccion. Opcional.

    Returns:
        Resultado de func().

    Raises:
        CircuitBreakerError: Si el circuito esta OPEN.
        Exception: La ultima excepcion si se agotan los retries.
    """
    if retry_config is None:
        retry_config = RetryConfig()

    # Verificar circuit breaker antes de intentar
    if circuit_breaker is not None and circuit_breaker.is_open:
        raise CircuitBreakerError(
            "Circuit breaker OPEN — provider bloqueado por fallos consecutivos."
        )

    last_exception: Optional[Exception] = None

    for attempt in range(retry_config.max_retries + 1):
        try:
            result = func()

            # Exito: registrar en circuit breaker si existe
            if circuit_breaker is not None:
                circuit_breaker.record_success()

            return result

        except CircuitBreakerError:
            raise

        except Exception as e:
            last_exception = e

            # Si no es retryable, registrar fallo y fallar inmediatamente
            if not retry_config.is_retryable(e):
                if circuit_breaker is not None:
                    circuit_breaker.record_failure()
                raise

            # Si es el ultimo intento, registrar fallo y relanzar
            if attempt >= retry_config.max_retries:
                if circuit_breaker is not None:
                    circuit_breaker.record_failure()
                raise

            # Registrar fallo en circuit breaker por cada intento fallido
            if circuit_breaker is not None:
                circuit_breaker.record_failure()

            # Calcular delay y esperar
            delay = retry_config.get_delay(attempt)
            time.sleep(delay)

    # No deberia llegar aqui, pero por seguridad
    if circuit_breaker is not None:
        circuit_breaker.record_failure()
    if last_exception is not None:
        raise last_exception