#!/usr/bin/env python3
"""Launcher unificado para todos los bots de Vanaheim."""

import sys
from pathlib import Path


sys.path.insert(0, str(Path(__file__).parent / "vanaheim-framework"))

BOTS = {
    "vanaheim": ("Bots.vanaheim-bot", "main"),
    "telegram": ("Bots.bot_telegram", "main"),
    "agente": ("Bots.llm_agente_2026", "main"),
    "conversation": ("Bots.conversation_bot", "main"),
    "scraper": ("Bots.scraper_bot", "main"),
    "plantilla": ("Bots.plantilla-bot", "main"),
}


def main():
    bot_name = sys.argv[1] if len(sys.argv) > 1 else "vanaheim"
    if bot_name not in BOTS:
        print(f"Bot desconocido: {bot_name}")
        print(f"Disponibles: {', '.join(BOTS.keys())}")
        sys.exit(1)

    module_path, func_name = BOTS[bot_name]
    try:
        import importlib

        module = importlib.import_module(module_path)
        getattr(module, func_name)()
    except ImportError as e:
        print(f"Error cargando bot: {e}")
        print("Asegurate de tener el entorno virtual activado.")
        sys.exit(1)
    except AttributeError:
        print(f"El bot no tiene funcion '{func_name}'")
        sys.exit(1)


if __name__ == "__main__":
    main()
