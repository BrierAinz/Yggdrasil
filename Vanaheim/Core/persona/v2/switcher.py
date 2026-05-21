"""PersonaSwitcher — runtime persona switching with history and rollback."""

from __future__ import annotations

import time
from typing import TYPE_CHECKING

from .models import PersonaContext, PersonaSwitchResult


if TYPE_CHECKING:
    from .engine import PersonaEngine


class PersonaSwitcher:
    """Manage runtime persona switches with history tracking and rollback."""

    def __init__(self, engine: PersonaEngine) -> None:
        """Initialize the PersonaSwitcher.

        Args:
            engine: The PersonaEngine instance to use for prompt building.
        """
        self._engine = engine
        self.current_persona: str = ""
        self._current_prompt: str = ""
        self._current_context: PersonaContext = PersonaContext()
        self.history: list[PersonaSwitchResult] = []

    def switch(
        self,
        template_id: str,
        context: PersonaContext | None = None,
    ) -> PersonaSwitchResult:
        """Switch to a new persona and record the switch.

        Args:
            template_id: The persona template to switch to.
            context: Optional context to apply when building the prompt.

        Returns:
            PersonaSwitchResult with the generated prompt and metadata.
        """
        effective_context = context or PersonaContext()
        prompt = self._engine.build_prompt(template_id, context=effective_context)

        result = PersonaSwitchResult(
            template_id=template_id,
            system_prompt=prompt,
            context_applied=effective_context,
            timestamp=time.time(),
        )

        self.current_persona = template_id
        self._current_prompt = prompt
        self._current_context = effective_context
        self.history.append(result)

        return result

    def get_current_prompt(self) -> str:
        """Return the system prompt of the currently active persona.

        Returns:
            The current system prompt string, or empty string if none set.
        """
        return self._current_prompt

    def get_history(self, limit: int = 10) -> list[PersonaSwitchResult]:
        """Return the last ``limit`` persona switch results.

        Args:
            limit: Maximum number of history entries to return.

        Returns:
            List of PersonaSwitchResult, most recent last.
        """
        return self.history[-limit:]

    def rollback(self) -> PersonaSwitchResult | None:
        """Revert to the previous persona in history.

        Returns:
            The PersonaSwitchResult of the previous persona, or None if
            there is no previous state to roll back to.
        """
        if len(self.history) < 2:
            return None

        # Remove the current entry and switch back to the previous one
        self.history.pop()
        previous = self.history[-1]

        self.current_persona = previous.template_id
        self._current_prompt = previous.system_prompt
        self._current_context = previous.context_applied

        return previous
