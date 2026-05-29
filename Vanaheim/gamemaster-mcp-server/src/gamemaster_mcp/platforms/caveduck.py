"""Caveduck platform handler — based on OFFICIAL docs (docs.caveduck.io).

Updated May 2026 with real field lengths, expert mode features, incentive program,
and content guidelines from official documentation.
"""

import logging
from typing import Any

from .base import BasePlatform

logger = logging.getLogger("gamemaster.caveduck")

# Caveduck tag taxonomy (May 2026 — official)
CAVEDUCK_GENRES = [
    "Romance",
    "Fantasy",
    "Contemporary fantasy",
    "Isekai",
    "Noir",
    "Comedy",
    "Horror",
    "BL",
    "GL",
    "Goth",
    "Mystery",
    "Action",
    "Adventure",
]

CAVEDUCK_CONCEPTS = [
    "Mafia",
    "Detective",
    "Knight",
    "Emperor",
    "Demon",
    "Vampire",
    "Angel",
    "Ghost",
    "Elf",
    "Yandere",
    "Tsundere",
    "Kuudere",
]

CAVEDUCK_RELATIONS = [
    "Lovers",
    "Love-Hate",
    "Possessiveness",
    "Unrequited Love",
    "Flirting",
    "Childhood Friend",
]

# Trending patterns (researched May 2026)
TRENDING_PATTERNS = {
    "top_genres": ["BL", "Noir", "Romance", "Fantasy"],
    "top_concepts": ["Possessiveness", "Yandere", "Mafia"],
    "top_performers": [
        {"name": "Two Killer Daddies", "chats": 35000, "pattern": "BL + Original + drama"},
        {"name": "The Leak", "chats": 14700, "pattern": "Superpowers + dark"},
        {"name": "Dance with a Corpse", "chats": 10700, "pattern": "Horror/fantasy"},
        {"name": "Hail", "chats": 10100, "pattern": "Romance + possessive quote"},
        {"name": "Baiye", "chats": 9400, "pattern": "Romance + poetic"},
    ],
    "gap_opportunities": [
        "GL + Dark fantasy (underserved)",
        "Comedy + Isekai (growing trend)",
        "Horror + Noir crossover (unique niche)",
        "Original characters with Korean/noir aesthetic (proven demand)",
    ],
}

# Content guidelines (CRITICAL for automation)
PROHIBITED_CONTENT = [
    "minors_sexual",  # Under 19 in sexual/romantic contexts
    "perceived_minors",  # School uniforms, classrooms, child-like appearance
    "real_people_sexual",  # Real people photos must be SFW
    "copyright_no_monetize",  # Third-party IP = disable monetization
    "sexual_violence",  # Rape, gang rape depictions
    "bestiality",  # Sexual acts between humans and animals
    "discrimination",  # Based on gender, religion, disability, etc.
]

SFW_PROHIBITED = [
    "sexual_content",  # Any sexual depiction
    "prostitution_refs",  # Sex workers, escorts, nightlife
    "seduction_mechanics",  # Pheromones, hypnosis, forced seduction
    "body_fluids_excessive",  # Excessive saliva, sweat descriptions
    "body_part_emphasis",  # Emphasis on specific body parts including feet
    "genital_refs",  # References to genitalia or pubic hair
]

NSFW_PROFILE_RULES = [
    "no_explicit_sexual_acts",  # No intercourse depictions
    "no_nipples_female",  # Female nipple exposure not allowed
    "no_genital_exposure",  # Must be censored
]

NSFW_ALBUM_RULES = [
    "censor_genitals",  # Genitals/pubic hair/anus must be censored
    "no_blur_see_through",  # Mosaic/blur/see-through that reveals details not allowed
    "no_skin_tone_censor",  # Skin-tone-like censorship not allowed
    "no_excessive_contact_realistic",  # No explicit content in realistic motion images
]


class CaveduckPlatform(BasePlatform):
    """Caveduck.io platform handler — based on official docs (May 2026).

    Key features discovered from official documentation:
    - 10,000 char description (not 200!)
    - 3 greeting variants
    - 10,000 char secrets
    - 10,000 char writing style prompts
    - 100 lorebook keywords (10 active per conversation)
    - 3 variables per character
    - Original Character program (6.6x more chats)
    - Cash withdrawal at 20K incentives = $100 USDC
    """

    name = "caveduck"
    url = "https://caveduck.io"

    def get_format_requirements(self) -> dict[str, Any]:
        """Caveduck official format requirements from docs.caveduck.io."""
        return {
            "name": {
                "max_length": 50,
                "required": True,
                "tip": (
                    "Use clear, internationally recognizable names. "
                    "Short like 'Jenny' or 'Eugene'."
                    " Avoid ambiguous names like 'Bora' or 'Mirae' that could mistranslate."
                ),
            },
            "description": {
                "max_length": 10_000,
                "required": True,
                "tip": (
                    "Describe age, country, appearance, outfit, personality, "
                    "hobbies in keywords."
                    " Focus on keywords for token efficiency. "
                    "Use {{user}} and {{char}} placeholders."
                ),
            },
            "world_scenario": {
                "max_length": 10_000,
                "required": False,
                "title_max": 60,
                "tip": "Worldview or background story. Multiple characters can share the same"
                " worldview via Worldview Management.",
            },
            "greeting": {
                "max_length": 10_000,
                "required": True,
                "max_variants": 3,
                "tip": "Up to 3 different introductions for different vibes."
                " Show off the character's personality. This is the hook!",
            },
            "secret": {
                "max_length": 10_000,
                "required": False,
                "tip": "Hidden info not revealed to user. Creates mystery and attractiveness."
                " The character can sometimes conceal this information.",
            },
            "writing_style": {
                "max_length": None,
                "required": False,
                "tip": "Even 1-2 sentences work. Examples: 'Use natural conversational speech.'"
                " 'Wrap narration in asterisks, dialogue in quotation marks.'",
            },
            "example_dialogue": {
                "required": False,
                "tip": (
                    "Focus on character's way of speaking. "
                    "Set dialogues character is likely to say."
                ),
            },
            "tags": {
                "max_count": 10,
                "required": True,
                "taxonomy": {
                    "genres": CAVEDUCK_GENRES,
                    "concepts": CAVEDUCK_CONCEPTS,
                    "relations": CAVEDUCK_RELATIONS,
                },
            },
            "album_images": {
                "max_count": 100,
                "tip": "Auto-keyword assigned. Keep keywords unified (e.g., 'smile' not 'smile1')."
                " Locked images earn 25 incentive per unlock.",
            },
            "super_voice": {
                "tip": "Set a voice for the character. Users pay 8🪽 to listen."
                " Creator earns 0.8 incentive per play.",
            },
            "one_line_introduction": {
                "required": False,
                "tip": "Brief intro for search/main page display.",
            },
            "related_characters": {
                "max_count": 6,
                "tip": "Link your own characters as recommendations.",
            },
            "original_character": {
                "tip": "Register as Original for 6.6x more chats and higher incentive rates."
                " Cannot be turned off for 3 months. Cannot upload to external platforms.",
            },
            "monetization_restriction": {
                "tip": "Must disable if: copyrighted images, sexual content, or real person based.",
            },
            # Expert mode features
            "expert_mode": {
                "production_type": {
                    "options": ["role-playing", "simulator"],
                    "tip": (
                        "Role-playing: character-focused drama. "
                        "Simulator: situation-focused, multiple chars."
                    ),
                },
                "manual_translation": {
                    "languages": [
                        "Korean",
                        "English",
                        "Japanese",
                        "Spanish",
                        "Chinese (Traditional)",
                    ],
                    "tip": (
                        "Auto-translates to other languages. "
                        "Manual edit recommended for natural expressions."
                    ),
                },
                "user_specific_description": {
                    "max_length": 15_000,
                    "tip": "Hidden description not shown to users. Markdown/HTML allowed.",
                },
                "lorebook": {
                    "max_keywords": 100,
                    "max_active": 10,
                    "tip": "Keyword book triggered during conversations. Use | for OR conditions.",
                },
                "variables": {
                    "max_count": 3,
                    "tip": (
                        "Set default value per introduction. "
                        "E.g., 'Intimacy' increases when friendly,"
                        " decreases when fighting."
                    ),
                },
            },
        }

    async def analyze_trending(self) -> dict[str, Any]:
        """Analyze Caveduck trending characters and identify gaps."""
        return {
            "platform": "caveduck",
            "trending_patterns": TRENDING_PATTERNS,
            "strategies": [
                "REGISTER AS ORIGINAL — 6.6x more chats (1,061 avg vs 161)",
                "Use {{user}} and {{char}} placeholders in all text fields",
                "Hook descriptions with evocative quotes — first impressions matter",
                "3 greetings with different vibes — maximize entry points",
                "Add secrets — mystery = engagement = more chats",
                "Lorebook with 10+ keywords — character feels more alive",
                "Writing style prompt — 1-2 sentences can define entire personality",
                "Lock 2-3 album images — 25 incentive per unlock",
                "Korean/noir aesthetic — proven demand in user base",
                "Animated GIF cards — higher click-through than static images",
                "Variables (up to 3) — Intimacy/Trust/Fear create progression",
            ],
            "monetization": {
                "chat_opus": "4 incentive/conversation (2.2 for Original)",
                "chat_sonnet": "1 incentive/conversation (1.1 for Original)",
                "chat_gemini": "0.8 per conversation (0.9 for Original)",
                "image_unlock": "25 incentive per unlock",
                "story_chapter": "10 incentive per view",
                "super_voice": "0.8 incentive per play",
                "friend_referral": "100 incentive per signup",
                "cash_withdrawal": "20,000 incentives = $100 USDC (minimum)",
            },
            "content_rules": {
                "prohibited": PROHIBITED_CONTENT,
                "sfw_prohibited": SFW_PROHIBITED,
                "nsfw_profile": NSFW_PROFILE_RULES,
                "nsfw_album": NSFW_ALBUM_RULES,
                "critical": (
                    "All NSFW characters must be defined as 19+ adults. Minors = immediate removal."
                ),
            },
        }

    async def suggest_tags(self, character: dict[str, Any]) -> list[str]:
        """Suggest Caveduck tags based on character traits and genre.

        Prioritizes: Original tag (always first) > Genre > Concept > Relations, max 10.
        """
        tags = ["Original"]  # Always recommend Original for 6.6x more chats

        desc = (character.get("description", "") + " " + character.get("name", "")).lower()

        # Genre tags
        if any(
            w in desc
            for w in ["demon", "vampire", "angel", "curse", "immortal", "magic", "elf", "dark"]
        ):
            tags.append("Fantasy")
        elif any(w in desc for w in ["mafia", "detective", "underworld", "crime", "noir"]):
            tags.append("Noir")
        elif any(w in desc for w in ["isekai", "transported", "another world", "reborn"]):
            tags.append("Isekai")
        elif any(w in desc for w in ["horror", "ghost", "dead", "undead", "corpse"]):
            tags.append("Horror")
        elif any(w in desc for w in ["love", "romance", "relationship", "heart"]):
            tags.append("Romance")

        # Concept tags
        if any(w in desc for w in ["possessive", "obsessive", "mine", "jealous"]):
            tags.append("Possessiveness")
        elif any(w in desc for w in ["cold", "distant", "ice", "stoic"]):
            tags.append("Kuudere")
        elif any(w in desc for w in ["hot", "cold", "switch", "tsun"]):
            tags.append("Tsundere")
        elif any(w in desc for w in ["obsessive", "stalk", "yandere"]):
            tags.append("Yandere")

        # Relation tags
        if any(w in desc for w in ["enemy", "rival", "hate", "against"]):
            tags.append("Love-Hate")
        elif any(w in desc for w in ["protect", "guard", "shield", "save"]):
            tags.append("Lovers")
        elif any(w in desc for w in ["childhood", "grew up", "always known"]):
            tags.append("Childhood Friend")

        # BL/GL tags
        if any(w in desc for w in ["he", "him", "male", "boy", "man"]) and any(
            w in desc for w in ["love", "romance", "relationship"]
        ):
            if "she" not in desc and "her" not in desc:
                tags.append("BL")

        return tags[:10]  # Max 10 tags
