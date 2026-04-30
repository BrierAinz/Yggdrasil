"""
Lilith v2.2 — Fase D: API de memoria para el panel MEMORIA en la UI.
GET /api/memory/semantic | episodic | procedural
"""
import json
import logging
from pathlib import Path
from typing import Any, Dict, List

from fastapi import APIRouter

logger = logging.getLogger("MemoryAPI")

router = APIRouter(prefix="/api/memory", tags=["Memory"])


def _project_root() -> Path:
    return Path(__file__).resolve().parent.parent.parent


@router.get("/semantic")
async def get_memory_semantic() -> Dict[str, Any]:
    """user_profile + últimas 5 entradas de architecture_decisions."""
    root = _project_root()
    out: Dict[str, Any] = {"user_profile": {}, "architecture_decisions": []}
    for name in ("memory", "Memory"):
        base = root / name
        if not base.exists():
            continue
        sem = base / "semantic"
        if sem.exists():
            pf = sem / "user_profile.json"
            if pf.exists():
                try:
                    with open(pf, "r", encoding="utf-8") as f:
                        out["user_profile"] = json.load(f)
                except Exception as e:
                    logger.warning("Failed to load user_profile: %s", e)
            ad = sem / "architecture_decisions.json"
            if ad.exists():
                try:
                    with open(ad, "r", encoding="utf-8") as f:
                        data = json.load(f)
                        out["architecture_decisions"] = (
                            data if isinstance(data, list) else []
                        )[-5:]
                except Exception as e:
                    logger.warning("Failed to load architecture_decisions: %s", e)
            break
    return out


@router.get("/episodic")
async def get_memory_episodic() -> Dict[str, Any]:
    """Últimos 10 session summaries (*_summary.json)."""
    root = _project_root()
    summaries: List[Dict[str, Any]] = []
    for name in ("Memory", "memory"):
        sessions_dir = root / name / "sessions"
        if not sessions_dir.exists():
            continue
        files = sorted(
            sessions_dir.glob("*_summary.json"),
            key=lambda p: p.stat().st_mtime,
            reverse=True,
        )
        for p in files[:10]:
            try:
                with open(p, "r", encoding="utf-8") as f:
                    data = json.load(f)
                session_id = data.get("session_id", p.stem.replace("_summary", ""))
                summaries.append(
                    {
                        "session_id": session_id,
                        "resumen": data.get("resumen", ""),
                        "temas": data.get("temas", []),
                        "generated_at": data.get("generated_at", ""),
                    }
                )
            except Exception as e:
                logger.warning("Failed to load summary %s: %s", p.name, e)
        break
    return {"summaries": summaries}


@router.get("/procedural")
async def get_memory_procedural() -> Dict[str, Any]:
    """error_history + patterns."""
    root = _project_root()
    out: Dict[str, Any] = {"error_history": [], "patterns": {}}
    for name in ("memory", "Memory"):
        proc = root / name / "procedural"
        if not proc.exists():
            continue
        eh = proc / "error_history.json"
        if eh.exists():
            try:
                with open(eh, "r", encoding="utf-8") as f:
                    data = json.load(f)
                out["error_history"] = data if isinstance(data, list) else []
            except Exception as e:
                logger.warning("Failed to load error_history: %s", e)
        pt = proc / "patterns.json"
        if pt.exists():
            try:
                with open(pt, "r", encoding="utf-8") as f:
                    out["patterns"] = json.load(f)
            except Exception as e:
                logger.warning("Failed to load patterns: %s", e)
        break
    return out
