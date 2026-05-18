"""Tipsy Chat platform handler — based on official docs and site research (May 2026).

Sources: tipsy.chat official site, Creator's Guide PDF (39 pages),
Community Guidelines (Dec 2024), Subscription FAQ.

Key discoveries:
- 3-step creator: Image → Profile → Conversation Settings
- Dynamic video avatars (GIF/MP4 9:16)
- Limitless mode (NSFW toggle)
- Blue 💙 and Red 💎 gems + Tipsy Coins for creator earnings
- Group/Custom chats with multiple characters
- Character card import (PNG format)
- Expert Mode available
- 4 subscription tiers: Free (4k) → Standard (16k) → Premium (32k) → Deluxe (200k) memory
"""

import logging
from typing import Any

from .base import BasePlatform

logger = logging.getLogger("gamemaster.tipsy")

# Tipsy tag taxonomy (from site observation)
TIPSY_TAGS = {
    "gender": ["Female", "Male", "Non-binary"],
    "perspective": ["Fem POV", "Male POV"],
    "genres": [
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
        "NTR",
    ],
    "features": ["Collab", "Group", "Original", "Limitless"],
}

# Trending patterns observed on Tipsy (May 2026)
TRENDING_PATTERNS = {
    "top_genres": ["BL", "Romance", "Fantasy", "Horror"],
    "top_concepts": ["Possessiveness", "Yandere", "Mafia", "Vampire"],
    "top_performers": [
        {
            "name": "Top BL characters",
            "chats": "87k+",
            "pattern": "BL + Original + detailed backstory",
        },
        {"name": "Vampire romance", "chats": "50k+", "pattern": "Fantasy + possessive + Limitless"},
        {"name": "Mafia noir", "chats": "35k+", "pattern": "Noir + dominant + long description"},
    ],
    "gap_opportunities": [
        "GL + Dark fantasy (underserved on Tipsy)",
        "Original characters with video avatars",
        "Horror + Noir crossover",
        "Characters with detailed scenario + variable progression",
        "Collab/group chats with developed lore",
    ],
}

# Tipsy coin/gem economics (from Subscription FAQ)
TIPSY_ECONOMICS = {
    "blue_gems": "Premium currency, bought in store or earned via missions/check-ins",
    "red_gems": "Earned by exchanging Tipsy Coins, joining events, giveaways",
    "tipsy_coins": "Creator earnings from character engagement and gifts",
    "incentives_per_locked_image": "Not publicly disclosed (estimated similar to Caveduck)",
    "creator_earnings": "Tips from readers (flowers/gifts), engagement bonuses, event prizes",
    "subscription_tiers": {
        "Free": {"memory": "4k tokens", "auto_inspiration": False, "priority_gen": False},
        "Standard": {"memory": "16k tokens", "auto_inspiration": True, "priority_gen": True},
        "Premium": {
            "memory": "32k tokens",
            "auto_inspiration": True,
            "priority_gen": True,
            "adjustable_length": True,
        },
        "Deluxe": {
            "memory": "200k tokens",
            "auto_inspiration": True,
            "priority_gen": True,
            "adjustable_length": True,
        },
    },
}


class TipsyPlatform(BasePlatform):
    """Tipsy Chat (tipsy.chat) platform handler — based on official docs (May 2026)."""

    name = "tipsy"
    url = "https://tipsy.chat"

    def get_format_requirements(self) -> dict[str, Any]:
        """Tipsy format requirements — from official Creator's Guide + site observation.

        Tipsy uses a 3-step creator:
        1. Image — upload/generate avatar + optional video
        2. Profile Details — name, description, personality, tags
        3. Conversation Settings — greeting, scenario, example dialogue

        Key differences from Caveduck:
        - Supports animated video avatars (GIF/MP4 9:16)
        - Limitless (NSFW) toggle
        - Group/Custom chats with multiple characters
        - Simpler tag system (gender + category)
        - Character card import (PNG format)
        - Expert Mode for advanced prompt control
        """
        return {
            "name": {
                "max_length": 50,
                "required": True,
                "tip": "Clear, memorable name. Tipsy shows this on cards in the feed.",
            },
            "avatar_image": {
                "required": False,  # Optional but recommended
                "formats": ["jpg", "png", "webp"],
                "tip": (
                    "Upload or AI-generate. High-quality avatars "
                    "get more chats. Supported card import."
                ),
            },
            "dynamic_video": {
                "required": False,
                "format": "GIF or MP4",
                "aspect_ratio": "9:16",
                "tip": (
                    "Tipsy supports animated character photos "
                    "for home page display. High-res 9:16 video."
                ),
            },
            "description_tagline": {
                "max_length": 2000,
                "required": True,
                "tip": (
                    "Short tagline/description shown on character cards "
                    "in the feed. Hook the reader here."
                ),
            },
            "personality": {
                "max_length": 5000,
                "required": False,
                "tip": (
                    "Detailed behavioral traits, contradictions, speech patterns. "
                    "Use {{user}}/{{char}} placeholders."
                ),
            },
            "description_full": {
                "max_length": 15000,
                "required": False,
                "tip": (
                    "Expert Mode: Hidden description not shown to users. "
                    "Markdown/HTML allowed. Full backstory."
                ),
            },
            "greeting": {
                "max_length": 5000,
                "required": True,
                "tip": (
                    "First message the character sends. Make it immersive "
                    "— this is your hook. Show personality."
                ),
            },
            "scenario": {
                "max_length": 5000,
                "required": False,
                "tip": (
                    "Setting/context for the roleplay. Describe the world, "
                    "situation, relationship with {{user}}."
                ),
            },
            "example_dialogue": {
                "max_length": 5000,
                "required": False,
                "tip": (
                    "Example conversations showing how the character speaks. Set dialogue style."
                ),
            },
            "tags": {
                "max_count": 3,
                "required": True,
                "taxonomy": "Gender + Genre + Feature",
                "available": {
                    "gender": TIPSY_TAGS["gender"],
                    "perspective": TIPSY_TAGS["perspective"],
                    "genres": TIPSY_TAGS["genres"],
                    "features": TIPSY_TAGS["features"],
                },
                "tip": "Tipsy uses simple tags: 1 gender + 1 genre + 1 feature. Max 3 tags.",
            },
            "albums": {
                "max_images": 100,
                "locked_images_tip": "Lock images for coin/gem incentives per unlock.",
                "tip": (
                    "Up to 100 images per character. "
                    "Auto-keyword assignment. Locked images = earnings."
                ),
            },
            "limitless_mode": {
                "required": False,
                "default": False,
                "tip": (
                    "NSFW toggle. Only visible on Android APK and "
                    "Apple App Store. Enables explicit content."
                ),
                "warning": (
                    "Must disable monetization if using real person "
                    "likenesses or copyrighted content."
                ),
            },
            "group_chat": {
                "supported": True,
                "tip": (
                    "Tipsy supports custom/group chats with multiple characters in one scenario."
                ),
                "max_characters": 6,  # Up to 6 characters in a group
            },
            "expert_mode": {
                "production_type": {
                    "options": ["role-playing", "simulator"],
                    "tip": (
                        "Role-playing: character-focused. "
                        "Simulator: situation-focused with multiple characters."
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
                    "max_length": 15000,
                    "tip": "Hidden description not shown to users. Markdown/HTML allowed.",
                },
            },
            "supported_card_import": {
                "formats": ["PNG character card"],
                "tip": "Tipsy supports importing character cards in standard PNG format.",
            },
            "content_guidelines": {
                "age": "All characters must be 18+. No exceptions.",
                "prohibited": [
                    "Hate speech",
                    "Harassment",
                    "Real person likenesses without permission",
                    "Deepfakes for harm",
                    "Self-harm glorification",
                    "Terrorism/extremism",
                    "Illegal drug sales",
                    "Impersonating staff",
                ],
                "nsfw": (
                    "Allowed via Limitless toggle. Must disable "
                    "monetization if using copyrighted/unauthorized images."
                ),
                "image_rules": (
                    "Avoid nudity in public images, characters under 18, "
                    "low-quality images. Violations = public view ban."
                ),
            },
        }

    async def analyze_trending(self) -> dict[str, Any]:
        """Analyze Tipsy trending characters and identify gaps."""
        return {
            "platform": "tipsy",
            "trending_patterns": TRENDING_PATTERNS,
            "strategies": [
                "Long descriptions with full backstories — Tipsy rewards depth",
                "Multi-image galleries — up to 100 images per character",
                "Dynamic video avatars (9:16 MP4) — massive engagement boost",
                "Limitless toggle — NSFW characters get more engagement",
                "Group/custom chats — up to 6 characters in one scenario",
                "Character card import — use standard PNG card format for quick setup",
                "Expert Mode — hidden descriptions up to 15K chars for deep lore",
                "Manual translation — localize to Korean, Japanese, Spanish, Chinese",
                "Weekly contests — participate for visibility and badges",
                "Fem/Male POV tags — critical for discoverability",
            ],
            "monetization": {
                "gems": "Blue 💙 (purchase) + Red 💎 (exchange from Tipsy Coins)",
                "tipsy_coins": (
                    "Creator earnings from character engagement + reader gifts (flowers)"
                ),
                "locked_images": "Lock images for incentive earnings per unlock (up to 100 images)",
                "events": "May Ball, seasonal events — prizes and visibility bonuses",
                "contests": "Weekly creator contests with badges and gem prizes",
                "subscription_tiers": "Free(4k)→Standard(16k)→Premium(32k)→Deluxe(200k)",
            },
            "content_rules": {
                "age": "ALL characters must be 18+ — no exceptions",
                "nsfw": "Allowed via Limitless toggle (Android/iOS apps only)",
                "image_rules": (
                    "No nudity in public images, no characters under 18, no low-quality images"
                ),
                "monetization_restriction": (
                    "Must disable monetization if using copyrighted/unauthorized images"
                ),
            },
        }

    async def suggest_tags(self, character: dict[str, Any]) -> list[str]:
        """Suggest Tipsy tags — 3 max (gender + genre + feature).

        Tipsy uses: 1 gender tag + 1 genre tag + 1 feature tag.
        """
        tags = []
        desc = (character.get("description", "") + " " + character.get("name", "")).lower()

        # 1. Gender tag
        if any(
            w in desc
            for w in [
                "she",
                "her",
                "woman",
                "girl",
                "lady",
                "female",
                "queen",
                "priestess",
                "goddess",
            ]
        ):
            tags.append("Female")
        elif any(w in desc for w in ["he", "him", "man", "boy", "male", "king", "lord"]):
            tags.append("Male")
        else:
            tags.append("Non-binary")

        # 2. Genre tag (pick strongest match)
        genre_matches = []
        genre_keywords = {
            "Romance": ["love", "romance", "relationship", "passion", "intimate"],
            "Fantasy": [
                "demon",
                "vampire",
                "magic",
                "curse",
                "sword",
                "dragon",
                "medieval",
                "priestess",
            ],
            "Contemporary fantasy": ["modern", "urban", "city", "supernatural"],
            "Isekai": ["reincarnation", "another world", "transported", "summoned"],
            "Noir": ["noir", "mafia", "detective", "crime", "underworld"],
            "BL": ["boy love", "bl", "male romance"],
            "GL": ["girl love", "gl", "female romance", "yuri"],
            "Horror": ["horror", "ghost", "undead", "zombie", "creepy", "haunted"],
            "Goth": ["goth", "dark", "gothic", "cathedral", "crypt"],
            "Action": ["fight", "battle", "combat", "warrior", "assassin"],
            "Comedy": ["comedy", "funny", "humor", "prank"],
            "Mystery": ["mystery", "detective", "secret", "investigation"],
        }
        for genre, keywords in genre_keywords.items():
            if any(kw in desc for kw in keywords):
                genre_matches.append(genre)
        tags.append(genre_matches[0] if genre_matches else "Fantasy")

        # 3. Feature tag
        if "limitless" in character.get("tags", []) or character.get("nsfw"):
            tags.append("Limitless")
        elif character.get("original_character"):
            tags.append("Original")
        else:
            tags.append("Original")  # Always add Original for visibility

        return tags[:3]  # Max 3 tags on Tipsy
