"""
Skill: pixel_prompt
Genera prompts optimizados para arte pixel, concept art y assets de juegos.
Especializado en Stable Diffusion y modelos de imagen.
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

ESTILOS = {
    "pixel": {
        "tags": "pixel art, 16-bit, retro, sprite, game asset, clean pixels, no anti-aliasing",
        "negative": "blurry, 3d render, photorealistic, smooth shading, anti-aliased",
    },
    "concept": {
        "tags": "concept art, digital painting, artstation, detailed, professional",
        "negative": "photo, 3d render, pixel art, low quality, amateur",
    },
    "souls": {
        "tags": "dark fantasy, dark souls style, gothic, atmospheric, moody lighting, detailed armor",
        "negative": "bright, colorful, cartoon, anime, chibi, cute",
    },
    "horror": {
        "tags": "horror, dark, creepy, atmospheric, unsettling, liminal space, dread",
        "negative": "bright, happy, colorful, cute, cartoon, safe",
    },
    "sprite": {
        "tags": "game sprite sheet, transparent background, multiple poses, character design, 2d game asset",
        "negative": "background, photorealistic, 3d, single image",
    },
}


def ejecutar(
    descripcion: str = "", estilo: str = "souls", resolucion: str = "512x512"
) -> str:
    """Genera prompt optimizado para generacion de arte."""
    from src.llm.gemini_client import GeminiClient

    if not descripcion:
        return f"ERROR: Se necesita 'descripcion' del arte. Estilos: {list(ESTILOS.keys())}"

    estilo = estilo.lower()
    if estilo not in ESTILOS:
        return f"ERROR: Estilo '{estilo}' no valido. Usa: {list(ESTILOS.keys())}"

    style_info = ESTILOS[estilo]

    gemini = GeminiClient()
    prompt = f"""Eres un experto en ingenieria de prompts para Stable Diffusion.
Genera un prompt OPTIMIZADO para esta descripcion:

Descripcion: {descripcion}
Estilo: {estilo}
Resolucion: {resolucion}

Incluye:
1. **Prompt positivo** (en ingles, con pesos entre parentesis, tags separados por coma)
   Tags base del estilo: {style_info['tags']}
2. **Prompt negativo** (lo que NO quieres)
   Tags base: {style_info['negative']}
3. **Settings recomendados** (steps, cfg scale, sampler)
4. **Variaciones** (3 versiones del mismo prompt con diferentes enfoques)

Formato de pesos: (palabra:1.2) para enfasis, ((palabra)) para mucho enfasis.
Responde en formato limpio, listo para copiar."""

    resultado = gemini.generate_text(prompt, model="gemini-2.0-flash")
    if not resultado:
        return "ERROR: No se pudo generar el prompt."

    # Save
    out_path = os.path.join(
        workspace_root,
        "Taller",
        f"art_prompt_{estilo}_{time.strftime('%Y%m%d_%H%M')}.md",
    )
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(f"# Art Prompt: {descripcion[:50]}\n")
        f.write(f"*Estilo: {estilo} | {time.strftime('%Y-%m-%d %H:%M')}*\n\n")
        f.write(resultado)

    return f"SUCCESS: Prompt de arte generado.\n\n{resultado}"


if __name__ == "__main__":
    d = (
        sys.argv[1]
        if len(sys.argv) > 1
        else "Un caballero corrupto con armadura de hueso en un castillo en ruinas"
    )
    e = sys.argv[2] if len(sys.argv) > 2 else "souls"
    print(ejecutar(d, e))
