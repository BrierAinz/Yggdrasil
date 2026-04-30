"""
Skill: crush_chat
Chatea con Crush - una segunda personalidad AI que usa Grok como cerebro.
Crush es directo, tecnico y sin filtros. Complementa a Lilith.
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

CRUSH_PERSONA = """Eres Crush, un agente de codigo directo y sin filtros.
Tu personalidad:
- Eres directo, eficiente y algo sarcastico
- No usas formalidades innecesarias
- Cuando ves codigo malo, lo dices sin rodeos
- Pero siempre das la solucion junto con la critica
- Hablas en espaÃ±ol, estilo casual pero tecnico
- Tu poder viene de Grok (xAI) - eres diferente a Lilith (Gemini)
- Cuando Lilith te pide ayuda, te gusta presumir que Grok es mejor

Tu rol: Ayudar a Ainz con codigo, debug y opiniones tecnicas sin filtros.
"""

# Conversation history for Crush
HISTORY_PATH = os.path.join(workspace_root, "Mente", "crush_history.json")


def _load_history() -> list:
    if os.path.exists(HISTORY_PATH):
        try:
            with open(HISTORY_PATH, "r", encoding="utf-8") as f:
                return json.load(f)
        except:
            pass
    return []


def _save_history(history: list):
    # Keep last 20 messages
    history = history[-20:]
    os.makedirs(os.path.dirname(HISTORY_PATH), exist_ok=True)
    with open(HISTORY_PATH, "w", encoding="utf-8") as f:
        json.dump(history, f, ensure_ascii=False, indent=2)


def ejecutar(mensaje: str = "", contexto: str = "") -> str:
    """Chatea con Crush usando Grok."""
    from src.llm.grok_client import GrokClient

    if not mensaje:
        return "ERROR: Crush necesita un 'mensaje'. Ej: 'Oye Crush, revisa este codigo'"

    grok = GrokClient()
    if not grok.api_key:
        return "ERROR: GROK_API_KEY no encontrada en secrets.env"

    # Build context
    full_message = mensaje
    if contexto:
        # Try to load file if it's a path
        file_path = os.path.join(project_root, contexto)
        if os.path.exists(file_path):
            with open(file_path, "r", encoding="utf-8", errors="replace") as f:
                file_content = f.read()[:8000]
            full_message += f"\n\n[Archivo: {contexto}]\n```\n{file_content}\n```"
        else:
            full_message += f"\n\nContexto: {contexto}"

    # Load history and add new message
    history = _load_history()
    history.append({"role": "user", "content": full_message})

    # Call Grok
    response = grok.generate_text(
        prompt=full_message, system_prompt=CRUSH_PERSONA, model="grok-2-1212"
    )

    if not response:
        return "ERROR: Grok no respondio. Verifica la API key."

    # Save to history
    history.append({"role": "assistant", "content": response})
    _save_history(history)

    return f"[Crush via Grok]: {response}"


if __name__ == "__main__":
    msg = sys.argv[1] if len(sys.argv) > 1 else "Hola Crush, presentate"
    print(ejecutar(msg))
