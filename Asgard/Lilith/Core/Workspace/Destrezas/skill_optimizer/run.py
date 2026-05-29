"""
Skill: skill_optimizer
Lilith revisa sus propias skills, detecta problemas y genera versiones mejoradas.
La habilidad de auto-mejora.
"""
import json
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


def ejecutar(skill_name: str = "", modo: str = "analizar") -> str:
    """Analiza o mejora una skill existente."""
    from src.llm.gemini_client import GeminiClient

    if not skill_name:
        # List all skills for analysis
        destrezas = os.path.join(workspace_root, "Destrezas")
        skills = [
            d
            for d in os.listdir(destrezas)
            if os.path.isdir(os.path.join(destrezas, d)) and d != "__pycache__"
        ]
        return f"Skills disponibles para optimizar: {skills}\nUsa: skill_name='nombre' modo='analizar|mejorar'"

    # Load the skill
    skill_path = os.path.join(workspace_root, "Destrezas", skill_name, "run.py")
    if not os.path.exists(skill_path):
        return f"ERROR: Skill '{skill_name}' no encontrada."

    with open(skill_path, "r", encoding="utf-8") as f:
        code = f.read()

    manifest_path = os.path.join(workspace_root, "Destrezas", skill_name, "skill.json")
    manifest = ""
    if os.path.exists(manifest_path):
        with open(manifest_path, "r", encoding="utf-8") as f:
            manifest = f.read()

    gemini = GeminiClient()

    if modo == "analizar":
        prompt = f"""Eres Lilith revisando una de tus propias skills. Analiza esta skill:

Nombre: {skill_name}
Manifest:
{manifest}

Codigo:
```python
{code}
```

Evalua:
1. **Calidad del codigo** (1-10)
2. **Manejo de errores** (faltan try/except? edge cases?)
3. **Eficiencia** (hay operaciones innecesarias?)
4. **Seguridad** (hay riesgos?)
5. **Mejoras sugeridas** (lista concreta)
6. **Bugs potenciales** (si los hay)

Responde en ESPAÃ‘OL."""

        resultado = gemini.generate_text(prompt, model="gemini-2.0-flash")
        return f"ANALISIS de '{skill_name}':\n\n{resultado}"

    elif modo == "mejorar":
        prompt = f"""Eres Lilith optimizando una de tus propias skills.
Genera una version MEJORADA de este codigo:

Nombre: {skill_name}
```python
{code}
```

Mejoras requeridas:
1. Mejor manejo de errores (try/except especificos)
2. Validacion de inputs
3. Logging informativo
4. Optimizacion de rendimiento
5. Documentacion completa

Genera SOLO el codigo Python mejorado, sin explicaciones, sin markdown."""

        improved = gemini.generate_text(prompt, model="gemini-2.0-flash")
        if not improved:
            return "ERROR: No se pudo generar mejora."

        # Clean
        if "```python" in improved:
            improved = improved.split("```python")[1].split("```")[0]

        # Save as _optimized version (don't overwrite original)
        opt_path = os.path.join(
            workspace_root, "Destrezas", skill_name, "run_optimized.py"
        )
        with open(opt_path, "w", encoding="utf-8") as f:
            f.write(improved)

        return (
            f"SUCCESS: Version mejorada guardada en Destrezas/{skill_name}/run_optimized.py\n"
            f"Revisa y renombra a run.py si la apruebas.\n\n{improved[:500]}..."
        )

    return f"ERROR: Modo '{modo}' no valido. Usa: analizar | mejorar"


if __name__ == "__main__":
    s = sys.argv[1] if len(sys.argv) > 1 else ""
    m = sys.argv[2] if len(sys.argv) > 2 else "analizar"
    print(ejecutar(s, m))
