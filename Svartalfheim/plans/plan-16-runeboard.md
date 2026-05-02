# RuneBoard — Kanban Personal con Runas Sagradas nórdicas.

> **For Hermes:** Use subagent-driven-development skill to implement this plan task-by-task.

**Goal:** Kanban board con drag-and-drop, soporte para 9 realms como columnas/swimlanes, runas como labels, e integración con git commits. TUI con Textual.

**Architecture:** SQLite storage → Textual TUI → drag-and-drop columns → git integration → Rich rendering. Local-first, sin servidor.

**Tech Stack:** Python 3.11+, Textual, Rich, SQLite, gitpython, Typer.

**Realm:** Midgard/RuneBoard/

---

## Task 1: Scaffold del proyecto

Files: `Midgard/RuneBoard/`, pyproject.toml con textual, rich, gitpython, typer.

**Commit:** `feat(runeboard): scaffold project`

---

## Task 2: Data model y SQLite

```python
@dataclass
class Board:
    id: int | None
    name: str
    description: str = ""
    realms: list[str] = field(default_factory=lambda: [
        "Asgard", "Vanaheim", "Alfheim", "Svartalfheim",
        "Midgard", "Muspelheim", "Niflheim", "Jotunheim", "Helheim"
    ])

@dataclass
class Card:
    id: int | None
    title: str
    description: str = ""
    column: str = "todo"  # todo, in-progress, review, done
    realm: str = "Midgard"
    rune: Rune | None = None  # Fehu, Uruz, Thurisaz... as labels
    priority: int = 0  # 0=low, 1=medium, 2=high, 3=critical
    assignee: str = ""
    tags: list[str] = field(default_factory=list)
    git_branch: str | None = None
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)
    due_date: date | None = None

class Rune(Enum):
    FEHU = "ᚠ"      # Wealth/Success
    URUZ = "ᚢ"       # Strength/Health
    THURISAZ = "ᚦ"   # Protection/Conflict
    ANSUZ = "ᚨ"      # Wisdom/Communication
    RAIDHO = "ᚱ"     # Journey/Progress
    KENAZ = "ᚲ"       # Knowledge/Creativity
    GEBO = "ᚷ"        # Gift/Collaboration
    WUNJO = "ᚹ"       # Joy/Harmony
    HAGALAZ = "ᚺ"     # Disruption/Change
    NAUTHIZ = "ᚾ"     # Need/Constraint
    ISA = "ᛁ"         # Ice/Pause
    JERA = "ᛃ"        # Harvest/Cycle
    EIHWAZ = "ᛇ"      # Defense/Endurance
    PERTHRO = "ᛈ"     # Mystery/Chance
    ALGIZ = "ᛉ"       # Protection/Shielding
    TIWAZ = "ᛏ"       # Justice/Sacrifice
```

**Commit:** `feat(runeboard): data model with Norse runes`

---

## Task 3: Column management

Columnas por defecto: Backlog → Todo → In Progress → Review → Done. Columnas personalizables. WIP limits opcionales.

**Commit:** `feat(runeboard): column management`

---

## Task 4: Textual TUI — Board view

Tablero Kanban visual en terminal:
- Columnas horizontales con cards
- Colores por realm (Asgard=gold, Helheim=crimson, etc.)
- Runas como labels visuales
- Priority indicators
- Due date highlighting

**Commit:** `feat(runeboard): Textual Kanban board view`

---

## Task 5: Card CRUD y drag-and-drop

```bash
runeboard add "Implement auth" --realm Asgard --rune Ansuz --priority high
runeboard move <card-id> --column "in-progress"
runeboard edit <card-id> --description "New description"
runeboard list --column todo --realm Midgard
runeboard done <card-id>
```

**Commit:** `feat(runeboard): card CRUD and movement`

---

## Task 6: Git integration

Asociar cards con git branches/commits:
- Auto-detectar branch name → card
- `runeboard commit <card-id>` → stage + commit con mensaje que referencia card
- `runeboard review <card-id>` → mostrar diff desde último commit del card

**Commit:** `feat(runeboard): git integration`

---

## Task 7: Filter, search y stats

```bash
runeboard filter --rune Fehu --priority high
runeboard search "auth"
runeboard stats                    # velocity, completion rate
runeboard stats --realm Asgard     # per-realm stats
```

**Commit:** `feat(runeboard): filtering and stats`

---

## Task 8: Export/import

Export a Markdown (Yggdrasil docs), JSON, CSV. Import desde CSV.

**Commit:** `feat(runeboard): export/import`

---

## Task 9: Tests + CI

**Commit:** `ci(runeboard): add test workflow`
