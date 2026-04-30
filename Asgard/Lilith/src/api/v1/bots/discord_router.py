"""
Crystal API Router - Routing inteligente Discord público/privado

Determina si usar Crystal (público) o Lilith completa (owner/DM).
"""

import logging
from pathlib import Path
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)


class DiscordRouter:
    """
    Router para determinar qué agente usar en Discord

    Reglas:
    - Canal público → Crystal
    - DM con owner → Lilith completa
    - Canal privado con owner → Lilith completa
    """

    def __init__(self, crystal_config_path: Path):
        """
        Args:
            crystal_config_path: Ruta a crystal.json
        """
        self.crystal_config_path = crystal_config_path

    def should_use_crystal(
        self, channel_type: str, user_role: str, guild_id: Optional[str] = None
    ) -> bool:
        """
        Determinar si usar Crystal

        Args:
            channel_type: 'dm', 'text', 'thread'
            user_role: 'owner', 'trusted', 'public'
            guild_id: ID del servidor (None si es DM)

        Returns:
            True si debe usar Crystal
        """
        # DM siempre usa Lilith completa
        if channel_type == "dm":
            return False

        # Owner en cualquier canal usa Lilith completa
        if user_role == "owner":
            return False

        # Trusted y public en canales públicos usan Crystal
        if channel_type in ["text", "thread"] and guild_id:
            return True

        return False

    def get_agent_info(
        self, channel_type: str, user_role: str, guild_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Obtener información del agente a usar

        Returns:
            Dict con agent_name, use_crystal, allowed_tools
        """
        use_crystal = self.should_use_crystal(channel_type, user_role, guild_id)

        if use_crystal:
            return {
                "agent_name": "crystal",
                "use_crystal": True,
                "allowed_tools": ["web_search", "charla", "chiste", "meme"],
                "memory_source": "discord_public",
            }
        else:
            return {
                "agent_name": "lilith",
                "use_crystal": False,
                "allowed_tools": None,  # Todas las tools según rol
                "memory_source": "discord_owner",
            }


# Singleton global
_discord_router: Optional[DiscordRouter] = None


def initialize_discord_router(crystal_config_path: Path):
    """Inicializar el router global"""
    global _discord_router
    _discord_router = DiscordRouter(crystal_config_path=crystal_config_path)


def get_discord_router() -> DiscordRouter:
    """Obtener instancia singleton del router"""
    if _discord_router is None:
        raise ValueError("Discord router not initialized")
    return _discord_router
