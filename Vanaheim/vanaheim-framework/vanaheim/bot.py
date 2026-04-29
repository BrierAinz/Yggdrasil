import logging
from abc import ABC, abstractmethod
from typing import Any, Dict


class BaseBot(ABC):
    name: str = "unnamed_bot"
    version: str = "0.1.0"
    description: str = ""

    def __init__(self, config: Dict[str, Any] = None):
        self.config = config or {}
        self.logger = logging.getLogger(self.name)
        self._setup_logging()

    def _setup_logging(self):
        handler = logging.StreamHandler()
        formatter = logging.Formatter(
            "%(asctime)s [%(name)s] %(levelname)s: %(message)s"
        )
        handler.setFormatter(formatter)
        self.logger.addHandler(handler)
        self.logger.setLevel(logging.INFO)

    @abstractmethod
    def run(self):
        pass

    @abstractmethod
    def handle_message(self, message: str) -> str:
        pass

    def health_check(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "version": self.version,
            "status": "healthy",
        }
