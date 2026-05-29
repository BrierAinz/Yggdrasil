"""
Audit API - Endpoints para consulta y gestión de auditoría

v4.2.8: API para consultar eventos de auditoría y exportar datos.
"""
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Optional

from fastapi import APIRouter, HTTPException, Query, Response
from pydantic import BaseModel, Field
from src.core.audit import EventType, get_auditor

router = APIRouter(prefix="/api/audit", tags=["audit"])


# Models


class AuditQueryParams(BaseModel):
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    event_types: Optional[List[str]] = None
    actor: Optional[str] = None
    resource: Optional[str] = None
    status: Optional[str] = None
    limit: int = Field(default=100, ge=1, le=1000)
    offset: int = Field(default=0, ge=0)


class AuditEventResponse(BaseModel):
    timestamp: str
    event_type: str
    actor: str
    resource: str
    action: str
    status: str
    details: dict
    ip_address: Optional[str]
    request_id: Optional[str]


class AuditStatsResponse(BaseModel):
    total_files: int
    total_size_bytes: int
    total_size_mb: float
    today_events: int
    retention_days: int
    base_path: str


# Endpoints


@router.get("/events")
async def list_events(
    start_date: Optional[datetime] = Query(None),
    end_date: Optional[datetime] = Query(None),
    event_type: Optional[str] = Query(None),
    actor: Optional[str] = Query(None),
    resource: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0),
):
    """Lista eventos de auditoría con filtros."""
    auditor = get_auditor()

    # Convertir string de tipos a lista de EventType
    event_types = None
    if event_type:
        try:
            event_types = [EventType(event_type)]
        except ValueError:
            raise HTTPException(
                status_code=400, detail=f"Tipo de evento inválido: {event_type}"
            )

    events = auditor.query(
        start_date=start_date,
        end_date=end_date,
        event_types=event_types,
        actor=actor,
        resource=resource,
        status=status,
        limit=limit,
        offset=offset,
    )

    return {
        "success": True,
        "data": [e.to_dict() for e in events],
        "count": len(events),
        "filters": {
            "start_date": start_date.isoformat() if start_date else None,
            "end_date": end_date.isoformat() if end_date else None,
            "event_type": event_type,
            "actor": actor,
            "resource": resource,
            "status": status,
        },
    }


@router.get("/events/types")
async def get_event_types():
    """Obtiene todos los tipos de eventos disponibles."""
    types = [
        {"value": et.value, "label": et.value.replace("_", " ").title()}
        for et in EventType
    ]

    # Agrupar por categoría
    from src.core.audit.events import EventCategory

    categories = {
        "security": [et.value for et in EventCategory.SECURITY],
        "operational": [et.value for et in EventCategory.OPERATIONAL],
        "data": [et.value for et in EventCategory.DATA],
        "system": [et.value for et in EventCategory.SYSTEM],
    }

    return {"success": True, "data": {"types": types, "categories": categories}}


@router.get("/stats")
async def get_stats():
    """Obtiene estadísticas del sistema de auditoría."""
    auditor = get_auditor()
    stats = auditor.get_stats()

    return {"success": True, "data": stats}


@router.get("/export/csv")
async def export_csv(
    start_date: Optional[datetime] = Query(None),
    end_date: Optional[datetime] = Query(None),
    event_type: Optional[str] = Query(None),
    actor: Optional[str] = Query(None),
):
    """Exporta eventos a CSV."""
    auditor = get_auditor()

    # Generar nombre de archivo
    timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    output_path = Path(f"/tmp/audit_export_{timestamp}.csv")

    event_types = None
    if event_type:
        try:
            event_types = [EventType(event_type)]
        except ValueError:
            raise HTTPException(
                status_code=400, detail=f"Tipo de evento inválido: {event_type}"
            )

    count = auditor.export_csv(
        output_path,
        start_date=start_date,
        end_date=end_date,
        event_types=event_types,
        actor=actor,
    )

    # Leer archivo y devolver
    with open(output_path, "rb") as f:
        content = f.read()

    output_path.unlink(missing_ok=True)

    return Response(
        content=content,
        media_type="text/csv",
        headers={
            "Content-Disposition": f"attachment; filename=audit_export_{timestamp}.csv"
        },
    )


@router.get("/export/json")
async def export_json(
    start_date: Optional[datetime] = Query(None),
    end_date: Optional[datetime] = Query(None),
    event_type: Optional[str] = Query(None),
    actor: Optional[str] = Query(None),
):
    """Exporta eventos a JSON."""
    auditor = get_auditor()

    timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    output_path = Path(f"/tmp/audit_export_{timestamp}.json")

    event_types = None
    if event_type:
        try:
            event_types = [EventType(event_type)]
        except ValueError:
            raise HTTPException(
                status_code=400, detail=f"Tipo de evento inválido: {event_type}"
            )

    count = auditor.export_json(
        output_path,
        start_date=start_date,
        end_date=end_date,
        event_types=event_types,
        actor=actor,
    )

    with open(output_path, "rb") as f:
        content = f.read()

    output_path.unlink(missing_ok=True)

    return Response(
        content=content,
        media_type="application/json",
        headers={
            "Content-Disposition": f"attachment; filename=audit_export_{timestamp}.json"
        },
    )


@router.post("/maintenance/compress")
async def compress_old_files():
    """Comprime archivos de auditoría antiguos."""
    auditor = get_auditor()
    auditor.compress_old()

    return {"success": True, "message": "Compresión de archivos antiguos iniciada"}


@router.post("/maintenance/cleanup")
async def cleanup_old_files():
    """Limpia archivos de auditoría según retención configurada."""
    auditor = get_auditor()
    auditor.cleanup_old()

    return {"success": True, "message": "Limpieza de archivos antiguos completada"}


@router.get("/recent")
async def get_recent_events(
    minutes: int = Query(60, ge=1, le=1440), limit: int = Query(100, ge=1, le=500)
):
    """Obtiene eventos recientes (últimos N minutos)."""
    auditor = get_auditor()

    end_date = datetime.utcnow()
    start_date = end_date - timedelta(minutes=minutes)

    events = auditor.query(start_date=start_date, end_date=end_date, limit=limit)

    return {
        "success": True,
        "data": [e.to_dict() for e in events],
        "period": {
            "start": start_date.isoformat(),
            "end": end_date.isoformat(),
            "minutes": minutes,
        },
    }


@router.get("/by-resource/{resource}")
async def get_events_by_resource(resource: str, limit: int = Query(50, ge=1, le=500)):
    """Obtiene eventos para un recurso específico."""
    auditor = get_auditor()

    events = auditor.query(resource=resource, limit=limit)

    return {
        "success": True,
        "data": [e.to_dict() for e in events],
        "resource": resource,
    }


@router.get("/by-actor/{actor}")
async def get_events_by_actor(actor: str, limit: int = Query(50, ge=1, le=500)):
    """Obtiene eventos para un actor específico."""
    auditor = get_auditor()

    events = auditor.query(actor=actor, limit=limit)

    return {"success": True, "data": [e.to_dict() for e in events], "actor": actor}
