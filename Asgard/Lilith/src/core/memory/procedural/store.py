"""
Lilith 3.0 — Store de memoria procedimental.
Patrones y recetas aprendidos (persistencia JSON). Carga vía json_safe (nunca falla por JSON).
Misión 3.3 (C.2): archivo de patrones no usados en N días en store_old_patterns.json.
"""
import json
import logging
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger("ProceduralStore")

DEFAULT_ARCHIVE_DAYS = 30


def _parse_iso_ts(ts: Optional[str]) -> Optional[datetime]:
    if not ts:
        return None
    try:
        s = (ts or "").strip()
        if s.endswith("Z"):
            s = s[:-1] + "+00:00"
        return datetime.fromisoformat(s.replace("Z", "+00:00"))
    except Exception:
        return None


class ProceduralStore:
    """Almacén de patrones aprendidos (Fase 4). C.2: archiva patrones inactivos."""

    def __init__(self, base_path: Path):
        self.base_path = Path(base_path)
        self.store_dir = self.base_path / "memory" / "procedural_v3"
        self.store_dir.mkdir(parents=True, exist_ok=True)
        self.patterns_file = self.store_dir / "learned_patterns.json"
        self.archive_file = self.store_dir / "store_old_patterns.json"

    def _archive_old_patterns(
        self, max_days_unused: int = DEFAULT_ARCHIVE_DAYS
    ) -> None:
        """C.2: Mueve patrones no usados en max_days_unused días a store_old_patterns.json."""
        from ...json_safe import safe_load

        patterns = safe_load(self.patterns_file, default=[])
        if not isinstance(patterns, list) or len(patterns) == 0:
            return
        cutoff = datetime.now(timezone.utc) - timedelta(days=max_days_unused)
        active: List[Dict[str, Any]] = []
        to_archive: List[Dict[str, Any]] = []
        for p in patterns:
            if not isinstance(p, dict):
                continue
            last = _parse_iso_ts(p.get("last_used"))
            created = _parse_iso_ts(p.get("created_at"))
            ref = last or created
            if ref and ref < cutoff:
                to_archive.append(p)
            else:
                active.append(p)
        if not to_archive:
            return
        existing_archive = safe_load(self.archive_file, default=[])
        if not isinstance(existing_archive, list):
            existing_archive = []
        existing_archive.extend(to_archive)
        try:
            with open(self.archive_file, "w", encoding="utf-8") as f:
                json.dump(existing_archive, f, ensure_ascii=False, indent=2)
            with open(self.patterns_file, "w", encoding="utf-8") as f:
                json.dump(active, f, ensure_ascii=False, indent=2)
            logger.info(
                "ProceduralStore: archived %d pattern(s) unused for %d days",
                len(to_archive),
                max_days_unused,
            )
        except Exception as e:
            logger.warning("ProceduralStore: archive failed: %s", e)

    def list_patterns(
        self, intent_filter: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Devuelve patrones activos. C.2: archiva viejos antes. C.3: intent_filter opcional."""
        from ...json_safe import safe_load

        cfg_path = self.base_path / "Config" / "memory.json"
        cfg = safe_load(cfg_path, default={})
        max_days = int(cfg.get("procedural_archive_days") or 0) or DEFAULT_ARCHIVE_DAYS
        self._archive_old_patterns(max_days_unused=max_days)
        data = safe_load(self.patterns_file, default=[])
        out = data if isinstance(data, list) else []
        if intent_filter and (intent_filter := str(intent_filter).strip()):
            out = [
                p
                for p in out
                if isinstance(p, dict)
                and (p.get("intent") or "").strip() == intent_filter
            ]
        return out

    def add_pattern(
        self,
        trigger: str,
        action: Dict[str, Any],
        description: str = "",
        intent: Optional[str] = None,
    ) -> None:
        """Añade un patrón (Fase 4). C.3: intent opcional para agrupación."""
        patterns = self.list_patterns()
        from datetime import datetime, timezone

        entry: Dict[str, Any] = {
            "pattern_id": f"p_{len(patterns)}",
            "description": description or trigger,
            "trigger": trigger,
            "action": action,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "use_count": 0,
            "last_used": None,
        }
        if intent and str(intent).strip():
            entry["intent"] = str(intent).strip()
        patterns.append(entry)
        try:
            with open(self.patterns_file, "w", encoding="utf-8") as f:
                json.dump(patterns, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.warning("ProceduralStore: failed to save: %s", e)

    def increment_use(self, pattern_id: str) -> None:
        """Misión 3.2 (C.1): refuerza un patrón tras uso exitoso (incrementa use_count, actualiza last_used)."""
        patterns = self.list_patterns()
        for p in patterns:
            if (p.get("pattern_id") or "").strip() == (pattern_id or "").strip():
                from datetime import datetime, timezone

                p["use_count"] = int(p.get("use_count") or 0) + 1
                p["last_used"] = datetime.now(timezone.utc).isoformat()
                break
        else:
            return
        try:
            with open(self.patterns_file, "w", encoding="utf-8") as f:
                json.dump(patterns, f, ensure_ascii=False, indent=2)
            logger.debug("ProceduralStore: reinforced pattern %s", pattern_id)
        except Exception as e:
            logger.warning("ProceduralStore: failed to save after increment: %s", e)
