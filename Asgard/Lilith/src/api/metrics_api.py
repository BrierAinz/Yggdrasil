"""
Lilith 4.1 — A.2 Métricas Prometheus.
Endpoint GET /metrics en formato texto Prometheus.
"""
from fastapi import APIRouter
from fastapi.responses import PlainTextResponse

router = APIRouter(tags=["telemetry"])


@router.get("/metrics", response_class=PlainTextResponse)
async def prometheus_metrics():
    """Expone métricas en formato Prometheus para scraping."""
    from src.telemetry.metrics import get_metrics_text

    return PlainTextResponse(
        content=get_metrics_text(),
        media_type="text/plain; version=0.0.4; charset=utf-8",
    )
