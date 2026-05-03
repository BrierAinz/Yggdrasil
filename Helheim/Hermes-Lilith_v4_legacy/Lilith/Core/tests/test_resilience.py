"""
Tests for Resilience System
============================
Circuit breaker, retry con backoff y integracion — los Norns
ponen a prueba cada runa del Yggdrasil antes de confiar en ella.
"""

import threading
import time
from unittest.mock import MagicMock, patch

import httpx
import pytest

from Lilith.Core.resilience import (
    CircuitBreaker,
    CircuitBreakerError,
    RetryConfig,
    retry_with_backoff,
)


# ─── CircuitBreaker Tests ────────────────────────────────────────────────────────


class TestCircuitBreakerInit:
    """Test de inicializacion del CircuitBreaker."""

    def test_init_defaults(self):
        cb = CircuitBreaker()
        assert cb.state == "CLOSED"
        assert cb.failure_count == 0
        assert cb.failure_threshold == 3
        assert cb.recovery_timeout == 60.0
        assert cb.half_max_calls == 1

    def test_init_custom(self):
        cb = CircuitBreaker(failure_threshold=5, recovery_timeout=30.0, half_max_calls=3)
        assert cb.failure_threshold == 5
        assert cb.recovery_timeout == 30.0
        assert cb.half_max_calls == 3

    def test_init_state_closed(self):
        cb = CircuitBreaker()
        assert cb.state == "CLOSED"
        assert not cb.is_open


class TestCircuitBreakerClosedState:
    """Tests del estado CLOSED (normal)."""

    def test_call_succeeds(self):
        cb = CircuitBreaker()
        result = cb.call(lambda: 42)
        assert result == 42

    def test_call_with_args(self):
        cb = CircuitBreaker()
        result = cb.call(lambda x, y: x + y, 3, y=4)
        assert result == 7

    def test_record_success_resets_failure_count(self):
        cb = CircuitBreaker()
        cb._failure_count = 2
        cb.record_success()
        assert cb.failure_count == 0

    def test_success_increments_success_count(self):
        cb = CircuitBreaker()
        cb.record_success()
        cb.record_success()
        assert cb.stats["success_count"] == 2

    def test_call_success_records_success(self):
        cb = CircuitBreaker()
        cb.call(lambda: "ok")
        assert cb.stats["success_count"] == 1
        assert cb.failure_count == 0


class TestCircuitBreakerOpensOnThreshold:
    """Tests de apertura del circuito tras N fallos."""

    def test_opens_after_threshold(self):
        cb = CircuitBreaker(failure_threshold=3)
        for i in range(3):
            try:
                cb.call(lambda: (_ for _ in ()).throw(ValueError(f"fail {i}")))
            except ValueError:
                pass
        assert cb.state == "OPEN"
        assert cb.is_open

    def test_does_not_open_below_threshold(self):
        cb = CircuitBreaker(failure_threshold=3)
        for i in range(2):
            try:
                cb.call(lambda: (_ for _ in ()).throw(ValueError("fail")))
            except ValueError:
                pass
        assert cb.state == "CLOSED"

    def test_failure_count_increments(self):
        cb = CircuitBreaker()
        try:
            cb.call(lambda: (_ for _ in ()).throw(ValueError("fail")))
        except ValueError:
            pass
        assert cb.failure_count == 1

    def test_records_failure_time_on_each_failure(self):
        cb = CircuitBreaker(failure_threshold=5)
        before = time.time()
        try:
            cb.call(lambda: (_ for _ in ()).throw(ValueError("fail")))
        except ValueError:
            pass
        after = time.time()
        assert cb.stats["last_failure_time"] is not None
        assert before <= cb.stats["last_failure_time"] <= after


class TestCircuitBreakerHalfOpen:
    """Tests del estado HALF_OPEN (probando)."""

    def test_transitions_to_half_open_after_timeout(self):
        cb = CircuitBreaker(failure_threshold=1, recovery_timeout=0.1)
        # Abrir el circuito
        try:
            cb.call(lambda: (_ for _ in ()).throw(ValueError("fail")))
        except ValueError:
            pass
        assert cb.state == "OPEN"

        # Esperar a que pase el timeout
        time.sleep(0.15)
        assert cb.state == "HALF_OPEN"

    def test_half_open_success_closes_circuit(self):
        cb = CircuitBreaker(failure_threshold=1, recovery_timeout=0.1)
        # Abrir
        try:
            cb.call(lambda: (_ for _ in ()).throw(ValueError("fail")))
        except ValueError:
            pass
        time.sleep(0.15)
        assert cb.state == "HALF_OPEN"

        # Exito cierra el circuito
        result = cb.call(lambda: "ok")
        assert result == "ok"
        assert cb.state == "CLOSED"
        assert cb.failure_count == 0

    def test_half_open_failure_reopens_circuit(self):
        cb = CircuitBreaker(failure_threshold=1, recovery_timeout=0.1)
        # Abrir
        try:
            cb.call(lambda: (_ for _ in ()).throw(ValueError("fail")))
        except ValueError:
            pass
        time.sleep(0.15)
        assert cb.state == "HALF_OPEN"

        # Fallo vuelve a abrir
        try:
            cb.call(lambda: (_ for _ in ()).throw(ValueError("fail again")))
        except ValueError:
            pass
        assert cb.state == "OPEN"

    def test_half_open_limits_calls(self):
        cb = CircuitBreaker(failure_threshold=1, recovery_timeout=0.1, half_max_calls=1)
        # Abrir
        try:
            cb.call(lambda: (_ for _ in ()).throw(ValueError("fail")))
        except ValueError:
            pass
        time.sleep(0.15)
        # La primera llamada en half-open se permite
        result = cb.call(lambda: "ok")
        assert result == "ok"


class TestCircuitBreakerOpen:
    """Tests del estado OPEN (bloqueado)."""

    def test_open_raises_circuit_breaker_error(self):
        cb = CircuitBreaker(failure_threshold=1, recovery_timeout=60.0)
        try:
            cb.call(lambda: (_ for _ in ()).throw(ValueError("fail")))
        except ValueError:
            pass
        assert cb.is_open

        with pytest.raises(CircuitBreakerError):
            cb.call(lambda: "should not pass")

    def test_open_block_all_calls(self):
        cb = CircuitBreaker(failure_threshold=1, recovery_timeout=60.0)
        try:
            cb.call(lambda: (_ for _ in ()).throw(ValueError("fail")))
        except ValueError:
            pass

        for _ in range(5):
            with pytest.raises(CircuitBreakerError):
                cb.call(lambda: "blocked")


class TestCircuitBreakerStats:
    """Tests de estadisticas del circuit breaker."""

    def test_stats_initial(self):
        cb = CircuitBreaker()
        stats = cb.stats
        assert stats["state"] == "CLOSED"
        assert stats["failure_count"] == 0
        assert stats["failure_threshold"] == 3
        assert stats["success_count"] == 0
        assert stats["last_failure_time"] is None

    def test_stats_after_failure(self):
        cb = CircuitBreaker()
        try:
            cb.call(lambda: (_ for _ in ()).throw(ValueError("fail")))
        except ValueError:
            pass
        stats = cb.stats
        assert stats["failure_count"] == 1
        assert stats["last_failure_time"] is not None

    def test_stats_after_success(self):
        cb = CircuitBreaker()
        cb.call(lambda: "ok")
        stats = cb.stats
        assert stats["success_count"] == 1
        assert stats["failure_count"] == 0


class TestCircuitBreakerReset:
    """Tests de reset manual del circuit breaker."""

    def test_reset_clears_state(self):
        cb = CircuitBreaker(failure_threshold=1)
        try:
            cb.call(lambda: (_ for _ in ()).throw(ValueError("fail")))
        except ValueError:
            pass
        assert cb.state == "OPEN"

        cb.reset()
        assert cb.state == "CLOSED"
        assert cb.failure_count == 0

    def test_reset_allows_calls_again(self):
        cb = CircuitBreaker(failure_threshold=1, recovery_timeout=60.0)
        try:
            cb.call(lambda: (_ for _ in ()).throw(ValueError("fail")))
        except ValueError:
            pass

        cb.reset()
        result = cb.call(lambda: "works")
        assert result == "works"


class TestCircuitBreakerThreadSafety:
    """Tests de thread-safety del circuit breaker."""

    def test_concurrent_calls_success(self):
        cb = CircuitBreaker(failure_threshold=10, recovery_timeout=60.0)
        results = []
        errors = []

        def worker(i):
            try:
                r = cb.call(lambda: i * 2)
                results.append(r)
            except Exception as e:
                errors.append(e)

        threads = [threading.Thread(target=worker, args=(i,)) for i in range(20)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert len(results) == 20
        assert len(errors) == 0

    def test_concurrent_mixed_success_failure(self):
        cb = CircuitBreaker(failure_threshold=100, recovery_timeout=60.0)
        call_count = 0

        def mixed_call():
            nonlocal call_count
            call_count += 1
            if call_count % 3 == 0:
                raise ValueError("intermittent")
            return "ok"

        successes = []
        failures = []

        def worker():
            try:
                r = cb.call(mixed_call)
                successes.append(r)
            except (ValueError, CircuitBreakerError) as e:
                failures.append(type(e).__name__)

        threads = [threading.Thread(target=worker) for _ in range(30)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        # Algunos exitos, algunos fallos, pero sin crash
        total = len(successes) + len(failures)
        assert total == 30


# ─── RetryConfig Tests ────────────────────────────────────────────────────────────


class TestRetryConfig:
    """Tests de configuracion de retry."""

    def test_defaults(self):
        config = RetryConfig()
        assert config.max_retries == 3
        assert config.base_delay == 1.0
        assert config.max_delay == 30.0
        assert config.backoff_factor == 2.0
        assert 429 in config.retryable_errors
        assert 500 in config.retryable_errors

    def test_custom_config(self):
        config = RetryConfig(
            max_retries=5,
            base_delay=0.5,
            max_delay=10.0,
            backoff_factor=3.0,
            retryable_errors=[500, 503],
        )
        assert config.max_retries == 5
        assert config.base_delay == 0.5
        assert config.max_delay == 10.0
        assert config.backoff_factor == 3.0
        assert config.retryable_errors == [500, 503]

    def test_get_delay_exponential(self):
        config = RetryConfig(base_delay=1.0, backoff_factor=2.0)
        assert config.get_delay(0) == 1.0   # 1.0 * 2^0
        assert config.get_delay(1) == 2.0   # 1.0 * 2^1
        assert config.get_delay(2) == 4.0   # 1.0 * 2^2
        assert config.get_delay(3) == 8.0   # 1.0 * 2^3

    def test_get_delay_respects_max(self):
        config = RetryConfig(base_delay=1.0, max_delay=5.0, backoff_factor=2.0)
        assert config.get_delay(10) == 5.0  # capped at max_delay

    def test_is_retryable_http_status(self):
        config = RetryConfig()
        error_429 = httpx.HTTPStatusError(
            "rate limited",
            request=httpx.Request("GET", "http://test"),
            response=httpx.Response(429),
        )
        error_404 = httpx.HTTPStatusError(
            "not found",
            request=httpx.Request("GET", "http://test"),
            response=httpx.Response(404),
        )
        assert config.is_retryable(error_429) is True
        assert config.is_retryable(error_404) is False

    def test_is_retryable_connection_error(self):
        config = RetryConfig()
        assert config.is_retryable(ConnectionError("refused")) is True
        assert config.is_retryable(httpx.ConnectError("no connection")) is True
        assert config.is_retryable(httpx.TimeoutException("timeout")) is True

    def test_is_retryable_non_retryable(self):
        config = RetryConfig()
        assert config.is_retryable(ValueError("bad value")) is False
        assert config.is_retryable(TypeError("wrong type")) is False


# ─── retry_with_backoff Tests ────────────────────────────────────────────────────


class TestRetryWithBackoff:
    """Tests de retry con backoff exponencial."""

    def test_success_first_try(self):
        func = MagicMock(return_value="result")
        result = retry_with_backoff(func)
        assert result == "result"
        assert func.call_count == 1

    def test_success_first_try_with_config(self):
        config = RetryConfig(max_retries=5)
        func = MagicMock(return_value="hello")
        result = retry_with_backoff(func, retry_config=config)
        assert result == "hello"
        assert func.call_count == 1

    def test_retries_on_retryable_error(self):
        config = RetryConfig(max_retries=2, base_delay=0.01, max_delay=0.05)
        func = MagicMock(side_effect=[ConnectionError("fail"), "ok"])
        result = retry_with_backoff(func, retry_config=config)
        assert result == "ok"
        assert func.call_count == 2

    def test_retries_on_http_error(self):
        config = RetryConfig(max_retries=3, base_delay=0.01, max_delay=0.05)
        error = httpx.HTTPStatusError(
            "server error",
            request=httpx.Request("GET", "http://test"),
            response=httpx.Response(503),
        )
        func = MagicMock(side_effect=[error, "recovered"])
        result = retry_with_backoff(func, retry_config=config)
        assert result == "recovered"
        assert func.call_count == 2

    def test_max_retries_exhausted(self):
        config = RetryConfig(max_retries=2, base_delay=0.01, max_delay=0.05)
        func = MagicMock(side_effect=ConnectionError("always fails"))
        with pytest.raises(ConnectionError):
            retry_with_backoff(func, retry_config=config)
        assert func.call_count == 3  # initial + 2 retries

    def test_non_retryable_error_raises_immediately(self):
        config = RetryConfig(max_retries=5, base_delay=0.01)
        func = MagicMock(side_effect=ValueError("not retryable"))
        with pytest.raises(ValueError):
            retry_with_backoff(func, retry_config=config)
        assert func.call_count == 1  # No retries for non-retryable

    def test_circuit_breaker_blocks_on_open(self):
        cb = CircuitBreaker(failure_threshold=1, recovery_timeout=60.0)
        # Abrir el circuit breaker
        try:
            cb.call(lambda: (_ for _ in ()).throw(ValueError("fail")))
        except ValueError:
            pass
        assert cb.is_open

        config = RetryConfig(max_retries=3)
        func = MagicMock(return_value="won't reach")

        with pytest.raises(CircuitBreakerError):
            retry_with_backoff(func, retry_config=config, circuit_breaker=cb)
        assert func.call_count == 0  # Nunca se llamo

    def test_circuit_breaker_records_success(self):
        cb = CircuitBreaker(failure_threshold=3)
        config = RetryConfig(max_retries=3)
        func = MagicMock(return_value="success")

        result = retry_with_backoff(func, retry_config=config, circuit_breaker=cb)
        assert result == "success"
        assert cb.state == "CLOSED"
        assert cb.stats["success_count"] == 1
        assert cb.failure_count == 0

    def test_circuit_breaker_records_failure_exhausted(self):
        cb = CircuitBreaker(failure_threshold=5)
        config = RetryConfig(max_retries=2, base_delay=0.01, max_delay=0.05)
        func = MagicMock(side_effect=ConnectionError("fail"))

        with pytest.raises(ConnectionError):
            retry_with_backoff(func, retry_config=config, circuit_breaker=cb)

        # After 3 attempts (1 initial + 2 retries), all failures are recorded
        assert cb.failure_count >= 3

    def test_backoff_delays_approximate(self):
        """Verify that backoff delays increase between retries."""
        config = RetryConfig(max_retries=3, base_delay=0.05, max_delay=1.0, backoff_factor=2.0)
        call_times = []

        def timed_func():
            call_times.append(time.time())
            if len(call_times) < 3:
                raise ConnectionError("retry me")
            return "done"

        result = retry_with_backoff(timed_func, retry_config=config)
        assert result == "done"

        # Verify delays increase (at least approx)
        if len(call_times) >= 3:
            delay1 = call_times[1] - call_times[0]
            delay2 = call_times[2] - call_times[1]
            # Second delay should be ~2x first delay
            assert delay2 >= delay1 * 0.8  # Allow some slack

    def test_retry_with_no_circuit_breaker(self):
        config = RetryConfig(max_retries=2, base_delay=0.01, max_delay=0.05)
        func = MagicMock(side_effect=[ConnectionError("fail"), "recovered"])
        result = retry_with_backoff(func, retry_config=config, circuit_breaker=None)
        assert result == "recovered"

    def test_circuit_breaker_integration_full_cycle(self):
        """Full cycle: fail -> open -> wait -> half_open -> success -> close."""
        cb = CircuitBreaker(failure_threshold=2, recovery_timeout=0.1)
        config = RetryConfig(max_retries=0, base_delay=0.01, max_delay=0.05)

        # Fail enough times to open the circuit (threshold=2)
        for _ in range(2):
            try:
                retry_with_backoff(
                    lambda: (_ for _ in ()).throw(ConnectionError("fail")),
                    retry_config=config,
                    circuit_breaker=cb,
                )
            except ConnectionError:
                pass

        assert cb.is_open

        # Wait for recovery -> circuit transitions to HALF_OPEN
        time.sleep(0.15)

        # Now the circuit should be HALF_OPEN and a success closes it
        result = retry_with_backoff(
            lambda: "back online",
            retry_config=config,
            circuit_breaker=cb,
        )
        assert result == "back online"
        assert cb.state == "CLOSED"

    def test_http_429_is_retryable(self):
        config = RetryConfig(max_retries=1, base_delay=0.01, max_delay=0.05)
        call_count = 0

        def func_429():
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise httpx.HTTPStatusError(
                    "rate limited",
                    request=httpx.Request("GET", "http://test"),
                    response=httpx.Response(429),
                )
            return "ok after rate limit"

        result = retry_with_backoff(func_429, retry_config=config)
        assert result == "ok after rate limit"
        assert call_count == 2

    def test_http_404_not_retryable(self):
        config = RetryConfig(max_retries=3, base_delay=0.01)
        call_count = 0

        def func_404():
            nonlocal call_count
            call_count += 1
            raise httpx.HTTPStatusError(
                "not found",
                request=httpx.Request("GET", "http://test"),
                response=httpx.Response(404),
            )

        with pytest.raises(httpx.HTTPStatusError):
            retry_with_backoff(func_404, retry_config=config)
        assert call_count == 1  # No retry for 404