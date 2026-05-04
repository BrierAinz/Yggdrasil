# Vanaheim Framework

> Where all bots find their home, as the Vanir once found theirs.

Base framework for all Vanaheim bots: configuration management, lifecycle hooks, Telegram integration, and Pydantic data models.

## Installation

```bash
pip install -e .
```

## Usage

```python
from vanaheim import BaseBot, BotConfig

config = BotConfig("my_bot")
config.set("api_token", "your-telegram-token")

class MyBot(BaseBot):
    name = "my_bot"
    def run(self): ...
    def handle_message(self, message: str) -> str:
        return f"Echo: {message}"

bot = MyBot(config=config._data)
bot.health_check()  # {'name': 'my_bot', 'version': '0.1.0', 'status': 'healthy'}
```

## Architecture

This package is part of the Vanaheim realm in the Yggdrasil ecosystem.

## License

MIT
