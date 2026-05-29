# SkillTree — Mapa Interactivo de Aprendizaje

> **For Hermes:** Use subagent-driven-development skill to implement this plan task-by-task.

**Goal:** Define skill trees (tipo RPG) para cualquier dominio, con prerrequisitos, recursos, y checkpoints de validación. Visualización web interactiva tipo árbol de habilidades de videojuego.

**Architecture:** YAML skill tree definitions → SQLite storage → validation engine → web visualization (D3.js/Canvas). CLI para crear, editar y trackear progreso.

**Tech Stack:** Python 3.11+, SQLite, Typer, Rich, FastAPI, Jinja2, D3.js/SVG.

**Realm:** Svartalfheim/SkillTree/

---

## Task 1: Scaffold del proyecto

Files: `Svartalfheim/SkillTree/`, pyproject.toml con typer, rich, fastapi, jinja2, pyyaml, svgwrite.

**Commit:** `feat(skilltree): scaffold project`

---

## Task 2: Skill tree data model

```python
@dataclass
class Skill:
    id: str                    # e.g. "python-oop"
    name: str                  # "Object-Oriented Programming"
    description: str
    category: str               # "programming", "music", "languages"
    difficulty: int            # 1-5 (XP levels)
    prerequisites: list[str]   # skill IDs
    resources: list[Resource]
    checkpoints: list[Checkpoint]
    xp_reward: int

@dataclass
class Resource:
    title: str
    url: str
    type: str  # article, video, course, book, practice
    estimated_hours: float

@dataclass
class Checkpoint:
    id: str
    description: str
    validation_type: str  # quiz, project, self-assessment
    questions: list[dict] | None  # for quiz type
    project_description: str | None  # for project type
```

YAML format para definir árboles. SQLite para progreso del usuario.

**Commit:** `feat(skilltree): data model and YAML schema`

---

## Task 3: Skill tree parser y validator

Parser YAML → Skill objects. Validación: ciclos en prereqs, IDs duplicados, prereqs inexistentes, orfanos.

**Commit:** `feat(skilltree): YAML parser and validator`

---

## Task 4: Progreso del usuario

Tracking: qué skills completados, XP total, % completion por rama, streaks. CLI para marcar skills como completados.

```bash
skilltree complete python-oop
skilltree progress                  # show overall progress
skilltree next                      # suggest next available skills
```

**Commit:** `feat(skilltree): user progress tracking`

---

## Task 5: Validación de checkpoints

Quiz mode: presenta preguntas, evalúa respuestas. Project mode: describe proyecto, auto-assessment. Self-assessment: confirmar con rating de confianza.

**Commit:** `feat(skilltree): checkpoint validation`

---

## Task 6: Web visualization (D3.js)

Interactivo skill tree SVG con D3.js:
- Nodos = skills, líneas = prereqs
- Colores por estado (locked → available → in-progress → completed)
- Hover muestra descripción, recursos, checkpoints
- Click para ver detalles y marcar progreso
- Zoom y pan

Dark theme Yggdrasil.

**Commit:** `feat(skilltree): D3.js web visualization`

---

## Task 7: Templates predefinidos

Skill trees para:
- Python programming (beginner → advanced)
- Web development (frontend → backend)
- Machine learning (math → DL)
- Music production
- Language learning

**Commit:** `feat(skilltree): predefined skill tree templates`

---

## Task 8: CLI completa

```bash
skilltree create my-tree.yaml      # crear desde YAML
skilltree validate my-tree.yaml    # validar estructura
skilltree progress                  # show progress
skilltree next                      # suggest next skills
skilltree complete <skill-id>       # mark skill complete
skilltree quiz <skill-id>           # take checkpoint quiz
skilltree web                       # launch web visualization
```

**Commit:** `feat(skilltree): complete CLI`

---

## Task 9: Tests + CI

**Commit:** `ci(skilltree): add test workflow`
