"""
Pre-4.0: Adapter para MuninnDB (memoria cognitiva).
Expone write() y activate() con config desde Config/muninn.json.
Usa SDK (muninn.MuninnClient) si está disponible; si no, usa la API REST vía httpx.
Si muninn_enabled es false, todas las operaciones son no-op / fallback.
Ver: PRE_4.0_MUNINNDB.md
"""
import asyncio
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger("MuninnAdapter")

_MUNINN_SDK_AVAILABLE: Optional[bool] = None


def _check_sdk() -> bool:
    global _MUNINN_SDK_AVAILABLE
    if _MUNINN_SDK_AVAILABLE is not None:
        return _MUNINN_SDK_AVAILABLE
    try:
        from muninn import MuninnClient  # noqa: F401

        _MUNINN_SDK_AVAILABLE = True
    except ImportError:
        _MUNINN_SDK_AVAILABLE = False
    return _MUNINN_SDK_AVAILABLE


def _load_config(base_path: Optional[Path] = None) -> Dict[str, Any]:
    if base_path is None:
        base_path = Path(__file__).resolve().parent.parent.parent.parent
    try:
        from src.core.json_safe import safe_load

        path = Path(base_path) / "Config" / "muninn.json"
        if path.exists():
            cfg = safe_load(path, default={})
            return cfg if isinstance(cfg, dict) else {}
        mem_path = Path(base_path) / "Config" / "memory.json"
        cfg = safe_load(mem_path, default={})
        if isinstance(cfg, dict) and any(k.startswith("muninn_") for k in cfg):
            return {k: v for k, v in cfg.items() if k.startswith("muninn_")}
    except Exception as e:
        logger.debug("MuninnAdapter config load: %s", e)
    return {}


def is_enabled(base_path: Optional[Path] = None) -> bool:
    """True si muninn_enabled=true en config. No requiere SDK (se usa API REST de respaldo)."""
    cfg = _load_config(base_path)
    return bool(cfg.get("muninn_enabled"))


def _muninn_token_from_env() -> str:
    """Token por defecto: ~/.muninn/mcp.token (el mismo que usa Cursor/MCP)."""
    try:
        home = Path.home()
        for name in (".muninn", "muninn"):
            p = home / name / "mcp.token"
            if p.exists():
                t = p.read_text(encoding="utf-8", errors="ignore").strip()
                if t:
                    return t
    except Exception:
        pass
    return ""


def _rest_base(base_path: Optional[Path]) -> tuple:
    cfg = _load_config(base_path)
    url = (cfg.get("muninn_url") or "http://localhost:8475").strip().rstrip("/")
    token = (cfg.get("muninn_token") or "").strip() or _muninn_token_from_env()
    return url, token


def _activate_rest(
    base_path: Optional[Path], context: List[str], top_k: int, vault: str
) -> List[Dict[str, Any]]:
    """Activate vía POST /api/activate (httpx)."""
    base_url, token = _rest_base(base_path)
    api_url = f"{base_url}/api/activate"
    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    payload = {
        "vault": vault,
        "context": [str(c) for c in context],
        "max_results": max(1, min(top_k, 50)),
    }
    try:
        import httpx

        with httpx.Client(timeout=10.0) as client:
            r = client.post(api_url, json=payload, headers=headers)
            r.raise_for_status()
            data = r.json()
    except Exception as e:
        logger.warning("MuninnAdapter REST activate failed: %s", e)
        return []
    out: List[Dict[str, Any]] = []
    items = (
        data
        if isinstance(data, list)
        else (data.get("activations") or data.get("results") or [])
    )
    if not isinstance(items, list):
        items = []
    for item in items[:top_k]:
        if isinstance(item, dict):
            text = (item.get("content") or item.get("concept") or "").strip()
            if text:
                out.append(
                    {
                        "text": text,
                        "concept": (item.get("concept") or "")[:200],
                        "score": float(item.get("score") or 0),
                        "why": str(item.get("why") or ""),
                    }
                )
    return out


def _write_rest(
    base_path: Optional[Path],
    vault: str,
    concept: str,
    content: str,
    tags: List[str],
) -> Optional[str]:
    """Write vía POST /api/engrams (httpx)."""
    base_url, token = _rest_base(base_path)
    api_url = f"{base_url}/api/engrams"
    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    payload = {
        "vault": vault,
        "concept": concept.strip()[:500],
        "content": content.strip()[:4000],
        "tags": tags[:20] if tags else [],
    }
    try:
        import httpx

        with httpx.Client(timeout=10.0) as client:
            r = client.post(api_url, json=payload, headers=headers)
            r.raise_for_status()
            data = r.json()
            return data.get("id") if isinstance(data, dict) else None
    except Exception as e:
        logger.warning("MuninnAdapter REST write failed: %s", e)
        return None


def write(
    base_path: Optional[Path],
    vault: Optional[str],
    concept: str,
    content: str,
    tags: Optional[List[str]] = None,
) -> Optional[str]:
    """
    Guarda un engrama en MuninnDB. Retorna el id del engrama o None si falla/deshabilitado.
    Usa SDK si está disponible; si no, API REST.
    """
    if not is_enabled(base_path) or not concept or not content:
        return None
    cfg = _load_config(base_path)
    url = (cfg.get("muninn_url") or "http://localhost:8475").strip()
    token = (cfg.get("muninn_token") or "").strip() or _muninn_token_from_env()
    v = (vault or cfg.get("muninn_vault") or "default").strip()
    tags = tags or []

    if _check_sdk():

        async def _do_write() -> Optional[str]:
            try:
                from muninn import MuninnClient

                async with MuninnClient(url, token=token or None) as client:
                    eid = await client.write(
                        vault=v,
                        concept=concept.strip()[:500],
                        content=content.strip()[:4000],
                        tags=tags[:20] if tags else None,
                    )
                    return str(eid) if eid is not None else None
            except Exception as e:
                logger.warning("MuninnAdapter write failed: %s", e)
                return None

        try:
            return asyncio.run(_do_write())
        except Exception as e:
            logger.warning("MuninnAdapter write: %s", e)
            return None
    return _write_rest(base_path, v, concept, content, tags)


def _delete_rest(base_path: Optional[Path], vault: str, engram_id: str) -> bool:
    """DELETE /api/engrams/{id}?vault=... (soft-delete en Muninn)."""
    base_url, token = _rest_base(base_path)
    api_url = f"{base_url}/api/engrams/{engram_id}"
    params = {"vault": vault}
    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    try:
        import httpx

        with httpx.Client(timeout=10.0) as client:
            r = client.delete(api_url, params=params, headers=headers)
            r.raise_for_status()
            return True
    except Exception as e:
        logger.warning("MuninnAdapter REST delete engram failed: %s", e)
        return False


def delete_engram(
    base_path: Optional[Path],
    vault: Optional[str],
    engram_id: str,
) -> bool:
    """
    Elimina (soft-delete) un engrama en MuninnDB por id.
    Útil para cuaderno cuando un ítem pasa de important=true a false (§6.3.1).
    """
    if not is_enabled(base_path) or not engram_id:
        return False
    cfg = _load_config(base_path)
    v = (vault or cfg.get("muninn_vault") or "default").strip()
    return _delete_rest(base_path, v, engram_id)


def activate(
    base_path: Optional[Path],
    context: List[str],
    top_k: Optional[int] = None,
    vault: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """
    Recupera las memorias más relevantes para el contexto.
    Usa SDK si está disponible; si no, API REST (POST /api/activate).
    """
    if not is_enabled(base_path) or not context:
        return []
    cfg = _load_config(base_path)
    url = (cfg.get("muninn_url") or "http://localhost:8475").strip()
    token = (cfg.get("muninn_token") or "").strip() or _muninn_token_from_env()
    v = (vault or cfg.get("muninn_vault") or "default").strip()
    k = top_k if top_k is not None else int(cfg.get("muninn_activate_top_k") or 5)

    if _check_sdk():

        async def _do_activate() -> List[Dict[str, Any]]:
            out: List[Dict[str, Any]] = []
            try:
                from muninn import MuninnClient

                async with MuninnClient(url, token=token or None) as client:
                    results = await client.activate(
                        vault=v,
                        context=context
                        if isinstance(context, list)
                        else [str(c) for c in context],
                        max_results=k,
                    )
                    activations = getattr(results, "activations", [])
                    if not isinstance(activations, list):
                        activations = []
                    for item in activations[:k]:
                        concept_val = getattr(item, "concept", None) or (
                            item.get("concept") if isinstance(item, dict) else ""
                        )
                        content_val = getattr(item, "content", None) or (
                            item.get("content") if isinstance(item, dict) else ""
                        )
                        score = getattr(item, "score", None) or (
                            item.get("score") if isinstance(item, dict) else 0
                        )
                        why = getattr(item, "why", None) or (
                            item.get("why") if isinstance(item, dict) else ""
                        )
                        text = (content_val or concept_val or "").strip()
                        if text:
                            out.append(
                                {
                                    "text": text,
                                    "concept": (concept_val or "")[:200],
                                    "score": float(score) if score is not None else 0,
                                    "why": str(why) if why else "",
                                }
                            )
            except Exception as e:
                logger.warning("MuninnAdapter activate failed: %s", e)
            return out

        try:
            return asyncio.run(_do_activate())
        except Exception as e:
            logger.warning("MuninnAdapter activate: %s", e)
            return []
    return _activate_rest(base_path, context, k, v)
