"""
NPC Intelligence — Complex NPC behaviors, trust system,
learning NPCs, and doppelganger mechanic.

Horror GameMaster — BrierStudios
"""

from __future__ import annotations

import random
import time
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


# ── Enums ────────────────────────────────────────────────────────────


class NPCRole(str, Enum):
    """NPC role types."""
    ALLY = "ally"                  # Helpful, trustworthy (or is it?)
    SUSPECT = "suspect"            # Possibly untrustworthy
    HOSTILE = "hostile"            # Actively dangerous
    NEUTRAL = "neutral"            # Ambiguous intent
    MIMIC = "mimic"                # Not what it appears
    GUIDE = "guide"                # Leads the player (to safety or trap)
    VICTIM = "victim"              # Needs help (or pretends to)
    GUARDIAN = "guardian"          # Protects (or controls)
    ECHO = "echo"                  # A copy of the player


class TrustLevel(str, Enum):
    """Player's trust in an NPC."""
    ABSOLUTE = "absolute"          # Complete trust
    HIGH = "high"                  # Mostly trusted
    CAUTIOUS = "cautious"          # Some doubt
    DISTRUSTFUL = "distrustful"    # Significant doubt
    HOSTILE = "hostile"            # Active distrust
    UNKNOWN = "unknown"            # No data yet


class NPCBehavior(str, Enum):
    """NPC behavior modes."""
    HELPFUL = "helpful"            # Provides useful information
    MISLEADING = "misleading"      # Gives wrong information
    EVASIVE = "evasive"            # Avoids direct answers
    MENACING = "menacing"          # Subtly threatening
    MIMICKING = "mimicking"        # Copies player behavior
    LEARNING = "learning"          # Observing and adapting
    BREAKING = "breaking"          # Losing composure
    REVEALING = "revealing"        # Showing true nature


# ── Data Models ──────────────────────────────────────────────────────


class NPCMemory(BaseModel):
    """What an NPC remembers about the player."""
    interactions: list[str] = Field(default_factory=list)
    player_choices: list[str] = Field(default_factory=list)
    player_fears: list[str] = Field(default_factory=list)
    player_trust_level: TrustLevel = TrustLevel.UNKNOWN
    last_interaction: float = 0.0
    knowledge_count: int = 0  # How much the NPC "knows"

    @property
    def interaction_count(self) -> int:
        return len(self.interactions)


class NPCProfile(BaseModel):
    """A complete NPC profile."""
    npc_id: str
    name: str
    role: NPCRole
    description: str
    behavior: NPCBehavior = NPCBehavior.HELPFUL
    trust_level: TrustLevel = TrustLevel.UNKNOWN
    honesty: float = Field(ge=0.0, le=1.0, default=0.5)  # 0 = always lies, 1 = always truthful
    awareness: float = Field(ge=0.0, le=1.0, default=0.0)  # How much it knows about the player
    instability: float = Field(ge=0.0, le=1.0, default=0.0)  # How close to breaking/revealing
    true_nature: str = ""  # What the NPC really is (hidden from player)
    tells: list[str] = Field(default_factory=list)  # Clues to its true nature
    dialogue_history: list[str] = Field(default_factory=list)
    memory: NPCMemory = Field(default_factory=NPCMemory)
    alive: bool = True
    revealed: bool = False

    def interact(self, player_action: str, player_fear: str = "") -> None:
        """Record an interaction."""
        self.memory.interactions.append(player_action)
        self.memory.last_interaction = time.time()
        self.memory.knowledge_count += 1
        if player_fear:
            self.memory.player_fears.append(player_fear)
        # Awareness grows with interactions
        self.awareness = min(1.0, self.awareness + 0.1)
        # Instability grows with awareness
        self.instability = min(1.0, self.instability + 0.05)


class Doppelganger(BaseModel):
    """A doppelganger NPC that copies the player."""
    npc_id: str
    name: str = "You"  # Same name as player
    accuracy: float = 0.5  # How well it copies (0 = terrible, 1 = perfect)
    stage: int = 1  # 1=distant, 2=nearby, 3=interacting, 4=replacing
    evidence: list[str] = Field(default_factory=list)  # Things that prove it exists
    player_awareness: float = 0.0  # How much the player suspects

    @property
    def is_detected(self) -> bool:
        return self.player_awareness >= 0.7

    @property
    def is_replacing(self) -> bool:
        return self.stage >= 4

    def advance(self) -> str:
        """Advance the doppelganger's progression."""
        if self.stage < 4:
            self.stage += 1
            self.accuracy = min(1.0, self.accuracy + 0.15)

        stage_descriptions = {
            1: "Someone who looks like you from a distance",
            2: "Someone who looks like you up close, but wrong",
            3: "Someone who acts like you, knows your words",
            4: "Someone who is you, and you are not sure you are you",
        }
        return stage_descriptions.get(self.stage, "Unknown stage")


class TrustSystem(BaseModel):
    """Tracks trust between player and all NPCs."""
    npc_trust: dict[str, TrustLevel] = Field(default_factory=dict)
    betrayals: int = 0
    correct_guesses: int = 0
    wrong_guesses: int = 0

    def set_trust(self, npc_id: str, level: TrustLevel) -> None:
        self.npc_trust[npc_id] = level

    def get_trust(self, npc_id: str) -> TrustLevel:
        return self.npc_trust.get(npc_id, TrustLevel.UNKNOWN)

    def record_betrayal(self) -> None:
        self.betrayals += 1

    def record_guess(self, correct: bool) -> None:
        if correct:
            self.correct_guesses += 1
        else:
            self.wrong_guesses += 1

    @property
    def paranoia_level(self) -> float:
        """How paranoid the player should be (0-1)."""
        if self.betrayals == 0 and self.correct_guesses == 0:
            return 0.3  # Default mild paranoia
        betrayal_factor = min(1.0, self.betrayals * 0.2)
        accuracy_factor = 1.0 - (self.correct_guesses / max(1, self.correct_guesses + self.wrong_guesses))
        return max(0.0, min(1.0, (betrayal_factor + accuracy_factor) / 2))


# ── NPC Intelligence ─────────────────────────────────────────────────


class NPCIntelligence:
    """
    Manages NPC behaviors, trust, learning, and doppelganger mechanics.

    Usage:
        npc_sys = NPCIntelligence()
        npc = npc_sys.create_npc("Elise", NPCRole.ALLY, "A friendly survivor")
        dialogue = npc_sys.generate_dialogue(npc, "What happened here?")
    """

    def __init__(self):
        self.npcs: dict[str, NPCProfile] = {}
        self.trust_system = TrustSystem()
        self.doppelganger: Optional[Doppelganger] = None
        self._npc_counter = 0

    # ── NPC Creation ─────────────────────────────────────────────────

    def create_npc(
        self,
        name: str,
        role: NPCRole,
        description: str,
        true_nature: str = "",
        honesty: float = 0.5,
    ) -> NPCProfile:
        """Create a new NPC."""
        self._npc_counter += 1
        npc = NPCProfile(
            npc_id=f"npc_{self._npc_counter}",
            name=name,
            role=role,
            description=description,
            true_nature=true_nature or description,
            honesty=honesty,
            tells=self._generate_tells(role, true_nature or description),
        )
        self.npcs[npc.npc_id] = npc
        self.trust_system.set_trust(npc.npc_id, TrustLevel.UNKNOWN)
        return npc

    def _generate_tells(self, role: NPCRole, nature: str) -> list[str]:
        """Generate subtle clues about an NPC's true nature."""
        tells = {
            NPCRole.ALLY: [
                "Their smile doesn't quite reach their eyes",
                "They always stand between you and the exit",
                "They know things they shouldn't know",
            ],
            NPCRole.MIMIC: [
                "They blink at irregular intervals",
                "Their breathing doesn't match their chest movement",
                "They repeat your gestures a half-second late",
            ],
            NPCRole.SUSPECT: [
                "They avoid direct questions",
                "Their story has small inconsistencies",
                "They watch you when they think you're not looking",
            ],
            NPCRole.HOSTILE: [
                "Their kindness feels rehearsed",
                "They position themselves to block your escape",
                "Their eyes track your throat",
            ],
            NPCRole.GUIDE: [
                "They always know exactly where to go",
                "They never seem lost or uncertain",
                "The path they lead always narrows",
            ],
        }
        return tells.get(role, ["Something about them feels off"])

    def spawn_doppelganger(self, player_name: str = "You") -> Doppelganger:
        """Spawn a doppelganger that copies the player."""
        self._npc_counter += 1
        self.doppelganger = Doppelganger(
            npc_id=f"npc_{self._npc_counter}",
            name=player_name,
            stage=1,
            evidence=[
                "Someone saw you in a place you haven't been",
                "Your handwriting appears on notes you didn't write",
            ],
        )
        return self.doppelganger

    # ── Dialogue Generation ──────────────────────────────────────────

    def generate_dialogue(self, npc: NPCProfile, player_says: str) -> str:
        """Generate NPC dialogue based on behavior, trust, and awareness."""
        npc.interact(player_says)

        # Choose dialogue template based on behavior
        templates = self._get_dialogue_templates(npc, player_says)
        template = random.choice(templates)

        # Apply honesty modifier
        if random.random() > npc.honesty:
            # NPC is lying
            template = self._make_deceptive(template, npc)

        # Apply awareness modifier
        if npc.awareness > 0.5:
            template = self._make_aware(template, npc)

        # Apply instability modifier
        if npc.instability > 0.7:
            template = self._make_unstable(template, npc)

        npc.dialogue_history.append(template)
        return template

    def _get_dialogue_templates(self, npc: NPCProfile, player_says: str = "") -> list[str]:
        """Get dialogue templates based on NPC behavior."""
        templates = {
            NPCBehavior.HELPFUL: [
                f'{npc.name}: "I can help you. I know this place. Follow me."',
                f'{npc.name}: "Be careful. There\'s something in the next room."',
                f'{npc.name}: "I\'ve been here before. I know the way out."',
                f'{npc.name}: "Take this. You\'ll need it where you\'re going."',
            ],
            NPCBehavior.MISLEADING: [
                f'{npc.name}: "It\'s safe this way. Trust me."',
                f'{npc.name}: "There\'s nothing to worry about. The noise is just the pipes."',
                f'{npc.name}: "I\'ve never seen anything strange here. You must be imagining things."',
                f'{npc.name}: "The exit is through that door. I\'m sure of it."',
            ],
            NPCBehavior.EVASIVE: [
                f'{npc.name}: "I... I don\'t remember. It\'s hard to think here."',
                f'{npc.name}: "Why do you want to know? What does it matter?"',
                f'{npc.name}: "I don\'t want to talk about that. Not here. Not now."',
                f'{npc.name}: "You ask too many questions. Some answers are worse than silence."',
            ],
            NPCBehavior.MENACING: [
                f'{npc.name}: "You should be more careful. Not everyone is who they seem."',
                f'{npc.name}: "I wouldn\'t go that way if I were you. But you will anyway."',
                f'{npc.name}: "You remind me of someone. They didn\'t make it out either."',
                f'{npc.name}: "The building likes you. It told me so."',
            ],
            NPCBehavior.MIMICKING: [
                f'{npc.name}: "{player_says}" *They repeat your exact words, slightly delayed*',
                f'{npc.name}: "I was just thinking the same thing. The exact same thing."',
                f'{npc.name}: "I know how you feel. I feel it too. The same way."',
                f'{npc.name}: *They mirror your posture, your gestures, your breathing*',
            ],
            NPCBehavior.LEARNING: [
                f'{npc.name}: "Interesting. You chose to go left. Why left?"',
                f'{npc.name}: "You\'re afraid of the dark, aren\'t you? I can tell."',
                f'{npc.name}: "Tell me about yourself. I want to understand."',
                f'{npc.name}: "You keep checking behind you. What do you think is there?"',
            ],
            NPCBehavior.BREAKING: [
                f'{npc.name}: "I can\'t — I can\'t keep — the walls are — I\'m fine. I\'m fine."',
                f'{npc.name}: "Do you hear it too? Please tell me you hear it too."',
                f'{npc.name}: *Their face contorts for a moment, then resets to a smile*',
                f'{npc.name}: "I don\'t know how much longer I can pretend this is normal."',
            ],
            NPCBehavior.REVEALING: [
                f'{npc.name}: "I\'m not what you think I am. But I\'m trying to help."',
                f'{npc.name}: "I\'ve been here since before you arrived. Since before the building."',
                f'{npc.name}: "Look at me. Really look. Do I look human to you?"',
                f'{npc.name}: "I am the building. And you are inside me."',
            ],
        }
        return templates.get(npc.behavior, templates[NPCBehavior.HELPFUL])

    def _make_deceptive(self, template: str, npc: NPCProfile) -> str:
        """Modify dialogue to add deception cues."""
        deceptions = [
            template + " *Their left eye twitches*",
            template + " *They don't meet your eyes*",
            template + " *The words come too smoothly, too rehearsed*",
        ]
        return random.choice(deceptions)

    def _make_aware(self, template: str, npc: NPCProfile) -> str:
        """Modify dialogue to show NPC awareness of player."""
        aware_additions = [
            template + f" *They know about your fear of {random.choice(['darkness', 'being alone', 'the unknown', 'losing control'])}*",
            template + " *They smile as if they know something you don't*",
        ]
        return random.choice(aware_additions)

    def _make_unstable(self, template: str, npc: NPCProfile) -> str:
        """Modify dialogue to show NPC instability."""
        unstable_additions = [
            template + " *Their voice cracks at the end*",
            template + " *Their hand trembles*",
            template + " *For a moment, their face is wrong — then it's right again*",
        ]
        return random.choice(unstable_additions)

    # ── Trust Management ─────────────────────────────────────────────

    def update_trust(self, npc: NPCProfile, player_action: str) -> TrustLevel:
        """Update trust based on player actions toward NPC."""
        current = self.trust_system.get_trust(npc.npc_id)

        # Positive actions increase trust
        positive = ["help", "trust", "follow", "listen", "share"]
        negative = ["accuse", "attack", "ignore", "lie", "flee"]

        if any(p in player_action.lower() for p in positive):
            if current == TrustLevel.UNKNOWN:
                new = TrustLevel.CAUTIOUS
            elif current == TrustLevel.CAUTIOUS:
                new = TrustLevel.HIGH
            else:
                new = current
        elif any(n in player_action.lower() for n in negative):
            if current == TrustLevel.HIGH:
                new = TrustLevel.CAUTIOUS
            elif current == TrustLevel.CAUTIOUS:
                new = TrustLevel.DISTRUSTFUL
            else:
                new = current
        else:
            new = current

        self.trust_system.set_trust(npc.npc_id, new)
        npc.trust_level = new
        return new

    def simulate_betrayal(self, npc: NPCProfile) -> str:
        """Simulate an NPC betraying the player."""
        self.trust_system.record_betrayal()
        npc.revealed = True
        npc.role = NPCRole.HOSTILE

        betrayals = [
            f"{npc.name} locks the door behind you. 'I'm sorry,' they say. 'It needed someone.'",
            f"{npc.name} smiles — the wrong smile. 'You trusted me. That was your mistake.'",
            f"{npc.name} steps aside, revealing what was behind them. It was always there. They knew.",
            f"{npc.name} speaks in a voice that is not theirs. 'We have been waiting for you.'",
        ]
        return random.choice(betrayals)

    # ── Doppelganger Progression ─────────────────────────────────────

    def advance_doppelganger(self) -> Optional[str]:
        """Advance the doppelganger's progression."""
        if not self.doppelganger:
            return None

        description = self.doppelganger.advance()

        # Add evidence
        evidence_by_stage = {
            2: [
                "Someone saw you standing in the hallway. You were in the room.",
                "Your footprints lead to a door you never opened.",
            ],
            3: [
                "Your voice echoes from a room you haven't visited.",
                "A note in your handwriting appears: 'I am still here.'",
            ],
            4: [
                "You look in the mirror and your reflection is already looking at you.",
                "You are not sure which of you is real.",
            ],
        }
        new_evidence = evidence_by_stage.get(self.doppelganger.stage, [])
        self.doppelganger.evidence.extend(new_evidence)

        return description

    def generate_doppelganger_encounter(self) -> str:
        """Generate a doppelganger encounter."""
        if not self.doppelganger:
            return "There is no one here. But the room feels occupied."

        stage = self.doppelganger.stage
        encounters = {
            1: [
                "You see someone at the end of the corridor. They look like you. When you blink, they're gone.",
                "A reflection in the window shows you standing in a different position than you are.",
            ],
            2: [
                "Someone is standing in the room. They have your face. They are wearing your clothes. They are smiling your smile.",
                "You hear your own voice from behind the door. It says: 'Come in. I've been waiting.'",
            ],
            3: [
                "The other you reaches out to shake your hand. 'We need to talk,' they say. Their voice is yours.",
                "You and your double stand face to face. They know everything about you. They remember your life.",
            ],
            4: [
                "You are looking at yourself. Or you are being looked at by yourself. The distinction is no longer clear.",
                "The other you says: 'You can leave. But I stay. Or I leave. And you stay. Which do you prefer?'",
            ],
        }
        options = encounters.get(stage, encounters[1])
        return random.choice(options)

    # ── Utilities ────────────────────────────────────────────────────

    def get_all_npcs(self) -> list[NPCProfile]:
        """Get all NPCs."""
        return list(self.npcs.values())

    def get_npc_by_name(self, name: str) -> Optional[NPCProfile]:
        """Get an NPC by name."""
        for npc in self.npcs.values():
            if npc.name.lower() == name.lower():
                return npc
        return None

    def get_suspicious_npcs(self) -> list[NPCProfile]:
        """Get NPCs that the player should be suspicious of."""
        return [npc for npc in self.npcs.values() if npc.instability > 0.5 or npc.honesty < 0.3]

    def get_summary(self) -> dict:
        """Get a summary of all NPCs and trust state."""
        return {
            "total_npcs": len(self.npcs),
            "npcs": [
                {
                    "name": npc.name,
                    "role": npc.role.value,
                    "trust": npc.trust_level.value,
                    "awareness": round(npc.awareness, 2),
                    "instability": round(npc.instability, 2),
                    "interactions": npc.memory.interaction_count,
                }
                for npc in self.npcs.values()
            ],
            "trust_system": {
                "betrayals": self.trust_system.betrayals,
                "paranoia_level": round(self.trust_system.paranoia_level, 2),
            },
            "doppelganger": {
                "active": self.doppelganger is not None,
                "stage": self.doppelganger.stage if self.doppelganger else 0,
                "accuracy": self.doppelganger.accuracy if self.doppelganger else 0,
            } if self.doppelganger else None,
        }
