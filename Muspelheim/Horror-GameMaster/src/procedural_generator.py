"""Procedural Generator — Generates horror content procedurally"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Optional
import random


class SceneType(Enum):
    """Types of horror scenes"""
    DARK_CORRIDOR = "dark_corridor"
    ABANDONED_ROOM = "abandoned_room"
    MIRROR_MAZE = "mirror_maze"
    BASEMENT = "basement"
    ATTIC = "attic"
    FOREST = "forest"
    HOSPITAL = "hospital"
    HOUSE = "house"


class EventType(Enum):
    """Types of horror events"""
    DOOR_CLOSES = "door_closes"
    LIGHTS_OFF = "lights_off"
    WHISPER = "whisper"
    SHADOW_MOVES = "shadow_moves"
    OBJECT_FALLS = "object_falls"
    FOOTSTEPS = "footsteps"
    BREATHING = "breathing"
    PHONE_RINGS = "phone_rings"


class NPCType(Enum):
    """Types of horror NPCs"""
    GHOST = "ghost"
    POSSESSED = "possessed"
    STRANGER = "stranger"
    CHILD = "child"
    DOPPELGANGER = "doppelganger"
    SHADOW = "shadow"


@dataclass
class HorrorScene:
    """A procedurally generated horror scene"""
    scene_type: SceneType
    description: str
    atmosphere: str
    events: list[EventType] = field(default_factory=list)
    npcs: list[NPCType] = field(default_factory=list)
    tension_level: float = 0.5
    
    def to_dict(self) -> dict:
        return {
            "scene_type": self.scene_type.value,
            "description": self.description,
            "atmosphere": self.atmosphere,
            "events": [e.value for e in self.events],
            "npcs": [n.value for n in self.npcs],
            "tension_level": self.tension_level,
        }


class ProceduralGenerator:
    """Generates horror content procedurally"""
    
    def __init__(self):
        self.scene_templates = {
            SceneType.DARK_CORRIDOR: {
                "descriptions": [
                    "A long, narrow corridor stretches into darkness. The walls seem to breathe.",
                    "The hallway is impossibly long. Your footsteps echo back, but with a delay.",
                    "Peeling wallpaper reveals something dark underneath. The air smells of copper.",
                ],
                "atmospheres": [
                    "The only light comes from a flickering bulb that casts dancing shadows.",
                    "Complete darkness. You can hear something moving ahead of you.",
                    "A cold draft carries whispers that seem to come from everywhere.",
                ],
            },
            SceneType.ABANDONED_ROOM: {
                "descriptions": [
                    "A room frozen in time. Dust covers everything. Something sits in the corner.",
                    "The furniture is arranged as if waiting for guests who never came.",
                    "Children's drawings cover the walls. All of them depict the same figure.",
                ],
                "atmospheres": [
                    "The clock on the wall ticks backwards.",
                    "A music box plays a tune you recognize but can't place.",
                    "The mirror reflects a room that's slightly different from this one.",
                ],
            },
            SceneType.MIRROR_MAZE: {
                "descriptions": [
                    "Mirrors everywhere. Your reflections don't quite match your movements.",
                    "The maze shifts when you're not looking. Paths appear and disappear.",
                    "In every mirror, you see yourself — but older, or younger, or wrong.",
                ],
                "atmospheres": [
                    "Your reflection smiles when you don't.",
                    "One mirror shows the room behind you, but there's someone standing there.",
                    "The reflections are getting closer, even when you stand still.",
                ],
            },
        }
        
        self.event_templates = {
            EventType.DOOR_CLOSES: "A door slams shut behind you. The sound echoes.",
            EventType.LIGHTS_OFF: "The lights flicker and die. Darkness rushes in.",
            EventType.WHISPER: "A whisper brushes your ear: '{whisper_text}'",
            EventType.SHADOW_MOVES: "Something moves in your peripheral vision.",
            EventType.OBJECT_FALLS: "Something falls in the next room. Then silence.",
            EventType.FOOTSTEPS: "Footsteps behind you. They stop when you stop.",
            EventType.BREATHING: "You hear breathing that isn't yours.",
            EventType.PHONE_RINGS: "A phone rings in the distance. No one answers.",
        }
        
        self.whisper_texts = [
            "I see you",
            "Don't turn around",
            "You shouldn't have come here",
            "It knows you're here",
            "Run",
            "You can't leave",
            "I've been waiting",
            "Look behind you",
        ]
    
    def generate_scene(
        self,
        scene_type: Optional[SceneType] = None,
        tension_level: float = 0.5,
        dominant_fear: Optional[str] = None,
    ) -> HorrorScene:
        """Generate a procedural horror scene"""
        if scene_type is None:
            scene_type = random.choice(list(SceneType))
        
        templates = self.scene_templates.get(scene_type, self.scene_templates[SceneType.DARK_CORRIDOR])
        
        description = random.choice(templates["descriptions"])
        atmosphere = random.choice(templates["atmospheres"])
        
        # Add events based on tension
        num_events = max(1, int(tension_level * 3))
        events = random.sample(list(EventType), min(num_events, len(EventType)))
        
        # Add NPCs based on tension
        npcs = []
        if tension_level > 0.7:
            npcs.append(random.choice(list(NPCType)))
        
        return HorrorScene(
            scene_type=scene_type,
            description=description,
            atmosphere=atmosphere,
            events=events,
            npcs=npcs,
            tension_level=tension_level,
        )
    
    def generate_event(self, event_type: Optional[EventType] = None) -> str:
        """Generate a horror event description"""
        if event_type is None:
            event_type = random.choice(list(EventType))
        
        template = self.event_templates[event_type]
        
        if "{whisper_text}" in template:
            template = template.replace("{whisper_text}", random.choice(self.whisper_texts))
        
        return template
    
    def generate_npc_dialogue(self, npc_type: NPCType) -> str:
        """Generate NPC dialogue"""
        dialogues = {
            NPCType.GHOST: [
                "You can see me, can't you?",
                "I've been here so long...",
                "Please, help me remember...",
            ],
            NPCType.POSSESSED: [
                "It's so cold in here.",
                "I can feel it watching.",
                "Don't listen to the walls.",
            ],
            NPCType.STRANGER: [
                "You look lost. I can help you.",
                "I know the way out. Follow me.",
                "We've met before, haven't we?",
            ],
            NPCType.CHILD: [
                "Will you play with me?",
                "I drew this for you.",
                "The man in the dark says hello.",
            ],
            NPCType.DOPPELGANGER: [
                "I'm you. From the other side.",
                "Don't you recognize yourself?",
                "We're the same, you and I.",
            ],
            NPCType.SHADOW: [
                "...",
                "*silence*",
                "*whispers*",
            ],
        }
        
        return random.choice(dialogues.get(NPCType.STRANGER, ["..."]))
