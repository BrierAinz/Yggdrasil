"""
Skill: explicador
Recibe codigo complejo y lo explica paso a paso en espaÃ±ol.
"""
import os
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


def ejecutar(filepath: str = "", nivel: str = "intermedio") -> str:
    """Explica codigo paso a paso."""
    from src.llm.gemini_client import GeminiClient

    if not filepath:
        return "ERROR: Se necesita 'filepath' del archivo a explicar."

    full_path = os.path.join(project_root, filepath)
    if not os.path.exists(full_path):
        return f"ERROR: Archivo no encontrado: {full_path}"

    with open(full_path, "r", encoding="utf-8", errors="replace") as f:
        code = f.read()

    if len(code) > 12000:
        code = code[:12000] + "\n... (truncado)"

    niveles = {
        "basico": "como si le explicaras a alguien que apenas empieza a programar",
        "intermedio": "asumiendo conocimiento basico de programacion",
        "avanzado": "enfocandote en patrones de diseÃ±o, complejidad y decisiones arquitectonicas",
    }
    desc_nivel = niveles.get(nivel, niveles["intermedio"])

    gemini = GeminiClient()
    prompt = f"""Eres Lilith en modo profesor. Explica este codigo {desc_nivel}.

Archivo: {filepath}
```
{code}
```

Estructura tu explicacion:
1. **Resumen** (que hace este archivo en 2 oraciones)
2. **Recorrido linea por linea** (agrupa por secciones logicas, no cada linea individual)
3. **Conceptos clave** (que patrones o tecnicas usa)
4. **Flujo de datos** (como se mueve la informacion)
5. **Posibles mejoras** (1-2 sugerencias)

Responde en ESPAÃ‘OL. Se claro y conciso."""

    resultado = gemini.generate_text(prompt, model="gemini-2.0-flash")
    return resultado if resultado else "ERROR: No se pudo generar la explicacion."


if __name__ == "__main__":
    f = sys.argv[1] if len(sys.argv) > 1 else "Backend/llm/gemini_client.py"
    n = sys.argv[2] if len(sys.argv) > 2 else "intermedio"
    print(ejecutar(f, n))
