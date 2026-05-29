"""
MuninnDB — Motor de Triggers para proactividad.
Evalúa callbacks de MuninnDB y decide si disparar una notificación proactiva.

Flujo:
  MuninnDB → POST /api/muninn/trigger → MuninnTriggerEngine.evaluate() → notify si procede
"""
import logging
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger("lilith.muninn_triggers")

# ─── Tipos de trigger ─────────────────────────────────────────────────────────

TRIGGER_TYPE_ACTIVATION = (
    "activation"  # Una memoria fue activada con score >= threshold
)
TRIGGER_TYPE_NEW_MEMORY = "new_memory"  # Nueva memoria escrita con tag de prioridad
TRIGGER_TYPE_HEBBIAN = "hebbian"  # Conexión hebbiana reforzada (uso repetido)
TRIGGER_TYPE_CUSTOM = "custom"  # Payload libre definido por el caller

# Tags que fuerzan disparo inmediato si aparecen en el payload
URGENT_TAGS = {"urgent", "critical", "owner_alert", "priority_high"}


class TriggerPayload:
    """Normaliza el payload crudo de MuninnDB en un objeto accesible."""

    def __init__(self, raw: Dict[str, Any]):
        self.raw = raw
        self.trigger_type: str = str(raw.get("type") or TRIGGER_TYPE_ACTIVATION)
        self.vault: str = str(raw.get("vault") or "lilith")
        self.concept: str = str(raw.get("concept") or raw.get("key") or "")
        self.content: str = str(raw.get("content") or raw.get("body") or "")
        self.score: float = float(raw.get("score") or raw.get("relevance") or 0.0)
        self.tags: List[str] = [str(t) for t in (raw.get("tags") or []) if t]
        self.why: Dict[str, Any] = raw.get("why") or {}
        self.timestamp: float = float(raw.get("timestamp") or time.time())

    @property
    def is_urgent(self) -> bool:
        return bool(URGENT_TAGS.intersection(self.tags))

    def to_notification_text(self) -> str:
        concept_short = self.concept[:80]
        content_short = self.content[:200].replace("\n", " ")
        vault_badge = f"[{self.vault}]" if self.vault else ""
        score_str = f"(score: {self.score:.2f})" if self.score > 0 else ""
        return f"🧠 **Trigger Muninn** {vault_badge} {score_str}\n• **{concept_short}**\n  {content_short}"


class MuninnTriggerEngine:
    """
    Evalúa payloads de trigger y decide si disparar notificación.
    Lee reglas desde Config/muninn.json (triggers_rules) si existen;
    aplica umbrales por defecto en otro caso.
    """

    def __init__(self, base_path: Path):
        self.base_path = Path(base_path)
        self._recent_triggers: List[float] = []  # timestamps de disparo reciente

    def _load_cfg(self) -> dict:
        try:
            from src.core.json_safe import safe_load

            return safe_load(self.base_path / "Config" / "muninn.json", default={})
        except Exception:
            return {}

    def _rate_ok(self, max_per_hour: int = 5) -> bool:
        now = time.time()
        self._recent_triggers = [t for t in self._recent_triggers if now - t < 3600]
        return len(self._recent_triggers) < max_per_hour

    def _record_trigger(self) -> None:
        self._recent_triggers.append(time.time())

    def evaluate(self, payload: TriggerPayload) -> bool:
        """
        Evalúa si el trigger debe disparar una notificación.
        Retorna True si procede notificar.
        """
        cfg = self._load_cfg()
        rules = cfg.get("trigger_rules") or {}

        # Urgentes: siempre pasan (sin rate limit)
        if payload.is_urgent:
            logger.info(
                "muninn_trigger: urgent tag → forzado (%s)", payload.concept[:60]
            )
            self._record_trigger()
            return True

        # Rate limit
        max_per_hour = int(rules.get("max_per_hour") or 4)
        if not self._rate_ok(max_per_hour):
            logger.debug("muninn_trigger: rate limit alcanzado (%d/h)", max_per_hour)
            return False

        # Umbral de score
        min_score = float(rules.get("min_score") or 0.55)
        if payload.score > 0 and payload.score < min_score:
            logger.debug(
                "muninn_trigger: score %.2f < umbral %.2f", payload.score, min_score
            )
            return False

        # Filtro de vaults (si está configurado, solo notifica de esos vaults)
        allowed_vaults = rules.get("allowed_vaults") or []
        if allowed_vaults and payload.vault not in allowed_vaults:
            logger.debug("muninn_trigger: vault '%s' no en allow-list", payload.vault)
            return False

        # Filtro de tags excluidos
        excluded_tags = set(rules.get("excluded_tags") or [])
        if excluded_tags.intersection(payload.tags):
            logger.debug("muninn_trigger: tag excluido en %s", payload.tags)
            return False

        # Hebbian: solo notifica si conexión relevante (why.hebbian > 0.2)
        if payload.trigger_type == TRIGGER_TYPE_HEBBIAN:
            hebbian = float((payload.why or {}).get("hebbian") or 0.0)
            min_hebbian = float(rules.get("min_hebbian_for_notify") or 0.2)
            if hebbian < min_hebbian:
                return False

        self._record_trigger()
        logger.info(
            "muninn_trigger: DISPARADO vault=%s concept=%s score=%.2f tags=%s",
            payload.vault,
            payload.concept[:60],
            payload.score,
            payload.tags,
        )
        return True

    async def handle(self, raw: Dict[str, Any]) -> Optional[str]:
        """
        Punto de entrada principal desde la API.
        Evalúa el payload y, si procede, notifica al owner.
        Devuelve el texto enviado o None.
        """
        payload = TriggerPayload(raw)
        if not self.evaluate(payload):
            return None

        msg = payload.to_notification_text()

        # Intentar Telegram primero, luego Discord
        notified = False
        try:
            from src.core.transport.telegram import notify_owner_telegram

            notified = await notify_owner_telegram(msg, urgent=payload.is_urgent)
        except Exception as e:
            logger.debug("muninn_trigger: telegram notify error: %s", e)

        if not notified:
            try:
                from src.core.transport.discord import notify_owner

                cfg = self._load_cfg()
                channel_id = cfg.get("trigger_notify_channel") or ""
                await notify_owner(self.base_path, msg, channel_id=channel_id)
                notified = True
            except Exception as e:
                logger.warning("muninn_trigger: discord notify error: %s", e)

        if notified:
            # Episodio de trigger
            try:
                from src.core.episode_builder import build_episode
                from src.core.memory.legacy_adapter import EpisodicStore

                EpisodicStore(self.base_path).append(
                    build_episode(
                        summary=msg[:400],
                        outcome="success",
                        source="muninn_trigger",
                        tags=["proactive", "muninn_trigger", payload.vault]
                        + payload.tags[:3],
                    )
                )
            except Exception:
                pass
            return msg

        return None


# ─── Singleton ────────────────────────────────────────────────────────────────

_trigger_engines: Dict[str, MuninnTriggerEngine] = {}


def get_trigger_engine(base_path: Path) -> MuninnTriggerEngine:
    key = str(base_path)
    if key not in _trigger_engines:
        _trigger_engines[key] = MuninnTriggerEngine(base_path)
    return _trigger_engines[key]
