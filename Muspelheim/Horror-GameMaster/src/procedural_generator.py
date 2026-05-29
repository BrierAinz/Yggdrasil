"""
Procedural Generator v2 — Scene templates, chain events, red herrings,
safe rooms, entity spawning, and narrative progression.

Horror GameMaster — BrierStudios
"""

from __future__ import annotations

import random
from enum import StrEnum

from pydantic import BaseModel, Field


# ── Enums ────────────────────────────────────────────────────────────


class SceneType(StrEnum):
    ABANDONED_HOSPITAL = "abandoned_hospital"
    DARK_FOREST = "dark_forest"
    UNDERGROUND_BUNKER = "underground_bunker"
    HAUNTED_HOUSE = "haunted_house"
    EMPTY_SCHOOL = "empty_school"
    DERELICT_SHIP = "derelict_ship"
    FROZEN_LIGHTHOUSE = "frozen_lighthouse"
    UNDERGROUND_CAVE = "underground_cave"
    ABANDONED_THEATER = "abandoned_theater"
    CORRUPTED_GARDEN = "corrupted_garden"
    MIRROR_MAZE = "mirror_maze"
    INFINITE_LIBRARY = "infinite_library"
    SINKING_SUBMARINE = "sinking_submarine"
    ORBITING_STATION = "orbiting_station"
    ANCIENT_TEMPLE = "ancient_temple"
    MODERN_OFFICE = "modern_office"
    PARKING_GARAGE = "parking_garage"
    SUBWAY_TUNNEL = "subway_tunnel"
    ELEVATOR_SHAFT = "elevator_shaft"
    ROOFTOP = "rooftop"
    SEWER_SYSTEM = "sewer_system"
    MORGUE = "morgue"


class EventType(StrEnum):
    FORESHADOWING = "foreshadowing"
    RED_HERRING = "red_herring"
    ESCALATION = "escalation"
    JUMPSCARE = "jumpscare"
    REVELATION = "revelation"
    ENVIRONMENTAL = "environmental"
    ENTITY_SIGHTING = "entity_sighting"
    SOUND_EVENT = "sound_event"
    ITEM_DISCOVERY = "item_discovery"
    NPC_ENCOUNTER = "npc_encounter"
    FALSE_SAFETY = "false_safety"
    TRAP = "trap"


class NarrativeAct(StrEnum):
    SETUP = "setup"  # Calm, establishing atmosphere
    RISING_TENSION = "rising"  # Gradual escalation
    CLIMAX = "climax"  # Peak horror moment
    RESOLUTION = "resolution"  # Aftermath, breathing room
    LOOP = "loop"  # Reset for next cycle


class EntityBehavior(StrEnum):
    STALKING = "stalking"  # Following at distance
    AMBUSHING = "ambushing"  # Waiting to strike
    MANIFESTING = "manifesting"  # Slowly appearing
    MIMICKING = "mimicking"  # Copying something familiar
    CORRUPTING = "corrupting"  # Changing the environment
    WATCHING = "watching"  # Observing, not acting
    WHISPERING = "whispering"  # Audible but not visible
    PHASING = "phasing"  # Intermittently visible


# ── Data Models ──────────────────────────────────────────────────────


class SensoryDetail(BaseModel):
    """Sensory information for a scene."""

    sound: str = ""
    smell: str = ""
    temperature: str = ""
    light_level: str = ""
    texture: str = ""
    taste: str = ""


class SceneTemplate(BaseModel):
    """A template for generating scenes."""

    scene_type: SceneType
    name: str
    description: str
    sensory: SensoryDetail
    available_exits: list[str] = []
    potential_events: list[EventType] = []
    ambient_details: list[str] = []
    danger_level: float = Field(ge=0.0, le=1.0, default=0.5)
    fear_types: list[str] = []


class GameEvent2(BaseModel):
    """An event in the game world."""

    event_id: str
    event_type: EventType
    description: str
    intensity: float = Field(ge=0.0, le=1.0)
    fear_type: str = ""
    follow_up_event: str | None = None
    requires_condition: str = ""
    narrative_text: str = ""


class ChainEvent(BaseModel):
    """A sequence of linked events."""

    chain_id: str
    name: str
    events: list[GameEvent2]
    trigger_condition: str = ""
    current_step: int = 0
    loop: bool = False


class SafeRoom(BaseModel):
    """A safe room that can degrade over time."""

    room_id: str
    name: str
    initial_description: str
    safety_level: float = 1.0  # 1.0 = safe, 0.0 = compromised
    degradation_rate: float = 0.05  # Per turn
    degradation_events: list[str] = []
    compromised: bool = False
    compromise_event: str = ""


class EntitySpawn(BaseModel):
    """An entity encounter configuration."""

    entity_id: str
    name: str
    description: str
    behavior: EntityBehavior
    fear_type: str
    proximity: float = 1.0  # 1.0 = far, 0.0 = touching
    visibility: float = 0.0  # 0.0 = invisible, 1.0 = fully visible
    weakness_hint: str = ""
    progression_events: list[str] = []


class NarrativeState(BaseModel):
    """Current state of the narrative progression."""

    current_act: NarrativeAct = NarrativeAct.SETUP
    tension_level: float = 0.0
    events_in_act: int = 0
    total_events: int = 0
    scares_delivered: int = 0
    session_duration: float = 0.0
    pacing: float = 0.5  # 0 = slow burn, 1 = relentless


# ── Procedural Generator ─────────────────────────────────────────────


class ProceduralGenerator:
    """
    Generates scenes, events, entities, and manages narrative progression.

    Usage:
        gen = ProceduralGenerator()
        scene = gen.generate_scene(SceneType.ABANDONED_HOSPITAL)
        event = gen.generate_event(EventType.FORESHADOWING, intensity=0.5)
    """

    def __init__(self, seed: int | None = None):
        self.rng = random.Random(seed)
        self.narrative = NarrativeState()
        self._templates = self._build_templates()
        self._chain_events = self._build_chains()
        self._safe_rooms: list[SafeRoom] = []
        self._active_entities: list[EntitySpawn] = []
        self._event_counter = 0

    # ── Scene Generation ─────────────────────────────────────────────

    def generate_scene(self, scene_type: SceneType | None = None) -> SceneTemplate:
        """Generate a scene, optionally of a specific type."""
        if scene_type is None:
            scene_type = self.rng.choice(list(SceneType))
        return self._templates.get(scene_type, self._templates[SceneType.ABANDONED_HOSPITAL])

    def generate_scene_by_fear(self, fear_type: str) -> SceneTemplate:
        """Generate a scene optimized for a specific fear type."""
        candidates = [t for t in self._templates.values() if fear_type in t.fear_types]
        if candidates:
            return self.rng.choice(candidates)
        return self.generate_scene()

    # ── Event Generation ─────────────────────────────────────────────

    def generate_event(
        self,
        event_type: EventType | None = None,
        intensity: float = 0.5,
        fear_type: str = "psychological",
    ) -> GameEvent2:
        """Generate a game event."""
        self._event_counter += 1
        if event_type is None:
            event_type = self._pick_event_type()

        templates = self._get_event_templates(event_type, fear_type)
        template = self.rng.choice(templates) if templates else self._default_event(event_type)

        return GameEvent2(
            event_id=f"evt_{self._event_counter}",
            event_type=event_type,
            description=template["description"],
            intensity=min(1.0, max(0.0, intensity)),
            fear_type=fear_type,
            narrative_text=template.get("narrative", ""),
        )

    def _pick_event_type(self) -> EventType:
        """Pick event type based on narrative act and pacing."""
        weights = {
            NarrativeAct.SETUP: {
                EventType.ENVIRONMENTAL: 4,
                EventType.FORESHADOWING: 3,
                EventType.ITEM_DISCOVERY: 2,
                EventType.SOUND_EVENT: 1,
            },
            NarrativeAct.RISING_TENSION: {
                EventType.ESCALATION: 3,
                EventType.ENTITY_SIGHTING: 3,
                EventType.FORESHADOWING: 2,
                EventType.RED_HERRING: 1,
                EventType.SOUND_EVENT: 2,
            },
            NarrativeAct.CLIMAX: {
                EventType.JUMPSCARE: 3,
                EventType.ESCALATION: 3,
                EventType.REVELATION: 2,
                EventType.ENTITY_SIGHTING: 2,
            },
            NarrativeAct.RESOLUTION: {
                EventType.ENVIRONMENTAL: 3,
                EventType.FALSE_SAFETY: 2,
                EventType.ITEM_DISCOVERY: 2,
            },
            NarrativeAct.LOOP: {
                EventType.ENVIRONMENTAL: 3,
                EventType.FORESHADOWING: 2,
                EventType.REVELATION: 1,
            },
        }
        act_weights = weights.get(self.narrative.current_act, weights[NarrativeAct.SETUP])
        types = list(act_weights.keys())
        weights_list = list(act_weights.values())
        return self.rng.choices(types, weights=weights_list, k=1)[0]

    def _get_event_templates(self, event_type: EventType, fear_type: str) -> list[dict]:
        """Get event templates for a given type and fear."""
        templates = {
            EventType.FORESHADOWING: [
                {
                    "description": "A distant sound echoes through the walls",
                    "narrative": "You hear something — not close, but not far enough. A sound that does not belong.",
                },
                {
                    "description": "An object has been moved since you last saw it",
                    "narrative": "The chair is not where you left it. It has moved three feet to the left. It is facing the wall.",
                },
                {
                    "description": "A shadow passes across the doorway",
                    "narrative": "Something crosses the doorway. Not a person — a shape, too fast, too dark, too wrong.",
                },
                {
                    "description": "A note appears where there was none before",
                    "narrative": "The note is written in handwriting that is almost yours. It says: 'DO NOT TRUST THE NEXT ROOM.'",
                },
            ],
            EventType.RED_HERRING: [
                {
                    "description": "A door rattles violently but nothing is behind it",
                    "narrative": "The door shakes in its frame. You open it. Nothing. Wind? There is no wind.",
                },
                {
                    "description": "A figure appears to be hiding but turns out to be a coat rack",
                    "narrative": "The shape in the corner is a person. No — a coat rack. It was always a coat rack. Wasn't it?",
                },
                {
                    "description": "A loud crash comes from a room that is empty",
                    "narrative": "The crash is massive — glass breaking, metal bending. You rush in. The room is pristine.",
                },
            ],
            EventType.ESCALATION: [
                {
                    "description": "The temperature drops sharply",
                    "narrative": "The cold arrives suddenly, as if someone opened a door to winter. Your breath fogs. The walls begin to frost.",
                },
                {
                    "description": "Lights begin to fail one by one",
                    "narrative": "The lights go out in sequence, each one dying with a pop. The darkness advances like a tide.",
                },
                {
                    "description": "Something that was hidden becomes visible",
                    "narrative": "The wall was smooth. Now it has cracks. The cracks form a pattern. The pattern is a face.",
                },
                {
                    "description": "The architecture changes subtly",
                    "narrative": "The hallway is longer than it was. The ceiling is lower. The doors are closer together. The building is compressing.",
                },
            ],
            EventType.JUMPSCARE: [
                {
                    "description": "Something drops from above",
                    "narrative": "It falls from the ceiling — not fast, not slow, but deliberate. It lands in front of you. It is looking up.",
                },
                {
                    "description": "A face appears in the window",
                    "narrative": "The face presses against the glass from outside. It is your face. It is smiling. You are not smiling.",
                },
                {
                    "description": "A hand grabs from below",
                    "narrative": "The hand comes through the floor — through solid concrete — and grabs your ankle. It pulls.",
                },
                {
                    "description": "Everything goes silent, then: a scream",
                    "narrative": "The silence is absolute. No heartbeat. No breathing. No ambient sound. Then the scream — from everywhere.",
                },
            ],
            EventType.REVELATION: [
                {
                    "description": "Evidence that the player is not who they think",
                    "narrative": "The documents are clear. The name is yours. The photo is yours. The date of death is last year.",
                },
                {
                    "description": "The true nature of the location is revealed",
                    "narrative": "This is not a building. It has never been a building. It is alive, and you are inside it.",
                },
                {
                    "description": "An NPC reveals they are not human",
                    "narrative": "She stops talking. Her mouth closes. But the voice continues. It comes from behind her face.",
                },
            ],
            EventType.ENVIRONMENTAL: [
                {
                    "description": "Water begins to rise from the floor",
                    "narrative": "The water is cold. Ankle-deep and rising. It smells like the ocean, but you are nowhere near the ocean.",
                },
                {
                    "description": "The walls begin to close in",
                    "narrative": "The walls are closer. Not your imagination — the gap between them has decreased by six inches.",
                },
                {
                    "description": "A strange sound fills the space",
                    "narrative": "The sound is not mechanical, not organic. It is the sound of something learning how to breathe.",
                },
                {
                    "description": "Gravity shifts subtly",
                    "narrative": "The glass on the table slides. Slowly, deliberately, toward the wall. Gravity has changed direction.",
                },
            ],
            EventType.ENTITY_SIGHTING: [
                {
                    "description": "A figure stands at the end of the corridor",
                    "narrative": "It stands at the far end. Motionless. Watching. It has been there since you arrived. You only just noticed.",
                },
                {
                    "description": "Something moves in peripheral vision",
                    "narrative": "Every time you turn your head, it moves to the edge of your vision. You cannot look directly at it.",
                },
                {
                    "description": "A reflection shows something that is not there",
                    "narrative": "The mirror shows the room correctly, except for the figure standing behind you. There is no one behind you.",
                },
            ],
            EventType.SOUND_EVENT: [
                {
                    "description": "Footsteps follow the player",
                    "narrative": "The footsteps match yours — same pace, same rhythm — but they are one step behind. When you stop, they take one more.",
                },
                {
                    "description": "Whispering from the walls",
                    "narrative": "The whispers are in a language you do not understand. But the tone is clear: it is discussing you.",
                },
                {
                    "description": "A child's laughter echoes",
                    "narrative": "The laughter comes from upstairs. From a room you have not entered. From a room that should not have a child in it.",
                },
            ],
            EventType.ITEM_DISCOVERY: [
                {
                    "description": "A key hidden in an unexpected place",
                    "narrative": "The key is inside the wall. You found it because the plaster was fresh — someone hid it recently.",
                },
                {
                    "description": "A photograph that should not exist",
                    "narrative": "The photo shows you, in this room, taken from the corner. Taken today. You were alone.",
                },
                {
                    "description": "A journal with entries in your handwriting",
                    "narrative": "The journal is full. Every page is in your handwriting. Every entry describes a day you do not remember.",
                },
            ],
            EventType.NPC_ENCOUNTER: [
                {
                    "description": "A person who should not be here",
                    "narrative": "She says she has been here for weeks. She says the building will not let her leave. She says you cannot leave either.",
                },
                {
                    "description": "A voice on the radio",
                    "narrative": "The radio crackles. A voice says your name. It says: 'Do not open the door.' The radio has no batteries.",
                },
                {
                    "description": "A child asking for help",
                    "narrative": "The child is lost. The child is scared. The child's skin is cold. The child's eyes do not blink.",
                },
            ],
            EventType.FALSE_SAFETY: [
                {
                    "description": "A room that seems perfectly safe",
                    "narrative": "The room is warm, lit, furnished. The door locks. The windows are intact. Nothing is wrong. Nothing. Yet.",
                },
                {
                    "description": "Contact from the outside world",
                    "narrative": "The phone rings. A voice says rescue is coming. The voice is yours.",
                },
                {
                    "description": "A familiar object in a strange place",
                    "narrative": "Your coffee mug. Your exact mug, with the chip on the handle. Here. In this impossible place.",
                },
            ],
            EventType.TRAP: [
                {
                    "description": "A door that locks behind the player",
                    "narrative": "The door closes. The lock engages. Not a click — a thud. The sound of something heavy sealing shut.",
                },
                {
                    "description": "The floor gives way",
                    "narrative": "The floor was solid. Now it is not. You fall — not far, but enough. The opening above you closes.",
                },
                {
                    "description": "An exit that leads back inside",
                    "narrative": "You walk through the door and you are in the same room. The same room. The door behind you is gone.",
                },
            ],
        }
        return templates.get(
            event_type, [{"description": "Something happens", "narrative": "Something happens."}]
        )

    def _default_event(self, event_type: EventType) -> dict:
        return {
            "description": f"A {event_type.value} event occurs",
            "narrative": "Something happens.",
        }

    # ── Chain Events ─────────────────────────────────────────────────

    def create_chain(self, chain_id: str, name: str, events: list[GameEvent2]) -> ChainEvent:
        """Create a chain of linked events."""
        chain = ChainEvent(chain_id=chain_id, name=name, events=events)
        self._chain_events.append(chain)
        return chain

    def advance_chain(self, chain: ChainEvent) -> GameEvent2 | None:
        """Get the next event in a chain."""
        if chain.current_step >= len(chain.events):
            if chain.loop:
                chain.current_step = 0
            else:
                return None
        event = chain.events[chain.current_step]
        chain.current_step += 1
        return event

    def _build_chains(self) -> list[ChainEvent]:
        """Build default event chains."""
        return []  # Built dynamically during gameplay

    # ── Red Herrings ─────────────────────────────────────────────────

    def generate_red_herring(self, fear_type: str = "paranoia") -> GameEvent2:
        """Generate a red herring event."""
        return self.generate_event(EventType.RED_HERRING, intensity=0.3, fear_type=fear_type)

    def generate_false_safety(self) -> GameEvent2:
        """Generate a false safety event."""
        return self.generate_event(EventType.FALSE_SAFETY, intensity=0.2, fear_type="psychological")

    # ── Safe Rooms ───────────────────────────────────────────────────

    def create_safe_room(self, room_id: str, name: str, description: str) -> SafeRoom:
        """Create a new safe room."""
        room = SafeRoom(
            room_id=room_id,
            name=name,
            initial_description=description,
            degradation_events=[
                "A sound echoes from outside the door",
                "The light flickers briefly",
                "The temperature drops slightly",
                "Something scratches against the wall",
                "The door handle rattles",
                "A shadow passes under the door",
                "The lock clicks — once — on its own",
                "The smell of something organic fills the room",
                "The walls creak as if under pressure",
                "The light goes out. It does not come back.",
            ],
        )
        self._safe_rooms.append(room)
        return room

    def degrade_safe_room(self, room: SafeRoom) -> str | None:
        """Degrade a safe room and return the degradation event."""
        if room.compromised:
            return None

        room.safety_level = max(0.0, room.safety_level - room.degradation_rate)

        if room.safety_level <= 0.0:
            room.compromised = True
            return (
                room.compromise_event
                or "The safe room is no longer safe. Something has changed. The room that protected you has turned against you."
            )

        event_index = int((1.0 - room.safety_level) * len(room.degradation_events))
        event_index = min(event_index, len(room.degradation_events) - 1)
        return room.degradation_events[event_index]

    # ── Entity Spawning ──────────────────────────────────────────────

    def spawn_entity(
        self,
        name: str,
        description: str,
        behavior: EntityBehavior,
        fear_type: str,
        weakness_hint: str = "",
    ) -> EntitySpawn:
        """Spawn a new entity."""
        entity = EntitySpawn(
            entity_id=f"entity_{len(self._active_entities)}",
            name=name,
            description=description,
            behavior=behavior,
            fear_type=fear_type,
            weakness_hint=weakness_hint,
            progression_events=[
                f"{name} is watching from a distance",
                f"{name} has moved closer",
                f"{name} is now visible in detail",
                f"{name} is approaching",
                f"{name} is here",
            ],
        )
        self._active_entities.append(entity)
        return entity

    def advance_entity(self, entity: EntitySpawn) -> str:
        """Advance an entity's progression and return description."""
        step = int((1.0 - entity.proximity) * len(entity.progression_events))
        step = min(step, len(entity.progression_events) - 1)

        entity.proximity = max(0.0, entity.proximity - 0.15)
        entity.visibility = min(1.0, entity.visibility + 0.2)

        return entity.progression_events[step]

    def generate_entity_encounter(self, fear_type: str) -> EntitySpawn:
        """Generate a random entity encounter for a given fear type."""
        templates = {
            "psychological": [
                (
                    "The Watcher",
                    "A figure that stands at the edge of your vision, always facing away",
                    EntityBehavior.WATCHING,
                ),
                (
                    "The Mimic",
                    "Something that copies the faces of people you know, but wrong",
                    EntityBehavior.MIMICKING,
                ),
                (
                    "The Whisperer",
                    "A voice that comes from inside the walls, speaking your thoughts",
                    EntityBehavior.WHISPERING,
                ),
            ],
            "body_horror": [
                (
                    "The Crawler",
                    "A mass of limbs that moves like a spider made of human arms",
                    EntityBehavior.STALKING,
                ),
                (
                    "The Bloom",
                    "A growth that spreads across surfaces, pulsing with a heartbeat",
                    EntityBehavior.CORRUPTING,
                ),
                (
                    "The Assembler",
                    "Something that collects body parts and arranges them into patterns",
                    EntityBehavior.AMBUSHING,
                ),
            ],
            "darkness": [
                (
                    "The Absence",
                    "A patch of darkness that is darker than the dark around it",
                    EntityBehavior.PHASING,
                ),
                (
                    "The Depth",
                    "Something that lives in the space between light and shadow",
                    EntityBehavior.STALKING,
                ),
                (
                    "The Void",
                    "An area where light goes to die, and something lives in the dead light",
                    EntityBehavior.CORRUPTING,
                ),
            ],
            "paranoia": [
                (
                    "The Observer",
                    "Someone who has been watching you for longer than you have been here",
                    EntityBehavior.WATCHING,
                ),
                (
                    "The Replacement",
                    "Something that is learning to be you, one detail at a time",
                    EntityBehavior.MIMICKING,
                ),
                (
                    "The Architect",
                    "The thing that built this place, and knows every wall is a cage",
                    EntityBehavior.CORRUPTING,
                ),
            ],
            "isolation": [
                (
                    "The Echo",
                    "Your own voice, coming back wrong, from places you did not speak",
                    EntityBehavior.WHISPERING,
                ),
                (
                    "The Distance",
                    "Something that exists in the space between you and the nearest person",
                    EntityBehavior.STALKING,
                ),
                (
                    "The Last",
                    "The thing that was here before you, and will be here after",
                    EntityBehavior.WATCHING,
                ),
            ],
            "loss_of_control": [
                (
                    "The Puppeteer",
                    "Something that moves your body when you are not paying attention",
                    EntityBehavior.CORRUPTING,
                ),
                (
                    "The Director",
                    "The entity that writes the script of your life, and you are reading it",
                    EntityBehavior.WATCHING,
                ),
                (
                    "The Loop",
                    "A thing that exists in the repetition, growing stronger with each cycle",
                    EntityBehavior.AMBUSHING,
                ),
            ],
            "jumpscare": [
                (
                    "The Lurker",
                    "Something that waits in the space you just checked, behind you",
                    EntityBehavior.AMBUSHING,
                ),
                (
                    "The Drop",
                    "A thing that falls from above, but only when you look up",
                    EntityBehavior.AMBUSHING,
                ),
                (
                    "The Face",
                    "Something that appears in windows, mirrors, and the dark",
                    EntityBehavior.MANIFESTING,
                ),
            ],
        }

        options = templates.get(fear_type, templates["psychological"])
        name, desc, behavior = self.rng.choice(options)
        return self.spawn_entity(name, desc, behavior, fear_type)

    # ── Narrative Progression ────────────────────────────────────────

    def advance_narrative(self) -> NarrativeAct:
        """Advance the narrative to the next act."""
        act_order = [
            NarrativeAct.SETUP,
            NarrativeAct.RISING_TENSION,
            NarrativeAct.CLIMAX,
            NarrativeAct.RESOLUTION,
            NarrativeAct.LOOP,
        ]
        current_idx = act_order.index(self.narrative.current_act)
        next_idx = (current_idx + 1) % len(act_order)
        self.narrative.current_act = act_order[next_idx]
        self.narrative.events_in_act = 0
        return self.narrative.current_act

    def should_advance(self) -> bool:
        """Check if it's time to advance to the next narrative act."""
        thresholds = {
            NarrativeAct.SETUP: 3,
            NarrativeAct.RISING_TENSION: 8,
            NarrativeAct.CLIMAX: 3,
            NarrativeAct.RESOLUTION: 2,
            NarrativeAct.LOOP: 2,
        }
        return self.narrative.events_in_act >= thresholds.get(self.narrative.current_act, 5)

    def generate_ending(self) -> str:
        """Generate an ending based on the narrative state."""
        endings = {
            "survival": "You emerge into daylight. The building stands behind you, silent, patient. You survived. But the building is still there. And it remembers your face.",
            "escape": "The door opens to the outside. Fresh air. Real sky. You run. You do not look back. You will never look back.",
            "transformation": "You look at your hands. They are not your hands anymore. They are better. You are better. The building did not trap you — it freed you.",
            "loop": "You open your eyes. You are at the beginning. The building is waiting. It has always been waiting. You have always been here.",
            "revelation": "The truth is simple: there is no building. There never was. The horror was always inside you. And now it is outside.",
            "sacrifice": "You close the door behind you. The lock engages. Someone else is free because you are not. The building accepts your offering.",
        }
        weights = {
            NarrativeAct.SETUP: "survival",
            NarrativeAct.RISING_TENSION: "escape",
            NarrativeAct.CLIMAX: "revelation",
            NarrativeAct.RESOLUTION: "transformation",
            NarrativeAct.LOOP: "loop",
        }
        ending_type = weights.get(self.narrative.current_act, "survival")
        return endings[ending_type]

    # ── Template Builder ─────────────────────────────────────────────

    def _build_templates(self) -> dict[SceneType, SceneTemplate]:
        """Build all scene templates."""
        templates = {}

        templates[SceneType.ABANDONED_HOSPITAL] = SceneTemplate(
            scene_type=SceneType.ABANDONED_HOSPITAL,
            name="Abandoned Hospital",
            description="Fluorescent lights flicker overhead. The smell of antiseptic and decay. Gurneys line the corridors. Somewhere, a heart monitor beeps.",
            sensory=SensoryDetail(
                sound="Dripping water, distant beeping, the hum of dying fluorescent lights",
                smell="Antiseptic, decay, formaldehyde",
                temperature="Cold, damp",
                light_level="Flickering fluorescent, intermittent darkness",
                texture="Smooth tile floors, sticky surfaces, cold metal",
            ),
            available_exits=["corridor", "stairs", "elevator", "emergency_exit"],
            potential_events=[
                EventType.ENTITY_SIGHTING,
                EventType.SOUND_EVENT,
                EventType.ESCALATION,
                EventType.FORESHADOWING,
            ],
            ambient_details=[
                "Empty wheelchairs",
                "Medical records scattered on the floor",
                "An IV stand with a full bag, dripping",
                "A wheelchair at the end of the corridor, facing you",
            ],
            danger_level=0.7,
            fear_types=["psychological", "body_horror", "isolation"],
        )

        templates[SceneType.DARK_FOREST] = SceneTemplate(
            scene_type=SceneType.DARK_FOREST,
            name="Dark Forest",
            description="Trees tower above, blocking the sky. The path is barely visible. Something moves in the undergrowth.",
            sensory=SensoryDetail(
                sound="Branches snapping, wind through leaves, distant animal sounds that stop suddenly",
                smell="Damp earth, pine, something organic and wrong",
                temperature="Cold, getting colder",
                light_level="Moonlight through canopy, deep shadows",
                texture="Rough bark, soft moss, wet leaves underfoot",
            ),
            available_exits=["deeper_forest", "clearing", "cave", "river"],
            potential_events=[
                EventType.ENTITY_SIGHTING,
                EventType.ENVIRONMENTAL,
                EventType.ESCALATION,
                EventType.TRAP,
            ],
            ambient_details=[
                "Trees that seem closer than before",
                "A path that leads back to where you started",
                "Eyes reflecting in the darkness",
                "A clearing with a circle of stones",
            ],
            danger_level=0.6,
            fear_types=["darkness", "isolation", "paranoia"],
        )

        templates[SceneType.MIRROR_MAZE] = SceneTemplate(
            scene_type=SceneType.MIRROR_MAZE,
            name="Mirror Maze",
            description="Infinite reflections. Your face repeated a thousand times. But one of them is not quite right.",
            sensory=SensoryDetail(
                sound="Your footsteps echoing from every direction, breathing that is not yours",
                smell="Glass cleaner, ozone, something sweet",
                temperature="Cool, consistent",
                light_level="Bright, harsh, no shadows",
                texture="Smooth glass, cold metal frames",
            ),
            available_exits=["turn_left", "turn_right", "straight_ahead", "back"],
            potential_events=[
                EventType.JUMPSCARE,
                EventType.REVELATION,
                EventType.ENTITY_SIGHTING,
                EventType.ESCALATION,
            ],
            ambient_details=[
                "A reflection that moves independently",
                "A mirror that shows a different room",
                "Glass that is warm to the touch",
                "A reflection with too many eyes",
            ],
            danger_level=0.8,
            fear_types=["psychological", "paranoia", "body_horror"],
        )

        templates[SceneType.INFINITE_LIBRARY] = SceneTemplate(
            scene_type=SceneType.INFINITE_LIBRARY,
            name="Infinite Library",
            description="Shelves stretch beyond sight. Every book has your name on it. The librarian does not have a face.",
            sensory=SensoryDetail(
                sound="Pages turning by themselves, the creak of wooden shelves, a distant cough",
                smell="Old paper, leather, dust, ink",
                temperature="Cool, dry",
                light_level="Warm lamplight, shadows between shelves",
                texture="Smooth paper, rough leather, dusty wood",
            ),
            available_exits=["between_shelves", "upstairs", "downstairs", "reading_room"],
            potential_events=[
                EventType.REVELATION,
                EventType.ENTITY_SIGHTING,
                EventType.FORESHADOWING,
                EventType.ITEM_DISCOVERY,
            ],
            ambient_details=[
                "A book that writes itself",
                "Shelves that rearrange",
                "A reading nook with a warm cup of tea",
                "A book that contains your memories",
            ],
            danger_level=0.6,
            fear_types=["psychological", "paranoia", "loss_of_control"],
        )

        templates[SceneType.MORGUE] = SceneTemplate(
            scene_type=SceneType.MORGUE,
            name="Morgue",
            description="Steel drawers line the walls. One is open. The body inside is you.",
            sensory=SensoryDetail(
                sound="The hum of refrigeration, dripping, a drawer sliding open",
                smell="Formaldehyde, cold metal, death",
                temperature="Very cold, refrigerated",
                light_level="Harsh fluorescent, one light broken",
                texture="Cold steel, smooth tile, rubber gloves",
            ),
            available_exits=["corridor", "cold_storage", "office", "stairs"],
            potential_events=[
                EventType.JUMPSCARE,
                EventType.REVELATION,
                EventType.ENTITY_SIGHTING,
                EventType.ESCALATION,
            ],
            ambient_details=[
                "A drawer that opens on its own",
                "Toe tags with your name",
                "A body that was not there a moment ago",
                "The refrigeration stops",
            ],
            danger_level=0.9,
            fear_types=["body_horror", "psychological", "jumpscare"],
        )

        # Add more templates with similar detail...
        for st in SceneType:
            if st not in templates:
                templates[st] = SceneTemplate(
                    scene_type=st,
                    name=st.value.replace("_", " ").title(),
                    description=f"A {st.value.replace('_', ' ')} that defies normal description.",
                    sensory=SensoryDetail(
                        sound="Unsettling ambient sounds",
                        smell="Something wrong",
                        temperature="Uncomfortable",
                        light_level="Insufficient",
                    ),
                    danger_level=0.5,
                    fear_types=["psychological"],
                )

        return templates
