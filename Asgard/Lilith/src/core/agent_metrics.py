"""
AgentMetrics — Métricas de rendimiento de agentes en tiempo real.
Registra latencia, éxitos, fallos y caché hits por herramienta/agente.
Endpoint de consulta: GET /api/agents/health
"""
import logging
import time
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Dict, List, Optional

logger = logging.getLogger("lilith.agent_metrics")

_PERCENTILE_WINDOW = 50  # últimas N llamadas para percentiles de latencia


@dataclass
class ToolStats:
    tool_name: str
    total_calls: int = 0
    success_count: int = 0
    error_count: int = 0
    cache_hits: int = 0
    total_latency_ms: float = 0.0
    recent_latencies: List[float] = field(default_factory=list)
    last_error: str = ""
    last_call_ts: float = 0.0

    @property
    def success_rate(self) -> float:
        if self.total_calls == 0:
            return 1.0
        return self.success_count / self.total_calls

    @property
    def avg_latency_ms(self) -> float:
        if self.success_count == 0:
            return 0.0
        return self.total_latency_ms / self.success_count

    @property
    def p95_latency_ms(self) -> float:
        lats = sorted(self.recent_latencies)
        if not lats:
            return 0.0
        idx = max(0, int(len(lats) * 0.95) - 1)
        return lats[idx]

    def to_dict(self) -> dict:
        return {
            "tool": self.tool_name,
            "calls": self.total_calls,
            "success_rate": round(self.success_rate, 3),
            "errors": self.error_count,
            "cache_hits": self.cache_hits,
            "avg_latency_ms": round(self.avg_latency_ms, 1),
            "p95_latency_ms": round(self.p95_latency_ms, 1),
            "last_error": self.last_error[:120] if self.last_error else "",
            "last_call_ts": self.last_call_ts,
        }


class AgentMetrics:
    """
    Singleton global de métricas de agentes.
    Thread-safe para reads; writes son atómicos (GIL de CPython).
    """

    def __init__(self):
        self._stats: Dict[str, ToolStats] = defaultdict(
            lambda: ToolStats(tool_name="unknown")
        )
        self._active_calls: Dict[str, int] = {}
        self._last_status: Dict[str, str] = {}

    def _get(self, tool_name: str) -> ToolStats:
        if tool_name not in self._stats:
            self._stats[tool_name] = ToolStats(tool_name=tool_name)
        return self._stats[tool_name]

    def record_call_start(self, tool_name: str) -> None:
        """Marca el inicio de una llamada a un tool/agente."""
        self._active_calls[tool_name] = self._active_calls.get(tool_name, 0) + 1
        self._last_status[tool_name] = "processing"

    def record_call_end(self, tool_name: str, success: bool) -> None:
        """Marca el fin de una llamada a un tool/agente."""
        self._active_calls[tool_name] = max(0, self._active_calls.get(tool_name, 0) - 1)
        if self._active_calls.get(tool_name, 0) == 0:
            self._last_status[tool_name] = "idle" if success else "error"

    def get_status(self, tool_name: Optional[str] = None) -> dict:
        """Devuelve el estado en tiempo real de un tool o de todos."""
        if tool_name:
            return {
                "tool": tool_name,
                "status": self._last_status.get(tool_name, "idle"),
                "active_calls": self._active_calls.get(tool_name, 0),
            }
        return {
            "tools": [
                {
                    "tool": name,
                    "status": self._last_status.get(name, "idle"),
                    "active_calls": self._active_calls.get(name, 0),
                }
                for name in sorted(self._stats.keys())
            ]
        }

    def get_stats_with_status(self, tool_name: Optional[str] = None) -> dict:
        """Devuelve stats + estado en tiempo real."""
        stats = self.get_stats(tool_name)
        if tool_name:
            s = self._stats.get(tool_name)
            if s:
                stats["status"] = self._last_status.get(tool_name, "idle")
                stats["active_calls"] = self._active_calls.get(tool_name, 0)
            return stats
        # Para todos: enriquecer cada tool
        status_map = {t["tool"]: t for t in self.get_status().get("tools", [])}
        for item in stats.get("tools", []):
            st = status_map.get(item["tool"], {})
            item["status"] = st.get("status", "idle")
            item["active_calls"] = st.get("active_calls", 0)
        return stats

    def record_call(
        self,
        tool_name: str,
        latency_ms: float,
        success: bool,
        error_msg: str = "",
        cache_hit: bool = False,
    ) -> None:
        """Registra el resultado de una llamada a un tool/agente."""
        s = self._get(tool_name)
        s.total_calls += 1
        s.last_call_ts = time.time()
        if cache_hit:
            s.cache_hits += 1
            return  # cache hits no cuentan para latencias de ejecución real
        if success:
            s.success_count += 1
            s.total_latency_ms += latency_ms
            s.recent_latencies.append(latency_ms)
            if len(s.recent_latencies) > _PERCENTILE_WINDOW:
                s.recent_latencies = s.recent_latencies[-_PERCENTILE_WINDOW:]
        else:
            s.error_count += 1
            if error_msg:
                s.last_error = error_msg[:200]

    def get_stats(self, tool_name: Optional[str] = None) -> dict:
        """Devuelve stats de un tool o de todos."""
        if tool_name:
            s = self._stats.get(tool_name)
            return s.to_dict() if s else {"tool": tool_name, "calls": 0}
        return {
            "tools": [
                s.to_dict()
                for s in sorted(self._stats.values(), key=lambda x: -x.total_calls)
            ],
            "total_tools_tracked": len(self._stats),
        }

    def health_summary(self) -> dict:
        """Resumen de salud: herramientas con success_rate < 0.7 o p95 > 10s."""
        degraded = []
        for s in self._stats.values():
            if s.total_calls < 2:
                continue
            issues = []
            if s.success_rate < 0.7:
                issues.append(f"success_rate={s.success_rate:.0%}")
            if s.p95_latency_ms > 10_000:
                issues.append(f"p95={s.p95_latency_ms/1000:.1f}s")
            if issues:
                degraded.append({"tool": s.tool_name, "issues": issues, **s.to_dict()})
        return {
            "healthy": len(degraded) == 0,
            "degraded_tools": degraded,
            "all_stats": self.get_stats(),
        }


# ─── Singleton global ─────────────────────────────────────────────────────────

_metrics = AgentMetrics()


def get_metrics() -> AgentMetrics:
    return _metrics
