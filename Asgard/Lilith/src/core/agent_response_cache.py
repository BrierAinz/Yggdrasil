"""
Lilith 3.5 B.1 — Cache de respuestas de agentes.
Guarda en Data/cache/ la respuesta de delegate_* por (tool_name, task, context) con TTL configurable.
"""
import hashlib
import json
import logging
from pathlib import Path
from typing import Any, Dict, Optional

logger = logging.getLogger("AgentCache")

CACHE_DIR_NAME = "Data/cache"
CACHE_AGENT_KEYS = (
    "delegate_eva",
    "delegate_adan",
    "delegate_lucifer",
    "delegate_odin",
    "delegate_local_irreverent",
)
DEFAULT_TTL_SECONDS = 3600
DEFAULT_CACHE_MAX_FILES = 200


def _cache_dir(base_path: Path) -> Path:
    d = base_path / CACHE_DIR_NAME
    d.mkdir(parents=True, exist_ok=True)
    return d


def _ttl_seconds(base_path: Path) -> int:
    try:
        from src.core.json_safe import safe_load

        cfg = safe_load(base_path / "Config" / "memory.json", default={})
        return int(cfg.get("agent_cache_ttl_seconds") or 0) or DEFAULT_TTL_SECONDS
    except Exception:
        return DEFAULT_TTL_SECONDS


def _cache_max_files(base_path: Path) -> int:
    """Límite de archivos en Data/cache/; si se supera, se podan los más viejos."""
    try:
        from src.core.json_safe import safe_load

        cfg = safe_load(base_path / "Config" / "memory.json", default={})
        return int(cfg.get("agent_cache_max_files") or 0) or DEFAULT_CACHE_MAX_FILES
    except Exception:
        return DEFAULT_CACHE_MAX_FILES


def _prune_cache(base_path: Path) -> None:
    """Mantiene solo los agent_cache_max_files más recientes; elimina el resto."""
    try:
        d = _cache_dir(base_path)
        files = list(d.glob("agent_*.json"))
        if not files:
            return
        max_files = _cache_max_files(base_path)
        if len(files) <= max_files:
            return
        by_mtime = sorted(files, key=lambda p: p.stat().st_mtime, reverse=True)
        for old in by_mtime[max_files:]:
            try:
                old.unlink(missing_ok=True)
            except Exception:
                pass
        logger.debug("AgentCache: pruned to %d files (max=%d)", max_files, max_files)
    except Exception as e:
        logger.debug("AgentCache prune: %s", e)


def _key(tool_name: str, params: Dict[str, Any]) -> str:
    """Incluye el final del context (donde va el mensaje del usuario) para evitar colisiones."""
    task = (params.get("task") or "").strip()[:2000]
    context = (params.get("context") or "").strip()
    # El mensaje del usuario suele estar al final; truncar solo el inicio dejaría la misma clave
    context_suffix = context[-1500:] if len(context) > 1500 else context
    raw = f"{tool_name}|{task}|{context_suffix}"
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:32]


def _cache_path(base_path: Path, key: str) -> Path:
    return _cache_dir(base_path) / f"agent_{key}.json"


def get(
    base_path: Optional[Path], tool_name: str, params: Dict[str, Any]
) -> Optional[Dict[str, Any]]:
    """Devuelve la respuesta cacheada si existe y no ha expirado."""
    if not base_path or tool_name not in CACHE_AGENT_KEYS:
        return None
    try:
        import time

        path = _cache_path(Path(base_path), _key(tool_name, params))
        if not path.exists():
            return None
        data = json.loads(path.read_text(encoding="utf-8"))
        ts = data.get("_ts", 0)
        if time.time() - ts > _ttl_seconds(Path(base_path)):
            path.unlink(missing_ok=True)
            return None
        return data.get("result")
    except Exception as e:
        logger.debug("AgentCache get: %s", e)
        return None


def set(
    base_path: Optional[Path],
    tool_name: str,
    params: Dict[str, Any],
    result: Dict[str, Any],
) -> None:
    """Guarda la respuesta en caché y poda si se supera agent_cache_max_files."""
    if not base_path or tool_name not in CACHE_AGENT_KEYS:
        return
    try:
        import time

        base = Path(base_path)
        path = _cache_path(base, _key(tool_name, params))
        path.write_text(
            json.dumps({"_ts": time.time(), "result": result}, ensure_ascii=False),
            encoding="utf-8",
        )
        _prune_cache(base)
    except Exception as e:
        logger.debug("AgentCache set: %s", e)
