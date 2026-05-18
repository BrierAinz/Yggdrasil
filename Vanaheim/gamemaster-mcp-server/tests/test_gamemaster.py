"""Tests for GameMaster MCP Server — unit tests for agent, platforms, and ComfyUI."""

import pytest

from gamemaster_mcp.agent import ARCHETYPES, GameMasterAgent
from gamemaster_mcp.comfyui import (
    CARD_SIZES,
    CHECKPOINTS,
    STYLE_PRESETS,
    build_character_card_workflow,
)
from gamemaster_mcp.platforms.base import BasePlatform
from gamemaster_mcp.platforms.caveduck import CaveduckPlatform
from gamemaster_mcp.platforms.tipsy import TipsyPlatform

# ── Agent Tests ──────────────────────────────────────────────────────────────


class TestGameMasterAgent:
    @pytest.fixture
    def agent(self):
        return GameMasterAgent()

    @pytest.mark.asyncio
    async def test_ideate_default(self, agent):
        concepts = await agent.ideate()
        assert len(concepts) == 5
        assert all(c["genre"] == "dark_fantasy" for c in concepts)

    @pytest.mark.asyncio
    async def test_ideate_noir(self, agent):
        concepts = await agent.ideate(genre="noir", count=3)
        assert len(concepts) == 3
        assert all(c["genre"] == "noir" for c in concepts)

    @pytest.mark.asyncio
    async def test_ideate_all_genres(self, agent):
        for genre in ARCHETYPES:
            concepts = await agent.ideate(genre=genre, count=2)
            assert len(concepts) == 2
            assert all(c["genre"] == genre for c in concepts)

    @pytest.mark.asyncio
    async def test_ideate_count_capped(self, agent):
        concepts = await agent.ideate(count=20)
        assert len(concepts) == 10  # max 10

    @pytest.mark.asyncio
    async def test_create_sheet(self, agent):
        concept = {"name": "Morrigan", "description": "A dark priestess", "theme": "curse"}
        platform = CaveduckPlatform()
        sheet = await agent.create_sheet(concept=concept, platform=platform, genre="dark_fantasy")
        assert sheet["name"] == "Morrigan"
        assert sheet["platform"] == "caveduck"
        assert "greeting_variants" in sheet
        assert "secret" in sheet
        assert "writing_style" in sheet
        assert "tags" in sheet
        assert len(sheet["tags"]) <= 10
        assert "Original" in sheet["tags"]
        assert sheet.get("original_character") is True

    @pytest.mark.asyncio
    async def test_generate_image_placeholder(self, agent):
        result = await agent.generate_image(prompt="A dark fantasy character", style="noir")
        assert result["status"] == "placeholder"
        assert "ComfyUI" in result["message"]


# ── Caveduck Platform Tests ──────────────────────────────────────────────────


class TestCaveduckPlatform:
    @pytest.fixture
    def platform(self):
        return CaveduckPlatform()

    def test_name(self, platform):
        assert platform.name == "caveduck"

    def test_url(self, platform):
        assert platform.url == "https://caveduck.io"

    def test_format_requirements_structure(self, platform):
        reqs = platform.get_format_requirements()
        assert "name" in reqs
        assert "description" in reqs
        assert "greeting" in reqs
        assert "secret" in reqs
        assert "writing_style" in reqs
        assert "tags" in reqs
        assert "expert_mode" in reqs

    def test_format_requirements_lengths(self, platform):
        reqs = platform.get_format_requirements()
        # Official Caveduck docs (May 2026)
        assert reqs["name"]["max_length"] == 50
        assert reqs["description"]["max_length"] == 10_000
        assert reqs["greeting"]["max_length"] == 10_000
        assert reqs["greeting"]["max_variants"] == 3
        assert reqs["secret"]["max_length"] == 10_000
        assert reqs["tags"]["max_count"] == 10
        assert reqs["expert_mode"]["lorebook"]["max_keywords"] == 100
        assert reqs["expert_mode"]["variables"]["max_count"] == 3

    @pytest.mark.asyncio
    async def test_analyze_trending(self, platform):
        result = await platform.analyze_trending()
        assert result["platform"] == "caveduck"
        assert "trending_patterns" in result
        assert "strategies" in result
        assert "monetization" in result
        assert "content_rules" in result
        # Key discovery from official docs
        assert "20,000 incentives" in result["monetization"]["cash_withdrawal"]

    @pytest.mark.asyncio
    async def test_suggest_tags(self, platform):
        char = {"name": "Morrigan", "description": "A dark demon priestess with cursed powers"}
        tags = await platform.suggest_tags(char)
        assert "Original" in tags  # Always first
        assert "Fantasy" in tags
        assert "Possessiveness" in tags
        assert len(tags) <= 10

    @pytest.mark.asyncio
    async def test_suggest_tags_noir(self, platform):
        char = {"name": "Vincent", "description": "A mafia detective in the noir underworld"}
        tags = await platform.suggest_tags(char)
        assert "Original" in tags
        assert "Noir" in tags
        assert "Mafia" in tags


# ── Tipsy Platform Tests ─────────────────────────────────────────────────────


class TestTipsyPlatform:
    @pytest.fixture
    def platform(self):
        return TipsyPlatform()

    def test_name(self, platform):
        assert platform.name == "tipsy"

    @pytest.mark.asyncio
    async def test_analyze_trending(self, platform):
        result = await platform.analyze_trending()
        assert result["platform"] == "tipsy"

    @pytest.mark.asyncio
    async def test_suggest_tags(self, platform):
        char = {"name": "Aria", "description": "A vampire queen"}
        tags = await platform.suggest_tags(char)
        assert isinstance(tags, list)
        assert len(tags) > 0


# ── ComfyUI Client Tests ─────────────────────────────────────────────────────


class TestComfyUI:
    def test_checkpoints_defined(self):
        assert "flux_dev_q8" in CHECKPOINTS
        assert "unstable_evolution_xxx" in CHECKPOINTS
        assert "getphat_reality_xxx" in CHECKPOINTS

    def test_style_presets(self):
        assert "dark_fantasy" in STYLE_PRESETS
        assert "noir" in STYLE_PRESETS
        assert "anime" in STYLE_PRESETS
        assert "photorealistic" in STYLE_PRESETS

    def test_card_sizes(self):
        assert "caveduck_profile" in CARD_SIZES
        assert "caveduck_album" in CARD_SIZES
        assert CARD_SIZES["caveduck_profile"]["width"] == 512
        assert CARD_SIZES["caveduck_profile"]["height"] == 768

    def test_build_workflow_gguf(self):
        workflow = build_character_card_workflow(
            prompt="test prompt",
            negative_prompt="bad quality",
            checkpoint="flux_dev_q8",
            style="dark_fantasy",
            card_type="caveduck_profile",
            seed=42,
        )
        # Check workflow structure
        assert "1" in workflow  # UNETLoader
        assert "6" in workflow  # KSampler
        assert "9" in workflow  # SaveImage
        assert workflow["1"]["class_type"] == "UNETLoader"
        assert workflow["1"]["inputs"]["unet_name"] == "flux1-dev-Q8_0.gguf"
        assert workflow["6"]["inputs"]["seed"] == 42

    def test_build_workflow_safetensors(self):
        workflow = build_character_card_workflow(
            prompt="test prompt",
            negative_prompt="bad quality",
            checkpoint="unstable_evolution_xxx",
            style="dark_fantasy",
            card_type="caveduck_profile",
            seed=123,
        )
        assert workflow["1"]["class_type"] == "UNETLoader"
        assert workflow["1"]["inputs"]["unet_name"] == "unstableEvolution_Fp8.safetensors"
        assert workflow["1"]["inputs"]["weight_dtype"] == "fp8_e4m3fn"


# ── Platform Base Tests ──────────────────────────────────────────────────────


class TestBasePlatform:
    def test_caveduck_inherits_base(self):
        platform = CaveduckPlatform()
        assert isinstance(platform, BasePlatform)

    def test_tipsy_inherits_base(self):
        platform = TipsyPlatform()
        assert isinstance(platform, BasePlatform)
