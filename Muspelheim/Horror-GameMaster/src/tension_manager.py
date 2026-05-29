"""
Tension Manager — Dynamic tension curves, cooldowns, false security,
escalation ladder, and pacing engine for the Horror GameMaster.

Horror GameMaster — BrierStudios
"""

from __future__ import annotations

import time
from enum import StrEnum

from pydantic import BaseModel, Field


# ── Enums ────────────────────────────────────────────────────────────


class TensionState(StrEnum):
    CALM = "calm"  # 0.0 - 0.2
    UNEASY = "uneasy"  # 0.2 - 0.4
    TENSE = "tense"  # 0.4 - 0.6
    TERRIFYING = "terrifying"  # 0.6 - 0.8
    PEAK = "peak"  # 0.8 - 1.0
    AFTERMATH = "aftermath"  # Post-scare cooldown


class CooldownState(StrEnum):
    INACTIVE = "inactive"
    ACTIVE = "active"
    FADING = "fading"
    COMPLETE = "complete"


class DecisionType(StrEnum):
    ESCALATE = "escalate"  # Raise tension
    MAINTAIN = "maintain"  # Keep current level
    DE_ESCALATE = "de_escalate"  # Give player a break
    FALSE_SECURITY = "false_security"  # Pretend to calm down
    SCARE = "scare"  # Deliver the scare


# ── Data Models ──────────────────────────────────────────────────────


class Cooldown(BaseModel):
    """Cooldown state after a scare."""

    state: CooldownState = CooldownState.INACTIVE
    start_time: float = 0.0
    duration: float = 0.0
    intensity: float = 0.0

    @property
    def remaining(self) -> float:
        if self.state == CooldownState.INACTIVE:
            return 0.0
        elapsed = time.time() - self.start_time
        return max(0.0, self.duration - elapsed)

    @property
    def progress(self) -> float:
        if self.state == CooldownState.INACTIVE:
            return 1.0
        elapsed = time.time() - self.start_time
        return min(1.0, elapsed / max(0.001, self.duration))


class FalseSecurityPhase(BaseModel):
    """A false security phase."""

    active: bool = False
    start_time: float = 0.0
    duration: float = 0.0
    intensity_bonus: float = 0.3  # Scare effectiveness multiplier

    @property
    def elapsed(self) -> float:
        if not self.active:
            return 0.0
        return time.time() - self.start_time

    @property
    def is_expired(self) -> bool:
        return self.active and self.elapsed >= self.duration


class EscalationLevel(BaseModel):
    """A level on the escalation ladder."""

    level: int = Field(ge=1, le=10)
    name: str
    description: str
    min_events: int = 3
    tension_threshold: float = 0.0
    available_events: list[str] = []
    max_intensity: float = 1.0


class PacingMetrics(BaseModel):
    """Metrics for pacing calculations."""

    session_start: float = Field(default_factory=time.time)
    total_events: int = 0
    scare_events: int = 0
    atmosphere_events: int = 0
    tension_events: int = 0
    last_scare_time: float = 0.0
    scare_window: list[float] = []  # Timestamps of recent scares

    @property
    def session_duration(self) -> float:
        return time.time() - self.session_start

    @property
    def scare_rate(self) -> float:
        """Scares per minute in the last 10 minutes."""
        if not self.scare_window:
            return 0.0
        cutoff = time.time() - 600  # 10 minutes
        recent = [t for t in self.scare_window if t > cutoff]
        return len(recent) / 10.0  # Per minute

    @property
    def atmosphere_ratio(self) -> float:
        """Ratio of atmosphere events to total events."""
        if self.total_events == 0:
            return 1.0
        return self.atmosphere_events / self.total_events


class TensionDecision(BaseModel):
    """A decision from the tension manager."""

    decision: DecisionType
    tension_target: float = 0.0
    recommended_intensity: float = 0.0
    recommended_event_type: str = ""
    timing_delay: float = 0.0  # Seconds to wait before acting
    reasoning: str = ""


# ── Tension Manager ──────────────────────────────────────────────────


class TensionManager:
    """
    Manages the tension curve of horror sessions.

    Controls pacing, cooldowns, false security, escalation,
    and makes decisions about when and how to scare the player.

    Usage:
        tm = TensionManager()
        tm.on_event("scare", intensity=0.8)
        decision = tm.decide()
    """

    def __init__(self, pacing: float = 0.5):
        self.tension: float = 0.1  # Start slightly above calm
        self.state: TensionState = TensionState.CALM
        self.cooldown = Cooldown()
        self.false_security = FalseSecurityPhase()
        self.escalation_level: int = 1
        self.pacing = PacingMetrics()
        self._pacing_speed = pacing  # 0 = slow burn, 1 = relentless
        self._events_at_level: int = 0
        self._stress_score: float = 0.0

        # Build escalation ladder
        self._escalation_ladder = self._build_escalation_ladder()

        # State transition thresholds
        self._state_thresholds = {
            TensionState.CALM: (0.0, 0.2),
            TensionState.UNEASY: (0.2, 0.4),
            TensionState.TENSE: (0.4, 0.6),
            TensionState.TERRIFYING: (0.6, 0.8),
            TensionState.PEAK: (0.8, 1.0),
        }

    # ── State Management ─────────────────────────────────────────────

    def _update_state(self) -> None:
        """Update the tension state based on current tension."""
        if self.cooldown.state in (CooldownState.ACTIVE, CooldownState.FADING):
            self.state = TensionState.AFTERMATH
            return

        for state, (low, high) in self._state_thresholds.items():
            if low <= self.tension < high:
                self.state = state
                return

        if self.tension >= 1.0:
            self.state = TensionState.PEAK

    def _clamp_tension(self) -> None:
        """Clamp tension to valid range."""
        self.tension = max(0.0, min(1.0, self.tension))

    # ── Event Handling ───────────────────────────────────────────────

    def on_event(self, event_type: str, intensity: float = 0.5, fear_type: str = "") -> None:
        """
        Process an event and update tension accordingly.

        event_type: "scare", "atmosphere", "tension", "revelation", etc.
        intensity: 0.0 to 1.0
        """
        self.pacing.total_events += 1

        # Check cooldown
        if self.cooldown.state == CooldownState.ACTIVE:
            if event_type == "scare":
                return  # Block scares during cooldown

        # Apply false security bonus
        if self.false_security.active and event_type == "scare":
            intensity += self.false_security.intensity_bonus
            intensity = min(1.0, intensity)
            self.false_security.active = False

        # Update tension based on event type
        if event_type == "scare":
            self._handle_scare(intensity)
        elif event_type == "atmosphere":
            self._handle_atmosphere(intensity)
        elif event_type == "tension":
            self._handle_tension(intensity)
        elif event_type == "revelation":
            self._handle_revelation(intensity)
        elif event_type == "safe":
            self._handle_safe(intensity)

        # Natural tension decay
        self._apply_decay()

        # Update stress score
        self._update_stress(intensity)

        # Check escalation
        self._check_escalation()

        self._clamp_tension()
        self._update_state()

    def _handle_scare(self, intensity: float) -> None:
        """Handle a scare event."""
        self.tension += intensity * 0.5
        self.pacing.scare_events += 1
        self.pacing.last_scare_time = time.time()
        self.pacing.scare_window.append(time.time())

        # Trigger cooldown
        cooldown_duration = 30 + intensity * 60  # 30-90 seconds
        self.cooldown = Cooldown(
            state=CooldownState.ACTIVE,
            start_time=time.time(),
            duration=cooldown_duration,
            intensity=intensity,
        )

    def _handle_atmosphere(self, intensity: float) -> None:
        """Handle an atmosphere event."""
        self.tension += intensity * 0.1
        self.pacing.atmosphere_events += 1

    def _handle_tension(self, intensity: float) -> None:
        """Handle a tension-building event."""
        self.tension += intensity * 0.2
        self.pacing.tension_events += 1

    def _handle_revelation(self, intensity: float) -> None:
        """Handle a revelation event."""
        self.tension += intensity * 0.3

    def _handle_safe(self, intensity: float) -> None:
        """Handle a safe/comfort event."""
        self.tension -= intensity * 0.15

    def _apply_decay(self) -> None:
        """Apply natural tension decay over time."""
        if self.state == TensionState.AFTERMATH:
            self.tension -= 0.02  # Faster decay during aftermath
        elif self.state == TensionState.CALM:
            pass  # No decay at calm
        else:
            self.tension -= 0.005  # Slow natural decay

    def _update_stress(self, intensity: float) -> None:
        """Update the player's stress score."""
        if intensity > 0.7:
            self._stress_score += 0.2
        elif intensity < 0.3:
            self._stress_score -= 0.1

        self._stress_score = max(0.0, min(1.0, self._stress_score))

    # ── Cooldown ─────────────────────────────────────────────────────

    def update_cooldown(self) -> None:
        """Update cooldown state."""
        if self.cooldown.state == CooldownState.INACTIVE:
            return

        progress = self.cooldown.progress
        if progress >= 1.0:
            self.cooldown.state = CooldownState.COMPLETE
        elif progress >= 0.7:
            self.cooldown.state = CooldownState.FADING
        # else stays ACTIVE

    # ── False Security ───────────────────────────────────────────────

    def trigger_false_security(self, duration: float = 120.0) -> None:
        """Trigger a false security phase."""
        self.false_security = FalseSecurityPhase(
            active=True,
            start_time=time.time(),
            duration=duration,
        )
        # Tension drops to simulate safety
        self.tension *= 0.6

    def update_false_security(self) -> None:
        """Check if false security has expired."""
        if self.false_security.is_expired:
            self.false_security.active = False

    # ── Escalation Ladder ────────────────────────────────────────────

    def _build_escalation_ladder(self) -> list[EscalationLevel]:
        """Build the 10-level escalation ladder."""
        return [
            EscalationLevel(
                level=1,
                name="Whispers",
                description="Subtle hints that something is wrong",
                min_events=2,
                tension_threshold=0.0,
                available_events=["environmental", "sound"],
                max_intensity=0.3,
            ),
            EscalationLevel(
                level=2,
                name="Shadows",
                description="Things seen in peripheral vision",
                min_events=3,
                tension_threshold=0.1,
                available_events=["environmental", "sound", "foreshadowing"],
                max_intensity=0.4,
            ),
            EscalationLevel(
                level=3,
                name="Unease",
                description="A growing sense of wrongness",
                min_events=3,
                tension_threshold=0.2,
                available_events=["foreshadowing", "entity_sighting", "sound"],
                max_intensity=0.5,
            ),
            EscalationLevel(
                level=4,
                name="Pursuit",
                description="Something is following",
                min_events=3,
                tension_threshold=0.3,
                available_events=["entity_sighting", "escalation", "sound"],
                max_intensity=0.6,
            ),
            EscalationLevel(
                level=5,
                name="Confrontation",
                description="Direct encounters",
                min_events=4,
                tension_threshold=0.4,
                available_events=["entity_sighting", "escalation", "jumpscare"],
                max_intensity=0.7,
            ),
            EscalationLevel(
                level=6,
                name="Assault",
                description="Active threat",
                min_events=3,
                tension_threshold=0.5,
                available_events=["jumpscare", "escalation", "revelation"],
                max_intensity=0.8,
            ),
            EscalationLevel(
                level=7,
                name="Revelation",
                description="The truth is revealed",
                min_events=3,
                tension_threshold=0.6,
                available_events=["revelation", "jumpscare", "escalation"],
                max_intensity=0.9,
            ),
            EscalationLevel(
                level=8,
                name="Collapse",
                description="Reality breaks down",
                min_events=2,
                tension_threshold=0.7,
                available_events=["revelation", "jumpscare", "escalation"],
                max_intensity=1.0,
            ),
            EscalationLevel(
                level=9,
                name="Abyss",
                description="The deepest horror",
                min_events=2,
                tension_threshold=0.8,
                available_events=["jumpscare", "revelation"],
                max_intensity=1.0,
            ),
            EscalationLevel(
                level=10,
                name="Transcendence",
                description="Beyond horror",
                min_events=1,
                tension_threshold=0.9,
                available_events=["revelation"],
                max_intensity=1.0,
            ),
        ]

    def _check_escalation(self) -> None:
        """Check if we should escalate or de-escalate."""
        self._events_at_level += 1
        current = self._escalation_ladder[self.escalation_level - 1]

        # Escalate if enough events and tension is above threshold
        if (
            self._events_at_level >= current.min_events
            and self.tension >= current.tension_threshold
            and self.escalation_level < 10
            and self.cooldown.state == CooldownState.INACTIVE
        ):
            self.escalation_level += 1
            self._events_at_level = 0

        # De-escalate if player is too stressed
        if self._stress_score > 0.8 and self.escalation_level > 1:
            self.escalation_level -= 1
            self._stress_score *= 0.5  # Reduce stress after de-escalation

    def get_escalation_level(self) -> EscalationLevel:
        """Get the current escalation level."""
        return self._escalation_ladder[self.escalation_level - 1]

    # ── Decision Engine ──────────────────────────────────────────────

    def decide(self) -> TensionDecision:
        """
        Make a decision about what to do next.

        Returns a TensionDecision with the recommended action.
        """
        self.update_cooldown()
        self.update_false_security()

        # During cooldown: maintain or de-escalate
        if self.cooldown.state == CooldownState.ACTIVE:
            return TensionDecision(
                decision=DecisionType.MAINTAIN,
                tension_target=self.tension,
                recommended_intensity=0.1,
                recommended_event_type="atmosphere",
                timing_delay=self.cooldown.remaining,
                reasoning="Cooldown active — maintaining with atmosphere",
            )

        # During fading cooldown: gentle tension building
        if self.cooldown.state == CooldownState.FADING:
            return TensionDecision(
                decision=DecisionType.ESCALATE,
                tension_target=self.tension + 0.1,
                recommended_intensity=0.3,
                recommended_event_type="tension",
                timing_delay=5.0,
                reasoning="Cooldown fading — building tension slowly",
            )

        # Check pacing — too many scares?
        if self.pacing.scare_rate > 2.0:  # More than 2 scares per minute
            return TensionDecision(
                decision=DecisionType.DE_ESCALATE,
                tension_target=max(0.2, self.tension - 0.2),
                recommended_intensity=0.2,
                recommended_event_type="atmosphere",
                timing_delay=30.0,
                reasoning="Scare rate too high — de-escalating for pacing",
            )

        # Check atmosphere ratio
        if self.pacing.atmosphere_ratio < 0.5 and self.pacing.total_events > 5:
            return TensionDecision(
                decision=DecisionType.MAINTAIN,
                tension_target=self.tension,
                recommended_intensity=0.3,
                recommended_event_type="atmosphere",
                timing_delay=10.0,
                reasoning="Not enough atmosphere — adding atmospheric events",
            )

        # False security opportunity
        if (
            self.tension > 0.4
            and not self.false_security.active
            and self.pacing.total_events > 10
            and self.pacing.total_events % 8 == 0
        ):
            self.trigger_false_security()
            return TensionDecision(
                decision=DecisionType.FALSE_SECURITY,
                tension_target=self.tension * 0.6,
                recommended_intensity=0.1,
                recommended_event_type="safe",
                timing_delay=60.0,
                reasoning="Triggering false security — will strike harder later",
            )

        # Peak tension — deliver the scare
        if self.tension >= 0.7 and self.escalation_level >= 5:
            return TensionDecision(
                decision=DecisionType.SCARE,
                tension_target=min(1.0, self.tension + 0.3),
                recommended_intensity=min(1.0, self.get_escalation_level().max_intensity),
                recommended_event_type="scare",
                timing_delay=0.0,
                reasoning=f"High tension ({self.tension:.1f}) + escalation level {self.escalation_level} — SCARE",
            )

        # Low tension — escalate
        if self.tension < 0.3:
            return TensionDecision(
                decision=DecisionType.ESCALATE,
                tension_target=self.tension + 0.15,
                recommended_intensity=0.4,
                recommended_event_type="tension",
                timing_delay=5.0,
                reasoning=f"Low tension ({self.tension:.1f}) — escalating",
            )

        # Medium tension — maintain with variety
        return TensionDecision(
            decision=DecisionType.MAINTAIN,
            tension_target=self.tension,
            recommended_intensity=0.5,
            recommended_event_type="tension",
            timing_delay=15.0,
            reasoning=f"Medium tension ({self.tension:.1f}) — maintaining",
        )

    # ── Utilities ────────────────────────────────────────────────────

    def get_state_summary(self) -> dict:
        """Get a comprehensive state summary."""
        return {
            "tension": round(self.tension, 3),
            "state": self.state.value,
            "cooldown": {
                "state": self.cooldown.state.value,
                "remaining": round(self.cooldown.remaining, 1),
            },
            "false_security": {
                "active": self.false_security.active,
                "elapsed": round(self.false_security.elapsed, 1),
            },
            "escalation_level": self.escalation_level,
            "escalation_name": self.get_escalation_level().name,
            "stress_score": round(self._stress_score, 3),
            "pacing": {
                "total_events": self.pacing.total_events,
                "scare_rate": round(self.pacing.scare_rate, 2),
                "atmosphere_ratio": round(self.pacing.atmosphere_ratio, 2),
                "session_duration": round(self.pacing.session_duration, 1),
            },
        }

    def reset(self) -> None:
        """Reset the tension manager for a new session."""
        self.tension = 0.1
        self.state = TensionState.CALM
        self.cooldown = Cooldown()
        self.false_security = FalseSecurityPhase()
        self.escalation_level = 1
        self.pacing = PacingMetrics()
        self._events_at_level = 0
        self._stress_score = 0.0
