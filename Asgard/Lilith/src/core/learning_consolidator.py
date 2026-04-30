"""
Lilith 4.0 — Consolidador de aprendizaje.
Job periódico (cada 6h vía APScheduler) que lee señales de feedback
y refuerza o debilita patrones en matching_learner.

Fuentes: Data/implicit_feedback.jsonl + Data/feedback.jsonl
Salidas: matching_learner.reinforce() / matching_learner.weaken()
"""
import json
import logging
import time
from pathlib import Path
from typing import Dict, List

logger = logging.getLogger("LearningConsolidator")

_DEFAULT_REINFORCE_THRESHOLD = 2.0
_DEFAULT_WEAKEN_THRESHOLD = -1.5
_DEFAULT_LOOKBACK_HOURS = 24.0
_MAX_FILE_BYTES = 5 * 1024 * 1024  # 5 MB → rotar
_ARCHIVE_KEEP_LINES = 1000


class LearningConsolidator:
    """Lee señales de feedback recientes y actualiza el matching learner."""

    def __init__(self, base_path: Path):
        self.base_path = Path(base_path)

    def consolidate(self) -> dict:
        """Lee señales de las últimas 24h y actualiza matching_learner.
        Retorna stats: {signals, reinforced, weakened}."""
        cfg = self._load_cfg()
        if not cfg.get("consolidation_enabled", True):
            logger.debug("[LearningConsolidator] Deshabilitado por config.")
            return {"signals": 0, "reinforced": 0, "weakened": 0}

        reinforce_threshold = float(
            cfg.get("reinforce_threshold", _DEFAULT_REINFORCE_THRESHOLD)
        )
        weaken_threshold = float(cfg.get("weaken_threshold", _DEFAULT_WEAKEN_THRESHOLD))
        lookback = float(
            cfg.get("consolidation_lookback_hours", _DEFAULT_LOOKBACK_HOURS)
        )

        signals = self._load_recent_signals(hours=lookback)
        if not signals:
            logger.debug("[LearningConsolidator] Sin señales recientes.")
            return {"signals": 0, "reinforced": 0, "weakened": 0}

        # Agrupar por (message_preview, tool_used)
        groups: Dict[str, dict] = {}
        for sig in signals:
            tool = (sig.get("tool_used") or "").strip()
            preview = (sig.get("message_preview") or "").strip()[:80]
            if not tool or not preview:
                continue
            key = f"{preview}|{tool}"
            if key not in groups:
                groups[key] = {
                    "preview": preview,
                    "tool": tool,
                    "total_weight": 0.0,
                    "count": 0,
                }
            groups[key]["total_weight"] += float(sig.get("weight", 0))
            groups[key]["count"] += 1

        try:
            from src.core import matching_learner
        except Exception as e:
            logger.warning(
                "[LearningConsolidator] No se pudo importar matching_learner: %s", e
            )
            return {"signals": len(signals), "reinforced": 0, "weakened": 0}

        reinforced = 0
        weakened = 0

        for data in groups.values():
            preview = data["preview"]
            tool = data["tool"]
            weight = data["total_weight"]

            if weight >= reinforce_threshold:
                try:
                    matching_learner.reinforce(self.base_path, preview, tool, count=3)
                    reinforced += 1
                    logger.info(
                        "[LearningConsolidator] + Reforzado: '%s' → %s (Σ=%.2f)",
                        preview[:40],
                        tool,
                        weight,
                    )
                except Exception as e:
                    logger.debug("[LearningConsolidator] Error reforzando: %s", e)

            elif weight <= weaken_threshold:
                try:
                    matching_learner.weaken(self.base_path, preview, tool)
                    weakened += 1
                    logger.info(
                        "[LearningConsolidator] - Debilitado: '%s' → %s (Σ=%.2f)",
                        preview[:40],
                        tool,
                        weight,
                    )
                except Exception as e:
                    logger.debug("[LearningConsolidator] Error debilitando: %s", e)

        stats = {
            "signals": len(signals),
            "reinforced": reinforced,
            "weakened": weakened,
        }
        logger.info("[LearningConsolidator] Consolidación: %s", stats)

        # Auditoría
        try:
            from src.core.auditor.decision_auditor import append_decision

            append_decision(
                decision_type="learning_consolidation",
                actor="consolidator",
                payload=stats,
                reason="scheduled_job",
            )
        except Exception:
            pass

        # Rotar archivo si es muy grande
        self._rotate_if_needed(self.base_path / "Data" / "implicit_feedback.jsonl")

        return stats

    # ─── Privados ─────────────────────────────────────────────────────────────

    def _load_cfg(self) -> dict:
        try:
            from src.core.json_safe import safe_load

            cfg = safe_load(self.base_path / "Config" / "learning.json", default={})
            return cfg if isinstance(cfg, dict) else {}
        except Exception:
            return {}

    def _load_recent_signals(self, hours: float = 24.0) -> List[dict]:
        """Lee señales de implicit_feedback.jsonl y feedback.jsonl."""
        cutoff = time.time() - hours * 3600
        signals = []
        for fname in ("implicit_feedback.jsonl", "feedback.jsonl"):
            path = self.base_path / "Data" / fname
            if not path.exists():
                continue
            try:
                with open(path, "r", encoding="utf-8") as f:
                    for line in f:
                        line = line.strip()
                        if not line:
                            continue
                        try:
                            obj = json.loads(line)
                            # feedback.jsonl usa "ts" como ISO string; implicit_feedback usa float
                            ts_raw = obj.get("ts", 0)
                            try:
                                ts = float(ts_raw)
                            except (TypeError, ValueError):
                                import datetime

                                ts = datetime.datetime.fromisoformat(
                                    str(ts_raw)
                                ).timestamp()
                            if ts >= cutoff:
                                # Normalizar campos para unificar estructura
                                if "tool_used" not in obj and "tool" not in obj:
                                    continue
                                if "tool_used" not in obj:
                                    obj["tool_used"] = obj.get("tool", "")
                                if "message_preview" not in obj:
                                    obj["message_preview"] = obj.get("comment", "")[:80]
                                if "weight" not in obj:
                                    # feedback.jsonl tiene "rating" 1-5
                                    rating = int(obj.get("rating", 3))
                                    obj["weight"] = (
                                        rating - 3
                                    ) / 2.0  # normalize: 1→-1.0, 3→0.0, 5→1.0
                                signals.append(obj)
                        except Exception:
                            continue
            except Exception as e:
                logger.debug("[LearningConsolidator] Error leyendo %s: %s", fname, e)
        return signals

    @staticmethod
    def _rotate_if_needed(path: Path) -> None:
        """Rota el archivo si supera 5MB, manteniendo las últimas N líneas."""
        if not path.exists():
            return
        try:
            if path.stat().st_size <= _MAX_FILE_BYTES:
                return
            archive = path.parent / (path.stem + "_archive.jsonl")
            with open(path, "r", encoding="utf-8") as f:
                lines = f.readlines()
            with open(archive, "a", encoding="utf-8") as f:
                f.writelines(lines[:-_ARCHIVE_KEEP_LINES])
            with open(path, "w", encoding="utf-8") as f:
                f.writelines(lines[-_ARCHIVE_KEEP_LINES:])
            logger.debug(
                "[LearningConsolidator] Rotado %s (%d líneas archivadas)",
                path.name,
                len(lines) - _ARCHIVE_KEEP_LINES,
            )
        except Exception as e:
            logger.debug("[LearningConsolidator] Error rotando: %s", e)
