"""
Skill: generador_commit
Analiza git diff y genera mensajes de commit descriptivos con Gemini.
"""
import os
import subprocess
import sys

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


def ejecutar() -> str:
    """Genera mensaje de commit basado en los cambios git actuales."""
    from src.llm.gemini_client import GeminiClient

    # Get git diff
    try:
        diff = subprocess.run(
            ["git", "diff", "--staged"],
            cwd=project_root,
            capture_output=True,
            text=True,
            timeout=10,
        ).stdout
        if not diff:
            diff = subprocess.run(
                ["git", "diff"],
                cwd=project_root,
                capture_output=True,
                text=True,
                timeout=10,
            ).stdout
        if not diff:
            # Try status instead
            status = subprocess.run(
                ["git", "status", "--short"],
                cwd=project_root,
                capture_output=True,
                text=True,
                timeout=10,
            ).stdout
            if not status:
                return "No hay cambios pendientes en git."
            diff = f"[Git Status]\n{status}"
    except Exception as e:
        return f"ERROR: No se pudo leer git: {e}"

    if len(diff) > 8000:
        diff = diff[:8000] + "\n... (diff truncado)"

    gemini = GeminiClient()
    prompt = f"""Eres Lilith. Genera un mensaje de commit para estos cambios git.

Reglas:
- Formato: tipo(scope): descripcion corta
- Tipos: feat, fix, refactor, docs, style, test, chore
- Maximo 72 caracteres en la primera linea
- Agrega un cuerpo descriptivo de 2-3 lineas si es necesario
- Escribe en ESPAÃ‘OL
- Da 3 opciones de mejor a peor

Cambios:
{diff}
"""
    resultado = gemini.generate_text(prompt, model="gemini-2.0-flash")
    return resultado if resultado else "ERROR: No se pudo generar el commit."


if __name__ == "__main__":
    print(ejecutar())
