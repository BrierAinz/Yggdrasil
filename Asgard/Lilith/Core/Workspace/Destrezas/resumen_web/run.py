"""
Skill: resumen_web
Investiga un tema en internet y genera un resumen guardado en Mente/conceptos_clave/
"""
import json
import os
import sys
import time

# Setup paths
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


def ejecutar(tema: str, max_results: int = 5) -> str:
    """Ejecuta la skill de investigacion web."""
    from src.llm.gemini_client import GeminiClient
    from src.tools.ecosystem.research import Research

    # Paso 1: Buscar en internet
    research = Research()
    resultados_raw = research.execute({"query": tema, "max_results": max_results})

    if "ERROR" in resultados_raw:
        return f"ERROR en busqueda: {resultados_raw}"

    # Paso 2: Resumir con Gemini
    gemini = GeminiClient()
    prompt = f"""Eres Lilith, una IA tactica. Resume la siguiente informacion sobre '{tema}' en un documento claro y conciso en ESPAÃ‘OL.

Estructura tu resumen asi:
1. Concepto principal (2-3 oraciones)
2. Puntos clave (lista con viÃ±etas)
3. Aplicacion practica (como se puede usar en un proyecto)

Informacion de internet:
{resultados_raw}
"""
    resumen = gemini.generate_text(prompt, model="gemini-2.0-flash")

    if not resumen:
        return "ERROR: No se pudo generar el resumen con Gemini."

    # Paso 3: Guardar en Mente/conceptos_clave/
    nombre_archivo = tema.lower().replace(" ", "_").replace("/", "_")[:50]
    output_path = os.path.join(
        workspace_root, "Mente", "conceptos_clave", f"{nombre_archivo}.md"
    )
    os.makedirs(os.path.dirname(output_path), exist_ok=True)

    contenido = f"# {tema}\n\n"
    contenido += f"*Investigado por Lilith el {time.strftime('%Y-%m-%d %H:%M')}*\n\n"
    contenido += resumen
    contenido += f"\n\n---\n*Fuentes: Busqueda DuckDuckGo ({max_results} resultados)*\n"

    with open(output_path, "w", encoding="utf-8") as f:
        f.write(contenido)

    return f"SUCCESS: Resumen sobre '{tema}' guardado en Mente/conceptos_clave/{nombre_archivo}.md ({len(resumen)} chars)"


if __name__ == "__main__":
    tema = sys.argv[1] if len(sys.argv) > 1 else "Python asyncio"
    print(ejecutar(tema))
