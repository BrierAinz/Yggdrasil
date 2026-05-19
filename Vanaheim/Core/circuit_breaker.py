"""Circuit Breaker para resiliencia en llamadas externas."""
import logging
from datetime import datetime


logger = logging.getLogger("bifrost.circuit_breaker")


class CircuitBreaker:
    """
    Circuit breaker para proteger contra fallos en cascada.
    Estados:
    - CLOSED: Funcionamiento normal, las llamadas pasan
    - OPEN: El circuito está abierto, las llamadas fallan rápidamente
    - HALF_OPEN: Probando si el servicio se ha recuperado
    """

    def __init__(self, failure_threshold: int = 3, recovery_timeout: int = 30):
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.failures = 0
        self.last_failure_time: datetime | None = None
        self.state = "closed"  # closed, open, half-open

    def can_execute(self) -> bool:
        """Determina si se puede ejecutar una llamada."""
        if self.state == "closed":
            return True

        if self.state == "open":
            if self.last_failure_time:
                elapsed = (datetime.now() - self.last_failure_time).total_seconds()
                if elapsed > self.recovery_timeout:
                    logger.info("[CircuitBreaker] Transitioning to half-open")
                    self.state = "half-open"
                    return True
            logger.debug("[CircuitBreaker] Circuit is OPEN, fast-failing")
            return False

        # half-open
        return True

    def record_success(self):
        """Registra un éxito, resetea el contador de fallos."""
        if self.state == "half-open":
            logger.info("[CircuitBreaker] Recovery successful, closing circuit")
        self.failures = 0
        self.state = "closed"

    def record_failure(self):
        """Registra un fallo, posiblemente abre el circuito."""
        self.failures += 1
        self.last_failure_time = datetime.now()

        if self.failures >= self.failure_threshold:
            if self.state != "open":
                logger.warning(
                    f"[CircuitBreaker] Opening circuit after {self.failures} failures"
                )
                self.state = "open"

    def get_status(self) -> dict:
        """Retorna estado actual para monitoreo."""
        return {
            "state": self.state,
            "failures": self.failures,
            "threshold": self.failure_threshold,
            "last_failure": self.last_failure_time.isoformat()
            if self.last_failure_time
            else None,
        }
