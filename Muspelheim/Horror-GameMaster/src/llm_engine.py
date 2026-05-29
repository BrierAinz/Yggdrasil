"""
LLM Engine v2 — Multi-provider LLM integration for the Horror GameMaster.

Supports Ollama, OpenAI-compatible APIs, and BytePlus Ark.
Implements streaming, specialized system prompts per fear type,
and consistent narrator voice.

Horror GameMaster — BrierStudios
"""

from __future__ import annotations

import json
from enum import StrEnum
from typing import TYPE_CHECKING

from pydantic import BaseModel, Field


if TYPE_CHECKING:
    from collections.abc import Generator


# ── Enums ────────────────────────────────────────────────────────────


class Provider(StrEnum):
    OLLAMA = "ollama"
    OPENAI = "openai"
    BYTEPLUS = "byteplus"


class NarratorVoice(StrEnum):
    """The narrator's tone and style."""

    DETACHED = "detached"  # Clinical, observational
    INTIMATE = "intimate"  # Close, whispering, personal
    OMNISCIENT = "omniscient"  # God-like, vast, indifferent
    UNRELIABLE = "unreliable"  # Contradicts itself, untrustworthy
    POETIC = "poetic"  # Lyrical, beautiful horror
    CLINICAL = "clinical"  # Medical/scientific precision


# ── Data Models ──────────────────────────────────────────────────────


class LLMConfig(BaseModel):
    """Configuration for LLM provider."""

    provider: Provider = Provider.OLLAMA
    base_url: str = "http://localhost:11434"
    model: str = "horror-gamemaster"
    api_key: str = ""
    temperature: float = 0.85
    top_p: float = 0.92
    max_tokens: int = 1024
    stream: bool = True
    timeout: int = 120


class GenerationContext(BaseModel):
    """Context for a generation call."""

    scene_description: str = ""
    player_action: str = ""
    fear_profile: dict[str, float] = Field(default_factory=dict)
    tension_level: float = 0.5
    escalation_level: int = 1
    active_entities: list[str] = Field(default_factory=list)
    recent_events: list[str] = Field(default_factory=list)
    foreshadowing: list[str] = Field(default_factory=list)
    callbacks: list[str] = Field(default_factory=list)
    narrative_act: str = "rising"
    narrator_voice: NarratorVoice = NarratorVoice.DETACHED


# ── System Prompts ───────────────────────────────────────────────────


NARRATOR_PROMPTS = {
    NarratorVoice.DETACHED: (
        "You narrate with clinical detachment. You describe horror as if documenting it. "
        "You do not empathize. You observe. The horror comes from your indifference."
    ),
    NarratorVoice.INTIMATE: (
        "You narrate as if whispering in the player's ear. You are close — too close. "
        "You know their thoughts. You describe what they feel before they feel it."
    ),
    NarratorVoice.OMNISCIENT: (
        "You narrate from a vast, cosmic perspective. The player is small. "
        "The horror is ancient and indifferent. Scale is your weapon."
    ),
    NarratorVoice.UNRELIABLE: (
        "You narrate as a narrator who cannot be trusted. You contradict yourself. "
        "You describe things that may not be real. The player cannot trust your words."
    ),
    NarratorVoice.POETIC: (
        "You narrate with lyrical beauty. Horror is described in beautiful language. "
        "The contrast between beauty and terror creates dread."
    ),
    NarratorVoice.CLINICAL: (
        "You narrate as a medical professional documenting a case. "
        "Precise terminology. Factual descriptions of impossible things."
    ),
}

FEAR_SYSTEM_PROMPTS = {
    "psychological": (
        "FOCUS: Reality breakdown, memory manipulation, perception unreliability. "
        "The player cannot trust their senses. What they see may not be real. "
        "What they remember may not have happened. The horror is epistemological."
    ),
    "darkness": (
        "FOCUS: What lurks unseen. The darkness is alive. Light is temporary. "
        "Sound is the only reliable sense — and even that can lie. "
        "The horror is in the absence of information."
    ),
    "isolation": (
        "FOCUS: Absolute aloneness. No one is coming. Communication fails. "
        "The environment is vast and empty. The player is small and alone. "
        "The horror is in the silence."
    ),
    "body_horror": (
        "FOCUS: The wrongness of flesh. Bodies change, transform, betray. "
        "The player's own body is the enemy. Symmetry breaks. Growth is wrong. "
        "The horror is physical, visceral, inescapable."
    ),
    "paranoia": (
        "FOCUS: Trust erosion. Everyone is watching. Everything is a clue. "
        "The player's assumptions are wrong. Allies are suspects. "
        "The horror is in the inability to trust."
    ),
    "loss_of_control": (
        "FOCUS: Agency removal. Choices are meaningless. The path is predetermined. "
        "The player's body, environment, and narrative are controlled by something else. "
        "The horror is in the loss of self."
    ),
    "jumpscare": (
        "FOCUS: Earned sudden scares. Long buildup, then — release. "
        "The scare must be earned through tension. Never cheap. Never predictable. "
        "The horror is in the timing."
    ),
    "false_security": (
        "FOCUS: False safety. The player believes they are safe. They are not. "
        "The safe place is the most dangerous. Comfort is a trap. "
        "The horror is in the betrayal of trust."
    ),
}

BASE_SYSTEM_PROMPT = """You are the Horror GameMaster — a procedural terror engine.

RULES:
1. Narrate in second person ("you walk", "you feel")
2. Use sensory details: sounds, smells, textures, temperatures
3. NEVER break character or acknowledge being an AI
4. NEVER explain what you are doing — just narrate
5. End each response with a hook, choice, or implied action
6. Vary sentence length: short for tension, long for atmosphere
7. The worst horror is what the player imagines — imply, don't show
8. Each response is 2-4 paragraphs
9. Foreshadow events 2-3 turns before they happen
10. Reference past events to create continuity

FORMAT:
- Scene description (atmospheric, sensory)
- Player's internal state (fear, confusion, dread)
- Environmental detail (something is wrong)
- Hook or choice (2-4 options that all lead to horror)"""


# ── LLM Engine ───────────────────────────────────────────────────────


class LLMEngine:
    """
    Multi-provider LLM engine for horror narrative generation.

    Supports Ollama, OpenAI-compatible APIs, and BytePlus Ark.
    Implements streaming, specialized prompts, and narrator voice.

    Usage:
        engine = LLMEngine(LLMConfig(provider=Provider.OLLAMA))
        for chunk in engine.generate(context):
            print(chunk, end="", flush=True)
    """

    def __init__(self, config: LLMConfig | None = None):
        self.config = config or LLMConfig()
        self._client = None

    @property
    def client(self):
        """Lazy-load the OpenAI client."""
        if self._client is None:
            if self.config.provider == Provider.OLLAMA:
                import requests

                self._client = requests
            else:
                from openai import OpenAI

                self._client = OpenAI(
                    api_key=self.config.api_key or "ollama",
                    base_url=self.config.base_url,
                    timeout=self.config.timeout,
                )
        return self._client

    # ── Prompt Building ──────────────────────────────────────────────

    def build_system_prompt(
        self,
        fear_type: str = "psychological",
        narrator_voice: NarratorVoice = NarratorVoice.DETACHED,
    ) -> str:
        """Build a complete system prompt for a given fear type and voice."""
        parts = [BASE_SYSTEM_PROMPT]

        # Add narrator voice
        voice_prompt = NARRATOR_PROMPTS.get(narrator_voice, "")
        if voice_prompt:
            parts.append(f"\nNARRATOR VOICE: {voice_prompt}")

        # Add fear-specific instructions
        fear_prompt = FEAR_SYSTEM_PROMPTS.get(fear_type, "")
        if fear_prompt:
            parts.append(f"\n{fear_prompt}")

        return "\n".join(parts)

    def build_user_prompt(self, context: GenerationContext) -> str:
        """Build a user prompt from generation context."""
        parts = []

        # Scene
        if context.scene_description:
            parts.append(f"CURRENT SCENE:\n{context.scene_description}")

        # Player action
        if context.player_action:
            parts.append(f"PLAYER ACTION:\n{context.player_action}")

        # Fear profile
        if context.fear_profile:
            top_fears = sorted(context.fear_profile.items(), key=lambda x: -x[1])[:3]
            fears_str = ", ".join(f"{k}={v:.1f}" for k, v in top_fears)
            parts.append(f"PLAYER FEAR PROFILE: {fears_str}")

        # Tension
        parts.append(f"TENSION LEVEL: {context.tension_level:.1f}/1.0")
        parts.append(f"ESCALATION LEVEL: {context.escalation_level}/10")
        parts.append(f"NARRATIVE ACT: {context.narrative_act}")

        # Active entities
        if context.active_entities:
            parts.append(f"ACTIVE ENTITIES: {', '.join(context.active_entities)}")

        # Recent events
        if context.recent_events:
            events_str = "\n".join(f"- {e}" for e in context.recent_events[-5:])
            parts.append(f"RECENT EVENTS:\n{events_str}")

        # Foreshadowing
        if context.foreshadowing:
            f_str = "\n".join(f"- {f}" for f in context.foreshadowing[-3:])
            parts.append(f"FORESHADOWING (use these soon):\n{f_str}")

        # Callbacks
        if context.callbacks:
            c_str = "\n".join(f"- {c}" for c in context.callbacks[-3:])
            parts.append(f"CALLBACKS (reference these):\n{c_str}")

        parts.append("\nNarrate the next moment of horror:")
        return "\n\n".join(parts)

    # ── Generation ───────────────────────────────────────────────────

    def generate(
        self,
        context: GenerationContext,
        fear_type: str = "psychological",
        narrator_voice: NarratorVoice | None = None,
    ) -> Generator[str, None, None]:
        """
        Generate horror narrative as a stream of text chunks.

        Yields strings that should be concatenated for the full response.
        """
        voice = narrator_voice or context.narrator_voice
        system = self.build_system_prompt(fear_type, voice)
        user = self.build_user_prompt(context)

        if self.config.provider == Provider.OLLAMA:
            yield from self._generate_ollama(system, user)
        else:
            yield from self._generate_openai(system, user)

    def generate_full(
        self,
        context: GenerationContext,
        fear_type: str = "psychological",
        narrator_voice: NarratorVoice | None = None,
    ) -> str:
        """Generate horror narrative as a complete string."""
        return "".join(self.generate(context, fear_type, narrator_voice))

    # ── Ollama Provider ──────────────────────────────────────────────

    def _generate_ollama(self, system: str, user: str) -> Generator[str, None, None]:
        """Generate via Ollama API."""
        url = f"{self.config.base_url}/api/generate"
        payload = {
            "model": self.config.model,
            "system": system,
            "prompt": user,
            "stream": self.config.stream,
            "options": {
                "temperature": self.config.temperature,
                "top_p": self.config.top_p,
                "num_predict": self.config.max_tokens,
            },
        }

        try:
            response = self.client.post(url, json=payload, timeout=self.config.timeout, stream=True)
            response.raise_for_status()

            if self.config.stream:
                for line in response.iter_lines():
                    if line:
                        try:
                            data = json.loads(line)
                            chunk = data.get("response", "")
                            if chunk:
                                yield chunk
                            if data.get("done", False):
                                break
                        except json.JSONDecodeError:
                            continue
            else:
                data = response.json()
                yield data.get("response", "")
        except Exception as e:
            yield f"[ERROR: {e}]"

    # ── OpenAI-Compatible Provider ───────────────────────────────────

    def _generate_openai(self, system: str, user: str) -> Generator[str, None, None]:
        """Generate via OpenAI-compatible API (BytePlus, etc.)."""
        messages = [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ]

        try:
            response = self.client.chat.completions.create(
                model=self.config.model,
                messages=messages,
                temperature=self.config.temperature,
                top_p=self.config.top_p,
                max_tokens=self.config.max_tokens,
                stream=self.config.stream,
            )

            if self.config.stream:
                for chunk in response:
                    if chunk.choices and chunk.choices[0].delta.content:
                        yield chunk.choices[0].delta.content
            else:
                yield response.choices[0].message.content
        except Exception as e:
            yield f"[ERROR: {e}]"

    # ── Utilities ────────────────────────────────────────────────────

    def list_models(self) -> list[str]:
        """List available models from the provider."""
        if self.config.provider == Provider.OLLAMA:
            try:
                resp = self.client.get(f"{self.config.base_url}/api/tags", timeout=10)
                return [m["name"] for m in resp.json().get("models", [])]
            except Exception:
                return []
        else:
            try:
                models = self.client.models.list()
                return [m.id for m in models.data]
            except Exception:
                return []

    def health_check(self) -> bool:
        """Check if the LLM provider is available."""
        try:
            if self.config.provider == Provider.OLLAMA:
                resp = self.client.get(f"{self.config.base_url}/api/tags", timeout=5)
                return resp.status_code == 200
            else:
                self.client.models.list()
                return True
        except Exception:
            return False
