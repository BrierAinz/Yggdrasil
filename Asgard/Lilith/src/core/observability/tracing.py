"""
Distributed Tracing - OpenTelemetry tracing

v5.0-Fase4C: Distributed tracing para request tracking y debugging.
"""
import asyncio
import json
import logging
import uuid
from contextlib import contextmanager
from contextvars import ContextVar
from dataclasses import asdict, dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

logger = logging.getLogger("lilith.observability.tracing")


class SpanStatus(Enum):
    """Estado de un span."""

    OK = "ok"
    ERROR = "error"
    CANCELLED = "cancelled"


class SpanKind(Enum):
    """Tipo de span."""

    INTERNAL = "internal"
    SERVER = "server"
    CLIENT = "client"
    PRODUCER = "producer"
    CONSUMER = "consumer"


@dataclass
class Span:
    """Span de traza."""

    trace_id: str
    span_id: str
    parent_id: Optional[str]
    name: str
    kind: SpanKind
    start_time: str
    end_time: Optional[str] = None
    status: SpanStatus = SpanStatus.OK
    attributes: Dict[str, Any] = field(default_factory=dict)
    events: List[Dict[str, Any]] = field(default_factory=list)
    links: List[Dict[str, Any]] = field(default_factory=list)


@dataclass
class Trace:
    """Traza completa."""

    trace_id: str
    root_span_id: str
    spans: Dict[str, Span] = field(default_factory=dict)
    start_time: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    end_time: Optional[str] = None
    resource: Dict[str, Any] = field(default_factory=dict)


# Contexto de traza actual
_current_span: ContextVar[Optional[Span]] = ContextVar("current_span", default=None)
_current_trace: ContextVar[Optional[Trace]] = ContextVar("current_trace", default=None)


class Tracer:
    """
    Tracer distribuido compatible con OpenTelemetry.

    Features:
    - Creación de trazas y spans
    - Context propagation
    - Exportación de trazas
    - Sampling configurable
    """

    def __init__(
        self,
        service_name: str = "lilith",
        service_version: str = "5.0.0",
        sampling_rate: float = 1.0,
        storage_path: Optional[Path] = None,
    ):
        self.service_name = service_name
        self.service_version = service_version
        self.sampling_rate = sampling_rate
        self.active_traces: Dict[str, Trace] = {}
        self.completed_traces: List[Trace] = []
        self.max_completed_traces = 1000
        self.storage_path = storage_path or Path("Data/traces")
        self.storage_path.mkdir(parents=True, exist_ok=True)
        self.export_handlers: List[Callable[[Trace], None]] = []
        self.lock = asyncio.Lock()

    def start_trace(
        self, name: str, attributes: Optional[Dict[str, Any]] = None
    ) -> Trace:
        """Inicia una nueva traza."""
        trace_id = self._generate_trace_id()
        span_id = self._generate_span_id()

        trace = Trace(
            trace_id=trace_id,
            root_span_id=span_id,
            resource={
                "service.name": self.service_name,
                "service.version": self.service_version,
                "telemetry.sdk.name": "lilith-tracer",
                "telemetry.sdk.version": "1.0.0",
            },
        )

        root_span = Span(
            trace_id=trace_id,
            span_id=span_id,
            parent_id=None,
            name=name,
            kind=SpanKind.SERVER,
            start_time=datetime.utcnow().isoformat(),
            attributes=attributes or {},
        )

        trace.spans[span_id] = root_span
        self.active_traces[trace_id] = trace

        # Set context
        _current_trace.set(trace)
        _current_span.set(root_span)

        return trace

    def start_span(
        self,
        name: str,
        kind: SpanKind = SpanKind.INTERNAL,
        attributes: Optional[Dict[str, Any]] = None,
    ) -> Span:
        """Inicia un nuevo span."""
        current = _current_span.get()
        trace = _current_trace.get()

        if not trace:
            # Auto-start trace
            trace = self.start_trace(name, attributes)
            return trace.spans[trace.root_span_id]

        span_id = self._generate_span_id()
        parent_id = current.span_id if current else trace.root_span_id

        span = Span(
            trace_id=trace.trace_id,
            span_id=span_id,
            parent_id=parent_id,
            name=name,
            kind=kind,
            start_time=datetime.utcnow().isoformat(),
            attributes=attributes or {},
        )

        trace.spans[span_id] = span
        _current_span.set(span)

        return span

    def end_span(
        self,
        span: Optional[Span] = None,
        status: SpanStatus = SpanStatus.OK,
        attributes: Optional[Dict[str, Any]] = None,
    ):
        """Finaliza un span."""
        if span is None:
            span = _current_span.get()

        if not span:
            return

        span.end_time = datetime.utcnow().isoformat()
        span.status = status

        if attributes:
            span.attributes.update(attributes)

        # Volver al span padre
        trace = self.active_traces.get(span.trace_id)
        if trace and span.parent_id:
            parent = trace.spans.get(span.parent_id)
            if parent:
                _current_span.set(parent)

    def end_trace(self, trace_id: Optional[str] = None):
        """Finaliza una traza."""
        if trace_id is None:
            trace = _current_trace.get()
            if trace:
                trace_id = trace.trace_id

        if not trace_id or trace_id not in self.active_traces:
            return

        trace = self.active_traces[trace_id]
        trace.end_time = datetime.utcnow().isoformat()

        # Finalizar spans abiertos
        for span in trace.spans.values():
            if not span.end_time:
                self.end_span(span)

        # Mover a completadas
        self.completed_traces.append(trace)
        if len(self.completed_traces) > self.max_completed_traces:
            self.completed_traces = self.completed_traces[-self.max_completed_traces :]

        del self.active_traces[trace_id]

        # Exportar
        self._export_trace(trace)

        # Clear context
        _current_trace.set(None)
        _current_span.set(None)

    def add_event(
        self,
        name: str,
        attributes: Optional[Dict[str, Any]] = None,
        span: Optional[Span] = None,
    ):
        """Añade un evento al span actual."""
        if span is None:
            span = _current_span.get()

        if not span:
            return

        event = {
            "name": name,
            "timestamp": datetime.utcnow().isoformat(),
            "attributes": attributes or {},
        }

        span.events.append(event)

    def add_link(
        self,
        trace_id: str,
        span_id: str,
        attributes: Optional[Dict[str, Any]] = None,
        span: Optional[Span] = None,
    ):
        """Añade un link a otra traza."""
        if span is None:
            span = _current_span.get()

        if not span:
            return

        link = {
            "trace_id": trace_id,
            "span_id": span_id,
            "attributes": attributes or {},
        }

        span.links.append(link)

    def get_current_span(self) -> Optional[Span]:
        """Obtiene el span actual."""
        return _current_span.get()

    def get_current_trace(self) -> Optional[Trace]:
        """Obtiene la traza actual."""
        return _current_trace.get()

    def get_trace(self, trace_id: str) -> Optional[Trace]:
        """Obtiene una traza por ID."""
        if trace_id in self.active_traces:
            return self.active_traces[trace_id]

        for trace in self.completed_traces:
            if trace.trace_id == trace_id:
                return trace

        return None

    def get_traces(
        self,
        limit: int = 100,
        service_name: Optional[str] = None,
        operation: Optional[str] = None,
    ) -> List[Trace]:
        """Obtiene trazas con filtros opcionales."""
        traces = list(self.active_traces.values()) + self.completed_traces

        if service_name:
            traces = [
                t for t in traces if t.resource.get("service.name") == service_name
            ]

        if operation:
            traces = [
                t for t in traces if any(s.name == operation for s in t.spans.values())
            ]

        # Ordenar por tiempo descendente
        traces.sort(key=lambda t: t.start_time, reverse=True)

        return traces[:limit]

    def register_export_handler(self, handler: Callable[[Trace], None]):
        """Registra un handler para exportar trazas."""
        self.export_handlers.append(handler)

    def _export_trace(self, trace: Trace):
        """Exporta una traza a handlers registrados."""
        for handler in self.export_handlers:
            try:
                handler(trace)
            except Exception as e:
                logger.error(f"Export handler error: {e}")

        # Guardar en disco
        self._save_trace(trace)

    def _save_trace(self, trace: Trace):
        """Guarda una traza en disco."""
        try:
            filename = (
                f"trace_{trace.trace_id}_{datetime.utcnow().strftime('%Y%m%d')}.json"
            )
            filepath = self.storage_path / filename

            data = {
                "trace_id": trace.trace_id,
                "start_time": trace.start_time,
                "end_time": trace.end_time,
                "resource": trace.resource,
                "spans": [
                    {
                        "span_id": s.span_id,
                        "parent_id": s.parent_id,
                        "name": s.name,
                        "kind": s.kind.value,
                        "start_time": s.start_time,
                        "end_time": s.end_time,
                        "status": s.status.value,
                        "attributes": s.attributes,
                        "events": s.events,
                        "links": s.links,
                    }
                    for s in trace.spans.values()
                ],
            }

            with open(filepath, "w") as f:
                json.dump(data, f, indent=2)

        except Exception as e:
            logger.error(f"Error saving trace: {e}")

    def _generate_trace_id(self) -> str:
        """Genera ID de traza."""
        return f"{uuid.uuid4().hex:032x}"

    def _generate_span_id(self) -> str:
        """Genera ID de span."""
        return f"{uuid.uuid4().hex:016x}"


@contextmanager
def trace_span(
    tracer: Tracer,
    name: str,
    kind: SpanKind = SpanKind.INTERNAL,
    attributes: Optional[Dict[str, Any]] = None,
):
    """Context manager para spans."""
    span = tracer.start_span(name, kind, attributes)
    try:
        yield span
        tracer.end_span(span, SpanStatus.OK)
    except Exception as e:
        tracer.end_span(
            span, SpanStatus.ERROR, {"error": str(e), "error.type": type(e).__name__}
        )
        raise


# Singleton
tracer_instance: Optional[Tracer] = None


def get_tracer(service_name: str = "lilith", service_version: str = "5.0.0") -> Tracer:
    """Obtiene el singleton del Tracer."""
    global tracer_instance
    if tracer_instance is None:
        tracer_instance = Tracer(service_name, service_version)
    return tracer_instance
