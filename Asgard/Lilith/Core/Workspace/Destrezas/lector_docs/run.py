"""
Skill: lector_docs
Lee una URL de documentacion tecnica, extrae el contenido y genera un resumen con Gemini.
"""
import os
import sys
import time

import requests

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


def _extract_text(html: str) -> str:
    """Extrae texto limpio del HTML."""
    try:
        from bs4 import BeautifulSoup

        soup = BeautifulSoup(html, "html.parser")
        for tag in soup(["script", "style", "nav", "footer", "header"]):
            tag.decompose()
        text = soup.get_text(separator="\n", strip=True)
        lines = [l.strip() for l in text.split("\n") if l.strip()]
        return "\n".join(lines)
    except ImportError:
        import re

        text = re.sub(r"<[^>]+>", " ", html)
        text = re.sub(r"\s+", " ", text)
        return text.strip()


def ejecutar(url: str = "", tema: str = "documentacion") -> str:
    """Lee una URL y genera un resumen."""
    from src.llm.gemini_client import GeminiClient

    if not url:
        return "ERROR: Se necesita 'url' de la documentacion."

    # Fetch URL
    try:
        resp = requests.get(url, timeout=15, headers={"User-Agent": "Lilith/2.0"})
        resp.raise_for_status()
        content = _extract_text(resp.text)
    except Exception as e:
        return f"ERROR: No se pudo leer la URL: {e}"

    if len(content) > 12000:
        content = content[:12000] + "\n... (truncado)"

    if not content or len(content) < 50:
        return "ERROR: No se pudo extraer contenido util de la URL."

    gemini = GeminiClient()
    prompt = f"""Eres Lilith. Resume la siguiente documentacion tecnica en ESPAÃ‘OL de forma clara.

Estructura:
1. **Que es** (2-3 oraciones)
2. **Conceptos principales** (lista)
3. **Como usarlo** (pasos practicos)
4. **Ejemplo de codigo** (si aplica)
5. **Tips** (buenas practicas)

URL: {url}
Contenido:
{content}
"""
    resumen = gemini.generate_text(prompt, model="gemini-2.0-flash")
    if not resumen:
        return "ERROR: No se pudo resumir con Gemini."

    # Guardar
    nombre = tema.lower().replace(" ", "_")[:40]
    output_path = os.path.join(
        workspace_root, "Mente", "conceptos_clave", f"{nombre}.md"
    )
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(f"# {tema}\n")
        f.write(f"*Fuente: {url}*\n")
        f.write(f"*Leido por Lilith el {time.strftime('%Y-%m-%d %H:%M')}*\n\n")
        f.write(resumen)

    return f"SUCCESS: Documentacion resumida y guardada en Mente/conceptos_clave/{nombre}.md\n\n{resumen[:500]}..."


if __name__ == "__main__":
    u = (
        sys.argv[1]
        if len(sys.argv) > 1
        else "https://docs.python.org/3/library/asyncio.html"
    )
    t = sys.argv[2] if len(sys.argv) > 2 else "Python Asyncio"
    print(ejecutar(u, t))
