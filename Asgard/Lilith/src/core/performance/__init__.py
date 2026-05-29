"""
Performance Module - Monitoreo y optimización

v5.0: Métricas en tiempo real, alertas y auto-optimización.
"""
from .monitor import (
    PerformanceMetrics,
    PerformanceMonitor,
    TimingContext,
    get_performance_monitor,
)

__all__ = [
    "PerformanceMonitor",
    "PerformanceMetrics",
    "TimingContext",
    "get_performance_monitor",
]
