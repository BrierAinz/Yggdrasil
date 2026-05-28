---
title: Cómo Contribuir al Ecosistema Yggdrasil
category: runbook
severity: standard
last_updated: 2026-05-02
---

# ⚒️ Runbook: Cómo Contribuir al Ecosistema Yggdrasil

> *Los Enanos de Svartalfheim forjan juntos — toda contribución fortalece el Yggdrasil.*

## 🌳 Filosofía de Contribución

Yggdrasil es un ecosistema personal organizado en 9 reinos. Cada contribución, sin importar su tamaño, fortalece las raíces del árbol. Las reglas son simples:

1. **Sin basura regenerable** — No `node_modules`, `__pycache__`, `.map` sueltos
2. **Sin código duplicado** — Un módulo vive en un solo lugar
3. **Sin archivos sueltos** — Todo proyecto tiene README.md y estructura definida
4. **Sin binarios sin fuente** — Si hay `.exe`, debe haber código fuente o build script
5. **Migración explícita** — Todo cambio de reino se documenta en commit y README

---

## 📁 Estructura de Reinos

Antes de contribuir, ubica tu trabajo en el reino correcto:

| Si quieres... | Ve a... |
|---------------|---------|
| Modificar el core (Lilith) | `Asgard/Hermes-Lilith/` |
| Crear/mejorar un bot | `Vanaheim/Bots/` |
| Hacer una UI o dashboard | `Alfheim/ui-seed/` |
| Escribir documentación | `Svartalfheim/` |
| Iniciar un experimento rápido | `Muspelheim/` (max 2 semanas) |
| Agregar modelos/assets | `Niflheim/Models/` |
| Archivar código legacy | `Helheim/` |
| Iniciar un proyecto grande | `Jotunheim/` |
| Hacer apps personales | `Midgard/` |

---

## 🔧 Tipos de Contribución

### 1. Código (Asgard, Vanaheim)

```bash
# 1. Crear feature branch
git checkout -b feature/nombre-descriptivo

# 2. Hacer cambios
# ... editar archivos ...

# 3. Correr tests
pytest -v

# 4. Formatear
black .
isort .

# 5. Commit con convención
git add .
git commit -m "feat: descripción del cambio"
```

**Convención de commits:**
- `feat:` Nueva funcionalidad
- `fix:` Bug fix
- `docs:` Documentación
- `refactor:` Refactor sin cambio funcional
- `test:` Tests
- `chore:` Mantenimiento

### 2. Documentación (Svartalfheim)

La documentación usa **Markdown con frontmatter YAML**:

```markdown
---
name: nombre-del-doc
realm: Asgard
status: Activo
last_updated: 2026-05-02
---

# Título del Documento

Contenido aquí...
```

**Ubicaciones:**
- Wiki pages: `Svartalfheim/wiki/`
- ADRs: `Svartalfheim/wiki/adrs/`
- Runbooks: `Svartalfheim/wiki/runbooks/`
- Arquitectura: `Svartalfheim/Docs/`
- Planes: `Svartalfheim/Docs/plans/`

### 3. Skills (Lilith Skills)

Los skills son archivos YAML+MD en `Asgard/Hermes-Lilith/Lilith/skills/`:

```yaml
---
name: mi-skill
description: Cuando usar este skill
trigger:
  - "keyword1"
trigger_regex:
  - "\\bmi-patron\\b"
trigger_intent:
  - "intent-category"
priority: 80
enabled: true
tools_required:
  - "read_file"
prompt_template: |
  Eres un experto en {{context}}.
  Ayuda con: {{user_input}}
---
```

### 4. ADRs (Architecture Decision Records)

Crear archivo en `Svartalfheim/wiki/adrs/`:

```bash
# Número secuencial: ADR-NNN
# Formato: ADR-NNN-titulo-kebab-case.md
Svartalfheim/wiki/adrs/ADR-011-mi-decision.md
```

Template:
```markdown
---
adr_id: ADR-011
title: Título de la Decisión
status: Proposed | Accepted | Deprecated | Superseded by ADR-NNN
date: 2026-05-02
decision_makers:
  - Nombre
---

## Context
¿Por qué se necesita esta decisión?

## Decision
¿Qué se decidió?

## Consequences
### Positivas
### Negativas
```

---

## 🧪 Testing

```bash
# Tests de todo el ecosistema
pytest -v

# Tests de un módulo específico
pytest Asgard/Hermes-Lilith/Lilith/Core/tests/ -v

# Tests por categoría
pytest -m unit        # Unit tests
pytest -m integration  # Integration tests

# Con coverage
pytest --cov=Lilith --cov-report=html
```

---

## 📏 Estilo de Código

### Python
- **Formatter**: Black (line length: 88)
- **Imports**: isort con profile=black
- **Type hints**: Pydantic para data models
- **Docstrings**: Google style con sabor dark fantasy cuando inspire

### Markdown
- **Frontmatter**: YAML siempre presente
- **Headers**: Con emojis rúnicos cuando apropiado
- **Links**: Relativos dentro del ecosistema

### Commits
- **Formato**: `tipo: descripción en español o inglés`
- **Tipos**: feat, fix, docs, refactor, test, chore
- **Scope**: Opcional, ej: `feat(memory): add consolidation`

---

## 🔄 Flujo de Revisión

```
1. Crear branch
2. Desarrollar + tests
3. Self-review
4. Commit con convención
5. Push al repo
6. Documentar cambios en Svartalfheim si son significativos
```

---

## 📋 Checklist de Contribución

- [ ] Código en el reino correcto
- [ ] Tests pasando (`pytest -v`)
- [ ] Formateado (`black .`, `isort .`)
- [ ] README.md actualizado si hay cambios estructurales
- [ ] Commit con convención
- [ ] Documentación en Svartalfheim si es un cambio significativo
- [ ] ADR si es una decisión arquitectónica
