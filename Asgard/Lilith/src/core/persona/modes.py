"""
ModeStore: modo de personalidad por canal/hilo (Discord).
Persistencia en Core/Memory/discord/mode_by_channel.json; clave por channel_id y opcional thread_id.
"""
import json
import logging
from pathlib import Path
from typing import Any, Dict, Optional

logger = logging.getLogger("ModeStore")

_CACHE: Dict[str, str] = {}
_CACHE_LOADED = False
_MODES_CONFIG: Optional[Dict[str, Dict[str, Any]]] = None


def _project_root_from_api() -> Path:
    return Path(__file__).resolve().parent.parent.parent


def _store_path(base_path: Optional[Path] = None) -> Path:
    root = base_path or _project_root_from_api()
    d = root / "Memory" / "discord"
    d.mkdir(parents=True, exist_ok=True)
    return d / "mode_by_channel.json"


def _key(channel_id: str, thread_id: Optional[str]) -> str:
    c = (channel_id or "").strip()
    t = (thread_id or "").strip()
    if not c:
        return ""
    if t:
        return f"{c}:{t}"
    return c


def _load_store(base_path: Optional[Path] = None) -> Dict[str, str]:
    """Carga el JSON de persistencia; devuelve dict key -> mode_id."""
    global _CACHE, _CACHE_LOADED
    path = _store_path(base_path)
    if not path.exists():
        _CACHE = {}
        _CACHE_LOADED = True
        return _CACHE
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        if isinstance(data, dict):
            _CACHE = {
                k: str(v).strip().lower() or "default"
                for k, v in data.items()
                if k and not k.startswith("_")
            }
        else:
            _CACHE = {}
        _CACHE_LOADED = True
        return _CACHE
    except Exception as e:
        logger.warning("ModeStore: no se pudo cargar %s: %s", path, e)
        _CACHE = {}
        _CACHE_LOADED = True
        return _CACHE


def _save_store(base_path: Optional[Path] = None) -> bool:
    global _CACHE
    path = _store_path(base_path)
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(_CACHE, f, ensure_ascii=False, indent=2)
        return True
    except Exception as e:
        logger.warning("ModeStore: no se pudo guardar %s: %s", path, e)
        return False


def _ensure_loaded(base_path: Optional[Path] = None) -> None:
    global _CACHE_LOADED
    if not _CACHE_LOADED:
        _load_store(base_path)


def get_mode(
    base_path: Optional[Path], channel_id: Optional[str], thread_id: Optional[str]
) -> str:
    """
    Devuelve el mode_id para el canal/hilo. Si hay thread_id, se busca primero clave channel:thread.
    Si no hay thread, se usa clave channel. Si no hay entrada, devuelve "default".
    """
    c = (channel_id or "").strip()
    if not c:
        return "default"
    _ensure_loaded(base_path)
    t = (thread_id or "").strip()
    # Primero thread, luego canal
    if t:
        key_thread = _key(c, t)
        if key_thread and key_thread in _CACHE:
            return _CACHE[key_thread]
    key_chan = _key(c, None)
    return _CACHE.get(key_chan, "default")


def set_mode(
    base_path: Optional[Path],
    channel_id: Optional[str],
    thread_id: Optional[str],
    mode_id: str,
) -> bool:
    """Establece el modo para el canal/hilo. mode_id debe existir en modos_lilith.json. Devuelve True si se guardó."""
    c = (channel_id or "").strip()
    if not c:
        return False
    mode_id = (mode_id or "default").strip().lower() or "default"
    if not _mode_defined(base_path, mode_id):
        return False
    _ensure_loaded(base_path)
    key = _key(c, (thread_id or "").strip() or None)
    if not key:
        return False
    _CACHE[key] = mode_id
    return _save_store(base_path)


def _load_modos_config(base_path: Optional[Path] = None) -> Dict[str, Dict[str, Any]]:
    """Carga Core/Config/modos_lilith.json y devuelve dict mode_id -> { system_prefix, name, ... }."""
    global _MODES_CONFIG
    if _MODES_CONFIG is not None:
        return _MODES_CONFIG
    root = base_path or _project_root_from_api()
    path = root / "Config" / "modos_lilith.json"
    out = {}
    if path.exists():
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
            for m in (
                (data.get("modes") or data)
                if isinstance(data.get("modes"), list)
                else (data if isinstance(data, list) else [])
            ):
                if isinstance(m, dict) and m.get("id"):
                    mid = (m.get("id") or "").strip().lower()
                    if mid:
                        out[mid] = m
        except Exception as e:
            logger.warning("ModeStore: no se pudo cargar modos_lilith.json: %s", e)
    # Fallback: persona_modes.json (solo system_prefix como string)
    if not out:
        path_legacy = root / "Config" / "persona_modes.json"
        if path_legacy.exists():
            try:
                with open(path_legacy, "r", encoding="utf-8") as f:
                    leg = json.load(f)
                for k, v in (leg or {}).items():
                    if k.startswith("_"):
                        continue
                    out[(k or "").strip().lower() or "default"] = {
                        "id": k,
                        "system_prefix": v or "",
                        "name": k,
                    }
            except Exception:
                pass
    _MODES_CONFIG = out
    return out


def _mode_defined(base_path: Optional[Path], mode_id: str) -> bool:
    if (mode_id or "").strip().lower() in ("default", ""):
        return True
    modes = _load_modos_config(base_path)
    return (mode_id or "").strip().lower() in modes


def get_mode_overlay(
    base_path: Optional[Path], channel_id: Optional[str], thread_id: Optional[str]
) -> str:
    """
    Devuelve el bloque a inyectar en el system prompt: "[Modo_Activo]\\n" + system_prefix.
    Si el modo es default o no hay system_prefix, devuelve "".
    """
    mode_id = get_mode(base_path, channel_id, thread_id)
    if (mode_id or "").strip().lower() in ("default", ""):
        return ""
    modes = _load_modos_config(base_path)
    m = modes.get((mode_id or "").strip().lower())
    if not m:
        return ""
    prefix = (m.get("system_prefix") or "").strip()
    if not prefix:
        return ""
    return "[Modo_Activo]\n" + prefix


def list_modes(base_path: Optional[Path] = None) -> list:
    """Lista los modos definidos: [ { id, name, description } ]."""
    modes = _load_modos_config(base_path)
    return [
        {
            "id": mid,
            "name": m.get("name") or mid,
            "description": (m.get("description") or "")[:200],
        }
        for mid, m in modes.items()
    ]
