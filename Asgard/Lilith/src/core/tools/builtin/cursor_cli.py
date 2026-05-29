"""
Lilith 3.0 — Tool: delegación a Cursor CLI.
Invoca el agente de Cursor en modo headless (--print) para tareas de código o análisis
que Lilith delega al CLI de Cursor. Requiere Cursor CLI instalado y autenticado.
La API key se usa desde la variable de entorno CURSOR_API_KEY o desde Config/secrets.env.
"""
import logging
import os
import shutil
import subprocess
from pathlib import Path
from typing import Any, Dict, List, Optional

from .protocol import LilithTool, ToolResult

logger = logging.getLogger("CursorCLITool")

# Timeout por defecto (segundos): el agente de Cursor puede tardar
DEFAULT_TIMEOUT = 120


def _get_cursor_api_key(project_root: Path) -> Optional[str]:
    """
    Obtiene CURSOR_API_KEY desde el entorno o desde Config/secrets.env.
    Así Lilith puede usar la key guardada sin tener que exportarla en cada sesión.
    """
    key = os.environ.get("CURSOR_API_KEY", "").strip()
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
                    if k.strip().upper() == "CURSOR_API_KEY":
                        return v.strip().strip('"').strip("'") or None
    except Exception as e:
        logger.debug("No se pudo leer CURSOR_API_KEY desde secrets.env: %s", e)
    return None


def _cursor_cli_command() -> Optional[List[str]]:
    """
    Devuelve el comando base para el CLI: ['agent'] (oficial) o ['cursor', 'agent'] (fallback).
    El CLI oficial se invoca como 'agent', no 'cursor agent' (en Windows 'cursor' suele ser la app de escritorio).
    """
    if shutil.which("agent") is not None:
        return ["agent"]
    if shutil.which("cursor") is not None:
        return ["cursor", "agent"]
    return None


def _run_cursor_agent_headless(
    prompt: str,
    workspace: Path,
    timeout: int = DEFAULT_TIMEOUT,
    allow_edits: bool = False,
    project_root: Optional[Path] = None,
) -> tuple[str, bool]:
    """
    Ejecuta el Cursor Agent CLI en modo headless: agent -p "prompt" (o cursor agent -p "prompt").
    Si project_root está definido, intenta cargar CURSOR_API_KEY desde Config/secrets.env.
    Returns: (stdout + stderr como string, ok: bool)
    """
    base = _cursor_cli_command()
    if not base:
        return (
            "Cursor Agent CLI no está en PATH. Instala con: irm 'https://cursor.com/install?win32=true' | iex (PowerShell). "
            "Verifica con: agent --version. El comando es 'agent', no 'cursor agent'.",
            False,
        )
    workspace_str = str(workspace.resolve())
    cmd = base + [
        "-p",
        prompt,
        "--workspace",
        workspace_str,
        "--trust",
    ]
    if allow_edits:
        cmd.append("--force")

    env = os.environ.copy()
    if project_root:
        api_key = _get_cursor_api_key(Path(project_root))
        if api_key:
            env["CURSOR_API_KEY"] = api_key

    try:
        result = subprocess.run(
            cmd,
            cwd=workspace_str,
            capture_output=True,
            text=True,
            timeout=timeout,
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
                or f"Cursor CLI terminó con código {result.returncode}. Comprueba que hayas hecho login: cursor agent login.",
                False,
            )
        return (combined or "(Cursor no devolvió texto)", True)
    except subprocess.TimeoutExpired:
        return (
            f"Cursor CLI superó el tiempo límite ({timeout}s). Prueba con una tarea más corta o aumenta el timeout.",
            False,
        )
    except FileNotFoundError:
        return (
            "No se encontró 'agent' ni 'cursor' en PATH. Instala Cursor Agent CLI y verifica con: agent --version.",
            False,
        )
    except Exception as e:
        logger.exception("Error ejecutando Cursor CLI: %s", e)
        return (f"Error al invocar Cursor CLI: {e}", False)


class CursorCLITool(LilithTool):
    """Delega una tarea al agente de Cursor vía CLI (modo headless)."""

    def __init__(self, project_root: Path, timeout: int = DEFAULT_TIMEOUT):
        self.project_root = Path(project_root)
        self.timeout = timeout

    @property
    def name(self) -> str:
        return "delegate_cursor"

    def get_description(self) -> str:
        return (
            "Ejecuta una tarea usando el Cursor CLI (agente de Cursor en modo headless). "
            "Útil para edición de código, refactors o análisis que Cursor pueda hacer en el workspace."
        )

    def get_parameters_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "task": {
                    "type": "string",
                    "description": "La tarea o prompt para el agente de Cursor.",
                },
                "context": {
                    "type": "string",
                    "description": "Contexto adicional (ej. contenido de archivo, instrucciones).",
                },
                "allow_edits": {
                    "type": "boolean",
                    "description": "Si true, permite que Cursor modifique archivos (--force).",
                },
            },
            "required": ["task"],
        }

    def execute(self, params: Dict[str, Any]) -> ToolResult:
        from src.core.input_sanitizer import sanitize_input, validate_instruction

        raw_task = (params.get("task") or "").strip()
        raw_context = (params.get("context") or "").strip()
        allow_edits = params.get("allow_edits") is True

        # Defensa inyección: sanitizar y validar; límite total del prompt
        max_prompt_len = 8000
        task = sanitize_input(raw_task, max_len=4000)
        context = sanitize_input(raw_context, max_len=4000)
        if not task:
            return {"response": "Indica la tarea para Cursor CLI.", "error": True}

        ok_t, err_t = validate_instruction(task, self.project_root)
        if not ok_t:
            return {
                "response": err_t or "La tarea contiene instrucciones no permitidas.",
                "error": True,
            }
        if context:
            ok_c, err_c = validate_instruction(context, self.project_root)
            if not ok_c:
                return {
                    "response": err_c
                    or "El contexto contiene instrucciones no permitidas.",
                    "error": True,
                }

        combined = f"{task}\n\n[Contexto]:\n{context}" if context else task
        if len(combined) > max_prompt_len:
            combined = combined[:max_prompt_len].rstrip() + "\n… (truncado)"
        prompt = combined

        response, ok = _run_cursor_agent_headless(
            prompt,
            self.project_root,
            timeout=self.timeout,
            allow_edits=allow_edits,
            project_root=self.project_root,
        )
        return {"response": response, "error": not ok}
