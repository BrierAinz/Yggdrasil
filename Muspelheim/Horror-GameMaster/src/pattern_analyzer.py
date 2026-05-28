"""
Pattern Analyzer v2 — Tracks player behavior, builds fear fingerprints,
detects habituation, and predicts optimal scare timing.

Horror GameMaster — BrierStudios
"""

from __future__ import annotations

import time
from collections import defaultdict
from enum import Enum
from typing import Optional

import numpy as np
from pydantic import BaseModel, Field

from memory.player_memory import (
    ActionType,
    EventCategory,
    FearDimension,
    FearFingerprint,
    GameEvent,
    HabituationTracker,
    PlayerFearProfile,
)


# ── Extended Enums ───────────────────────────────────────────────────


class ExtendedAction(str, Enum):
    """Extended action types beyond the base ActionType."""

    MOVE = "move"
    EXAMINE = "examine"
    INTERACT = "interact"
    HIDE = "hide"
    FLEE = "flee"
    USE_ITEM = "use_item"
    TALK = "talk"
    WAIT = "wait"
    PANIC = "panic"
    LISTEN = "listen"
    TOUCH = "touch"
    READ = "read"
    OPEN = "open"
    CLOSE = "close"
    BREAK = "break"
    SEARCH = "search"
    CALL_OUT = "call_out"
    BARRICADE = "barricade"
    PRAY = "pray"
    CRY = "cry"


class ExplorationStyle(str, Enum):
    THOROUGH = "thorough"      # Examines everything, slow
    BALANCED = "balanced"      # Normal pace
    RUSHED = "rushed"          # Moves fast, skips details
    CAUTIOUS = "cautious"      # Hides often, avoids risk
    RECKLESS = "reckless"      # Charges into danger


class BraveryIndex(str, Enum):
    FROZEN = "frozen"          # Cannot act, paralyzed
    PANICKING = "panicking"    # Erratic actions, fleeing
    NERVOUS = "nervous"        # Hesitant but functional
    BRAVE = "brave"            # Steady, deliberate
    FEARLESS = "fearless"      # Seeks out danger


# ── Data Models ──────────────────────────────────────────────────────


class ActionRecord(BaseModel):
    """A single player action with full context."""

    action: ExtendedAction
    timestamp: float = Field(default_factory=time.time)
    location: str = ""
    fear_state: dict[FearDimension, float] = Field(default_factory=dict)
    nearby_events: list[str] = []
    response_time: float = 0.0  # Seconds between event and action
    outcome: str = ""  # What happened as a result


class PatternSignature(BaseModel):
    """A detected behavioral pattern."""

    name: str
    description: str
    confidence: float = Field(ge=0.0, le=1.0)
    occurrences: int = 0
    last_seen: float = 0.0


class FearVelocity(BaseModel):
    """How fast fear changes in each dimension."""

    dimension: FearDimension
    current: float = 0.0
    velocity: float = 0.0  # Positive = increasing, negative = decreasing
    acceleration: float = 0.0  # Rate of change of velocity
    peak: float = 0.0
    baseline: float = 0.5


class PredictionResult(BaseModel):
    """A prediction about player behavior or optimal scare timing."""

    predicted_action: Optional[ExtendedAction] = None
    confidence: float = 0.0
    optimal_fear_type: Optional[FearDimension] = None
    optimal_intensity: float = 0.0
    timing_score: float = 0.0  # 0 = bad time, 1 = perfect time
    reasoning: str = ""


# ── Pattern Analyzer ─────────────────────────────────────────────────


class PatternAnalyzer:
    """
    Analyzes player behavior patterns, builds psychological fingerprints,
    detects habituation, and predicts optimal scare timing.

    Usage:
        analyzer = PatternAnalyzer()
        analyzer.record_action(ExtendedAction.HIDE, location="dark_corridor")
        fingerprint = analyzer.get_fingerprint()
        prediction = analyzer.predict_next()
    """

    def __init__(self):
        self.action_history: list[ActionRecord] = []
        self.fear_velocities: dict[FearDimension, FearVelocity] = {
            d: FearVelocity(dimension=d) for d in FearDimension
        }
        self.detected_patterns: list[PatternSignature] = []
        self.habituation: dict[FearDimension, HabituationTracker] = {
            d: HabituationTracker(fear_type=d) for d in FearDimension
        }
        self._action_counts: dict[ExtendedAction, int] = defaultdict(int)
        self._fear_triggers: dict[FearDimension, list[str]] = defaultdict(list)
        self._session_start: float = time.time()
        self._last_scare_time: float = 0.0
        self._scare_count: int = 0
        self._novelty_scores: dict[FearDimension, float] = {
            d: 1.0 for d in FearDimension
        }

    # ── Recording ────────────────────────────────────────────────────

    def record_action(
        self,
        action: ExtendedAction,
        location: str = "",
        nearby_events: list[str] = None,
        response_time: float = 0.0,
        outcome: str = "",
    ) -> None:
        """Record a player action with context."""
        record = ActionRecord(
            action=action,
            location=location,
            nearby_events=nearby_events or [],
            response_time=response_time,
            outcome=outcome,
        )
        self.action_history.append(record)
        self._action_counts[action] += 1
        self._update_patterns()
        self._update_bravery()

    def record_fear_response(
        self,
        dimension: FearDimension,
        intensity: float,
        trigger: str = "",
    ) -> None:
        """Record a fear response and update velocity tracking."""
        velocity = self.fear_velocities[dimension]
        old_value = velocity.current

        # Update velocity (rate of change)
        dt = max(0.001, time.time() - (self._session_start + len(self.action_history) * 0.1))
        velocity.velocity = (intensity - old_value) / max(dt, 0.001)
        velocity.current = intensity
        velocity.peak = max(velocity.peak, intensity)

        # Update habituation
        self.habituation[dimension].record_exposure(intensity)

        # Update novelty (decreases with repeated exposure)
        self._novelty_scores[dimension] = max(
            0.1, self._novelty_scores[dimension] * 0.9
        )

        # Record trigger
        if trigger:
            self._fear_triggers[dimension].append(trigger)

        # Track scare timing
        if intensity > 0.7:
            self._last_scare_time = time.time()
            self._scare_count += 1

    # ── Fingerprint ──────────────────────────────────────────────────

    def get_fingerprint(self) -> FearFingerprint:
        """Build a FearFingerprint from accumulated data."""
        fp = FearFingerprint()
        for dim in FearDimension:
            v = self.fear_velocities[dim]
            # Blend current value with peak (weighted toward current)
            blended = v.current * 0.7 + v.peak * 0.3
            fp.set(dim, max(0.0, min(1.0, blended)))
        return fp

    def get_fear_velocities(self) -> dict[FearDimension, FearVelocity]:
        """Get current fear velocity for each dimension."""
        return self.fear_velocities.copy()

    # ── Habituation ──────────────────────────────────────────────────

    def get_novelty_scores(self) -> dict[FearDimension, float]:
        """Get novelty scores (1.0 = fresh, 0.0 = fully habituated)."""
        return self._novelty_scores.copy()

    def get_fresh_fears(self) -> list[FearDimension]:
        """Get fears the player has NOT habituated to (novelty > 0.5)."""
        return [d for d, score in self._novelty_scores.items() if score > 0.5]

    def get_stale_fears(self) -> list[FearDimension]:
        """Get fears the player HAS habituated to (novelty < 0.3)."""
        return [d for d, score in self._novelty_scores.items() if score < 0.3]

    def recommend_fear_rotation(self) -> list[FearDimension]:
        """Recommend which fear types to use next, sorted by effectiveness."""
        scores = {}
        for d in FearDimension:
            novelty = self._novelty_scores[d]
            habituation = 1.0 - self.habituation[d].habituation_score
            velocity = max(0, -self.fear_velocities[d].velocity)  # Decreasing fear = good target
            scores[d] = novelty * 0.5 + habituation * 0.3 + velocity * 0.2

        return sorted(scores, key=scores.get, reverse=True)

    # ── Pattern Recognition ──────────────────────────────────────────

    def _update_patterns(self) -> None:
        """Detect behavioral patterns from action history."""
        if len(self.action_history) < 5:
            return

        recent = self.action_history[-20:]

        # Detect hiding pattern
        hide_count = sum(1 for a in recent if a.action == ExtendedAction.HIDE)
        if hide_count > len(recent) * 0.4:
            self._add_pattern("avoidant", "Player hides frequently", 0.8)

        # Detect rushing pattern
        move_count = sum(1 for a in recent if a.action == ExtendedAction.MOVE)
        examine_count = sum(1 for a in recent if a.action == ExtendedAction.EXAMINE)
        if move_count > examine_count * 3:
            self._add_pattern("rusher", "Player moves without examining", 0.7)

        # Detect thorough explorer
        if examine_count > move_count * 1.5:
            self._add_pattern("explorer", "Player examines everything", 0.7)

        # Detect panic pattern
        panic_count = sum(1 for a in recent if a.action in (ExtendedAction.PANIC, ExtendedAction.FLEE))
        if panic_count > len(recent) * 0.3:
            self._add_pattern("panicked", "Player is in panic mode", 0.9)

        # Detect investigative pattern
        listen_read = sum(
            1 for a in recent
            if a.action in (ExtendedAction.LISTEN, ExtendedAction.READ, ExtendedAction.EXAMINE)
        )
        if listen_read > len(recent) * 0.3:
            self._add_pattern("investigator", "Player seeks information", 0.7)

    def _add_pattern(self, name: str, description: str, confidence: float) -> None:
        """Add or update a detected pattern."""
        for p in self.detected_patterns:
            if p.name == name:
                p.occurrences += 1
                p.last_seen = time.time()
                p.confidence = min(1.0, p.confidence + 0.05)
                return
        self.detected_patterns.append(
            PatternSignature(
                name=name,
                description=description,
                confidence=confidence,
                occurrences=1,
                last_seen=time.time(),
            )
        )

    def get_exploration_style(self) -> ExplorationStyle:
        """Determine the player's exploration style."""
        if not self.action_history:
            return ExplorationStyle.BALANCED

        recent = self.action_history[-30:]
        move = sum(1 for a in recent if a.action == ExtendedAction.MOVE)
        examine = sum(1 for a in recent if a.action == ExtendedAction.EXAMINE)
        hide = sum(1 for a in recent if a.action == ExtendedAction.HIDE)
        flee = sum(1 for a in recent if a.action == ExtendedAction.FLEE)
        total = len(recent)

        if hide > total * 0.3:
            return ExplorationStyle.CAUTIOUS
        if flee > total * 0.2:
            return ExplorationStyle.RUSHED
        if examine > move * 1.5:
            return ExplorationStyle.THOROUGH
        if move > examine * 3:
            return ExplorationStyle.RUSHED
        return ExplorationStyle.BALANCED

    def _update_bravery(self) -> None:
        """Update bravery index based on recent behavior."""
        # Bravery is implicit in the fear velocities and action patterns

    def get_bravery_index(self) -> BraveryIndex:
        """Calculate the player's current bravery level."""
        if not self.action_history:
            return BraveryIndex.NERVOUS

        recent = self.action_history[-10:]
        panic = sum(1 for a in recent if a.action in (ExtendedAction.PANIC, ExtendedAction.CRY))
        flee = sum(1 for a in recent if a.action == ExtendedAction.FLEE)
        hide = sum(1 for a in recent if a.action == ExtendedAction.HIDE)
        advance = sum(
            1 for a in recent
            if a.action in (ExtendedAction.MOVE, ExtendedAction.OPEN, ExtendedAction.INTERACT)
        )

        if panic > 3:
            return BraveryIndex.FROZEN
        if panic + flee > len(recent) * 0.5:
            return BraveryIndex.PANICKING
        if hide > len(recent) * 0.4:
            return BraveryIndex.NERVOUS
        if advance > len(recent) * 0.5:
            return BraveryIndex.BRAVE
        if advance > len(recent) * 0.7:
            return BraveryIndex.FEARLESS
        return BraveryIndex.NERVOUS

    # ── Prediction ───────────────────────────────────────────────────

    def predict_next(self) -> PredictionResult:
        """Predict the player's next action and recommend optimal scare timing."""
        if len(self.action_history) < 3:
            return PredictionResult(
                reasoning="Not enough data for prediction",
                timing_score=0.3,
            )

        recent = self.action_history[-10:]

        # Predict action based on patterns
        predicted_action = self._predict_action(recent)

        # Find best fear type to use
        rotation = self.recommend_fear_rotation()
        optimal_fear = rotation[0] if rotation else FearDimension.PSYCHOLOGICAL

        # Calculate timing score
        timing = self._calculate_timing()

        # Determine optimal intensity
        bravery = self.get_bravery_index()
        intensity_map = {
            BraveryIndex.FROZEN: 0.3,      # Low — they're already scared
            BraveryIndex.PANICKING: 0.4,
            BraveryIndex.NERVOUS: 0.6,
            BraveryIndex.BRAVE: 0.8,
            BraveryIndex.FEARLESS: 0.95,    # High — they need a real scare
        }
        optimal_intensity = intensity_map.get(bravery, 0.5)

        return PredictionResult(
            predicted_action=predicted_action,
            confidence=0.6,
            optimal_fear_type=optimal_fear,
            optimal_intensity=optimal_intensity,
            timing_score=timing,
            reasoning=f"Bravery: {bravery.value}, Style: {self.get_exploration_style().value}, "
                      f"Fresh fears: {[d.value for d in self.get_fresh_fears()[:3]]}",
        )

    def _predict_action(self, recent: list[ActionRecord]) -> ExtendedAction:
        """Predict next action based on recent history."""
        # Count action frequencies in recent history
        counts: dict[ExtendedAction, int] = defaultdict(int)
        for a in recent:
            counts[a.action] += 1

        # Weight recent actions more heavily
        if recent:
            last = recent[-1].action
            # After hiding, player usually moves or examines
            if last == ExtendedAction.HIDE:
                return ExtendedAction.MOVE
            # After fleeing, player usually hides or waits
            if last == ExtendedAction.FLEE:
                return ExtendedAction.HIDE
            # After examining, player usually interacts or moves
            if last == ExtendedAction.EXAMINE:
                return ExtendedAction.INTERACT

        # Default: most common action
        if counts:
            return max(counts, key=counts.get)
        return ExtendedAction.MOVE

    def _calculate_timing(self) -> float:
        """Calculate optimal timing for a scare (0=bad, 1=perfect)."""
        if self._last_scare_time == 0:
            return 0.8  # First scare — good timing

        time_since_last = time.time() - self._last_scare_time
        session_duration = time.time() - self._session_start

        # Too soon after last scare
        if time_since_last < 30:
            return 0.1

        # Sweet spot: 1-3 minutes after last scare
        if 60 < time_since_last < 180:
            base = 0.9
        elif 30 < time_since_last < 60:
            base = 0.6
        else:
            base = 0.7  # Long gap — tension may have dissipated

        # Adjust for bravery
        bravery = self.get_bravery_index()
        if bravery in (BraveryIndex.FEARLESS, BraveryIndex.BRAVE):
            base += 0.1  # They can handle more
        elif bravery == BraveryIndex.FROZEN:
            base -= 0.3  # Give them a break

        # Adjust for habituation
        fresh = len(self.get_fresh_fears())
        if fresh > 4:
            base += 0.1  # Many fresh fears available
        elif fresh < 2:
            base -= 0.2  # Running out of fresh scares

        return max(0.0, min(1.0, base))

    # ── Utilities ────────────────────────────────────────────────────

    def get_session_stats(self) -> dict:
        """Get comprehensive session statistics."""
        return {
            "total_actions": len(self.action_history),
            "session_duration": time.time() - self._session_start,
            "action_counts": {a.value: c for a, c in self._action_counts.items()},
            "exploration_style": self.get_exploration_style().value,
            "bravery_index": self.get_bravery_index().value,
            "scare_count": self._scare_count,
            "detected_patterns": [p.name for p in self.detected_patterns],
            "fresh_fears": [d.value for d in self.get_fresh_fears()],
            "stale_fears": [d.value for d in self.get_stale_fears()],
            "recommended_rotation": [d.value for d in self.recommend_fear_rotation()[:3]],
            "fear_velocities": {
                d.value: {"current": v.current, "velocity": v.velocity}
                for d, v in self.fear_velocities.items()
            },
        }
