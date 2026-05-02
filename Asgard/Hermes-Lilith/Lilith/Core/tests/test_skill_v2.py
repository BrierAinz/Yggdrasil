"""
Tests para Skill System v2
==========================
RED-GREEN-REFACTOR: TDD estricto para las nuevas funcionalidades del Skill system v2.

Cubre:
- Nuevos campos en Skill dataclass
- Regex triggers (compilacion, matching, patterns invalidos)
- Intent triggers
- Template rendering con variables
- Enable/disable skills (via SkillRegistry)
- Usage stats (record_trigger, get_usage_stats)
- YAML file parsing
- Score ponderado (keyword + regex + intent)
- Backward compatibility (skills viejos sin nuevos campos)
- Tools_required validation
"""
import time
from pathlib import Path

import pytest
from Lilith.Core.skill_parser import Skill, SkillParseError, SkillParser
from Lilith.Core.skill_registry import SkillRegistry


# ═══════════════════════════════════════════════════════════════════════════════
# Skill Dataclass — Nuevos campos
# ═══════════════════════════════════════════════════════════════════════════════


class TestSkillNewFields:
    """Tests para los nuevos campos en Skill dataclass."""

    def test_default_trigger_regex(self):
        """trigger_regex debe ser lista vacia por defecto."""
        skill = Skill(name="test", description="Test", content="Content")
        assert skill.trigger_regex == []

    def test_default_trigger_intent(self):
        """trigger_intent debe ser lista vacia por defecto."""
        skill = Skill(name="test", description="Test", content="Content")
        assert skill.trigger_intent == []

    def test_default_enabled(self):
        """enabled debe ser True por defecto."""
        skill = Skill(name="test", description="Test", content="Content")
        assert skill.enabled is True

    def test_default_tools_required(self):
        """tools_required debe ser lista vacia por defecto."""
        skill = Skill(name="test", description="Test", content="Content")
        assert skill.tools_required == []

    def test_default_prompt_template(self):
        """prompt_template debe ser None por defecto."""
        skill = Skill(name="test", description="Test", content="Content")
        assert skill.prompt_template is None

    def test_default_times_triggered(self):
        """_times_triggered debe ser 0 por defecto."""
        skill = Skill(name="test", description="Test", content="Content")
        assert skill._times_triggered == 0

    def test_default_last_triggered(self):
        """_last_triggered debe ser None por defecto."""
        skill = Skill(name="test", description="Test", content="Content")
        assert skill._last_triggered is None

    def test_all_fields_set(self):
        """Debe poder setear todos los campos nuevos."""
        skill = Skill(
            name="full-skill",
            description="Full skill",
            content="Content",
            version="2.0.0",
            trigger=["python", "code"],
            trigger_regex=[r"\bpython\b", r"\bcode\b"],
            trigger_intent=["coding", "debugging"],
            priority=50,
            enabled=False,
            tools_required=["read_file", "write_file"],
            prompt_template="Eres un experto. {{user_input}}",
            source_file=Path("/tmp/test.md"),
            metadata={"author": "test"},
        )
        assert skill.trigger_regex == [r"\bpython\b", r"\bcode\b"]
        assert skill.trigger_intent == ["coding", "debugging"]
        assert skill.enabled is False
        assert skill.tools_required == ["read_file", "write_file"]
        assert skill.prompt_template == "Eres un experto. {{user_input}}"
        assert skill.metadata == {"author": "test"}

    def test_to_dict_includes_new_fields(self):
        """to_dict debe incluir los nuevos campos."""
        skill = Skill(
            name="test",
            description="Test",
            content="Content",
            trigger_regex=[r"\bpython\b"],
            trigger_intent=["coding"],
            enabled=False,
            tools_required=["read_file"],
            prompt_template="Hello {{user_input}}",
        )
        d = skill.to_dict()
        assert d["trigger_regex"] == [r"\bpython\b"]
        assert d["trigger_intent"] == ["coding"]
        assert d["enabled"] is False
        assert d["tools_required"] == ["read_file"]
        assert d["prompt_template"] == "Hello {{user_input}}"


# ═══════════════════════════════════════════════════════════════════════════════
# Regex Triggers
# ═══════════════════════════════════════════════════════════════════════════════


class TestRegexTriggers:
    """Tests para triggers basados en regex."""

    def test_regex_match_basic(self):
        """Debe hacer match con regex patterns."""
        skill = Skill(
            name="python-skill",
            description="Python skill",
            content="Content",
            trigger_regex=[r"\bpython\b"],
        )
        assert skill.should_trigger("I want to learn python programming")

    def test_regex_match_case_insensitive(self):
        """Regex matching debe ser case-insensitive."""
        skill = Skill(
            name="python-skill",
            description="Python skill",
            content="Content",
            trigger_regex=[r"\bpython\b"],
        )
        assert skill.should_trigger("I love Python")

    def test_regex_no_match(self):
        """No debe activarse si el regex no match."""
        skill = Skill(
            name="python-skill",
            description="Python skill",
            content="Content",
            trigger_regex=[r"\bpython\b"],
        )
        assert not skill.should_trigger("I love javascript")

    def test_regex_score_single_match(self):
        """Score regex con 1 de 2 patterns que matchean."""
        skill = Skill(
            name="multi-regex",
            description="Multi regex",
            content="Content",
            trigger_regex=[r"\bpython\b", r"\bjavascript\b"],
        )
        score = skill.trigger_score("I code in python")
        # regex_score = 1/2 = 0.5; weighted = 0.5 * 0.4 / 0.4 = 0.5
        assert 0.4 < score <= 0.6

    def test_regex_score_all_match(self):
        """Score regex con todos los patterns que matchean."""
        skill = Skill(
            name="multi-regex",
            description="Multi regex",
            content="Content",
            trigger_regex=[r"\bpython\b", r"\bcode\b"],
        )
        score = skill.trigger_score("I python code today")
        assert score == 1.0

    def test_regex_score_no_match(self):
        """Score regex sin matches."""
        skill = Skill(
            name="regex-skill",
            description="Regex skill",
            content="Content",
            trigger_regex=[r"\bpython\b"],
        )
        score = skill.trigger_score("I love rust")
        assert score == 0.0

    def test_invalid_regex_does_not_crash(self):
        """Un pattern regex invalido no debe causar crash, solo loguear warning."""
        skill = Skill(
            name="bad-regex",
            description="Bad regex",
            content="Content",
            trigger_regex=[r"[invalid", r"\bvalid\b"],
        )
        # No debe lanzar excepcion
        score = skill.trigger_score("I have a valid point")
        # Solo el pattern valido matchea: 1/2 * 0.4 / 0.4 = 0.5
        assert score > 0.0

    def test_regex_word_boundary(self):
        """Regex con word boundary debe matchear palabras completas."""
        skill = Skill(
            name="word-boundary",
            description="Word boundary test",
            content="Content",
            trigger_regex=[r"\bgo\b"],
        )
        # "go" como palabra completa
        assert skill.should_trigger("Let's go home")
        # "go" dentro de "golang" NO debe matchear con \b
        assert not skill.should_trigger("I use golang")


# ═══════════════════════════════════════════════════════════════════════════════
# Intent Triggers
# ═══════════════════════════════════════════════════════════════════════════════


class TestIntentTriggers:
    """Tests para triggers basados en intents."""

    def test_intent_match_basic(self):
        """Debe hacer match con intent labels."""
        skill = Skill(
            name="coding-skill",
            description="Coding helper",
            content="Content",
            trigger_intent=["coding"],
        )
        # Intent matching es por inclusion del label en el texto
        assert skill.should_trigger("I need help with coding")

    def test_intent_no_match(self):
        """No debe activarse si el intent no esta en el texto."""
        skill = Skill(
            name="coding-skill",
            description="Coding helper",
            content="Content",
            trigger_intent=["coding"],
        )
        assert not skill.should_trigger("I want to cook dinner")

    def test_intent_score_partial(self):
        """Score de intent con match parcial."""
        skill = Skill(
            name="multi-intent",
            description="Multi intent",
            content="Content",
            trigger_intent=["coding", "research"],
        )
        score = skill.trigger_score("I need coding help")
        # intent_score = 1/2 = 0.5; weighted = 0.5 * 0.2 / 0.2 = 0.5
        assert 0.4 < score < 0.6

    def test_intent_score_all_match(self):
        """Score de intent con todos los intents que matchean."""
        skill = Skill(
            name="multi-intent",
            description="Multi intent",
            content="Content",
            trigger_intent=["coding", "debugging"],
        )
        score = skill.trigger_score("I need help with coding and debugging")
        assert score == 1.0


# ═══════════════════════════════════════════════════════════════════════════════
# Score Ponderado
# ═══════════════════════════════════════════════════════════════════════════════


class TestWeightedScore:
    """Tests para el score ponderado (keyword * 0.4 + regex * 0.4 + intent * 0.2)."""

    def test_keyword_only_score(self):
        """Score con solo keywords (backward compat)."""
        skill = Skill(
            name="test",
            description="Test",
            content="Content",
            trigger=["python", "code"],
        )
        score = skill.trigger_score("I love python")
        # keyword_score = 1/2 = 0.5; total = 0.5 (keyword only, weight 0.4 normalized to 1.0)
        assert score == 0.5

    def test_regex_only_score(self):
        """Score con solo regex triggers."""
        skill = Skill(
            name="test",
            description="Test",
            content="Content",
            trigger_regex=[r"\bpython\b"],
        )
        score = skill.trigger_score("I love python")
        assert score == 1.0

    def test_intent_only_score(self):
        """Score con solo intent triggers."""
        skill = Skill(
            name="test",
            description="Test",
            content="Content",
            trigger_intent=["coding"],
        )
        score = skill.trigger_score("I need coding help")
        assert score == 1.0

    def test_combined_score(self):
        """Score ponderado combinando keywords + regex + intent."""
        skill = Skill(
            name="test",
            description="Test",
            content="Content",
            trigger=["python"],
            trigger_regex=[r"\bpython\b"],
            trigger_intent=["coding"],
        )
        # "python coding" - keyword match "python" -> 1/1=1.0
        # regex match r"\bpython\b" -> 1/1=1.0
        # intent "coding" in "python coding" -> 1/1=1.0
        # Score = (0.4*1.0 + 0.4*1.0 + 0.2*1.0) / (0.4+0.4+0.2) = 1.0/1.0 = 1.0
        score = skill.trigger_score("python coding")
        assert score == 1.0

    def test_partial_combined_score(self):
        """Score ponderado con match parcial en algunos tipos."""
        skill = Skill(
            name="test",
            description="Test",
            content="Content",
            trigger=["python", "java"],
            trigger_regex=[r"\bpython\b"],
            trigger_intent=["coding", "research"],
        )
        # "python code" - keyword: "python" match, "java" no -> 1/2 = 0.5
        # regex: r"\bpython\b" match -> 1/1 = 1.0
        # intent: "coding" no in text, "research" no -> 0/2 = 0.0
        # Score = (0.4*0.5 + 0.4*1.0 + 0.2*0.0) / (0.4+0.4+0.2) 
        #        = (0.2 + 0.4 + 0.0) / 1.0 = 0.6
        score = skill.trigger_score("python code")
        assert abs(score - 0.6) < 0.01

    def test_no_triggers_at_all(self):
        """Score sin ningun tipo de trigger debe ser 0."""
        skill = Skill(
            name="test",
            description="Test",
            content="Content",
        )
        assert skill.trigger_score("anything") == 0.0


# ═══════════════════════════════════════════════════════════════════════════════
# Template Rendering
# ═══════════════════════════════════════════════════════════════════════════════


class TestTemplateRendering:
    """Tests para render() con template variables."""

    def test_render_with_prompt_template(self):
        """Debe renderizar prompt_template con variables."""
        skill = Skill(
            name="test",
            description="Test",
            content="Original content",
            prompt_template="Hello {{user_input}}, your context is {{context}}",
        )
        result = skill.render(user_input="Alice", context="coding")
        assert result == "Hello Alice, your context is coding"

    def test_render_fallback_to_content(self):
        """Si no hay prompt_template, debe usar content como template."""
        skill = Skill(
            name="test",
            description="Test",
            content="Hello {{user_input}}",
        )
        result = skill.render(user_input="Bob")
        assert result == "Hello Bob"

    def test_render_missing_variable(self):
        """Variables no proporcionadas quedan sin reemplazar."""
        skill = Skill(
            name="test",
            description="Test",
            content="Hello {{user_input}}, {{missing}}",
        )
        result = skill.render(user_input="Alice")
        assert result == "Hello Alice, {{missing}}"

    def test_render_multiple_variables(self):
        """Debe reemplazar todas las variables soportadas."""
        skill = Skill(
            name="test",
            description="Test",
            content="Input: {{user_input}}, Context: {{context}}, Memory: {{memory}}, Skills: {{skills}}",
        )
        result = skill.render(
            user_input="help",
            context="python",
            memory="previous chat",
            skills="coding,debugging",
        )
        assert "Input: help" in result
        assert "Context: python" in result
        assert "Memory: previous chat" in result
        assert "Skills: coding,debugging" in result

    def test_render_empty_kwargs(self):
        """Si no se pasan kwargs, el template se devuelve sin cambios."""
        skill = Skill(
            name="test",
            description="Test",
            content="Content",
            prompt_template="Hello {{user_input}}",
        )
        result = skill.render()
        assert result == "Hello {{user_input}}"


# ═══════════════════════════════════════════════════════════════════════════════
# SkillParser — Nuevos campos YAML
# ═══════════════════════════════════════════════════════════════════════════════


class TestSkillParserNewFields:
    """Tests para el parser con los nuevos campos."""

    def test_parse_trigger_regex(self):
        """Debe parsear trigger_regex desde YAML frontmatter."""
        content = """---
name: regex-skill
description: Regex skill
trigger_regex:
  - '\\bpython\\b'
  - '\\bjavascript\\b'
---

Content.
"""
        parser = SkillParser()
        skill = parser.parse(content)
        assert skill.trigger_regex == [r"\bpython\b", r"\bjavascript\b"]

    def test_parse_trigger_intent(self):
        """Debe parsear trigger_intent desde YAML frontmatter."""
        content = """---
name: intent-skill
description: Intent skill
trigger_intent:
  - "coding"
  - "debugging"
---

Content.
"""
        parser = SkillParser()
        skill = parser.parse(content)
        assert skill.trigger_intent == ["coding", "debugging"]

    def test_parse_enabled_false(self):
        """Debe parsear enabled: false desde YAML."""
        content = """---
name: disabled-skill
description: Disabled skill
enabled: false
---

Content.
"""
        parser = SkillParser()
        skill = parser.parse(content)
        assert skill.enabled is False

    def test_parse_enabled_true_default(self):
        """Debe default enabled a True si no se especifica."""
        content = """---
name: enabled-skill
description: Enabled skill
---

Content.
"""
        parser = SkillParser()
        skill = parser.parse(content)
        assert skill.enabled is True

    def test_parse_tools_required(self):
        """Debe parsear tools_required desde YAML."""
        content = """---
name: tool-skill
description: Tool skill
tools_required:
  - "read_file"
  - "write_file"
---

Content.
"""
        parser = SkillParser()
        skill = parser.parse(content)
        assert skill.tools_required == ["read_file", "write_file"]

    def test_parse_prompt_template(self):
        """Debe parsear prompt_template desde YAML."""
        content = """---
name: template-skill
description: Template skill
prompt_template: "Eres un experto en {{context}}. Ayuda con: {{user_input}}"
---

Content.
"""
        parser = SkillParser()
        skill = parser.parse(content)
        assert skill.prompt_template == "Eres un experto en {{context}}. Ayuda con: {{user_input}}"

    def test_parse_all_new_fields_together(self):
        """Debe parsear todos los nuevos campos juntos."""
        content = """---
name: full-v2-skill
description: Full v2 skill
version: "2.0.0"
trigger:
  - "python"
trigger_regex:
  - '\\bpython\\b'
trigger_intent:
  - "coding"
priority: 50
enabled: false
tools_required:
  - "run_terminal"
prompt_template: "Help with {{user_input}}"
custom_field: custom_value
---

Body content.
"""
        parser = SkillParser()
        skill = parser.parse(content)
        assert skill.name == "full-v2-skill"
        assert skill.trigger == ["python"]
        assert skill.trigger_regex == [r"\bpython\b"]
        assert skill.trigger_intent == ["coding"]
        assert skill.priority == 50
        assert skill.enabled is False
        assert skill.tools_required == ["run_terminal"]
        assert skill.prompt_template == "Help with {{user_input}}"
        assert skill.content == "Body content."
        assert skill.metadata.get("custom_field") == "custom_value"

    def test_parse_single_string_trigger_regex(self):
        """Debe manejar trigger_regex como string (no lista)."""
        content = """---
name: single-regex
description: Single regex
trigger_regex: '\\bpython\\b'
---

Content.
"""
        parser = SkillParser()
        skill = parser.parse(content)
        assert skill.trigger_regex == [r"\bpython\b"]

    def test_parse_single_string_trigger_intent(self):
        """Debe manejar trigger_intent como string (no lista)."""
        content = """---
name: single-intent
description: Single intent
trigger_intent: "coding"
---

Content.
"""
        parser = SkillParser()
        skill = parser.parse(content)
        assert skill.trigger_intent == ["coding"]

    def test_parse_single_string_tools_required(self):
        """Debe manejar tools_required como string (no lista)."""
        content = """---
name: single-tool
description: Single tool
tools_required: "read_file"
---

Content.
"""
        parser = SkillParser()
        skill = parser.parse(content)
        assert skill.tools_required == ["read_file"]


# ═══════════════════════════════════════════════════════════════════════════════
# YAML File Parsing
# ═══════════════════════════════════════════════════════════════════════════════


class TestYAMLFileParsing:
    """Tests para parsear archivos YAML puros (.yaml/.yml)."""

    def test_parse_yaml_pure(self):
        """Debe parsear un archivo YAML puro sin frontmatter."""
        content = """name: yaml-skill
description: YAML skill
trigger:
  - "test"
version: "2.0.0"
trigger_regex:
  - '\\bpython\\b'
trigger_intent:
  - "coding"
enabled: true
tools_required:
  - "read_file"
content: |
  This is the content
  of the skill.
"""
        parser = SkillParser()
        skill = parser.parse(content)
        assert skill.name == "yaml-skill"
        assert skill.description == "YAML skill"
        assert skill.trigger == ["test"]
        assert skill.trigger_regex == [r"\bpython\b"]
        assert skill.trigger_intent == ["coding"]
        assert skill.enabled is True
        assert "content" in skill.content

    def test_parse_yaml_file(self, tmp_path):
        """Debe parsear un archivo .yaml desde disco."""
        yaml_file = tmp_path / "skill.yaml"
        yaml_file.write_text("""name: yaml-file-skill
description: YAML file skill
trigger:
  - "yaml"
content: "YAML content here"
""")
        parser = SkillParser()
        skill = parser.parse_file(yaml_file)
        assert skill.name == "yaml-file-skill"
        assert skill.source_file == yaml_file

    def test_parse_yml_file(self, tmp_path):
        """Debe parsear un archivo .yml desde disco."""
        yml_file = tmp_path / "skill.yml"
        yml_file.write_text("""name: yml-file-skill
description: YML file skill
trigger:
  - "yml"
content: "YML content"
""")
        parser = SkillParser()
        skill = parser.parse_file(yml_file)
        assert skill.name == "yml-file-skill"

    def test_is_valid_skill_file_yaml(self, tmp_path):
        """is_valid_skill_file debe aceptar archivos .yaml."""
        parser = SkillParser()
        valid_yaml = tmp_path / "valid.yaml"
        valid_yaml.write_text("""name: valid
description: Valid YAML
content: "Content"
""")
        assert parser.is_valid_skill_file(valid_yaml) is True

    def test_is_valid_skill_file_yml(self, tmp_path):
        """is_valid_skill_file debe aceptar archivos .yml."""
        parser = SkillParser()
        valid_yml = tmp_path / "valid.yml"
        valid_yml.write_text("""name: valid
description: Valid YML
content: "Content"
""")
        assert parser.is_valid_skill_file(valid_yml) is True

    def test_yaml_pure_without_name_raises(self):
        """YAML puro sin nombre debe lanzar SkillParseError."""
        content = """description: No name skill
content: "Content"
"""
        parser = SkillParser()
        with pytest.raises(SkillParseError) as exc_info:
            parser.parse(content)
        assert "name" in str(exc_info.value).lower()

    def test_yaml_pure_empty_content(self):
        """YAML puro con content vacio debe crear skill con content vacio."""
        content = """name: empty-content
description: Empty content
"""
        parser = SkillParser()
        skill = parser.parse(content)
        assert skill.content == ""


# ═══════════════════════════════════════════════════════════════════════════════
# Enable/Disable Skills (via SkillRegistry)
# ═══════════════════════════════════════════════════════════════════════════════


class TestEnableDisableSkills:
    """Tests para enable/disable de skills en SkillRegistry."""

    def test_enable_skill(self, tmp_path):
        """Debe habilitar un skill."""
        registry = SkillRegistry(skills_dir=tmp_path, hot_reload=False)
        skill = Skill(
            name="disabled-skill",
            description="Disabled",
            content="Content",
            enabled=False,
        )
        registry.add_skill(skill)

        assert registry.is_enabled("disabled-skill") is False
        assert registry.enable_skill("disabled-skill") is True
        assert registry.is_enabled("disabled-skill") is True

    def test_disable_skill(self, tmp_path):
        """Debe deshabilitar un skill."""
        registry = SkillRegistry(skills_dir=tmp_path, hot_reload=False)
        skill = Skill(
            name="enabled-skill",
            description="Enabled",
            content="Content",
            enabled=True,
        )
        registry.add_skill(skill)

        assert registry.is_enabled("enabled-skill") is True
        assert registry.disable_skill("enabled-skill") is True
        assert registry.is_enabled("enabled-skill") is False

    def test_enable_nonexistent_skill(self, tmp_path):
        """Debe retornar False si el skill no existe."""
        registry = SkillRegistry(skills_dir=tmp_path, hot_reload=False)
        assert registry.enable_skill("nonexistent") is False

    def test_disable_nonexistent_skill(self, tmp_path):
        """Debe retornar False si el skill no existe."""
        registry = SkillRegistry(skills_dir=tmp_path, hot_reload=False)
        assert registry.disable_skill("nonexistent") is False

    def test_is_enabled_nonexistent_skill(self, tmp_path):
        """Debe retornar False si el skill no existe."""
        registry = SkillRegistry(skills_dir=tmp_path, hot_reload=False)
        assert registry.is_enabled("nonexistent") is False

    def test_disabled_skill_not_triggered(self, tmp_path):
        """Skills deshabilitados no deben aparecer en get_triggered_skills."""
        registry = SkillRegistry(skills_dir=tmp_path, hot_reload=False)
        skill = Skill(
            name="disabled-skill",
            description="Disabled",
            content="Content",
            trigger=["test"],
            enabled=False,
        )
        registry.add_skill(skill)

        triggered = registry.get_triggered_skills("test something")
        assert len(triggered) == 0

    def test_enabled_skill_is_triggered(self, tmp_path):
        """Skills habilitados deben aparecer en get_triggered_skills."""
        registry = SkillRegistry(skills_dir=tmp_path, hot_reload=False)
        skill = Skill(
            name="enabled-skill",
            description="Enabled",
            content="Content",
            trigger=["test"],
            enabled=True,
        )
        registry.add_skill(skill)

        triggered = registry.get_triggered_skills("test something")
        assert len(triggered) == 1
        assert triggered[0].name == "enabled-skill"


# ═══════════════════════════════════════════════════════════════════════════════
# Usage Stats
# ═══════════════════════════════════════════════════════════════════════════════


class TestUsageStats:
    """Tests para estadisticas de uso de skills."""

    def test_record_trigger(self, tmp_path):
        """Debe incrementar el counter de triggers."""
        registry = SkillRegistry(skills_dir=tmp_path, hot_reload=False)
        skill = Skill(
            name="tracked-skill",
            description="Tracked",
            content="Content",
            trigger=["test"],
        )
        registry.add_skill(skill)

        registry.record_trigger("tracked-skill")
        assert registry.get("tracked-skill")._times_triggered == 1

        registry.record_trigger("tracked-skill")
        assert registry.get("tracked-skill")._times_triggered == 2

    def test_record_trigger_updates_last_triggered(self, tmp_path):
        """Debe actualizar last_triggered timestamp."""
        registry = SkillRegistry(skills_dir=tmp_path, hot_reload=False)
        skill = Skill(
            name="tracked-skill",
            description="Tracked",
            content="Content",
        )
        registry.add_skill(skill)

        before = time.time()
        registry.record_trigger("tracked-skill")
        after = time.time()

        last_triggered = registry.get("tracked-skill")._last_triggered
        assert last_triggered is not None
        assert before <= last_triggered <= after

    def test_record_trigger_nonexistent(self, tmp_path):
        """No debe lanzar error para skill inexistente."""
        registry = SkillRegistry(skills_dir=tmp_path, hot_reload=False)
        registry.record_trigger("nonexistent")  # Should not raise

    def test_get_usage_stats(self, tmp_path):
        """Debe retornar estadisticas de uso para todos los skills."""
        registry = SkillRegistry(skills_dir=tmp_path, hot_reload=False)
        skill1 = Skill(name="skill-1", description="1", content="C1")
        skill2 = Skill(name="skill-2", description="2", content="C2")
        registry.add_skill(skill1)
        registry.add_skill(skill2)

        registry.record_trigger("skill-1")
        registry.record_trigger("skill-1")
        registry.record_trigger("skill-2")

        stats = registry.get_usage_stats()
        assert stats["skill-1"]["times_triggered"] == 2
        assert stats["skill-1"]["last_triggered"] is not None
        assert stats["skill-2"]["times_triggered"] == 1
        assert stats["skill-2"]["last_triggered"] is not None


# ═══════════════════════════════════════════════════════════════════════════════
# Backward Compatibility
# ═══════════════════════════════════════════════════════════════════════════════


class TestBackwardCompatibility:
    """Tests para retro-compatibilidad con skills existentes."""

    def test_old_skill_md_still_works(self):
        """Un skill MD con solo campos viejos debe seguir funcionando."""
        content = """---
name: old-skill
description: Old skill
trigger:
  - "test"
priority: 50
---

Old content.
"""
        parser = SkillParser()
        skill = parser.parse(content)
        assert skill.name == "old-skill"
        assert skill.trigger == ["test"]
        assert skill.priority == 50
        assert skill.trigger_regex == []
        assert skill.trigger_intent == []
        assert skill.enabled is True
        assert skill.tools_required == []
        assert skill.prompt_template is None

    def test_old_trigger_score_still_works(self):
        """El trigger_score de solo keywords debe funcionar igual que antes."""
        skill = Skill(
            name="test",
            description="Test",
            content="Content",
            trigger=["test", "debug"],
        )
        # Exactamente el mismo comportamiento que antes
        assert skill.trigger_score("test this") == 0.5
        assert skill.trigger_score("test and debug this") == 1.0
        assert skill.trigger_score("nothing relevant") == 0.0

    def test_old_should_trigger_still_works(self):
        """should_trigger con solo keywords debe funcionar igual."""
        skill = Skill(
            name="test",
            description="Test",
            content="Content",
            trigger=["test", "debug"],
        )
        assert skill.should_trigger("I need to test something") is True
        assert skill.should_trigger("hello world") is False

    def test_registry_loads_old_md_skills(self, tmp_path):
        """SkillRegistry debe cargar skills MD existentes sin problemas."""
        skill_file = tmp_path / "old_skill.md"
        skill_file.write_text("""---
name: old-skill
description: Old skill
trigger:
  - "test"
priority: 100
---

Old content.
""")
        registry = SkillRegistry(skills_dir=tmp_path, hot_reload=False)
        assert len(registry.skills) == 1
        skill = registry.get("old-skill")
        assert skill.name == "old-skill"
        assert skill.trigger == ["test"]
        assert skill.trigger_regex == []
        assert skill.enabled is True

    def test_old_to_dict_still_works(self):
        """to_dict debe funcionar para skills viejos."""
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
        # Nuevos campos tambien presentes
        assert d["trigger_regex"] == []
        assert d["trigger_intent"] == []
        assert d["enabled"] is True
        assert d["tools_required"] == []
        assert d["prompt_template"] is None


# ═══════════════════════════════════════════════════════════════════════════════
# Tools Required Validation
# ═══════════════════════════════════════════════════════════════════════════════


class TestToolsRequiredValidation:
    """Tests para validacion de tools_required."""

    def test_skill_with_tools_required_loaded(self, tmp_path):
        """Skills con tools_required deben cargarse normalmente."""
        skill_file = tmp_path / "tool_skill.md"
        skill_file.write_text("""---
name: tool-skill
description: Skill con tools
tools_required:
  - "read_file"
  - "write_file"
---

Content.
""")
        registry = SkillRegistry(skills_dir=tmp_path, hot_reload=False)
        skill = registry.get("tool-skill")
        assert skill is not None
        assert skill.tools_required == ["read_file", "write_file"]

    def test_tools_required_lowers_priority_for_missing_tools(self, tmp_path):
        """Si tools_required tiene tools no disponibles, se baja prioridad."""
        # Crear un mock tool_registry
        class MockToolRegistry:
            _tools = {"read_file": object()}  # Solo read_file disponible

        registry = SkillRegistry(skills_dir=tmp_path, hot_reload=False)
        skill = Skill(
            name="tool-skill",
            description="Skill con tools",
            content="Content",
            priority=100,
            tools_required=["read_file", "missing_tool"],
        )
        registry.add_skill(skill)

        # Sin tool_registry, prioridad se mantiene
        assert skill.priority == 100

        # Con tool_registry, prioridad se baja
        registry.set_tool_registry(MockToolRegistry())
        assert skill.priority < 100  # Prioridad reducida

    def test_tools_required_no_change_if_all_available(self, tmp_path):
        """Si todas las tools estan disponibles, prioridad no cambia."""
        class MockToolRegistry:
            _tools = {"read_file": object(), "write_file": object()}

        registry = SkillRegistry(skills_dir=tmp_path, hot_reload=False)
        skill = Skill(
            name="tool-skill",
            description="Skill con tools",
            content="Content",
            priority=100,
            tools_required=["read_file", "write_file"],
        )
        registry.add_skill(skill)

        registry.set_tool_registry(MockToolRegistry())
        assert skill.priority == 100  # Sin cambio

    def test_skill_without_tools_required_unchanged(self, tmp_path):
        """Skills sin tools_required no deben ser afectados."""
        class MockToolRegistry:
            _tools = {"read_file": object()}

        registry = SkillRegistry(skills_dir=tmp_path, hot_reload=False)
        skill = Skill(
            name="no-tools",
            description="No tools needed",
            content="Content",
            priority=100,
        )
        registry.add_skill(skill)

        registry.set_tool_registry(MockToolRegistry())
        assert skill.priority == 100

    def test_registry_stats_includes_enabled_count(self, tmp_path):
        """get_stats debe incluir conteo de enabled/disabled."""
        registry = SkillRegistry(skills_dir=tmp_path, hot_reload=False)
        skill1 = Skill(name="s1", description="1", content="C", enabled=True)
        skill2 = Skill(name="s2", description="2", content="C", enabled=False)
        registry.add_skill(skill1)
        registry.add_skill(skill2)

        stats = registry.get_stats()
        assert stats["total_skills"] == 2
        assert stats["enabled_skills"] == 1
        assert stats["disabled_skills"] == 1


# ═══════════════════════════════════════════════════════════════════════════════
# YAML Registry Loading
# ═══════════════════════════════════════════════════════════════════════════════


class TestYAMLRegistryLoading:
    """Tests para SkillRegistry cargando archivos YAML."""

    def test_load_yaml_file(self, tmp_path):
        """Debe cargar archivos .yaml desde el directorio."""
        yaml_skill = tmp_path / "skill.yaml"
        yaml_skill.write_text("""name: yaml-skill
description: YAML loaded skill
trigger:
  - "yaml"
content: "YAML content"
""")
        registry = SkillRegistry(skills_dir=tmp_path, hot_reload=False)
        assert "yaml-skill" in registry.skills
        skill = registry.get("yaml-skill")
        assert skill.name == "yaml-skill"

    def test_load_yml_file(self, tmp_path):
        """Debe cargar archivos .yml desde el directorio."""
        yml_skill = tmp_path / "skill.yml"
        yml_skill.write_text("""name: yml-skill
description: YML loaded skill
trigger:
  - "yml"
content: "YML content"
""")
        registry = SkillRegistry(skills_dir=tmp_path, hot_reload=False)
        assert "yml-skill" in registry.skills

    def test_load_md_and_yaml_together(self, tmp_path):
        """Debe cargar .md y .yaml/yml juntos."""
        md_skill = tmp_path / "skill.md"
        md_skill.write_text("""---
name: md-skill
description: MD skill
trigger:
  - "md"
---

MD content.
""")
        yaml_skill = tmp_path / "skill.yaml"
        yaml_skill.write_text("""name: yaml-skill
description: YAML skill
trigger:
  - "yaml"
content: "YAML content"
""")
        registry = SkillRegistry(skills_dir=tmp_path, hot_reload=False)
        assert len(registry.skills) == 2
        assert "md-skill" in registry.skills
        assert "yaml-skill" in registry.skills

    def test_yaml_skill_triggered(self, tmp_path):
        """Skills YAML deben ser encontrados por get_triggered_skills."""
        yaml_skill = tmp_path / "coding.yaml"
        yaml_skill.write_text("""name: coding-helper
description: Coding helper
trigger:
  - "python"
  - "code"
trigger_regex:
  - "\\bpython\\b"
trigger_intent:
  - "coding"
content: "You are a coding assistant."
""")
        registry = SkillRegistry(skills_dir=tmp_path, hot_reload=False)
        triggered = registry.get_triggered_skills("I need help with python code")
        assert len(triggered) == 1
        assert triggered[0].name == "coding-helper"