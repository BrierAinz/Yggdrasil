"""
Lilith 4.1 — A.2 Telemetría: trazas OpenTelemetry.
Instrumenta flujos críticos: request → plan → steps → LLM.
Exporta a Jaeger/Tempo via OTLP gRPC.
"""
import logging
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Dict, Optional

logger = logging.getLogger("lilith.telemetry.tracing")

_tracer = None
_initialized = False


def _load_config() -> Dict[str, Any]:
    try:
        from src.core.json_safe import safe_load

        bp = Path(__file__).resolve().parent.parent.parent
        cfg = safe_load(bp / "Config" / "telemetry.json", default={})
        return cfg if isinstance(cfg, dict) else {}
    except Exception:
        return {}


def init_tracing() -> bool:
    """
    Inicializa el TracerProvider con exportador OTLP si está configurado.
    Devuelve True si se inicializó correctamente.
    """
    global _tracer, _initialized
    if _initialized:
        return _tracer is not None

    _initialized = True
    cfg = _load_config()
    otel_cfg = cfg.get("opentelemetry", {})

    if not otel_cfg.get("enabled", False):
        logger.debug("[Tracing] OpenTelemetry desactivado por config.")
        return False

    try:
        from opentelemetry import trace
        from opentelemetry.sdk.resources import Resource
        from opentelemetry.sdk.trace import TracerProvider
        from opentelemetry.sdk.trace.export import BatchSpanProcessor

        service_name = otel_cfg.get("service_name", "lilith-backend")
        resource = Resource.create({"service.name": service_name})
        provider = TracerProvider(resource=resource)

        # Exportador OTLP
        endpoint = otel_cfg.get("endpoint", "localhost:4317")
        try:
            from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import (
                OTLPSpanExporter,
            )

            exporter = OTLPSpanExporter(endpoint=endpoint, insecure=True)
            provider.add_span_processor(BatchSpanProcessor(exporter))
            logger.info("[Tracing] Exportador OTLP configurado → %s", endpoint)
        except ImportError:
            logger.warning(
                "[Tracing] opentelemetry-exporter-otlp no instalado. Trazas solo locales."
            )

        trace.set_tracer_provider(provider)
        _tracer = trace.get_tracer("lilith.backend")
        logger.info("[Tracing] OpenTelemetry inicializado (service=%s).", service_name)
        return True

    except Exception as e:
        logger.warning("[Tracing] Error inicializando OpenTelemetry: %s", e)
        return False


def get_tracer():
    """Devuelve el tracer (o None si no está inicializado)."""
    global _tracer
    if not _initialized:
        init_tracing()
    return _tracer


# ── Context managers de instrumentación ───────────────────────────────────────


@contextmanager
def span_request(message: str, transport: str = "unknown", user_id: str = ""):
    """Span padre para un request completo (mensaje → respuesta)."""
    tracer = get_tracer()
    if tracer is None:
        yield None
        return
    with tracer.start_as_current_span("process_request") as span:
        span.set_attribute("transport", transport)
        span.set_attribute("user.id", user_id or "")
        span.set_attribute("message.length", len(message))
        yield span


@contextmanager
def span_plan(message: str):
    """Span para la fase de planificación."""
    tracer = get_tracer()
    if tracer is None:
        yield None
        return
    with tracer.start_as_current_span("create_plan") as span:
        span.set_attribute("message.preview", message[:100])
        yield span


@contextmanager
def span_step(tool_name: str, step_index: int = 0, step_id: str = ""):
    """Span para ejecución de un step del plan."""
    tracer = get_tracer()
    if tracer is None:
        yield None
        return
    with tracer.start_as_current_span(f"execute_step_{tool_name}") as span:
        span.set_attribute("tool.name", tool_name)
        span.set_attribute("step.index", step_index)
        if step_id:
            span.set_attribute("step.id", step_id)
        yield span


@contextmanager
def span_llm_call(model: str, user_role: str = "user"):
    """Span para una llamada LLM."""
    tracer = get_tracer()
    if tracer is None:
        yield None
        return
    with tracer.start_as_current_span("llm_call") as span:
        span.set_attribute("llm.model", model)
        span.set_attribute("user.role", user_role)
        yield span


def record_error(span, error: Exception) -> None:
    """Marca un span como error con detalles de la excepción."""
    if span is None:
        return
    try:
        from opentelemetry.trace import StatusCode

        span.set_status(StatusCode.ERROR, str(error))
        span.record_exception(error)
    except Exception:
        pass
