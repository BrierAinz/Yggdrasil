"""
Player Memory — Fear profiles, habituation tracking, and session persistence.

Uses Pydantic v2 for validation, SQLite for structured metadata,
and integrates with EmbeddingPipeline for semantic retrieval.
"""

from __future__ import annotations

import json
import sqlite3
import time
from enum import StrEnum
from pathlib import Path

import numpy as np
from pydantic import BaseModel, Field


# ── Enums ────────────────────────────────────────────────────────────


class FearDimension(StrEnum):
    """The seven fundamental fear dimensions the engine tracks."""

    DARKNESS = "darkness"
    ISOLATION = "isolation"
    JUMPSCARE = "jumpscare"
    PSYCHOLOGICAL = "psychological"
    BODY_HORROR = "body_horror"
    PARANOIA = "paranoia"
    LOSS_OF_CONTROL = "loss_of_control"


class ActionType(StrEnum):
    """High-level categories of player actions."""

    MOVE = "move"
    EXAMINE = "examine"
    INTERACT = "interact"
    HIDE = "hide"
    FLEE = "flee"
    USE_ITEM = "use_item"
    TALK = "talk"
    WAIT = "wait"
    PANIC = "panic"


class EventCategory(StrEnum):
    """Categories of game events for embedding and retrieval."""

    SCENE_DESCRIPTION = "scene_description"
    NPC_DIALOGUE = "npc_dialogue"
    ENVIRONMENTAL = "environmental"
    FORESHADOWING = "foreshadowing"
    RED_HERRING = "red_herring"
    TENSION_ESCALATION = "tension_escalation"
    FALSE_SECURITY = "false_security"
    JUMPSCARE = "jumpscare"
    REVELATION = "revelation"


# ── Data Models ──────────────────────────────────────────────────────


class FearFingerprint(BaseModel):
    """A player's fear profile across all seven dimensions.

    Values range from 0.0 (no fear) to 1.0 (maximum fear response).
    """

    darkness: float = Field(default=0.5, ge=0.0, le=1.0)
    isolation: float = Field(default=0.5, ge=0.0, le=1.0)
    jumpscare: float = Field(default=0.5, ge=0.0, le=1.0)
    psychological: float = Field(default=0.5, ge=0.0, le=1.0)
    body_horror: float = Field(default=0.5, ge=0.0, le=1.0)
    paranoia: float = Field(default=0.5, ge=0.0, le=1.0)
    loss_of_control: float = Field(default=0.5, ge=0.0, le=1.0)

    def get(self, dimension: FearDimension) -> float:
        return getattr(self, dimension.value)

    def set(self, dimension: FearDimension, value: float) -> None:
        object.__setattr__(self, dimension.value, max(0.0, min(1.0, value)))

    def dominant_fear(self) -> FearDimension:
        """Return the fear dimension with the highest score."""
        scores = {d: self.get(d) for d in FearDimension}
        return max(scores, key=scores.get)

    def top_fears(self, n: int = 3) -> list[tuple[FearDimension, float]]:
        """Return the top-N fear dimensions sorted by score descending."""
        scores = [(d, self.get(d)) for d in FearDimension]
        scores.sort(key=lambda x: x[1], reverse=True)
        return scores[:n]

    def to_vector(self) -> np.ndarray:
        """Convert to a 7-dim numpy vector for similarity computation."""
        return np.array([self.get(d) for d in FearDimension], dtype=np.float32)


class ResponsePattern(BaseModel):
    """How a player responded to a specific type of horror stimulus."""

    fear_type: FearDimension
    stimulus_description: str
    action_taken: ActionType
    intensity: float = Field(ge=0.0, le=1.0)
    timestamp: float = Field(default_factory=time.time)
    session_id: str = ""


class HabituationTracker(BaseModel):
    """Tracks how quickly a player habituates to different fear types.

    When habituation_score approaches 1.0, the player is no longer
    affected by that type of horror and the engine should escalate.
    """

    fear_type: FearDimension
    exposure_count: int = 0
    habituation_score: float = Field(default=0.0, ge=0.0, le=1.0)
    last_exposure: float = Field(default=0.0)
    cooldown_active: bool = False
    cooldown_until: float = 0.0

    def record_exposure(self, intensity: float) -> None:
        """Record an exposure to this fear type and update habituation."""
        self.exposure_count += 1
        self.last_exposure = time.time()

        # Diminishing returns: each exposure increases habituation less
        delta = intensity * (0.5 ** (self.exposure_count - 1))
        self.habituation_score = min(1.0, self.habituation_score + delta)

        # Activate cooldown after high-intensity events
        if intensity > 0.7:
            self.cooldown_active = True
            self.cooldown_until = time.time() + 30.0  # 30s cooldown

    def should_escalate(self) -> bool:
        """True if the player has habituated and we need stronger stimuli."""
        return self.habituation_score > 0.6

    def is_cooling_down(self) -> bool:
        if self.cooldown_active and time.time() > self.cooldown_until:
            self.cooldown_active = False
        return self.cooldown_active

    def reset(self, amount: float = 0.3) -> None:
        """Partially reset habituation (e.g., after a long break)."""
        self.habituation_score = max(0.0, self.habituation_score - amount)


class GameEvent(BaseModel):
    """A single event in the game world — used for embedding and retrieval."""

    event_id: str
    category: EventCategory
    description: str
    fear_types: list[FearDimension] = []
    intensity: float = Field(ge=0.0, le=1.0)
    session_id: str = ""
    timestamp: float = Field(default_factory=time.time)
    player_action: str = ""
    narrative_response: str = ""
    embedding_id: str | None = None


class SessionMemory(BaseModel):
    """Summary of a single game session."""

    session_id: str
    started_at: float = Field(default_factory=time.time)
    ended_at: float | None = None
    events: list[GameEvent] = []
    fear_snapshot: FearFingerprint | None = None
    dominant_fear_at_end: FearDimension | None = None
    event_count: int = 0
    peak_intensity: float = 0.0

    def add_event(self, event: GameEvent) -> None:
        self.events.append(event)
        self.event_count += 1
        self.peak_intensity = max(self.peak_intensity, event.intensity)

    def close(self) -> None:
        self.ended_at = time.time()
        if self.events:
            self.dominant_fear_at_end = max(
                FearDimension,
                key=lambda d: sum(1 for e in self.events if d in e.fear_types),
            )


class MemoryQueryResult(BaseModel):
    """Result from querying the player memory store."""

    events: list[GameEvent]
    relevance_scores: list[float]
    fear_context: FearFingerprint
    habituation_warnings: list[FearDimension] = []
    query_text: str = ""


class PlayerFearProfile(BaseModel):
    """Complete player profile — fear fingerprint + history + habituation."""

    player_id: str
    fingerprint: FearFingerprint = Field(default_factory=FearFingerprint)
    habituation: dict[FearDimension, HabituationTracker] = Field(
        default_factory=lambda: {d: HabituationTracker(fear_type=d) for d in FearDimension}
    )
    response_history: list[ResponsePattern] = []
    sessions: list[SessionMemory] = []
    total_play_time: float = 0.0
    created_at: float = Field(default_factory=time.time)
    updated_at: float = Field(default_factory=time.time)

    def record_response(
        self,
        fear_type: FearDimension,
        stimulus: str,
        action: ActionType,
        intensity: float,
        session_id: str = "",
    ) -> None:
        """Record a player response and update fear profile."""
        pattern = ResponsePattern(
            fear_type=fear_type,
            stimulus_description=stimulus,
            action_taken=action,
            intensity=intensity,
            session_id=session_id,
        )
        self.response_history.append(pattern)

        # Update fingerprint: weighted average moving toward new data
        current = self.fingerprint.get(fear_type)
        weight = 0.3  # How much the new data influences
        new_value = current * (1 - weight) + intensity * weight
        self.fingerprint.set(fear_type, new_value)

        # Update habituation
        self.habituation[fear_type].record_exposure(intensity)
        self.updated_at = time.time()

    def should_escalate(self, fear_type: FearDimension) -> bool:
        return self.habituation[fear_type].should_escalate()

    def get_fresh_fears(self) -> list[FearDimension]:
        """Return fears that the player has NOT habituated to."""
        return [d for d in FearDimension if not self.habituation[d].should_escalate()]

    def get_stale_fears(self) -> list[FearDimension]:
        """Return fears the player has habituated to (needs escalation)."""
        return [d for d in FearDimension if self.habituation[d].should_escalate()]


# ── Store ────────────────────────────────────────────────────────────


class PlayerMemoryStore:
    """Persistent storage for player fear profiles using SQLite.

    Provides save/load for PlayerFearProfile objects and query
    methods for the game engine to retrieve relevant context.
    """

    def __init__(self, db_path: str | Path = "player_memory.db"):
        self.db_path = Path(db_path)
        self._init_db()

    def _init_db(self) -> None:
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                """CREATE TABLE IF NOT EXISTS players (
                    player_id TEXT PRIMARY KEY,
                    profile_json TEXT NOT NULL,
                    updated_at REAL NOT NULL
                )"""
            )
            conn.execute(
                """CREATE TABLE IF NOT EXISTS events (
                    event_id TEXT PRIMARY KEY,
                    player_id TEXT NOT NULL,
                    session_id TEXT,
                    category TEXT,
                    description TEXT,
                    fear_types TEXT,
                    intensity REAL,
                    timestamp REAL,
                    embedding_id TEXT,
                    FOREIGN KEY (player_id) REFERENCES players(player_id)
                )"""
            )
            conn.execute("CREATE INDEX IF NOT EXISTS idx_events_player ON events(player_id)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_events_session ON events(session_id)")
            conn.commit()

    def save_profile(self, profile: PlayerFearProfile) -> None:
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                "INSERT OR REPLACE INTO players (player_id, profile_json, updated_at) VALUES (?, ?, ?)",
                (profile.player_id, profile.model_dump_json(), time.time()),
            )
            conn.commit()

    def load_profile(self, player_id: str) -> PlayerFearProfile | None:
        with sqlite3.connect(self.db_path) as conn:
            row = conn.execute(
                "SELECT profile_json FROM players WHERE player_id = ?",
                (player_id,),
            ).fetchone()
            if row:
                return PlayerFearProfile.model_validate_json(row[0])
        return None

    def get_or_create(self, player_id: str) -> PlayerFearProfile:
        profile = self.load_profile(player_id)
        if profile is None:
            profile = PlayerFearProfile(player_id=player_id)
            self.save_profile(profile)
        return profile

    def save_event(self, player_id: str, event: GameEvent) -> None:
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                """INSERT OR REPLACE INTO events
                (event_id, player_id, session_id, category, description,
                 fear_types, intensity, timestamp, embedding_id)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    event.event_id,
                    player_id,
                    event.session_id,
                    event.category.value,
                    event.description,
                    json.dumps([f.value for f in event.fear_types]),
                    event.intensity,
                    event.timestamp,
                    event.embedding_id,
                ),
            )
            conn.commit()

    def get_recent_events(self, player_id: str, limit: int = 20) -> list[GameEvent]:
        with sqlite3.connect(self.db_path) as conn:
            rows = conn.execute(
                """SELECT event_id, category, description, fear_types,
                          intensity, session_id, timestamp, embedding_id
                   FROM events WHERE player_id = ?
                   ORDER BY timestamp DESC LIMIT ?""",
                (player_id, limit),
            ).fetchall()
        events = []
        for r in rows:
            events.append(
                GameEvent(
                    event_id=r[0],
                    category=EventCategory(r[1]),
                    description=r[2],
                    fear_types=[FearDimension(f) for f in json.loads(r[3])],
                    intensity=r[4],
                    session_id=r[5] or "",
                    timestamp=r[6],
                    player_action="",
                    narrative_response="",
                    embedding_id=r[7],
                )
            )
        return events

    def list_players(self) -> list[str]:
        with sqlite3.connect(self.db_path) as conn:
            rows = conn.execute("SELECT player_id FROM players").fetchall()
            return [r[0] for r in rows]
