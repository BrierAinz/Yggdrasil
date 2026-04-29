#!/usr/bin/env python3
"""EchoBot — Bot de ejemplo funcional usando vanaheim-framework."""
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "vanaheim-framework"))

from vanaheim.bot import BaseBot
from vanaheim.config import load_config


class EchoBot(BaseBot):
    name = "echo"
    description = "Bot de eco con soporte de tools"

    async def on_message(self, message: str, context: dict) -> str:
        msg = message.strip()

        if msg.startswith("/tools"):
            return "Tools: system_info, system_time, file_read, web_search, browser, coding"

        if msg.startswith("/search "):
            query = msg[8:]
            result = self.execute_tool("web_search", {"query": query})
            hits = result.get("results", [])
            if hits:
                lines = [f"{i+1}. {h['title']} - {h['url']}" for i, h in enumerate(hits[:3])]
                return "Resultados:
" + "
".join(lines)
            return "Sin resultados."

        if msg.startswith("/status"):
            result = self.execute_tool("system_info", {})
            return f"Sistema: {result}"

        return f"Echo: {msg}"


async def main():
    config = load_config()
    bot = EchoBot(config)
    print(f"[EchoBot] Iniciado. Escribe /salir para terminar.")
    while True:
        try:
            user = input("> ").strip()
        except (EOFError, KeyboardInterrupt):
            break
        if user in ("/salir", "/quit"):
            break
        resp = await bot.on_message(user, {})
        print(f"[{bot.name}] {resp}")


if __name__ == "__main__":
    asyncio.run(main())
