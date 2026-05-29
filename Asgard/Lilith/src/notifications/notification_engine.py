"""
Lilith v2.3 — Fase B: Motor de notificaciones proactivas.
Ejecuta 4 monitores cada 60s y escribe en NotificationStore; emite notification_new por callback.
"""
import logging
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

from .notification_store import NotificationStore

logger = logging.getLogger("NotificationEngine")

CONTEXT_MAX = 262_000
CONTEXT_80_PCT = 209_600  # 80% de 262k
INACTIVITY_HOURS = 2
MIN_SESSIONS_FOR_INSIGHT = 5
MIN_SESSIONS_SAME_THEME = 3


class NotificationEngine:
    def __init__(
        self,
        base_path: Optional[Path] = None,
        get_token_stats: Optional[Callable[[], Dict[str, Any]]] = None,
        send_event: Optional[Callable[[Dict[str, Any]], None]] = None,
    ):
        if base_path is None:
            base_path = Path(__file__).resolve().parent.parent.parent
        self.base_path = Path(base_path)
        self._store = NotificationStore(self.base_path)
        self._get_token_stats = get_token_stats or (lambda: {})
        self._send_event = send_event or (lambda _: None)

    def run_once(self) -> None:
        """Ejecuta los 4 monitores una vez. Llamar cada 60s desde el Core."""
        try:
            self._run_error_pattern_monitor()
            self._run_token_usage_monitor()
            self._run_inactivity_monitor()
            self._run_memory_insight_monitor()
        except Exception as e:
            logger.warning("NotificationEngine run_once: %s", e)

    def _emit(self, item: Dict[str, Any]) -> None:
        payload = {
            "type": "notification_new",
            "id": item.get("id"),
            "tipo": item.get("tipo"),
            "mensaje": item.get("mensaje"),
        }
        try:
            self._send_event(payload)
        except Exception as e:
            logger.warning("Send notification event: %s", e)

    def _load_json(self, path: Path, default: Any = None):
        if default is None:
            default = []
        if not path.exists():
            return default
        try:
            with open(path, "r", encoding="utf-8") as f:
                import json

                return json.load(f)
        except Exception as e:
            logger.debug("Load %s: %s", path, e)
            return default

    def _run_error_pattern_monitor(self) -> None:
        for base in ("memory", "Memory"):
            root = self.base_path / base
            if not root.exists():
                continue
            err_path = root / "procedural" / "error_history.json"
            if not err_path.exists():
                continue
            raw = self._load_json(err_path, [])
            errors = (
                raw
                if isinstance(raw, list)
                else ([raw] if isinstance(raw, dict) else [])
            )
            for e in errors:
                rec = e.get("recurrencias") or 0
                if rec < 3:
                    continue
                err_text = (e.get("error") or "")[:80]
                ref_id = f"err:{err_text}"
                if self._store.already_notified_today(ref_id):
                    continue
                soluciones = e.get("soluciones") or []
                sol = (
                    (soluciones[0][:200] + "…")
                    if soluciones and len(soluciones[0]) > 200
                    else (soluciones[0] if soluciones else "—")
                )
                mensaje = f"⚠️ Error recurrente: {err_text} ha ocurrido {rec} veces. Última solución: {sol}"
                item = self._store.add("error_recurrente", mensaje, ref_id=ref_id)
                logger.info(
                    "Notification created: error_recurrente (ref_id=%s)",
                    ref_id[:50] if ref_id else "",
                )
                self._emit(item)
            break

    def _run_token_usage_monitor(self) -> None:
        ref_id = "token_80"
        if self._store.already_notified_today(ref_id):
            return
        try:
            stats = self._get_token_stats()
        except Exception:
            return
        pct = stats.get("percentage") or 0
        if pct < 80:
            return
        mensaje = f"⚡ Contexto al {pct:.0f}%. Considera nueva sesión."
        item = self._store.add("token_usage", mensaje, ref_id=ref_id)
        self._emit(item)

    def _run_inactivity_monitor(self) -> None:
        ref_id = "inactivity_2h"
        if self._store.already_notified_today(ref_id):
            return
        for base in ("Memory", "memory"):
            stats_path = self.base_path / base / "stats.json"
            if not stats_path.exists():
                continue
            data = self._load_json(stats_path, {})
            last = data.get("last_activity_iso")
            if not last:
                break
            try:
                dt = datetime.fromisoformat(last.replace("Z", "+00:00"))
            except Exception:
                break
            if (
                datetime.now(timezone.utc) - dt
            ).total_seconds() < INACTIVITY_HOURS * 3600:
                break
            patterns_path = self.base_path / "memory" / "procedural" / "patterns.json"
            if not patterns_path.exists():
                break
            patterns = self._load_json(patterns_path, {})
            if not patterns:
                break
            task = (
                list(patterns.keys())[0]
                if isinstance(patterns, dict)
                else str(patterns)[:50]
            )
            mensaje = f"💤 Sin actividad 2h. Tarea pendiente: {task}"
            item = self._store.add("inactivity", mensaje, ref_id=ref_id)
            self._emit(item)
            break

    def _run_memory_insight_monitor(self) -> None:
        summaries: List[Dict[str, Any]] = []
        for base in ("Memory", "memory"):
            sessions_dir = self.base_path / base / "sessions"
            if not sessions_dir.exists():
                continue
            for p in sessions_dir.glob("*_summary.json"):
                data = self._load_json(p, {})
                if isinstance(data, dict) and data.get("temas"):
                    summaries.append(data)
            if len(summaries) >= MIN_SESSIONS_FOR_INSIGHT:
                break
        if len(summaries) < MIN_SESSIONS_FOR_INSIGHT:
            return
        from collections import Counter

        all_temas: List[str] = []
        for s in summaries:
            temas = s.get("temas") or []
            if isinstance(temas, list):
                all_temas.extend(temas)
        if not all_temas:
            return
        counter = Counter(all_temas)
        for tema, count in counter.most_common(5):
            if count < MIN_SESSIONS_SAME_THEME:
                continue
            ref_id = f"insight:{tema[:30]}"
            if self._store.already_notified_today(ref_id):
                continue
            mensaje = f"🧠 Patrón detectado: trabajas frecuentemente en «{tema}». ¿Quieres que lo agregue a tu perfil?"
            item = self._store.add("memory_insight", mensaje, ref_id=ref_id)
            self._emit(item)
            return
        return
