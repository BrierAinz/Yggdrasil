"""
Retry Manager con Backoff Exponencial

Sistema de reintentos para llamadas HTTP con:
- Backoff exponencial
- Jitter aleatorio
- Rate limit detection (429)
- Logs estructurados
"""

import logging
import random
import time
from dataclasses import dataclass
from typing import Any, Callable, Dict, Optional

logger = logging.getLogger(__name__)


@dataclass
class RetryConfig:
    """Configuración de retry"""

    max_attempts: int = 3
    base_delay: float = 1.0  # Segundos
    max_delay: float = 30.0  # Segundos
    exponential_base: float = 2.0
    jitter: bool = True


class RetryManager:
    """
    Gestor de reintentos con backoff exponencial

    Ejemplo:
        result = retry_manager.execute(
            func=lambda: requests.post(...),
            config=RetryConfig(max_attempts=3)
        )
    """

    def __init__(self, default_config: Optional[RetryConfig] = None):
        """
        Args:
            default_config: Configuración por defecto
        """
        self.default_config = default_config or RetryConfig()

    def execute(
        self,
        func: Callable[[], Any],
        config: Optional[RetryConfig] = None,
        is_retryable: Optional[Callable[[Exception], bool]] = None,
    ) -> Any:
        """
        Ejecutar función con reintentos

        Args:
            func: Función a ejecutar (sin args)
            config: Configuración de retry (usa default si None)
            is_retryable: Función que determina si un error es retriable

        Returns:
            Resultado de func()

        Raises:
            Exception: Si todos los intentos fallan
        """
        if config is None:
            config = self.default_config

        if is_retryable is None:
            is_retryable = self._default_is_retryable

        last_exception = None

        for attempt in range(1, config.max_attempts + 1):
            try:
                result = func()

                if attempt > 1:
                    logger.info(f"Retry succeeded on attempt {attempt}")

                return result

            except Exception as e:
                last_exception = e

                # Verificar si es retriable
                if not is_retryable(e):
                    logger.warning(f"Non-retryable error: {e}")
                    raise

                # Si es el último intento, raise
                if attempt >= config.max_attempts:
                    logger.error(f"All {config.max_attempts} retry attempts failed")
                    raise

                # Calcular delay con backoff exponencial
                delay = self._calculate_delay(
                    attempt=attempt, config=config, exception=e
                )

                logger.warning(
                    f"Attempt {attempt}/{config.max_attempts} failed: {e}. "
                    f"Retrying in {delay:.1f}s..."
                )

                time.sleep(delay)

        # Fallback (no debería llegar aquí)
        raise last_exception

    def _calculate_delay(
        self, attempt: int, config: RetryConfig, exception: Optional[Exception] = None
    ) -> float:
        """
        Calcular delay con backoff exponencial

        Args:
            attempt: Número de intento (1-indexed)
            config: Configuración
            exception: Excepción (para detectar rate limits)

        Returns:
            Delay en segundos
        """
        # Detectar rate limit (429)
        if exception and self._is_rate_limit_error(exception):
            # Rate limit: esperar más tiempo
            delay = config.max_delay
            logger.info(f"Rate limit detected, using max delay: {delay}s")
        else:
            # Backoff exponencial: base_delay * (exponential_base ^ (attempt - 1))
            delay = config.base_delay * (config.exponential_base ** (attempt - 1))

            # Clamp a max_delay
            delay = min(delay, config.max_delay)

        # Agregar jitter aleatorio
        if config.jitter:
            jitter_amount = delay * 0.25  # ±25%
            delay += random.uniform(-jitter_amount, jitter_amount)
            delay = max(0.1, delay)  # Mínimo 0.1s

        return delay

    def _default_is_retryable(self, exception: Exception) -> bool:
        """
        Determinar si un error es retriable por defecto

        Args:
            exception: Excepción

        Returns:
            True si es retriable
        """
        # Errors de red son retriables
        exception_type = type(exception).__name__

        retriable_types = [
            "ConnectionError",
            "Timeout",
            "TimeoutError",
            "HTTPError",
            "RequestException",
        ]

        if any(t in exception_type for t in retriable_types):
            return True

        # Rate limits son retriables
        if self._is_rate_limit_error(exception):
            return True

        # Por defecto, no retriable
        return False

    def _is_rate_limit_error(self, exception: Exception) -> bool:
        """Detectar si es un error de rate limit (429)"""
        exception_str = str(exception).lower()

        rate_limit_indicators = ["429", "rate limit", "too many requests"]

        return any(indicator in exception_str for indicator in rate_limit_indicators)


# Singleton global
_retry_manager: Optional[RetryManager] = None


def get_retry_manager() -> RetryManager:
    """Obtener instancia singleton del retry manager"""
    global _retry_manager
    if _retry_manager is None:
        _retry_manager = RetryManager()
    return _retry_manager


def retry_with_backoff(
    func: Callable[[], Any], max_attempts: int = 3, base_delay: float = 1.0
) -> Any:
    """
    Función de conveniencia para retry con backoff

    Args:
        func: Función a ejecutar
        max_attempts: Máximo de intentos
        base_delay: Delay base en segundos

    Returns:
        Resultado de func()
    """
    manager = get_retry_manager()
    config = RetryConfig(max_attempts=max_attempts, base_delay=base_delay)
    return manager.execute(func=func, config=config)
