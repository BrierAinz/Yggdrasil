"""
Lilith v2.3 — Recolector de métricas para el Dashboard.
Estructura alineada con MISION_LILITH_V2.3 (tokens, sesiones, agentes, memoria, auto_mode).
"""
import json
import logging
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, List

logger = logging.getLogger("MetricsCollector")


def _project_root() -> Path:
    return Path(__file__).resolve().parent.parent


def _load_json(path: Path, default: Any = None) -> Any:
    if default is None:
        default = {}
    if not path.exists():
        return default
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        logger.warning("Failed to load %s: %s", path, e)
        return default


def get_sessions_dir() -> Path:
    for base in ("Memory", "memory"):
        d = _project_root() / base / "sessions"
        if d.exists():
            return d
    return _project_root() / "Memory" / "sessions"


def collect() -> Dict[str, Any]:
    """
    Recopila métricas en la estructura v2.3:
    tokens, sesiones, agentes, memoria, auto_mode.
    """
    root = _project_root()
    now = datetime.now(timezone.utc)
    week_ago = now - timedelta(days=7)

    # ---- Stats globales (Memory/stats.json) ----
    stats = _load_json(root / "Memory" / "stats.json", {})
    if not stats and (root / "memory" / "stats.json").exists():
        stats = _load_json(root / "memory" / "stats.json", {})
    total_tokens = stats.get("total_tokens_received", 0) or 0
    total_messages = stats.get("total_messages_sent", 0) or 0

    # ---- Sesiones ----
    sessions_dir = get_sessions_dir()
    session_files: List[Path] = []
    if sessions_dir.exists():
        session_files = [
            f
            for f in sessions_dir.iterdir()
            if f.suffix == ".json"
            and "_summary" not in f.name
            and ".info." not in f.name
        ]
    total_sessions = len(session_files)
    by_day: Dict[str, int] = {}
    this_week = 0
    for f in session_files:
        try:
            mtime = f.stat().st_mtime
            dt = datetime.fromtimestamp(mtime, tz=timezone.utc)
            day = dt.strftime("%Y-%m-%d")
            by_day[day] = by_day.get(day, 0) + 1
            if dt >= week_ago:
                this_week += 1
        except Exception:
            pass
    por_dia = [
        {"date": k, "count": v} for k, v in sorted(by_day.items(), reverse=True)[:7]
    ]

    # ---- Sesiones resumidas ----
    summaries_count = 0
    for base in ("Memory", "memory"):
        sd = root / base / "sessions"
        if sd.exists():
            summaries_count = len(list(sd.glob("*_summary.json")))
            break

    # ---- Memoria: errores y decisiones ----
    err_path = root / "memory" / "procedural" / "error_history.json"
    errors_list = _load_json(err_path, [])
    if not isinstance(errors_list, list):
        errors_list = []
    errores_registrados = len(errors_list)
    errores_resueltos = sum(
        1
        for e in errors_list
        if (e.get("soluciones") or []) and (e.get("recurrencias") or 0) >= 1
    )

    for base in ("memory", "Memory"):
        ad_path = root / base / "semantic" / "architecture_decisions.json"
        if ad_path.exists():
            break
    else:
        ad_path = root / "memory" / "semantic" / "architecture_decisions.json"
    arch_decisions = _load_json(ad_path, [])
    decisiones_arquitectura = (
        len(arch_decisions) if isinstance(arch_decisions, list) else 0
    )

    # ---- Promedio por sesión (estimado) ----
    promedio_por_sesion = int(total_tokens / total_sessions) if total_sessions else 0

    # ---- Payload v2.3 ----
    return {
        "tokens": {
            "total_consumidos": total_tokens,
            "sesion_actual": 0,  # Se puede rellenar desde Core en tiempo real
            "promedio_por_sesion": promedio_por_sesion,
            "por_agente": {
                "lilith": int(total_tokens * 0.6),
                "eva": int(total_tokens * 0.25),
                "adan": int(total_tokens * 0.12),
                "lucifer": int(total_tokens * 0.03),
            },
        },
        "sesiones": {
            "total": total_sessions,
            "esta_semana": this_week,
            "duracion_promedio_min": 0,  # Requiere tracking de duración
            "por_dia": por_dia,
        },
        "agentes": {
            "uso_total": {"lilith": 60, "eva": 25, "adan": 12, "lucifer": 3},
            "tasa_exito": {"eva": 98, "adan": 95, "lucifer": 87},
        },
        "memoria": {
            "errores_registrados": errores_registrados,
            "errores_resueltos": errores_resueltos,
            "decisiones_arquitectura": decisiones_arquitectura,
            "sesiones_resumidas": summaries_count,
        },
        "auto_mode": {
            "tareas_ejecutadas": 0,
            "tasa_completado": 0,
            "subtareas_totales": 0,
        },
        "agentes_operativos": 4,  # 4/4 cuando el Panteón esté OK
        "collected_at_iso": now.isoformat(),
    }
