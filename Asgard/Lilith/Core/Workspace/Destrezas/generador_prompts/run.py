"""
Skill: generador_prompts
Crea prompts optimizados para diferentes modelos y tareas.
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


def ejecutar(objetivo: str = "", target: str = "gemini") -> str:
    """Genera un prompt optimizado para el objetivo dado."""
    from src.llm.gemini_client import GeminiClient

    if not objetivo:
        return "ERROR: Se necesita 'objetivo' (que quieres lograr con el prompt)."

    gemini = GeminiClient()
    meta_prompt = f"""Eres un experto en ingenieria de prompts. Genera un prompt OPTIMIZADO para lograr lo siguiente:

Objetivo: {objetivo}
Modelo destino: {target}

Reglas:
1. El prompt debe ser claro, especifico y estructurado
2. Incluye el rol del AI, contexto, formato de salida y restricciones
3. Si es para Stable Diffusion: usa formato de tags, pesos y negative prompts
4. Si es para codigo: incluye lenguaje, estilo y constraints
5. Si es para narrativa: incluye tono, genero y perspectiva

Genera:
1. **Prompt principal** (listo para copiar y pegar)
2. **Variante corta** (version resumida)
3. **Tips de uso** (como ajustar para mejores resultados)

Responde en ESPAÃ‘OL."""

    resultado = gemini.generate_text(meta_prompt, model="gemini-2.0-flash")
    if not resultado:
        return "ERROR: No se pudo generar el prompt."

    # Guardar
    output_path = os.path.join(
        workspace_root, "Taller", f"prompt_{target}_{time.strftime('%Y%m%d_%H%M')}.md"
    )
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(f"# Prompt Generado: {objetivo[:50]}\n")
        f.write(
            f"*Target: {target} | Generado el {time.strftime('%Y-%m-%d %H:%M')}*\n\n"
        )
        f.write(resultado)

    return f"SUCCESS: Prompt generado.\n\n{resultado}"


if __name__ == "__main__":
    obj = sys.argv[1] if len(sys.argv) > 1 else "Generar arte de un castillo gotico"
    tgt = sys.argv[2] if len(sys.argv) > 2 else "stable-diffusion"
    print(ejecutar(obj, tgt))
