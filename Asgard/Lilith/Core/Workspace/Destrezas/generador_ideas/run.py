"""
Skill: generador_ideas
Brainstorming de mecanicas de juego, lore, personajes y mundos usando Gemini.
Orientado al camino de Ainz como Game Creator.
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

PROMPTS_POR_TIPO = {
    "mecanica": """Genera 5 ideas de MECANICAS DE JUEGO innovadoras para un juego {tema}.
Para cada una incluye:
- Nombre de la mecanica
- Descripcion en 2 oraciones
- Por que es unica/innovadora
- Ejemplo de como se sentiria jugandola""",
    "lore": """Genera 5 ideas de LORE/HISTORIA para un universo {tema}.
Para cada una incluye:
- Titulo del concepto
- Premisa central (2-3 oraciones)
- Un misterio o giro narrativo
- Como conecta con la jugabilidad""",
    "personaje": """Genera 5 ideas de PERSONAJES/BOSSES para un juego {tema}.
Para cada uno incluye:
- Nombre y titulo
- Apariencia y estetica
- Motivacion/trasfondo oscuro
- Mecanica de pelea unica""",
    "mundo": """Genera 5 ideas de REGIONES/AREAS para un mundo {tema}.
Para cada una incluye:
- Nombre del area
- Descripcion visual y atmosfera
- Enemigos tipicos de la zona
- Secreto oculto o mecanica ambiental""",
}


def ejecutar(tema: str = "souls-like dark fantasy", tipo: str = "mecanica") -> str:
    """Genera ideas creativas para juegos."""
    from src.llm.gemini_client import GeminiClient

    tipo = tipo.lower()
    if tipo not in PROMPTS_POR_TIPO:
        return f"ERROR: Tipo '{tipo}' no valido. Usa: {list(PROMPTS_POR_TIPO.keys())}"

    template = PROMPTS_POR_TIPO[tipo]
    prompt = f"""Eres Lilith, IA tactica de un creador de videojuegos que ama Dark Fantasy, Mitologia y juegos Souls-like.
{template.format(tema=tema)}

IMPORTANTE: Responde en ESPAÃ‘OL. Se creativo pero coherente. Piensa como un diseÃ±ador de FromSoftware o Team ICO."""

    gemini = GeminiClient()
    resultado = gemini.generate_text(prompt, model="gemini-2.0-flash", temperature=0.9)

    if not resultado:
        return "ERROR: No se generaron ideas."

    # Guardar en Taller
    output_path = os.path.join(
        workspace_root, "Taller", f"ideas_{tipo}_{time.strftime('%Y%m%d_%H%M')}.md"
    )
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(f"# Ideas: {tipo.title()} - {tema}\n")
        f.write(f"*Generado por Lilith el {time.strftime('%Y-%m-%d %H:%M')}*\n\n")
        f.write(resultado)

    return f"SUCCESS: Ideas generadas y guardadas.\n\n{resultado}"


if __name__ == "__main__":
    tema = sys.argv[1] if len(sys.argv) > 1 else "souls-like dark fantasy"
    tipo = sys.argv[2] if len(sys.argv) > 2 else "mecanica"
    print(ejecutar(tema, tipo))
