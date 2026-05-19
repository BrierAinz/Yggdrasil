"""Cargador de personalidades para agentes de Vanaheim.

Adaptado de Asgard/Lilith para funcionar de forma independiente.
"""

import json
from pathlib import Path


class PersonaLoader:
    """Cargador de personalidades de agentes."""

    def __init__(self, base_path: str | None = None):
        self.base_path = base_path or self._find_personas_path()
        self._cache: dict[str, dict] = {}

    def _find_personas_path(self) -> str:
        """Encontrar la ruta al archivo de personalidades."""
        # Intentar rutas posibles
        candidates = [
            Path("Config/personas.json"),
            Path("../Asgard/Lilith/Core/Config/personas.json"),
            Path("../../Asgard/Lilith/Core/Config/personas.json"),
        ]
        for candidate in candidates:
            if candidate.exists():
                return str(candidate)
        # Default relativo a Vanaheim
        return "Config/personas.json"

    def load_personas(self) -> dict:
        """Cargar todas las personalidades."""
        try:
            with Path(self.base_path).open(encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {"agents": {}, "common": {}}

    def get_system_prompt(self, agent_id: str, include_common: bool = True) -> str:
        """Obtener el system prompt para un agente.

        Args:
            agent_id: ID del agente (eva, adan, odin, etc.)
            include_common: Incluir instrucciones comunes

        Returns:
            System prompt completo
        """
        if agent_id in self._cache:
            persona = self._cache[agent_id]
        else:
            personas = self.load_personas()
            persona = personas.get("agents", {}).get(agent_id, {})
            self._cache[agent_id] = persona

        parts = []

        # Personalidad específica del agente
        if "personality" in persona:
            parts.append(persona["personality"])

        # Instrucciones comunes
        if include_common:
            common = self._get_common_instructions()
            if common:
                parts.append(common)

        # Capabilities específicas
        if "capabilities" in persona:
            caps = persona["capabilities"]
            if isinstance(caps, list):
                parts.append("Capabilities: " + ", ".join(caps))

        return "\n\n".join(parts) if parts else f"You are {agent_id}, an AI assistant."

    def _get_common_instructions(self) -> str:
        """Obtener instrucciones comunes a todos los agentes."""
        try:
            with Path(self.base_path).open(encoding="utf-8") as f:
                data = json.load(f)
            common = data.get("common", {})
            return common.get("instructions", "")
        except Exception:
            return ""


def get_persona_loader(base_path: str | None = None) -> PersonaLoader:
    """Obtener instancia del cargador de personalidades."""
    return PersonaLoader(base_path)
