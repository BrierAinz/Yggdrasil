# TerminalDashboard — TUI Beautiful para Yggdrasil

> **For Hermes:** Use subagent-driven-development skill to implement this plan task-by-task.

**Goal:** Interfaz terminal (Textual/Rich) que muestra status de todos los realms, proyectos activos, health checks, y permite navegar el ecosistema desde una sola pantalla.

**Architecture:** Single Textual app con paneles por realm → status polling → real-time updates → keyboard navigation. Reemplaza los .bat sueltos.

**Tech Stack:** Python 3.11+, Textual, Rich, asyncio, SQLite (read from existing schemas).

**Realm:** Alfheim/TerminalDashboard/

---

## Task 1: Scaffold del proyecto

Files: `Alfheim/TerminalDashboard/`, pyproject.toml con textual, rich, asyncio, psutil.

**Commit:** `feat(term dashboard): scaffold project`

---

## Task 2: Realm status scanner

Escanea todos los realms y recopila:
- Proyectos en cada realm (git status, test status, last commit)
- Health checks (services running, ports, disk usage)
- Active branches, uncommitted changes
- Test pass rates

```python
class RealmScanner:
    def scan_all(self) -> dict[str, RealmStatus]:
        """Scan all 9 realms for status."""
        ...

    def scan_realm(self, realm: str) -> RealmStatus:
        """Scan a single realm."""
        ...
```

**Commit:** `feat(term dashboard): realm status scanner`

---

## Task 3: Textual app structure

Layout principal:
- Header: Yggdrasil logo + timestamp
- Sidebar: 9 realms navigation
- Main: realm detail view
- Footer: keybindings help

```python
class YggdrasilDashboard(App):
    CSS_PATH = "styles.tcss"
    BINDINGS = [
        ("q", "quit", "Quit"),
        ("r", "refresh", "Refresh"),
        ("1-9", "switch_realm", "Switch Realm"),
    ]
```

**Commit:** `feat(term dashboard): Textual app structure`

---

## Task 4: Realm detail views

Cada realm tiene su view personalizado:
- Asgard: Lilith status, active providers, memory usage
- Vanaheim: agents status, running tasks
- Midgard: app dashboards (FinTracker, HabitForge)
- Svartalfheim: wiki stats, docs freshness
- Alfheim: UI prototypes, dashboards
- Muspelheim: WIP projects, branch status
- Niflheim: resources, model inventory, disk usage
- Jotunheim: large project status
- Helheim: archived items count

**Commit:** `feat(term dashboard): realm detail views`

---

## Task 5: Real-time updates

Auto-refresh cada N segundos con asyncio. Cambios resaltados con flash animation. Notificaciones para: test failures, service down, new commits.

**Commit:** `feat(term dashboard): real-time updates`

---

## Task 6: Quick actions

Keyboard shortcuts para acciones comunes:
- `t` — run tests for current realm
- `g` — git status/commit
- `h` — health check
- `o` — open in VS Code
- `d` — open docs in browser

**Commit:** `feat(term dashboard): quick actions`

---

## Task 7: System health panel

CPU, RAM, GPU usage, disk space, Python processes. Integración con el RTX 3060 monitoring (nvidia-smi).

**Commit:** `feat(term dashboard): system health panel`

---

## Task 8: Tests + CI

**Commit:** `ci(term dashboard): add test workflow`
