"""
ExecSandbox — Ejecución segura con kill de árbol de procesos, cap de output y timeout configurable.
Capa de seguridad adicional para pc_agent.py y exec_tool.py.
"""
from __future__ import annotations

import logging
import os
import subprocess
import threading
import time
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional

logger = logging.getLogger("lilith.exec_sandbox")

# ─── Defaults ─────────────────────────────────────────────────────────────────

DEFAULT_TIMEOUT_S: int = 30
DEFAULT_MAX_OUTPUT_BYTES: int = 256 * 1024  # 256 KB
DEFAULT_MAX_LINES: int = 2000


# ─── Kill tree ────────────────────────────────────────────────────────────────


def _kill_tree(pid: int) -> None:
    """Termina el proceso y todos sus hijos (Windows y Unix)."""
    try:
        if os.name == "nt":
            subprocess.call(
                ["taskkill", "/F", "/T", "/PID", str(pid)],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                timeout=5,
            )
        else:
            import signal

            os.killpg(os.getpgid(pid), signal.SIGKILL)
    except Exception as e:
        logger.debug("_kill_tree pid=%s: %s", pid, e)


# ─── Resultado ────────────────────────────────────────────────────────────────


@dataclass
class SandboxResult:
    ok: bool
    exit_code: int
    stdout: str
    stderr: str
    elapsed_s: float
    timed_out: bool = False
    output_truncated: bool = False
    error_msg: str = ""

    @property
    def output(self) -> str:
        """stdout + stderr combinados, como en subprocess.run(capture_output=True)."""
        parts = []
        if self.stdout:
            parts.append(self.stdout)
        if self.stderr:
            parts.append(self.stderr)
        return "\n".join(parts).strip()


# ─── ExecSandbox ──────────────────────────────────────────────────────────────


class ExecSandbox:
    """
    Ejecuta un comando con:
    - shell=False (sin expansión de shell)
    - stdin=DEVNULL (sin interactividad)
    - timeout + kill de árbol de procesos completo
    - Cap de output por bytes y líneas
    """

    def __init__(
        self,
        timeout_s: int = DEFAULT_TIMEOUT_S,
        max_output_bytes: int = DEFAULT_MAX_OUTPUT_BYTES,
        max_lines: int = DEFAULT_MAX_LINES,
    ) -> None:
        self.timeout_s = max(1, int(timeout_s))
        self.max_output_bytes = max(1024, int(max_output_bytes))
        self.max_lines = max(10, int(max_lines))

    def run(
        self,
        args: List[str],
        cwd: Optional[str] = None,
        env: Optional[dict] = None,
    ) -> SandboxResult:
        """
        Ejecuta `args` de forma segura.
        args: lista de strings (argv), nunca string + shell=True.
        """
        if not args:
            return SandboxResult(
                ok=False,
                exit_code=-1,
                stdout="",
                stderr="",
                elapsed_s=0.0,
                error_msg="args vacío",
            )

        started = time.monotonic()
        proc: Optional[subprocess.Popen] = None
        timed_out = False

        try:
            extra_kwargs = {}
            if os.name != "nt":
                # En Unix: creamos un grupo de procesos para matar toda la jerarquía
                extra_kwargs["start_new_session"] = True

            proc = subprocess.Popen(
                args,
                cwd=cwd,
                env=env,
                stdin=subprocess.DEVNULL,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                shell=False,
                **extra_kwargs,
            )

            # Leer output con cap en un thread separado
            stdout_chunks: List[bytes] = []
            stderr_chunks: List[bytes] = []
            stdout_bytes_read = [0]
            stderr_bytes_read = [0]
            stdout_truncated = [False]
            stderr_truncated = [False]

            def _reader(
                pipe, chunks: List[bytes], bytes_read: List[int], truncated: List[bool]
            ) -> None:
                try:
                    while True:
                        chunk = pipe.read(4096)
                        if not chunk:
                            break
                        remaining = self.max_output_bytes - bytes_read[0]
                        if remaining <= 0:
                            truncated[0] = True
                            break
                        if len(chunk) > remaining:
                            chunks.append(chunk[:remaining])
                            bytes_read[0] += remaining
                            truncated[0] = True
                            break
                        chunks.append(chunk)
                        bytes_read[0] += len(chunk)
                except Exception:
                    pass

            t_out = threading.Thread(
                target=_reader,
                args=(proc.stdout, stdout_chunks, stdout_bytes_read, stdout_truncated),
                daemon=True,
            )
            t_err = threading.Thread(
                target=_reader,
                args=(proc.stderr, stderr_chunks, stderr_bytes_read, stderr_truncated),
                daemon=True,
            )
            t_out.start()
            t_err.start()

            try:
                proc.wait(timeout=self.timeout_s)
            except subprocess.TimeoutExpired:
                timed_out = True
                _kill_tree(proc.pid)
                try:
                    proc.wait(timeout=3)
                except Exception:
                    pass

            t_out.join(timeout=2)
            t_err.join(timeout=2)

            elapsed = round(time.monotonic() - started, 3)
            exit_code = proc.returncode if proc.returncode is not None else -1

            stdout_raw = b"".join(stdout_chunks).decode("utf-8", errors="replace")
            stderr_raw = b"".join(stderr_chunks).decode("utf-8", errors="replace")

            # Cap de líneas
            stdout_lines = stdout_raw.splitlines()
            stderr_lines = stderr_raw.splitlines()
            output_truncated = stdout_truncated[0] or stderr_truncated[0]
            if len(stdout_lines) > self.max_lines:
                stdout_raw = "\n".join(stdout_lines[-self.max_lines :])
                output_truncated = True
            if len(stderr_lines) > self.max_lines:
                stderr_raw = "\n".join(stderr_lines[-self.max_lines :])
                output_truncated = True

            return SandboxResult(
                ok=(exit_code == 0 and not timed_out),
                exit_code=exit_code,
                stdout=stdout_raw,
                stderr=stderr_raw,
                elapsed_s=elapsed,
                timed_out=timed_out,
                output_truncated=output_truncated,
                error_msg=f"timeout after {self.timeout_s}s" if timed_out else "",
            )

        except FileNotFoundError as e:
            return SandboxResult(
                ok=False,
                exit_code=-1,
                stdout="",
                stderr="",
                elapsed_s=round(time.monotonic() - started, 3),
                error_msg=f"Comando no encontrado: {e}",
            )
        except Exception as e:
            if proc is not None:
                try:
                    _kill_tree(proc.pid)
                except Exception:
                    pass
            return SandboxResult(
                ok=False,
                exit_code=-1,
                stdout="",
                stderr="",
                elapsed_s=round(time.monotonic() - started, 3),
                error_msg=str(e),
            )


# ─── Singleton config-driven ──────────────────────────────────────────────────

_sandbox: Optional[ExecSandbox] = None


def get_exec_sandbox(base_path: Optional[Path] = None) -> ExecSandbox:
    """Devuelve el singleton, leyendo Config/pc_agent.json si se proporciona base_path."""
    global _sandbox
    if _sandbox is not None:
        return _sandbox

    timeout_s = DEFAULT_TIMEOUT_S
    max_output_bytes = DEFAULT_MAX_OUTPUT_BYTES
    max_lines = DEFAULT_MAX_LINES

    if base_path:
        try:
            from src.core.json_safe import safe_load

            cfg = safe_load(Path(base_path) / "Config" / "pc_agent.json", default={})
            sandbox_cfg = (cfg or {}).get("sandbox") or {}
            timeout_s = int(sandbox_cfg.get("timeout_s", timeout_s))
            max_output_bytes = int(
                sandbox_cfg.get("max_output_bytes", max_output_bytes)
            )
            max_lines = int(sandbox_cfg.get("max_lines", max_lines))
        except Exception:
            pass

    _sandbox = ExecSandbox(
        timeout_s=timeout_s,
        max_output_bytes=max_output_bytes,
        max_lines=max_lines,
    )
    return _sandbox
