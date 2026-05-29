"""GameMaster Agent Loop — pydantic-ai integration for intelligent character creation.

Uses pydantic-ai agents with model-driven decision making:
- LLM-powered ideation (creative character concepts)
- Automatic genre/audience analysis
- Quality scoring and iteration
- Memory of previously created characters
- Cross-platform adaptation

The agent loop wraps the GameMasterAgent's template-based generation with
LLM reasoning for richer, more creative outputs.
"""

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Any

logger = logging.getLogger("gamemaster.agent_loop")

# Memory file for created characters
MEMORY_DIR = Path.home() / ".hermes" / "gamemaster_memory"
MEMORY_DIR.mkdir(parents=True, exist_ok=True)
CHARACTERS_FILE = MEMORY_DIR / "characters.json"


def load_character_memory() -> list[dict]:
    """Load previously created characters from memory."""
    if CHARACTERS_FILE.exists():
        try:
            return json.loads(CHARACTERS_FILE.read_text())
        except (json.JSONDecodeError, ValueError):
            return []
    return []


def save_character_memory(characters: list[dict]) -> None:
    """Save characters to memory file."""
    CHARACTERS_FILE.write_text(json.dumps(characters, indent=2, ensure_ascii=False))


def record_character(sheet: dict, platform: str = "caveduck") -> None:
    """Record a created character in memory for future reference."""
    characters = load_character_memory()
    record = {
        "name": sheet.get("name", "unknown"),
        "platform": platform,
        "genre": sheet.get("theme", sheet.get("genre", "unknown")),
        "tags": sheet.get("tags", []),
        "original_character": sheet.get("original_character", False),
        "created_at": datetime.utcnow().isoformat(),
        "production_type": sheet.get("production_type", "role-playing"),
    }
    characters.append(record)
    save_character_memory(characters)


def get_character_stats() -> dict[str, Any]:
    """Get statistics about created characters."""
    characters = load_character_memory()
    if not characters:
        return {"total": 0, "platforms": {}, "genres": {}}

    stats = {
        "total": len(characters),
        "platforms": {},
        "genres": {},
        "original_count": sum(1 for c in characters if c.get("original_character")),
    }
    for c in characters:
        p = c.get("platform", "unknown")
        stats["platforms"][p] = stats["platforms"].get(p, 0) + 1
        g = c.get("genre", "unknown")
        stats["genres"][g] = stats["genres"].get(g, 0) + 1
    return stats


def check_duplicate(name: str) -> dict | None:
    """Check if a character with the given name already exists."""
    characters = load_character_memory()
    for c in characters:
        if c.get("name", "").lower() == name.lower():
            return c
    return None


def score_character_sheet(sheet: dict) -> dict[str, Any]:
    """Score a character sheet on quality metrics.

    Based on Caveduck's official structure and best practices:
    - Hook quality (does the greeting grab attention?)
    - Description richness (are all fields filled?)
    - Tag optimization (are tags relevant and maxed out?)
    - Secret depth (does the secret add mystery?)
    - Writing style clarity (is the style prompt effective?)
    """
    score = 0
    max_score = 100
    feedback = []

    # Name (0-10)
    name = sheet.get("name", "")
    if len(name) > 0:
        score += 5
    if 2 <= len(name) <= 20:
        score += 5
        feedback.append("✅ Name length is ideal (2-20 chars)")
    elif len(name) > 20:
        feedback.append("⚠️ Name too long — consider a shorter, catchier name")

    # Description (0-25)
    desc = sheet.get("description", "")
    if len(desc) > 0:
        score += 5
    if len(desc) > 200:
        score += 10
        feedback.append("✅ Description has good detail")
    if len(desc) > 1000:
        score += 10
    if "{{user}}" in desc or "{{char}}" in desc:
        score += 5
        feedback.append("✅ Uses {{user}}/{{char}} placeholders")
    else:
        feedback.append("💡 Add {{user}} and {{char}} placeholders for better AI response")

    # Greeting variants (0-20)
    greetings = sheet.get("greeting_variants", [])
    if greetings:
        score += 7
    if len(greetings) >= 2:
        score += 6
        feedback.append("✅ Multiple greeting variants — great for different vibes")
    if len(greetings) >= 3:
        score += 7
        feedback.append("✅ Max greeting variants (3) — maximum entry points")

    # Secret (0-10)
    secret = sheet.get("secret", "")
    if secret and secret != "[Generate hidden secret":
        score += 10
        feedback.append("✅ Secret adds mystery and engagement")
    else:
        feedback.append("💡 Add a secret — characters with secrets get more chats")

    # Tags (0-15)
    tags = sheet.get("tags", [])
    if len(tags) >= 5:
        score += 8
    if len(tags) >= 8:
        score += 4
    if "Original" in tags:
        score += 3
        feedback.append("✅ Original tag — 6.6x more chats per character!")

    # Writing style (0-10)
    writing_style = sheet.get("writing_style", "")
    if writing_style:
        score += 5
    if len(writing_style) > 50:
        score += 5

    # Lorebook (0-5)
    lorebook = sheet.get("lorebook_keywords", "")
    if lorebook and not lorebook.startswith("[Generate"):
        score += 5

    # Variables (0-5)
    variables = sheet.get("variables", [])
    if variables:
        score += 5

    grade = (
        "S"
        if score >= 90
        else "A"
        if score >= 75
        else "B"
        if score >= 60
        else "C"
        if score >= 45
        else "D"
    )

    return {
        "score": score,
        "max_score": max_score,
        "grade": grade,
        "feedback": feedback,
        "recommendations": [
            "Register as Original Character for 6.6x more chats",
            "Add 3 greeting variants for different vibes",
            "Use {{user}} and {{char}} in all text fields",
            "Add secrets for mystery and engagement",
            "Lock 2-3 album images for incentive earnings",
            "Add Lorebook keywords (up to 100, 10 active per conversation)",
            "Set up to 3 variables for progression (Intimacy, Trust, Fear)",
        ],
    }


def generate_prompt_hints(sheet: dict) -> dict[str, str]:
    """Generate LLM-ready prompt hints for filling in template placeholders.

    These hints guide an LLM to fill in the [Generate...] placeholders
    in a character sheet with creative, cohesive content.
    """
    name = sheet.get("name", "the character")
    genre = sheet.get("genre", sheet.get("theme", "dark_fantasy"))
    species = sheet.get("species", "")
    power = sheet.get("power_dynamic", "")

    return {
        "description_hint": (
            f"Write a vivid, keyword-rich character description for {name}, "
            f"a {species} {power} in a {genre} setting. "
            f"Include: age (19+), nationality, appearance (hair, eyes, build), "
            f"distinguishing features, outfit style, personality traits, "
            f" backstory hints, and what makes them unique. "
            f"Use {{user}} and {{char}} placeholders. Max 10,000 chars."
        ),
        "greeting_hint": (
            f"Write 3 greeting variants for {name}. Each should be an immersive "
            f"opening that hooks the reader. Variant 1: Dramatic entrance. "
            f"Variant 2: Mysterious/intimate tone. Variant 3: Casual/unexpected "
            f"encounter. Show personality through dialogue and narration. "
            f"Max 10,000 chars each."
        ),
        "secret_hint": (
            f"Create a compelling secret for {name} that adds depth and mystery. "
            f"This should be information the character hides — a past trauma, "
            f"a forbidden desire, a hidden identity, or a dangerous knowledge. "
            f"Max 10,000 chars."
        ),
        "world_hint": (
            f"Describe the world {name} inhabits. What are the rules, conflicts, "
            f"and aesthetics of this {genre} setting? How does the character's "
            f"power dynamic ({power}) shape their place in this world? "
            f"Max 10,000 chars."
        ),
        "lorebook_hint": (
            f"Generate 15-20 Lorebook keywords for {name} with descriptions. "
            f"Use | for OR conditions. Example: 'manor|estate: The grand gothic "
            f"residence where {{char}} resides, filled with ancient secrets.' "
            f"Each entry should enrich the character's world."
        ),
        "variables_hint": (
            f"Design 3 character variables for {name}: "
            f"1. Intimacy (starts 0, increases with trust/tenderness, decreases with conflict). "
            f"2. A genre-appropriate variable (e.g., Corruption, Devotion, Fear). "
            f"3. A personality-specific variable (e.g., Sanity, Loyalty, Pride). "
            f"Define rules for increase/decrease and milestone thresholds."
        ),
    }
