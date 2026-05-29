"""
Lilith 4.1 — D.11 Pattern Detector.
Analiza memoria episódica para detectar tareas repetitivas y sugerir automatizaciones al owner.
"""
import logging
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger("lilith.pattern_detector")


def _load_config(base_path: Path) -> Dict[str, Any]:
    try:
        from src.core.json_safe import safe_load

        cfg = safe_load(base_path / "Config" / "learning.json", default={})
        return cfg if isinstance(cfg, dict) else {}
    except Exception:
        return {}


def _normalize_tool(tool: str) -> str:
    return (tool or "unknown").strip().lower()


def _similarity_key(summary: str) -> str:
    """Clave normalizada de resumen para agrupar tareas similares."""
    import re

    s = (summary or "").lower().strip()
    s = re.sub(r"[^a-záéíóúüñ\s]", " ", s)
    words = s.split()
    # Tomar las primeras 6 palabras significativas (stop-words mínimas)
    _stop = {
        "el",
        "la",
        "los",
        "las",
        "un",
        "una",
        "de",
        "en",
        "a",
        "y",
        "o",
        "que",
        "se",
        "es",
    }
    sig = [w for w in words if w not in _stop][:6]
    return " ".join(sig)


class PatternDetector:
    """
    D.11 — Detecta patrones repetitivos en episodic_log.jsonl y genera sugerencias de
    automatización para notificar al owner.
    """

    def __init__(self, base_path: Path):
        self.base_path = Path(base_path)

    def analyze_episodic_patterns(self) -> List[Dict[str, Any]]:
        """
        Lee los últimos `lookback_days` días de episodic_log.jsonl.
        Detecta tareas repetitivas (misma tool + similar input ≥ min_occurrences veces).
        Devuelve lista de sugerencias [{tool, pattern, count, suggestion}].
        """
        cfg = _load_config(self.base_path)
        pd_cfg = cfg.get("pattern_detection", {})
        if not pd_cfg.get("enabled", True):
            logger.info("[PatternDetector] Desactivado por config.")
            return []

        min_occ = int(pd_cfg.get("min_occurrences", 3))
        lookback_days = int(pd_cfg.get("lookback_days", 30))

        episodes = self._load_recent_episodes(lookback_days)
        if not episodes:
            logger.info(
                "[PatternDetector] Sin episodios en los últimos %d días.", lookback_days
            )
            return []

        # Agrupar por (tool, similarity_key)
        groups: Dict[str, Dict[str, Any]] = defaultdict(
            lambda: {"count": 0, "examples": [], "tool": ""}
        )
        for ep in episodes:
            summary = ep.get("summary") or ""
            tags = ep.get("tags") or []
            # Intentar extraer tool de tags
            tool = next((t for t in tags if t.startswith("tool:")), "")
            if tool:
                tool = tool[5:]
            else:
                # Inferir por source
                tool = ep.get("source") or "unknown"
            key = f"{_normalize_tool(tool)}::{_similarity_key(summary)}"
            groups[key]["count"] += 1
            groups[key]["tool"] = tool
            if len(groups[key]["examples"]) < 3:
                groups[key]["examples"].append(summary[:120])

        suggestions: List[Dict[str, Any]] = []
        for key, data in groups.items():
            if data["count"] < min_occ:
                continue
            tool = data["tool"]
            examples = data["examples"]
            pattern_label = key.split("::", 1)[1] if "::" in key else key
            suggestion_text = (
                f"He notado que la tarea '{pattern_label}' (tool: {tool}) se repite "
                f"{data['count']} veces en los últimos {lookback_days} días. "
                f"¿Quieres que lo automatice con un monitor o tarea programada?"
            )
            suggestions.append(
                {
                    "tool": tool,
                    "pattern": pattern_label,
                    "count": data["count"],
                    "examples": examples,
                    "suggestion": suggestion_text,
                }
            )

        logger.info(
            "[PatternDetector] Found %d repetitive tasks: %s",
            len(suggestions),
            [s["pattern"] for s in suggestions],
        )
        return suggestions

    def _load_recent_episodes(self, lookback_days: int) -> List[Dict[str, Any]]:
        """Carga episodios dentro del window de lookback_days."""
        import json

        path = self.base_path / "Data" / "episodic_log.jsonl"
        if not path.exists():
            return []
        cutoff = datetime.now(timezone.utc) - timedelta(days=lookback_days)
        results = []
        try:
            with open(path, "r", encoding="utf-8") as f:
                for line in f:
                    try:
                        d = json.loads(line)
                        ts_str = d.get("timestamp") or ""
                        if ts_str:
                            dt = datetime.fromisoformat(
                                str(ts_str).replace("Z", "+00:00")
                            )
                            if dt.tzinfo is None:
                                dt = dt.replace(tzinfo=timezone.utc)
                            if dt < cutoff:
                                continue
                        results.append(d)
                    except Exception:
                        continue
        except Exception as e:
            logger.warning("[PatternDetector] Error leyendo episodic_log: %s", e)
        return results

    async def detect_and_notify(self) -> int:
        """
        Detecta patrones y notifica al owner vía Discord si notify_owner=True.
        Devuelve número de sugerencias enviadas.
        """
        cfg = _load_config(self.base_path)
        pd_cfg = cfg.get("pattern_detection", {})
        notify = bool(pd_cfg.get("notify_owner", True))

        suggestions = self.analyze_episodic_patterns()
        if not suggestions:
            return 0

        if not notify:
            return len(suggestions)

        try:
            from src.core.transport.discord import notify_owner

            lines = ["💡 **Sugerencias de automatización detectadas:**"]
            for s in suggestions[:5]:  # máximo 5 para no spamear
                lines.append(f"\n• {s['suggestion']}")
            msg = "\n".join(lines)[:1800]
            await notify_owner(self.base_path, msg)
            logger.info(
                "[PatternDetector] Notificación enviada al owner con %d sugerencias.",
                len(suggestions),
            )
        except Exception as e:
            logger.warning("[PatternDetector] Error notificando al owner: %s", e)

        return len(suggestions)
