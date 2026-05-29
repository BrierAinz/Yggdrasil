import json
import logging
import time
from pathlib import Path
from typing import List

logger = logging.getLogger("lilith.proactive")


class ProactiveEngine:
    def __init__(self, base_path: Path):
        self.base_path = Path(base_path)
        self.state_path = self.base_path / "Data" / "proactive_state.json"
        self.state_path.parent.mkdir(parents=True, exist_ok=True)

    def _load_cfg(self) -> dict:
        from src.core.json_safe import safe_load

        return safe_load(self.base_path / "Config" / "proactive_mode.json", default={})

    def _load_state(self) -> dict:
        try:
            data = json.loads(self.state_path.read_text(encoding="utf-8"))
        except Exception:
            data = {}
        if not isinstance(data, dict):
            data = {}

        # Compatibilidad con estado previo
        if "seen_keys" not in data and isinstance(
            data.get("seen_activation_keys"), list
        ):
            data["seen_keys"] = list(data.get("seen_activation_keys") or [])
        if "last_run_ts" not in data and data.get("last_run_ts") is None:
            data["last_run_ts"] = 0

        if "seen_keys" not in data:
            data["seen_keys"] = []
        if "sent_timestamps" not in data:
            data["sent_timestamps"] = []
        if "last_run_ts" not in data:
            data["last_run_ts"] = 0
        return data

    def _save_state(self, state: dict) -> None:
        try:
            self.state_path.write_text(
                json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8"
            )
        except Exception:
            pass

    def _rate_ok(self, timestamps: List[float], max_per_hour: int) -> bool:
        now = time.time()
        recent = []
        for t in timestamps or []:
            try:
                if now - float(t) < 3600:
                    recent.append(float(t))
            except Exception:
                continue
        # devolver además la lista saneada para persistencia
        timestamps[:] = recent
        return len(recent) < max_per_hour

    async def run_once(self) -> None:
        cfg = self._load_cfg()
        if not cfg.get("enabled", True):
            return

        state = self._load_state()
        seen_keys = set(state.get("seen_keys", []))
        sent_ts = state.get("sent_timestamps", [])
        max_per_hour = int(cfg.get("max_notifications_per_hour", 3))

        if not self._rate_ok(sent_ts, max_per_hour):
            logger.info("Proactive rate limit alcanzado (%d/h)", max_per_hour)
            self._save_state(state)
            return

        # Construir contexto desde seeds + tags recientes
        contexts = list(cfg.get("contexts", []))
        try:
            from src.core.memory.legacy_adapter import EpisodicStore

            recent = EpisodicStore(self.base_path).search(limit=5)
            for ep in recent or []:
                try:
                    contexts.extend(ep.get("tags") or [])
                except Exception:
                    pass
        except Exception:
            pass

        contexts = list(
            dict.fromkeys([str(x).strip() for x in contexts if str(x).strip()])
        )[:10]

        # Activar Muninn — multi-vault (Mejora-5: proactividad en todos los vaults activos)
        try:
            from src.core.memory.muninn_memory import AGENT_VAULTS, MuninnMemory

            muninn = MuninnMemory(self.base_path)
            max_results = int(cfg.get("max_activations", 5))
            min_score = float(cfg.get("min_score", 0.6))

            # Determinar vaults a sondear
            if cfg.get("proactive_multi_vault", True):
                vaults_to_poll = list(dict.fromkeys(AGENT_VAULTS.values()))
            else:
                vaults_to_poll = [cfg.get("vault", "lilith")]

            # Activar en todos los vaults y fusionar resultados (dedup por concept)
            seen_concepts: set = set()
            all_activations = []
            for vault in vaults_to_poll:
                try:
                    acts = await muninn.activate(
                        context=contexts,
                        vault=vault,
                        max_results=max_results,
                        log_why=False,
                    )
                    for a in acts or []:
                        concept_key = str(a.get("concept") or "")[:80].lower().strip()
                        if concept_key and concept_key not in seen_concepts:
                            seen_concepts.add(concept_key)
                            a["_vault"] = vault  # trazabilidad
                            all_activations.append(a)
                except Exception as _e:
                    logger.debug("Muninn activate vault=%s error: %s", vault, _e)

            activations = all_activations
        except Exception as e:
            logger.warning("Muninn activate error: %s", e)
            return

        candidates = [
            a for a in (activations or []) if (a.get("score", 0) or 0) >= min_score
        ]

        # Dedup por clave (concepto normalizado)
        new_candidates = []
        for c in candidates:
            try:
                key = str(c.get("concept") or "")[:80].lower().strip()
            except Exception:
                key = ""
            if not key:
                continue
            if key not in seen_keys:
                new_candidates.append(c)
                seen_keys.add(key)

        if not new_candidates:
            logger.info("Proactive: sin candidatos nuevos")
            state["last_run_ts"] = time.time()
            state["seen_keys"] = list(seen_keys)[-500:]
            state["sent_timestamps"] = sent_ts
            self._save_state(state)
            return

        # Construir mensaje
        top = new_candidates[:3]
        lines = ["🧠 **Lilith — memoria proactiva**"]
        for item in top:
            score = item.get("score", 0)
            concept = str(item.get("concept") or "")[:80]
            content = (str(item.get("content") or "")[:150]).replace("\n", " ")
            lines.append(f"• **{concept}** *(score: {float(score):.2f})*\n  {content}")
        msg = "\n".join(lines)

        # Notificar — Telegram primero (canal principal), Discord como fallback
        notified = False
        try:
            from src.core.transport.telegram import notify_owner_telegram

            notified = await notify_owner_telegram(msg, urgent=False)
            if notified:
                logger.info(
                    "Proactive: notificación enviada por Telegram (%d items)", len(top)
                )
        except Exception as e:
            logger.debug("Proactive Telegram notify error: %s", e)

        if not notified:
            try:
                from src.core.transport.discord import notify_owner

                await notify_owner(
                    self.base_path,
                    msg,
                    channel_id=cfg.get("notify_channel") or "",
                )
                logger.info(
                    "Proactive: notificación enviada por Discord (%d items)", len(top)
                )
            except Exception as e:
                logger.warning("Proactive notify error: %s", e)
                return

        # Persistir estado
        now = time.time()
        sent_ts = [t for t in (sent_ts or []) if now - float(t) < 3600] + [now]
        state["seen_keys"] = list(seen_keys)[-500:]
        state["sent_timestamps"] = sent_ts
        state["last_run_ts"] = now
        self._save_state(state)

        # Episodio
        try:
            from src.core.episode_builder import build_episode
            from src.core.memory.legacy_adapter import EpisodicStore

            EpisodicStore(self.base_path).append(
                build_episode(
                    summary=msg[:400],
                    outcome="success",
                    source="proactive",
                    channel_name="proactive",
                )
            )
        except Exception:
            pass
