"""
PromptTemplate — Plantillas de sistema reutilizables para agentes.
Permite componer system prompts desde secciones nombradas, con
soporte para override por instancia y marcadores de memoria.
"""
from dataclasses import dataclass, field
from typing import Dict, List, Optional

# ─── Secciones estándar ───────────────────────────────────────────────────────

SECTION_IDENTITY = "identity"  # Quién es el agente
SECTION_RULES = "rules"  # Reglas absolutas de comportamiento
SECTION_CAPABILITIES = "capabilities"  # Qué puede hacer
SECTION_FORMAT = "format"  # Formato de respuesta esperado
SECTION_MEMORY = "memory"  # Bloque de memoria (inyectado dinámicamente)
SECTION_EXTRA = "extra"  # Contexto adicional de canal/rol


@dataclass
class AgentPromptConfig:
    """
    Configuración de prompt para un agente.
    `sections` es un dict ordenado section_name → text.
    Las secciones se concatenan en orden de inserción.
    """

    agent_name: str
    sections: Dict[str, str] = field(default_factory=dict)
    separator: str = "\n\n"

    def add_section(self, name: str, text: str) -> "AgentPromptConfig":
        self.sections[name] = text.strip()
        return self

    def override_section(self, name: str, text: str) -> "AgentPromptConfig":
        """Override (o añade) una sección."""
        self.sections[name] = text.strip()
        return self

    def remove_section(self, name: str) -> "AgentPromptConfig":
        self.sections.pop(name, None)
        return self

    def build(
        self,
        memory_block: str = "",
        extra_context: str = "",
    ) -> str:
        """
        Construye el system prompt final.
        - `memory_block`: texto de memoria del agente (Muninn/semantic).
        - `extra_context`: instrucciones adicionales de canal o rol.
        """
        parts: List[str] = []
        for name, text in self.sections.items():
            if name == SECTION_MEMORY:
                # La sección de memoria se rellena con memory_block en tiempo de build
                if memory_block:
                    parts.append(memory_block.strip())
            elif name == SECTION_EXTRA:
                if extra_context:
                    parts.append(extra_context.strip())
            elif text:
                parts.append(text)

        # Si no hay sección MEMORY explícita pero tenemos memory_block, añadir al final
        if SECTION_MEMORY not in self.sections and memory_block:
            parts.append(memory_block.strip())
        if SECTION_EXTRA not in self.sections and extra_context:
            parts.append(extra_context.strip())

        return self.separator.join(p for p in parts if p)


# ─── Fábrica ──────────────────────────────────────────────────────────────────


def make_prompt(agent_name: str) -> AgentPromptConfig:
    """Retorna una AgentPromptConfig vacía para el agente dado."""
    return AgentPromptConfig(agent_name=agent_name)


def from_string(agent_name: str, system_prompt: str) -> AgentPromptConfig:
    """
    Crea una AgentPromptConfig desde un string monolítico (compatibilidad legado).
    El string completo se registra como sección SECTION_IDENTITY.
    """
    cfg = AgentPromptConfig(agent_name=agent_name)
    cfg.add_section(SECTION_IDENTITY, system_prompt)
    cfg.add_section(SECTION_MEMORY, "")  # placeholder
    cfg.add_section(SECTION_EXTRA, "")  # placeholder
    return cfg
