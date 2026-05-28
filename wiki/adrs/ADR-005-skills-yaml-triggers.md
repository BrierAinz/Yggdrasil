---
adr_id: ADR-005
title: Skills como YAML Templates con trigger_regex
status: Accepted
date: 2026-04-29
decision_makers:
  - Völundr
  - Hermes
---

# ⚔️ ADR-005: Skills como YAML Templates con trigger_regex

## Context

Lilith necesita un sistema de skills dinámicos que se activen automáticamente según la intención del usuario. Las opciones eran: hardcodear skills en Python (rígido), usar solo keywords (impreciso), o definir skills como templates con triggers flexibles.

## Decision

Implementar **skills como archivos YAML+MD** con frontmatter y triggers:

1. **Formato dual**: YAML frontmatter + Markdown body para contenido
2. **Triggers múltiples**:
   - `trigger`: Keywords exactos para matching simple
   - `trigger_regex`: Regex para matching avanzado
   - `trigger_intent`: Categorías semánticas (coding, writing, etc.)
3. **Prioridad**: Skills con `priority` mayor se ejecutan primero
4. **`tools_required`**: Declaración de tools que el skill necesita
5. **`prompt_template`**: Templates Jinja2 con variables `{{user_input}}` y `{{context}}`

Ejemplo de skill:

```yaml
---
name: writing
description: Creative writing and content generation
trigger:
  - "write"
  - "draft"
trigger_regex:
  - "write\\s+(a\\s+)?(blog|article|essay|story)"
trigger_intent:
  - "writing"
priority: 75
enabled: true
tools_required: []
prompt_template: |
  You are a skilled writer. Help with: {{user_input}}
  Context: {{context}}
---
```

El `SkillParser` soporta tanto `.md` (con frontmatter) como `.yaml/.yml` puro.

## Consequences

### Positivas
- **Declarativo**: No requiere código Python para nuevos skills
- **Flexible**: Tres niveles de matching (keyword, regex, intent)
- **Hot-reload**: Se pueden agregar skills sin reiniciar
- **Priorizable**: Skills compiten por relevancia con `priority`

### Negativas
- **YAML parsing**: Puede ser frágil si el frontmatter tiene errores
- **Regex complexity**: `trigger_regex` requiere conocimiento de regex
- **Intent matching**: Los `trigger_intent` dependen de heuristicas, no de NLU
