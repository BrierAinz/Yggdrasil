"""Base platform class — defines the interface for all platform handlers."""

from abc import ABC, abstractmethod
from typing import Any


class BasePlatform(ABC):
    """Base class for AI chat platform handlers."""

    name: str = "base"
    url: str = ""

    @abstractmethod
    async def analyze_trending(self) -> dict[str, Any]:
        """Analyze trending characters on this platform.

        Returns:
            Dict with: top_genres, popular_tags, gap_opportunities, recommended_strategies
        """
        ...

    @abstractmethod
    async def suggest_tags(self, character: dict[str, Any]) -> list[str]:
        """Suggest optimal tags for a character on this platform.

        Args:
            character: Character dict with at least 'name' and 'description'

        Returns:
            List of recommended tags ordered by relevance and visibility
        """
        ...

    def get_format_requirements(self) -> dict[str, Any]:
        """Return platform-specific character format requirements.

        Returns:
            Dict with field names, max lengths, required/optional, and examples
        """
        return {
            "name": {"max_length": 50, "required": True},
            "description": {"max_length": 500, "required": True},
            "greeting": {"max_length": 2000, "required": True},
            "personality": {"max_length": 2000, "required": False},
            "scenario": {"max_length": 3000, "required": False},
            "tags": {"max_count": 10, "required": True},
        }
