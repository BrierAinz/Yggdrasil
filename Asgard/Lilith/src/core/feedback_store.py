"""
Lilith 3.5 C.3 — Almacén de feedback explícito (valoración 1-5 + comentario).
Persiste en Data/feedback.jsonl y aplica refuerzo/castigo a patrones según valoración.
"""
import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional

logger = logging.getLogger("FeedbackStore")

DEFAULT_BASE_PATH: Optional[Path] = None


def _base_path() -> Path:
    global DEFAULT_BASE_PATH
    if DEFAULT_BASE_PATH is None:
        DEFAULT_BASE_PATH = Path(__file__).resolve().parent.parent.parent.parent
    return DEFAULT_BASE_PATH


def set_base_path(path: Path) -> None:
    global DEFAULT_BASE_PATH
    DEFAULT_BASE_PATH = Path(path)


def record_last_plan(user_id: str, pattern_id: Optional[str]) -> None:
    """Guarda el último pattern_id usado para este user (para aplicar feedback después)."""
    if not user_id:
        return
    try:
        base = _base_path()
        path = base / "Data" / "last_plan_by_user.json"
        path.parent.mkdir(parents=True, exist_ok=True)
        data = {}
        if path.exists():
            from src.core.json_safe import safe_load

            data = safe_load(path, default={})
            if not isinstance(data, dict):
                data = {}
        data[user_id] = {
            "pattern_id": pattern_id,
            "ts": datetime.now(timezone.utc).isoformat(),
        }
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=0)
    except Exception as e:
        logger.debug("FeedbackStore record_last_plan: %s", e)


def record_feedback(
    user_id: str,
    rating: int,
    comment: Optional[str] = None,
    memory_manager: Optional[Any] = None,
) -> None:
    """
    Guarda el feedback en Data/feedback.jsonl y aplica refuerzo si rating >= 4.
    Si hay pattern_id guardado para user_id y rating >= 4, refuerza el patrón.
    """
    try:
        base = _base_path()
        path = base / "Data" / "feedback.jsonl"
        path.parent.mkdir(parents=True, exist_ok=True)
        entry = {
            "ts": datetime.now(timezone.utc).isoformat(),
            "user_id": user_id or "default",
            "rating": max(1, min(5, int(rating))),
            "comment": (comment or "").strip()[:500],
        }
        with open(path, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")
        # Misión 3.8: umbral de refuerzo desde Config/learning.json
        try:
            from src.core.learning.learning_engine import get_learning_config

            cfg = get_learning_config(_base_path())
            reinforce_threshold = int(cfg.get("feedback_reinforce_threshold") or 4)
        except Exception:
            reinforce_threshold = 4
        if rating >= reinforce_threshold and memory_manager and user_id:
            from src.core.json_safe import safe_load

            last_path = base / "Data" / "last_plan_by_user.json"
            if last_path.exists():
                data = safe_load(last_path, default={})
                user_data = data.get(user_id) if isinstance(data, dict) else {}
                if isinstance(user_data, dict):
                    pid = user_data.get("pattern_id")
                    if pid:
                        memory_manager.reinforce_procedural_pattern(pid)
                        logger.info(
                            "FeedbackStore: reinforced pattern %s (rating=%s)",
                            pid,
                            rating,
                        )
    except Exception as e:
        logger.warning("FeedbackStore record_feedback: %s", e)
