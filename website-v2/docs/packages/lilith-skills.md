---
sidebar_position: 7
title: lilith-skills
---

# lilith-skills

Skill loading system. Reads SKILL.md files from the filesystem and parses them into structured objects.

## Skill Structure

```
skills/
├── creative/
│   ├── comfyui/
│   │   └── SKILL.md
│   └── ascii-art/
│       └── SKILL.md
├── devops/
│   └── docusaurus/
│       └── SKILL.md
└── gaming/
    └── minecraft/
        └── SKILL.md
```

## Quick Start

```python
from lilith_skills.loader import SkillLoader

# Load skills from directory
loader = SkillLoader(Path("skills/"))
skills = loader.load_all()

for skill in skills:
    print(f"{skill.name}: {skill.description}")
```

## SKILL.md Format

```markdown
---
name: my-skill
description: "What this skill does"
version: 1.0.0
tags: [devops, automation]
---

# My Skill

Instructions for the agent...

## Steps

1. Do this
2. Do that
```
