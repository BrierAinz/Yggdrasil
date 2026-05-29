"""
Skill: worldbuilder
Construye incrementalmente el lore y worldbuilding del universo de juego de Ainz.
Cada ejecucion lee el lore existente y lo expande coherentemente.
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

LORE_PATH = None  # Set in ejecutar

ASPECTOS = {
    "cosmologia": "la estructura del universo, planos de existencia, creacion y destruccion",
    "facciones": "ordenes, reinos, cultos, gremios y sus conflictos politicos",
    "magia": "sistemas de magia, fuentes de poder, costos y restricciones",
    "historia": "eras, eventos cataclismicos, guerras antiguas y profecias",
    "geografia": "regiones, biomas, ciudades, ruinas y dungeons",
    "criaturas": "bestias, demonios, dioses menores, no-muertos y aberraciones",
}


def ejecutar(aspecto: str = "cosmologia", semilla: str = "") -> str:
    """Expande el worldbuilding del universo del juego."""
    from src.llm.gemini_client import GeminiClient

    aspecto = aspecto.lower()
    if aspecto not in ASPECTOS:
        return f"ERROR: Aspecto '{aspecto}' no valido. Usa: {list(ASPECTOS.keys())}"

    # Load existing lore
    lore_dir = os.path.join(workspace_root, "Mente", "worldbuilding")
    os.makedirs(lore_dir, exist_ok=True)
    lore_file = os.path.join(lore_dir, f"{aspecto}.md")

    existing_lore = ""
    if os.path.exists(lore_file):
        with open(lore_file, "r", encoding="utf-8") as f:
            existing_lore = f.read()

    # Read other aspects for cross-references
    cross_refs = ""
    for other in ASPECTOS:
        if other != aspecto:
            other_file = os.path.join(lore_dir, f"{other}.md")
            if os.path.exists(other_file):
                with open(other_file, "r", encoding="utf-8") as f:
                    content = f.read()[:500]
                    if content:
                        cross_refs += f"\n[{other}]: {content[:300]}...\n"

    gemini = GeminiClient()
    prompt = f"""Eres un maestro del worldbuilding al nivel de Miyazaki (Dark Souls), Tolkien y Lovecraft.
Estas construyendo un universo Dark Fantasy con elementos Souls-like para un videojuego.

Aspecto a desarrollar: **{aspecto}** ({ASPECTOS[aspecto]})
{'Idea semilla: ' + semilla if semilla else ''}

{'## Lore existente (NO repetir, EXPANDIR coherentemente)' + chr(10) + existing_lore if existing_lore else '## Primera vez - crear desde cero'}

{'## Referencias de otros aspectos del mundo' + chr(10) + cross_refs if cross_refs else ''}

REGLAS:
1. Mantener coherencia con el lore existente
2. Agregar misterio y ambiguedad (estilo Souls)
3. Cada concepto debe tener implicaciones para la jugabilidad
4. Nombres evocadores y memorables
5. Maximo 500 palabras de contenido NUEVO
6. Responde en ESPAÃ‘OL

Genera NUEVA seccion de lore (no repetir lo existente):"""

    resultado = gemini.generate_text(prompt, model="gemini-2.0-flash", temperature=0.85)
    if not resultado:
        return "ERROR: No se pudo generar lore."

    # Append to lore file
    with open(lore_file, "a", encoding="utf-8") as f:
        if not existing_lore:
            f.write(f"# {aspecto.title()} - Worldbuilding\n\n")
        f.write(f"\n---\n*Generado el {time.strftime('%Y-%m-%d %H:%M')}*\n")
        if semilla:
            f.write(f"*Semilla: {semilla}*\n")
        f.write(f"\n{resultado}\n")

    return f"SUCCESS: Lore de '{aspecto}' expandido.\n\n{resultado}"


if __name__ == "__main__":
    a = sys.argv[1] if len(sys.argv) > 1 else "cosmologia"
    s = sys.argv[2] if len(sys.argv) > 2 else "un dios muerto cuyo cadaver es el mundo"
    print(ejecutar(a, s))
