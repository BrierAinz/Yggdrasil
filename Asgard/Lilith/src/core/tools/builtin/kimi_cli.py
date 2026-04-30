"""
Lilith — Tool: delegación al Kimi Code CLI (Moonshot AI).
Invoca el agente Kimi en modo no interactivo para tareas de código o análisis.
Requiere: pip install kimi-cli (o npm install -g kimi-cli) y KIMI_API_KEY.
Docs: https://github.com/MoonshotAI/kimi-cli
"""
import logging
import os
import shutil
import subprocess
from pathlib import Path
from typing import Any, Dict, Optional

from .protocol import LilithTool, ToolResult

logger = logging.getLogger("KimiCLITool")

DEFAULT_TIMEOUT = 120


def _get_kimi_api_key(project_root: Path) -> Optional[str]:
    """Obtiene KIMI_API_KEY desde el entorno o Config/secrets.env."""
    key = os.environ.get("KIMI_API_KEY", "").strip()
    if key:
        return key
    secrets_path = Path(project_root) / "Config" / "secrets.env"
    if not secrets_path.is_file():
        return None
    try:
        with open(secrets_path, "r", encoding="utf-8", errors="replace") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                if "=" in line:
                    k, _, v = line.partition("=")
                    if k.strip().upper() == "KIMI_API_KEY":
                        return v.strip().strip('"').strip("'") or None
    except Exception as e:
        logger.debug("No se pudo leer KIMI_API_KEY desde secrets.env: %s", e)
    return None


def _kimi_cli_available() -> bool:
    """True si el comando 'kimi' está en PATH."""
    return shutil.which("kimi") is not None


def _sanitize_kimi_output(raw: str) -> str:
    """Quita salida cruda (TurnBegin, ThinkPart, ToolCall, etc.) y deja solo texto legible para Discord."""
    if not raw or "TurnBegin(" not in raw and "ToolResult(" not in raw:
        return raw.strip()
    import re

    # Extraer solo el contenido de TextPart(type='text', text='...')
    parts = re.findall(r"text=['\"]([^'\"]*(?:\\.[^'\"]*)*)['\"]", raw)
    if parts:
        return "\n\n".join(p.replace("\\n", "\n") for p in parts).strip()
    # Si no hay TextPart, quitar líneas de metadatos
    lines = []
    for line in raw.splitlines():
        s = line.strip()
        if any(
            s.startswith(x)
            for x in (
                "TurnBegin(",
                "StepBegin(",
                "ThinkPart(",
                "ToolCall(",
                "ToolResult(",
                "StatusUpdate(",
            )
        ):
            continue
        if s:
            lines.append(line)
    return "\n".join(lines).strip() if lines else raw.strip()


def _run_kimi_cli(
    prompt: str,
    workspace: Path,
    timeout: int = DEFAULT_TIMEOUT,
    project_root: Optional[Path] = None,
    model: Optional[str] = None,
) -> tuple[str, bool]:
    """
    Ejecuta Kimi Code CLI en modo no interactivo: kimi -p "prompt" -w <workspace> --print --yolo.
    Returns: (stdout + stderr, ok).
    """
    if not _kimi_cli_available():
        return (
            "Kimi CLI no está en PATH. Instala con: pip install kimi-cli (o npm install -g kimi-cli). "
            "Luego configura KIMI_API_KEY y ejecuta 'kimi login' si hace falta.",
            False,
        )
    workspace_str = str(Path(workspace).resolve())
    cmd = ["kimi", "-p", prompt, "-w", workspace_str, "--print", "--yolo"]
    if model:
        cmd.extend(["-m", model])

    env = os.environ.copy()
    env["PYTHONIOENCODING"] = "utf-8"
    env["PYTHONUTF8"] = "1"
    if project_root:
        api_key = _get_kimi_api_key(Path(project_root))
        if api_key:
            env["KIMI_API_KEY"] = api_key

    try:
        last_error = None
        for attempt, use_timeout in enumerate([timeout, timeout + 30]):
            try:
                result = subprocess.run(
                    cmd,
                    cwd=workspace_str,
                    capture_output=True,
                    text=True,
                    timeout=use_timeout,
                    encoding="utf-8",
                    errors="replace",
                    env=env,
                )
                out = (result.stdout or "").strip()
                err = (result.stderr or "").strip()
                combined = f"{out}\n{err}".strip() if err else out
                if result.returncode != 0:
                    return (
                        combined
                        or f"Kimi CLI terminó con código {result.returncode}. Comprueba KIMI_API_KEY y 'kimi login'.",
                        False,
                    )
                cleaned = _sanitize_kimi_output(combined)
                return (cleaned or "(Kimi no devolvió texto)", True)
            except subprocess.TimeoutExpired as e:
                last_error = e
                if attempt == 0:
                    logger.info(
                        "Kimi CLI timeout (%ss); reintentando con %ss.",
                        timeout,
                        use_timeout,
                    )
                    continue
                return (
                    f"Kimi CLI superó el tiempo límite ({use_timeout}s) tras reintento.",
                    False,
                )
        if last_error:
            return (f"Kimi CLI superó el tiempo límite ({timeout}s).", False)
    except FileNotFoundError:
        return (
            "No se encontró 'kimi' en PATH. Instala con: pip install kimi-cli.",
            False,
        )
    except Exception as e:
        logger.exception("Error ejecutando Kimi CLI: %s", e)
        return (str(e), False)


class KimiCLITool(LilithTool):
    """Delega una tarea al Kimi Code CLI (Moonshot AI) en modo headless."""

    def __init__(self, project_root: Path, timeout: int = DEFAULT_TIMEOUT) -> None:
        self.project_root = Path(project_root)
        self.timeout = timeout

    @property
    def name(self) -> str:
        return "delegate_kimi_cli"

    def get_description(self) -> str:
        return (
            "Ejecuta una tarea usando el Kimi Code CLI (Moonshot AI). "
            "Útil para código, análisis y refactors con contexto largo (Kimi). Requiere kimi-cli instalado."
        )

    def get_parameters_schema(self) -> Dict[str, Any]:
        return {
            "task": "string — La tarea o prompt para Kimi CLI.",
            "context": "string — Contexto adicional opcional.",
            "model": "string opcional — Modelo (ej. moonshot-v1-128k).",
        }

    def execute(self, params: Dict[str, Any]) -> ToolResult:
        from src.core.input_sanitizer import sanitize_input, validate_instruction

        raw_task = (params.get("task") or "").strip()
        raw_context = (params.get("context") or "").strip()
        model = (params.get("model") or "").strip() or None

        task = sanitize_input(raw_task, max_len=4000)
        context = sanitize_input(raw_context, max_len=4000)
        if not task:
            return {"response": "Indica la tarea para Kimi CLI.", "error": True}

        ok_t, err_t = validate_instruction(task, self.project_root)
        if not ok_t:
            return {
                "response": err_t or "La tarea contiene instrucciones no permitidas.",
                "error": True,
            }
        if context:
            ok_c, _ = validate_instruction(context, self.project_root)
            if not ok_c:
                return {
                    "response": "El contexto contiene instrucciones no permitidas.",
                    "error": True,
                }

        max_prompt_len = 8000
        combined = f"{task}\n\n[Contexto]:\n{context}" if context else task
        if len(combined) > max_prompt_len:
            combined = combined[:max_prompt_len].rstrip() + "\n… (truncado)"

        response, ok = _run_kimi_cli(
            combined,
            self.project_root,
            timeout=self.timeout,
            project_root=self.project_root,
            model=model,
        )
        return {"response": response, "error": not ok}
