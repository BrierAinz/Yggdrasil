---
sidebar_position: 6
title: Svartalfheim
---

# ᛊ Svartalfheim — La Forja de los Enanos

Svartalfheim es el reino de las herramientas y los skills. Aquí se forjan las capacidades del agente.

## Skills

Los skills son scripts reutilizables que extienden las capacidades de Lilith. Cada skill tiene:
- **SKILL.md** — Documentación y instrucciones
- **scripts/** — Código ejecutable
- **templates/** — Plantillas reutilizables
- **references/** — Documentación de referencia

### Categorías de Skills

| Categoría | Ejemplos |
|-----------|----------|
| autonomous-ai-agents | claude-code, codex, hermes-agent |
| creative | ascii-art, architecture-diagram, comfyui |
| devops | kanban-orchestrator, docusaurus-github-pages |
| gaming | game-ai-engines, minecraft-modpack-server |
| github | github-pr-workflow, github-code-review |
| mlops | vllm, llama-cpp, huggingface-hub |
| productivity | notion, obsidian, google-workspace |

## Crear un Skill

```bash
# Desde el CLI de Hermes
hermes skill create my-skill --category devops
```

## Principio

Las herramientas se forjan con precisión. Un skill mal diseñado es peor que ningún skill.
