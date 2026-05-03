"""
Tests de Agent Templates
========================
Tests unitarios para la librería de templates de agentes de Lilith.
"""

import sys
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

_project_root = Path(__file__).parent.parent.parent.parent
if str(_project_root) not in sys.path:
    sys.path.insert(0, str(_project_root))

from Lilith.MCP.templates import (
    AgentTemplate,
    TemplateLibrary,
    TemplateRenderer,
)


# ═══════════════════════════════════════════════════════════════════════════════
# Fixtures
# ═══════════════════════════════════════════════════════════════════════════════


@pytest.fixture
def renderer():
    """Crea un TemplateRenderer."""
    return TemplateRenderer()


@pytest.fixture
def library(tmp_path):
    """Crea una TemplateLibrary con directorio temporal."""
    return TemplateLibrary(templates_dir=tmp_path / "templates")


@pytest.fixture
def researcher_template():
    """Template de researcher para tests."""
    return AgentTemplate(
        name="researcher",
        description="Investigador profundo",
        system_prompt="Eres un investigador especializado en {topic}. Busca información sobre {topic}.",
        allowed_tools=["search_google", "read_file", "open_url"],
        constraints=["No inventar información", "Citar fuentes"],
        variables={"topic": "general"},
        category="builtin",
        version="1.0",
    )


@pytest.fixture
def coder_template():
    """Template de coder para tests."""
    return AgentTemplate(
        name="coder",
        description="Desarrollador de código",
        system_prompt="Eres un desarrollador experto en {language}. Escribe código limpio y eficiente.",
        allowed_tools=["run_terminal", "read_file", "write_file"],
        constraints=["No ejecutar comandos destructivos"],
        variables={"language": "Python"},
        category="builtin",
        version="1.0",
    )


# ═══════════════════════════════════════════════════════════════════════════════
# Test AgentTemplate dataclass
# ═══════════════════════════════════════════════════════════════════════════════


class TestAgentTemplate:
    """Tests para la dataclass AgentTemplate."""

    def test_template_creation(self):
        """Una template se crea correctamente."""
        t = AgentTemplate(name="test", description="Test template")
        assert t.name == "test"
        assert t.description == "Test template"
        assert t.allowed_tools == []
        assert t.constraints == []
        assert t.category == "builtin"
        assert t.version == "1.0"

    def test_template_custom_values(self, researcher_template):
        """Una template con valores custom se crea correctamente."""
        assert researcher_template.name == "researcher"
        assert researcher_template.description == "Investigador profundo"
        assert len(researcher_template.allowed_tools) == 3
        assert len(researcher_template.constraints) == 2
        assert researcher_template.variables == {"topic": "general"}

    def test_template_to_dict(self, researcher_template):
        """to_dict serializa correctamente."""
        d = researcher_template.to_dict()
        assert d["name"] == "researcher"
        assert d["description"] == "Investigador profundo"
        assert d["allowed_tools"] == ["search_google", "read_file", "open_url"]
        assert d["variables"] == {"topic": "general"}
        assert d["category"] == "builtin"

    def test_template_from_dict(self):
        """from_dict deserializa correctamente."""
        data = {
            "name": "analyst",
            "description": "Data analyst",
            "system_prompt": "Analyze {data_type} data",
            "allowed_tools": ["run_python_script"],
            "constraints": ["Be objective"],
            "variables": {"data_type": "financial"},
            "category": "custom",
            "version": "2.0",
        }
        t = AgentTemplate.from_dict(data)
        assert t.name == "analyst"
        assert t.description == "Data analyst"
        assert t.system_prompt == "Analyze {data_type} data"
        assert t.allowed_tools == ["run_python_script"]
        assert t.category == "custom"
        assert t.version == "2.0"

    def test_template_roundtrip(self, researcher_template):
        """Serializar y deserializar preserva los datos."""
        data = researcher_template.to_dict()
        restored = AgentTemplate.from_dict(data)
        assert restored.name == researcher_template.name
        assert restored.description == researcher_template.description
        assert restored.system_prompt == researcher_template.system_prompt
        assert restored.allowed_tools == researcher_template.allowed_tools
        assert restored.constraints == researcher_template.constraints

    def test_template_to_yaml(self, researcher_template):
        """to_yaml produce un YAML válido."""
        yaml_str = researcher_template.to_yaml()
        assert 'name: "researcher"' in yaml_str
        assert "---" in yaml_str
        assert "Eres un investigador" in yaml_str

    def test_template_from_yaml(self):
        """from_yaml parsea una template YAML correctamente."""
        yaml_content = '''name: "my_template"
description: "My custom template"
category: "custom"
version: "1.0"
allowed_tools:
  - "tool_a"
  - "tool_b"
constraints:
  - "Be careful"
---
You are a {role} agent specializing in {domain}.'''
        t = AgentTemplate.from_yaml(yaml_content)
        assert t.name == "my_template"
        assert t.description == "My custom template"
        assert t.category == "custom"
        assert "tool_a" in t.allowed_tools
        assert "Be careful" in t.constraints
        assert "{role}" in t.system_prompt
        assert "{domain}" in t.system_prompt

    def test_template_from_yaml_with_frontmatter_only(self):
        """from_yaml con solo frontmatter (sin system_prompt en body)."""
        yaml_content = '''name: "minimal"
description: "Minimal template"
system_prompt: "Built-in prompt"
---
'''
        t = AgentTemplate.from_yaml(yaml_content)
        assert t.name == "minimal"
        # El system_prompt viene del body o del frontmatter
        assert t.system_prompt  # No vacío


# ═══════════════════════════════════════════════════════════════════════════════
# Test TemplateRenderer
# ═══════════════════════════════════════════════════════════════════════════════


class TestTemplateRenderer:
    """Tests para el TemplateRenderer."""

    def test_render_basic(self, renderer, researcher_template):
        """render reemplaza variables en el system prompt."""
        result = renderer.render(researcher_template, variables={"topic": "Python"})
        assert "Python" in result
        assert "{topic}" not in result

    def test_render_with_default_variables(self, renderer, researcher_template):
        """render usa defaults de la template si no se proveen variables."""
        result = renderer.render(researcher_template)
        assert "general" in result  # Default de "topic"

    def test_render_override_defaults(self, renderer, researcher_template):
        """render permite sobreescribir los defaults."""
        result = renderer.render(researcher_template, variables={"topic": "IA"})
        assert "IA" in result
        assert "general" not in result

    def test_render_multiple_variables(self, renderer):
        """render maneja múltiples variables."""
        t = AgentTemplate(
            name="multi",
            system_prompt="Eres {role} en {domain} con nivel {level}.",
            variables={"role": "asistente", "domain": "tecnología", "level": "avanzado"},
        )
        result = renderer.render(t, variables={"role": "experto", "domain": "medicina"})
        assert "experto" in result
        assert "medicina" in result
        assert "avanzado" in result  # Default, no sobreescribió

    def test_render_no_variables(self, renderer):
        """render con template sin variables retorna el prompt tal cual."""
        t = AgentTemplate(name="simple", system_prompt="Eres un agente útil.")
        result = renderer.render(t)
        assert result == "Eres un agente útil."

    def test_render_missing_variable_keeps_placeholder(self, renderer):
        """Variables sin default ni valor se mantienen como placeholders."""
        t = AgentTemplate(name="incomplete", system_prompt="Eres {unknown_var}.")
        result = renderer.render(t)
        assert "{unknown_var}" in result

    def test_render_full(self, renderer, researcher_template):
        """render_full retorna la configuración completa renderizada."""
        result = renderer.render_full(researcher_template, variables={"topic": "Rust"})
        assert "name" in result
        assert "system_prompt" in result
        assert "allowed_tools" in result
        assert result["name"] == "researcher"
        assert "Rust" in result["system_prompt"]
        assert "search_google" in result["allowed_tools"]

    def test_extract_variables(self, renderer):
        """extract_variables encuentra todas las variables en un texto."""
        text = "Eres {role} especializado en {domain}. Nivel: {level}."
        vars_found = renderer.extract_variables(text)
        assert set(vars_found) == {"role", "domain", "level"}

    def test_extract_variables_no_vars(self, renderer):
        """extract_variables retorna lista vacía si no hay variables."""
        text = "Eres un agente sin variables."
        vars_found = renderer.extract_variables(text)
        assert vars_found == []


# ═══════════════════════════════════════════════════════════════════════════════
# Test TemplateLibrary
# ═══════════════════════════════════════════════════════════════════════════════


class TestTemplateLibrary:
    """Tests para la TemplateLibrary."""

    def test_library_creation(self, library):
        """La librería se crea correctamente con templates built-in."""
        assert len(library.list_templates()) >= 5  # researcher, coder, analyst, reviewer, creative

    def test_list_builtin_templates(self, library):
        """list_templates retorna las templates built-in."""
        builtins = library.list_templates(category="builtin")
        names = [t.name for t in builtins]
        assert "researcher" in names
        assert "coder" in names
        assert "analyst" in names
        assert "reviewer" in names
        assert "creative" in names

    def test_list_custom_templates(self, library):
        """list_templates con category=custom retorna solo custom."""
        custom = library.list_templates(category="custom")
        for t in custom:
            assert t.category == "custom"

    def test_get_builtin_template(self, library):
        """get retorna una template built-in."""
        t = library.get("researcher")
        assert t is not None
        assert t.name == "researcher"
        assert t.category == "builtin"

    def test_get_nonexistent_template(self, library):
        """get retorna None para template inexistente."""
        t = library.get("nonexistent_template")
        assert t is None

    def test_save_template(self, library):
        """save_template guarda una template custom."""
        t = AgentTemplate(
            name="my_custom",
            description="Mi template custom",
            system_prompt="Eres un agente {role}.",
            variables={"role": "asistente"},
        )
        filepath = library.save_template(t)
        assert filepath.exists()
        assert t.category == "custom"

    def test_save_and_retrieve_template(self, library):
        """Guardar y recuperar una template custom funciona."""
        t = AgentTemplate(
            name="saved",
            description="Template guardada",
            system_prompt="Prompt {var}.",
            allowed_tools=["tool1"],
            variables={"var": "default"},
        )
        library.save_template(t)

        # Crear nueva librería que cargue desde el mismo dir
        library2 = TemplateLibrary(templates_dir=library.templates_dir)
        retrieved = library2.get("saved")
        assert retrieved is not None
        assert retrieved.name == "saved"
        assert retrieved.category == "custom"

    def test_delete_template(self, library):
        """delete_template elimina una template custom."""
        t = AgentTemplate(name="to_delete", description="Temporal")
        library.save_template(t)
        assert library.get("to_delete") is not None

        result = library.delete_template("to_delete")
        assert result is True
        assert library.get("to_delete") is None

    def test_delete_builtin_template_fails(self, library):
        """delete_template retorna False para templates built-in."""
        result = library.delete_template("researcher")
        assert result is False

    def test_custom_overrides_builtin(self, tmp_path):
        """Una template custom sobreescribe una built-in del mismo nombre."""
        lib = TemplateLibrary(templates_dir=tmp_path / "templates")

        # Crear una template custom con nombre "researcher"
        custom = AgentTemplate(
            name="researcher",
            description="Custom researcher",
            system_prompt="Eres un investigador custom.",
            category="custom",
        )
        lib.save_template(custom)

        # Recargar
        lib2 = TemplateLibrary(templates_dir=lib.templates_dir)
        result = lib2.get("researcher")
        assert result is not None
        # La custom debería tener prioridad
        assert result.description == "Custom researcher"

    def test_reload(self, library):
        """reload recarga las templates custom desde disco."""
        # Guardar una template
        t = AgentTemplate(name="reload_test", description="Test de reload")
        library.save_template(t)

        # Recargar
        count = library.reload()
        assert count >= 1
        assert library.get("reload_test") is not None

    def test_builtin_templates_have_tools(self, library):
        """Las templates built-in tienen tools permitidas."""
        for name in ["researcher", "coder", "analyst", "reviewer", "creative"]:
            t = library.get(name)
            assert t is not None, f"Template {name} no encontrada"
            assert len(t.allowed_tools) > 0, f"Template {name} no tiene tools"

    def test_builtin_templates_have_prompts(self, library):
        """Las templates built-in tienen system prompts."""
        for name in ["researcher", "coder", "analyst", "reviewer", "creative"]:
            t = library.get(name)
            assert t is not None
            assert len(t.system_prompt) > 0

    def test_builtin_templates_have_constraints(self, library):
        """Las templates built-in tienen constraints."""
        for name in ["researcher", "coder", "analyst", "reviewer", "creative"]:
            t = library.get(name)
            assert t is not None
            assert len(t.constraints) > 0

    def test_builtin_templates_have_variables(self, library):
        """Las templates built-in tienen variables de template."""
        for name in ["researcher", "coder", "analyst", "reviewer", "creative"]:
            t = library.get(name)
            assert t is not None
            assert len(t.variables) > 0


# ═══════════════════════════════════════════════════════════════════════════════
# Test YAML serialization roundtrip
# ═══════════════════════════════════════════════════════════════════════════════


class TestTemplateYAMLRoundtrip:
    """Tests de serialización/deserialización YAML de templates."""

    def test_yaml_roundtrip_simple(self):
        """Una template simple sobrevive un roundtrip YAML."""
        original = AgentTemplate(
            name="simple",
            description="Template simple",
            system_prompt="Eres un agente simple.",
        )
        yaml_str = original.to_yaml()
        restored = AgentTemplate.from_yaml(yaml_str)
        assert restored.name == "simple"
        assert restored.description == "Template simple"

    def test_yaml_roundtrip_with_tools(self):
        """Una template con tools sobrevive un roundtrip YAML."""
        original = AgentTemplate(
            name="equipped",
            description="Template con tools",
            system_prompt="Eres un agente equipado.",
            allowed_tools=["tool_a", "tool_b", "tool_c"],
        )
        yaml_str = original.to_yaml()
        restored = AgentTemplate.from_yaml(yaml_str)
        assert restored.name == "equipped"
        assert "tool_a" in restored.allowed_tools
        assert "tool_b" in restored.allowed_tools
        assert "tool_c" in restored.allowed_tools

    def test_yaml_roundtrip_with_constraints(self):
        """Una template con constraints sobrevive un roundtrip YAML."""
        original = AgentTemplate(
            name="constrained",
            description="Template con constraints",
            system_prompt="Eres un agente con reglas.",
            constraints=["No inventar", "Ser preciso"],
        )
        yaml_str = original.to_yaml()
        restored = AgentTemplate.from_yaml(yaml_str)
        assert "No inventar" in restored.constraints
        assert "Ser preciso" in restored.constraints

    def test_yaml_roundtrip_with_variables(self):
        """Una template con variables sobrevive un roundtrip YAML."""
        original = AgentTemplate(
            name="variable",
            description="Template con variables",
            system_prompt="Eres {role} en {domain}.",
            variables={"role": "experto", "domain": "tecnología"},
        )
        yaml_str = original.to_yaml()
        restored = AgentTemplate.from_yaml(yaml_str)
        assert restored.name == "variable"
        # Las variables se serializan en el YAML
        assert "role" in restored.variables
        assert restored.variables["role"] == "experto"


# ═══════════════════════════════════════════════════════════════════════════════
# Test singleton
# ═══════════════════════════════════════════════════════════════════════════════


class TestTemplateLibrarySingleton:
    """Tests del singleton de TemplateLibrary."""

    def test_get_template_library_returns_instance(self):
        """get_template_library retorna una instancia."""
        import Lilith.MCP.templates as templates_mod
        templates_mod._library_instance = None  # Reset
        lib = templates_mod.get_template_library()
        assert isinstance(lib, TemplateLibrary)

    def test_get_template_library_singleton(self):
        """get_template_library retorna la misma instancia."""
        import Lilith.MCP.templates as templates_mod
        templates_mod._library_instance = None  # Reset
        l1 = templates_mod.get_template_library()
        l2 = templates_mod.get_template_library()
        assert l1 is l2


# ═══════════════════════════════════════════════════════════════════════════════
# Test dark fantasy aesthetic
# ═══════════════════════════════════════════════════════════════════════════════


class TestDarkFantasyAesthetic:
    """Tests que verifican la estética dark fantasy de las templates."""

    def test_creative_template_genre(self, library):
        """La template creative tiene género de fantasía oscura por defecto."""
        t = library.get("creative")
        assert t is not None
        assert t.variables.get("genre") == "fantasía oscura"

    def test_researcher_has_topic_variable(self, library):
        """La template researcher tiene variable topic."""
        t = library.get("researcher")
        assert "topic" in t.variables

    def test_coder_has_language_variable(self, library):
        """La template coder tiene variable language."""
        t = library.get("coder")
        assert "language" in t.variables