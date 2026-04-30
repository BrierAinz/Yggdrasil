"""
Skill: diario_dev
Genera automaticamente un log diario de trabajo basado en archivos modificados y actividad.
"""
import glob
import os
import subprocess
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


def _get_recent_files(hours: int = 24) -> list:
    """Encuentra archivos modificados en las ultimas N horas."""
    import datetime

    cutoff = time.time() - (hours * 3600)
    recent = []

    ignore = {".venv", "node_modules", "__pycache__", ".git", ".crush", "venv"}
    code_ext = {".py", ".js", ".html", ".css", ".json", ".md", ".yaml"}

    for root, dirs, files in os.walk(project_root):
        dirs[:] = [d for d in dirs if d not in ignore]
        for fname in files:
            _, ext = os.path.splitext(fname)
            if ext not in code_ext:
                continue
            fpath = os.path.join(root, fname)
            try:
                if os.path.getmtime(fpath) > cutoff:
                    rel = os.path.relpath(fpath, project_root)
                    recent.append(
                        {
                            "path": rel,
                            "modified": time.strftime(
                                "%H:%M", time.localtime(os.path.getmtime(fpath))
                            ),
                            "size": os.path.getsize(fpath),
                        }
                    )
            except:
                pass

    return sorted(recent, key=lambda x: x["modified"], reverse=True)[:30]


def ejecutar() -> str:
    """Genera el diario de desarrollo del dia."""
    from src.llm.gemini_client import GeminiClient

    today = time.strftime("%Y-%m-%d")
    recent = _get_recent_files(24)

    if not recent:
        return "No se encontraron archivos modificados en las ultimas 24 horas."

    # Build context
    files_ctx = "\n".join(
        [f"- [{f['modified']}] {f['path']} ({f['size']} bytes)" for f in recent]
    )

    gemini = GeminiClient()
    prompt = f"""Eres Lilith. Genera un DIARIO DE DESARROLLO para hoy ({today}).

Archivos modificados en las ultimas 24 horas:
{files_ctx}

Genera un resumen en ESPAÃ‘OL con:
1. **Resumen del dia** (que se trabajo hoy, 2-3 oraciones)
2. **Archivos clave** (los mas importantes y que se hizo en ellos)
3. **Progreso** (que se logro)
4. **Pendientes** (que queda por hacer basandote en los patrones)

Se conciso. Maximo 200 palabras."""

    resultado = gemini.generate_text(prompt, model="gemini-2.0-flash")

    # Save diary
    diario_dir = os.path.join(workspace_root, "Mente", "diarios")
    os.makedirs(diario_dir, exist_ok=True)
    diario_path = os.path.join(diario_dir, f"{today}.md")

    with open(diario_path, "w", encoding="utf-8") as f:
        f.write(f"# Diario Dev - {today}\n\n")
        f.write(resultado or "Sin resumen disponible.")
        f.write(f"\n\n---\n## Archivos modificados ({len(recent)})\n")
        for fi in recent:
            f.write(f"- `{fi['path']}` ({fi['modified']})\n")

    return f"SUCCESS: Diario guardado en Mente/diarios/{today}.md\n\n{resultado}"


if __name__ == "__main__":
    print(ejecutar())
