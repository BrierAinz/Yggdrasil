"""
Tests para Skill Registry
=========================
RED-GREEN-REFACTOR: TDD estricto para el registry de skills.
"""
import os
import time
from pathlib import Path

import pytest
from Lilith.Core.skill_parser import Skill
from Lilith.Core.skill_registry import SkillRegistry


class TestSkillRegistry:
    """Tests para el registro de skills."""

    def test_load_skills_from_directory(self, tmp_path):
        """RED: Debe cargar skills desde directorio."""
        # Crear skills de prueba
        skill1 = tmp_path / "skill1.md"
        skill1.write_text(
            """---
name: skill-one
description: First skill
trigger:
  - "test"
priority: 100
---

Content one.
"""
        )
        skill2 = tmp_path / "skill2.md"
        skill2.write_text(
            """---
name: skill-two
description: Second skill
trigger:
  - "debug"
priority: 50
---

Content two.
"""
        )

        registry = SkillRegistry(skills_dir=tmp_path, hot_reload=False)

        assert len(registry.skills) == 2
        assert "skill-one" in registry.skills
        assert "skill-two" in registry.skills

    def test_load_skills_empty_directory(self, tmp_path):
        """RED: Debe manejar directorio vacio."""
        registry = SkillRegistry(skills_dir=tmp_path, hot_reload=False)
        assert len(registry.skills) == 0

    def test_load_skills_creates_directory(self, tmp_path):
        """RED: Debe crear directorio si no existe."""
        nonexistent = tmp_path / "nonexistent" / "skills"
        registry = SkillRegistry(skills_dir=nonexistent, hot_reload=False)
        assert nonexistent.exists()

    def test_get_skill(self, tmp_path):
        """RED: Debe obtener skill por nombre."""
        skill_file = tmp_path / "test.md"
        skill_file.write_text(
            """---
name: test-skill
description: Test
---

Content.
"""
        )
        registry = SkillRegistry(skills_dir=tmp_path, hot_reload=False)

        skill = registry.get("test-skill")
        assert skill is not None
        assert skill.name == "test-skill"

    def test_get_skill_not_found(self, tmp_path):
        """RED: Debe retornar None si skill no existe."""
        registry = SkillRegistry(skills_dir=tmp_path, hot_reload=False)
        assert registry.get("nonexistent") is None

    def test_list_skills_sorted_by_priority(self, tmp_path):
        """RED: Debe listar skills ordenados por prioridad."""
        skill1 = tmp_path / "low.md"
        skill1.write_text(
            """---
name: low-priority
description: Low
trigger:
  - "test"
priority: 10
---

Content.
"""
        )
        skill2 = tmp_path / "high.md"
        skill2.write_text(
            """---
name: high-priority
description: High
trigger:
  - "test"
priority: 100
---

Content.
"""
        )

        registry = SkillRegistry(skills_dir=tmp_path, hot_reload=False)
        skills = registry.list_skills()

        assert skills[0].name == "high-priority"
        assert skills[1].name == "low-priority"

    def test_get_triggered_skills(self, tmp_path):
        """RED: Debe encontrar skills por trigger."""
        skill1 = tmp_path / "test.md"
        skill1.write_text(
            """---
name: test-skill
description: Test skill
trigger:
  - "test"
  - "testing"
priority: 100
---

Content.
"""
        )
        skill2 = tmp_path / "debug.md"
        skill2.write_text(
            """---
name: debug-skill
description: Debug skill
trigger:
  - "debug"
priority: 50
---

Content.
"""
        )

        registry = SkillRegistry(skills_dir=tmp_path, hot_reload=False)
        triggered = registry.get_triggered_skills("I need to test this", max_skills=3)

        assert len(triggered) == 1
        assert triggered[0].name == "test-skill"

    def test_get_triggered_skills_multiple(self, tmp_path):
        """RED: Debe encontrar multiples skills ordenados por score."""
        skill1 = tmp_path / "test.md"
        skill1.write_text(
            """---
name: test-skill
description: Test
trigger:
  - "test"
  - "debug"
priority: 100
---

Content.
"""
        )
        skill2 = tmp_path / "code.md"
        skill2.write_text(
            """---
name: code-skill
description: Code
trigger:
  - "test"
  - "code"
priority: 50
---

Content.
"""
        )

        registry = SkillRegistry(skills_dir=tmp_path, hot_reload=False)
        triggered = registry.get_triggered_skills("test code", max_skills=3)

        assert len(triggered) == 2
        # code-skill: score=1.0 (2/2 matches: "test" + "code"), priority=50
        # test-skill: score=0.5 (1/2 matches: "test" only), priority=100
        # Mejor score gana aunque priority sea menor
        assert triggered[0].name == "code-skill"
        assert triggered[1].name == "test-skill"

    def test_get_triggered_skills_max_limit(self, tmp_path):
        """RED: Debe respetar limite max_skills."""
        for i in range(5):
            skill_file = tmp_path / f"skill{i}.md"
            skill_file.write_text(
                f"""---
name: skill-{i}
description: Skill {i}
trigger:
  - "test"
priority: {100 - i}
---

Content.
"""
            )

        registry = SkillRegistry(skills_dir=tmp_path, hot_reload=False)
        triggered = registry.get_triggered_skills("test", max_skills=2)

        assert len(triggered) == 2

    def test_get_triggered_skills_no_match(self, tmp_path):
        """RED: Debe retornar lista vacia sin matches."""
        skill_file = tmp_path / "test.md"
        skill_file.write_text(
            """---
name: test-skill
description: Test
trigger:
  - "test"
---

Content.
"""
        )

        registry = SkillRegistry(skills_dir=tmp_path, hot_reload=False)
        triggered = registry.get_triggered_skills("hello world", max_skills=3)

        assert len(triggered) == 0

    def test_add_skill_manually(self, tmp_path):
        """RED: Debe agregar skill manualmente."""
        registry = SkillRegistry(skills_dir=tmp_path, hot_reload=False)
        skill = Skill(
            name="manual-skill",
            description="Manual",
            content="Content",
        )

        registry.add_skill(skill)
        assert registry.get("manual-skill") == skill

    def test_remove_skill(self, tmp_path):
        """RED: Debe eliminar skill."""
        skill_file = tmp_path / "test.md"
        skill_file.write_text(
            """---
name: test-skill
description: Test
---

Content.
"""
        )

        registry = SkillRegistry(skills_dir=tmp_path, hot_reload=False)
        assert registry.remove_skill("test-skill") is True
        assert registry.get("test-skill") is None

    def test_remove_skill_not_found(self, tmp_path):
        """RED: Debe retornar False si skill no existe."""
        registry = SkillRegistry(skills_dir=tmp_path, hot_reload=False)
        assert registry.remove_skill("nonexistent") is False

    def test_reload(self, tmp_path):
        """RED: Debe recargar todos los skills."""
        skill_file = tmp_path / "test.md"
        skill_file.write_text(
            """---
name: test-skill
description: Test
---

Content.
"""
        )

        registry = SkillRegistry(skills_dir=tmp_path, hot_reload=False)
        assert len(registry.skills) == 1

        # Agregar otro skill
        skill2 = tmp_path / "new.md"
        skill2.write_text(
            """---
name: new-skill
description: New
---

Content.
"""
        )

        reloaded = registry.reload()
        assert len(registry.skills) == 2
        assert "new-skill" in reloaded

    def test_reload_file(self, tmp_path):
        """RED: Debe recargar un skill especifico."""
        skill_file = tmp_path / "test.md"
        skill_file.write_text(
            """---
name: test-skill
description: Test
---

Content.
"""
        )

        registry = SkillRegistry(skills_dir=tmp_path, hot_reload=False)

        # Modificar archivo
        skill_file.write_text(
            """---
name: test-skill
description: Updated
---

Updated content.
"""
        )

        result = registry.reload_file(skill_file)
        assert result == "test-skill"
        assert registry.get("test-skill").description == "Updated"

    def test_stats(self, tmp_path):
        """RED: Debe retornar estadisticas."""
        skill_file = tmp_path / "test.md"
        skill_file.write_text(
            """---
name: test-skill
description: Test
---

Content.
"""
        )

        registry = SkillRegistry(skills_dir=tmp_path, hot_reload=False)
        stats = registry.get_stats()

        assert stats["total_skills"] == 1
        assert stats["hot_reload"] is False
        assert "test-skill" in stats["skill_names"]

    def test_on_reload_callback(self, tmp_path):
        """RED: Debe llamar callback en reload."""
        skill_file = tmp_path / "test.md"
        skill_file.write_text(
            """---
name: test-skill
description: Test
---

Content.
"""
        )

        registry = SkillRegistry(skills_dir=tmp_path, hot_reload=False)

        called_with = []

        def callback(skills):
            called_with.extend(skills)

        registry.on_reload(callback)
        registry.reload()

        assert "test-skill" in called_with

    def test_ignores_hidden_files(self, tmp_path):
        """RED: Debe ignorar archivos ocultos."""
        hidden = tmp_path / ".hidden.md"
        hidden.write_text(
            """---
name: hidden
description: Hidden
---

Content.
"""
        )

        registry = SkillRegistry(skills_dir=tmp_path, hot_reload=False)
        assert registry.get("hidden") is None

    def test_ignores_non_md_files(self, tmp_path):
        """RED: Debe ignorar archivos que no son .md."""
        txt = tmp_path / "test.txt"
        txt.write_text(
            """---
name: txt-skill
description: TXT
---

Content.
"""
        )

        registry = SkillRegistry(skills_dir=tmp_path, hot_reload=False)
        assert registry.get("txt-skill") is None


class TestSkillRegistryHotReload:
    """Tests para hot-reload (requiere watchdog + filesystem real)."""

    @pytest.mark.skip(reason="watchdog no detecta eventos en entorno de test WSL/tmpfs")
    def test_hot_reload_detects_new_file(self, tmp_path):
        """RED: Debe detectar nuevo skill."""
        registry = SkillRegistry(skills_dir=tmp_path, hot_reload=True)

        # Esperar a que el watcher inicie
        time.sleep(0.5)

        # Crear nuevo skill
        new_skill = tmp_path / "new.md"
        new_skill.write_text(
            """---
name: hot-reload-skill
description: Hot reload test
trigger:
  - "hot"
---

Content.
"""
        )

        # Retry loop: esperar hasta 5 segundos
        found = False
        for _ in range(50):
            time.sleep(0.1)
            if registry.get("hot-reload-skill") is not None:
                found = True
                break

        assert found, "Hot-reload no detecto nuevo skill en 5s"

        # Cleanup
        registry.stop_watching()

    @pytest.mark.skip(reason="watchdog no detecta eventos en entorno de test WSL/tmpfs")
    def test_hot_reload_detects_modification(self, tmp_path):
        """RED: Debe detectar modificacion de skill."""
        skill_file = tmp_path / "test.md"
        skill_file.write_text(
            """---
name: test-skill
description: Original
---

Original content.
"""
        )

        registry = SkillRegistry(skills_dir=tmp_path, hot_reload=True)
        time.sleep(0.5)

        assert registry.get("test-skill").description == "Original"

        # Modificar
        skill_file.write_text(
            """---
name: test-skill
description: Updated
---

Updated content.
"""
        )

        # Retry loop: esperar hasta 5 segundos
        updated = False
        for _ in range(50):
            time.sleep(0.1)
            skill = registry.get("test-skill")
            if skill and skill.description == "Updated":
                updated = True
                break

        assert updated, "Hot-reload no detecto modificacion en 5s"

        # Cleanup
        registry.stop_watching()
