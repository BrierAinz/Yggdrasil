"""Persona Engine v2 — builds system prompts from templates and context."""

from __future__ import annotations

import copy
from typing import TYPE_CHECKING

from .templates import PersonaTemplateLoader


if TYPE_CHECKING:
    from .models import PersonaContext, PersonaIdentity, PersonaTemplate


# Context-based prompt suffixes
_MOOD_SUFFIXES: dict[str, str] = {
    "frustrated": "El usuario está frustrado. Sé más paciente y detallado.",
    "happy": "El usuario está de buen humor. Puedes ser más directo.",
    "rushed": "El usuario tiene prisa. Sé conciso y ve al grano.",
}

_PROJECT_SUFFIXES: dict[str, str] = {
    "debugging": "Estamos en modo debugging. Sé metodológico y detallado.",
    "creative": "Estamos en modo creativo. Sé imaginativo y propone ideas.",
    "deployment": "Estamos en modo deployment. Sé cauteloso y verifica todo.",
}

_COMPLEXITY_SUFFIXES: dict[str, str] = {
    "high": "Tarea compleja. Desglosa en pasos.",
    "simple": "Tarea simple. Responde directo.",
}


class PersonaEngine:
    """Core engine that loads persona templates and builds system prompts."""

    def __init__(self, template_loader: PersonaTemplateLoader | None = None) -> None:
        """Initialize the PersonaEngine.

        Args:
            template_loader: Optional template loader. Uses default if None.
        """
        self._loader = template_loader or PersonaTemplateLoader()
        self._template_cache: dict[str, PersonaTemplate] = {}

    @property
    def loader(self) -> PersonaTemplateLoader:
        """The template loader used by this engine."""
        return self._loader

    def load_template(self, template_id: str) -> PersonaTemplate:
        """Load a specific persona template by id.

        Args:
            template_id: The persona template identifier.

        Returns:
            The resolved PersonaTemplate.
        """
        if template_id not in self._template_cache:
            self._template_cache[template_id] = self._loader.load_template(template_id)
        return self._template_cache[template_id]

    def build_prompt(
        self,
        template_id: str,
        context: PersonaContext | None = None,
        extra_context: str = "",
    ) -> str:
        """Build a complete system prompt from a template and optional context.

        Args:
            template_id: The persona template identifier.
            context: Optional runtime context to modify the prompt.
            extra_context: Additional free-form context text to append.

        Returns:
            The assembled system prompt string.
        """
        template = self.load_template(template_id)

        if context is not None:
            template = self._apply_context_modifiers(template, context)

        prompt = self._format_prompt(template.identity)

        # Append context-based suffixes
        suffixes: list[str] = []
        if context is not None:
            if context.user_mood in _MOOD_SUFFIXES:
                suffixes.append(_MOOD_SUFFIXES[context.user_mood])
            if context.project_type in _PROJECT_SUFFIXES:
                suffixes.append(_PROJECT_SUFFIXES[context.project_type])
            if context.complexity in _COMPLEXITY_SUFFIXES:
                suffixes.append(_COMPLEXITY_SUFFIXES[context.complexity])

        if suffixes:
            prompt += "\n\n" + "\n".join(suffixes)

        if extra_context:
            prompt += f"\n\n{extra_context}"

        return prompt

    def _apply_context_modifiers(
        self,
        template: PersonaTemplate,
        context: PersonaContext,
    ) -> PersonaTemplate:
        """Apply dynamic context modifiers from the template based on context state.

        Matches context fields (user_mood, project_type) to modifier entries
        defined in the template, appending any extra rules they specify.

        Args:
            template: The base persona template.
            context: The runtime context.

        Returns:
            A new PersonaTemplate with context modifiers applied.
        """
        template = copy.deepcopy(template)

        # Determine which context keys to check
        context_keys: list[str] = []
        if context.user_mood and context.user_mood != "neutral":
            context_keys.append(context.user_mood)
        if context.project_type:
            context_keys.append(context.project_type)

        modifiers = template.context_modifiers
        extra_rules: list[str] = []

        for key in context_keys:
            modifier = modifiers.get(key, {})
            if "append_rules" in modifier:
                extra_rules.extend(modifier["append_rules"])

        if extra_rules:
            template.identity.rules.extend(extra_rules)

        return template

    @staticmethod
    def _format_prompt(
        identity: PersonaIdentity,
        rules_override: list[str] | None = None,
    ) -> str:
        """Format the final system prompt string from a PersonaIdentity.

        Args:
            identity: The persona identity to format.
            rules_override: Optional list to override identity rules.

        Returns:
            The formatted system prompt string.
        """
        parts: list[str] = []

        if identity.name:
            parts.append(f"Eres {identity.name}.")
        if identity.role:
            parts.append(f"Rol: {identity.role}")
        if identity.description:
            parts.append(identity.description)
        if identity.tone:
            parts.append(f"Tono: {identity.tone}")
        if identity.vocabulary:
            parts.append(f"Vocabulario: {identity.vocabulary}")

        rules = rules_override if rules_override is not None else identity.rules
        if rules:
            parts.append("Reglas:")
            for i, rule in enumerate(rules, 1):
                parts.append(f"  {i}. {rule}")

        if identity.format_spec:
            parts.append(f"Formato: {identity.format_spec}")

        return "\n\n".join(parts)
