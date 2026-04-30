"""
Skill: auto_debugger
Recibe un error/traceback, analiza el codigo y sugiere el fix.
"""
import os
import re
import sys
import time

skill_dir = os.path.dirname(os.path.abspath(__file__))
workspace_root = os.path.dirname(os.path.dirname(skill_dir))
project_root = os.path.dirname(workspace_root)
sys.path.insert(0, project_root)

secrets_path = os.path.join(project_root, "Config", "secrets.env")
if os.path.exists(secrets_path):
    with open(secrets_path, "r") as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#"):
                key, val = line.split("=", 1)
                os.environ[key.strip()] = val.strip()


def _extract_files_from_traceback(error: str) -> list:
    """Extrae archivos mencionados en un traceback."""
    pattern = r'File "([^"]+)", line (\d+)'
    matches = re.findall(pattern, error)
    return [(f, int(l)) for f, l in matches]


def _read_code_context(filepath: str, line: int, context: int = 10) -> str:
    """Lee el codigo alrededor de la linea del error."""
    try:
        with open(filepath, "r", encoding="utf-8", errors="replace") as f:
            lines = f.readlines()
        start = max(0, line - context)
        end = min(len(lines), line + context)
        result = []
        for i in range(start, end):
            marker = ">>>" if i + 1 == line else "   "
            result.append(f"{marker} {i+1}: {lines[i].rstrip()}")
        return "\n".join(result)
    except:
        return ""


def ejecutar(error: str = "", archivo: str = "") -> str:
    """Analiza un error y sugiere el fix."""
    from src.llm.gemini_client import GeminiClient

    if not error:
        return "ERROR: Se necesita 'error' (el traceback o mensaje de error)."

    # Gather code context
    code_context = ""

    # From explicit file
    if archivo:
        full_path = os.path.join(project_root, archivo)
        if os.path.exists(full_path):
            with open(full_path, "r", encoding="utf-8", errors="replace") as f:
                code_context += (
                    f"\n## Archivo: {archivo}\n```python\n{f.read()[:6000]}\n```\n"
                )

    # From traceback
    files = _extract_files_from_traceback(error)
    for fpath, line_num in files[:3]:
        if os.path.exists(fpath):
            ctx = _read_code_context(fpath, line_num)
            if ctx:
                code_context += f"\n## {os.path.basename(fpath)} (linea {line_num})\n```\n{ctx}\n```\n"

    gemini = GeminiClient()
    prompt = f"""Eres Lilith en modo debugger. Analiza este error y da la solucion.

## Error/Traceback
```
{error}
```

{code_context}

Responde en ESPAÃ‘OL con:
1. **Que paso** (explicacion clara del error)
2. **Por que paso** (causa raiz)
3. **Fix** (codigo corregido, listo para copiar)
4. **Como prevenir** (tip para evitar errores similares)
"""
    resultado = gemini.generate_text(prompt, model="gemini-2.0-flash")
    if not resultado:
        return "ERROR: No se pudo analizar el error."

    return f"SUCCESS: Analisis de debug completado.\n\n{resultado}"


if __name__ == "__main__":
    test_error = """Traceback (most recent call last):
  File "Backend/main.py", line 42, in <module>
    from src.llm.venice_client import VeniceClient
ImportError: cannot import name 'VeniceClient'"""
    print(ejecutar(test_error))
