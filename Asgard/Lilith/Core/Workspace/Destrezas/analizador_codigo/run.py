"""
Skill: analizador_codigo
Analiza un archivo Python, detecta bugs, antipatterns y sugiere mejoras usando Gemini.
"""
import os
import sys
import time

skill_dir = os.path.dirname(os.path.abspath(__file__))
workspace_root = os.path.dirname(os.path.dirname(skill_dir))
project_root = os.path.dirname(workspace_root)
sys.path.insert(0, project_root)

# Load secrets
secrets_path = os.path.join(project_root, "Config", "secrets.env")
if os.path.exists(secrets_path):
    with open(secrets_path, "r") as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#"):
                key, val = line.split("=", 1)
                os.environ[key.strip()] = val.strip()


def ejecutar(filepath: str = "") -> str:
    """Analiza un archivo Python y genera reporte de mejoras."""
    from src.llm.gemini_client import GeminiClient

    if not filepath:
        return "ERROR: Se necesita 'filepath' (ruta al archivo a analizar)."

    # Resolve path
    full_path = os.path.join(project_root, filepath)
    if not os.path.exists(full_path):
        return f"ERROR: Archivo no encontrado: {full_path}"

    with open(full_path, "r", encoding="utf-8", errors="replace") as f:
        code = f.read()

    if len(code) > 15000:
        code = code[:15000] + "\n... (truncado por limite)"

    gemini = GeminiClient()
    prompt = f"""Eres Lilith, una IA tactica especializada en revision de codigo.
Analiza el siguiente archivo Python y genera un reporte en ESPAÃ‘OL con:

1. **Resumen** (2-3 oraciones de que hace el archivo)
2. **Bugs detectados** (errores logicos, excepciones no manejadas, etc.)
3. **Antipatterns** (malas practicas, codigo repetido, etc.)
4. **Sugerencias de mejora** (optimizaciones, mejor organizacion, etc.)
5. **Calificacion** (1-10)

Archivo: {filepath}
```python
{code}
```
"""
    resultado = gemini.generate_text(prompt, model="gemini-2.0-flash")
    if not resultado:
        return "ERROR: No se pudo obtener analisis de Gemini."

    # Save report
    nombre = os.path.basename(filepath).replace(".py", "")
    report_path = os.path.join(
        workspace_root, "Taller", f"analisis_{nombre}_{time.strftime('%Y%m%d')}.md"
    )
    with open(report_path, "w", encoding="utf-8") as f:
        f.write(f"# Analisis: {filepath}\n")
        f.write(f"*Analizado por Lilith el {time.strftime('%Y-%m-%d %H:%M')}*\n\n")
        f.write(resultado)

    return f"SUCCESS: Analisis de '{filepath}' completado.\n\n{resultado}"


if __name__ == "__main__":
    target = sys.argv[1] if len(sys.argv) > 1 else "Backend/llm/gemini_client.py"
    print(ejecutar(target))
