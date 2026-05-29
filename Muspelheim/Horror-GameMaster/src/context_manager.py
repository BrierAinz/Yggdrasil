"""
Context Manager — Maintains session context, foreshadowing,
callback system, and red thread (connected narrative threads).

Horror GameMaster — BrierStudios
"""

from __future__ import annotations

import time
from enum import StrEnum

from pydantic import BaseModel, Field


# ── Enums ────────────────────────────────────────────────────────────


class ThreadType(StrEnum):
    """Types of narrative threads."""

    MAIN = "main"  # Primary narrative arc
    SUBPLOT = "subplot"  # Secondary narrative
    ENTITY = "entity"  # Entity-specific thread
    PERSONAL = "personal"  # Player-specific thread
    ENVIRONMENTAL = "environmental"  # Location-based thread


class ForeshadowState(StrEnum):
    PLANTED = "planted"  # Foreshadowing planted, not yet delivered
    ECHOING = "echoing"  # Being referenced in current events
    DELIVERED = "delivered"  # The foreshadowed event happened
    EXPIRED = "expired"  # Too late, context lost


# ── Data Models ──────────────────────────────────────────────────────


class NarrativeThread(BaseModel):
    """A connected narrative thread (red thread)."""

    thread_id: str
    thread_type: ThreadType
    name: str
    description: str
    events: list[str] = Field(default_factory=list)
    active: bool = True
    resolved: bool = False
    created_at: float = Field(default_factory=time.time)
    last_event_at: float = Field(default_factory=time.time)
    resolution_hint: str = ""

    def add_event(self, event: str) -> None:
        self.events.append(event)
        self.last_event_at = time.time()

    @property
    def age(self) -> float:
        return time.time() - self.created_at

    @property
    def staleness(self) -> float:
        """How long since last event (seconds)."""
        return time.time() - self.last_event_at


class ForeshadowSeed(BaseModel):
    """A planted piece of foreshadowing."""

    seed_id: str
    description: str
    payoff_event: str  # What will happen when it pays off
    fear_type: str = ""
    state: ForeshadowState = ForeshadowState.PLANTED
    planted_at: float = Field(default_factory=time.time)
    deliver_after: int = 2  # Minimum events before delivery
    events_since_plant: int = 0
    max_age: int = 10  # Max events before it expires

    @property
    def is_ready(self) -> bool:
        return (
            self.state == ForeshadowState.PLANTED and self.events_since_plant >= self.deliver_after
        )

    @property
    def is_expired(self) -> bool:
        return self.events_since_plant > self.max_age


class Callback(BaseModel):
    """A reference to a past event."""

    callback_id: str
    original_event: str
    reference_text: str  # How to reference it in narration
    emotional_weight: float = 0.5  # How impactful the callback is
    times_used: int = 0
    max_uses: int = 3
    created_at: float = Field(default_factory=time.time)

    @property
    def is_exhausted(self) -> bool:
        return self.times_used >= self.max_uses


class SessionContext(BaseModel):
    """Complete context for a game session."""

    session_id: str
    started_at: float = Field(default_factory=time.time)
    current_scene: str = ""
    current_location: str = ""
    player_action: str = ""
    turn_count: int = 0
    narrative_threads: list[NarrativeThread] = Field(default_factory=list)
    foreshadow_seeds: list[ForeshadowSeed] = Field(default_factory=list)
    callbacks: list[Callback] = Field(default_factory=list)
    scene_history: list[str] = Field(default_factory=list)
    action_history: list[str] = Field(default_factory=list)
    fear_history: list[dict[str, float]] = Field(default_factory=list)
    entity_encounters: list[str] = Field(default_factory=list)
    revelations: list[str] = Field(default_factory=list)

    @property
    def duration(self) -> float:
        return time.time() - self.started_at


# ── Context Manager ──────────────────────────────────────────────────


class ContextManager:
    """
    Manages narrative context for a Horror GameMaster session.

    Handles:
    - Session state tracking
    - Foreshadowing (plant → echo → deliver)
    - Callback system (reference past events)
    - Red threads (connected narrative arcs)

    Usage:
        ctx = ContextManager(session_id="session_1")
        ctx.plant_foreshadow("A distant bell tolls", "The bell is in the room")
        ctx.add_callback("You found a locked door", "The locked door from before")
        prompt = ctx.build_prompt()
    """

    def __init__(self, session_id: str = "default"):
        self.session = SessionContext(session_id=session_id)
        self._thread_counter = 0
        self._seed_counter = 0
        self._callback_counter = 0

    # ── Session State ────────────────────────────────────────────────

    def update_scene(self, scene: str, location: str = "") -> None:
        """Update the current scene."""
        self.session.current_scene = scene
        if location:
            self.session.current_location = location
        self.session.scene_history.append(scene)
        self.session.turn_count += 1
        self._advance_seeds()

    def record_action(self, action: str) -> None:
        """Record a player action."""
        self.session.player_action = action
        self.session.action_history.append(action)

    def record_fear_state(self, fears: dict[str, float]) -> None:
        """Record the current fear state."""
        self.session.fear_history.append(fears)

    def record_entity_encounter(self, entity: str) -> None:
        """Record an entity encounter."""
        self.session.entity_encounters.append(entity)

    def record_revelation(self, revelation: str) -> None:
        """Record a narrative revelation."""
        self.session.revelations.append(revelation)

    # ── Foreshadowing ────────────────────────────────────────────────

    def plant_foreshadow(
        self,
        description: str,
        payoff_event: str,
        fear_type: str = "",
        deliver_after: int = 2,
    ) -> ForeshadowSeed:
        """Plant a piece of foreshadowing."""
        self._seed_counter += 1
        seed = ForeshadowSeed(
            seed_id=f"seed_{self._seed_counter}",
            description=description,
            payoff_event=payoff_event,
            fear_type=fear_type,
            deliver_after=deliver_after,
        )
        self.session.foreshadow_seeds.append(seed)
        return seed

    def _advance_seeds(self) -> None:
        """Advance all foreshadow seeds by one event."""
        for seed in self.session.foreshadow_seeds:
            if seed.state == ForeshadowState.PLANTED:
                seed.events_since_plant += 1
                if seed.is_expired:
                    seed.state = ForeshadowState.EXPIRED

    def get_ready_foreshadows(self) -> list[ForeshadowSeed]:
        """Get foreshadowing that is ready to pay off."""
        return [s for s in self.session.foreshadow_seeds if s.is_ready]

    def deliver_foreshadow(self, seed: ForeshadowSeed) -> str:
        """Mark a foreshadow as delivered and return its payoff."""
        seed.state = ForeshadowState.DELIVERED
        return seed.payoff_event

    def get_active_foreshadows(self) -> list[ForeshadowSeed]:
        """Get all active (undelivered) foreshadowing."""
        return [s for s in self.session.foreshadow_seeds if s.state == ForeshadowState.PLANTED]

    # ── Callbacks ────────────────────────────────────────────────────

    def add_callback(
        self, original_event: str, reference_text: str, emotional_weight: float = 0.5
    ) -> Callback:
        """Register a past event for future callbacks."""
        self._callback_counter += 1
        cb = Callback(
            callback_id=f"cb_{self._callback_counter}",
            original_event=original_event,
            reference_text=reference_text,
            emotional_weight=emotional_weight,
        )
        self.session.callbacks.append(cb)
        return cb

    def get_callbacks(self, max_count: int = 3) -> list[Callback]:
        """Get the most impactful unused callbacks."""
        available = [c for c in self.session.callbacks if not c.is_exhausted]
        available.sort(key=lambda c: c.emotional_weight, reverse=True)
        return available[:max_count]

    def use_callback(self, callback: Callback) -> str:
        """Use a callback and return its reference text."""
        callback.times_used += 1
        return callback.reference_text

    # ── Narrative Threads ────────────────────────────────────────────

    def create_thread(
        self,
        name: str,
        description: str,
        thread_type: ThreadType = ThreadType.MAIN,
        resolution_hint: str = "",
    ) -> NarrativeThread:
        """Create a new narrative thread."""
        self._thread_counter += 1
        thread = NarrativeThread(
            thread_id=f"thread_{self._thread_counter}",
            thread_type=thread_type,
            name=name,
            description=description,
            resolution_hint=resolution_hint,
        )
        self.session.narrative_threads.append(thread)
        return thread

    def add_to_thread(self, thread: NarrativeThread, event: str) -> None:
        """Add an event to a narrative thread."""
        thread.add_event(event)

    def resolve_thread(self, thread: NarrativeThread) -> None:
        """Mark a thread as resolved."""
        thread.resolved = True
        thread.active = False

    def get_active_threads(self) -> list[NarrativeThread]:
        """Get all active narrative threads."""
        return [t for t in self.session.narrative_threads if t.active and not t.resolved]

    def get_stale_threads(self) -> list[NarrativeThread]:
        """Get threads that haven't had events recently (need attention)."""
        return [t for t in self.get_active_threads() if t.staleness > 300]  # 5 minutes

    # ── Prompt Building ──────────────────────────────────────────────

    def build_context_prompt(self) -> str:
        """Build a context prompt for the LLM."""
        parts = []

        # Current scene
        if self.session.current_scene:
            parts.append(f"CURRENT SCENE: {self.session.current_scene}")

        if self.session.current_location:
            parts.append(f"LOCATION: {self.session.current_location}")

        # Player action
        if self.session.player_action:
            parts.append(f"PLAYER ACTION: {self.session.player_action}")

        # Recent events
        if self.session.scene_history:
            recent = self.session.scene_history[-3:]
            parts.append("RECENT SCENES:\n" + "\n".join(f"- {s}" for s in recent))

        # Foreshadowing ready to pay off
        ready = self.get_ready_foreshadows()
        if ready:
            parts.append(
                "FORESHADOWING READY:\n"
                + "\n".join(f"- {s.description} → {s.payoff_event}" for s in ready)
            )

        # Active foreshadowing
        active = self.get_active_foreshadows()
        if active:
            parts.append(
                "PLANTED FORESHADOWING (use soon):\n"
                + "\n".join(f"- {s.description}" for s in active)
            )

        # Callbacks
        callbacks = self.get_callbacks()
        if callbacks:
            parts.append(
                "CALLBACKS (reference these):\n"
                + "\n".join(f"- {c.reference_text}" for c in callbacks)
            )

        # Active threads
        threads = self.get_active_threads()
        if threads:
            parts.append(
                "ACTIVE NARRATIVE THREADS:\n"
                + "\n".join(
                    f"- [{t.thread_type.value}] {t.name}: {t.description} ({len(t.events)} events)"
                    for t in threads
                )
            )

        # Stale threads
        stale = self.get_stale_threads()
        if stale:
            parts.append(
                "STALE THREADS (need attention):\n" + "\n".join(f"- {t.name}" for t in stale)
            )

        # Entity encounters
        if self.session.entity_encounters:
            recent_entities = self.session.entity_encounters[-3:]
            parts.append("RECENT ENTITIES:\n" + "\n".join(f"- {e}" for e in recent_entities))

        # Revelations
        if self.session.revelations:
            parts.append(
                "REVELATIONS SO FAR:\n" + "\n".join(f"- {r}" for r in self.session.revelations)
            )

        # Turn count
        parts.append(f"TURN: {self.session.turn_count}")

        return "\n\n".join(parts)

    # ── Auto-Generation ──────────────────────────────────────────────

    def auto_seed_foreshadow(self, fear_type: str) -> ForeshadowSeed | None:
        """Automatically plant foreshadowing based on fear type."""
        templates = {
            "psychological": [
                (
                    "A mirror shows your reflection a half-second behind",
                    "Your reflection steps out of the mirror",
                ),
                (
                    "You hear your own voice from another room",
                    "You meet yourself coming the other way",
                ),
                ("The clock skips forward by an hour", "You have no memory of the lost hour"),
            ],
            "darkness": [
                ("A shadow moves in the corner of your eye", "The shadow is standing behind you"),
                ("The lights flicker once", "The lights go out and do not come back"),
                ("You hear breathing from the dark", "Something in the dark breathes your name"),
            ],
            "paranoia": [
                ("You notice a camera in the smoke detector", "Every room has been watching you"),
                (
                    "Your phone shows a call from your own number",
                    "You have been calling yourself for weeks",
                ),
                ("A stranger smiles at you on the street", "The stranger has your face"),
            ],
            "body_horror": [
                ("A mole appears on your hand that was not there", "The mole is moving"),
                (
                    "Your reflection shows a scar you do not have",
                    "The scar appears on your real face",
                ),
                ("You hear a second heartbeat", "The second heartbeat is coming from inside you"),
            ],
        }

        options = templates.get(fear_type, templates["psychological"])
        import random

        desc, payoff = random.choice(options)
        return self.plant_foreshadow(desc, payoff, fear_type)

    def auto_add_callback(self, event: str) -> Callback:
        """Automatically create a callback from a significant event."""
        return self.add_callback(event, f"Remember when {event.lower()}", emotional_weight=0.6)

    # ── Utilities ────────────────────────────────────────────────────

    def get_summary(self) -> dict:
        """Get a summary of the session context."""
        return {
            "session_id": self.session.session_id,
            "turn": self.session.turn_count,
            "duration": round(self.session.duration, 1),
            "current_scene": self.session.current_scene[:80],
            "active_threads": len(self.get_active_threads()),
            "stale_threads": len(self.get_stale_threads()),
            "active_foreshadows": len(self.get_active_foreshadows()),
            "ready_foreshadows": len(self.get_ready_foreshadows()),
            "callbacks": len(self.session.callbacks),
            "entity_encounters": len(self.session.entity_encounters),
            "revelations": len(self.session.revelations),
        }

    def reset(self) -> None:
        """Reset for a new session."""
        self.session = SessionContext(session_id=self.session.session_id)
        self._thread_counter = 0
        self._seed_counter = 0
        self._callback_counter = 0
