from vanaheim.bot import BaseBot
from vanaheim.config import BotConfig


class DummyBot(BaseBot):
    name = "dummy"
    version = "1.0.0"

    def run(self):
        pass

    def handle_message(self, message: str) -> str:
        return f"Echo: {message}"


def test_bot_health():
    bot = DummyBot()
    health = bot.health_check()
    assert health["name"] == "dummy"
    assert health["status"] == "healthy"


def test_bot_handle_message():
    bot = DummyBot()
    assert bot.handle_message("hola") == "Echo: hola"


def test_config_persistence(tmp_path):
    cfg = BotConfig("test_bot", config_dir=tmp_path)
    cfg.set("token", "abc123")
    cfg2 = BotConfig("test_bot", config_dir=tmp_path)
    assert cfg2.get("token") == "abc123"
