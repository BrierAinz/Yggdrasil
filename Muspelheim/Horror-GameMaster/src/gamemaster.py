"""
GameMaster — Main orchestrator for the Horror GameMaster engine.

Connects all modules: Pattern Analyzer, Procedural Generator,
Tension Manager, LLM Engine, Context Manager, and NPC Intelligence.

Horror GameMaster — BrierStudios
"""

from __future__ import annotations

import time
from typing import Optional

from pydantic import BaseModel, Field

from pattern_analyzer import PatternAnalyzer, ExtendedAction, FearDimension
from procedural_generator import ProceduralGenerator, SceneType, EventType, EntityBehavior
from tension_manager import TensionManager, DecisionType
from llm_engine import LLMEngine, LLMConfig, GenerationContext, NarratorVoice, Provider
from context_manager import ContextManager, ThreadType
from npc_intelligence import NPCIntelligence, NPCRole, NPCBehavior


# ── Data Models ──────────────────────────────────────────────────────


class GameConfig(BaseModel):
    """Configuration for a GameMaster session."""
    session_id: str = "default"
    llm_config: Optional[LLMConfig] = None
    pacing: float = 0.5  # 0 = slow burn, 1 = relentless
    narrator_voice: NarratorVoice = NarratorVoice.DETACHED
    fear_type_focus: str = "psychological"  # Primary fear type
    enable_npc: bool = True
    enable_doppelganger: bool = True
    max_turns: int = 100
    auto_foreshadow: bool = True


class GameState(BaseModel):
    """Current state of the game."""
    turn: int = 0
    scene: str = ""
    location: str = ""
    narrative: str = ""
    choices: list[str] = Field(default_factory=list)
    tension: float = 0.0
    escalation_level: int = 1
    active_entities: list[str] = Field(default_factory=list)
    npc_present: str = ""
    game_over: bool = False
    ending: str = ""


# ── GameMaster ───────────────────────────────────────────────────────


class GameMaster:
    """
    Main orchestrator for the Horror GameMaster engine.

    Ties together all modules to create a cohesive horror experience.

    Usage:
        gm = GameMaster(GameConfig(session_id="test"))
        state = gm.start()
        state = gm.process_action("I open the door")
    """

    def __init__(self, config: Optional[GameConfig] = None):
        self.config = config or GameConfig()

        # Initialize all modules
        self.analyzer = PatternAnalyzer()
        self.generator = ProceduralGenerator()
        self.tension = TensionManager(pacing=self.config.pacing)
        self.llm = LLMEngine(self.config.llm_config)
        self.context = ContextManager(self.config.session_id)
        self.npc_system = NPCIntelligence()

        # Game state
        self.state = GameState()
        self._narrator_voice = self.config.narrator_voice

    # ── Game Flow ────────────────────────────────────────────────────

    def start(self, scene_type: Optional[SceneType] = None) -> GameState:
        """Start a new game session."""
        # Generate initial scene
        scene = self.generator.generate_scene(scene_type)
        self.state.scene = scene.name
        self.state.location = scene.name

        # Update context
        self.context.update_scene(scene.description, scene.name)

        # Create initial narrative thread
        self.context.create_thread(
            name="Main Mystery",
            description="The central mystery of this place",
            thread_type=ThreadType.MAIN,
        )

        # Auto-plant foreshadowing
        if self.config.auto_foreshadow:
            self.context.auto_seed_foreshadow(self.config.fear_type_focus)
            self.context.auto_seed_foreshadow(self.config.fear_type_focus)

        # Spawn initial NPC if enabled
        if self.config.enable_npc:
            self._spawn_initial_npc()

        # Generate opening narrative
        self.state.narrative = self._generate_narrative(
            f"You find yourself in {scene.name}. {scene.description}",
            scene.sensory.sound,
        )

        # Generate choices
        self.state.choices = self._generate_choices(scene)

        # Record event
        self.tension.on_event("atmosphere", intensity=0.3)
        self.analyzer.record_action(ExtendedAction.MOVE, location=scene.name)

        return self.state

    def process_action(self, player_input: str) -> GameState:
        """Process a player action and generate the next moment."""
        if self.state.game_over:
            return self.state

        self.state.turn += 1

        # Record the action
        action = self._classify_action(player_input)
        self.analyzer.record_action(action, location=self.state.location)
        self.context.record_action(player_input)

        # Get tension decision
        decision = self.tension.decide()

        # Process based on decision
        if decision.decision == DecisionType.SCARE:
            self._deliver_scare()
        elif decision.decision == DecisionType.ESCALATE:
            self._escalate()
        elif decision.decision == DecisionType.FALSE_SECURITY:
            self._false_security()
        elif decision.decision == DecisionType.DE_ESCALATE:
            self._de_escalate()
        else:
            self._maintain()

        # Check for foreshadowing payoff
        self._check_foreshadowing()

        # Check for NPC interaction
        npc_dialogue = self._check_npc_interaction(player_input)

        # Check for doppelganger
        doppelganger_event = self._check_doppelganger()

        # Generate narrative
        context_text = self.context.build_context_prompt()
        self.state.narrative = self._generate_narrative(
            player_input,
            context_text,
            npc_dialogue,
            doppelganger_event,
        )

        # Generate choices
        scene = self.generator.generate_scene(SceneType(self.state.location.lower().replace(" ", "_")))
        self.state.choices = self._generate_choices(scene)

        # Update state
        self.state.tension = self.tension.tension
        self.state.escalation_level = self.tension.escalation_level

        # Auto-foreshadow if enabled
        if self.config.auto_foreshadow and self.state.turn % 3 == 0:
            self.context.auto_seed_foreshadow(self.config.fear_type_focus)

        # Check for game over
        self._check_game_over()

        return self.state

    # ── Scare Delivery ───────────────────────────────────────────────

    def _deliver_scare(self) -> None:
        """Deliver a scare event."""
        # Pick fear type from analyzer's recommendation
        prediction = self.analyzer.predict_next()
        fear_type = prediction.optimal_fear_type or FearDimension.PSYCHOLOGICAL

        # Generate scare event
        event = self.generator.generate_event(
            EventType.JUMPSCARE,
            intensity=prediction.optimal_intensity,
            fear_type=fear_type.value,
        )

        # Update tension
        self.tension.on_event("scare", intensity=prediction.optimal_intensity)

        # Record in context
        self.context.record_action(f"SURVIVED SCARE: {event.description}")
        self.context.auto_add_callback(f"the scare: {event.description}")

        # Record fear response
        self.analyzer.record_fear_response(fear_type, prediction.optimal_intensity, event.description)

    def _escalate(self) -> None:
        """Escalate tension."""
        event = self.generator.generate_event(
            EventType.ESCALATION,
            intensity=0.5,
            fear_type=self.config.fear_type_focus,
        )
        self.tension.on_event("tension", intensity=0.4)

    def _false_security(self) -> None:
        """Create a false sense of security."""
        self.tension.trigger_false_security()
        self.tension.on_event("safe", intensity=0.3)

    def _de_escalate(self) -> None:
        """De-escalate tension."""
        self.tension.on_event("atmosphere", intensity=0.2)

    def _maintain(self) -> None:
        """Maintain current tension."""
        self.tension.on_event("atmosphere", intensity=0.3)

    # ── Foreshadowing ────────────────────────────────────────────────

    def _check_foreshadowing(self) -> None:
        """Check for foreshadowing that's ready to pay off."""
        ready = self.context.get_ready_foreshadows()
        if ready:
            seed = ready[0]  # Pay off the oldest one
            payoff = self.context.deliver_foreshadow(seed)
            self.context.record_revelation(payoff)
            self.tension.on_event("revelation", intensity=0.6)

    # ── NPC Interaction ──────────────────────────────────────────────

    def _spawn_initial_npc(self) -> None:
        """Spawn an initial NPC for the session."""
        import random
        npc_configs = [
            ("A stranger", NPCRole.SUSPECT, "A person who should not be here", NPCBehavior.EVASIVE),
            ("A survivor", NPCRole.ALLY, "Someone who has been here longer than you", NPCBehavior.HELPFUL),
            ("A child", NPCRole.VICTIM, "A lost child who needs help", NPCBehavior.HELPFUL),
            ("A guard", NPCRole.GUARDIAN, "Someone who claims to protect this place", NPCBehavior.MENACING),
        ]
        name, role, desc, behavior = random.choice(npc_configs)
        npc = self.npc_system.create_npc(name, role, desc)
        npc.behavior = behavior

    def _check_npc_interaction(self, player_input: str) -> str:
        """Check if the player is interacting with an NPC."""
        npcs = self.npc_system.get_all_npcs()
        if not npcs:
            return ""

        # Check if player mentions an NPC
        for npc in npcs:
            if npc.name.lower() in player_input.lower() or npc.alive:
                dialogue = self.npc_system.generate_dialogue(npc, player_input)
                self.npc_system.update_trust(npc, player_input)
                return dialogue

        return ""

    def _check_doppelganger(self) -> str:
        """Check for doppelganger events."""
        if not self.config.enable_doppelganger:
            return ""

        if not self.npc_system.doppelganger:
            # Spawn doppelganger after turn 5
            if self.state.turn >= 5:
                self.npc_system.spawn_doppelganger()
                return "You see someone at the edge of your vision. They look like you."

        if self.npc_system.doppelganger:
            # Advance every 3 turns
            if self.state.turn % 3 == 0:
                desc = self.npc_system.advance_doppelganger()
                return self.npc_system.generate_doppelganger_encounter()

        return ""

    # ── Narrative Generation ─────────────────────────────────────────

    def _generate_narrative(
        self,
        player_action: str,
        context: str = "",
        npc_dialogue: str = "",
        doppelganger_event: str = "",
    ) -> str:
        """Generate narrative using the LLM."""
        # Build generation context
        prediction = self.analyzer.predict_next()
        fingerprint = self.analyzer.get_fingerprint()

        gen_context = GenerationContext(
            scene_description=self.state.scene,
            player_action=player_action,
            fear_profile={d.value: fingerprint.get(d) for d in FearDimension},
            tension_level=self.tension.tension,
            escalation_level=self.tension.escalation_level,
            active_entities=self.state.active_entities,
            recent_events=self.context.session.action_history[-5:],
            foreshadowing=[s.description for s in self.context.get_active_foreshadows()],
            callbacks=[c.reference_text for c in self.context.get_callbacks()],
            narrative_act=self.generator.narrative.current_act.value,
            narrator_voice=self._narrator_voice,
        )

        # Add NPC dialogue to context
        if npc_dialogue:
            gen_context.recent_events.append(f"NPC SAYS: {npc_dialogue}")

        # Add doppelganger event
        if doppelganger_event:
            gen_context.recent_events.append(f"DOPPELGANGER: {doppelganger_event}")

        # Generate with LLM
        try:
            narrative = self.llm.generate_full(
                gen_context,
                fear_type=self.config.fear_type_focus,
            )
        except Exception:
            # Fallback to template-based narrative
            narrative = self._fallback_narrative(player_action)

        return narrative

    def _fallback_narrative(self, player_action: str) -> str:
        """Fallback narrative when LLM is unavailable."""
        templates = [
            f"You {player_action.lower()}. The air changes. Something is different. Something is watching.",
            f"As you {player_action.lower()}, the shadows deepen. The temperature drops. You are not alone.",
            f"The action echoes. {player_action}. The sound comes back wrong. Too loud. Too long. Not just yours.",
        ]
        import random
        return random.choice(templates)

    # ── Choice Generation ────────────────────────────────────────────

    def _generate_choices(self, scene) -> list[str]:
        """Generate player choices based on current state."""
        prediction = self.analyzer.predict_next()

        base_choices = [
            "Move forward cautiously",
            "Examine your surroundings",
            "Listen for sounds",
        ]

        # Add fear-specific choices
        if self.analyzer.get_bravery_index().value in ("frozen", "panicking"):
            base_choices.append("Try to calm down")

        if self.tension.tension > 0.6:
            base_choices.append("Look for a safe place")

        if self.state.active_entities:
            base_choices.append("Confront what you see")

        # Add scene-specific choices
        if hasattr(scene, 'available_exits') and scene.available_exits:
            for exit in scene.available_exits[:2]:
                base_choices.append(f"Go to {exit.replace('_', ' ')}")

        return base_choices[:4]  # Max 4 choices

    # ── Game Over ────────────────────────────────────────────────────

    def _check_game_over(self) -> None:
        """Check if the game should end."""
        if self.state.turn >= self.config.max_turns:
            self.state.game_over = True
            self.state.ending = self.generator.generate_ending()

        # Check if player is in permanent panic
        if self.analyzer.get_bravery_index().value == "frozen":
            if self.state.turn > 10:
                self.state.game_over = True
                self.state.ending = "You freeze. The darkness closes in. You do not move. You cannot move. The building accepts your stillness as surrender."

    # ── Action Classification ────────────────────────────────────────

    def _classify_action(self, player_input: str) -> ExtendedAction:
        """Classify a player's text input into an action type."""
        lower = player_input.lower()

        action_keywords = {
            ExtendedAction.MOVE: ["go", "walk", "move", "enter", "proceed", "head", "approach"],
            ExtendedAction.EXAMINE: ["look", "examine", "inspect", "check", "study", "observe"],
            ExtendedAction.INTERACT: ["open", "take", "grab", "use", "push", "pull", "touch"],
            ExtendedAction.HIDE: ["hide", "duck", "crouch", "conceal", "shelter"],
            ExtendedAction.FLEE: ["run", "flee", "escape", "retreat", "sprint", "bolt"],
            ExtendedAction.LISTEN: ["listen", "hear", "sound", "noise"],
            ExtendedAction.READ: ["read", "note", "journal", "sign", "letter"],
            ExtendedAction.TALK: ["talk", "speak", "say", "ask", "call", "shout"],
            ExtendedAction.WAIT: ["wait", "stay", "remain", "pause"],
            ExtendedAction.PANIC: ["panic", "scream", "cry", "tremble", "shake"],
        }

        for action, keywords in action_keywords.items():
            if any(kw in lower for kw in keywords):
                return action

        return ExtendedAction.MOVE  # Default

    # ── Utilities ────────────────────────────────────────────────────

    def get_full_state(self) -> dict:
        """Get the complete game state including all modules."""
        return {
            "game": self.state.model_dump(),
            "tension": self.tension.get_state_summary(),
            "analyzer": self.analyzer.get_session_stats(),
            "context": self.context.get_summary(),
            "npcs": self.npc_system.get_summary(),
        }
