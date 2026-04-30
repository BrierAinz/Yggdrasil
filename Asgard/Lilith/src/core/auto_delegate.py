"""
AutoDelegate — Detección de URLs y delegación automática de investigación.
Cuando el owner pega una URL de dominio conocido, Lilith la investiga
automáticamente sin necesidad de comando explícito.
"""
import logging
import re
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional
from urllib.parse import urlparse

logger = logging.getLogger("lilith.auto_delegate")

URL_REGEX = re.compile(r'https?://[^\s<>"{}|\\^`\[\]]+', re.IGNORECASE)

# Dominios de alta confianza → investiga directo
_HIGH_CONFIDENCE_DOMAINS = {
    "github.com",
    "gist.github.com",
    "docs.python.org",
    "docs.rust-lang.org",
    "arxiv.org",
    "developer.mozilla.org",
    "developer.android.com",
    "stackoverflow.com",
    "stackexchange.com",
    "reddit.com",
    "huggingface.co",
    "news.ycombinator.com",
    "openai.com",
    "anthropic.com",
    "medium.com",
    "dev.to",
    "substack.com",
    "wikipedia.org",
    "pypi.org",
    "npmjs.com",
}

# Dominios de baja confianza → preguntar antes
_LOW_CONFIDENCE_DOMAINS = {
    "youtube.com",
    "youtu.be",
    "twitter.com",
    "x.com",
    "instagram.com",
    "tiktok.com",
    "facebook.com",
    "linkedin.com",
}

# Frases que indican intento explícito de investigación
_INVESTIGATION_INTENTS = [
    r"investiga",
    r"búsca?\s+sobre",
    r"qué\s+dice\s+la\s+web",
    r"busca?\s+en\s+internet",
    r"mira\s+qué\s+hay\s+sobre",
    r"encuentra\s+info",
    r"search\s+for",
    r"investiga\s+esto",
    r"qué\s+es\s+esto",
    r"explícame\s+esto",
    r"qué\s+dice",
]
_INTENT_RE = [re.compile(p, re.IGNORECASE) for p in _INVESTIGATION_INTENTS]


def _extract_domain(url: str) -> str:
    try:
        domain = urlparse(url).netloc.lower()
        return domain[4:] if domain.startswith("www.") else domain
    except Exception:
        return ""


class AutoDelegateDetector:
    """
    Detecta URLs en mensajes y decide si auto-investigar o preguntar.
    """

    def __init__(self, config: Optional[Dict] = None):
        cfg = config or {}
        self.enabled: bool = cfg.get("auto_delegate_enabled", True)
        self.min_confidence: float = cfg.get("auto_delegate_min_confidence", 0.7)
        self.require_owner: bool = cfg.get("auto_delegate_require_owner", True)
        self.max_per_hour: int = cfg.get("auto_delegate_max_per_hour", 10)
        self.blocked_domains: set = set(cfg.get("blocked_domains") or [])
        self.extra_high: set = set(cfg.get("allowed_domains_extra") or [])
        self._recent: List[datetime] = []

    def _is_rate_limited(self) -> bool:
        cutoff = datetime.now() - timedelta(hours=1)
        self._recent = [t for t in self._recent if t > cutoff]
        return len(self._recent) >= self.max_per_hour

    def _record(self) -> None:
        self._recent.append(datetime.now())

    def _score(self, url: str, has_intent: bool, msg_is_short: bool) -> float:
        domain = _extract_domain(url)
        if domain in self.blocked_domains:
            return 0.0
        score = 0.0
        if domain in _HIGH_CONFIDENCE_DOMAINS or domain in self.extra_high:
            score = 0.85
        elif domain in _LOW_CONFIDENCE_DOMAINS:
            score = 0.25
        else:
            score = 0.5
        if has_intent:
            score = min(score + 0.2, 1.0)
        if msg_is_short:
            score = min(score + 0.1, 1.0)
        return score

    def detect(self, message: str, role: str = "owner") -> Optional[Dict]:
        """
        Analiza el mensaje. Retorna:
        - None si no aplica delegación
        - {"action": "auto_investigate", "urls": [...], "ask_urls": [...]}
        - {"action": "ask_user", "urls": [...], "message": "..."}
        """
        if not self.enabled:
            return None
        if self.require_owner and role != "owner":
            return None
        if self._is_rate_limited():
            logger.debug("auto_delegate: rate limit alcanzado")
            return None

        urls = URL_REGEX.findall(message)
        if not urls:
            return None

        has_intent = any(r.search(message) for r in _INTENT_RE)
        msg_is_short = len(message.split()) < 12

        investigate: List[str] = []
        ask: List[str] = []

        for url in urls:
            s = self._score(url, has_intent, msg_is_short)
            if s >= self.min_confidence:
                investigate.append(url)
            elif s > 0:
                ask.append(url)

        if investigate:
            self._record()
            return {
                "action": "auto_investigate",
                "urls": investigate,
                "ask_urls": ask,
                "investigation_message": "Investiga estas URLs: "
                + " ".join(investigate),
            }
        if ask:
            return {
                "action": "ask_user",
                "urls": ask,
                "message": (
                    f"He detectado {'estas URLs' if len(ask) > 1 else 'esta URL'}: "
                    + ", ".join(f"`{u}`" for u in ask)
                    + "\n¿Quieres que las investigue?"
                ),
            }
        return None


# ─── Singleton ────────────────────────────────────────────────────────────────

_detectors: Dict[str, AutoDelegateDetector] = {}


def get_auto_delegate_detector(
    base_path: Optional[Path] = None,
) -> AutoDelegateDetector:
    key = str(base_path) if base_path else "default"
    if key not in _detectors:
        cfg: Dict = {}
        if base_path:
            try:
                from src.core.json_safe import safe_load

                cfg = safe_load(
                    Path(base_path) / "Config" / "auto_delegate.json", default={}
                )
            except Exception:
                pass
        _detectors[key] = AutoDelegateDetector(cfg)
    return _detectors[key]
