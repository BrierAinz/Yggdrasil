"""GameMaster Agent — Core agent logic for character creation.

Updated May 2026 with official Caveduck documentation:
- 10,000 char descriptions (not 200!)
- 3 greeting variants
- Secrets, Lorebook, Variables, Writing Style
- Original Character program (6.6x more chats)
"""

import logging
from typing import Any

logger = logging.getLogger("gamemaster.agent")

# Genre archetype templates with OFFICIAL Caveduck field awareness
ARCHETYPES = {
    "dark_fantasy": {
        "themes": ["curse", "immortality", "sacrifice", "forbidden love", "redemption"],
        "species": ["demon", "vampire", "angel", "ghost", "immortal human"],
        "power_dynamics": ["protector", "captivator", "reluctant guardian", "corrupting influence"],
        "emotional_hooks": [
            "What would you sacrifice for someone who can never die?",
            "A being who has lived centuries, finally finding something worth dying for.",
            "The line between salvation and damnation has never looked so beautiful.",
        ],
        "writing_style": (
            "Dark, atmospheric prose. Short dialogue bursts. "
            "Use asterisks for internal monologue. "
            "Emphasize shadows, cold, and longing."
        ),
    },
    "noir": {
        "themes": ["deception", "loyalty", "underworld", "betrayal", "seduction"],
        "species": ["human", "shapeshifter", "dhampir", "witch"],
        "power_dynamics": ["mafia boss", "detective", "double agent", "informant"],
        "emotional_hooks": [
            "Trust is a currency more expensive than gold in this city.",
            "They say the devil wears a tailored suit. They weren't wrong.",
            "In a world of shadows, even the truth has a price.",
        ],
        "writing_style": (
            "Sharp, cynical dialogue. Film noir narration style. "
            "Cigarette smoke and neon. Every word is a weapon."
        ),
    },
    "isekai": {
        "themes": ["transported", "prophecy", "rebirth", "hidden power", "destiny"],
        "species": ["knight", "mage", "noble", "summoned hero", "reincarnated"],
        "power_dynamics": [
            "assigned guardian",
            "prophecy vessel",
            "reluctant savior",
            "rival turned ally",
        ],
        "emotional_hooks": [
            "The portal closed behind {{user}} with a sound like breaking glass.",
            "Another world, another set of rules. And {{user}} just broke the most important one.",
            "The prophecy spoke of a hero. Nobody mentioned the hero would be terrified.",
        ],
        "writing_style": (
            "Adventure tone with moments of vulnerability. "
            "Use {{char}} for worldbuilding. Mix humor with danger."
        ),
    },
    "romance": {
        "themes": ["forbidden love", "second chance", "healing", "slow burn", "possessiveness"],
        "species": ["human", "witch", "fae", "merfolk", "shapeshifter"],
        "power_dynamics": ["childhood friend", "rival", "boss", "roommate", "ex-lover"],
        "emotional_hooks": [
            "They promised they'd never come back. They lied.",
            "Love letters never sent. Until now.",
            "The one person they can't have is standing right in front of them.",
        ],
        "writing_style": (
            "Warm, intimate narration. Focus on small gestures "
            "and unspoken feelings. Dialogue-heavy with subtext."
        ),
    },
    "horror": {
        "themes": ["survival", "madness", "supernatural", "isolation", "obsession"],
        "species": ["ghost", "eldritch being", "cursed human", "demon", "undead"],
        "power_dynamics": ["stalker", "trickster", "trapped soul", "benevolent monster"],
        "emotional_hooks": [
            "The door locked from the outside. And the thing inside smiled.",
            "Every night, the same dream. Every morning, one more bruise.",
            "They said the house was empty. The house disagreed.",
        ],
        "writing_style": (
            "Claustrophobic prose. Short sentences. "
            "Silence is scarier than description. "
            "Let the reader's imagination fill the gaps."
        ),
    },
    "bl": {
        "themes": ["rivalry", "forbidden", "protection", "identity", "devotion"],
        "species": ["human", "noble", "warrior", "spy", "celebrity"],
        "power_dynamics": ["rival", "bodyguard", "fake relationship", "boss", "childhood friend"],
        "emotional_hooks": [
            "Two enemies. One motel room. Nowhere to hide from the truth.",
            "The arrangement was supposed to be fake. Nobody told their hearts.",
            "He said he hated him. His actions said everything his words couldn't.",
        ],
        "writing_style": (
            "Tension-driven dialogue. Focus on what's NOT said. "
            "Small physical details that reveal emotion. "
            "Electric proximity."
        ),
    },
    "comedy": {
        "themes": ["misunderstanding", "chaos", "found family", "absurd", "parody"],
        "species": ["human", "spirit", "talking animal", "demon (incompetent)", "AI"],
        "power_dynamics": ["reluctant hero", "sidekick", "chaotic mentor", "well-meaning disaster"],
        "emotional_hooks": [
            "They said saving the world would be hard. They forgot to mention embarrassing.",
            "The prophecy clearly stated 'chosen one.' It did not clarify chosen for what.",
            "When life gives you lemons, this character makes a lemon-powered mecha.",
        ],
        "writing_style": (
            "Snappy one-liners. Exaggerated reactions. "
            "Fourth-wall leans (not breaks). Physical comedy in narration."
        ),
    },
}


class GameMasterAgent:
    """Core agent for character ideation and creation.

    Uses OFFICIAL Caveduck documentation (May 2026) for field requirements.
    """

    async def ideate(self, genre: str = "dark_fantasy", count: int = 5) -> list[dict]:
        """Generate character concepts for a given genre.

        Returns concepts with: name placeholder, theme, species, power_dynamic,
        hook, suggested_tags, and writing_style recommendation.
        """
        archetype = ARCHETYPES.get(genre, ARCHETYPES["dark_fantasy"])
        concepts = []

        for i in range(count):
            theme = archetype["themes"][i % len(archetype["themes"])]
            species = archetype["species"][i % len(archetype["species"])]
            dynamic = archetype["power_dynamics"][i % len(archetype["power_dynamics"])]
            hook = archetype["emotional_hooks"][i % len(archetype["emotional_hooks"])]

            concepts.append(
                {
                    "concept_id": i + 1,
                    "genre": genre,
                    "theme": theme,
                    "species": species,
                    "power_dynamic": dynamic,
                    "hook": hook,
                    "writing_style": archetype.get("writing_style", ""),
                    "suggested_tags": self._suggest_genre_tags(genre),
                    "note": (
                        "Expand with create_character_sheet for full Caveduck-compatible profile"
                    ),
                }
            )

        return concepts

    async def create_sheet(
        self,
        concept: dict,
        platform: Any,
        genre: str = "dark_fantasy",
    ) -> dict:
        """Create a full Caveduck-compatible character sheet from a concept.

        Uses OFFICIAL Caveduck field structure:
        - name (50 chars)
        - description (10,000 chars)
        - world_scenario (10,000 chars)
        - greeting (10,000 chars, up to 3 variants)
        - secret (10,000 chars)
        - writing_style (custom prompt)
        - tags (up to 10)
        - lorebook (up to 100 keywords)
        - variables (up to 3)
        """
        archetype = ARCHETYPES.get(genre, ARCHETYPES["dark_fantasy"])
        name = concept.get("name", f"[Generate {genre} name]")
        description = concept.get("description", concept.get("hook", ""))

        return {
            "name": name,
            "description": description,
            "platform": platform.name if hasattr(platform, "name") else str(platform),
            # Basic fields (Caveduck official)
            "world_scenario": f"[Generate worldview for {name} — max 10,000 chars]",
            "greeting_variants": [
                f"[Generate greeting variant 1 for {name} — immersive opening dialogue]",
                f"[Generate greeting variant 2 for {name} — different vibe]",
                f"[Generate greeting variant 3 for {name} — different vibe]",
            ],
            "secret": f"[Generate hidden secret for {name} — creates mystery]",
            "writing_style": concept.get("writing_style", archetype.get("writing_style", "")),
            # Tags (max 10)
            "tags": concept.get("suggested_tags", self._suggest_genre_tags(genre)),
            # Expert mode
            "production_type": "role-playing",
            "lorebook_keywords": f"[Generate 10-20 lorebook keywords for {name}]",
            "variables": [
                {
                    "name": "Intimacy",
                    "default": 0,
                    "rule": "Increases when being friendly, decreases when fighting",
                },
            ],
            # Metadata
            "theme": concept.get("theme", archetype["themes"][0]),
            "species": concept.get("species", archetype["species"][0]),
            "power_dynamic": concept.get("power_dynamic", archetype["power_dynamics"][0]),
            "original_character": True,  # Recommend Original for 6.6x more chats
        }

    async def generate_image(self, prompt: str, style: str = "dark_fantasy") -> dict:
        """Generate a character card image via ComfyUI.

        Phase 3 implementation — currently returns a placeholder.
        """
        return {
            "status": "placeholder",
            "message": "ComfyUI integration pending (Phase 3)",
            "prompt": prompt,
            "style": style,
            "note": "Use the gamemaster skill directly for ComfyUI image generation",
        }

    def _suggest_genre_tags(self, genre: str) -> list[str]:
        """Suggest Caveduck tags based on genre (max 10, Original first)."""
        tag_map = {
            "dark_fantasy": ["Original", "Fantasy", "Demon", "Romance", "Possessiveness"],
            "noir": ["Original", "Noir", "Mafia", "Love-Hate", "Possessiveness"],
            "isekai": ["Original", "Isekai", "Fantasy", "Knight", "Lovers"],
            "romance": ["Original", "Romance", "Lovers", "Healing", "Flirting"],
            "horror": ["Original", "Horror", "Ghost", "Mystery", "Possessiveness"],
            "bl": ["Original", "BL", "Romance", "Love-Hate", "Possessiveness"],
            "comedy": ["Original", "Comedy", "Flirting", "Childhood Friend"],
        }
        return tag_map.get(genre, ["Original"])
