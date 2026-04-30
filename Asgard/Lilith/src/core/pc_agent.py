"""
PC Agent — Control remoto seguro de PC desde Discord.
Alto nivel de seguridad: red deshabilitada por defecto, redacción de secretos, dry-run, rate limits, kill switch.
"""
import hashlib
import json
import logging
import os
import random
import re
import shlex
import shutil
import stat
import string
import subprocess
import time
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

logger = logging.getLogger("lilith.pc_agent")


@dataclass
class PCAgentResult:
    success: bool
    output: str
    requires_confirm: bool = False
    confirm_token: Optional[str] = None
    confirm_phrase: Optional[str] = None  # Frase para confirmación de alto riesgo
    metadata: Dict[str, Any] = field(default_factory=dict)
    dry_run_info: Optional[Dict] = None  # Info de dry-run para operaciones peligrosas


class PathSecurityError(Exception):
    pass


class CommandSecurityError(Exception):
    pass


class NetworkPolicyError(Exception):
    pass


class KillSwitchError(Exception):
    pass


class RateLimitError(Exception):
    pass


class PCAgent:
    def __init__(self, base_path: Path):
        self.base_path = Path(base_path)
        from src.core.json_safe import safe_load

        self.cfg = safe_load(self.base_path / "Config" / "pc_agent.json", default={})
        self.audit_path = self.base_path / self.cfg.get(
            "audit_log", "Data/pc_agent_audit.jsonl"
        )
        self.rate_limit_path = self.base_path / self.cfg.get(
            "rate_limit_log", "Data/pc_agent_rate_limits.jsonl"
        )
        self.audit_path.parent.mkdir(parents=True, exist_ok=True)
        self.rate_limit_path.parent.mkdir(parents=True, exist_ok=True)

        # Cargar reglas de allowlist de comandos detalladas
        self._cmd_rules = self.cfg.get("allowed_commands_detailed", {})

        # Umbrales para operaciones bulk
        self._bulk_file_threshold = self.cfg.get("bulk_file_threshold", 10)
        self._bulk_size_threshold = self.cfg.get(
            "bulk_size_threshold", 100 * 1024 * 1024
        )

        # Política de red
        self._network_policy = self.cfg.get("network_policy", {"default": False})

        # Rate limits
        self._rate_limits = self.cfg.get("rate_limits", {})

        # Secret patterns para redacción
        self._secret_patterns = self.cfg.get("secret_patterns", [])

        # Output limits
        self._output_limits = self.cfg.get("output_limits", {"max_chars": 1900})

    # ── Kill Switch ─────────────────────────────────────────────────────────

    def _check_kill_switch(self) -> None:
        """Verifica si el kill switch está activado."""
        if self.cfg.get("kill_switch", False):
            raise KillSwitchError(
                "PC Agent está bloqueado (kill switch activado). Usa /pc unlock para desbloquear."
            )

    def toggle_kill_switch(self, enabled: bool, user_id: str = "") -> bool:
        """Activa o desactiva el kill switch."""
        try:
            self.cfg["kill_switch"] = enabled
            config_path = self.base_path / "Config" / "pc_agent.json"
            with open(config_path, "w", encoding="utf-8") as f:
                json.dump(self.cfg, f, ensure_ascii=False, indent=2)

            action = "ACTIVADO" if enabled else "DESACTIVADO"
            self._audit(
                "kill_switch", {"enabled": enabled}, f"Kill switch {action}", user_id
            )
            return True
        except Exception as e:
            logger.error(f"Error toggling kill switch: {e}")
            return False

    # ── Rate Limiting ──────────────────────────────────────────────────────

    def _check_rate_limit(self, op: str, user_id: str = "") -> Tuple[bool, str]:
        """Verifica rate limits por tipo de operación."""
        now = time.time()
        window_minutes = 60

        # Cargar historial de rate limits
        try:
            if self.rate_limit_path.exists():
                with open(self.rate_limit_path, "r", encoding="utf-8") as f:
                    history = [json.loads(line) for line in f if line.strip()]
            else:
                history = []
        except:
            history = []

        # Filtrar entradas recientes (última hora)
        cutoff = now - (window_minutes * 60)
        recent = [h for h in history if h.get("ts", 0) > cutoff]

        # Contar por tipo
        exec_count = sum(1 for h in recent if h.get("op") == "exec")
        delete_count = sum(1 for h in recent if "delete" in h.get("op", ""))
        network_count = sum(1 for h in recent if h.get("network", False))
        failure_count = sum(1 for h in recent if not h.get("success", True))

        # Verificar límites
        max_exec = self._rate_limits.get("max_exec_per_minute", 5)
        max_delete = self._rate_limits.get("max_delete_per_hour", 20)
        max_network = self._rate_limits.get("max_network_ops_per_hour", 10)
        max_failures = self._rate_limits.get("max_failures_per_hour", 10)
        auto_lock = self._rate_limits.get("auto_lock_on_failures", True)

        if op == "exec" and exec_count >= max_exec:
            return False, f"Rate limit: max {max_exec} execs/minuto"

        if "delete" in op and delete_count >= max_delete:
            return False, f"Rate limit: max {max_delete} deletes/hora"

        if op == "exec_network" and network_count >= max_network:
            return False, f"Rate limit: max {max_network} operaciones de red/hora"

        if failure_count >= max_failures:
            if auto_lock and not self.cfg.get("kill_switch", False):
                self.toggle_kill_switch(True, user_id="auto_rate_limit")
                return (
                    False,
                    f"Demasiados fallos ({failure_count}). Kill switch activado automáticamente.",
                )
            return False, f"Rate limit: demasiados fallos ({failure_count})"

        return True, ""

    def _record_rate_limit(
        self, op: str, success: bool, network: bool = False, user_id: str = ""
    ):
        """Registra una operación para rate limiting."""
        entry = {
            "ts": time.time(),
            "op": op,
            "success": success,
            "network": network,
            "user_id": user_id,
        }
        try:
            with open(self.rate_limit_path, "a", encoding="utf-8") as f:
                f.write(json.dumps(entry) + "\n")
        except Exception:
            pass

    # ── Seguridad de Rutas ─────────────────────────────────────────────────

    def _resolve_real_path(self, path_str: str) -> Path:
        """Resuelve la ruta real, siguiendo symlinks, y verifica que no sea un symlink/junction."""
        try:
            p = Path(path_str)
            # Verificar primero si es symlink antes de resolver
            if p.is_symlink():
                raise PathSecurityError(f"ruta es un symlink/junction: {path_str}")
            # Resolver path absoluto
            resolved = p.resolve()
            # Bloquear reparse points (junctions) en cualquier componente (Windows)
            try:
                if os.name == "nt":
                    parts = list(resolved.parts)
                    cur = Path(parts[0]) if parts else resolved
                    for part in parts[1:]:
                        cur = cur / part
                        try:
                            st = os.stat(str(cur), follow_symlinks=False)
                            attrs = getattr(st, "st_file_attributes", 0)
                            if attrs & stat.FILE_ATTRIBUTE_REPARSE_POINT:
                                raise PathSecurityError(
                                    f"ruta contiene junction/symlink (reparse point): {cur}"
                                )
                        except FileNotFoundError:
                            # si no existe aún (mkdir target), validamos parents existentes
                            continue
                        except PathSecurityError:
                            raise
                        except Exception:
                            continue
            except PathSecurityError:
                raise
            return resolved
        except PathSecurityError:
            raise
        except Exception as e:
            raise PathSecurityError(f"ruta inválida: {e}")

    def _path_allowed(self, path_str: str) -> Tuple[bool, str, Optional[Path]]:
        """
        Verifica si una ruta está permitida.
        Retorna: (ok, reason, resolved_path)
        """
        try:
            p = self._resolve_real_path(path_str)
        except PathSecurityError as e:
            return False, str(e), None

        p_str = str(p).lower()

        # Denylist por substring (primera capa)
        for denied in self.cfg.get("denied_patterns", []):
            if denied.lower() in p_str:
                return False, f"ruta denegada ({denied})", p

        # Verificar que no haya path traversal con .. que escape de allowed_roots
        allowed_roots = [Path(r).resolve() for r in self.cfg.get("allowed_roots", [])]
        if not allowed_roots:
            return False, "no hay allowed_roots configurados", p

        # La ruta debe estar dentro de ALGUNO de los allowed_roots
        in_allowed = False
        for a in allowed_roots:
            try:
                # Intentar obtener path relativo - si falla, no está dentro
                p.relative_to(a)
                in_allowed = True
                break
            except ValueError:
                continue

        if not in_allowed:
            return False, f"ruta fuera de allowed_roots: {p}", p

        return True, "", p

    def _check_bulk_operation(
        self, path: Path, op: str
    ) -> Tuple[bool, str, List[Dict]]:
        """
        Verifica si una operación afecta demasiados archivos (bulk).
        Retorna: (is_bulk, reason, affected_items)
        """
        if not path.exists():
            return False, "", []

        if path.is_file():
            return False, "", [{"path": str(path), "size": path.stat().st_size}]

        # Es un directorio - contar archivos y tamaño
        affected = []
        try:
            file_count = 0
            total_size = 0
            for root, dirs, files in os.walk(path):
                for f in files:
                    try:
                        fp = Path(root) / f
                        if fp.is_symlink():
                            continue  # Ignorar symlinks
                        size = fp.stat().st_size
                        affected.append({"path": str(fp), "size": size})
                        file_count += 1
                        total_size += size
                    except:
                        pass
                # Limitar profundidad de búsqueda
                if file_count > self._bulk_file_threshold * 2:
                    break

            if file_count > self._bulk_file_threshold:
                return (
                    True,
                    f"operación bulk detectada: {file_count} archivos (umbral: {self._bulk_file_threshold})",
                    affected,
                )

            if total_size > self._bulk_size_threshold:
                return (
                    True,
                    f"operación bulk detectada: {total_size / 1024 / 1024:.1f}MB (umbral: {self._bulk_size_threshold / 1024 / 1024:.1f}MB)",
                    affected,
                )

        except Exception as e:
            logger.warning(f"Error verificando bulk: {e}")

        return False, "", affected

    # ── Redacción de Secretos ──────────────────────────────────────────────

    def _redact_secrets(self, text: str) -> str:
        """Redacta patrones de secretos del texto."""
        if not text:
            return text

        redacted = text
        for pattern in self._secret_patterns:
            try:
                # Reemplazar matches con [REDACTED]
                redacted = re.sub(
                    pattern,
                    lambda m: f"[REDACTED:{m.group(0)[:4]}****]"
                    if len(m.group(0)) > 8
                    else "[REDACTED]",
                    redacted,
                    flags=re.IGNORECASE,
                )
            except re.error as e:
                logger.warning(f"Regex inválida en secret_patterns: {pattern} - {e}")
                continue

        return redacted

    def _sanitize_output(
        self, output: str, max_chars: int = None, max_lines: int = None
    ) -> str:
        """Sanitiza y limita el output."""
        if not output:
            return output

        max_chars = max_chars or self._output_limits.get("max_chars", 1900)
        max_lines = max_lines or self._output_limits.get("max_lines", 100)

        # Redactar secretos primero
        sanitized = self._redact_secrets(output)

        # Limitar líneas
        lines = sanitized.split("\n")
        if len(lines) > max_lines:
            lines = lines[:max_lines]
            lines.append(f"... ({len(lines) - max_lines} líneas omitidas)")
            sanitized = "\n".join(lines)

        # Limitar caracteres
        if len(sanitized) > max_chars:
            sanitized = (
                sanitized[: max_chars - 50]
                + f"\n... ({len(sanitized) - max_chars + 50} caracteres omitidos)"
            )

        return sanitized

    # ── Seguridad de Comandos y Red ────────────────────────────────────────

    def _parse_command(self, cmd: str) -> Tuple[List[str], str]:
        """
        Parsea el comando a lista de argumentos.
        Retorna: (args_list, error_message)
        """
        try:
            # Usar shlex para parsear correctamente (respeta comillas, escapes)
            args = shlex.split(cmd, posix=False)
            return args, ""
        except ValueError as e:
            return [], f"comando malformado: {e}"

    def _detect_network_activity(self, exe: str, args: List[str]) -> Tuple[bool, str]:
        """
        Detecta si un comando intentará hacer actividad de red.
        Retorna: (uses_network, reason)
        """
        cmd_str = " ".join(args).lower()

        # Comandos conocidos por hacer red
        network_commands = {
            "curl": True,
            "wget": True,
            "nc": True,  # netcat
            "telnet": True,
        }

        if exe in network_commands:
            return True, f"{exe} siempre usa red"

        # Verificar argumentos de red comunes
        network_args = [
            "install",
            "uninstall",
            "download",
            "fetch",
            "pull",
            "push",
            "clone",
            "http",
            "https",
            "--registry",
            "--index-url",
            "--extra-index-url",
        ]

        for arg in args:
            if arg.lower() in network_args:
                return True, f"argumento de red detectado: {arg}"

        # URLs en el comando
        url_patterns = [
            r"https?://[^\s\"]+",
            r"git@[^\s:]+:[^\s\"]+",
        ]
        for pattern in url_patterns:
            if re.search(pattern, cmd_str, re.IGNORECASE):
                return True, "URL detectada en comando"

        return False, ""

    def _cmd_allowed(self, cmd: str) -> Tuple[bool, str, List[str], Dict]:
        """
        Verifica si un comando está permitido con reglas detalladas.
        Retorna: (ok, reason, parsed_args, metadata)
        """
        args, error = self._parse_command(cmd)
        if error:
            return False, error, [], {}

        if not args:
            return False, "comando vacío", [], {}

        exe = args[0].lower().rstrip(".exe")
        metadata = {"exe": exe, "network": False, "high_risk": False}

        # Verificar si está bloqueado completamente
        if exe in self._cmd_rules:
            rules = self._cmd_rules[exe]
            if rules.get("blocked", False):
                return (
                    False,
                    f"{exe} está bloqueado: {rules.get('reason', 'no permitido')}",
                    args,
                    metadata,
                )

            metadata["high_risk"] = rules.get("high_risk", False)
            metadata["requires_phrase"] = rules.get("requires_phrase", False)

            # Verificar allowlist de subcomandos/argumentos
            allowed_args = rules.get("allowed_args", [])
            blocked_args = rules.get("blocked_args", [])
            blocked_patterns = rules.get("blocked_patterns", [])

            # Verificar argumentos bloqueados
            for arg in args[1:]:
                arg_lower = arg.lower()
                if arg_lower in blocked_args:
                    return False, f"argumento bloqueado: {arg}", args, metadata
                for pattern in blocked_patterns:
                    if pattern.lower() in arg_lower:
                        return (
                            False,
                            f"argumento contiene patrón bloqueado: {pattern}",
                            args,
                            metadata,
                        )

            # Si hay allowlist de args, verificar que todos los args estén permitidos
            if allowed_args:
                for arg in args[1:]:
                    arg_lower = arg.lower()
                    if arg_lower not in allowed_args:
                        return False, f"argumento no permitido: {arg}", args, metadata

            # Verificar política de red del comando
            cmd_allows_network = rules.get(
                "network", self._network_policy.get("default", False)
            )
            uses_network, reason = self._detect_network_activity(exe, args)

            if uses_network and not cmd_allows_network:
                return (
                    False,
                    f"comando requiere red pero está deshabilitado: {reason}",
                    args,
                    metadata,
                )

            metadata["network"] = uses_network
        else:
            # Fallback a allowlist simple
            allowed = [c.lower() for c in self.cfg.get("allowed_commands", [])]
            if exe not in allowed:
                return False, f"comando '{exe}' no está en allowlist", args, metadata

            # Detectar red
            uses_network, reason = self._detect_network_activity(exe, args)
            if uses_network and not self._network_policy.get("default", False):
                return False, f"red deshabilitada por defecto: {reason}", args, metadata
            metadata["network"] = uses_network

        return True, "", args, metadata

    def _is_dangerous(self, op: str) -> bool:
        return op in self.cfg.get("dangerous_ops", [])

    def _generate_confirm_phrase(self) -> str:
        """Genera una frase de confirmación aleatoria."""
        chars = string.ascii_uppercase + string.digits
        code = "".join(random.choices(chars, k=6))
        return f"CONFIRMO-{code}"

    # ── Auditoría ──────────────────────────────────────────────────────────

    def _audit(
        self,
        op: str,
        params: dict,
        result: str,
        user_id: str,
        metadata: Dict[str, Any] = None,
    ) -> None:
        """Auditoría extendida con más contexto."""
        entry = {
            "ts": time.time(),
            "ts_iso": datetime.now().isoformat(),
            "op": op,
            "params": params,
            "result_preview": result[:200] if result else "",
            "user_id": user_id,
            "pid": os.getpid(),
        }

        if metadata:
            entry["metadata"] = {
                k: v
                for k, v in metadata.items()
                if k
                not in (
                    "confirm_token",
                    "token",
                    "confirm_phrase",
                )  # No guardar secrets
            }
            # Guardar solo prefijo del token para correlación
            if "confirm_token" in metadata:
                token = metadata["confirm_token"]
                entry["token_prefix"] = token[:4] + "****" if token else None

        try:
            with open(self.audit_path, "a", encoding="utf-8") as f:
                f.write(json.dumps(entry, ensure_ascii=False) + "\n")
        except Exception as e:
            logger.error(f"Error en auditoría: {e}")

    # ── Dry Run Preview ────────────────────────────────────────────────────

    def _calculate_dry_run(self, op: str, **kwargs) -> Dict:
        """Calcula qué se va a tocar en una operación peligrosa."""
        preview = {
            "operation": op,
            "items": [],
            "total_files": 0,
            "total_dirs": 0,
            "total_size": 0,
            "warnings": [],
        }

        if op in ("delete", "delete_bulk"):
            path = Path(kwargs.get("path", ""))
            if path.exists():
                if path.is_file():
                    stat = path.stat()
                    preview["items"].append(
                        {"type": "file", "path": str(path), "size": stat.st_size}
                    )
                    preview["total_files"] = 1
                    preview["total_size"] = stat.st_size
                else:
                    # Directorio - listar contenido
                    max_items = self.cfg.get("dry_run_preview", {}).get(
                        "max_items", 100
                    )
                    for item in path.rglob("*"):
                        if item.is_symlink():
                            continue
                        try:
                            if len(preview["items"]) >= max_items:
                                preview["warnings"].append(
                                    f"Más de {max_items} items, listado truncado"
                                )
                                break

                            stat = item.stat()
                            item_info = {
                                "type": "dir" if item.is_dir() else "file",
                                "path": str(item),
                                "size": stat.st_size if item.is_file() else 0,
                            }
                            preview["items"].append(item_info)

                            if item.is_file():
                                preview["total_files"] += 1
                                preview["total_size"] += stat.st_size
                            else:
                                preview["total_dirs"] += 1
                        except:
                            pass

        elif op in ("move", "move_bulk", "copy", "copy_bulk"):
            src = Path(kwargs.get("src", ""))
            dst = kwargs.get("dst", "")
            if src.exists():
                preview["items"].append(
                    {
                        "type": "dir" if src.is_dir() else "file",
                        "path": str(src),
                        "destination": dst,
                    }
                )
                if src.is_file():
                    preview["total_files"] = 1
                    preview["total_size"] = src.stat().st_size

        return preview

    def _format_dry_run(self, preview: Dict) -> str:
        """Formatea el preview de dry-run para mostrar al usuario."""
        lines = [f"📋 Dry-run: {preview['operation']}", ""]

        if preview["total_files"] > 0:
            lines.append(f"📄 Archivos: {preview['total_files']}")
        if preview["total_dirs"] > 0:
            lines.append(f"📁 Directorios: {preview['total_dirs']}")
        if preview["total_size"] > 0:
            lines.append(
                f"💾 Tamaño total: {preview['total_size'] / 1024 / 1024:.2f} MB"
            )

        lines.append("")
        lines.append("Items afectados:")

        for item in preview["items"][:20]:
            icon = "📁" if item.get("type") == "dir" else "📄"
            path = item.get("path", "")
            if "destination" in item:
                lines.append(f"{icon} {path} → {item['destination']}")
            else:
                size = item.get("size", 0)
                size_str = f" ({size / 1024:.1f} KB)" if size > 0 else ""
                lines.append(f"{icon} {path}{size_str}")

        if len(preview["items"]) > 20:
            lines.append(f"... y {len(preview['items']) - 20} más")

        if preview["warnings"]:
            lines.append("")
            lines.append("⚠️ Advertencias:")
            for w in preview["warnings"]:
                lines.append(f"  - {w}")

        return "\n".join(lines)

    # ── Operaciones Filesystem ─────────────────────────────────────────────

    def list_dir(self, path: str, user_id: str = "") -> PCAgentResult:
        self._check_kill_switch()

        ok, reason, resolved = self._path_allowed(path)
        if not ok:
            self._audit("list", {"path": path}, f"DENIED: {reason}", user_id)
            return PCAgentResult(False, f"Acceso denegado: {reason}")
        try:
            if not resolved.exists():
                return PCAgentResult(False, f"No existe: {path}")
            items = list(resolved.iterdir())
            lines = []
            for item in sorted(items)[:50]:
                prefix = "📁" if item.is_dir() else "📄"
                lines.append(f"{prefix} {item.name}")
            output = "\n".join(lines) or "(vacío)"
            self._audit("list", {"path": str(resolved)}, "OK", user_id)
            return PCAgentResult(True, f"**{resolved}**\n{output}")
        except Exception as e:
            return PCAgentResult(False, str(e))

    def make_dir(self, path: str, user_id: str = "") -> PCAgentResult:
        self._check_kill_switch()

        ok, reason, resolved = self._path_allowed(path)
        if not ok:
            return PCAgentResult(False, f"Acceso denegado: {reason}")
        try:
            resolved.mkdir(parents=True, exist_ok=True)
            self._audit("mkdir", {"path": str(resolved)}, "OK", user_id)
            return PCAgentResult(True, f"✅ Carpeta creada: `{resolved}`")
        except Exception as e:
            return PCAgentResult(False, str(e))

    def move_path(self, src: str, dst: str, user_id: str = "") -> PCAgentResult:
        self._check_kill_switch()

        for label, p in [("src", src), ("dst", dst)]:
            ok, reason, resolved = self._path_allowed(p)
            if not ok:
                return PCAgentResult(False, f"Acceso denegado en {label}: {reason}")

        # Verificar operación bulk
        src_resolved = self._resolve_real_path(src)
        is_bulk, bulk_reason, affected = self._check_bulk_operation(
            src_resolved, "move"
        )

        op_type = "move_bulk" if is_bulk else "move"
        preview = self._calculate_dry_run(op_type, src=str(src_resolved), dst=dst)

        if is_bulk or self._is_dangerous(op_type):
            return self._create_confirm_op(
                op_type,
                {"src": str(src_resolved), "dst": dst, "preview": preview},
                user_id,
                f"⚠️ {bulk_reason if is_bulk else 'Operación peligrosa'}\n{self._format_dry_run(preview)}",
                high_risk=True,
            )

        try:
            shutil.move(str(src_resolved), str(dst))
            self._audit(
                "move", {"src": str(src_resolved), "dst": str(dst)}, "OK", user_id
            )
            return PCAgentResult(True, f"✅ Movido: `{src}` → `{dst}`")
        except Exception as e:
            return PCAgentResult(False, str(e))

    def copy_path(self, src: str, dst: str, user_id: str = "") -> PCAgentResult:
        self._check_kill_switch()

        for label, p in [("src", src), ("dst", dst)]:
            ok, reason, resolved = self._path_allowed(p)
            if not ok:
                return PCAgentResult(False, f"Acceso denegado en {label}: {reason}")

        # Verificar operación bulk
        src_resolved = self._resolve_real_path(src)
        is_bulk, bulk_reason, affected = self._check_bulk_operation(
            src_resolved, "copy"
        )

        op_type = "copy_bulk" if is_bulk else "copy"
        preview = self._calculate_dry_run(op_type, src=str(src_resolved), dst=dst)

        if is_bulk or self._is_dangerous(op_type):
            return self._create_confirm_op(
                op_type,
                {"src": str(src_resolved), "dst": dst, "preview": preview},
                user_id,
                f"⚠️ {bulk_reason if is_bulk else 'Operación peligrosa'}\n{self._format_dry_run(preview)}",
                high_risk=True,
            )

        try:
            if src_resolved.is_dir():
                shutil.copytree(src, dst, dirs_exist_ok=True)
            else:
                shutil.copy2(src, dst)
            self._audit(
                "copy", {"src": str(src_resolved), "dst": str(dst)}, "OK", user_id
            )
            return PCAgentResult(True, f"✅ Copiado: `{src}` → `{dst}`")
        except Exception as e:
            return PCAgentResult(False, str(e))

    def delete_path(self, path: str, user_id: str = "") -> PCAgentResult:
        self._check_kill_switch()

        ok, reason, resolved = self._path_allowed(path)
        if not ok:
            return PCAgentResult(False, f"Acceso denegado: {reason}")

        # Verificar operación bulk (directorio con muchos archivos)
        is_bulk, bulk_reason, affected = self._check_bulk_operation(resolved, "delete")
        op_type = "delete_bulk" if is_bulk else "delete"

        # Calcular dry-run preview
        preview = self._calculate_dry_run(op_type, path=str(resolved))

        # Delete siempre requiere confirmación con preview
        return self._create_confirm_op(
            op_type,
            {"path": str(resolved), "preview": preview},
            user_id,
            f"⚠️ {bulk_reason if is_bulk else 'Vas a eliminar'}\n{self._format_dry_run(preview)}",
            high_risk=True,
        )

    def write_file(
        self, path: str, content: str, overwrite: bool = False, user_id: str = ""
    ) -> PCAgentResult:
        """
        Escribe un archivo de texto (UTF-8) en una ruta permitida.
        - Si el archivo existe y overwrite=False → requiere confirmación.
        - Si overwrite=True → requiere confirmación (alto riesgo si existe).
        """
        self._check_kill_switch()

        ok, reason, resolved = self._path_allowed(path)
        if not ok:
            return PCAgentResult(False, f"Acceso denegado: {reason}")
        if resolved is None:
            return PCAgentResult(False, "Ruta inválida.")

        # Límite duro para evitar payloads gigantes
        try:
            max_chars = int(self.cfg.get("max_write_chars", 120_000))
        except Exception:
            max_chars = 120_000
        text = str(content or "")
        if len(text) > max_chars:
            return PCAgentResult(
                False,
                f"Contenido demasiado grande ({len(text)} chars). Límite: {max_chars}.",
            )

        # Preparar preview minimal (no incluir contenido entero)
        exists = resolved.exists()
        high_risk = bool(exists)
        preview = {
            "op": "write_file",
            "path": str(resolved),
            "exists": exists,
            "overwrite": bool(overwrite),
            "chars": len(text),
        }

        if exists and not overwrite:
            return self._create_confirm_op(
                "write_file",
                {
                    "path": str(resolved),
                    "content": text,
                    "overwrite": False,
                    "preview": preview,
                },
                user_id,
                f"⚠️ El archivo ya existe y overwrite=false.\nRuta: `{resolved}`\nTamaño: {len(text)} chars",
                high_risk=True,
            )
        if overwrite:
            return self._create_confirm_op(
                "write_file_overwrite",
                {
                    "path": str(resolved),
                    "content": text,
                    "overwrite": True,
                    "preview": preview,
                },
                user_id,
                f"⚠️ Vas a sobrescribir un archivo.\nRuta: `{resolved}`\nTamaño: {len(text)} chars",
                high_risk=True,
            )

        # Crear nuevo archivo sin confirmación adicional
        try:
            resolved.parent.mkdir(parents=True, exist_ok=True)
            resolved.write_text(text, encoding="utf-8")
            self._audit(
                "write_file", {"path": str(resolved), "chars": len(text)}, "OK", user_id
            )
            return PCAgentResult(
                True, f"✅ Archivo escrito: `{resolved}` ({len(text)} chars)"
            )
        except Exception as e:
            return PCAgentResult(False, str(e))

    def batch(self, steps: Any, user_id: str = "") -> PCAgentResult:
        """
        Crea una operación en lote (batch) que se confirma UNA sola vez.
        steps: lista de dicts {op, ...} donde op ∈ list|mkdir|move|copy|delete|exec|write_file.
        """
        self._check_kill_switch()
        if not isinstance(steps, list) or not steps:
            return PCAgentResult(False, "steps debe ser una lista no vacía.")

        normalized: List[Dict[str, Any]] = []
        high_risk = False
        for i, s in enumerate(steps[:30]):  # cap de seguridad
            if not isinstance(s, dict):
                return PCAgentResult(False, f"Step {i} inválido (no es dict).")
            op = (s.get("op") or "").strip().lower()
            if op not in (
                "list",
                "mkdir",
                "move",
                "copy",
                "delete",
                "exec",
                "write_file",
            ):
                return PCAgentResult(False, f"Step {i}: op no soportada: {op}")
            item: Dict[str, Any] = {"op": op}
            if op in ("list", "mkdir", "delete"):
                item["path"] = str(s.get("path") or "").strip()
            elif op in ("move", "copy"):
                item["src"] = str(s.get("src") or s.get("path") or "").strip()
                item["dst"] = str(s.get("dst") or "").strip()
            elif op == "exec":
                item["cmd"] = str(s.get("cmd") or "").strip()
                item["cwd"] = str(s.get("cwd") or "").strip()
            elif op == "write_file":
                item["path"] = str(s.get("path") or "").strip()
                item["content"] = str(s.get("content") or "")
                item["overwrite"] = bool(s.get("overwrite", False))
            # marcar riesgo
            if op in ("delete", "exec") or (
                op == "write_file" and item.get("overwrite")
            ):
                high_risk = True
            normalized.append(item)

        # Preview legible
        lines = ["⚠️ Vas a ejecutar un **BATCH** de operaciones:"]
        for idx, it in enumerate(normalized, start=1):
            op = it["op"]
            if op in ("list", "mkdir", "delete"):
                lines.append(f"{idx}. {op} {it.get('path','')}")
            elif op in ("move", "copy"):
                lines.append(f"{idx}. {op} {it.get('src','')} -> {it.get('dst','')}")
            elif op == "exec":
                lines.append(f"{idx}. exec {it.get('cmd','')}")
            elif op == "write_file":
                ov = " overwrite" if it.get("overwrite") else ""
                lines.append(
                    f"{idx}. write_file{ov} {it.get('path','')} ({len(it.get('content',''))} chars)"
                )

        params = {
            "steps": normalized,
            "preview": {"lines": lines[:80], "count": len(normalized)},
        }
        return self._create_confirm_op(
            "batch",
            params,
            user_id,
            "\n".join(lines[:80]),
            high_risk=high_risk,
        )

    def _create_confirm_op(
        self,
        op: str,
        params: dict,
        user_id: str,
        warning_msg: str,
        high_risk: bool = False,
    ) -> PCAgentResult:
        """Crea una operación que requiere confirmación."""
        import uuid

        token = uuid.uuid4().hex[:8].upper()

        # Generar frase de confirmación para operaciones de alto riesgo
        confirm_phrase = None
        require_phrase = bool(self.cfg.get("high_risk_requires_phrase", True))
        if (high_risk or op in ("exec", "exec_network", "taskkill")) and require_phrase:
            confirm_phrase = self._generate_confirm_phrase()

        self._save_pending(op, params, token, user_id, confirm_phrase)

        msg_parts = [warning_msg, f"\nToken: `{token}`"]
        if confirm_phrase:
            msg_parts.append(
                f"\n⚠️ **ALTO RIESGO** — Para confirmar, usa:\n`/pc_confirm {token}`\nY escribe la frase: `{confirm_phrase}`"
            )
        else:
            msg_parts.append(f"\nConfirma con: `/pc_confirm {token}`")
        msg_parts.append(
            f"\n(caduca en {self.cfg.get('confirm_timeout_seconds', 60)}s)"
        )

        return PCAgentResult(
            True,
            "".join(msg_parts),
            requires_confirm=True,
            confirm_token=token,
            confirm_phrase=confirm_phrase,
            dry_run_info=params.get("preview"),
        )

    def exec_command(self, cmd: str, user_id: str = "", cwd: str = "") -> PCAgentResult:
        """Ejecuta comando tras confirmación."""
        self._check_kill_switch()

        # Verificar rate limits
        ok, reason = self._check_rate_limit("exec", user_id)
        if not ok:
            return PCAgentResult(False, f"Rate limit: {reason}")

        ok, reason, args, metadata = self._cmd_allowed(cmd)
        if not ok:
            self._audit("exec_denied", {"cmd": cmd}, reason, user_id)
            self._record_rate_limit("exec", False, False, user_id)
            return PCAgentResult(False, f"Comando no permitido: {reason}")

        cwd_resolved = None
        if cwd:
            ok, reason, cwd_resolved = self._path_allowed(cwd)
            if not ok:
                return PCAgentResult(False, f"cwd denegado: {reason}")

        # Determinar tipo de operación
        op_type = "exec_network" if metadata.get("network") else "exec"

        # Verificar rate limits específicos de red
        if metadata.get("network"):
            ok, reason = self._check_rate_limit("exec_network", user_id)
            if not ok:
                return PCAgentResult(False, f"Rate limit de red: {reason}")

        import uuid

        token = uuid.uuid4().hex[:8].upper()
        confirm_phrase = None

        # Alto riesgo si usa red o está marcado como high_risk
        is_high_risk = (
            metadata.get("network")
            or metadata.get("high_risk")
            or metadata.get("requires_phrase")
        )
        if is_high_risk:
            confirm_phrase = self._generate_confirm_phrase()

        self._save_pending(
            op_type,
            {
                "cmd": cmd,
                "args": args,
                "cwd": str(cwd_resolved) if cwd_resolved else "",
                "network": metadata.get("network", False),
                "requires_phrase": is_high_risk,
            },
            token,
            user_id,
            confirm_phrase,
        )

        network_warning = (
            "\n🌐 **Este comando USA RED**" if metadata.get("network") else ""
        )
        high_risk_warning = "\n⚠️ **COMANDO DE ALTO RIESGO**" if is_high_risk else ""

        msg = f"⚠️ Ejecutar: `{cmd}`{network_warning}{high_risk_warning}\nArgs: {args[:5]}..."
        if confirm_phrase:
            msg += f"\n\n**Confirma con:**\n`/pc_confirm {token}`\n**Frase:** `{confirm_phrase}`"
        else:
            msg += f"\n\nConfirma con: `/pc_confirm {token}`"
        msg += f"\n(caduca en {self.cfg.get('confirm_timeout_seconds', 60)}s)"

        return PCAgentResult(
            True,
            msg,
            requires_confirm=True,
            confirm_token=token,
            confirm_phrase=confirm_phrase,
            metadata={"network": metadata.get("network", False)},
        )

    def confirm_and_run(
        self, token: str, user_id: str = "", phrase: str = ""
    ) -> PCAgentResult:
        """Ejecuta la operación pendiente si el token es válido."""
        self._check_kill_switch()

        pending = self._load_pending(token)
        if not pending:
            return PCAgentResult(False, "Token inválido o caducado.")

        # Verificar que no haya expirado
        confirm_timeout = self.cfg.get("confirm_timeout_seconds", 60)
        if time.time() - pending["ts"] > confirm_timeout:
            self._delete_pending(token)
            return PCAgentResult(False, f"Token caducado ({confirm_timeout}s).")

        # Verificar que el user_id coincida
        pending_user = pending.get("user_id", "")
        if pending_user and pending_user != user_id:
            return PCAgentResult(False, "Token no válido para este usuario.")

        # Verificar frase de confirmación si se requiere
        expected_phrase = pending.get("confirm_phrase")
        if expected_phrase:
            if not phrase or phrase.strip().upper() != expected_phrase.upper():
                return PCAgentResult(
                    False,
                    f"Frase de confirmación requerida. Usa: `/pc_confirm {token} frase:{expected_phrase}`",
                )

        op = pending["op"]
        params = pending["params"]

        # Verificar rate limits antes de ejecutar
        ok, reason = self._check_rate_limit(op, user_id)
        if not ok:
            return PCAgentResult(False, f"Rate limit: {reason}")

        # Invalidar token inmediatamente (único uso)
        self._delete_pending(token)

        metadata = {
            "confirmed_by": user_id,
            "original_user": pending_user,
            "token_prefix": token[:4] + "****",
        }

        if op == "delete" or op == "delete_bulk":
            path = params["path"]
            preview = params.get("preview", {})
            try:
                # Revalidar ruta en confirmación (anti-TOCTOU)
                okp, reasonp, resolved = self._path_allowed(path)
                if not okp:
                    self._record_rate_limit(op, False, False, user_id)
                    self._audit(
                        op,
                        {"path": path},
                        f"DENIED_CONFIRM: {reasonp}",
                        user_id,
                        metadata,
                    )
                    return PCAgentResult(False, f"Acceso denegado: {reasonp}")
                p = resolved
                if p.is_dir():
                    shutil.rmtree(str(p))
                else:
                    p.unlink()
                self._record_rate_limit(op, True, False, user_id)
                self._audit(op, params, "OK", user_id, metadata)
                return PCAgentResult(
                    True,
                    f"✅ Eliminado: `{p}` ({preview.get('total_files', 0)} archivos)",
                )
            except Exception as e:
                self._record_rate_limit(op, False, False, user_id)
                self._audit(op, params, f"ERROR: {e}", user_id, metadata)
                return PCAgentResult(False, str(e))

        elif op in ("write_file", "write_file_overwrite"):
            path = params.get("path") or ""
            content = params.get("content") or ""
            overwrite = bool(params.get("overwrite", False))
            try:
                okp, reasonp, resolved = self._path_allowed(path)
                if not okp or resolved is None:
                    self._audit(
                        op,
                        {"path": path},
                        f"DENIED_CONFIRM: {reasonp}",
                        user_id,
                        metadata,
                    )
                    return PCAgentResult(False, f"Acceso denegado: {reasonp}")
                if resolved.exists() and not overwrite:
                    return PCAgentResult(
                        False, "El archivo ya existe (overwrite=false)."
                    )
                resolved.parent.mkdir(parents=True, exist_ok=True)
                resolved.write_text(str(content), encoding="utf-8")
                self._audit(
                    op,
                    {
                        "path": str(resolved),
                        "chars": len(str(content)),
                        "overwrite": overwrite,
                    },
                    "OK",
                    user_id,
                    metadata,
                )
                return PCAgentResult(
                    True, f"✅ Archivo escrito: `{resolved}` ({len(str(content))} chars)"
                )
            except Exception as e:
                self._audit(op, {"path": path}, f"ERROR: {e}", user_id, metadata)
                return PCAgentResult(False, str(e))

        elif op == "batch":
            steps = params.get("steps") if isinstance(params, dict) else None
            if not isinstance(steps, list) or not steps:
                return PCAgentResult(False, "Batch inválido (sin steps).")
            outputs: List[str] = []
            for i, s in enumerate(steps, start=1):
                if not isinstance(s, dict):
                    return PCAgentResult(False, f"Step {i} inválido.")
                sop = (s.get("op") or "").strip().lower()
                try:
                    if sop == "list":
                        rr = self.list_dir(s.get("path", ""), user_id=user_id)
                    elif sop == "mkdir":
                        rr = self.make_dir(s.get("path", ""), user_id=user_id)
                    elif sop == "move":
                        rr = self.move_path(
                            s.get("src", ""), s.get("dst", ""), user_id=user_id
                        )
                    elif sop == "copy":
                        rr = self.copy_path(
                            s.get("src", ""), s.get("dst", ""), user_id=user_id
                        )
                    elif sop == "delete":
                        # Ejecutar delete directo (sin nueva confirmación), reusando lógica confirmada
                        okp, reasonp, resolved = self._path_allowed(s.get("path", ""))
                        if not okp or resolved is None:
                            return PCAgentResult(
                                False, f"Step {i} delete denegado: {reasonp}"
                            )
                        if resolved.is_dir():
                            shutil.rmtree(str(resolved))
                        else:
                            resolved.unlink()
                        rr = PCAgentResult(True, f"✅ Eliminado: `{resolved}`")
                    elif sop == "exec":
                        cmd = s.get("cmd", "")
                        cwd = s.get("cwd", "")
                        # Ejecutar exec directo tras revalidar allowlist
                        ok2, reason2, args2, meta2 = self._cmd_allowed(cmd)
                        if not ok2:
                            return PCAgentResult(
                                False, f"Step {i} exec denegado: {reason2}"
                            )
                        if cwd:
                            ok_cwd, reason_cwd, cwd_res = self._path_allowed(cwd)
                            if not ok_cwd:
                                return PCAgentResult(
                                    False, f"Step {i} cwd denegado: {reason_cwd}"
                                )
                            cwd_use = str(cwd_res) if cwd_res else None
                        else:
                            cwd_use = None
                        result = subprocess.run(
                            args2,
                            shell=False,
                            capture_output=True,
                            text=True,
                            timeout=30,
                            cwd=cwd_use,
                            stdin=subprocess.DEVNULL,
                        )
                        out = self._sanitize_output(
                            ((result.stdout or "") + (result.stderr or "")).strip(),
                            max_chars=1200,
                        )
                        if result.returncode != 0:
                            return PCAgentResult(
                                False,
                                f"Step {i} exec falló (exit {result.returncode}):\n```\n{out}\n```",
                            )
                        rr = PCAgentResult(
                            True, f"✅ Exec OK (step {i}).\n```\n{out}\n```"
                        )
                    elif sop == "write_file":
                        okp, reasonp, resolved = self._path_allowed(s.get("path", ""))
                        if not okp or resolved is None:
                            return PCAgentResult(
                                False, f"Step {i} write_file denegado: {reasonp}"
                            )
                        overwrite = bool(s.get("overwrite", False))
                        if resolved.exists() and not overwrite:
                            return PCAgentResult(
                                False,
                                f"Step {i}: archivo existe y overwrite=false: {resolved}",
                            )
                        resolved.parent.mkdir(parents=True, exist_ok=True)
                        content = str(s.get("content") or "")
                        resolved.write_text(content, encoding="utf-8")
                        rr = PCAgentResult(True, f"✅ Archivo escrito: `{resolved}`")
                    else:
                        return PCAgentResult(False, f"Step {i}: op desconocida: {sop}")
                except Exception as e:
                    return PCAgentResult(False, f"Step {i} error: {e}")

                if not rr.success:
                    return rr
                outputs.append(rr.output.strip())

            joined = "\n".join(outputs)
            self._audit("batch", {"count": len(steps)}, "OK", user_id, metadata)
            return PCAgentResult(
                True, joined[:1900] if joined else "✅ Batch completado."
            )

        elif op == "exec" or op == "exec_network":
            cmd = params.get("cmd") or ""
            # Revalidar comando y args en confirmación (anti-TOCTOU/config drift)
            ok2, reason2, args2, meta2 = self._cmd_allowed(cmd)
            if not ok2:
                self._record_rate_limit(op, False, False, user_id)
                self._audit(
                    "exec_denied_confirm", {"cmd": cmd}, reason2, user_id, metadata
                )
                return PCAgentResult(False, f"Comando no permitido: {reason2}")

            args = args2
            cwd = params.get("cwd") or str(self.base_path)
            uses_network = params.get("network", False)

            start_time = time.time()
            try:
                # Revalidar cwd permitido
                ok_cwd, reason_cwd, cwd_resolved = self._path_allowed(cwd)
                if not ok_cwd:
                    self._record_rate_limit(op, False, uses_network, user_id)
                    self._audit(
                        "exec_cwd_denied_confirm",
                        {"cwd": cwd},
                        reason_cwd,
                        user_id,
                        metadata,
                    )
                    return PCAgentResult(False, f"cwd denegado: {reason_cwd}")

                # Usar ExecSandbox (kill tree + output cap)
                try:
                    from .exec_sandbox import get_exec_sandbox as _get_sandbox

                    _sb = _get_sandbox(self.base_path)
                    _sr = _sb.run(args, cwd=str(cwd_resolved) if cwd_resolved else None)

                    class _FakeResult:
                        returncode = _sr.exit_code
                        stdout = _sr.stdout
                        stderr = _sr.stderr

                    result = _FakeResult()
                    if _sr.timed_out:
                        raise subprocess.TimeoutExpired(args, _sb.timeout_s)
                except ImportError:
                    result = subprocess.run(
                        args,
                        shell=False,
                        capture_output=True,
                        text=True,
                        timeout=30,
                        cwd=str(cwd_resolved) if cwd_resolved else None,
                        stdin=subprocess.DEVNULL,
                    )
                duration_ms = int((time.time() - start_time) * 1000)

                # Sanitizar output (redactar secretos)
                raw_output = (result.stdout + result.stderr).strip()
                output = self._sanitize_output(raw_output, max_chars=1800)

                metadata.update(
                    {
                        "exit_code": result.returncode,
                        "duration_ms": duration_ms,
                        "cwd": cwd,
                        "network": uses_network,
                    }
                )

                self._record_rate_limit(
                    op, result.returncode == 0, uses_network, user_id
                )
                self._audit("exec", params, raw_output[:100], user_id, metadata)

                if result.returncode != 0:
                    return PCAgentResult(
                        False,
                        f"Exit code {result.returncode}:\n```\n{output or '(sin output)'}\n```",
                    )

                network_note = "\n🌐 (usó red)" if uses_network else ""
                return PCAgentResult(
                    True, f"```\n{output or '(sin output)'}\n```{network_note}"
                )
            except subprocess.TimeoutExpired:
                self._record_rate_limit(op, False, uses_network, user_id)
                self._audit("exec", params, "TIMEOUT", user_id, metadata)
                return PCAgentResult(False, "Timeout (30s).")
            except Exception as e:
                self._record_rate_limit(op, False, uses_network, user_id)
                self._audit("exec", params, f"ERROR: {e}", user_id, metadata)
                return PCAgentResult(False, str(e))

        elif op in ("move", "move_bulk", "copy", "copy_bulk"):
            src = params["src"]
            dst = params["dst"]
            preview = params.get("preview", {})
            try:
                # Revalidar rutas en confirmación
                ok_src, reason_src, src_res = self._path_allowed(src)
                if not ok_src:
                    self._record_rate_limit(op, False, False, user_id)
                    self._audit(
                        op,
                        {"src": src, "dst": dst},
                        f"DENIED_CONFIRM_SRC: {reason_src}",
                        user_id,
                        metadata,
                    )
                    return PCAgentResult(False, f"Acceso denegado en src: {reason_src}")
                ok_dst, reason_dst, dst_res = self._path_allowed(dst)
                if not ok_dst:
                    self._record_rate_limit(op, False, False, user_id)
                    self._audit(
                        op,
                        {"src": src, "dst": dst},
                        f"DENIED_CONFIRM_DST: {reason_dst}",
                        user_id,
                        metadata,
                    )
                    return PCAgentResult(False, f"Acceso denegado en dst: {reason_dst}")

                if op.startswith("move"):
                    shutil.move(str(src_res), str(dst_res))
                    action = "Movido"
                else:
                    if Path(str(src_res)).is_dir():
                        shutil.copytree(str(src_res), str(dst_res), dirs_exist_ok=True)
                    else:
                        shutil.copy2(str(src_res), str(dst_res))
                    action = "Copiado"
                self._record_rate_limit(op, True, False, user_id)
                self._audit(op, params, "OK", user_id, metadata)
                return PCAgentResult(
                    True,
                    f"✅ {action}: `{src_res}` → `{dst_res}` ({preview.get('total_files', 0)} archivos)",
                )
            except Exception as e:
                self._record_rate_limit(op, False, False, user_id)
                self._audit(op, params, f"ERROR: {e}", user_id, metadata)
                return PCAgentResult(False, str(e))

        return PCAgentResult(False, f"Operación desconocida: {op}")

    # ── Pendientes ────────────────────────────────────────────────────────

    def _pending_path(self) -> Path:
        return self.base_path / "Data" / "pc_agent_pending.json"

    def _compute_op_hash(self, op: str, params: dict) -> str:
        """Genera un hash de la operación para vincular el token a los parámetros exactos."""
        # Excluir preview del hash (puede ser grande)
        hash_params = {k: v for k, v in params.items() if k != "preview"}
        data = json.dumps({"op": op, "params": hash_params}, sort_keys=True)
        return hashlib.sha256(data.encode()).hexdigest()[:16]

    def _save_pending(
        self,
        op: str,
        params: dict,
        token: str,
        user_id: str,
        confirm_phrase: str = None,
    ):
        try:
            p = self._pending_path()
            try:
                data = json.loads(p.read_text(encoding="utf-8"))
            except Exception:
                data = {}

            # Limpiar caducados
            now = time.time()
            confirm_timeout = self.cfg.get("confirm_timeout_seconds", 60)
            data = {
                k: v
                for k, v in data.items()
                if now - v.get("ts", 0) < confirm_timeout * 2
            }

            # Guardar con hash de operación
            entry = {
                "op": op,
                "params": params,
                "op_hash": self._compute_op_hash(op, params),
                "ts": now,
                "user_id": user_id,
            }
            if confirm_phrase:
                entry["confirm_phrase"] = confirm_phrase
                entry["requires_phrase"] = True

            data[token] = entry
            p.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
        except Exception as e:
            logger.error(f"Error guardando pendiente: {e}")

    def _load_pending(self, token: str) -> Optional[dict]:
        try:
            data = json.loads(self._pending_path().read_text(encoding="utf-8"))
            pending = data.get(token)
            if pending:
                # Verificar integridad del hash
                stored_hash = pending.get("op_hash", "")
                computed_hash = self._compute_op_hash(
                    pending.get("op", ""), pending.get("params", {})
                )
                if stored_hash != computed_hash:
                    logger.warning(f"Hash mismatch para token {token[:4]}****")
                    return None
            return pending
        except Exception:
            return None

    def _delete_pending(self, token: str):
        try:
            p = self._pending_path()
            data = json.loads(p.read_text(encoding="utf-8"))
            data.pop(token, None)
            p.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
        except Exception:
            pass
