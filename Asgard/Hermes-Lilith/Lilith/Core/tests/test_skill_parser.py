"""
Tests para Skill Parser
=======================
RED-GREEN-REFACTOR: TDD estricto para el parser de skills.
"""
from pathlib import Path

import pytest
from Lilith.Core.skill_parser import Skill, SkillParseError, SkillParser


class TestSkillParser:
    """Tests para el parser de skills."""

    def test_parse_valid_skill(self):
        """RED: Debe parsear un skill valido."""
        content = """---
name: test-skill
description: Use when testing
version: 1.0.0
trigger:
  - "test"
  - "testing"
priority: 100
---

# Test Skill

This is a test skill.

## Steps

1. Do something
2. Do something else
"""
        parser = SkillParser()
        skill = parser.parse(content)

        assert skill.name == "test-skill"
        assert skill.description == "Use when testing"
        assert skill.version == "1.0.0"
        assert skill.trigger == ["test", "testing"]
        assert skill.priority == 100
        assert "Test Skill" in skill.content
        assert "## Steps" in skill.content

    def test_parse_skill_without_optional_fields(self):
        """RED: Debe parsear skill con solo campos requeridos."""
        content = """---
name: minimal-skill
description: Minimal skill
---

Minimal content.
"""
        parser = SkillParser()
        skill = parser.parse(content)

        assert skill.name == "minimal-skill"
        assert skill.description == "Minimal skill"
        assert skill.version == "1.0.0"  # default
        assert skill.trigger == []  # default
        assert skill.priority == 100  # default

    def test_parse_skill_single_trigger(self):
        """RED: Debe manejar trigger como string (no lista)."""
        content = """---
name: single-trigger
description: Single trigger test
trigger: "test"
---

Content.
"""
        parser = SkillParser()
        skill = parser.parse(content)

        assert skill.trigger == ["test"]

    def test_parse_skill_empty_trigger(self):
        """RED: Debe manejar trigger vacio."""
        content = """---
name: no-trigger
description: No trigger
trigger: []
---

Content.
"""
        parser = SkillParser()
        skill = parser.parse(content)

        assert skill.trigger == []

    def test_parse_invalid_no_frontmatter(self):
        """RED: Debe fallar si no hay frontmatter."""
        content = "Just markdown without YAML frontmatter."
        parser = SkillParser()

        with pytest.raises(SkillParseError) as exc_info:
            parser.parse(content)

        assert "frontmatter" in str(exc_info.value).lower()

    def test_parse_invalid_missing_required_fields(self):
        """RED: Debe fallar si faltan campos requeridos."""
        content = """---
name: missing-description
---

Content.
"""
        parser = SkillParser()

        with pytest.raises(SkillParseError) as exc_info:
            parser.parse(content)

        assert "description" in str(exc_info.value).lower()

    def test_parse_invalid_yaml(self):
        """RED: Debe fallar con YAML invalido."""
        content = """---
name: bad-yaml
  description: indented wrong
---

Content.
"""
        parser = SkillParser()

        with pytest.raises(SkillParseError) as exc_info:
            parser.parse(content)

        assert "yaml" in str(exc_info.value).lower()

    def test_parse_file(self, tmp_path):
        """RED: Debe parsear desde archivo."""
        skill_file = tmp_path / "test_skill.md"
        skill_file.write_text(
            """---
name: file-skill
description: From file
---

File content.
"""
        )
        parser = SkillParser()
        skill = parser.parse_file(skill_file)

        assert skill.name == "file-skill"
        assert skill.source_file == skill_file

    def test_parse_file_not_found(self, tmp_path):
        """RED: Debe fallar si archivo no existe."""
        parser = SkillParser()

        with pytest.raises(SkillParseError):
            parser.parse_file(tmp_path / "nonexistent.md")

    def test_is_valid_skill_file(self, tmp_path):
        """RED: Debe detectar archivos de skill validos."""
        parser = SkillParser()

        valid = tmp_path / "valid.md"
        valid.write_text(
            """---
name: valid
description: Valid
---

Content.
"""
        )
        assert parser.is_valid_skill_file(valid) is True

        invalid = tmp_path / "invalid.txt"
        invalid.write_text("No frontmatter here.")
        assert parser.is_valid_skill_file(invalid) is False

        no_frontmatter = tmp_path / "no_frontmatter.md"
        no_frontmatter.write_text("Just markdown.")
        assert parser.is_valid_skill_file(no_frontmatter) is False


class TestSkill:
    """Tests para la clase Skill."""

    def test_should_trigger_with_matching_keyword(self):
        """RED: Debe activarse cuando hay match."""
        skill = Skill(
            name="test",
            description="Test",
            content="Content",
            trigger=["test", "debug"],
        )

        assert skill.should_trigger("I need to test something") is True
        assert skill.should_trigger("debug this code") is True

    def test_should_trigger_no_match(self):
        """RED: No debe activarse sin match."""
        skill = Skill(
            name="test",
            description="Test",
            content="Content",
            trigger=["test"],
        )

        assert skill.should_trigger("hello world") is False

    def test_should_trigger_empty_trigger(self):
        """RED: No debe activarse si no hay triggers."""
        skill = Skill(
            name="test",
            description="Test",
            content="Content",
            trigger=[],
        )

        assert skill.should_trigger("anything") is False

    def test_trigger_score_single_match(self):
        """RED: Score debe ser 0.5 con 1 de 2 matches."""
        skill = Skill(
            name="test",
            description="Test",
            content="Content",
            trigger=["test", "debug"],
        )

        assert skill.trigger_score("test this") == 0.5

    def test_trigger_score_all_match(self):
        """RED: Score debe ser 1.0 con todos los matches."""
        skill = Skill(
            name="test",
            description="Test",
            content="Content",
            trigger=["test", "debug"],
        )

        assert skill.trigger_score("test and debug this") == 1.0

    def test_trigger_score_no_trigger(self):
        """RED: Score debe ser 0.0 sin triggers."""
        skill = Skill(
            name="test",
            description="Test",
            content="Content",
            trigger=[],
        )

        assert skill.trigger_score("anything") == 0.0

    def test_to_dict(self):
        """RED: Debe serializar a dict correctamente."""
        skill = Skill(
            name="test",
            description="Test skill",
            content="Content",
            version="2.0.0",
            trigger=["test"],
            priority=50,
        )

        d = skill.to_dict()
        assert d["name"] == "test"
        assert d["description"] == "Test skill"
        assert d["version"] == "2.0.0"
        assert d["trigger"] == ["test"]
        assert d["priority"] == 50

    def test_skill_case_insensitive_trigger(self):
        """RED: Trigger debe ser case-insensitive."""
        skill = Skill(
            name="test",
            description="Test",
            content="Content",
            trigger=["TEST"],
        )

        assert skill.should_trigger("test this") is True
        assert skill.should_trigger("TEST this") is True
        assert skill.should_trigger("TeSt this") is True
