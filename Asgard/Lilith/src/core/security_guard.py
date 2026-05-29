from __future__ import annotations

import json
import threading
import time
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import Any, Dict, List, Optional, Tuple

from .execution_context import get_current_agent


@dataclass(frozen=True)
class GuardDecision:
    allowed: bool
    response: Dict[str, Any]


def _project_root() -> Path:
    # .../Core/Backend/core/security_guard.py -> .../Core
    return Path(__file__).resolve().parent.parent.parent


def _normalize_path(p: Path) -> Path:
    return p.expanduser().resolve(strict=False)


def _safe_rel_to_root(candidate_abs: Path, root_abs: Path) -> Optional[str]:
    try:
        rel = candidate_abs.relative_to(root_abs)
        return rel.as_posix()
    except Exception:
        return None


def _matches_any_glob(rel_posix: str, globs: Optional[List[str]]) -> bool:
    if not globs:
        return True
    p = PurePosixPath(rel_posix)
    for g in globs:
        gg = (g or "").strip()
        if not gg:
            continue
        # PurePosixPath.match soporta '**' correctamente.
        if p.match(gg):
            return True
        # Compat: patrones tipo '**/file' deben matchear también 'file' en raíz.
        if gg.startswith("**/") and p.match(gg[3:]):
            return True
    return False


def _deny_payload(
    *, agent: str, op: str, path: str, reason: str, hint: str
) -> Dict[str, Any]:
    return {
        "error": "permission_denied",
        "message": "Permiso denegado por SecurityGuard.",
        "reason": reason,
        "agent": agent,
        "op": op,
        "path": path,
        "hint": hint,
    }


def _deny_exec_payload(
    *, agent: str, argv: List[str], reason: str, hint: str
) -> Dict[str, Any]:
    return {
        "error": "exec_denied",
        "message": "Ejecución denegada por SecurityGuard.",
        "reason": reason,
        "agent": agent,
        "argv": argv,
        "hint": hint,
    }


class SecurityGuard:
    """
    Guardián central de acceso a disco (deny-by-default + explicit-deny-overrides).

    - Normaliza rutas con resolve(strict=False) para aplanar ../
    - Evalúa reglas por agente: cualquier deny que matchee => denegar
    - Si no hay deny, cualquier allow que matchee => permitir
    - Si no hay match => denegar (si deny_by_default)
    """

    def __init__(self, base_path: Optional[Path] = None) -> None:
        self.base_path = _normalize_path(base_path) if base_path else _project_root()
        self._cfg = self._load_config()

    # --- allow temporal en memoria (UAC) ---
    _temp_lock = threading.Lock()
    _temp_grants: List[Dict[str, Any]] = []

    @classmethod
    def _cleanup_temp_grants(cls) -> None:
        now = time.time()
        with cls._temp_lock:
            cls._temp_grants = [
                g for g in cls._temp_grants if float(g.get("expires_at") or 0) > now
            ]

    def grant_temp_scope(
        self, *, agent: str, op: str, target_path: str, ttl_seconds: int = 3600
    ) -> Dict[str, Any]:
        """
        Otorga un allow temporal. NO modifica agent_scopes.json.
        Importante: no puede anular denies explícitos (deny-overrides) porque el check_path
        siempre evalúa denies permanentes antes de aplicar el grant.
        """
        agent_norm = (agent or "").strip().lower() or "nobody"
        op_norm = (op or "").strip().lower()
        if op_norm not in ("read", "list", "edit", "write", "delete"):
            return {"ok": False, "error": "operation inválida"}
        ttl = max(60, min(24 * 3600, int(ttl_seconds or 3600)))
        root_abs = _normalize_path(self.base_path)
        cand_abs = _normalize_path(root_abs / str(target_path))
        rel = _safe_rel_to_root(cand_abs, root_abs)
        if rel is None:
            return {"ok": False, "error": "target_path fuera del proyecto"}
        rel_posix = rel
        expires_at = time.time() + ttl
        grant = {
            "agent": agent_norm,
            "op": op_norm,
            "rel": rel_posix,
            "expires_at": expires_at,
        }
        self._cleanup_temp_grants()
        with self._temp_lock:
            self._temp_grants.append(grant)
        return {
            "ok": True,
            "expires_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(expires_at)),
            "rule": {
                "agent": agent_norm,
                "operation": op_norm,
                "target_path": rel_posix,
                "ttl_seconds": ttl,
            },
        }

    @classmethod
    def _temp_allows(cls, agent: str, op: str, rel_posix: str) -> bool:
        cls._cleanup_temp_grants()
        with cls._temp_lock:
            for g in cls._temp_grants:
                if (g.get("agent") or "") != agent:
                    continue
                if (g.get("op") or "") != op:
                    continue
                if (g.get("rel") or "") == rel_posix:
                    return True
        return False

    def _load_config(self) -> Dict[str, Any]:
        cfg_path = self.base_path / "Config" / "agent_scopes.json"
        if not cfg_path.exists():
            return {
                "version": 1,
                "defaults": {"deny_by_default": True, "exec_enabled": False},
                "agents": {},
            }
        try:
            raw = cfg_path.read_text(encoding="utf-8")
            data = json.loads(raw)
            return data if isinstance(data, dict) else {}
        except Exception:
            return {
                "version": 1,
                "defaults": {"deny_by_default": True, "exec_enabled": False},
                "agents": {},
            }

    def _rules_for(self, agent: str) -> List[Dict[str, Any]]:
        agents = self._cfg.get("agents") if isinstance(self._cfg, dict) else None
        if not isinstance(agents, dict):
            return []
        block = agents.get(agent) or agents.get("owner") or {}
        rules = block.get("rules") if isinstance(block, dict) else None
        return rules if isinstance(rules, list) else []

    def _deny_by_default(self) -> bool:
        defaults = self._cfg.get("defaults") if isinstance(self._cfg, dict) else None
        if not isinstance(defaults, dict):
            return True
        return bool(defaults.get("deny_by_default", True))

    def _exec_enabled(self) -> bool:
        defaults = self._cfg.get("defaults") if isinstance(self._cfg, dict) else None
        if not isinstance(defaults, dict):
            return False
        return bool(defaults.get("exec_enabled", False))

    def _exec_profiles_for(self, agent: str) -> List[Dict[str, Any]]:
        agents = self._cfg.get("agents") if isinstance(self._cfg, dict) else None
        if not isinstance(agents, dict):
            return []
        block = agents.get(agent) or agents.get("owner") or {}
        profiles = block.get("exec_profiles") if isinstance(block, dict) else None
        return profiles if isinstance(profiles, list) else []

    def check_exec(
        self,
        *,
        agent: str,
        argv: List[str],
        cwd: Optional[str] = None,
    ) -> GuardDecision:
        """
        Validador estructural de exec (sin regex):
        - argv[0] debe coincidir con un profile.command allow.
        - flags permitidos: tokens que empiezan por '-' deben estar en allowed_flags.
        - args no-flag: si allow_path_args -> tratar como ruta y validar root+ext; si no -> denegar.
        - working_dir_root: cwd debe quedar dentro de ese root (si se pasa).
        """
        agent_norm = (agent or "").strip().lower() or "nobody"
        if not self._exec_enabled():
            return GuardDecision(
                False,
                _deny_exec_payload(
                    agent=agent_norm,
                    argv=argv or [],
                    reason="exec_disabled",
                    hint="exec está deshabilitado en Config/agent_scopes.json (defaults.exec_enabled=false).",
                ),
            )
        if not argv or not isinstance(argv, list) or not (argv[0] or "").strip():
            return GuardDecision(
                False,
                _deny_exec_payload(
                    agent=agent_norm,
                    argv=argv or [],
                    reason="missing_argv",
                    hint="Indica argv como lista: ['python', 'script.py', '-q'].",
                ),
            )

        profiles = self._exec_profiles_for(agent_norm)
        cmd = (argv[0] or "").strip()
        matched: Optional[Dict[str, Any]] = None
        for p in profiles:
            if not isinstance(p, dict) or not bool(p.get("allow", False)):
                continue
            if (p.get("command") or "").strip() == cmd:
                matched = p
                break
        if not matched:
            return GuardDecision(
                False,
                _deny_exec_payload(
                    agent=agent_norm,
                    argv=argv,
                    reason="command_not_allowed",
                    hint=f"El comando base '{cmd}' no está permitido para este agente.",
                ),
            )

        allowed_flags = matched.get("allowed_flags")
        if not isinstance(allowed_flags, list):
            allowed_flags = []
        allowed_flags_set = {str(x) for x in allowed_flags if str(x).strip()}
        allow_path_args = bool(matched.get("allow_path_args", False))
        allowed_exts = matched.get("allowed_extensions")
        if not isinstance(allowed_exts, list):
            allowed_exts = []
        allowed_exts = [str(e).lower() for e in allowed_exts if str(e).strip()]

        root_abs = _normalize_path(self.base_path)
        work_root = _normalize_path(
            root_abs / str(matched.get("working_dir_root") or "./")
        )

        if cwd:
            cwd_abs = _normalize_path(Path(cwd))
            if _safe_rel_to_root(cwd_abs, work_root) is None:
                return GuardDecision(
                    False,
                    _deny_exec_payload(
                        agent=agent_norm,
                        argv=argv,
                        reason="cwd_out_of_scope",
                        hint="working_dir fuera del root permitido para este comando.",
                    ),
                )
        else:
            cwd_abs = work_root

        for tok in argv[1:]:
            t = str(tok)
            if not t:
                continue
            if t.startswith("-"):
                if t not in allowed_flags_set:
                    return GuardDecision(
                        False,
                        _deny_exec_payload(
                            agent=agent_norm,
                            argv=argv,
                            reason="flag_not_allowed",
                            hint=f"Flag no permitido: {t}",
                        ),
                    )
                continue
            # no-flag
            if not allow_path_args:
                return GuardDecision(
                    False,
                    _deny_exec_payload(
                        agent=agent_norm,
                        argv=argv,
                        reason="arg_not_allowed",
                        hint=f"Argumento no permitido (no-ruta) para '{cmd}': {t}",
                    ),
                )
            cand_abs = _normalize_path(cwd_abs / t)
            if _safe_rel_to_root(cand_abs, work_root) is None:
                return GuardDecision(
                    False,
                    _deny_exec_payload(
                        agent=agent_norm,
                        argv=argv,
                        reason="path_arg_out_of_scope",
                        hint="Argumento-ruta fuera del working_dir_root permitido.",
                    ),
                )
            if allowed_exts:
                if cand_abs.suffix.lower() not in allowed_exts:
                    return GuardDecision(
                        False,
                        _deny_exec_payload(
                            agent=agent_norm,
                            argv=argv,
                            reason="extension_not_allowed",
                            hint=f"Extensión no permitida: {cand_abs.suffix}",
                        ),
                    )

        max_timeout = matched.get("max_timeout")
        try:
            max_timeout_i = int(max_timeout) if max_timeout is not None else 15
        except Exception:
            max_timeout_i = 15
        max_timeout_i = max(1, min(60, max_timeout_i))

        return GuardDecision(
            True,
            {
                "ok": True,
                "agent": agent_norm,
                "argv": argv,
                "cwd": str(cwd_abs),
                "max_timeout": max_timeout_i,
            },
        )

    def check_path(
        self, op: str, path: str, *, agent: Optional[str] = None
    ) -> GuardDecision:
        op_norm = (op or "").strip().lower()
        agent_norm = ((agent or "").strip().lower()) or get_current_agent()
        if not path or not str(path).strip():
            return GuardDecision(
                False,
                _deny_payload(
                    agent=agent_norm,
                    op=op_norm,
                    path="",
                    reason="missing_path",
                    hint="Indica una ruta dentro de tu ámbito permitido.",
                ),
            )

        # Candidate absoluto dentro del proyecto (paths relativos al proyecto).
        root_abs = _normalize_path(self.base_path)
        cand_abs = _normalize_path(root_abs / str(path))
        rel = _safe_rel_to_root(cand_abs, root_abs)
        if rel is None:
            return GuardDecision(
                False,
                _deny_payload(
                    agent=agent_norm,
                    op=op_norm,
                    path=str(cand_abs),
                    reason="path_out_of_scope",
                    hint="La ruta sale del proyecto. Pide al Owner que mueva el archivo a tu zona permitida o ejecute la acción manualmente.",
                ),
            )

        rel_posix = rel
        rules = self._rules_for(agent_norm)
        allow_hits: List[Dict[str, Any]] = []
        temp_allowed = self._temp_allows(agent_norm, op_norm, rel_posix)

        # Explicit deny overrides: si algún deny matchea, bloquear.
        for r in rules:
            if not isinstance(r, dict):
                continue
            allow = bool(r.get("allow", False))
            ops = r.get("ops")
            if isinstance(ops, list) and ops:
                if op_norm not in [str(o).strip().lower() for o in ops if o]:
                    continue
            # Si ops no está, aplica a todas.
            paths = r.get("paths")
            roots = (
                [str(p) for p in paths] if isinstance(paths, list) and paths else ["./"]
            )
            globs = r.get("globs")

            matched_root = False
            for rp in roots:
                root_rule_abs = _normalize_path(root_abs / rp)
                if _safe_rel_to_root(cand_abs, root_rule_abs) is not None:
                    matched_root = True
                    break
            if not matched_root:
                continue
            if not _matches_any_glob(
                rel_posix, globs if isinstance(globs, list) else None
            ):
                continue

            if not allow:
                return GuardDecision(
                    False,
                    _deny_payload(
                        agent=agent_norm,
                        op=op_norm,
                        path=str(path),
                        reason="explicit_deny",
                        hint="No tienes acceso a la ruta solicitada. Tu ámbito está restringido. Pide al Owner que mueva el archivo a tu zona permitida o que ejecute la acción manualmente.",
                    ),
                )
            allow_hits.append(r)

        if temp_allowed or allow_hits:
            return GuardDecision(
                True,
                {"ok": True, "agent": agent_norm, "op": op_norm, "path": str(path)},
            )

        if self._deny_by_default():
            return GuardDecision(
                False,
                _deny_payload(
                    agent=agent_norm,
                    op=op_norm,
                    path=str(path),
                    reason="deny_by_default",
                    hint="Tu ámbito no incluye esa ruta/operación. Pide al Owner que amplíe tu scope o que ejecute la acción manualmente.",
                ),
            )
        return GuardDecision(
            True, {"ok": True, "agent": agent_norm, "op": op_norm, "path": str(path)}
        )
