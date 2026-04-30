import re
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Optional


@dataclass
class DetectResult:
    should_delegate: bool
    url: Optional[str]
    confidence: float
    reason: str


_session_counts: dict = {}  # {user_id+channel_id: (count, timestamp)}


class AutoDelegateDetector:
    def __init__(self, base_path: Path):
        from src.core.json_safe import safe_load

        cfg = safe_load(base_path / "Config" / "auto_delegate.json", default={})
        self.enabled = bool(cfg.get("enabled", True))
        self.auto_confirm = bool(cfg.get("auto_confirm_owner", True))
        self.threshold = float(cfg.get("confidence_threshold", 0.75))
        self.url_patterns = cfg.get("url_patterns", ["http://", "https://"])
        self.triggers = [t.lower() for t in cfg.get("intent_triggers", [])]
        self.excluded = cfg.get("excluded_domains", ["localhost", "127.0.0.1"])
        self.max_per_session = int(cfg.get("max_auto_per_session", 5))

    def detect(
        self, text: str, user_id: str = "", channel_id: str = ""
    ) -> DetectResult:
        no = DetectResult(False, None, 0.0, "")
        if not self.enabled:
            return no

        # Verificar max_auto_per_session
        key = f"{user_id}:{channel_id}"
        now = time.time()
        count, ts = _session_counts.get(key, (0, now))
        if now - ts > 3600:  # reset cada hora
            count = 0
        if count >= self.max_per_session:
            return DetectResult(False, None, 0.0, "max_per_session_reached")

        # Descartar URLs en bloques de código
        clean = re.sub(r"```.*?```", "", text, flags=re.DOTALL)
        clean = re.sub(r"`[^`]+`", "", clean)

        # Extraer primera URL válida
        url_match = re.search(r"https?://[^\s<>\"']+", clean)
        url = None
        if url_match:
            candidate = url_match.group(0).rstrip(".,;)")
            # Excluir dominios prohibidos
            if any(ex in candidate for ex in self.excluded):
                url = None
            # Excluir extensiones de archivo
            elif re.search(
                r"\.(png|jpg|jpeg|gif|pdf|zip|rar|mp4|mp3|exe)(\?|$)", candidate, re.I
            ):
                url = None
            else:
                url = candidate

        # Detectar intent triggers
        lower = text.lower()
        has_trigger = any(t in lower for t in self.triggers)

        # Calcular confidence
        if url and has_trigger:
            confidence = 1.0
            reason = "url+trigger"
        elif has_trigger:
            confidence = 0.8
            reason = "trigger_only"
        elif url:
            confidence = 0.85
            reason = "url_only"
        else:
            return no

        if confidence < self.threshold:
            return no

        # Registrar uso
        _session_counts[key] = (count + 1, now)

        return DetectResult(True, url, confidence, reason)
