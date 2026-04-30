"""
Skill: generador_tests
Lee una funcion Python y genera tests unitarios con pytest.
"""
import os
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


def ejecutar(filepath: str = "", funcion: str = "") -> str:
    """Genera tests unitarios para un archivo o funcion Python."""
    from src.llm.gemini_client import GeminiClient

    if not filepath:
        return "ERROR: Se necesita 'filepath' del archivo a testear."

    full_path = os.path.join(project_root, filepath)
    if not os.path.exists(full_path):
        return f"ERROR: Archivo no encontrado: {full_path}"

    with open(full_path, "r", encoding="utf-8", errors="replace") as f:
        code = f.read()

    if len(code) > 10000:
        code = code[:10000] + "\n... (truncado)"

    focus = f"\nEnfocate especificamente en la funcion: {funcion}" if funcion else ""

    gemini = GeminiClient()
    prompt = f"""Eres un experto en testing Python con pytest. Genera tests unitarios para este codigo.{focus}

Archivo: {filepath}
```python
{code}
```

Reglas:
1. Usa pytest (no unittest)
2. Incluye asserts claros y descriptivos
3. Testea edge cases (None, vacio, limites)
4. Usa fixtures si es necesario
5. Naming: test_<funcion>_<caso>
6. Minimo 5 tests, maximo 15
7. Agrega comentarios explicando que testea cada uno
8. El codigo de test debe ser ejecutable directamente

Genera SOLO el codigo del archivo de test, listo para guardar como test_<nombre>.py"""

    resultado = gemini.generate_text(prompt, model="gemini-2.0-flash")
    if not resultado:
        return "ERROR: No se pudieron generar tests."

    # Clean markdown
    if "```python" in resultado:
        resultado = resultado.split("```python")[1].split("```")[0]

    # Save test file
    nombre = os.path.basename(filepath).replace(".py", "")
    test_path = os.path.join(project_root, "Tests", f"test_{nombre}_auto.py")
    with open(test_path, "w", encoding="utf-8") as f:
        f.write(
            f'"""Tests auto-generados para {filepath} - {time.strftime("%Y-%m-%d")}"""\n'
        )
        f.write(resultado)

    return f"SUCCESS: Tests generados en Tests/test_{nombre}_auto.py\n\n{resultado[:600]}..."


if __name__ == "__main__":
    f = sys.argv[1] if len(sys.argv) > 1 else "Backend/llm/gemini_client.py"
    print(ejecutar(f))
