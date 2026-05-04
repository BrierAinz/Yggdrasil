"""
Persona Loader — Sistema de identidades del Panteón de Lilith.
Carga y compone system prompts para todos los agentes.
"""
import json
from pathlib import Path
from typing import Any, Dict, Optional


class PersonaLoader:
    """
    Carga y compone system prompts para agentes del Panteón.
    Capas: BLOQUE_COMUN + IDENTIDAD_AGENTE + CONTEXTO_TAREA
    """

    def __init__(self, base_path: Optional[Path] = None):
        self._base_path = (
            Path(base_path)
            if base_path
            else Path(__file__).resolve().parent.parent.parent
        )
        self._config_path = self._base_path / "Config" / "personas.json"
        self._config: Optional[Dict[str, Any]] = None
        self._load_config()

    def _load_config(self) -> None:
        """Carga personas.json desde Config."""
        try:
            if self._config_path.exists():
                with open(self._config_path, "r", encoding="utf-8") as f:
                    self._config = json.load(f)
            else:
                self._config = self._default_config()
        except Exception as e:
            print(f"[PersonaLoader] Error cargando config: {e}")
            self._config = self._default_config()

    def _default_config(self) -> Dict[str, Any]:
        """Config mínima de fallback si no existe personas.json."""
        return {
            "version": "1.0",
            "common_block": "[SISTEMA LILITH]\nEres parte del Panteón de Lilith.\nTu creador es Ainz (Martin).",
            "owner_profile": {
                "name": "Martin",
                "alias": "Ainz",
                "age": 23,
                "language": "es-MX",
                "style": "directo, técnico",
                "projects": ["Lilith", "Yggdrasil"],
            },
            "agents": {},
        }

    def get_system_prompt(
        self, agent_name: str, extra_context: str = "", include_common: bool = True
    ) -> str:
        """
        Compone el system prompt para un agente.

        Args:
            agent_name: Nombre del agente (lilith, odin, eva, adan, shalltear)
            extra_context: Contexto adicional a inyectar (memoria, tarea específica)
            include_common: Si True, incluye BLOQUE_COMUN

        Returns:
            System prompt completo compuesto
        """
        if not self._config:
            return f"Eres {agent_name}, agente del Panteón de Lilith."

        parts = []

        # Capa 1: BLOQUE_COMUN
        if include_common:
            common = self._config.get("common_block", "")
            if common:
                parts.append(common)

        # Capa 2: IDENTIDAD_AGENTE
        agents = self._config.get("agents", {})
        agent_config = agents.get(agent_name.lower(), {})

        if agent_config:
            identity = agent_config.get("identity", "")
            rules = agent_config.get("rules", "")
            format_spec = agent_config.get("format", "")

            if identity:
                parts.append(identity)
            if rules:
                parts.append(rules)
            if format_spec:
                parts.append(format_spec)
        else:
            # Fallback si el agente no está en config
            parts.append(
                f"[IDENTIDAD]\nEres {agent_name}, agente del Panteón de Lilith."
            )

        # Capa 3: CONTEXTO_TAREA
        if extra_context:
            parts.append(f"[CONTEXTO]\n{extra_context}")

        return "\n\n".join(parts)

    def get_owner_context(self) -> str:
        """Retorna bloque de contexto del owner para inyectar en prompts."""
        owner = self._config.get("owner_profile", {})
        if not owner:
            return "Owner: Ainz"

        lines = [
            f"[OWNER]",
            f"Nombre: {owner.get('name', 'Martin')} (alias {owner.get('alias', 'Ainz')})",
            f"Edad: {owner.get('age', 23)} años",
            f"Estilo: {owner.get('style', 'directo, técnico')}",
            f"Proyectos: {', '.join(owner.get('projects', ['Lilith', 'Yggdrasil']))}",
        ]

        prefs = owner.get("preferences", {})
        if prefs:
            lines.append(f"Preferencias: {prefs}")

        return "\n".join(lines)

    def get_owner_profile(self) -> Dict[str, Any]:
        """Retorna el perfil completo del owner."""
        return self._config.get(
            "owner_profile",
            {
                "name": "Martin",
                "alias": "Ainz",
                "age": 23,
                "language": "es-MX",
                "style": "directo, técnico",
                "projects": ["Lilith", "Yggdrasil"],
            },
        )

    def get_agent_config(self, agent_name: str) -> Dict[str, Any]:
        """Retorna la configuración cruda de un agente."""
        agents = self._config.get("agents", {})
        return agents.get(agent_name.lower(), {})

    def get_identity_only(self, agent_name: str) -> str:
        """Retorna solo la identidad del agente (sin reglas ni formato)."""
        agents = self._config.get("agents", {})
        agent_config = agents.get(agent_name.lower(), {})
        return agent_config.get("identity", f"Eres {agent_name}, agente del Panteón.")

    def get_rules_only(self, agent_name: str) -> str:
        """Retorna solo las reglas del agente."""
        agents = self._config.get("agents", {})
        agent_config = agents.get(agent_name.lower(), {})
        return agent_config.get("rules", "")

    def get_format_only(self, agent_name: str) -> str:
        """Retorna solo el formato del agente."""
        agents = self._config.get("agents", {})
        agent_config = agents.get(agent_name.lower(), {})
        return agent_config.get("format", "")

    def list_agents(self) -> list:
        """Lista todos los agentes configurados."""
        return list(self._config.get("agents", {}).keys())

    def reload(self) -> None:
        """Recarga la configuración desde disco."""
        self._load_config()


# Singleton para uso global
_loader: Optional[PersonaLoader] = None


def get_persona_loader(base_path: Optional[Path] = None) -> PersonaLoader:
    """
    Obtiene el singleton del PersonaLoader.

    Args:
        base_path: Path base del proyecto (opcional, para inicialización)

    Returns:
        Instancia de PersonaLoader
    """
    global _loader
    if _loader is None:
        _loader = PersonaLoader(base_path)
    return _loader


def reset_persona_loader() -> None:
    """Resetea el singleton (útil para tests o reload forzado)."""
    global _loader
    _loader = None
