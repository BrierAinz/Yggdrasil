"""
Telegram Bot - Wrapper para compatibilidad con LILITH.bat
Importa y ejecuta el bot principal desde telegram_bot.py
"""
import sys
from pathlib import Path

# Agregar directorio padre al path para importar Core si es necesario
sys.path.insert(0, str(Path(__file__).parent.parent))

# Importar y ejecutar el bot principal
try:
    from telegram_bot import main

    if __name__ == "__main__":
        print("[Telegram Bot] Iniciando desde wrapper bot.py...")
        main()
except ImportError as e:
    print(f"[Telegram Bot] Error importando: {e}")
    print("[Telegram Bot] Asegúrate de tener telegram_bot.py en este directorio")
    sys.exit(1)
except Exception as e:
    print(f"[Telegram Bot] Error iniciando: {e}")
    sys.exit(1)
