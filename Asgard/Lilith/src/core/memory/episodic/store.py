"""
Lilith 3.0 — Store de memoria episódica.
Persiste logs de interacción en JSON/JSONL para análisis y aprendizaje.
Misión 3.2: política de retención (límite por fecha o cantidad).
Carga/parseo JSON vía json_safe para no fallar nunca por JSON inválido.
"""
import json
import logging
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from .models import InteractionLog

logger = logging.getLogger("EpisodicStore")

# Valores por defecto si no existe Config/memory.json
DEFAULT_MAX_EPISODIC_DAYS = 90
DEFAULT_MAX_EPISODIC_ENTRIES = 5000


def _parse_iso_ts(ts: str) -> Optional[datetime]:
    try:
        if ts.endswith("Z"):
            ts = ts[:-1] + "+00:00"
        return datetime.fromisoformat(ts.replace("Z", "+00:00"))
    except Exception:
        return None


class EpisodicStore:
    """Almacén de interacciones: append-only JSONL con retención configurable."""

    def __init__(self, base_path: Path):
        self.base_path = Path(base_path)
        self.log_dir = self.base_path / "memory" / "episodic"
        self.log_dir.mkdir(parents=True, exist_ok=True)
        self.log_file = self.log_dir / "interactions.jsonl"

    def _memory_config(self) -> Dict[str, Any]:
        """Carga Config/memory.json (Misión 3.2). Nunca falla por JSON."""
        from ...json_safe import safe_load

        cfg_path = self.base_path / "Config" / "memory.json"
        out = safe_load(cfg_path, default={})
        return out if isinstance(out, dict) else {}

    def _prune_old(self) -> None:
        """Elimina entradas antiguas según max_episodic_days y max_episodic_entries (B.1)."""
        if not self.log_file.exists():
            return
        cfg = self._memory_config()
        max_days = int(cfg.get("max_episodic_days") or 0) or DEFAULT_MAX_EPISODIC_DAYS
        max_entries = (
            int(cfg.get("max_episodic_entries") or 0) or DEFAULT_MAX_EPISODIC_ENTRIES
        )
        cutoff = datetime.now(timezone.utc) - timedelta(days=max_days)
        from ...json_safe import safe_load_lines

        kept = safe_load_lines(self.log_file, default=[])
        kept = [e for e in kept if isinstance(e, dict)]
        for i in range(len(kept) - 1, -1, -1):
            ts = _parse_iso_ts((kept[i].get("timestamp") or ""))
            if ts and ts < cutoff:
                kept.pop(i)
        if len(kept) <= max_entries:
            return
        kept = kept[-max_entries:]
        try:
            with open(self.log_file, "w", encoding="utf-8") as f:
                for e in kept:
                    f.write(json.dumps(e, ensure_ascii=False) + "\n")
            logger.debug(
                "EpisodicStore: pruned to %d entries (max_days=%d, max_entries=%d)",
                len(kept),
                max_days,
                max_entries,
            )
        except Exception as e:
            logger.warning("EpisodicStore: failed to write after prune: %s", e)

    def store(
        self,
        user_message: str,
        plan: List[Dict[str, Any]],
        final_response: str,
        outcome: str = "success",
        user_id: str = "",
    ) -> None:
        """Añade una interacción al log (una línea JSON por entrada). Tras escribir, aplica retención (B.1)."""
        entry = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "user_id": user_id or "default",
            "message": user_message,
            "plan": plan,
            "final_response": final_response[:2000],  # truncar para no inflar
            "outcome": outcome,
        }
        try:
            with open(self.log_file, "a", encoding="utf-8") as f:
                f.write(json.dumps(entry, ensure_ascii=False) + "\n")
            logger.debug("EpisodicStore: stored interaction (outcome=%s)", outcome)
            self._prune_old()
        except Exception as e:
            logger.warning("EpisodicStore: failed to store: %s", e)

    def list_recent(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Devuelve las últimas N interacciones (para consultas o análisis). Nunca falla por JSON."""
        from ...json_safe import safe_load_lines

        all_entries = safe_load_lines(self.log_file, default=[])
        valid = [e for e in all_entries if isinstance(e, dict)]
        return list(reversed(valid[-limit:]))[:limit]
