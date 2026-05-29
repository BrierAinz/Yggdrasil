"""GameMaster MCP Server — FastMCP server exposing character creation tools."""

from fastmcp import FastMCP

from .agent import GameMasterAgent
from .agent_loop import (
    check_duplicate,
    generate_prompt_hints,
    get_character_stats,
    record_character,
    score_character_sheet,
)
from .comfyui import (
    CHECKPOINTS,
    generate_character_card,
    get_available_checkpoints,
)
from .platforms import CaveduckPlatform, TipsyPlatform

mcp = FastMCP(
    name="gamemaster",
    version="0.2.0",
)

agent = GameMasterAgent()

# Platform registry
PLATFORMS = {
    "caveduck": CaveduckPlatform(),
    "tipsy": TipsyPlatform(),
}


@mcp.tool()
async def ideate_characters(genre: str = "dark_fantasy", count: int = 5) -> list[dict]:
    """Generate character concepts for AI chat platforms.

    Args:
        genre: Genre archetype (dark_fantasy, noir, isekai, romance, horror, bl, comedy)
        count: Number of concepts to generate (1-10)

    Returns:
        List of character concepts with name, description, hooks, and suggested tags
    """
    return await agent.ideate(genre=genre, count=min(count, 10))


@mcp.tool()
async def create_character_sheet(
    concept: dict,
    platform: str = "caveduck",
    genre: str = "dark_fantasy",
) -> dict:
    """Create a full character sheet for an AI chat platform.

    Args:
        concept: Character concept from ideate_characters or custom dict with name/description
        platform: Target platform (caveduck, tipsy)
        genre: Genre archetype for prompt framing

    Returns:
        Complete character sheet: name, description, greeting variants, secrets,
        writing_style, tags, lorebook, variables (Caveduck official format)
    """
    platform_handler = PLATFORMS.get(platform, PLATFORMS["caveduck"])
    return await agent.create_sheet(concept=concept, platform=platform_handler, genre=genre)


@mcp.tool()
async def analyze_trending(platform: str = "caveduck") -> dict:
    """Analyze trending characters on a platform and identify gaps.

    Args:
        platform: Platform to analyze (caveduck, tipsy)

    Returns:
        Trending analysis: top genres, popular tags, gap opportunities,
        monetization info, content rules, recommended strategies
    """
    platform_handler = PLATFORMS.get(platform, PLATFORMS["caveduck"])
    return await platform_handler.analyze_trending()


@mcp.tool()
async def suggest_tags(character: dict, platform: str = "caveduck") -> list[str]:
    """Suggest optimal tags for a character on a specific platform.

    Args:
        character: Character dict with at least 'name' and 'description' keys
        platform: Target platform (caveduck, tipsy)

    Returns:
        List of recommended tags ordered by relevance and visibility potential
    """
    platform_handler = PLATFORMS.get(platform, PLATFORMS["caveduck"])
    return await platform_handler.suggest_tags(character)


@mcp.tool()
async def generate_character_image(
    prompt: str,
    style: str = "dark_fantasy",
    checkpoint: str = "flux_dev_q8",
    card_type: str = "caveduck_profile",
    seed: int | None = None,
) -> dict:
    """Generate a character card image via ComfyUI.

    Args:
        prompt: Visual description of the character for image generation
        style: Art style preset (dark_fantasy, noir, anime, photorealistic)
        checkpoint: Checkpoint to use (flux_dev_q8, unstable_evolution_xxx, getphat_reality_xxx)
        card_type: Card size format
            (caveduck_profile, caveduck_album, tipsy_profile, reference_sheet)
        seed: Optional seed for reproducibility (random if not set)

    Returns:
        Dict with status, prompt_id, output file paths, and generation metadata.
        ComfyUI must be running on localhost:8188.
    """
    return await generate_character_card(
        prompt=prompt,
        style=style,
        checkpoint=checkpoint,
        card_type=card_type,
        seed=seed,
    )


@mcp.tool()
async def list_available_checkpoints() -> dict:
    """List available ComfyUI checkpoints for image generation.

    Returns:
        Dict with available checkpoint names, descriptions, VRAM requirements,
        and whether they are SFW or NSFW.
    """
    online = await get_available_checkpoints()
    result = {
        "status": online.get("status", "unknown"),
        "checkpoints": {},
    }
    for name, info in CHECKPOINTS.items():
        result["checkpoints"][name] = {
            "filename": info["filename"],
            "description": info["description"],
            "vram_gb": info["vram_gb"],
            "type": info["type"],
            "sfw": "xxx" not in name,
        }
    if online.get("status") == "ok":
        result["currently_loaded"] = online.get("checkpoints", [])
    return result


@mcp.tool()
async def get_platform_requirements(platform: str = "caveduck") -> dict:
    """Get the official format requirements for a platform.

    Args:
        platform: Platform name (caveduck, tipsy)

    Returns:
        Complete format requirements including field lengths, required/optional,
        tips, and expert mode features (based on official documentation)
    """
    platform_handler = PLATFORMS.get(platform, PLATFORMS["caveduck"])
    return platform_handler.get_format_requirements()


@mcp.tool()
async def score_character(character_sheet: dict) -> dict:
    """Score a character sheet on quality metrics (0-100 scale, S/A/B/C/D grade).

    Evaluates: name quality, description richness, greeting hook power,
    tag optimization, secret depth, writing style, lorebook, variables.

    Args:
        character_sheet: Complete character sheet from create_character_sheet

    Returns:
        Score (0-100), grade (S/A/B/C/D), feedback list, and improvement recommendations
    """
    return score_character_sheet(character_sheet)


@mcp.tool()
async def get_prompt_hints(character_sheet: dict) -> dict:
    """Generate LLM-ready prompt hints for filling character sheet templates.

    Takes a character sheet with [Generate...] placeholders and returns
    detailed prompts that guide an LLM to fill in creative, cohesive content.

    Args:
        character_sheet: Character sheet with template placeholders

    Returns:
        Dict of prompt hints for each field
        (description, greetings, secret, world, lorebook, variables)
    """
    return generate_prompt_hints(character_sheet)


@mcp.tool()
async def check_character_exists(name: str) -> dict:
    """Check if a character with the given name has already been created.

    Args:
        name: Character name to check (case-insensitive)

    Returns:
        Dict with 'exists' boolean and character record if found, or empty record
    """
    existing = check_duplicate(name)
    if existing:
        return {"exists": True, "character": existing}
    return {"exists": False, "character": None}


@mcp.tool()
async def get_creation_stats() -> dict:
    """Get statistics about all characters created through GameMaster.

    Returns:
        Total character count, platform breakdown, genre distribution, original count
    """
    return get_character_stats()


@mcp.tool()
async def register_character(character_sheet: dict, platform: str = "caveduck") -> dict:
    """Register a completed character in GameMaster memory.

    Call this after finalizing a character sheet to track it for future reference
    and avoid creating duplicate characters.

    Args:
        character_sheet: Completed character sheet to register
        platform: Platform the character is for (caveduck, tipsy)

    Returns:
        Confirmation dict with character name and total registered count
    """
    record_character(character_sheet, platform=platform)
    stats = get_character_stats()
    return {
        "registered": character_sheet.get("name", "unknown"),
        "platform": platform,
        "total_registered": stats["total"],
    }


def main():
    mcp.run()


if __name__ == "__main__":
    main()
