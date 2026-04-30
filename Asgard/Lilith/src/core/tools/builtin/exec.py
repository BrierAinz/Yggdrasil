from __future__ import annotations

import os
import subprocess
import time
import uuid
from pathlib import Path
from typing import Any, Dict, List

from ..execution_context import get_current_agent
from ..security_guard import SecurityGuard
from .protocol import LilithTool, ToolResult


class ExecTool(LilithTool):
    """
    Exec seguro (V1):
    - Recibe argv como lista (sin parsing de string).
    - Valida con SecurityGuard.check_exec (allowlist estructural).
    - Ejecuta con shell=False, stdin=DEVNULL, timeout fijo.
    - Fusiona stdout+stderr en un solo stream (cronología).
    - Devuelve tail (últimos N chars) y guarda log completo en scratch/exec_logs.
    """

    def __init__(self, project_root: Path) -> None:
        self._root = Path(project_root)

    @property
    def name(self) -> str:
        return "exec"

    def get_description(self) -> str:
        return "Ejecuta un comando permitido (allowlist) de forma segura, sin shell, con timeout y logs truncados."

    def get_parameters_schema(self) -> Dict[str, Any]:
        return {
            "command_args": "list[str] (argv). Ej: ['python','-m','pytest','-q'] o ['python','scripts/test.py','-v']",
            "cwd": "string opcional (ruta relativa). Si se omite, se usa working_dir_root del profile.",
            "tail_chars": "int opcional (por defecto 3000).",
        }

    def execute(self, params: Dict[str, Any]) -> ToolResult:
        argv = params.get("command_args")
        if not isinstance(argv, list) or not argv:
            return {"response": "Falta command_args (lista de strings).", "error": True}
        argv = [str(x) for x in argv if str(x)]
        if not argv:
            return {"response": "command_args vacío.", "error": True}

        agent = get_current_agent()
        guard = SecurityGuard(self._root)
        cwd = (params.get("cwd") or "").strip() or None
        decision = guard.check_exec(
            agent=agent,
            argv=argv,
            cwd=str((self._root / cwd).resolve(strict=False)) if cwd else None,
        )
        if not decision.allowed:
            return {
                "response": str(decision.response),
                "error": True,
                **(decision.response if isinstance(decision.response, dict) else {}),
            }

        meta = decision.response if isinstance(decision.response, dict) else {}
        timeout_s = int(meta.get("max_timeout") or 15)
        cwd_abs = meta.get("cwd") or str(self._root)

        try:
            tail_chars = int(params.get("tail_chars") or 3000)
        except Exception:
            tail_chars = 3000
        tail_chars = max(500, min(12000, tail_chars))

        run_id = uuid.uuid4().hex
        logs_dir = self._root / "scratch" / "exec_logs"
        logs_dir.mkdir(parents=True, exist_ok=True)
        log_path = logs_dir / f"exec_{run_id}.txt"

        started = time.time()
        try:
            completed = subprocess.run(
                argv,
                cwd=str(cwd_abs),
                stdin=subprocess.DEVNULL,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                shell=False,
                timeout=timeout_s,
            )
            out_bytes = completed.stdout or b""
            out_text = out_bytes.decode("utf-8", errors="replace")
            log_path.write_text(out_text, encoding="utf-8", errors="replace")
            tail = out_text[-tail_chars:] if len(out_text) > tail_chars else out_text
            elapsed = round(time.time() - started, 3)
            payload = {
                "ok": completed.returncode == 0,
                "exit_code": completed.returncode,
                "elapsed_s": elapsed,
                "argv": argv,
                "cwd": str(cwd_abs),
                "log_path": str(log_path),
                "output_tail": tail,
                "truncated": len(out_text) > len(tail),
            }
            # Para el LLM: tail primero
            resp = f"[exec] exit={completed.returncode} elapsed={elapsed}s\n\n{tail}".strip()
            return {
                "response": resp,
                "data": payload,
                "error": completed.returncode != 0,
            }
        except subprocess.TimeoutExpired as e:
            out_bytes = getattr(e, "output", None) or b""
            out_text = out_bytes.decode("utf-8", errors="replace")
            log_path.write_text(out_text, encoding="utf-8", errors="replace")
            elapsed = round(time.time() - started, 3)
            tail = out_text[-tail_chars:] if len(out_text) > tail_chars else out_text
            resp = f"[exec] timeout after {timeout_s}s elapsed={elapsed}s\n\n{tail}".strip()
            return {
                "response": resp,
                "error": True,
                "data": {
                    "ok": False,
                    "error": "timeout",
                    "elapsed_s": elapsed,
                    "argv": argv,
                    "cwd": str(cwd_abs),
                    "timeout_s": timeout_s,
                    "log_path": str(log_path),
                    "output_tail": tail,
                },
            }
        except Exception as e:
            return {"response": f"[exec] error: {e}", "error": True}
