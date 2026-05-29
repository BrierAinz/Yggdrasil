<<<<<<< HEAD
"""Skill management and discovery for Lilith."""

=======
"""Lilith Skills — Yggdrasil Knowledge Loader.

Load, parse, and search the skill collection stored in
Svartalfheim/Docs/skills/ within the Yggdrasil monorepo.
"""

from lilith_skills.context import SkillContext
from lilith_skills.loader import SkillLoader
from lilith_skills.models import Skill, SkillManifest
from lilith_skills.registry import SkillRegistry


__all__ = ["Skill", "SkillContext", "SkillLoader", "SkillManifest", "SkillRegistry"]
>>>>>>> origin/main
__version__ = "1.0.0"
