# YggSite Generator — Generador de Sitios Estáticos para el Ecosistema

> **For Hermes:** Use subagent-driven-development skill to implement this plan task-by-task.

**Goal:** Genera el sitio web de Yggdrasil (GitHub Pages) automáticamente desde los datos de los 9 realms. Un solo comando `yggdrasil build` genera todo el site actualizado con info de cada realm.

**Architecture:** Realm scanner → data collection → Jinja2 templates → static HTML/CSS/JS → GitHub Pages deploy. Se conecta a la estructura existente del website en `/website/`.

**Tech Stack:** Python 3.11+, Jinja2, Typer, Rich, PyYAML, httpx (para API calls).

**Realm:** Alfheim/YggSiteGenerator/

---

## Task 1: Scaffold del proyecto

Files: `Alfheim/YggSiteGenerator/`, pyproject.toml con jinja2, typer, rich, pyyaml, httpx.

**Commit:** `feat(yggsite): scaffold project`

---

## Task 2: Realm data collector

Escanea cada realm y recopila:
- Proyectos (nombre, descripción, status, tech stack, repo URL)
- README info
- Test status (si existe pytest.ini o similar)
- Last commit date
- Language breakdown

```python
class RealmCollector:
    def collect(self, realm_path: str) -> RealmData:
        """Scan a realm directory and collect project data."""
        ...

    def collect_all(self) -> dict[str, RealmData]:
        """Scan all 9 realms."""
        ...
```

**Commit:** `feat(yggsite): realm data collector`

---

## Task 3: Template system (Jinja2)

Templates para:
- `index.html` — Landing page con overview del ecosistema
- `realm.html` — Página por realm (reutilizable, datos inyectados)
- `project.html` — Página por proyecto
- `architecture.html` — Diagramas Yggdrasil
- `sitemap.xml` — Auto-generado

Los templates usan el dark theme existente del website actual.

**Commit:** `feat(yggsite): Jinja2 template system`

---

## Task 4: GitHub stats integration

Usa GitHub API (httpx) para:
- Stars, forks, last activity
- Contributors
- Release info
- CI status

```python
class GitHubStatsCollector:
    def collect(self, repo: str) -> GitHubStats:
        ...
```

**Commit:** `feat(yggsite): GitHub stats integration`

---

## Task 5: Build system

```bash
yggdrasil build                    # generate full site
yggdrasil build --realm Asgard     # only Asgard page
yggdrasil build --watch            # watch for changes, rebuild
yggdrasil serve                    # local preview on :8080
yggdrasil deploy                   # deploy to GitHub Pages
```

El builder genera HTML en `website/` directo, listo para GitHub Pages.

**Commit:** `feat(yggsite): build system`

---

## Task 6: Auto-index de documentación

Escanea Svartalfheim/wiki y genera índice de documentación automáticamente. Links a ADRs, features, y guías.

**Commit:** `feat(yggsite): auto documentation indexing`

---

## Task 7: Diagramas generados

Genera árbol Yggdrasil (SVG) dinámicamente basado en datos reales:
- Nodos = realms con project count
- Líneas = conexiones entre realms
- Color coding por estado

**Commit:** `feat(yggsite): dynamic Yggdrasil tree diagram`

---

## Task 8: CI integration

Workflow que corre `yggdrasil build` + `yggdrasil deploy` en cada push a main. Solo re-deploy si hay cambios.

**Commit:** `ci(yggsite): auto-build and deploy workflow`
