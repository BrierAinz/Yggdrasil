"""
Permisos por rol (owner/trusted/public) desde Config/discord_roles.json.
Overrides por usuario trusted en Config/trusted_scopes.json (capability -> true/false).
Si no existe el archivo o el rol/capacidad no está, se usa comportamiento por defecto.
"""
import json
import logging
from pathlib import Path
from typing import Any, Dict, Optional

logger = logging.getLogger("discord_roles_config")

_DEFAULT = {
    "owner": ["*"],
    "trusted": ["limited_chat", "charla", "chiste", "meme", "status"],
    "public": ["charla", "chiste", "meme"],
}

_cached: Optional[dict] = None
_scopes_cached: Optional[dict] = None


def _config_path(base_path: Optional[Path] = None) -> Path:
    if base_path is None:
        base_path = Path(__file__).resolve().parent.parent.parent
    return base_path / "Config" / "discord_roles.json"


def _scopes_path(base_path: Optional[Path] = None) -> Path:
    if base_path is None:
        base_path = Path(__file__).resolve().parent.parent.parent
    return base_path / "Config" / "trusted_scopes.json"


def _load(base_path: Optional[Path] = None) -> dict:
    global _cached
    if _cached is not None:
        return _cached
    path = _config_path(base_path)
    if not path.exists():
        _cached = _DEFAULT.copy()
        return _cached
    try:
        raw = path.read_text(encoding="utf-8")
        data = json.loads(raw)
        if isinstance(data, dict):
            _cached = {
                "owner": data.get("owner")
                if isinstance(data.get("owner"), list)
                else _DEFAULT["owner"],
                "trusted": data.get("trusted")
                if isinstance(data.get("trusted"), list)
                else _DEFAULT["trusted"],
                "public": data.get("public")
                if isinstance(data.get("public"), list)
                else _DEFAULT["public"],
            }
            return _cached
    except Exception as e:
        logger.debug("discord_roles_config load: %s", e)
    _cached = _DEFAULT.copy()
    return _cached


def _load_trusted_scopes(
    base_path: Optional[Path] = None,
) -> Dict[str, Dict[str, bool]]:
    """Carga overrides por user_id: { "user_id": { "capability": true|false } }."""
    global _scopes_cached
    if _scopes_cached is not None:
        return _scopes_cached
    path = _scopes_path(base_path)
    if not path.exists():
        _scopes_cached = {}
        return _scopes_cached
    try:
        raw = path.read_text(encoding="utf-8")
        data = json.loads(raw)
        overrides = data.get("overrides") if isinstance(data, dict) else {}
        _scopes_cached = {
            str(k): {
                str(c): bool(v) for c, v in (v if isinstance(v, dict) else {}).items()
            }
            for k, v in (overrides or {}).items()
        }
        return _scopes_cached
    except Exception as e:
        logger.debug("discord_roles_config trusted_scopes load: %s", e)
        _scopes_cached = {}
        return _scopes_cached


def role_can(role: str, capability: str, base_path: Optional[Path] = None) -> bool:
    """
    True si el rol tiene esa capacidad (sin overrides por usuario).
    role: "owner" | "trusted" | "public"
    capability: "orchestrator_full", "limited_chat", "charla", "chiste", "meme", "status", etc.
    Si owner tiene "*" en su lista, puede todo.
    """
    role = (role or "public").lower()
    if role not in ("owner", "trusted", "public"):
        role = "public"
    cfg = _load(base_path)
    caps = cfg.get(role) or []
    if "*" in caps:
        return True
    return capability in caps


def capability_allowed(
    user_id: Optional[str],
    role: str,
    capability: str,
    base_path: Optional[Path] = None,
) -> bool:
    """
    True si el usuario tiene esa capacidad. Para trusted aplica overrides de trusted_scopes.json.
    user_id: ID de Discord (para resolver overrides si role == trusted).
    role: "owner" | "trusted" | "public"
    """
    role = (role or "public").lower()
    if role not in ("owner", "trusted", "public"):
        role = "public"
    if role == "owner":
        return role_can("owner", capability, base_path)
    if role == "public":
        return role_can("public", capability, base_path)
    # trusted: aplicar overrides
    overrides = _load_trusted_scopes(base_path)
    uid = (user_id or "").strip()
    if uid and uid in overrides and capability in overrides[uid]:
        return overrides[uid][capability]
    return role_can("trusted", capability, base_path)


def get_trusted_scope_overrides(
    base_path: Optional[Path] = None,
) -> Dict[str, Dict[str, bool]]:
    """Devuelve copia de overrides (para listar y editar)."""
    return dict(_load_trusted_scopes(base_path))


def set_trusted_scope(
    base_path: Optional[Path],
    user_id: str,
    capability: str,
    allowed: bool,
) -> bool:
    """Establece override para un usuario trusted. Devuelve True si se guardó."""
    path = _scopes_path(base_path)
    uid = (user_id or "").strip()
    cap = (capability or "").strip()
    if not uid or not cap:
        return False
    global _scopes_cached
    overrides = get_trusted_scope_overrides(base_path)
    if uid not in overrides:
        overrides[uid] = {}
    overrides[uid][cap] = bool(allowed)
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        data = {
            "_comment": "Overrides de capacidades por usuario trusted (Discord user_id).",
            "overrides": overrides,
        }
        path.write_text(
            json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        _scopes_cached = overrides
        return True
    except Exception as e:
        logger.warning("discord_roles_config set_trusted_scope: %s", e)
        return False


def invalidate_cache() -> None:
    """Para recargar el JSON tras editar (p. ej. en tests)."""
    global _cached, _scopes_cached
    _cached = None
    _scopes_cached = None
