"""Tool de ejecucion de codigo Python sandboxed."""
import subprocess
import tempfile
from typing import Any, Dict

from lilith_tools.base import BaseTool


class CodingTool(BaseTool):
    name = "coding"
    description = (
        "Ejecuta codigo Python en entorno sandboxed. "
        "Parametros: code (str), timeout (int, default 10)"
    )
    parameters = {
        "code": {"type": "string", "description": "Codigo Python a ejecutar"},
        "timeout": {
            "type": "integer",
            "description": "Timeout en segundos",
            "default": 10,
        },
    }

    def execute(self, code: str = "", timeout: int = 10) -> Dict[str, Any]:
        if not code:
            return {"error": "Codigo vacio"}
        blocked = [
            "__import__",
            "eval(",
            "exec(",
            "compile(",
            "open(",
            "os.system",
            "subprocess",
            "import os",
            "import sys",
        ]
        for b in blocked:
            if b in code:
                return {"error": f"Uso bloqueado detectado: {b}"}
        try:
            with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
                f.write(code)
                f.flush()
                result = subprocess.run(
                    ["python3", f.name],
                    capture_output=True,
                    text=True,
                    timeout=timeout,
                )
            return {
                "stdout": result.stdout,
                "stderr": result.stderr,
                "returncode": result.returncode,
            }
        except subprocess.TimeoutExpired:
            return {"error": "Timeout"}
        except Exception as e:
            return {"error": str(e)}
