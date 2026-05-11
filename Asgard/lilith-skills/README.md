# Lilith Skills — Yggdrasil Knowledge Loader

Skill loader and registry for the Yggdrasil knowledge base. Loads, parses,
and searches the skill collection stored in `Svartalfheim/Docs/skills/`.

## Usage

```python
from lilith_skills import SkillRegistry

# Auto-discover skills from Yggdrasil repo
registry = SkillRegistry.from_repo("/mnt/d/Proyectos/Yggdrasil")

# List all skills
for skill in registry.list_skills():
    print(f"{skill.category}/{skill.name}: {skill.description}")

# Search skills
results = registry.search("comfyui")
for skill in results:
    print(skill.name, skill.tags)

# Load a specific skill's full content
skill = registry.get("mlops/lora-training-pipeline")
print(skill.content[:500])

# Get skills by category
creative = registry.by_category("creative")
print(f"{len(creative)} creative skills")

# Export skill as context for LLM prompt
prompt = registry.get("software-development/yggdrasil-ecosystem").to_prompt()
```

## Skill Format

Each skill lives in a directory under its category:

```
skills/
└── mlops/
    └── lora-training-pipeline/
        ├── SKILL.md          # Main document (YAML frontmatter + markdown)
        ├── references/       # Supplementary docs
        ├── scripts/          # Executable scripts
        └── templates/        # File templates
```

SKILL.md frontmatter:
```yaml
---
name: lora-training-pipeline
description: Full LoRA training pipeline...
trigger: When fine-tuning character/person generation...
tags: [lora, training, ai-image-generation, pixai, kohya]
version: 1.0.0
---
```

---

*᛭ Yggdrasil — Where knowledge takes root*
