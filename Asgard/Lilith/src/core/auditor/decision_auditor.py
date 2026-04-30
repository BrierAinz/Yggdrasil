"""
Misión 3.4 E.3 + Auditoría v2 (Misión A–Z).
Registra decisiones en Data/decision_audit_YYYY-MM-DD.jsonl (un archivo por día, UTC).
Rotación por fecha, threading.Lock, append_decision() central, _prune_old_audit_files().
No se propaga excepción al flujo principal (P).

decision_type (W): plan | step_executed | classify_important | confirm_requested | confirm_resolved.
  - plan: Planner (learned_plan, classifier, intent_patterns, matching_learning, fallback_lucifer).
  - step_executed: PlanExecutor tras cada paso.
  - classify_important: auto_learn classifier (heuristic_then_llm).
  - confirm_requested: Discord crea confirmación pendiente (acción peligrosa).
  - confirm_resolved: Discord resuelve (confirmed | cancelled | timeout | error).

Zona horaria: Los nombres de archivo usan siempre la fecha en UTC (YYYY-MM-DD). Una decisión
a las 22:00 en Ciudad de México (UTC-6) se escribe en el archivo del día siguiente en UTC.
Para GET /api/discord/audit: el parámetro date= debe interpretarse en UTC salvo que la API
acepte tz= (ej. America/Mexico_City) y convierta "hoy" local a el/los archivo(s) UTC correspondientes.
"""
import json
import logging
import re
import threading
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger("DecisionAuditor")

_WRITE_LOCK = threading.Lock()
_LAST_PRUNE_DATE: Optional[date] = None
_LEGACY_RENAMED = False

DEFAULT_AUDIT_RETENTION_DAYS = 30
DEFAULT_AUDIT_DIR = "Data"
AUDIT_FILENAME_PREFIX = "decision_audit"
MAX_MESSAGE_CHARS = 2000
MAX_REASON_CHARS = 500
MAX_PAYLOAD_STRING_CHARS = (
    2000  # truncado recursivo en payload (evita bloats tipo resultado web masivo)
)
MAX_PAYLOAD_DEPTH = 6
MAX_PAYLOAD_LIST_LEN = 50


def _project_base() -> Path:
    """Raíz del proyecto (carpeta que contiene Backend)."""
    return Path(__file__).resolve().parent.parent.parent.parent


def _audit_config() -> Dict[str, Any]:
    """Carga Config/memory.json para audit_retention_days, audit_dir (y legacy audit_max_*)."""
    try:
        from src.core.json_safe import safe_load

        out = safe_load(_project_base() / "Config" / "memory.json", default={})
        return out if isinstance(out, dict) else {}
    except Exception:
        return {}


def _audit_base_dir() -> Path:
    """Directorio donde se escriben los JSONL de auditoría (por defecto Data)."""
    cfg = _audit_config()
    name = (cfg.get("audit_dir") or DEFAULT_AUDIT_DIR).strip() or DEFAULT_AUDIT_DIR
    base = _project_base()
    path = base / name
    path.mkdir(parents=True, exist_ok=True)
    return path


def _audit_path_for_date(d: date) -> Path:
    """Ruta del archivo de auditoría para la fecha dada (UTC)."""
    return _audit_base_dir() / f"{AUDIT_FILENAME_PREFIX}_{d.isoformat()}.jsonl"


def _audit_path_for_today() -> Path:
    """Ruta del archivo de auditoría de hoy (UTC)."""
    return _audit_path_for_date(datetime.now(timezone.utc).date())


def _sanitize_payload(obj: Any, depth: int = 0) -> Any:
    """
    Recorre payload (dict/list) y trunca strings largos para evitar líneas de MB.
    Limita profundidad y longitud de listas. No modifica el dict original; devuelve copia saneada.
    """
    if depth > MAX_PAYLOAD_DEPTH:
        return "<max_depth>"
    if isinstance(obj, dict):
        return {k: _sanitize_payload(v, depth + 1) for k, v in obj.items()}
    if isinstance(obj, list):
        if len(obj) > MAX_PAYLOAD_LIST_LEN:
            obj = obj[:MAX_PAYLOAD_LIST_LEN] + [
                f"<truncated {len(obj) - MAX_PAYLOAD_LIST_LEN} more>"
            ]
        return [_sanitize_payload(x, depth + 1) for x in obj]
    if isinstance(obj, str):
        if len(obj) > MAX_PAYLOAD_STRING_CHARS:
            return obj[:MAX_PAYLOAD_STRING_CHARS] + "..."
        return obj
    if isinstance(obj, (int, float, bool, type(None))):
        return obj
    return str(obj)[:MAX_PAYLOAD_STRING_CHARS]


def _version() -> str:
    try:
        from src.core.version import LILITH_VERSION

        return LILITH_VERSION
    except Exception:
        return "3.4"


def _prune_old_audit_files() -> None:
    """
    Borra archivos decision_audit_YYYY-MM-DD.jsonl cuya fecha sea anterior a
    hoy - audit_retention_days. No usa el lock de escritura (solo listar/borrar).
    FileNotFoundError/OSError al borrar (p. ej. otro hilo ya lo borró) se capturan para no colapsar.
    """
    global _LAST_PRUNE_DATE
    base = _audit_base_dir()
    cfg = _audit_config()
    retention = (
        int(cfg.get("audit_retention_days") or 0) or DEFAULT_AUDIT_RETENTION_DAYS
    )
    today = datetime.now(timezone.utc).date()
    cutoff = today - timedelta(days=retention)
    pattern = re.compile(
        r"^" + re.escape(AUDIT_FILENAME_PREFIX) + r"_(\d{4}-\d{2}-\d{2})\.jsonl$"
    )
    removed = 0
    try:
        for f in base.iterdir():
            if not f.is_file():
                continue
            m = pattern.match(f.name)
            if not m:
                continue
            try:
                file_date = date.fromisoformat(m.group(1))
                if file_date < cutoff:
                    f.unlink()
                    removed += 1
            except (ValueError, OSError, FileNotFoundError) as e:
                # FileNotFoundError: otro hilo pudo borrarlo; condición de carrera inofensiva
                logger.debug("DecisionAuditor: skip prune %s: %s", f.name, e)
        if removed:
            logger.debug(
                "DecisionAuditor: pruned %d old audit files (retention_days=%d)",
                removed,
                retention,
            )
        _LAST_PRUNE_DATE = today
    except Exception as e:
        logger.debug("DecisionAuditor: prune_old_audit_files failed: %s", e)


def _maybe_prune_once_per_day() -> None:
    """Llama a _prune_old_audit_files() como máximo una vez por día (UTC)."""
    global _LAST_PRUNE_DATE
    today = datetime.now(timezone.utc).date()
    if _LAST_PRUNE_DATE is None or _LAST_PRUNE_DATE != today:
        _prune_old_audit_files()


def append_decision(
    decision_type: str,
    actor: str,
    payload: Dict[str, Any],
    *,
    reason: Optional[str] = None,
    message: Optional[str] = None,
    extra: Optional[Dict[str, Any]] = None,
) -> None:
    """
    Escribe una línea de auditoría en el archivo del día (UTC). Thread-safe (Lock).
    No propaga excepciones; fallos se registran con logger.debug.
    """
    if not (decision_type or "").strip() or not (actor or "").strip():
        logger.warning(
            "DecisionAuditor: append_decision requires decision_type and actor"
        )
        return
    if not isinstance(payload, dict):
        logger.warning("DecisionAuditor: payload must be a dict")
        return
    try:
        ts = datetime.now(timezone.utc).isoformat()
        payload_safe = _sanitize_payload(payload)
        entry = {
            "timestamp": ts,
            "version": _version(),
            "decision_type": (decision_type or "").strip(),
            "actor": (actor or "").strip(),
            "payload": payload_safe,
        }
        if message is not None:
            entry["message"] = (str(message) or "")[:MAX_MESSAGE_CHARS]
        if reason is not None:
            entry["reason"] = (str(reason) or "")[:MAX_REASON_CHARS]
        if extra:
            entry["extra"] = extra

        path = _audit_path_for_today()
        path.parent.mkdir(parents=True, exist_ok=True)
        with _WRITE_LOCK:
            global _LEGACY_RENAMED
            if not _LEGACY_RENAMED:
                legacy = path.parent / "decision_audit.jsonl"
                if legacy.exists() and legacy != path:
                    try:
                        legacy.rename(path.parent / "decision_audit_legacy.jsonl")
                        logger.debug(
                            "DecisionAuditor: renamed legacy decision_audit.jsonl to decision_audit_legacy.jsonl"
                        )
                    except Exception as e:
                        logger.debug("DecisionAuditor: legacy rename skipped: %s", e)
                _LEGACY_RENAMED = True
            with open(path, "a", encoding="utf-8") as f:
                f.write(json.dumps(entry, ensure_ascii=False) + "\n")
            _maybe_prune_once_per_day()
    except Exception as e:
        logger.debug("DecisionAuditor: append_decision failed: %s", e)


def log_plan_decision(
    message: str,
    decision_source: str,
    *,
    matched_intent: Optional[str] = None,
    plan_generated: Optional[List[str]] = None,
    reason: Optional[str] = None,
    extra: Optional[Dict[str, Any]] = None,
) -> None:
    """
    Registra una decisión del Planner. Delega en append_decision(decision_type="plan", ...).
    Compatible con todas las llamadas existentes desde planner.py.
    """
    payload = {
        "decision_source": decision_source,
    }
    if matched_intent is not None:
        payload["matched_intent"] = matched_intent
    if plan_generated is not None:
        payload["plan_generated"] = [str(t) for t in plan_generated[:20]]
    append_decision(
        decision_type="plan",
        actor="planner",
        payload=payload,
        reason=reason,
        message=(message or "")[:MAX_MESSAGE_CHARS] if message else None,
        extra=extra,
    )


def get_audit_events(
    for_date: Optional[date] = None,
    limit: int = 10,
) -> List[Dict[str, Any]]:
    """
    Lee las últimas `limit` líneas del archivo de auditoría para la fecha dada (UTC).
    for_date: None = hoy UTC. Devuelve lista de dicts (más recientes al final); vacía si no hay archivo.
    """
    d = for_date or datetime.now(timezone.utc).date()
    path = _audit_path_for_date(d)
    if not path.exists():
        return []
    events: List[Dict[str, Any]] = []
    try:
        with open(path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    obj = json.loads(line)
                    if isinstance(obj, dict):
                        events.append(obj)
                except Exception:
                    pass
        return events[-limit:] if len(events) > limit else events
    except Exception as e:
        logger.debug("DecisionAuditor: get_audit_events failed: %s", e)
        return []


def get_audit_file_path(for_date: Optional[date] = None) -> Path:
    """Ruta del archivo de auditoría para la fecha (para adjunto). for_date=None = hoy UTC."""
    d = for_date or datetime.now(timezone.utc).date()
    return _audit_path_for_date(d)


# ─── Legacy: solo para referencia o migración; no se usa en el camino crítico ───


def _audit_path() -> Path:
    """Alias a archivo de hoy (compatibilidad). Ya no se escribe en un solo archivo fijo."""
    return _audit_path_for_today()


def _parse_ts(ts: str) -> Optional[datetime]:
    try:
        if ts.endswith("Z"):
            ts = ts[:-1] + "+00:00"
        return datetime.fromisoformat(ts.replace("Z", "+00:00"))
    except Exception:
        return None


def _prune_audit() -> None:
    """
    Legacy: poda del archivo único (reescribe todo el archivo). Ya no se llama en append.
    Mantenido por si se desea ejecutar una última vez sobre decision_audit.jsonl antes de migrar.
    """
    path = _project_base() / DEFAULT_AUDIT_DIR / "decision_audit.jsonl"
    if not path.exists():
        return
    cfg = _audit_config()
    max_entries = int(cfg.get("audit_max_entries") or 0) or 5000
    max_days = int(cfg.get("audit_max_days") or 0) or 30
    cutoff = datetime.now(timezone.utc) - timedelta(days=max_days)
    try:
        lines = []
        with open(path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    obj = json.loads(line)
                    if isinstance(obj, dict):
                        ts = _parse_ts((obj.get("timestamp") or ""))
                        if ts and ts < cutoff:
                            continue
                        lines.append(obj)
                except Exception:
                    pass
        if len(lines) <= max_entries:
            return
        kept = lines[-max_entries:]
        with open(path, "w", encoding="utf-8") as f:
            for e in kept:
                f.write(json.dumps(e, ensure_ascii=False) + "\n")
        logger.debug("DecisionAuditor: legacy prune to %d entries", len(kept))
    except Exception as e:
        logger.debug("DecisionAuditor: legacy prune failed: %s", e)
