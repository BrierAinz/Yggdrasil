"""Tests for Persona Engine v2."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest


# Ensure the parent of 'persona' package is in sys.path
_CORE_DIR = str(Path(__file__).resolve().parent.parent.parent)
if _CORE_DIR not in sys.path:
    sys.path.insert(0, _CORE_DIR)

from persona.v2.engine import PersonaEngine  # noqa: E402
from persona.v2.models import PersonaContext, PersonaIdentity, PersonaTemplate  # noqa: E402
from persona.v2.switcher import PersonaSwitcher  # noqa: E402
from persona.v2.templates import BUILTIN_TEMPLATES, PersonaTemplateLoader  # noqa: E402


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def loader() -> PersonaTemplateLoader:
    """Template loader with no YAML dir — uses built-in fallbacks."""
    return PersonaTemplateLoader(template_dir=Path("/nonexistent"))


@pytest.fixture()
def engine(loader: PersonaTemplateLoader) -> PersonaEngine:
    """PersonaEngine with built-in fallback templates."""
    return PersonaEngine(template_loader=loader)


# ---------------------------------------------------------------------------
# Loading templates
# ---------------------------------------------------------------------------


class TestTemplateLoading:
    """Tests for loading templates via PersonaTemplateLoader."""

    def test_load_all_returns_builtin_templates(self, loader: PersonaTemplateLoader) -> None:
        templates = loader.load_all()
        for name in ("base", "lilith", "odin", "mimir", "eva", "adan"):
            assert name in templates, f"Missing built-in template: {name}"

    def test_load_specific_template(self, loader: PersonaTemplateLoader) -> None:
        template = loader.load_template("lilith")
        assert template.id == "lilith"
        assert template.identity.name == "Lilith"

    def test_load_nonexistent_template_raises(self, loader: PersonaTemplateLoader) -> None:
        with pytest.raises(KeyError, match="not_found"):
            loader.load_template("not_found")

    def test_builtin_data_matches_models(self) -> None:
        for tid, tdata in BUILTIN_TEMPLATES.items():
            template = PersonaTemplate(**tdata)
            assert template.id == tid


# ---------------------------------------------------------------------------
# Template inheritance
# ---------------------------------------------------------------------------


class TestTemplateInheritance:
    """Tests for template inheritance resolution."""

    def test_child_inherits_from_base(self, loader: PersonaTemplateLoader) -> None:
        lilith = loader.load_template("lilith")
        assert lilith.identity.name == "Lilith"
        assert len(lilith.identity.rules) >= 6

    def test_base_no_inheritance(self, loader: PersonaTemplateLoader) -> None:
        base = loader.load_template("base")
        assert base.inherits is None
        assert base.identity.name == ""

    def test_inheritance_resolves_parent_chain(self) -> None:
        parent = PersonaTemplate(
            id="parent_test",
            version="1.0",
            identity=PersonaIdentity(name="Parent", role="parent role", rules=["rule1"]),
            inherits=None,
        )
        child = PersonaTemplate(
            id="child_test",
            version="1.0",
            identity=PersonaIdentity(name="Child", role="", rules=["rule2"]),
            inherits="parent_test",
        )
        all_templates = {"parent_test": parent, "child_test": child}
        loader_instance = PersonaTemplateLoader()
        resolved = loader_instance._resolve_inheritance(child, all_templates)
        assert resolved.identity.name == "Child"
        assert resolved.identity.role == "parent role"
        assert "rule1" in resolved.identity.rules
        assert "rule2" in resolved.identity.rules


# ---------------------------------------------------------------------------
# Building prompts
# ---------------------------------------------------------------------------


class TestBuildPrompt:
    """Tests for PersonaEngine.build_prompt."""

    def test_build_prompt_without_context(self, engine: PersonaEngine) -> None:
        prompt = engine.build_prompt("lilith")
        assert "Lilith" in prompt
        assert "Diosa Oscura" in prompt
        assert "Reglas:" in prompt

    def test_build_prompt_with_neutral_context(self, engine: PersonaEngine) -> None:
        context = PersonaContext(user_mood="neutral", complexity="normal")
        prompt = engine.build_prompt("lilith", context=context)
        assert "Lilith" in prompt
        assert "frustrado" not in prompt.lower()

    def test_build_prompt_extra_context(self, engine: PersonaEngine) -> None:
        prompt = engine.build_prompt("lilith", extra_context="Proyecto secreto.")
        assert "Proyecto secreto." in prompt

    def test_build_prompt_returns_string(self, engine: PersonaEngine) -> None:
        result = engine.build_prompt("odin")
        assert isinstance(result, str)
        assert len(result) > 0


# ---------------------------------------------------------------------------
# Context modifiers
# ---------------------------------------------------------------------------


class TestContextModifiers:
    """Tests for dynamic context adaptation in prompts."""

    def test_frustrated_mood(self, engine: PersonaEngine) -> None:
        context = PersonaContext(user_mood="frustrated")
        prompt = engine.build_prompt("lilith", context=context)
        assert "frustrado" in prompt.lower() or "paciente" in prompt.lower()

    def test_happy_mood(self, engine: PersonaEngine) -> None:
        context = PersonaContext(user_mood="happy")
        prompt = engine.build_prompt("lilith", context=context)
        assert "buen humor" in prompt.lower() or "directo" in prompt.lower()

    def test_rushed_mood(self, engine: PersonaEngine) -> None:
        context = PersonaContext(user_mood="rushed")
        prompt = engine.build_prompt("lilith", context=context)
        assert "prisa" in prompt.lower() or "conciso" in prompt.lower()

    def test_debugging_project(self, engine: PersonaEngine) -> None:
        context = PersonaContext(project_type="debugging")
        prompt = engine.build_prompt("lilith", context=context)
        assert "debugging" in prompt.lower() or "metodológic" in prompt.lower()

    def test_creative_project(self, engine: PersonaEngine) -> None:
        context = PersonaContext(project_type="creative")
        prompt = engine.build_prompt("lilith", context=context)
        assert "creativ" in prompt.lower() or "imaginativ" in prompt.lower()

    def test_deployment_project(self, engine: PersonaEngine) -> None:
        context = PersonaContext(project_type="deployment")
        prompt = engine.build_prompt("lilith", context=context)
        assert "deployment" in prompt.lower() or "cautelos" in prompt.lower()

    def test_high_complexity(self, engine: PersonaEngine) -> None:
        context = PersonaContext(complexity="high")
        prompt = engine.build_prompt("lilith", context=context)
        assert "compleja" in prompt.lower() or "desglosa" in prompt.lower()

    def test_simple_complexity(self, engine: PersonaEngine) -> None:
        context = PersonaContext(complexity="simple")
        prompt = engine.build_prompt("lilith", context=context)
        assert "simple" in prompt.lower() or "directo" in prompt.lower()

    def test_context_modifiers_from_template(self, engine: PersonaEngine) -> None:
        context = PersonaContext(user_mood="frustrated")
        prompt = engine.build_prompt("lilith", context=context)
        assert "paciente" in prompt.lower() or "paso" in prompt.lower()

    def test_combined_context(self, engine: PersonaEngine) -> None:
        context = PersonaContext(user_mood="rushed", project_type="deployment")
        prompt = engine.build_prompt("lilith", context=context)
        assert "prisa" in prompt.lower() or "conciso" in prompt.lower()
        assert "deployment" in prompt.lower() or "cautelos" in prompt.lower()


# ---------------------------------------------------------------------------
# PersonaSwitcher
# ---------------------------------------------------------------------------


class TestPersonaSwitcher:
    """Tests for PersonaSwitcher switching, history, and rollback."""

    def test_switch_returns_result(self, engine: PersonaEngine) -> None:
        switcher = PersonaSwitcher(engine)
        result = switcher.switch("lilith")
        assert result.template_id == "lilith"
        assert result.system_prompt
        assert result.timestamp > 0

    def test_switch_updates_current_persona(self, engine: PersonaEngine) -> None:
        switcher = PersonaSwitcher(engine)
        switcher.switch("lilith")
        assert switcher.current_persona == "lilith"

    def test_get_current_prompt(self, engine: PersonaEngine) -> None:
        switcher = PersonaSwitcher(engine)
        switcher.switch("odin")
        prompt = switcher.get_current_prompt()
        assert "Odin" in prompt

    def test_history_tracking(self, engine: PersonaEngine) -> None:
        switcher = PersonaSwitcher(engine)
        switcher.switch("lilith")
        switcher.switch("odin")
        history = switcher.get_history()
        assert len(history) == 2
        assert history[0].template_id == "lilith"
        assert history[1].template_id == "odin"

    def test_history_limit(self, engine: PersonaEngine) -> None:
        switcher = PersonaSwitcher(engine)
        for tid in ("lilith", "odin", "mimir", "eva", "adan"):
            switcher.switch(tid)
        limited = switcher.get_history(limit=3)
        assert len(limited) == 3

    def test_rollback(self, engine: PersonaEngine) -> None:
        switcher = PersonaSwitcher(engine)
        switcher.switch("lilith")
        switcher.switch("odin")
        result = switcher.rollback()
        assert result is not None
        assert result.template_id == "lilith"
        assert switcher.current_persona == "lilith"

    def test_rollback_empty_history(self, engine: PersonaEngine) -> None:
        switcher = PersonaSwitcher(engine)
        assert switcher.rollback() is None

    def test_rollback_single_entry(self, engine: PersonaEngine) -> None:
        switcher = PersonaSwitcher(engine)
        switcher.switch("lilith")
        assert switcher.rollback() is None

    def test_switch_with_context(self, engine: PersonaEngine) -> None:
        switcher = PersonaSwitcher(engine)
        context = PersonaContext(user_mood="frustrated")
        result = switcher.switch("lilith", context=context)
        assert result.context_applied.user_mood == "frustrated"


# ---------------------------------------------------------------------------
# Fallback when template not found
# ---------------------------------------------------------------------------


class TestFallbacks:
    """Tests for fallback behaviour."""

    def test_template_not_found_raises_keyerror(self, engine: PersonaEngine) -> None:
        with pytest.raises(KeyError):
            engine.build_prompt("nonexistent_persona")

    def test_switcher_template_not_found_raises(self, engine: PersonaEngine) -> None:
        switcher = PersonaSwitcher(engine)
        with pytest.raises(KeyError):
            switcher.switch("nonexistent_persona")
