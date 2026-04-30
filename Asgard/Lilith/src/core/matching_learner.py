"""
Misión 4.0 — Fase 0: Matching Learning.
Aprende de cada decisión (mensaje → tool) y sugiere la tool más adecuada para mensajes similares.
Persiste en Data/matching_learning.jsonl.

Refinamiento: tras acumular datos, ajustar min_matches y confidence_threshold en learning.json.
Opcional: evolucionar _similarity() a TF-IDF + coseno sin cambiar el resto del módulo.
"""
import json
import logging
import re
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger("MatchingLearner")

DEFAULT_MAX_ENTRIES = 3000
DEFAULT_MIN_MATCHES = 2
DEFAULT_CONFIDENCE_THRESHOLD = 0.35


def _config(base_path: Optional[Path] = None) -> Dict[str, Any]:
    if base_path is None:
        base_path = Path(__file__).resolve().parent.parent.parent
    try:
        from src.core.json_safe import safe_load

        cfg = safe_load(Path(base_path) / "Config" / "learning.json", default={})
        return cfg if isinstance(cfg, dict) else {}
    except Exception:
        return {}


def _store_path(base_path: Path) -> Path:
    p = Path(base_path) / "Data" / "matching_learning.jsonl"
    p.parent.mkdir(parents=True, exist_ok=True)
    return p


def _normalize_for_key(text: str, max_chars: int = 120) -> str:
    if not text:
        return ""
    t = re.sub(r"\s+", " ", (text or "").strip().lower())
    return t[:max_chars].strip()


def _word_set(text: str) -> set:
    return set(re.findall(r"[a-z0-9áéíóúñ]+", (text or "").lower()))


def _similarity(a: str, b: str) -> float:
    """Similitud por palabras en común (Jaccard suavizado)."""
    wa, wb = _word_set(a), _word_set(b)
    if not wa and not wb:
        return 1.0
    if not wa or not wb:
        return 0.0
    inter = len(wa & wb)
    union = len(wa | wb)
    return inter / union if union else 0.0


def is_enabled(base_path: Optional[Path] = None) -> bool:
    """True si matching_learning_enabled en Config/learning.json."""
    cfg = _config(base_path)
    return bool(cfg.get("matching_learning_enabled"))


def record(
    base_path: Path,
    message: str,
    primary_tool: str,
    outcome: str = "success",
) -> None:
    """
    Registra una decisión para aprendizaje: mensaje → tool usada.
    Se llama tras cada plan() con la tool del primer paso.
    """
    if not base_path or not primary_tool:
        return
    cfg = _config(base_path)
    if not cfg.get("matching_learning_enabled"):
        return
    preview = _normalize_for_key(message or "", 200)
    if not preview:
        return
    path = _store_path(base_path)
    entry = {
        "message_preview": preview,
        "tool": primary_tool.strip(),
        "outcome": (outcome or "success").strip()[:50],
        "ts": __import__("datetime")
        .datetime.now(__import__("datetime").timezone.utc)
        .isoformat(),
    }
    try:
        with open(path, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")
        # Poda por tamaño (opcional)
        _prune_if_needed(path, cfg)
    except Exception as e:
        logger.debug("MatchingLearner record: %s", e)


def _prune_if_needed(path: Path, cfg: Dict[str, Any]) -> None:
    max_entries = (
        int(cfg.get("matching_learning_max_entries") or 0) or DEFAULT_MAX_ENTRIES
    )
    try:
        with open(path, "r", encoding="utf-8") as f:
            lines = [ln.strip() for ln in f if ln.strip()]
        if len(lines) <= max_entries:
            return
        with open(path, "w", encoding="utf-8") as f:
            for ln in lines[-max_entries:]:
                f.write(ln + "\n")
    except Exception:
        pass


def suggest(
    base_path: Path,
    message: str,
    *,
    min_matches: Optional[int] = None,
    confidence_threshold: Optional[float] = None,
    similarity_min: float = 0.25,
) -> Optional[Tuple[str, float]]:
    """
    Sugiere una tool para el mensaje a partir de decisiones pasadas similares.
    Retorna (tool_name, confidence) o None si no hay suficientes coincidencias o confianza.
    """
    if not base_path or not (message or "").strip():
        return None
    cfg = _config(base_path)
    if not cfg.get("matching_learning_enabled"):
        return None
    path = _store_path(base_path)
    if not path.exists():
        return None
    min_m = (
        min_matches
        if min_matches is not None
        else int(cfg.get("matching_learning_min_matches") or DEFAULT_MIN_MATCHES)
    )
    thresh = (
        confidence_threshold
        if confidence_threshold is not None
        else float(
            cfg.get("matching_learning_confidence_threshold")
            or DEFAULT_CONFIDENCE_THRESHOLD
        )
    )

    key_new = _normalize_for_key(message, 200)
    words_new = _word_set(key_new)
    if not words_new:
        return None

    tool_counts: Dict[str, int] = {}
    similar_count = 0
    try:
        with open(path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    obj = json.loads(line)
                    if not isinstance(obj, dict):
                        continue
                    preview = (obj.get("message_preview") or "").strip()
                    tool = (obj.get("tool") or "").strip()
                    if not tool:
                        continue
                    sim = _similarity(key_new, preview)
                    if sim < similarity_min:
                        continue
                    similar_count += 1
                    tool_counts[tool] = tool_counts.get(tool, 0) + 1
                except Exception:
                    continue
    except Exception as e:
        logger.debug("MatchingLearner suggest read: %s", e)
        return None

    if similar_count < min_m or not tool_counts:
        return None
    best_tool = max(tool_counts, key=tool_counts.get)
    confidence = tool_counts[best_tool] / similar_count
    if confidence < thresh:
        return None
    return (best_tool, round(confidence, 3))


def reinforce(base_path: Path, message_pattern: str, tool: str, count: int = 3) -> None:
    """Refuerza un patrón añadiendo N entradas de éxito. Usado por LearningConsolidator."""
    if not base_path or not message_pattern or not tool:
        return
    cfg = _config(base_path)
    if not cfg.get("matching_learning_enabled"):
        return
    preview = _normalize_for_key(message_pattern, 200)
    if not preview:
        return
    path = _store_path(base_path)
    import datetime as _dt

    ts = _dt.datetime.now(_dt.timezone.utc).isoformat()
    try:
        with open(path, "a", encoding="utf-8") as f:
            for _ in range(count):
                entry = {
                    "message_preview": preview,
                    "tool": tool.strip(),
                    "outcome": "reinforced",
                    "ts": ts,
                }
                f.write(json.dumps(entry, ensure_ascii=False) + "\n")
        _prune_if_needed(path, cfg)
    except Exception as e:
        logger.debug("MatchingLearner reinforce: %s", e)


def weaken(base_path: Path, message_pattern: str, tool: str) -> None:
    """Debilita un patrón añadiendo una entrada de fallo. Usado por LearningConsolidator."""
    if not base_path or not message_pattern or not tool:
        return
    cfg = _config(base_path)
    if not cfg.get("matching_learning_enabled"):
        return
    preview = _normalize_for_key(message_pattern, 200)
    if not preview:
        return
    path = _store_path(base_path)
    import datetime as _dt

    ts = _dt.datetime.now(_dt.timezone.utc).isoformat()
    entry = {
        "message_preview": preview,
        "tool": tool.strip(),
        "outcome": "weakened",
        "ts": ts,
    }
    try:
        with open(path, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")
    except Exception as e:
        logger.debug("MatchingLearner weaken: %s", e)


def has_recent_negatives_for_tool(
    base_path: Path,
    message: str,
    tool: str,
    lookback: int = 100,
    min_negatives: int = 2,
) -> bool:
    """True si hay >= min_negatives entradas weakened/failure recientes para mensaje+tool.
    Usado por la metacognición del Planner para rechazar planes aprendidos dudosos."""
    if not base_path or not message or not tool:
        return False
    path = _store_path(base_path)
    if not path.exists():
        return False
    key = _normalize_for_key(message, 200)
    negative_count = 0
    try:
        with open(path, "r", encoding="utf-8") as f:
            lines = [ln.strip() for ln in f if ln.strip()]
        for line in lines[-lookback:]:
            try:
                obj = json.loads(line)
                if obj.get("tool") != tool:
                    continue
                if obj.get("outcome") not in ("weakened", "failure"):
                    continue
                sim = _similarity(key, obj.get("message_preview", ""))
                if sim >= 0.25:
                    negative_count += 1
            except Exception:
                continue
    except Exception:
        return False
    return negative_count >= min_negatives
