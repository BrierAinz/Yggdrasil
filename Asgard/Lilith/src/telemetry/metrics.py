"""
Lilith 4.1 — A.2 Telemetría: métricas Prometheus.
Centraliza todos los contadores, histogramas y gauges del sistema.
Endpoint: GET /metrics (expuesto por prometheus-client WSGI)
"""
import logging
import time
from contextlib import contextmanager
from typing import Optional

logger = logging.getLogger("lilith.telemetry.metrics")

# ── Inicialización lazy (evita importar prometheus en tests sin necesidad) ────

_registry_initialized = False
_prom = None  # módulo prometheus_client


def _init():
    global _registry_initialized, _prom
    if _registry_initialized:
        return
    try:
        import prometheus_client as prom

        _prom = prom
        _registry_initialized = True
    except ImportError:
        logger.warning(
            "[Metrics] prometheus_client no instalado. Métricas desactivadas."
        )


# ── Definición de métricas ────────────────────────────────────────────────────


class _NullMetric:
    """Métrica nula: no hace nada (cuando prometheus no está disponible)."""

    def labels(self, **kw):
        return self

    def inc(self, amount=1):
        pass

    def dec(self, amount=1):
        pass

    def set(self, v):
        pass

    def observe(self, v):
        pass

    def time(self):
        return self

    def __enter__(self):
        return self

    def __exit__(self, *a):
        pass


_null = _NullMetric()


def _counter(name: str, desc: str, labels: list):
    _init()
    if _prom is None:
        return _null
    try:
        return _prom.Counter(name, desc, labels)
    except Exception:
        return _null


def _histogram(name: str, desc: str, labels: list, buckets=None):
    _init()
    if _prom is None:
        return _null
    try:
        kw = {}
        if buckets:
            kw["buckets"] = buckets
        return _prom.Histogram(name, desc, labels, **kw)
    except Exception:
        return _null


def _gauge(name: str, desc: str, labels: list):
    _init()
    if _prom is None:
        return _null
    try:
        return _prom.Gauge(name, desc, labels)
    except Exception:
        return _null


# ── Métricas definidas ────────────────────────────────────────────────────────

# Contadores LLM
llm_requests_total = _counter(
    "lilith_llm_requests_total",
    "Total de requests a LLM",
    ["model", "user_role"],
)
llm_errors_total = _counter(
    "lilith_llm_errors_total",
    "Total de errores LLM",
    ["model", "error_type"],
)
llm_tokens_total = _counter(
    "lilith_llm_tokens_total",
    "Total de tokens consumidos",
    ["model", "direction"],  # direction: input | output
)

# Histogramas LLM (latencia)
llm_latency_seconds = _histogram(
    "lilith_llm_latency_seconds",
    "Latencia de requests LLM (segundos)",
    ["model"],
    buckets=[0.1, 0.5, 1.0, 2.0, 5.0, 10.0, 30.0, 60.0],
)

# Contadores de tools
tool_calls_total = _counter(
    "lilith_tool_calls_total",
    "Total de llamadas a tools",
    ["tool_name", "status"],  # status: success | error | timeout
)

# Histogramas de tools
tool_latency_seconds = _histogram(
    "lilith_tool_latency_seconds",
    "Latencia de ejecución de tools (segundos)",
    ["tool_name"],
    buckets=[0.01, 0.05, 0.1, 0.5, 1.0, 5.0, 30.0],
)

# Gauges de sesiones activas
active_sessions = _gauge(
    "lilith_active_sessions",
    "Sesiones de conversación activas",
    ["transport"],  # transport: discord | telegram | vscode | websocket
)

# Gauges de salud de subsistemas
subsystem_healthy = _gauge(
    "lilith_subsystem_healthy",
    "Estado de salud de subsistemas (1=healthy, 0=unhealthy)",
    ["subsystem"],
)

# Gauge de tamaño de episodic log
episodic_log_entries = _gauge(
    "lilith_episodic_log_entries_total",
    "Total de entradas en episodic_log.jsonl",
    [],
)

# Contadores de planes
plans_generated_total = _counter(
    "lilith_plans_generated_total",
    "Total de planes generados",
    [
        "reason"
    ],  # reason: learned | classifier | intent_pattern | fallback | shalltear | ...
)

# Histograma de confianza del planner
plan_confidence = _histogram(
    "lilith_plan_confidence",
    "Confianza del planner en el plan generado",
    ["reason"],
    buckets=[0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0],
)


# ── Helpers de instrumentación ────────────────────────────────────────────────


@contextmanager
def time_llm_call(model: str):
    """Context manager para medir latencia de llamada LLM."""
    start = time.perf_counter()
    try:
        yield
    finally:
        elapsed = time.perf_counter() - start
        try:
            llm_latency_seconds.labels(model=model).observe(elapsed)
        except Exception:
            pass


@contextmanager
def time_tool_call(tool_name: str):
    """Context manager para medir latencia de tool."""
    start = time.perf_counter()
    status = "success"
    try:
        yield
    except Exception:
        status = "error"
        raise
    finally:
        elapsed = time.perf_counter() - start
        try:
            tool_latency_seconds.labels(tool_name=tool_name).observe(elapsed)
            tool_calls_total.labels(tool_name=tool_name, status=status).inc()
        except Exception:
            pass


def record_llm_request(
    model: str, user_role: str = "user", input_tokens: int = 0, output_tokens: int = 0
):
    """Registra una llamada LLM completada."""
    try:
        llm_requests_total.labels(model=model, user_role=user_role).inc()
        if input_tokens:
            llm_tokens_total.labels(model=model, direction="input").inc(input_tokens)
        if output_tokens:
            llm_tokens_total.labels(model=model, direction="output").inc(output_tokens)
    except Exception:
        pass


def record_plan(reason: str, confidence: float):
    """Registra un plan generado."""
    try:
        plans_generated_total.labels(reason=reason).inc()
        plan_confidence.labels(reason=reason).observe(confidence)
    except Exception:
        pass


def set_subsystem_health(subsystem: str, healthy: bool):
    """Actualiza gauge de salud de subsistema."""
    try:
        subsystem_healthy.labels(subsystem=subsystem).set(1 if healthy else 0)
    except Exception:
        pass


def get_metrics_text() -> str:
    """Devuelve métricas en formato texto Prometheus (para /metrics endpoint)."""
    _init()
    if _prom is None:
        return "# prometheus_client no disponible\n"
    try:
        from prometheus_client import CONTENT_TYPE_LATEST, generate_latest

        return generate_latest().decode("utf-8")
    except Exception as e:
        return f"# Error generando métricas: {e}\n"
