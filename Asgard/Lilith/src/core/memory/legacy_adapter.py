import json
import logging
import re
from dataclasses import asdict, dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger("lilith.episodic")


@dataclass
class Episode:
    timestamp: str
    summary: str
    project_id: str
    outcome: str  # "success" | "failure" | "partial"
    tags: List[str]
    source: str  # "investiga" | "chat" | "auto_delegate" | ...
    channel_id: Optional[str] = None
    message_id: Optional[str] = None
    url: Optional[str] = None

    # NUEVOS CAMPOS 4.2 - Enriquecimiento
    emotional_tag: Optional[
        str
    ] = None  # "frustrating" | "successful" | "routine" | "exciting"
    context_snapshot: Optional[Dict[str, Any]] = None  # Estado relevante en ese momento
    tool_used: Optional[str] = None
    user_id: Optional[str] = None

    # Metadata adicional
    id: Optional[str] = None
    summarized: bool = False


class EpisodicStore:
    """
    Episodios enriquecidos (4.2): JSONL con campos extendidos.
    Uso: append() para guardar; search() para consultas tipo "última vez que...".
    """

    def __init__(self, base_path: Path):
        self.base_path = Path(base_path)
        self.path = Path(base_path) / "Data" / "episodic_log.jsonl"
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def append(self, episode: Episode) -> None:
        """Guarda un episodio enriquecido."""
        try:
            # Generar ID si no existe
            if not episode.id:
                episode.id = self._generate_id(episode)

            with open(self.path, "a", encoding="utf-8") as f:
                f.write(json.dumps(asdict(episode), ensure_ascii=False) + "\n")

            logger.info(
                f"[EpisodicStore] Saved episode with project_id: {episode.project_id}, "
                f"outcome: {episode.outcome}, tags: {episode.tags}"
            )
        except Exception as e:
            logger.warning(f"[EpisodicStore] Error saving episode: {e}")
            return

        # MuninnDB (memoria cognitiva): espejo de episodios
        try:
            from src.core.memory.muninn_memory import (
                MuninnMemory,
                _run_coro_fire_and_forget,
            )

            _run_coro_fire_and_forget(
                MuninnMemory(self.base_path).write_episode(
                    concept=f"{episode.source}: {(episode.summary or '')[:100]}",
                    content=episode.summary or "",
                    tags=episode.tags or [],
                )
            )
        except Exception as _e:
            logger.debug("Muninn espejo falló: %s", _e)

        # Grafo (mínimo): relaciones a partir de URL/tags del episodio
        try:
            from src.core.graph_relations import extract_edges, save_edges_to_muninn
            from src.core.memory.muninn_memory import _run_coro_fire_and_forget

            edges = extract_edges(
                concept=f"{episode.source}: {(episode.summary or '')[:80]}",
                content=episode.summary or "",
                tags=episode.tags or [],
                url=episode.url or "",
                topic=episode.project_id or episode.source,
            )
            _run_coro_fire_and_forget(save_edges_to_muninn(edges, self.base_path))
        except Exception as _e:
            logger.debug("graph_relations falló: %s", _e)

    def _generate_id(self, episode: Episode) -> str:
        """Genera ID único para episodio."""
        import hashlib

        base = f"{episode.timestamp}:{episode.source}:{episode.summary[:50]}"
        return hashlib.sha256(base.encode()).hexdigest()[:16]

    def search(
        self,
        project_id: Optional[str] = None,
        tag: Optional[str] = None,
        outcome: Optional[str] = None,
        emotional_tag: Optional[str] = None,
        tool_used: Optional[str] = None,
        limit: int = 5,
    ) -> List[Dict[str, Any]]:
        """Búsqueda avanzada de episodios con múltiples filtros."""
        if not self.path.exists():
            return []
        results: List[Dict[str, Any]] = []
        try:
            with open(self.path, "r", encoding="utf-8") as f:
                for line in f:
                    try:
                        d = json.loads(line)
                        if project_id and d.get("project_id") != project_id:
                            continue
                        if outcome and d.get("outcome") != outcome:
                            continue
                        if tag and tag not in (d.get("tags") or []):
                            continue
                        if emotional_tag and d.get("emotional_tag") != emotional_tag:
                            continue
                        if tool_used and d.get("tool_used") != tool_used:
                            continue
                        results.append(d)
                    except Exception:
                        continue
        except Exception:
            return []
        # Más recientes primero
        results.reverse()
        return results[: limit if limit > 0 else 5]

    def query_by_outcome(
        self, outcome: str, project_id: Optional[str] = None, limit: int = 10
    ) -> List[Dict[str, Any]]:
        """
        Consulta episodios por outcome.
        Ej: "última vez que deployment falló en proyecto X"
        """
        return self.search(outcome=outcome, project_id=project_id, limit=limit)

    def query_by_project(
        self,
        project_id: str,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        limit: int = 50,
    ) -> List[Dict[str, Any]]:
        """
        Obtiene timeline de proyecto.
        """
        episodes = self._load_all()
        filtered = []

        for ep in episodes:
            if ep.get("project_id") != project_id:
                continue

            ts_str = ep.get("timestamp", "")
            try:
                ep_date = datetime.fromisoformat(ts_str.replace("Z", "+00:00"))

                if start_date:
                    start_dt = datetime.fromisoformat(start_date)
                    if ep_date < start_dt:
                        continue
                if end_date:
                    end_dt = datetime.fromisoformat(end_date)
                    if ep_date > end_dt:
                        continue

                filtered.append(ep)
            except Exception:
                continue

        # Ordenar por fecha (más recientes primero)
        filtered.sort(key=lambda x: x.get("timestamp", ""), reverse=True)
        return filtered[:limit]

    def update_episode(self, episode_id: str, updates: Dict[str, Any]) -> bool:
        """
        Actualiza un episodio existente (ej: añadir emotional_tag).
        """
        all_eps = self._load_all()
        found = False

        for ep in all_eps:
            if ep.get("id") == episode_id or ep.get("timestamp") == episode_id:
                ep.update(updates)
                found = True
                logger.info(f"[EpisodicStore] Updated episode {episode_id}")
                break

        if found:
            self._rewrite(all_eps)

        return found

    def get_episode_by_id(self, episode_id: str) -> Optional[Dict[str, Any]]:
        """Obtiene un episodio por ID."""
        all_eps = self._load_all()
        for ep in all_eps:
            if ep.get("id") == episode_id or ep.get("timestamp") == episode_id:
                return ep
        return None

    def get_stats_by_project(self, project_id: str) -> Dict[str, Any]:
        """
        Obtiene estadísticas de un proyecto.
        """
        episodes = self.query_by_project(project_id)

        if not episodes:
            return {"total": 0}

        # Contar por outcome
        outcomes = {}
        emotions = {}
        tags_count = {}

        for ep in episodes:
            # Outcomes
            out = ep.get("outcome", "unknown")
            outcomes[out] = outcomes.get(out, 0) + 1

            # Emotional tags
            emotion = ep.get("emotional_tag")
            if emotion:
                emotions[emotion] = emotions.get(emotion, 0) + 1

            # Tags
            for tag in ep.get("tags", []):
                tags_count[tag] = tags_count.get(tag, 0) + 1

        return {
            "project_id": project_id,
            "total": len(episodes),
            "outcomes": outcomes,
            "emotional_breakdown": emotions,
            "top_tags": sorted(tags_count.items(), key=lambda x: x[1], reverse=True)[
                :10
            ],
            "success_rate": outcomes.get("success", 0) / len(episodes)
            if episodes
            else 0,
        }

    # ── Helpers internos ─────────────────────────────────────────────────────

    def _load_all(self) -> List[Dict[str, Any]]:
        """Carga todos los episodios del JSONL. Devuelve lista vacía si no existe."""
        if not self.path.exists():
            return []
        out: List[Dict[str, Any]] = []
        try:
            with open(self.path, "r", encoding="utf-8") as f:
                for line in f:
                    try:
                        out.append(json.loads(line))
                    except Exception:
                        continue
        except Exception as e:
            logger.warning("EpisodicStore _load_all error: %s", e)
        return out

    def _rewrite(self, episodes: List[Dict[str, Any]]) -> None:
        """Reescribe el JSONL con los episodios dados (reemplaza el fichero)."""
        try:
            with open(self.path, "w", encoding="utf-8") as f:
                for ep in episodes:
                    f.write(json.dumps(ep, ensure_ascii=False) + "\n")
        except Exception as e:
            logger.warning("EpisodicStore _rewrite error: %s", e)

    # ── Episodios no resumidos / marcado ──────────────────────────────────────

    def get_unsummarized(self, channel_id: str = "") -> List[Dict[str, Any]]:
        """Devuelve episodios que no han sido resumidos, filtrados por canal si se especifica."""
        all_eps = self._load_all()
        results = []
        for ep in all_eps:
            if ep.get("summarized"):
                continue
            if channel_id:
                ep_ch = ep.get("source") or ep.get("channel_id") or ""
                if ep_ch != channel_id:
                    continue
            results.append(ep)
        return results

    def mark_summarized(self, episode_ids: List[str]) -> None:
        """Marca episodios como ya resumidos (por id o timestamp)."""
        if not episode_ids:
            return
        ids_set = set(episode_ids)
        all_eps = self._load_all()
        modified = False
        for ep in all_eps:
            ep_id = ep.get("id") or ep.get("timestamp") or ""
            if ep_id in ids_set and not ep.get("summarized"):
                ep["summarized"] = True
                modified = True
        if modified:
            self._rewrite(all_eps)

    def get_purgeable(
        self,
        max_episodes: int = 5000,
        retention_days: int = 90,
    ) -> tuple:
        """
        Calcula qué episodios serían purgados por cleanup() SIN modificar el fichero.
        Devuelve (kept: List, purged: List).
        """
        all_episodes = self._load_all()
        cutoff = datetime.now(timezone.utc) - timedelta(days=retention_days)
        kept: List[Dict[str, Any]] = []
        for ep in all_episodes:
            ts_str = ep.get("timestamp") or ""
            try:
                dt = datetime.fromisoformat(str(ts_str).replace("Z", "+00:00"))
                if dt.tzinfo is None:
                    dt = dt.replace(tzinfo=timezone.utc)
                if dt >= cutoff:
                    kept.append(ep)
            except Exception:
                kept.append(ep)
        if len(kept) > max_episodes:
            kept = kept[-max_episodes:]
        kept_set = {id(ep) for ep in kept}
        purged = [ep for ep in all_episodes if id(ep) not in kept_set]
        return kept, purged

    def cleanup(
        self,
        max_episodes: int = 5000,
        retention_days: int = 90,
    ) -> Dict[str, Any]:
        """
        Mejora-3: poda episodios viejos por dos criterios.
        Devuelve resumen {total_before, kept, removed, reason}.
        """
        all_episodes = self._load_all()
        total_before = len(all_episodes)
        if not all_episodes:
            return {"total_before": 0, "kept": 0, "removed": 0}

        kept, _ = self.get_purgeable(max_episodes, retention_days)
        removed = total_before - len(kept)
        if removed > 0:
            self._rewrite(kept)
            logger.info(
                "EpisodicStore cleanup: %d eliminados, %d conservados (retention=%dd, max=%d)",
                removed,
                len(kept),
                retention_days,
                max_episodes,
            )
        return {"total_before": total_before, "kept": len(kept), "removed": removed}

    def recent_since(self, *, since_ts: float, limit: int = 50) -> List[Dict[str, Any]]:
        """Devuelve episodios con timestamp >= since_ts (epoch seconds)."""
        if not self.path.exists():
            return []
        out: List[Dict[str, Any]] = []
        try:
            with open(self.path, "r", encoding="utf-8") as f:
                for line in f:
                    try:
                        d = json.loads(line)
                        ts = d.get("timestamp")
                        if not ts:
                            continue
                        # timestamp ISO UTC
                        dt = datetime.fromisoformat(str(ts).replace("Z", "+00:00"))
                        if dt.tzinfo is None:
                            dt = dt.replace(tzinfo=timezone.utc)
                        if dt.timestamp() < float(since_ts):
                            continue
                        out.append(d)
                    except Exception:
                        continue
        except Exception:
            return []
        out.sort(key=lambda x: x.get("timestamp") or "", reverse=True)
        return out[: max(1, min(200, int(limit or 50)))]
