"""
Session Summarizer — Resúmenes de sesión de trabajo.

Triggers:
  1. Inactividad: N minutos sin mensajes en un canal → resumir sesión
  2. Pre-purga: antes de que episodic_cleanup elimine episodios → preservar conocimiento
  3. Bajo demanda: "¿qué hicimos ayer?", "/resumen", "última vez que X"

Almacenamiento: Data/session_summaries.jsonl
Cada resumen tiene: timestamp, channel_id, episode_count, date_range, summary, tags, reason
"""
import json
import logging
import re
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger("lilith.session_summarizer")

# ── Patrones de consulta de resúmenes ────────────────────────────────────────

SUMMARY_QUERY_PATTERNS = [
    r"(?:qué|que)\s+hicimos\s+(.+)",
    r"resumen\s+de\s+(.+)",
    r"(?:última|ultima)\s+vez\s+que\s+(.+)",
    r"/resumen(?:\s+(.+))?",
    r"qué\s+pasó\s+(?:el\s+|la\s+|con\s+)?(.+)",
    r"qu[eé]\s+trabajamos\s+en\s+(.+)",
]
_SUMMARY_RE = re.compile("|".join(SUMMARY_QUERY_PATTERNS), re.IGNORECASE)

# ── Resolución de referencias temporales ─────────────────────────────────────


def _parse_time_reference(query: str) -> str:
    """
    Convierte referencias como 'ayer', 'esta semana', 'lunes' en fecha ISO YYYY-MM-DD.
    Devuelve "" si no reconoce la referencia.
    """
    q = query.lower().strip()
    today = datetime.now(timezone.utc).date()
    if "ayer" in q:
        return (today - timedelta(days=1)).isoformat()
    if any(x in q for x in ("esta semana", "esta week", "semana")):
        monday = today - timedelta(days=today.weekday())
        return monday.isoformat()
    if any(x in q for x in ("este mes", "mes")):
        return today.replace(day=1).isoformat()
    if any(x in q for x in ("hoy", "today")):
        return today.isoformat()
    return ""


# ── LLM Adapter ──────────────────────────────────────────────────────────────


class _OrchestratorLLMAdapter:
    """
    Wraps the orchestrator.execute_plan() as a sync LLM interface.
    Se instancia con lazy import para evitar ciclos de dependencia.
    """

    def generate(self, system: str, prompt: str) -> str:
        try:
            from src.api.dependencies import get_orchestrator

            orch = get_orchestrator()
            result = orch.execute_plan(
                prompt,
                context=system,
                user_id="session_summarizer",
                skip_cache=True,
            )
            return (result or "").strip()
        except Exception as e:
            raise RuntimeError(f"LLM unavailable: {e}") from e


# ── Clase principal ───────────────────────────────────────────────────────────


class SessionSummarizer:
    """
    Genera, persiste y busca resúmenes de sesiones de trabajo.
    """

    def __init__(self, base_path: Path, config: Optional[Dict[str, Any]] = None):
        self.base_path = Path(base_path)
        cfg = config or {}
        self.inactivity_minutes: int = int(cfg.get("session_inactivity_minutes") or 30)
        self.min_episodes: int = int(cfg.get("min_episodes_for_summary") or 5)
        self.search_k: int = int(cfg.get("session_summary_search_k") or 3)
        self.summaries_path = self.base_path / "Data" / "session_summaries.jsonl"
        self.summaries_path.parent.mkdir(parents=True, exist_ok=True)
        self._last_activity: Dict[str, datetime] = {}
        self._llm = _OrchestratorLLMAdapter()

    # ── Tracking de actividad ─────────────────────────────────────────────────

    def record_activity(self, channel_id: str) -> None:
        """Llamar en cada mensaje procesado."""
        self._last_activity[channel_id] = datetime.now(timezone.utc)

    def get_inactive_channels(self) -> List[str]:
        """Devuelve canales con inactividad > threshold."""
        now = datetime.now(timezone.utc)
        inactive = []
        for ch, last in list(self._last_activity.items()):
            if (now - last).total_seconds() > self.inactivity_minutes * 60:
                inactive.append(ch)
        return inactive

    # ── Generación de resúmenes ───────────────────────────────────────────────

    async def summarize_episodes(
        self,
        episodes: List[Dict[str, Any]],
        channel_id: str = "",
        reason: str = "inactivity",
    ) -> Optional[Dict[str, Any]]:
        """
        Genera un resumen a partir de episodios.
        reason: "inactivity" | "pre_purge" | "on_demand"
        """
        if not episodes or len(episodes) < self.min_episodes:
            return None

        episode_lines = []
        for ep in episodes:
            ts = (ep.get("timestamp") or "?")[:16]
            source = ep.get("source") or ep.get("transport") or ""
            summary = str(
                ep.get("summary") or ep.get("content") or ep.get("message") or ""
            )[:300]
            outcome = ep.get("outcome") or ""
            tags = ",".join(ep.get("tags") or [])[:60]
            episode_lines.append(
                f"[{ts}] ({source}) {summary[:200]}"
                + (f" → {outcome}" if outcome else "")
                + (f" [{tags}]" if tags else "")
            )

        episodes_text = "\n".join(episode_lines[:50])  # max 50 líneas

        system = (
            "Eres un asistente que genera resúmenes concisos y útiles de sesiones de trabajo. "
            "Responde solo con el resumen, sin preámbulos ni explicaciones."
        )
        prompt = (
            f"Resume esta sesión de trabajo en 3-5 oraciones concisas en español.\n"
            f"Incluye: qué se hizo, qué herramientas/agentes se usaron, resultado general, "
            f"problemas encontrados si los hubo. Sé específico, no genérico.\n\n"
            f"Episodios ({len(episodes)}):\n{episodes_text}\n\nResumen:"
        )

        try:
            import asyncio

            summary_text = await asyncio.to_thread(self._llm.generate, system, prompt)
        except Exception as e:
            # Fallback mecánico si el LLM no está disponible
            tools_used: set = set()
            sources: set = set()
            for ep in episodes:
                t = ep.get("source") or ep.get("tool") or ""
                if t:
                    tools_used.add(t)
                s = ep.get("source") or ""
                if s:
                    sources.add(s)
            summary_text = (
                f"Sesión con {len(episodes)} interacciones desde "
                f"{', '.join(sources) or 'canal desconocido'}. "
                f"Fuentes: {', '.join(tools_used) or 'N/A'}. "
                f"(Resumen automático — LLM no disponible: {e})"
            )

        tags = self._extract_tags(episodes)
        summary = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "channel_id": channel_id,
            "episode_count": len(episodes),
            "first_episode_ts": (episodes[0].get("timestamp") or ""),
            "last_episode_ts": (episodes[-1].get("timestamp") or ""),
            "summary": summary_text.strip(),
            "tags": tags,
            "reason": reason,
        }
        self._append_summary(summary)
        logger.info(
            "SessionSummarizer: resumen generado (%d episodios, reason=%s)",
            len(episodes),
            reason,
        )
        return summary

    async def summarize_before_purge(
        self, episodes_to_purge: List[Dict[str, Any]]
    ) -> Optional[Dict[str, Any]]:
        """Llamar ANTES de eliminar episodios en cleanup()."""
        if not episodes_to_purge:
            return None
        return await self.summarize_episodes(
            episodes_to_purge, channel_id="all", reason="pre_purge"
        )

    async def check_inactivity_and_summarize(
        self, episodic_store
    ) -> List[Dict[str, Any]]:
        """Revisar canales inactivos y generar resúmenes pendientes."""
        summaries = []
        for channel_id in self.get_inactive_channels():
            unsummarized = episodic_store.get_unsummarized(channel_id=channel_id)
            if len(unsummarized) >= self.min_episodes:
                summary = await self.summarize_episodes(
                    unsummarized, channel_id=channel_id, reason="inactivity"
                )
                if summary:
                    summaries.append(summary)
                    episode_ids = [
                        e.get("id") or e.get("timestamp") or "" for e in unsummarized
                    ]
                    episodic_store.mark_summarized(episode_ids)
            self._last_activity.pop(channel_id, None)
        return summaries

    # ── Búsqueda ──────────────────────────────────────────────────────────────

    def search_summaries(
        self,
        query: str,
        k: int = 3,
        channel_id: str = "",
        after: str = "",
    ) -> List[Dict[str, Any]]:
        """
        Busca en resúmenes por texto libre, canal y/o fecha (after=YYYY-MM-DD).
        """
        summaries = self._load_all_summaries()
        query_lower = query.lower()
        results = []

        for s in reversed(summaries):
            if channel_id and s.get("channel_id", "") not in ("", "all", channel_id):
                continue
            if after and (s.get("timestamp") or "") < after:
                continue
            text_match = query_lower and query_lower in s.get("summary", "").lower()
            tag_match = any(query_lower in t.lower() for t in s.get("tags") or [])
            # Sin query → devolver todos (para /resumen sin args)
            if (not query_lower) or text_match or tag_match:
                results.append(s)
                if len(results) >= k:
                    break

        return results

    def format_for_context(self, summaries: List[Dict[str, Any]]) -> str:
        """Formatea resúmenes para inyectar en el system prompt."""
        if not summaries:
            return ""
        lines = ["[Resúmenes de sesiones relevantes]"]
        for s in summaries:
            first = (s.get("first_episode_ts") or "")[:10]
            last = (s.get("last_episode_ts") or "")[:10]
            date_range = (
                first
                if first == last
                else (f"{first}–{last}" if first and last else first or last)
            )
            count = s.get("episode_count") or "?"
            lines.append(f"- ({date_range}, {count} episodios): {s.get('summary', '')}")
        return "\n".join(lines)

    # ── Detección de query de resumen en mensaje ──────────────────────────────

    @staticmethod
    def detect_summary_query(message: str) -> Optional[str]:
        """
        Si el mensaje es una consulta de resumen, devuelve el término de búsqueda.
        Devuelve None si no es una consulta de resumen.
        """
        m = _SUMMARY_RE.search(message.strip())
        if not m:
            return None
        # El primer grupo no None es el término de búsqueda
        query = next((g for g in m.groups() if g is not None), "") or ""
        return query.strip()

    def answer_summary_query(self, message: str) -> Optional[str]:
        """
        Si el mensaje es una consulta de resumen, busca y devuelve respuesta formateada.
        Devuelve None si no es una consulta (para que el flujo normal procese el mensaje).
        """
        query = self.detect_summary_query(message)
        if query is None:
            return None

        after = _parse_time_reference(query)
        summaries = self.search_summaries(
            query=query,
            k=self.search_k,
            after=after,
        )

        if not summaries:
            return "No encontré resúmenes que coincidan con eso."

        lines = ["Esto es lo que encontré:\n"]
        for s in summaries:
            date = (s.get("first_episode_ts") or s.get("timestamp") or "")[:10]
            count = s.get("episode_count") or "?"
            lines.append(f"**{date}** ({count} episodios):\n{s.get('summary', '')}\n")
        return "\n".join(lines).strip()

    # ── Helpers internos ──────────────────────────────────────────────────────

    def _extract_tags(self, episodes: List[Dict[str, Any]]) -> List[str]:
        tags: set = set()
        for ep in episodes:
            source = ep.get("source") or ""
            if source:
                tags.add(source)
            for t in ep.get("tags") or []:
                if t:
                    tags.add(str(t))
        return list(tags)[:20]

    def _append_summary(self, summary: Dict[str, Any]) -> None:
        try:
            with open(self.summaries_path, "a", encoding="utf-8") as f:
                f.write(json.dumps(summary, ensure_ascii=False) + "\n")
        except Exception as e:
            logger.warning("SessionSummarizer append error: %s", e)

    def _load_all_summaries(self) -> List[Dict[str, Any]]:
        if not self.summaries_path.exists():
            return []
        summaries = []
        try:
            with open(self.summaries_path, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if line:
                        try:
                            summaries.append(json.loads(line))
                        except json.JSONDecodeError:
                            continue
        except Exception as e:
            logger.warning("SessionSummarizer load error: %s", e)
        return summaries


# ── Singleton por base_path ───────────────────────────────────────────────────

_instances: Dict[str, SessionSummarizer] = {}


def get_session_summarizer(base_path: Path) -> SessionSummarizer:
    """Devuelve (o crea) la instancia singleton de SessionSummarizer para la base_path dada."""
    key = str(Path(base_path).resolve())
    if key not in _instances:
        try:
            from src.core.json_safe import safe_load

            cfg = safe_load(Path(base_path) / "Config" / "memory.json", default={})
            cfg = cfg if isinstance(cfg, dict) else {}
        except Exception:
            cfg = {}
        _instances[key] = SessionSummarizer(base_path, config=cfg)
    return _instances[key]
