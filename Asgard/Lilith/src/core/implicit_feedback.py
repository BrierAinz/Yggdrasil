"""
Lilith 4.0 — Feedback implícito.
Detecta señales de corrección, éxito o negatividad del owner sin rating explícito.
Se ejecuta como post-hook después de cada interacción y cuando llega el siguiente mensaje.

Señales detectadas:
  - correction: "no, usa Eva" / "eso no era" / "incorrecto" → weight -1.0
  - explicit_positive: "perfecto" / "exacto" / "gracias" → weight +1.0
  - confirmation_approved: owner autorizó una acción peligrosa → weight +0.8
  - confirmation_denied: owner denegó una acción peligrosa → weight -1.0
"""
import hashlib
import json
import logging
import re
import time
from pathlib import Path
from typing import Dict, Optional

logger = logging.getLogger("ImplicitFeedback")

# Estado en memoria: última interacción por user_id (entre requests)
_last_interactions: Dict[str, dict] = {}

# ─── Patrones de detección ───────────────────────────────────────────────────

_CORRECTION_PATTERNS = [
    r"no,?\s*(usa|hazlo con|mejor con|intenta con|pregúntale a|pide a)\s",
    r"eso no (era|es|fue) lo que",
    r"\b(incorrecto|equivocado)\b",
    r"(cambia|switch|usa)\s+a?\s*(eva|adán|adan|odín|odin)",
    r"no era eso",
    r"no,?\s*mejor\s*(con|usa|llama)",
]

_POSITIVE_WORDS = {
    "perfecto",
    "gracias",
    "exacto",
    "eso era",
    "genial",
    "bien",
    "correcto",
    "nice",
    "thanks",
    "great",
    "excelente",
    "ideal",
    "justo eso",
    "perfecto",
    "justo lo que",
    "bien hecho",
    "muy bien",
}


# ─── Helpers internos (duplicados de matching_learner para evitar acoplamiento) ─


def _word_set(text: str) -> set:
    return set(re.findall(r"[a-z0-9áéíóúñ]+", (text or "").lower()))


def _similarity(a: str, b: str) -> float:
    wa, wb = _word_set(a), _word_set(b)
    if not wa and not wb:
        return 1.0
    if not wa or not wb:
        return 0.0
    inter = len(wa & wb)
    union = len(wa | wb)
    return inter / union if union else 0.0


def _normalize_key(text: str, max_chars: int = 120) -> str:
    t = re.sub(r"\s+", " ", (text or "").strip().lower())
    return t[:max_chars].strip()


def _msg_hash(message: str) -> str:
    return hashlib.sha256((message or "").encode("utf-8")).hexdigest()[:16]


def _feedback_path(base_path: Path) -> Path:
    p = Path(base_path) / "Data" / "implicit_feedback.jsonl"
    p.parent.mkdir(parents=True, exist_ok=True)
    return p


# ─── API pública ─────────────────────────────────────────────────────────────


def register_interaction(
    base_path: Path,
    user_id: str,
    message: str,
    tool_used: str,
    response: str,
    transport: str = "discord",
) -> None:
    """Registra la última interacción del usuario para análisis de followup.
    Se llama DESPUÉS de generar la respuesta."""
    if not user_id or not message:
        return
    _last_interactions[user_id] = {
        "message": message[:300],
        "message_key": _normalize_key(message),
        "tool_used": (tool_used or "generate_reply").strip(),
        "response": response[:300],
        "transport": transport,
        "ts": time.time(),
        "hash": _msg_hash(message),
    }


def analyze_followup_and_record(
    base_path: Path,
    user_id: str,
    followup_message: str,
    ttl_seconds: float = 300.0,
) -> Optional[dict]:
    """Analiza si el mensaje actual es feedback sobre la interacción anterior.
    Si se detecta señal, la escribe a Data/implicit_feedback.jsonl.
    Se llama al INICIO de procesar cada nuevo mensaje (antes de generar respuesta).
    Retorna el dict de señal o None."""
    if not user_id or not (followup_message or "").strip():
        return None
    last = _last_interactions.get(user_id)
    if not last:
        return None
    # Ventana temporal
    if time.time() - last["ts"] > ttl_seconds:
        _last_interactions.pop(user_id, None)
        return None

    signal = _classify_signal(followup_message, last)
    if signal:
        _write_signal(base_path, signal)
        if signal.get("type") == "correction":
            # Limpiar para no registrar doble corrección
            _last_interactions.pop(user_id, None)
    return signal


def record_confirmation_signal(
    base_path: Path,
    message: str,
    tool_used: str,
    approved: bool,
    transport: str = "discord",
) -> None:
    """Registra señal directa de confirmación (aprobación o denegación del owner)."""
    signal = {
        "type": "confirmation_approved" if approved else "confirmation_denied",
        "tool_used": (tool_used or "unknown").strip(),
        "message_hash": _msg_hash(message),
        "message_preview": _normalize_key(message or ""),
        "transport": transport,
        "weight": 0.8 if approved else -1.0,
        "ts": time.time(),
    }
    _write_signal(base_path, signal)
    logger.debug(
        "[ImplicitFeedback] Confirmación %s registrada (tool=%s)",
        "aprobada" if approved else "denegada",
        tool_used,
    )


def has_recent_negatives_for_tool(
    base_path: Path,
    message: str,
    tool: str,
    lookback_hours: float = 24.0,
    min_negatives: int = 2,
) -> bool:
    """True si hay >= min_negatives señales negativas recientes para este mensaje+tool.
    Usado por la metacognición del Planner para rechazar planes aprendidos dudosos."""
    if not base_path or not message or not tool:
        return False
    try:
        path = _feedback_path(base_path)
        if not path.exists():
            return False
        cutoff = time.time() - lookback_hours * 3600
        key = _normalize_key(message)
        negative_count = 0
        with open(path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    obj = json.loads(line)
                    if float(obj.get("ts", 0)) < cutoff:
                        continue
                    if obj.get("tool_used") != tool:
                        continue
                    if float(obj.get("weight", 0)) >= 0:
                        continue
                    sim = _similarity(
                        key, _normalize_key(obj.get("message_preview", ""))
                    )
                    if sim >= 0.25:
                        negative_count += 1
                except Exception:
                    continue
        return negative_count >= min_negatives
    except Exception as e:
        logger.debug("[ImplicitFeedback] has_recent_negatives: %s", e)
        return False


# ─── Internos ────────────────────────────────────────────────────────────────


def _classify_signal(followup: str, last: dict) -> Optional[dict]:
    """Clasifica el tipo de señal de feedback en el followup."""
    msg_lower = (followup or "").strip().lower()
    tool = last.get("tool_used", "")

    # 1. Corrección explícita
    for pattern in _CORRECTION_PATTERNS:
        if re.search(pattern, msg_lower, re.IGNORECASE):
            corrected_tool = _extract_corrected_tool(msg_lower)
            return {
                "type": "correction",
                "tool_used": tool,
                "corrected_tool": corrected_tool,
                "message_hash": last["hash"],
                "message_preview": last.get("message_key", "")[:120],
                "transport": last.get("transport", "discord"),
                "weight": -1.0,
                "ts": time.time(),
            }

    # 2. Feedback positivo explícito
    if any(w in msg_lower for w in _POSITIVE_WORDS):
        return {
            "type": "explicit_positive",
            "tool_used": tool,
            "message_hash": last["hash"],
            "message_preview": last.get("message_key", "")[:120],
            "transport": last.get("transport", "discord"),
            "weight": 1.0,
            "ts": time.time(),
        }

    return None


def _extract_corrected_tool(msg: str) -> Optional[str]:
    """Extrae la herramienta correcta mencionada en un mensaje de corrección."""
    if re.search(r"\b(eva|estratega)\b", msg, re.IGNORECASE):
        return "delegate_eva"
    if re.search(r"\b(adán|adan|artesano|código)\b", msg, re.IGNORECASE):
        return "delegate_adan"
    if re.search(r"\b(odín|odin|lucifer)\b", msg, re.IGNORECASE):
        return "delegate_odin"
    return None


def _write_signal(base_path: Path, signal: dict) -> None:
    """Escribe señal a Data/implicit_feedback.jsonl."""
    try:
        path = _feedback_path(base_path)
        with open(path, "a", encoding="utf-8") as f:
            f.write(json.dumps(signal, ensure_ascii=False) + "\n")
        logger.debug(
            "[ImplicitFeedback] %s registrado (tool=%s, weight=%s)",
            signal.get("type"),
            signal.get("tool_used"),
            signal.get("weight"),
        )
    except Exception as e:
        logger.debug("[ImplicitFeedback] Error escribiendo señal: %s", e)
